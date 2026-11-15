"""WebSocket connection manager."""
from fastapi import WebSocket
from typing import Dict, Optional
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

    async def connect_user(self, websocket: WebSocket, user_id: str):
        """Accept and register a user WebSocket connection."""
        await websocket.accept()
        self.user_connections[user_id] = websocket
        logger.info(f"User {user_id} connected via WebSocket")

    async def connect_device(self, websocket: WebSocket, device_id: str):
        """Register a device WebSocket connection (already accepted)."""
        self.device_connections[device_id] = websocket
        logger.info(f"Device {device_id} connected via WebSocket")

    def disconnect_user(self, user_id: str):
        """Remove a user connection."""
        self.user_connections.pop(user_id, None)
        logger.info(f"User {user_id} disconnected")

    def disconnect_device(self, device_id: str):
        """Remove a device connection."""
        self.device_connections.pop(device_id, None)
        logger.info(f"Device {device_id} disconnected")

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


# Global singleton
connection_manager = ConnectionManager()
