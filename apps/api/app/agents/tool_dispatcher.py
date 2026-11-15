"""Dispatcher to send tool requests to local Windows workspace agent over WebSocket."""
import asyncio
import logging
import uuid
from typing import Dict, Any, Optional
from app.websocket.manager import connection_manager

logger = logging.getLogger(__name__)


async def execute_remote_tool(
    device_id: str,
    tool_name: str,
    arguments: Dict[str, Any],
    user_id: Optional[str] = None,
    timeout_seconds: int = 120,
) -> Dict[str, Any]:
    """Dispatch a tool request to the authenticated local agent and await response."""
    if not connection_manager.is_device_connected(device_id):
        raise ConnectionError(f"Local agent device {device_id} is not connected via WebSocket")

    correlation_id = str(uuid.uuid4())
    loop = asyncio.get_running_loop()
    future = loop.create_future()

    # Store future in pending requests mapped by correlation_id
    connection_manager.pending_requests[correlation_id] = {
        "future": future,
        "tool_name": tool_name,
        "device_id": device_id,
        "user_id": user_id,
    }

    payload = {
        "type": "tool_request",
        "id": correlation_id,
        "tool_name": tool_name,
        "arguments": arguments,
        "timeout": timeout_seconds,
    }

    logger.info(f"[ToolDispatcher] Sending {tool_name} to device {device_id} (corr_id={correlation_id})")
    await connection_manager.send_to_device(device_id, payload)

    try:
        response = await asyncio.wait_for(future, timeout=timeout_seconds)
        return response
    except asyncio.TimeoutError:
        logger.error(f"[ToolDispatcher] Tool {tool_name} timed out after {timeout_seconds}s")
        raise TimeoutError(f"Execution of tool {tool_name} on device {device_id} timed out")
    finally:
        connection_manager.pending_requests.pop(correlation_id, None)
