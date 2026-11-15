"""WebSocket message protocol."""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from uuid import uuid4


class BaseMessage(BaseModel):
    type: str
    id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    correlation_id: Optional[str] = None


class ToolRequest(BaseMessage):
    type: str = "tool_request"
    tool_name: str = ""
    arguments: Dict[str, Any] = {}
    timeout: int = 300


class ToolResponse(BaseMessage):
    type: str = "tool_response"
    success: bool = True
    result: Optional[Any] = None
    error: Optional[str] = None
    execution_time_ms: Optional[float] = None
