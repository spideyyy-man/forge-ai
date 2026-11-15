"""Agent Task execution state model."""

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from sqlalchemy import DateTime, Enum, ForeignKey, Integer, JSON, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.conversation import Conversation
    from app.models.project import Project
    from app.models.user import User


class AgentTaskStatus(str, enum.Enum):
    """Lifecycle status of an agent execution task."""
    PENDING = "PENDING"
    PLANNING = "PLANNING"
    EXECUTING = "EXECUTING"
    PAUSED = "PAUSED"
    VERIFYING = "VERIFYING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class TaskComplexity(str, enum.Enum):
    """Estimated difficulty category for resource allocation."""
    SIMPLE = "SIMPLE"
    MODERATE = "MODERATE"
    COMPLEX = "COMPLEX"
    CRITICAL = "CRITICAL"


class AgentTask(BaseModel):
    """Autonomous agent task orchestration model."""

    __tablename__ = "agent_tasks"

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    status: Mapped[AgentTaskStatus] = mapped_column(
        Enum(AgentTaskStatus, native_enum=False),
        default=AgentTaskStatus.PENDING,
        nullable=False,
        index=True,
    )
    complexity: Mapped[TaskComplexity] = mapped_column(
        Enum(TaskComplexity, native_enum=False),
        default=TaskComplexity.MODERATE,
        nullable=False,
    )
    priority: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
    )
    model_used: Mapped[Optional[str]] = mapped_column(
        String(128),
        nullable=True,
    )
    agent_type: Mapped[str] = mapped_column(
        String(64),
        default="general",
        nullable=False,
    )
    plan: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
    )
    completed_steps: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )
    modified_files: Mapped[List[str]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )
    commands_executed: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )
    verification_results: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
    )
    token_usage: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )
    error_info: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    conversation: Mapped["Conversation"] = relationship(
        "Conversation",
        back_populates="tasks",
    )
    project: Mapped["Project"] = relationship(
        "Project",
        back_populates="tasks",
    )
    user: Mapped["User"] = relationship(
        "User",
        back_populates="tasks",
    )
