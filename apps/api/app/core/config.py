"""Application configuration using Pydantic Settings."""

from functools import lru_cache
from typing import Dict, List, Optional, Tuple, Union
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# Query params that libpq/psql understand but asyncpg does not accept in the
# DSN. Managed Postgres providers (Neon, Supabase, Render, ...) hand out URLs
# that carry these, so we strip them and translate the SSL intent into
# asyncpg connect_args instead.
_LIBPQ_ONLY_PARAMS = {"sslmode", "channel_binding", "options"}
_SSL_ENABLING_VALUES = {"require", "verify-ca", "verify-full", "prefer", "allow", "true", "1"}


def normalize_db_url(raw: str) -> Tuple[str, Dict[str, object]]:
    """Return an asyncpg-compatible SQLAlchemy URL and its connect_args.

    - Upgrades bare ``postgres://`` / ``postgresql://`` schemes to
      ``postgresql+asyncpg://`` so a provider's plain DSN works unchanged.
    - Drops libpq-only query params (``sslmode``, ``channel_binding``,
      ``options``) that asyncpg rejects, and converts an SSL request into
      ``connect_args={"ssl": True}``.
    - Leaves sqlite and already-qualified (``+driver``) URLs untouched.
    """
    url = (raw or "").strip()
    connect_args: Dict[str, object] = {}
    if not url:
        return url, connect_args

    parts = urlsplit(url)
    scheme = parts.scheme

    # Upgrade bare postgres schemes to the async driver.
    if scheme in ("postgres", "postgresql"):
        scheme = "postgresql+asyncpg"

    # Only postgres needs the libpq param / SSL handling.
    if scheme.startswith("postgresql"):
        kept: List[Tuple[str, str]] = []
        ssl_required = False
        for key, value in parse_qsl(parts.query, keep_blank_values=True):
            lowered = key.lower()
            if lowered in _LIBPQ_ONLY_PARAMS:
                if value.lower() in _SSL_ENABLING_VALUES:
                    ssl_required = True
                continue
            if lowered == "ssl":
                if value.lower() in _SSL_ENABLING_VALUES:
                    ssl_required = True
                continue
            kept.append((key, value))
        parts = parts._replace(scheme=scheme, query=urlencode(kept))
        url = urlunsplit(parts)
        if ssl_required:
            connect_args["ssl"] = True
    elif scheme != parts.scheme:
        url = urlunsplit(parts._replace(scheme=scheme))

    return url, connect_args


class Settings(BaseSettings):
    """FORGE AI server settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Server settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True
    ENVIRONMENT: str = "development"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://forge:forge@localhost:5432/forge_ai"

    # Security & Auth
    SECRET_KEY: str = "forge-ai-production-super-secret-key-change-in-production-min-32-chars"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
    ENCRYPTION_KEY: Optional[str] = None

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]

    # Redis Cache & Message Broker (optional)
    REDIS_URL: Optional[str] = None

    # Agent / WebSocket Settings
    DEVICE_HEARTBEAT_TIMEOUT_SECONDS: int = 60
    PAIRING_CODE_EXPIRE_MINUTES: int = 15

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        return ["*"]

    @property
    def sqlalchemy_url(self) -> str:
        """DATABASE_URL normalized to an asyncpg-compatible SQLAlchemy URL."""
        return normalize_db_url(self.DATABASE_URL)[0]

    @property
    def db_connect_args(self) -> Dict[str, object]:
        """Driver connect_args derived from DATABASE_URL (e.g. SSL for managed Postgres)."""
        return normalize_db_url(self.DATABASE_URL)[1]


@lru_cache()
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()


settings = get_settings()
