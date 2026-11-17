"""Persistence for agent runs: lifecycle status + activity-event stream.

Powers live status and refresh replay. Every function is best-effort and never raises
into the running task — persistence must not be able to break a run. One row per
conversation, updated in place.
"""
import logging
import uuid as _uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.run import AgentRun, AgentRunStatus

logger = logging.getLogger(__name__)

# Cap the stream so a runaway loop can't bloat a single row unbounded.
MAX_EVENTS = 500


def _coerce(value) -> Optional[_uuid.UUID]:
    try:
        return _uuid.UUID(str(value))
    except (ValueError, TypeError):
        return None


def slim_event(event: Dict[str, Any]) -> Dict[str, Any]:
    """Keep only replay-relevant fields; drop large tool arguments."""
    out: Dict[str, Any] = {"type": event.get("event_type") or event.get("type")}
    if "tool" in event:
        out["tool"] = event["tool"]
    if "ok" in event:
        out["ok"] = event["ok"]
    args = event.get("arguments")
    if isinstance(args, dict):
        out["target"] = (
            args.get("path") or args.get("command") or args.get("query")
            or args.get("project_path") or args.get("repo_path") or ""
        )
    return out


async def start_run(conversation_id, user_id, description: str = "") -> None:
    """Create or reset the run record for a conversation to RUNNING."""
    cid, uid = _coerce(conversation_id), _coerce(user_id)
    if cid is None or uid is None:
        return
    try:
        async with AsyncSessionLocal() as db:
            row = (await db.execute(select(AgentRun).where(AgentRun.conversation_id == cid))).scalar_one_or_none()
            if row is None:
                row = AgentRun(conversation_id=cid, user_id=uid)
                db.add(row)
            row.status = AgentRunStatus.RUNNING
            row.description = (description or "")[:4000]
            row.events = []
            row.modified_files = []
            row.executed_commands = []
            row.verification_passed = None
            row.error = None
            row.final_text = None
            row.started_at = datetime.now(timezone.utc)
            row.completed_at = None
            await db.commit()
    except Exception as e:  # pragma: no cover - persistence is non-critical
        logger.warning("start_run failed for %s: %s", conversation_id, e)


async def append_event(conversation_id, event: Dict[str, Any]) -> None:
    """Append one slimmed activity event to the run's ordered stream."""
    cid = _coerce(conversation_id)
    if cid is None:
        return
    try:
        async with AsyncSessionLocal() as db:
            row = (await db.execute(select(AgentRun).where(AgentRun.conversation_id == cid))).scalar_one_or_none()
            if row is None:
                return
            events = list(row.events or [])
            if len(events) >= MAX_EVENTS:
                return
            events.append({"seq": len(events), **slim_event(event)})
            row.events = events
            await db.commit()
    except Exception as e:  # pragma: no cover
        logger.warning("append_event failed for %s: %s", conversation_id, e)


async def finish_run(
    conversation_id,
    *,
    status: Union[str, AgentRunStatus],
    final_text: Optional[str] = None,
    modified_files: Optional[List[str]] = None,
    executed_commands: Optional[List[Dict[str, Any]]] = None,
    verification_passed: Optional[bool] = None,
    error: Optional[str] = None,
) -> None:
    """Mark the run finished (COMPLETED/CANCELLED/FAILED) and store the summary."""
    cid = _coerce(conversation_id)
    if cid is None:
        return
    try:
        async with AsyncSessionLocal() as db:
            row = (await db.execute(select(AgentRun).where(AgentRun.conversation_id == cid))).scalar_one_or_none()
            if row is None:
                return
            row.status = status if isinstance(status, AgentRunStatus) else AgentRunStatus(status)
            if final_text is not None:
                row.final_text = final_text[:8000]
            if modified_files is not None:
                row.modified_files = modified_files
            if executed_commands is not None:
                row.executed_commands = executed_commands
            if verification_passed is not None:
                row.verification_passed = verification_passed
            if error is not None:
                row.error = error[:4000]
            row.completed_at = datetime.now(timezone.utc)
            await db.commit()
    except Exception as e:  # pragma: no cover
        logger.warning("finish_run failed for %s: %s", conversation_id, e)


async def get_run(conversation_id) -> Optional[AgentRun]:
    """Load the run record for a conversation (or None)."""
    cid = _coerce(conversation_id)
    if cid is None:
        return None
    async with AsyncSessionLocal() as db:
        return (await db.execute(select(AgentRun).where(AgentRun.conversation_id == cid))).scalar_one_or_none()
