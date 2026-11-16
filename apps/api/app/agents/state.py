"""Agent state schema for LangGraph workflows."""
from typing import List, Dict, Any, Optional, Annotated
from typing_extensions import TypedDict
import operator


class AgentExecutionState(TypedDict):
    task_id: str
    user_id: str
    device_id: Optional[str]
    workspace_path: str
    configured_keys: Optional[Dict[str, Any]]  # provider -> list[str] of keys (rotation)
    privacy_mode: Optional[str]  # CLOUD_ASSISTED | LOCAL_ONLY (enforced outside the model)
    repo_context: Optional[str]
    model_candidates: Optional[List[Dict[str, str]]]
    description: str
    status: str
    plan: List[str]
    current_step_index: int
    messages: Annotated[List[Dict[str, Any]], operator.add]
    modified_files: Annotated[List[str], operator.add]
    executed_commands: Annotated[List[Dict[str, Any]], operator.add]
    undo_buffer: Optional[List[Dict[str, Any]]]  # per-file {path, old_content, was_created} for rollback
    diagnostics: Optional[Dict[str, Any]]
    error: Optional[str]
    repair_context: Optional[str]  # test-failure output fed into the next coding pass
    verification_passed: bool
    retry_count: int
    max_retries: int
