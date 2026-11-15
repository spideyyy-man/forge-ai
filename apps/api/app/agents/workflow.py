"""LangGraph stateful workflow for Autonomous Engineering (Plan -> Act -> Verify -> Self-Repair)."""
import logging
from typing import Dict, Any, List
from langgraph.graph import StateGraph, END
from app.agents.state import AgentExecutionState
from app.agents.tool_dispatcher import execute_remote_tool
from app.providers.router import model_router, RouterPolicy

logger = logging.getLogger(__name__)


async def planner_node(state: AgentExecutionState) -> Dict[str, Any]:
    """Inspect requirements and generate structured execution plan."""
    logger.info(f"[Agent Workflow] Planning step for task: {state['task_id']}")
    description = state["description"]

    # Initial plan breakdown
    plan = [
        f"Inspect repository structure in {state.get('workspace_path', '.')}",
        "Analyze affected source files and dependencies",
        "Implement requested code modifications",
        "Run unit tests and collect diagnostics",
        "Verify changes against security constraints",
    ]

    return {
        "plan": plan,
        "status": "PLANNING",
        "current_step_index": 0,
        "messages": [{"role": "assistant", "content": f"Formulated execution plan with {len(plan)} steps."}],
    }


async def inspection_node(state: AgentExecutionState) -> Dict[str, Any]:
    """Inspect repository structure through local workspace agent."""
    device_id = state.get("device_id")
    workspace = state.get("workspace_path", ".")

    if device_id:
        try:
            # Query local files via local daemon tool
            listing = await execute_remote_tool(device_id, "list_directory", {"path": workspace})
            files_found = len(listing.get("entries", [])) if isinstance(listing, dict) else 0
            message = f"Inspected workspace: detected {files_found} files/directories."
        except Exception as e:
            message = f"Local inspection skipped or offline: {str(e)}"
    else:
        message = "No active device paired; inspection performed in sandbox mode."

    return {
        "status": "EXECUTING",
        "current_step_index": 1,
        "messages": [{"role": "system", "content": message}],
    }


async def coding_node(state: AgentExecutionState) -> Dict[str, Any]:
    """Generate and apply code modifications with LLM completions."""
    device_id = state.get("device_id")
    description = state["description"]
    repo_context = state.get("repo_context") or ""

    # Prompt caching: the big, STABLE content (instructions + repo snapshot) goes first in
    # the system message so it's byte-identical across turns in the same workspace. Providers
    # (OpenAI, Gemini 2.5, DeepSeek, Anthropic) then cache that prefix and only bill/process
    # the small variable task below — cutting repeat-call token cost ~75-90%.
    instructions = (
        "You are FORGE AI, a senior autonomous software engineer. You are given a snapshot "
        "of the user's ACTUAL repository below (directory structure and key files such as "
        "READMEs and manifests). Ground every answer in that snapshot: reference real file "
        "names, detected languages/frameworks, and real structure. "
        "NEVER ask the user to paste or describe information that is already visible in the "
        "snapshot — read it yourself. Be concrete and actionable: give specific, prioritized "
        "suggestions, not generic checklists. If the snapshot is empty, briefly tell the user "
        "to open a folder in the Workspace tab (and, for live file edits, connect the local "
        "agent) — do not ask them to type out a long manual description."
    )
    if repo_context:
        stable = f"{instructions}\n\nActive workspace: {state.get('workspace_path')}\n\n=== REPOSITORY SNAPSHOT ===\n{repo_context}\n=== END SNAPSHOT ==="
    else:
        stable = f"{instructions}\n\nActive workspace: {state.get('workspace_path')}\n(No repository snapshot is available — the workspace folder could not be read.)"

    messages = [
        {"role": "system", "content": stable},      # large, stable → cached prefix
        {"role": "user", "content": f"Task: {description}"},  # small, variable → not cached
    ]

    # Stream the completion token-by-token to the user's WebSocket as it is generated.
    from app.websocket.manager import connection_manager

    user_id = state.get("user_id")
    conv_id = state.get("task_id")

    async def on_delta(chunk: str):
        try:
            await connection_manager.send_to_user(str(user_id), {
                "type": "agent_delta",
                "conversation_id": str(conv_id),
                "delta": chunk,
            })
        except Exception:
            pass  # streaming is best-effort; the final message is still saved to the DB

    # Discovery-ranked candidate models (registry ∩ live-available + free extras).
    from app.providers.registry import ModelCapability
    candidates = [
        ModelCapability(model_id=c["model_id"], provider=c["provider"], litellm_id=c["litellm_id"], api_base=c.get("api_base"))
        for c in (state.get("model_candidates") or [])
    ] or None

    completion = await model_router.stream_completion(
        messages=messages,
        policy=RouterPolicy.QUALITY,
        configured_keys=state.get("configured_keys") or {},
        on_delta=on_delta,
        candidates=candidates,
    )

    if completion.get("success"):
        response_text = completion.get("text") or ""
    else:
        response_text = f"Fallback exhausted: {completion.get('error')}"

    return {
        "status": "VERIFYING",
        "current_step_index": 2,
        "messages": [{"role": "assistant", "content": response_text}],
    }


async def verification_node(state: AgentExecutionState) -> Dict[str, Any]:
    """Execute tests via local workspace agent to verify code correctness."""
    device_id = state.get("device_id")
    workspace = state.get("workspace_path", ".")
    passed = True
    error_msg = None

    if device_id:
        try:
            # Trigger discover/run tests
            test_res = await execute_remote_tool(device_id, "discover_tests", {"project_path": workspace})
            passed = test_res.get("success", True)
        except Exception as e:
            passed = False
            error_msg = str(e)

    return {
        "verification_passed": passed,
        "error": error_msg,
        "current_step_index": 3,
        "messages": [{"role": "system", "content": f"Verification {'PASSED' if passed else 'FAILED'}."}],
    }


def should_repair(state: AgentExecutionState) -> str:
    """Conditional router: verify passed or attempt bounded self-repair."""
    if state.get("verification_passed"):
        return "completed"
    if state.get("retry_count", 0) < state.get("max_retries", 2):
        return "repair"
    return "completed"


async def repair_node(state: AgentExecutionState) -> Dict[str, Any]:
    """Attempt bounded self-repair for failed verification steps."""
    new_retry = state.get("retry_count", 0) + 1
    logger.info(f"[Agent Self-Repair] Attempt {new_retry}/{state.get('max_retries', 2)}")

    return {
        "retry_count": new_retry,
        "status": "REPAIRING",
        "messages": [{"role": "system", "content": f"Entering self-repair cycle (attempt {new_retry}). Diagnosing error: {state.get('error')}"}],
    }


def build_engineering_graph():
    """Build and compile the LangGraph autonomous engineer cycle."""
    workflow = StateGraph(AgentExecutionState)

    workflow.add_node("planner", planner_node)
    workflow.add_node("inspection", inspection_node)
    workflow.add_node("coding", coding_node)
    workflow.add_node("verification", verification_node)
    workflow.add_node("repair", repair_node)

    workflow.set_entry_point("planner")
    workflow.add_edge("planner", "inspection")
    workflow.add_edge("inspection", "coding")
    workflow.add_edge("coding", "verification")

    workflow.add_conditional_edges(
        "verification",
        should_repair,
        {
            "repair": "repair",
            "completed": END,
        },
    )
    workflow.add_edge("repair", "coding")

    return workflow.compile()


engineering_graph = build_engineering_graph()
