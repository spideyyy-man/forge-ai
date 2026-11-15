"""Device schemas."""
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import Optional, Dict, Any


class DeviceRegister(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    device_type: str = Field(default="WINDOWS")
    os_info: Optional[Dict[str, Any]] = None


class DevicePair(BaseModel):
    pairing_code: str = Field(..., min_length=6, max_length=6)
    device_id: UUID


class DeviceResponse(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    device_type: str
    status: str
    pairing_code: Optional[str] = None
    last_seen_at: Optional[datetime] = None
    agent_version: Optional[str] = None
    os_info: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class DeviceStatusUpdate(BaseModel):
    status: Optional[str] = None
    agent_version: Optional[str] = None
    os_info: Optional[Dict[str, Any]] = None
