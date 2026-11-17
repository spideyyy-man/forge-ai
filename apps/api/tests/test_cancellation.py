"""Tests for cooperative cancellation and disconnect fail-fast cleanup."""
import asyncio
import json

import pytest

from app.agents.engineering_loop import run_engineering_loop
from app.websocket.manager import ConnectionManager


class FakeMessage:
    def __init__(self, content=None, tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls


class FakeToolCall:
    def __init__(self, call_id, name, arguments):
        self.id = call_id
        self.type = "function"
        self.function = type("F", (), {"name": name, "arguments": arguments})()


async def _noop_emit(event):
    pass


# --- loop-level cancellation -------------------------------------------------

async def test_cancel_before_first_step_runs_no_model():
    async def complete(messages, tools):
        raise AssertionError("model should not be called once cancelled")

    result = await run_engineering_loop(
        description="x", repo_context="", workspace_path="/ws",
        complete=complete, exec_tool=lambda n, a: None,
        request_approval=lambda p: None, emit=_noop_emit,
        device_connected=True, should_cancel=lambda: True,
    )
    assert result["cancelled"] is True
    assert result["steps"] == 0
    assert result["modified_files"] == []


async def test_cancel_between_tool_calls_skips_tool():
    polls = {"n": 0}

    def should_cancel():
        # False at the top-of-step check, True at the pre-tool check.
        polls["n"] += 1
        return polls["n"] >= 2

    async def complete(messages, tools):
        return {"success": True, "message": FakeMessage(
            tool_calls=[FakeToolCall("c1", "read_file", json.dumps({"path": "/ws/a.py"}))]
        )}

    async def exec_tool(name, args):
        raise AssertionError("tool should not run after cancel")

    result = await run_engineering_loop(
        description="x", repo_context="", workspace_path="/ws",
        complete=complete, exec_tool=exec_tool,
        request_approval=lambda p: None, emit=_noop_emit,
        device_connected=True, should_cancel=should_cancel,
    )
    assert result["cancelled"] is True
    assert result["steps"] == 1


# --- manager cancel registry -------------------------------------------------

def test_cancel_registry_lifecycle():
    cm = ConnectionManager()
    assert cm.request_cancel("conv-x") is False      # not registered yet
    ev = cm.get_cancel_event("conv-x")
    assert ev.is_set() is False
    assert cm.is_cancelled("conv-x") is False
    assert cm.request_cancel("conv-x") is True        # registered -> matched
    assert cm.is_cancelled("conv-x") is True
    cm.clear_cancel("conv-x")
    assert cm.is_cancelled("conv-x") is False


# --- disconnect fail-fast ----------------------------------------------------

async def test_disconnect_device_fails_pending_tool_future():
    cm = ConnectionManager()
    fut = asyncio.get_running_loop().create_future()
    cm.pending_requests["corr-1"] = {"future": fut, "device_id": "dev-1", "user_id": "u1"}
    cm.disconnect_device("dev-1")
    assert fut.done()
    with pytest.raises(ConnectionError):
        fut.result()


async def test_disconnect_user_rejects_pending_approval():
    cm = ConnectionManager()
    fut = asyncio.get_running_loop().create_future()
    cm.pending_approvals["appr-1"] = {"future": fut, "user_id": "u1"}
    cm.disconnect_user("u1")
    assert fut.done()
    assert fut.result() is False  # fail-closed reject
