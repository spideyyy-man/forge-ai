"""Project schemas."""
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import Optional, Dict, Any, List


class ProjectCreate(BaseModel):
    workspace_id: UUID
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    root_path: str = Field(..., min_length=1)
    privacy_mode: str = Field(default="CLOUD_ASSISTED")
    settings: Optional[Dict[str, Any]] = None


class ProjectResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    user_id: UUID
    name: str
    description: Optional[str] = None
    root_path: str
    detected_languages: Optional[List[str]] = None
    detected_frameworks: Optional[List[str]] = None
    privacy_mode: str
    status: str
    last_indexed_at: Optional[datetime] = None
    settings: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    privacy_mode: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None
