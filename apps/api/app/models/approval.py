"""Per-user approval policy: which agent operation classes auto-run vs. require approval."""
import uuid
from typing import Any, Dict

from sqlalchemy import ForeignKey, JSON, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class ApprovalPolicy(BaseModel):
    """One row per user. ``modes`` maps op-class -> 'auto' | 'approve'."""

    __tablename__ = "approval_policies"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    modes: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
