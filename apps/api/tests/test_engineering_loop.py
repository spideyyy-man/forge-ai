"""Unit tests for the bounded tool-calling engineering loop.

The loop's collaborators (model, remote tool exec, approval, emit) are injected, so
these tests drive it with fakes and assert the approval gate, undo buffer, rejection
path, and step bound — no network or local agent required.
"""
import json
import pytest

from app.agents.engineering_loop import run_engineering_loop, message_to_dict


class FakeMessage:
    """Mimics a LiteLLM response message object."""
    def __init__(self, content=None, tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls


class FakeToolCall:
    def __init__(self, call_id, name, arguments):
        self.id = call_id
        self.type = "function"
        self.function = type("F", (), {"name": name, "arguments": arguments})()


def _tool_call(call_id, name, **args):
    return FakeToolCall(call_id, name, json.dumps(args))


async def _noop_emit(event):
    pass


async def _always_fail_tool(name, args):
    raise AssertionError(f"exec_tool should not be called for {name} in this test")


async def test_plain_text_answer_ends_loop():
    """A completion with no tool calls returns immediately as the final text."""
    async def complete(messages, tools):
        return {"success": True, "message": FakeMessage(content="Here is my analysis.")}

    result = await run_engineering_loop(
        description="Explain the repo", repo_context="", workspace_path="/ws",
        complete=complete, exec_tool=_always_fail_tool,
        request_approval=lambda p: pytest.fail("no approval expected"),
        emit=_noop_emit, device_connected=True,
    )
    assert result["text"] == "Here is my analysis."
    assert result["modified_files"] == []
    assert result["steps"] == 1


async def test_read_tool_runs_without_approval_then_summary():
    """Read tools execute immediately; a following text turn ends the loop."""
    turns = [
        FakeMessage(tool_calls=[_tool_call("c1", "read_file", path="/ws/app.py")]),
        FakeMessage(content="I read app.py; nothing to change."),
    ]
    calls = []

    async def complete(messages, tools):
        return {"success": True, "message": turns[len(calls)]}

    async def exec_tool(name, args):
        calls.append((name, args))
        return {"success": True, "content": "print('hi')\n"}

    approvals = []
    result = await run_engineering_loop(
        description="look", repo_context="", workspace_path="/ws",
        complete=complete, exec_tool=exec_tool,
        request_approval=lambda p: approvals.append(p) or True,
        emit=_noop_emit, device_connected=True,
    )
    assert calls == [("read_file", {"path": "/ws/app.py"})]
    assert approvals == []  # read tools are never gated
    assert "app.py" in result["text"]


async def test_apply_edit_requires_approval_and_records_undo():
    """apply_edit: dry-run preview -> approval -> real write -> undo buffer captured."""
    turns = [
        FakeMessage(tool_calls=[_tool_call("c1", "apply_edit", path="/ws/a.py", content="new\n")]),
        FakeMessage(content="Edited a.py."),
    ]
    completions = {"n": 0}
    exec_log = []
    proposals = []

    async def complete(messages, tools):
        m = turns[completions["n"]]
        completions["n"] += 1
        return {"success": True, "message": m}

    async def exec_tool(name, args):
        exec_log.append((name, dict(args)))
        if name == "apply_edit" and args.get("dry_run"):
            return {"success": True, "diff": "--- a/a.py\n+++ b/a.py\n+new", "additions": 1,
                    "deletions": 0, "created": False, "unchanged": False}
        if name == "apply_edit":
            return {"success": True, "old_content": "old\n", "created": False, "size": 4}
        return {"success": True}

    async def request_approval(proposal):
        proposals.append(proposal)
        return True

    result = await run_engineering_loop(
        description="edit a.py", repo_context="", workspace_path="/ws",
        complete=complete, exec_tool=exec_tool, request_approval=request_approval,
        emit=_noop_emit, device_connected=True,
    )

    # Dry-run happened before the real write.
    assert exec_log[0] == ("apply_edit", {"path": "/ws/a.py", "content": "new\n", "dry_run": True})
    assert exec_log[1] == ("apply_edit", {"path": "/ws/a.py", "content": "new\n", "dry_run": False})
    assert len(proposals) == 1 and proposals[0]["kind"] == "edit" and proposals[0]["additions"] == 1
    assert result["modified_files"] == ["/ws/a.py"]
    assert result["undo"] == [{"path": "/ws/a.py", "old_content": "old\n", "was_created": False}]


async def test_apply_edit_rejected_is_not_written():
    """If the user rejects, no real write happens and nothing is recorded as modified."""
    turns = [
        FakeMessage(tool_calls=[_tool_call("c1", "apply_edit", path="/ws/a.py", content="new\n")]),
        FakeMessage(content="Understood, I won't change it."),
    ]
    completions = {"n": 0}
    real_writes = []

    async def complete(messages, tools):
        m = turns[completions["n"]]
        completions["n"] += 1
        return {"success": True, "message": m}

    async def exec_tool(name, args):
        if name == "apply_edit" and args.get("dry_run"):
            return {"success": True, "diff": "+new", "additions": 1, "deletions": 0,
                    "created": False, "unchanged": False}
        if name == "apply_edit":
            real_writes.append(args)
            return {"success": True, "old_content": "old\n"}
        return {"success": True}

    async def reject(proposal):
        return False

    result = await run_engineering_loop(
        description="edit", repo_context="", workspace_path="/ws",
        complete=complete, exec_tool=exec_tool, request_approval=reject,
        emit=_noop_emit, device_connected=True,
    )
    assert real_writes == []            # never wrote
    assert result["modified_files"] == []
    assert result["undo"] == []


async def test_no_device_falls_back_to_text_without_tools():
    """Without a connected agent the loop must not offer tools and cannot edit."""
    seen_tools = {}

    async def complete(messages, tools):
        seen_tools["tools"] = tools
        return {"success": True, "message": FakeMessage(content="Connect the agent to edit.")}

    result = await run_engineering_loop(
        description="edit", repo_context="", workspace_path="/ws",
        complete=complete, exec_tool=_always_fail_tool,
        request_approval=lambda p: pytest.fail("no approval"),
        emit=_noop_emit, device_connected=False,
    )
    assert seen_tools["tools"] is None
    assert result["modified_files"] == []


async def test_loop_is_bounded_by_max_steps():
    """A model that loops forever on tool calls is stopped at max_steps."""
    async def complete(messages, tools):
        return {"success": True, "message": FakeMessage(
            tool_calls=[_tool_call("c", "read_file", path="/ws/x")])}

    async def exec_tool(name, args):
        return {"success": True, "content": "..."}

    result = await run_engineering_loop(
        description="loop", repo_context="", workspace_path="/ws",
        complete=complete, exec_tool=exec_tool,
        request_approval=lambda p: True, emit=_noop_emit,
        device_connected=True, max_steps=3,
    )
    assert result["steps"] == 3
    assert "maximum number of steps" in result["text"].lower()


def test_message_to_dict_normalizes_tool_calls():
    msg = FakeMessage(content="", tool_calls=[_tool_call("id1", "read_file", path="/a")])
    d = message_to_dict(msg)
    assert d["role"] == "assistant"
    assert d["tool_calls"][0]["id"] == "id1"
    assert d["tool_calls"][0]["function"]["name"] == "read_file"
    assert json.loads(d["tool_calls"][0]["function"]["arguments"]) == {"path": "/a"}
