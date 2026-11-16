"""Tests for the WebSocket approval transport (fail-closed semantics)."""
import asyncio
import pytest

from app.websocket.manager import ConnectionManager


class FakeWS:
    def __init__(self):
        self.sent = []

    async def send_json(self, message):
        self.sent.append(message)


async def test_approval_auto_rejects_when_user_not_connected():
    cm = ConnectionManager()
    approved = await cm.request_user_approval("user-1", "conv-1", {"kind": "edit"}, timeout_seconds=1)
    assert approved is False


async def test_approval_times_out_to_reject():
    cm = ConnectionManager()
    cm.user_connections["user-1"] = FakeWS()
    approved = await cm.request_user_approval("user-1", "conv-1", {"kind": "edit"}, timeout_seconds=0.2)
    assert approved is False
    assert cm.pending_approvals == {}  # cleaned up


async def test_approval_resolved_by_decision():
    cm = ConnectionManager()
    ws = FakeWS()
    cm.user_connections["user-1"] = ws

    async def decide_soon():
        await asyncio.sleep(0.05)
        approval_id = ws.sent[-1]["approval_id"]
        assert cm.resolve_approval(approval_id, True) is True

    decider = asyncio.create_task(decide_soon())
    approved = await cm.request_user_approval("user-1", "conv-1", {"kind": "command"}, timeout_seconds=2)
    await decider
    assert approved is True
    assert ws.sent[-1]["type"] == "approval_request"


def test_resolve_unknown_approval_returns_false():
    cm = ConnectionManager()
    assert cm.resolve_approval("does-not-exist", True) is False
