"""WebSocket client with auto-reconnect and heartbeat."""
import asyncio
import json
import logging
from typing import Optional, Callable, Awaitable
from datetime import datetime, timezone

try:
    import websockets
    from websockets.client import connect as ws_connect
except ImportError:
    websockets = None
    ws_connect = None

logger = logging.getLogger(__name__)


class WebSocketClient:
    """WebSocket client for connecting to the FORGE AI cloud backend."""

    def __init__(
        self,
        server_url: str,
        device_id: str,
        auth_token: str,
        on_message: Callable[[dict], Awaitable[None]],
        heartbeat_interval: int = 30,
        max_reconnect_delay: int = 60,
    ):
        self.server_url = server_url
        self.device_id = device_id
        self.auth_token = auth_token
        self.on_message = on_message
        self.heartbeat_interval = heartbeat_interval
        self.max_reconnect_delay = max_reconnect_delay

        self._ws = None
        self._connected = False
        self._reconnect_delay = 1
        self._should_run = True

    @property
    def is_connected(self) -> bool:
        return self._connected

    async def connect(self):
        """Connect to the server with auto-reconnect."""
        if not ws_connect:
            logger.error("websockets package is not available.")
            return

        while self._should_run:
            try:
                logger.info(f"Connecting to {self.server_url}...")
                async with ws_connect(self.server_url) as ws:
                    self._ws = ws
                    self._connected = True
                    self._reconnect_delay = 1

                    # Send authentication
                    await ws.send(json.dumps({
                        "type": "auth",
                        "device_id": self.device_id,
                        "auth_token": self.auth_token,
                    }))

                    # Wait for auth response
                    raw_resp = await ws.recv()
                    response = json.loads(raw_resp)
                    if response.get("type") == "auth_error":
                        logger.error(f"Authentication failed: {response.get('message')}")
                        self._should_run = False
                        return

                    logger.info("Connected and authenticated.")

                    # Start heartbeat and message loop
                    heartbeat_task = asyncio.create_task(self._heartbeat_loop())
                    try:
                        async for raw_message in ws:
                            try:
                                message = json.loads(raw_message)
                                await self.on_message(message)
                            except json.JSONDecodeError:
                                logger.error(f"Invalid JSON received: {str(raw_message)[:100]}")
                            except Exception as e:
                                logger.error(f"Error handling message: {e}")
                    finally:
                        heartbeat_task.cancel()

            except Exception as e:
                self._connected = False
                self._ws = None

                if not self._should_run:
                    break

                logger.warning(f"Connection lost: {e}. Reconnecting in {self._reconnect_delay}s...")
                await asyncio.sleep(self._reconnect_delay)
                self._reconnect_delay = min(self._reconnect_delay * 2, self.max_reconnect_delay)

    async def _heartbeat_loop(self):
        """Send periodic heartbeats."""
        while True:
            try:
                await asyncio.sleep(self.heartbeat_interval)
                await self.send({
                    "type": "heartbeat",
                    "device_id": self.device_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")

    async def send(self, message: dict):
        """Send a message to the server."""
        if self._ws and self._connected:
            try:
                await self._ws.send(json.dumps(message, default=str))
            except Exception as e:
                logger.error(f"Send error: {e}")
                self._connected = False

    async def disconnect(self):
        """Gracefully disconnect."""
        self._should_run = False
        self._connected = False
        if self._ws:
            try:
                await self._ws.close()
            except Exception:
                pass
            self._ws = None
