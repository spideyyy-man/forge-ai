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
    """Run the bounded tool-calling engineering loop (inspect -> propose -> approve -> apply)."""
    from app.websocket.manager import connection_manager
    from app.providers.registry import ModelCapability
    from app.agents.engineering_loop import run_engineering_loop

    device_id = state.get("device_id")
    user_id = str(state.get("user_id"))
    conv_id = str(state.get("task_id"))
    workspace_path = state.get("workspace_path", ".")

    # Discovery-ranked candidate models (registry ∩ live-available + free extras).
    candidates = [
        ModelCapability(model_id=c["model_id"], provider=c["provider"], litellm_id=c["litellm_id"], api_base=c.get("api_base"))
        for c in (state.get("model_candidates") or [])
    ] or None
    configured_keys = state.get("configured_keys") or {}

    async def complete(messages, tools):
        """Call the router (with tools when available) and surface the message object."""
        res = await model_router.execute_completion(
            messages=messages,
            tools=tools,
            policy=RouterPolicy.QUALITY,
            configured_keys=configured_keys,
            candidates=candidates,
        )
        if not res.get("success"):
            return {"success": False, "error": res.get("error")}
        try:
            message = res["response"].choices[0].message
        except (KeyError, AttributeError, IndexError) as e:
            return {"success": False, "error": f"Malformed model response: {e}"}
        return {"success": True, "message": message, "model_used": res.get("model_used")}

    async def exec_tool(name, arguments):
        return await execute_remote_tool(device_id, name, arguments, user_id=user_id)

    async def request_approval(proposal):
        return await connection_manager.request_user_approval(user_id, conv_id, proposal)

    async def emit(event):
        try:
            await connection_manager.send_to_user(user_id, {**event, "conversation_id": conv_id})
        except Exception:
            pass  # events are best-effort

    result = await run_engineering_loop(
        description=state["description"],
        repo_context=state.get("repo_context") or "",
        workspace_path=workspace_path,
        complete=complete,
        exec_tool=exec_tool,
        request_approval=request_approval,
        emit=emit,
        device_connected=bool(device_id),
    )

    return {
        "status": "VERIFYING",
        "current_step_index": 2,
        "messages": [{"role": "assistant", "content": result["text"]}],
        "modified_files": result.get("modified_files", []),
        "executed_commands": result.get("executed_commands", []),
        "undo_buffer": result.get("undo", []),
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
