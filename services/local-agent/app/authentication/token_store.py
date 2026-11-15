"""Secure machine-encrypted auth token storage."""

from __future__ import annotations

import base64
import os
import platform
import uuid
from pathlib import Path

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from app.logging_config.setup import get_logger

logger = get_logger("token_store")

# Static salt combined with machine-specific seeds for key derivation
SALT = b"forge_ai_local_agent_salt_v1_secure"


def _get_machine_fingerprint() -> bytes:
    """Generate a consistent machine-specific fingerprint string."""
    parts = [
        str(uuid.getnode()),
        platform.node(),
        platform.system(),
        platform.machine(),
    ]
    # On Windows, try reading MachineGuid from registry if accessible
    if platform.system() == "Windows":
        try:
            import winreg

            with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Microsoft\Cryptography",
            ) as key:
                guid, _ = winreg.QueryValueEx(key, "MachineGuid")
                parts.append(str(guid))
        except Exception:
            pass
    # On Linux, try /etc/machine-id
    elif os.path.exists("/etc/machine-id"):
        try:
            with open("/etc/machine-id", "r", encoding="utf-8") as f:
                parts.append(f.read().strip())
        except Exception:
            pass

    return "_".join(parts).encode("utf-8")


def _derive_fernet_key() -> bytes:
    """Derive a URL-safe base64-encoded 32-byte key from machine fingerprint."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=SALT,
        iterations=100_000,
    )
    key = kdf.derive(_get_machine_fingerprint())
    return base64.urlsafe_b64encode(key)


class TokenStore:
    """Stores and retrieves auth tokens encrypted with a machine-bound key."""

    def __init__(self, token_path: str | Path = ".forge_agent_token") -> None:
        """Initialize TokenStore with a local token storage path.

        Args:
            token_path: Relative or absolute path to store the encrypted token.
        """
        self.token_path = Path(token_path)
        self._fernet: Fernet | None = None

    def _get_fernet(self) -> Fernet:
        """Lazily initialize Fernet instance."""
        if self._fernet is None:
            key = _derive_fernet_key()
            self._fernet = Fernet(key)
        return self._fernet

    def save_token(self, token: str) -> None:
        """Encrypt and persist the authentication token.

        Args:
            token: Plain text auth token.
        """
        if not token.strip():
            self.clear_token()
            return

        fernet = self._get_fernet()
        encrypted = fernet.encrypt(token.encode("utf-8"))

        self.token_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.token_path, "wb") as f:
            f.write(encrypted)
        logger.info("Auth token securely saved and encrypted")

    def load_token(self) -> str | None:
        """Load and decrypt the stored authentication token.

        Returns:
            Decrypted plain token string or None if not found/invalid.
        """
        if not self.token_path.exists():
            return None

        try:
            with open(self.token_path, "rb") as f:
                encrypted = f.read()

            if not encrypted:
                return None

            fernet = self._get_fernet()
            decrypted = fernet.decrypt(encrypted)
            return decrypted.decode("utf-8")
        except Exception as e:
            logger.error("Failed to decrypt stored token: %s", e)
            return None

    def rotate_token(self, new_token: str) -> None:
        """Replace current token with a newly refreshed token.

        Args:
            new_token: The new token received from cloud backend.
        """
        self.save_token(new_token)
        logger.info("Auth token rotated successfully")

    def clear_token(self) -> None:
        """Delete stored authentication token file."""
        if self.token_path.exists():
            try:
                self.token_path.unlink()
                logger.info("Cleared stored auth token")
            except OSError as e:
                logger.warning("Could not delete token file: %s", e)

    def is_authenticated(self) -> bool:
        """Check if a valid decryptable token is stored."""
        token = self.load_token()
        return bool(token and token.strip())


import getpass
import hashlib
import json

STORE_DIR = Path.home() / ".forge-ai"
STORE_FILE = STORE_DIR / "credentials.enc"


def _get_machine_key() -> bytes:
    """Derive encryption key from machine-specific info."""
    machine_id = f"{platform.node()}-{getpass.getuser()}-forge-ai-local"
    key_hash = hashlib.sha256(machine_id.encode()).digest()
    return base64.urlsafe_b64encode(key_hash)


def save_token(device_id: str, auth_token: str) -> None:
    """Save auth token encrypted."""
    STORE_DIR.mkdir(parents=True, exist_ok=True)
    fernet = Fernet(_get_machine_key())
    data = json.dumps({"device_id": device_id, "auth_token": auth_token})
    encrypted = fernet.encrypt(data.encode())
    STORE_FILE.write_bytes(encrypted)
    logger.info("Credentials saved securely.")


def load_token() -> dict | None:
    """Load saved token."""
    if not STORE_FILE.exists():
        return None
    try:
        fernet = Fernet(_get_machine_key())
        encrypted = STORE_FILE.read_bytes()
        data = fernet.decrypt(encrypted)
        return json.loads(data.decode())
    except Exception as e:
        logger.error(f"Failed to load credentials: {e}")
        return None

