"""Workspace schemas."""
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import Optional, Dict, Any


class WorkspaceCreate(BaseModel):
    device_id: UUID
    name: str = Field(..., min_length=1, max_length=200)
    root_path: str = Field(..., min_length=1)
    settings: Optional[Dict[str, Any]] = None


class WorkspaceResponse(BaseModel):
    id: UUID
    device_id: UUID
    user_id: UUID
    name: str
    root_path: str
    is_active: bool
    settings: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class WorkspaceUpdate(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None
    settings: Optional[Dict[str, Any]] = None
