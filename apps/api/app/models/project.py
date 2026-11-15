"""Project model representing a software repository managed by FORGE AI."""

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from sqlalchemy import DateTime, Enum, ForeignKey, JSON, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.conversation import Conversation
    from app.models.task import AgentTask
    from app.models.user import User
    from app.models.workspace import Workspace


class PrivacyMode(str, enum.Enum):
    """Data sharing and execution boundary for a project."""
    CLOUD_ASSISTED = "CLOUD_ASSISTED"
    LOCAL_ONLY = "LOCAL_ONLY"
    CONFIGURABLE = "CONFIGURABLE"


class ProjectStatus(str, enum.Enum):
    """Lifecycle status of a project."""
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"
    INDEXING = "INDEXING"


class Project(BaseModel):
    """A managed software repository on a user's workspace."""

    __tablename__ = "projects"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
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
        index=True,
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    root_path: Mapped[str] = mapped_column(
        String(1024),
        nullable=False,
    )
    detected_languages: Mapped[List[str]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )
    detected_frameworks: Mapped[List[str]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )
    settings: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )
    privacy_mode: Mapped[PrivacyMode] = mapped_column(
        Enum(PrivacyMode, native_enum=False),
        default=PrivacyMode.CLOUD_ASSISTED,
        nullable=False,
    )
    status: Mapped[ProjectStatus] = mapped_column(
        Enum(ProjectStatus, native_enum=False),
        default=ProjectStatus.ACTIVE,
        nullable=False,
        index=True,
    )
    last_indexed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    workspace: Mapped["Workspace"] = relationship(
        "Workspace",
        back_populates="projects",
    )
    user: Mapped["User"] = relationship(
        "User",
        back_populates="projects",
    )
    conversations: Mapped[List["Conversation"]] = relationship(
        "Conversation",
        back_populates="project",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    tasks: Mapped[List["AgentTask"]] = relationship(
        "AgentTask",
        back_populates="project",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
