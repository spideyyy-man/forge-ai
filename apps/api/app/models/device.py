"""Device model for local development machines."""

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from sqlalchemy import DateTime, Enum, ForeignKey, JSON, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.workspace import Workspace


class DeviceType(str, enum.Enum):
    """Supported client OS platforms."""
    WINDOWS = "WINDOWS"
    MACOS = "MACOS"
    LINUX = "LINUX"


class DeviceStatus(str, enum.Enum):
    """Device registration and connectivity state."""
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    DISCONNECTED = "DISCONNECTED"
    REVOKED = "REVOKED"


class Device(BaseModel):
    """Registered developer device executing local actions."""

    __tablename__ = "devices"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )
    device_type: Mapped[DeviceType] = mapped_column(
        Enum(DeviceType, native_enum=False),
        nullable=False,
        default=DeviceType.WINDOWS,
    )
    status: Mapped[DeviceStatus] = mapped_column(
        Enum(DeviceStatus, native_enum=False),
        nullable=False,
        default=DeviceStatus.PENDING,
        index=True,
    )
    pairing_code: Mapped[Optional[str]] = mapped_column(
        String(32),
        unique=True,
        index=True,
        nullable=True,
    )
    auth_token_hash: Mapped[Optional[str]] = mapped_column(
        String(128),
        nullable=True,
    )
    pairing_code_expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    agent_version: Mapped[Optional[str]] = mapped_column(
        String(32),
        nullable=True,
    )
    os_info: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        default=dict,
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="devices",
    )
    workspaces: Mapped[List["Workspace"]] = relationship(
        "Workspace",
        back_populates="device",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
