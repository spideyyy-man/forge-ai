"""Security and cryptographic utilities for FORGE AI."""

import base64
import hashlib
import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Union

import bcrypt
from cryptography.fernet import Fernet, InvalidToken
from jose import JWTError, jwt

from app.core.config import settings


# Password hashing
def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a bcrypt hash."""
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except Exception:
        return False


# JWT Tokens
def create_access_token(
    subject: Union[str, Any],
    expires_delta: Optional[timedelta] = None,
    extra_claims: Optional[Dict[str, Any]] = None,
) -> str:
    """Generate a signed JWT access token."""
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode: Dict[str, Any] = {
        "sub": str(subject),
        "exp": expire,
        "iat": now,
        "type": "access",
    }
    if extra_claims:
        to_encode.update(extra_claims)

    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(
    subject: Union[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Generate a signed JWT refresh token."""
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(days=30)

    to_encode: Dict[str, Any] = {
        "sub": str(subject),
        "exp": expire,
        "iat": now,
        "type": "refresh",
    }
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return payload
    except JWTError as exc:
        raise ValueError(f"Invalid or expired token: {str(exc)}") from exc


# Symmetric Encryption for API Keys
def _get_fernet() -> Fernet:
    """Derive a 32-byte urlsafe Fernet key deterministically."""
    key = settings.ENCRYPTION_KEY
    if not key:
        derived = hashlib.sha256(settings.SECRET_KEY.encode("utf-8")).digest()
        urlsafe_key = base64.urlsafe_b64encode(derived)
    else:
        if len(key) == 44:
            urlsafe_key = key.encode("utf-8")
        else:
            derived = hashlib.sha256(key.encode("utf-8")).digest()
            urlsafe_key = base64.urlsafe_b64encode(derived)
    return Fernet(urlsafe_key)


def encrypt_api_key(api_key: str) -> str:
    """Encrypt a sensitive API key before database persistence."""
    if not api_key:
        return ""
    fernet = _get_fernet()
    encrypted = fernet.encrypt(api_key.encode("utf-8"))
    return encrypted.decode("utf-8")


def decrypt_api_key(encrypted_api_key: str) -> str:
    """Decrypt a persisted API key for provider calls."""
    if not encrypted_api_key:
        return ""
    fernet = _get_fernet()
    try:
        decrypted = fernet.decrypt(encrypted_api_key.encode("utf-8"))
        return decrypted.decode("utf-8")
    except InvalidToken as exc:
        raise ValueError("Failed to decrypt API key: invalid encryption token") from exc


# Device Tokens & Pairing Codes
def generate_pairing_code(length: int = 8) -> str:
    """Generate a human-readable pairing code (e.g., FORGE-XXXX)."""
    charset = string.ascii_uppercase + string.digits
    # Exclude ambiguous characters: 0, O, 1, I
    clean_charset = "".join(ch for ch in charset if ch not in "0OI1")
    code = "".join(secrets.choice(clean_charset) for _ in range(length))
    return f"{code[:4]}-{code[4:]}"


def generate_device_token() -> str:
    """Generate a high-entropy device authorization token."""
    return f"forge_dev_{secrets.token_urlsafe(36)}"


def hash_device_token(token: str) -> str:
    """Compute SHA-256 hash of a device auth token for safe database storage."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def verify_device_token(plain_token: str, token_hash: str) -> bool:
    """Compare device token with constant-time equality check."""
    computed_hash = hash_device_token(plain_token)
    return secrets.compare_digest(computed_hash, token_hash)
