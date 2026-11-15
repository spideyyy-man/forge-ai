"""Provider schemas."""
from pydantic import BaseModel, Field, field_validator
from uuid import UUID
from datetime import datetime
from typing import Optional, Dict, Any, List

from app.models.provider import ProviderType


class ProviderCreate(BaseModel):
    provider_type: str = Field(..., description="One of the ProviderType values, e.g. OPENAI, GROQ, GOOGLE.")
    display_name: str = Field(..., min_length=1, max_length=100)
    api_key: str = Field(..., min_length=1)
    base_url: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None

    @field_validator("provider_type")
    @classmethod
    def _valid_provider_type(cls, v: str) -> str:
        # Normalize to the stored enum form and reject unknown values so an invalid
        # type can never be written to the enum column (which would break reads/login).
        normalized = (v or "").strip().upper()
        valid = {p.value for p in ProviderType}
        if normalized not in valid:
            raise ValueError(f"Unsupported provider_type '{v}'. Must be one of: {', '.join(sorted(valid))}")
        return normalized


class ProviderResponse(BaseModel):
    id: UUID
    user_id: UUID
    provider_type: str
    display_name: str
    has_api_key: bool = True
    base_url: Optional[str] = None
    is_enabled: bool
    is_validated: bool
    last_validated_at: Optional[datetime] = None
    settings: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ProviderUpdate(BaseModel):
    display_name: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    is_enabled: Optional[bool] = None
    settings: Optional[Dict[str, Any]] = None


class ModelEntryResponse(BaseModel):
    id: UUID
    provider_id: UUID
    model_id_str: str
    display_name: str
    context_window: Optional[int] = None
    supports_tools: bool = False
    supports_streaming: bool = True
    supports_structured_output: bool = False
    coding_score: Optional[int | float] = None
    reasoning_score: Optional[int | float] = None
    speed_tier: Optional[str] = None
    is_available: bool = True
    cost_per_1k_input: Optional[float] = None
    cost_per_1k_output: Optional[float] = None

    model_config = {"from_attributes": True}


class ProviderTestResult(BaseModel):
    success: bool
    latency_ms: Optional[float] = None
    models_found: Optional[int] = None
    error: Optional[str] = None
