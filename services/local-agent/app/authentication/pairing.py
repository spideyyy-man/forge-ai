"""Device pairing flow."""
import json
import platform
import getpass
import logging
import urllib.error
import urllib.request
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


def derive_api_base(server_url: Optional[str], override: Optional[str] = None) -> str:
    """Work out the REST API base URL from the WebSocket server URL.

    The agent talks WebSocket to e.g. ws://localhost:8000/ws/agent; the pairing
    REST endpoint lives at http://localhost:8000/api. An explicit override wins.
    """
    if override:
        return override.rstrip("/")
    base = server_url or "ws://localhost:8000/ws/agent"
    base = base.replace("wss://", "https://").replace("ws://", "http://")
    # Strip the websocket path and append the REST prefix.
    for suffix in ("/ws/agent", "/ws"):
        if base.endswith(suffix):
            base = base[: -len(suffix)]
            break
    return base.rstrip("/") + "/api"


def pair_with_backend(api_base: str, device_id: str, pairing_code: str, timeout: int = 15) -> Dict[str, str]:
    """Exchange a pairing code for a device auth token via the cloud backend.

    Args:
        api_base: REST API base, e.g. http://localhost:8000/api
        device_id: Device ID shown in the web pairing dialog.
        pairing_code: 6-character code shown in the web pairing dialog.

    Returns:
        {"device_id": ..., "auth_token": ...}

    Raises:
        RuntimeError: with a human-readable message on any failure.
    """
    url = api_base.rstrip("/") + "/devices/pair"
    payload = json.dumps({"pairing_code": pairing_code, "device_id": device_id}).encode("utf-8")
    req = urllib.request.Request(
        url, data=payload, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            detail = json.loads(exc.read().decode("utf-8")).get("detail", "")
        except Exception:
            pass
        raise RuntimeError(f"Pairing rejected by server ({exc.code}): {detail or exc.reason}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"Could not reach the backend at {url}. Is it running? ({exc.reason})"
        ) from exc

    token = data.get("auth_token")
    if not token:
        raise RuntimeError(f"Backend did not return an auth token: {data}")
    return {"device_id": str(data.get("device_id", device_id)), "auth_token": token}


def get_device_info() -> Dict[str, Any]:
    """Collect device information for registration."""
    return {
        "hostname": platform.node(),
        "os_type": platform.system(),
        "os_version": platform.version(),
        "os_release": platform.release(),
        "architecture": platform.machine(),
        "username": getpass.getuser(),
        "python_version": platform.python_version(),
    }


class DeviceInfo(BaseModel):
    """Device details for pairing and registration."""
    hostname: str = Field(default_factory=platform.node)
    os_type: str = Field(default_factory=platform.system)
    os_version: str = Field(default_factory=platform.version)
    os_release: str = Field(default_factory=platform.release)
    architecture: str = Field(default_factory=platform.machine)
    username: str = Field(default_factory=getpass.getuser)
    python_version: str = Field(default_factory=platform.python_version)


class PairingManager:
    """Manages pairing session and initial token registration with cloud backend."""

    def __init__(self, server_url: str, device_id: Optional[str] = None):
        self.server_url = server_url
        self.device_id = device_id
        self.device_info = get_device_info()

    def get_info(self) -> Dict[str, Any]:
        """Return gathered device info."""
        return self.device_info
