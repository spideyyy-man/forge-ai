"""Workspace model representing a local folder environment on a device."""

import uuid
from typing import TYPE_CHECKING, Any, Dict, List
from sqlalchemy import Boolean, ForeignKey, JSON, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.device import Device
    from app.models.project import Project
    from app.models.user import User


class Workspace(BaseModel):
    """Local device workspace containing projects and tool configurations."""

    __tablename__ = "workspaces"

    device_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("devices.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
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
    root_path: Mapped[str] = mapped_column(
        String(1024),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    settings: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )

    # Relationships
    device: Mapped["Device"] = relationship(
        "Device",
        back_populates="workspaces",
    )
    user: Mapped["User"] = relationship(
        "User",
        back_populates="workspaces",
    )
    projects: Mapped[List["Project"]] = relationship(
        "Project",
        back_populates="workspace",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
