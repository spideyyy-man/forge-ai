"""WebSocket message protocol definitions."""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from uuid import uuid4


class WSMessage(BaseModel):
    """Base WebSocket message."""
    type: str
    id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    correlation_id: Optional[str] = None


class ToolRequest(WSMessage):
    """Request to execute a tool on a device."""
    type: str = "tool_request"
    tool_name: str
    arguments: Dict[str, Any] = {}
    timeout: int = 300


class ToolResponse(WSMessage):
    """Response from a tool execution."""
    type: str = "tool_response"
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None
    execution_time_ms: Optional[float] = None


class HeartbeatMessage(WSMessage):
    """Agent heartbeat."""
    type: str = "heartbeat"
    device_id: str = ""
    agent_version: str = ""
    uptime_seconds: float = 0


class DeviceInfoMessage(WSMessage):
    """Device information update."""
    type: str = "device_info"
    device_id: str = ""
    hostname: str = ""
    os_type: str = ""
    os_version: str = ""
    workspaces: List[str] = []


class AgentEvent(WSMessage):
    """Agent execution event for streaming to frontend."""
    type: str = "agent_event"
    event_type: str = ""  # thinking, tool_call, tool_result, plan_update, error, completion
    content: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    task_id: Optional[str] = None


class ApprovalRequest(WSMessage):
    """Request user approval for an operation."""
    type: str = "approval_request"
    operation: str = ""
    description: str = ""
    diff: Optional[str] = None
    command: Optional[str] = None
    path: Optional[str] = None
    risk_level: str = "low"  # low, medium, high, critical


class ApprovalResponse(WSMessage):
    """User response to approval request."""
    type: str = "approval_response"
    request_id: str = ""
    approved: bool = False
    reason: Optional[str] = None


class ExecutionStreamMessage(WSMessage):
    """Streaming command or agent execution output."""
    type: str = "execution_stream"
    user_id: Optional[str] = None
    content: str = ""
    stream_type: str = "stdout"  # stdout, stderr, system


class ErrorMessage(WSMessage):
    """Error message."""
    type: str = "error"
    message: str = ""
    code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
