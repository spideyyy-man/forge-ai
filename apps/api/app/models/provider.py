"""Provider and model catalog models."""

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, JSON, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.user import User


class ProviderType(str, enum.Enum):
    """Supported model provider backends."""
    OPENAI = "OPENAI"
    ANTHROPIC = "ANTHROPIC"
    GOOGLE = "GOOGLE"
    GROQ = "GROQ"
    OLLAMA = "OLLAMA"
    OPENROUTER = "OPENROUTER"
    MISTRAL = "MISTRAL"
    DEEPSEEK = "DEEPSEEK"
    NVIDIA = "NVIDIA"
    CEREBRAS = "CEREBRAS"
    GITHUB = "GITHUB"
    SAMBANOVA = "SAMBANOVA"
    CUSTOM = "CUSTOM"


class SpeedTier(str, enum.Enum):
    """Latency and throughput classification."""
    FAST = "FAST"
    BALANCED = "BALANCED"
    POWERFUL = "POWERFUL"


class ProviderAccount(BaseModel):
    """User-configured LLM provider credentials and options."""

    __tablename__ = "provider_accounts"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    provider_type: Mapped[ProviderType] = mapped_column(
        Enum(ProviderType, native_enum=False),
        nullable=False,
    )
    display_name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )
    encrypted_api_key: Mapped[Optional[str]] = mapped_column(
        String(1024),
        nullable=True,
    )
    base_url: Mapped[Optional[str]] = mapped_column(
        String(512),
        nullable=True,
    )
    is_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    is_validated: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    last_validated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    settings: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="provider_accounts",
    )
    models: Mapped[List["ModelEntry"]] = relationship(
        "ModelEntry",
        back_populates="provider",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class ModelEntry(BaseModel):
    """Available model capabilities catalog under a provider."""

    __tablename__ = "model_entries"

    provider_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("provider_accounts.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    model_id_str: Mapped[str] = mapped_column(
        String(128),
        index=True,
        nullable=False,
    )
    display_name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )
    context_window: Mapped[int] = mapped_column(
        Integer,
        default=128000,
        nullable=False,
    )
    supports_tools: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    supports_streaming: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    supports_structured_output: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    coding_score: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )
    reasoning_score: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )
    speed_tier: Mapped[SpeedTier] = mapped_column(
        Enum(SpeedTier, native_enum=False),
        default=SpeedTier.BALANCED,
        nullable=False,
    )
    is_available: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    cost_per_1k_input: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )
    cost_per_1k_output: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )

    # Relationships
    provider: Mapped["ProviderAccount"] = relationship(
        "ProviderAccount",
        back_populates="models",
    )
