"""Persisted agent run record.

One row per conversation (updated in place). Holds the run lifecycle status, the
ordered activity-event stream the UI replays after a refresh, and the final result
summary. Separate from AgentTask (which requires a project) so a run can be persisted
even when no project exists.
"""
import enum
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, JSON, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class AgentRunStatus(str, enum.Enum):
    """High-level state used by the UI to decide running vs finished."""
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"


class AgentRun(BaseModel):
    """Live + replayable record of one agent run, keyed by conversation."""

    __tablename__ = "agent_runs"

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), index=True, nullable=False)
    status: Mapped[AgentRunStatus] = mapped_column(
        Enum(AgentRunStatus, native_enum=False),
        default=AgentRunStatus.RUNNING,
        nullable=False,
        index=True,
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Ordered activity stream ({seq, type, tool?, ok?, target?}) for refresh replay.
    events: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    modified_files: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    executed_commands: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    verification_passed: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    final_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
