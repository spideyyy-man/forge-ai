"""WebSocket message handlers."""
import logging
from typing import Optional

from app.websocket.manager import connection_manager

logger = logging.getLogger(__name__)


async def handle_websocket_message(
    data: dict,
    user_id: Optional[str] = None,
    device_id: Optional[str] = None,
):
    """Route incoming WebSocket messages to appropriate handlers."""
    msg_type = data.get("type", "unknown")

    if device_id:
        await handle_device_message(data, device_id)
    elif user_id:
        await handle_user_message(data, user_id)
    else:
        logger.warning(f"Unroutable WebSocket message: {msg_type}")


async def handle_device_message(data: dict, device_id: str):
    """Handle messages from local workspace agents."""
    msg_type = data.get("type")

    if msg_type == "heartbeat":
        logger.debug(f"Heartbeat from device {device_id}")

    elif msg_type == "tool_response":
        correlation_id = data.get("correlation_id")
        if correlation_id and correlation_id in connection_manager.pending_requests:
            request_info = connection_manager.pending_requests.get(correlation_id)
            if request_info:
                # If an async future is waiting for this response, resolve it
                future = request_info.get("future")
                if future and not future.done():
                    future.set_result(data.get("result") if data.get("success", True) else {"error": data.get("error")})

                # Also forward to user if connected
                user_id = request_info.get("user_id")
                if user_id:
                    await connection_manager.send_to_user(user_id, {
                        "type": "tool_result",
                        "correlation_id": correlation_id,
                        "result": data.get("result"),
                        "success": data.get("success", True),
                        "error": data.get("error"),
                    })

    elif msg_type == "execution_stream":
        # Forward streaming output to user
        user_id = data.get("user_id")
        if user_id:
            await connection_manager.send_to_user(user_id, {
                "type": "execution_stream",
                "content": data.get("content"),
                "stream_type": data.get("stream_type", "stdout"),
            })

    elif msg_type == "file_changed":
        logger.debug(f"File changed on device {device_id}: {data.get('path')}")

    else:
        logger.warning(f"Unknown device message type: {msg_type}")


async def handle_user_message(data: dict, user_id: str):
    """Handle messages from frontend clients."""
    msg_type = data.get("type")

    if msg_type == "ping":
        await connection_manager.send_to_user(user_id, {"type": "pong"})

    elif msg_type == "subscribe":
        logger.info(f"User {user_id} subscribing to: {data.get('channel')}")

    elif msg_type == "approval_decision":
        approval_id = data.get("approval_id")
        approved = bool(data.get("approved"))
        matched = connection_manager.resolve_approval(approval_id, approved)
        if not matched:
            logger.info(f"Approval decision for unknown/expired id {approval_id} from user {user_id}")

    else:
        logger.warning(f"Unknown user message type: {msg_type}")
