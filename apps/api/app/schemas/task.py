"""Task schemas."""
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import Optional, List, Dict, Any


class TaskCreate(BaseModel):
    conversation_id: UUID
    project_id: UUID
    description: str = Field(..., min_length=1)
    complexity: str = Field(default="MODERATE")
    priority: int = Field(default=5, ge=1, le=10)
    model_override: Optional[str] = None
    agent_type: Optional[str] = None


class TaskResponse(BaseModel):
    id: UUID
    conversation_id: UUID
    project_id: UUID
    user_id: UUID
    description: str
    status: str
    complexity: str
    priority: int
    model_used: Optional[str] = None
    agent_type: Optional[str] = None
    plan: Optional[Dict[str, Any]] = None
    completed_steps: Optional[List[Dict[str, Any]]] = None
    modified_files: Optional[List[str]] = None
    commands_executed: Optional[List[Dict[str, Any]]] = None
    verification_results: Optional[Dict[str, Any]] = None
    token_usage: Optional[Dict[str, Any]] = None
    error_info: Optional[Dict[str, Any]] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class TaskUpdate(BaseModel):
    status: Optional[str] = None
    plan: Optional[Dict[str, Any]] = None


class TaskStepResult(BaseModel):
    step_name: str
    status: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    duration_ms: Optional[float] = None
