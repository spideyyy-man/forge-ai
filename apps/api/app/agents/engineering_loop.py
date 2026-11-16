"""Bounded tool-calling engineering loop.

This is the core of the agent: instead of emitting a single block of text, the model
is given a small set of tools and runs a bounded plan->act->observe loop. Read/inspect
tools run immediately against the paired local agent; write/command tools are
APPROVAL-GATED — the loop asks the user (over WebSocket) before anything touches disk.

The loop is dependency-injected (``complete``, ``exec_tool``, ``request_approval``,
``emit``) so it can be unit-tested with fakes and has no direct import of the router,
WebSocket manager, or local agent.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Awaitable, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

# Tools the model may call. Read tools auto-execute; write/command tools need approval.
READ_TOOLS = {"read_file", "list_directory", "search_text", "git_status", "git_diff"}
WRITE_TOOLS = {"apply_edit", "execute_command", "git_commit"}

TOOL_DEFS: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a file's contents from the workspace. Prefer this over guessing file contents.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Absolute or workspace-relative file path."},
                    "start_line": {"type": "integer"},
                    "end_line": {"type": "integer"},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_directory",
            "description": "List files and subdirectories of a directory in the workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "recursive": {"type": "boolean"},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_text",
            "description": "Search workspace file contents for a string or regex. Returns matching files and lines.",
            "parameters": {
                "type": "object",
                "properties": {
                    "root_path": {"type": "string"},
                    "query": {"type": "string"},
                    "file_patterns": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["root_path", "query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "git_status",
            "description": "Show the working-tree status of the repository.",
            "parameters": {
                "type": "object",
                "properties": {"repo_path": {"type": "string"}},
                "required": ["repo_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "git_diff",
            "description": "Show the current git diff of the repository.",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo_path": {"type": "string"},
                    "staged": {"type": "boolean"},
                },
                "required": ["repo_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "apply_edit",
            "description": (
                "Replace a file's ENTIRE contents with `content` (creating it if needed). "
                "Provide the full intended file, not a patch. The user must approve the diff "
                "before it is written. Use this for every code change."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string", "description": "The full new file contents."},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "execute_command",
            "description": (
                "Run a shell command in the workspace (e.g. run tests, install deps). "
                "Requires user approval. Destructive commands are blocked by the local agent."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string"},
                    "cwd": {"type": "string"},
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "git_commit",
            "description": "Commit staged/working changes with a message. Requires user approval.",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo_path": {"type": "string"},
                    "message": {"type": "string"},
                },
                "required": ["repo_path", "message"],
            },
        },
    },
]

SYSTEM_INSTRUCTIONS = (
    "You are FORGE AI, a senior autonomous software engineer working directly in the "
    "user's real repository through tools. Ground every action in the actual code: read "
    "files before editing them, and reference real paths. To change code, call `apply_edit` "
    "with the COMPLETE new file contents — the user reviews and approves each diff before it "
    "is written, so make focused, correct edits. After editing, you may run tests via "
    "`execute_command`. When the task is done, reply with a short plain-text summary of what "
    "you changed and why (no tool call). Do not claim you changed a file unless an apply_edit "
    "for it was approved and succeeded. If a tool returns an error or a rejection, adapt."
)

# Type aliases for the injected collaborators.
CompleteFn = Callable[[List[Dict[str, Any]], Optional[List[Dict[str, Any]]]], Awaitable[Dict[str, Any]]]
ExecToolFn = Callable[[str, Dict[str, Any]], Awaitable[Dict[str, Any]]]
ApprovalFn = Callable[[Dict[str, Any]], Awaitable[bool]]
EmitFn = Callable[[Dict[str, Any]], Awaitable[None]]


def message_to_dict(msg: Any) -> Dict[str, Any]:
    """Normalize a LiteLLM response message into a plain, re-sendable dict."""
    content = getattr(msg, "content", None)
    if isinstance(msg, dict):
        content = msg.get("content")
        tool_calls = msg.get("tool_calls")
    else:
        tool_calls = getattr(msg, "tool_calls", None)
    d: Dict[str, Any] = {"role": "assistant", "content": content or ""}
    if tool_calls:
        norm = []
        for tc in tool_calls:
            if isinstance(tc, dict):
                fn = tc.get("function", {})
                norm.append({
                    "id": tc.get("id"),
                    "type": "function",
                    "function": {"name": fn.get("name"), "arguments": fn.get("arguments") or "{}"},
                })
            else:
                norm.append({
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments or "{}"},
                })
        d["tool_calls"] = norm
    return d


def _parse_args(raw: Any) -> Dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    try:
        return json.loads(raw or "{}")
    except (json.JSONDecodeError, TypeError):
        return {}


async def run_engineering_loop(
    *,
    description: str,
    repo_context: str,
    workspace_path: str,
    complete: CompleteFn,
    exec_tool: ExecToolFn,
    request_approval: ApprovalFn,
    emit: EmitFn,
    device_connected: bool,
    max_steps: int = 12,
) -> Dict[str, Any]:
    """Run the bounded tool-calling loop. Returns a result summary dict.

    Keys: text, modified_files, executed_commands, undo (list of {path, old_content,
    was_created} for rollback), steps.
    """
    stable = f"{SYSTEM_INSTRUCTIONS}\n\nActive workspace: {workspace_path}"
    if repo_context:
        stable += f"\n\n=== REPOSITORY SNAPSHOT ===\n{repo_context}\n=== END SNAPSHOT ==="
    else:
        stable += "\n(No repository snapshot available.)"

    messages: List[Dict[str, Any]] = [
        {"role": "system", "content": stable},
        {"role": "user", "content": f"Task: {description}"},
    ]

    modified_files: List[str] = []
    executed_commands: List[Dict[str, Any]] = []
    undo: List[Dict[str, Any]] = []

    # Without a connected agent we cannot run tools, so fall back to a single advisory reply.
    tools = TOOL_DEFS if device_connected else None

    for step in range(max_steps):
        res = await complete(messages, tools)
        if not res.get("success"):
            return {
                "text": f"Model fallback exhausted: {res.get('error')}",
                "modified_files": modified_files,
                "executed_commands": executed_commands,
                "undo": undo,
                "steps": step,
            }

        msg_dict = message_to_dict(res["message"])
        messages.append(msg_dict)
        tool_calls = msg_dict.get("tool_calls")

        if not tool_calls:
            return {
                "text": msg_dict.get("content") or "Done.",
                "modified_files": modified_files,
                "executed_commands": executed_commands,
                "undo": undo,
                "steps": step + 1,
            }

        for tc in tool_calls:
            name = tc["function"]["name"]
            args = _parse_args(tc["function"]["arguments"])
            call_id = tc.get("id")
            await emit({"type": "agent_event", "event_type": "tool_call", "tool": name, "arguments": args})

            if not device_connected:
                result = {"success": False, "error": "No local agent connected; cannot run tools."}
            elif name in READ_TOOLS:
                result = await exec_tool(name, args)
            elif name in WRITE_TOOLS:
                result = await _handle_write_tool(name, args, exec_tool, request_approval, emit,
                                                  modified_files, executed_commands, undo)
            else:
                result = {"success": False, "error": f"Unknown tool: {name}"}

            await emit({"type": "agent_event", "event_type": "tool_result", "tool": name,
                        "ok": bool(result.get("success", False))})
            messages.append({
                "role": "tool",
                "tool_call_id": call_id,
                "name": name,
                "content": json.dumps(_summarize_for_model(name, result))[:8000],
            })

    return {
        "text": "Reached the maximum number of steps for this task without a final summary.",
        "modified_files": modified_files,
        "executed_commands": executed_commands,
        "undo": undo,
        "steps": max_steps,
    }


async def _handle_write_tool(
    name: str,
    args: Dict[str, Any],
    exec_tool: ExecToolFn,
    request_approval: ApprovalFn,
    emit: EmitFn,
    modified_files: List[str],
    executed_commands: List[Dict[str, Any]],
    undo: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Run an approval-gated tool: build a preview, ask the user, then apply or reject."""
    if name == "apply_edit":
        # Dry-run first (no write) to compute the diff shown for approval.
        preview = await exec_tool("apply_edit", {**args, "dry_run": True})
        if not preview.get("success"):
            return preview
        if preview.get("unchanged"):
            return {"success": True, "skipped": True, "reason": "No change (new content identical)."}
        proposal = {
            "kind": "edit",
            "path": args.get("path"),
            "diff": preview.get("diff"),
            "additions": preview.get("additions"),
            "deletions": preview.get("deletions"),
            "created": preview.get("created"),
        }
        approved = await request_approval(proposal)
        if not approved:
            return {"success": False, "rejected": True, "error": "User rejected the edit."}
        applied = await exec_tool("apply_edit", {**args, "dry_run": False})
        if applied.get("success"):
            modified_files.append(args.get("path"))
            undo.append({
                "path": args.get("path"),
                "old_content": applied.get("old_content"),
                "was_created": bool(applied.get("created")),
            })
        return applied

    if name == "execute_command":
        proposal = {"kind": "command", "command": args.get("command"), "cwd": args.get("cwd")}
        approved = await request_approval(proposal)
        if not approved:
            return {"success": False, "rejected": True, "error": "User rejected the command."}
        result = await exec_tool("execute_command", args)
        executed_commands.append({"command": args.get("command"), "ok": bool(result.get("success"))})
        return result

    if name == "git_commit":
        proposal = {"kind": "commit", "repo_path": args.get("repo_path"), "message": args.get("message")}
        approved = await request_approval(proposal)
        if not approved:
            return {"success": False, "rejected": True, "error": "User rejected the commit."}
        return await exec_tool("git_commit", args)

    return {"success": False, "error": f"Unhandled write tool: {name}"}


def _summarize_for_model(name: str, result: Dict[str, Any]) -> Dict[str, Any]:
    """Trim tool results before feeding them back to the model.

    apply_edit echoes old_content (the undo buffer) which the model does not need and
    which wastes tokens — strip it.
    """
    if name == "apply_edit" and isinstance(result, dict):
        return {k: v for k, v in result.items() if k not in ("old_content", "diff")}
    return result
