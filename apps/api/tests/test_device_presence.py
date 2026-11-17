"""Tests for live device presence (is_connected overlay + socket lifecycle).

These stay DB-free: _persist_device_presence is best-effort and safely no-ops when the
device id is not a real UUID, so connect/disconnect can be exercised without a database.
"""
import uuid
from datetime import datetime, timezone

import app.api.devices as devices_mod
from app.websocket.manager import ConnectionManager


class FakeWS:
    async def send_json(self, message):
        pass


async def test_connect_and_disconnect_track_is_connected():
    cm = ConnectionManager()
    assert cm.is_device_connected("not-a-uuid") is False
    await cm.connect_device(FakeWS(), "not-a-uuid")  # presence persist no-ops on bad uuid
    assert cm.is_device_connected("not-a-uuid") is True
    await cm.mark_device_disconnected("not-a-uuid")
    assert cm.is_device_connected("not-a-uuid") is False


class _Dev:
    """Minimal object DeviceResponse can validate from attributes."""
    def __init__(self, status="ACTIVE"):
        self.id = uuid.uuid4()
        self.user_id = uuid.uuid4()
        self.name = "Test"
        self.device_type = "WINDOWS"
        self.status = status
        self.pairing_code = None
        self.last_seen_at = None
        self.agent_version = None
        self.os_info = None
        self.created_at = datetime.now(timezone.utc)
        self.updated_at = None


def test_with_presence_false_when_no_socket():
    dev = _Dev()
    devices_mod.connection_manager.device_connections.pop(str(dev.id), None)
    resp = devices_mod._with_presence(dev)
    assert resp.is_connected is False
    assert resp.status == "ACTIVE"  # persisted lifecycle is untouched


def test_with_presence_true_when_socket_open():
    dev = _Dev()
    devices_mod.connection_manager.device_connections[str(dev.id)] = FakeWS()
    try:
        resp = devices_mod._with_presence(dev)
        assert resp.is_connected is True
    finally:
        devices_mod.connection_manager.device_connections.pop(str(dev.id), None)
