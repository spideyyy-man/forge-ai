"""WebSocket connection manager."""
import asyncio
import uuid
from fastapi import WebSocket
from typing import Dict, Optional, Any
import logging
import json
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for users and devices."""

    def __init__(self):
        self.user_connections: Dict[str, WebSocket] = {}
        self.device_connections: Dict[str, WebSocket] = {}
        self.pending_requests: Dict[str, dict] = {}
        # approval_id -> {"future": Future} awaiting a user approve/reject decision.
        self.pending_approvals: Dict[str, dict] = {}
        # conversation_id -> Event; set when the user asks to stop that run.
        self.cancel_events: Dict[str, "asyncio.Event"] = {}

    async def connect_user(self, websocket: WebSocket, user_id: str):
        """Accept and register a user WebSocket connection."""
        await websocket.accept()
        self.user_connections[user_id] = websocket
        logger.info(f"User {user_id} connected via WebSocket")

    async def connect_device(self, websocket: WebSocket, device_id: str):
        """Register a device WebSocket connection (already accepted)."""
        self.device_connections[device_id] = websocket
        logger.info(f"Device {device_id} connected via WebSocket")
        await self._persist_device_presence(device_id, connected=True)

    def disconnect_user(self, user_id: str):
        """Remove a user connection and fail-close any approvals they were awaiting."""
        self.user_connections.pop(user_id, None)
        self._fail_user_approvals(user_id)
        logger.info(f"User {user_id} disconnected")

    def disconnect_device(self, device_id: str):
        """Remove a device connection (socket only; see mark_device_disconnected to persist).

        Also fails any in-flight tool-call futures for this device so callers fail fast
        instead of blocking the full request timeout."""
        self.device_connections.pop(device_id, None)
        self._fail_device_requests(device_id)
        logger.info(f"Device {device_id} disconnected")

    def _fail_user_approvals(self, user_id: str):
        """Reject (fail-closed) any pending approvals the departing user owned."""
        for approval_id, info in list(self.pending_approvals.items()):
            if info.get("user_id") != user_id:
                continue
            future = info.get("future")
            if future and not future.done():
                future.set_result(False)

    def _fail_device_requests(self, device_id: str):
        """Fail any in-flight tool calls awaiting the departing device."""
        for correlation_id, info in list(self.pending_requests.items()):
            if info.get("device_id") != device_id:
                continue
            future = info.get("future")
            if future and not future.done():
                future.set_exception(ConnectionError(f"Local agent {device_id} disconnected"))

    # --- Run cancellation (cooperative) ---------------------------------------
    def get_cancel_event(self, conversation_id: str) -> "asyncio.Event":
        """Return (creating if needed) the cancel Event for a conversation's run."""
        event = self.cancel_events.get(conversation_id)
        if event is None:
            event = asyncio.Event()
            self.cancel_events[conversation_id] = event
        return event

    def request_cancel(self, conversation_id: str) -> bool:
        """Signal a running task to stop. Returns True if a run was registered to cancel."""
        event = self.cancel_events.get(conversation_id)
        if event is None:
            return False
        event.set()
        return True

    def is_cancelled(self, conversation_id: str) -> bool:
        event = self.cancel_events.get(conversation_id)
        return bool(event and event.is_set())

    def clear_cancel(self, conversation_id: str):
        self.cancel_events.pop(conversation_id, None)

    async def mark_device_disconnected(self, device_id: str):
        """Remove the socket and persist DISCONNECTED + last_seen in the DB."""
        self.disconnect_device(device_id)
        await self._persist_device_presence(device_id, connected=False)

    async def touch_device(self, device_id: str):
        """Record a heartbeat: refresh last_seen_at (and reaffirm ACTIVE)."""
        await self._persist_device_presence(device_id, connected=True)

    async def _persist_device_presence(self, device_id: str, *, connected: bool):
        """Write live presence to the devices table. Best-effort: never raises into the
        WebSocket loop. `status` tracks connectivity; REVOKED is never overridden."""
        # Imported lazily to avoid an import cycle (database/models import late).
        import uuid as _uuid
        from datetime import datetime, timezone
        from sqlalchemy import select
        from app.core.database import AsyncSessionLocal
        from app.models.device import Device, DeviceStatus
        try:
            dev_uuid = _uuid.UUID(str(device_id))
        except (ValueError, TypeError):
            return
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(select(Device).where(Device.id == dev_uuid))
                device = result.scalar_one_or_none()
                if device is None:
                    return
                if device.status != DeviceStatus.REVOKED:
                    device.status = DeviceStatus.ACTIVE if connected else DeviceStatus.DISCONNECTED
                device.last_seen_at = datetime.now(timezone.utc)
                await db.commit()
        except Exception as e:  # pragma: no cover - defensive; presence is non-critical
            logger.warning("Could not persist presence for device %s: %s", device_id, e)

    async def send_to_user(self, user_id: str, message: dict):
        """Send a message to a specific user."""
        ws = self.user_connections.get(user_id)
        if ws:
            try:
                await ws.send_json(message)
            except Exception as e:
                logger.error(f"Error sending to user {user_id}: {e}")
                self.disconnect_user(user_id)

    async def send_to_device(self, device_id: str, message: dict):
        """Send a message to a specific device."""
        ws = self.device_connections.get(device_id)
        if ws:
            try:
                await ws.send_json(message)
            except Exception as e:
                logger.error(f"Error sending to device {device_id}: {e}")
                self.disconnect_device(device_id)

    def is_device_connected(self, device_id: str) -> bool:
        """Check if a device is connected."""
        return device_id in self.device_connections

    def get_connected_devices(self) -> list[str]:
        """Get list of connected device IDs."""
        return list(self.device_connections.keys())

    async def broadcast_to_user_devices(self, user_id: str, message: dict):
        """Broadcast a message to all devices of a user."""
        # Broadcast to devices mapped to user if tracked
        pass

    async def request_user_approval(
        self,
        user_id: str,
        conversation_id: str,
        proposal: Dict[str, Any],
        timeout_seconds: int = 300,
    ) -> bool:
        """Send an approval request to the user and await their decision.

        Returns True if approved, False if rejected, the user is not connected, or the
        request times out. Fail-closed: a missing/late decision never silently applies a
        change. The frontend resolves this by sending an ``approval_decision`` message.
        """
        if user_id not in self.user_connections:
            logger.info("Approval requested but user %s not connected; auto-rejecting.", user_id)
            return False

        approval_id = str(uuid.uuid4())
        loop = asyncio.get_running_loop()
        future: asyncio.Future = loop.create_future()
        self.pending_approvals[approval_id] = {"future": future, "user_id": user_id}

        await self.send_to_user(user_id, {
            "type": "approval_request",
            "approval_id": approval_id,
            "conversation_id": conversation_id,
            "proposal": proposal,
        })

        try:
            return bool(await asyncio.wait_for(future, timeout=timeout_seconds))
        except asyncio.TimeoutError:
            logger.info("Approval %s timed out; auto-rejecting.", approval_id)
            return False
        finally:
            self.pending_approvals.pop(approval_id, None)

    def resolve_approval(self, approval_id: str, approved: bool) -> bool:
        """Resolve a pending approval future from a user's decision. Returns True if matched."""
        info = self.pending_approvals.get(approval_id)
        if not info:
            return False
        future = info.get("future")
        if future and not future.done():
            future.set_result(bool(approved))
        return True


# Global singleton
connection_manager = ConnectionManager()
