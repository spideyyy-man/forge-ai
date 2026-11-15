"""Conversation schemas."""
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import Optional, List, Dict, Any


class ConversationCreate(BaseModel):
    project_id: Optional[UUID] = None
    title: Optional[str] = None
    model_id: Optional[str] = None
    agent_type: Optional[str] = "general"


class ConversationResponse(BaseModel):
    id: UUID
    user_id: UUID
    project_id: Optional[UUID] = None
    title: Optional[str] = None
    model_id: Optional[str] = None
    agent_type: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class MessageCreate(BaseModel):
    role: str = Field(default="user")
    content: str = Field(..., min_length=1)
    model_override: Optional[str] = None


class MessageResponse(BaseModel):
    id: UUID
    conversation_id: UUID
    role: str
    content: str
    model_used: Optional[str] = None
    token_count: Optional[int] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_results: Optional[List[Dict[str, Any]]] = None
    created_at: datetime

    model_config = {"from_attributes": True}
