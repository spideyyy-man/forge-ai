"""Tests for agent-run persistence (status + event stream for refresh replay)."""
import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
import app.models  # noqa: F401 - registers AgentRun on the metadata
import app.agents.run_store as rs
from app.models.run import AgentRunStatus


@pytest_asyncio.fixture
async def mem_db(monkeypatch):
    # Shared in-memory DB (StaticPool keeps one connection so every session sees it).
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    monkeypatch.setattr(rs, "AsyncSessionLocal", async_sessionmaker(engine, expire_on_commit=False))
    yield
    await engine.dispose()


def test_slim_event_keeps_replay_fields_only():
    call = rs.slim_event({"event_type": "tool_call", "tool": "read_file",
                          "arguments": {"path": "/ws/a.py", "extra": "x" * 999}})
    assert call == {"type": "tool_call", "tool": "read_file", "target": "/ws/a.py"}
    result = rs.slim_event({"event_type": "tool_result", "tool": "apply_edit", "ok": True})
    assert result == {"type": "tool_result", "tool": "apply_edit", "ok": True}


async def test_run_lifecycle_persists_and_replays(mem_db):
    conv, user = str(uuid.uuid4()), str(uuid.uuid4())
    await rs.start_run(conv, user, "do a thing")
    run = await rs.get_run(conv)
    assert run is not None and run.status == AgentRunStatus.RUNNING and run.events == []

    await rs.append_event(conv, {"event_type": "tool_call", "tool": "read_file", "arguments": {"path": "/a"}})
    await rs.append_event(conv, {"event_type": "tool_result", "tool": "read_file", "ok": True})
    run = await rs.get_run(conv)
    assert [e["seq"] for e in run.events] == [0, 1]
    assert run.events[0]["type"] == "tool_call" and run.events[0]["target"] == "/a"
    assert run.events[1]["ok"] is True

    await rs.finish_run(conv, status="COMPLETED", final_text="done",
                        modified_files=["/a"], verification_passed=True)
    run = await rs.get_run(conv)
    assert run.status == AgentRunStatus.COMPLETED
    assert run.final_text == "done" and run.modified_files == ["/a"]
    assert run.verification_passed is True and run.completed_at is not None


async def test_start_run_resets_previous_run(mem_db):
    conv, user = str(uuid.uuid4()), str(uuid.uuid4())
    await rs.start_run(conv, user, "first")
    await rs.append_event(conv, {"event_type": "tool_call", "tool": "x"})
    await rs.start_run(conv, user, "second")  # a re-run clears the old stream
    run = await rs.get_run(conv)
    assert run.events == [] and run.description == "second"
    assert run.status == AgentRunStatus.RUNNING


async def test_bad_ids_are_ignored_without_db():
    # Coercion fails before any DB access, so these are safe no-ops.
    await rs.start_run("not-a-uuid", "also-bad", "x")
    assert await rs.get_run("not-a-uuid") is None
