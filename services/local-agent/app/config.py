"""Configuration management for FORGE AI Local Agent using Pydantic Settings and TOML."""

from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Any

import toml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AgentConfig(BaseSettings):
    """Configuration settings for the FORGE AI Local Workspace Agent."""

    model_config = SettingsConfigDict(
        env_prefix="FORGE_",
        case_sensitive=False,
        extra="ignore",
    )

    # Server settings
    server_url: str = Field(
        default="ws://localhost:8000/ws/agent",
        description="WebSocket URL to cloud backend",
    )

    # Device & Authentication
    device_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique device identifier",
    )
    auth_token: str = Field(
        default="",
        description="Bearer authentication token obtained during pairing",
    )

    # Workspaces
    approved_workspaces: list[str] = Field(
        default_factory=list,
        description="Approved directory paths agent can access",
    )

    # Operational settings
    heartbeat_interval: int = Field(
        default=30,
        ge=5,
        le=300,
        description="Interval in seconds between heartbeats",
    )
    max_reconnect_delay: int = Field(
        default=60,
        ge=5,
        le=600,
        description="Maximum backoff delay in seconds for reconnecting",
    )
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR)",
    )

    # Security settings
    terminal_timeout: int = Field(
        default=300,
        ge=10,
        le=3600,
        description="Maximum command execution timeout in seconds",
    )
    max_file_size_mb: int = Field(
        default=50,
        ge=1,
        le=500,
        description="Maximum file size in megabytes for file operations",
    )
    protected_patterns: list[str] = Field(
        default_factory=lambda: [
            ".env",
            ".env.*",
            "*.pem",
            "*.key",
            "id_rsa",
            "id_rsa.*",
            "id_ed25519",
            "id_ed25519.*",
            "*.pfx",
            "*.p12",
        ],
        description="Glob patterns for protected sensitive files",
    )

    # Audit log settings
    audit_log_path: str = Field(
        default="forge-audit.jsonl",
        description="Path to structured audit log file",
    )
    max_sessions: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum concurrent terminal sessions",
    )

    @classmethod
    def load_from_toml(cls, config_path: str | Path) -> AgentConfig:
        """Load configuration from a TOML file with environment variable fallback.

        Args:
            config_path: Path to forge-agent.toml file.

        Returns:
            Initialized AgentConfig instance.
        """
        path = Path(config_path)
        data: dict[str, Any] = {}

        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                toml_data = toml.load(f)

            # Flatten sections from toml
            server_section = toml_data.get("server", {})
            agent_section = toml_data.get("agent", {})
            security_section = toml_data.get("security", {})
            workspaces_section = toml_data.get("workspaces", {})

            if "url" in server_section:
                data["server_url"] = server_section["url"]

            if "device_id" in agent_section:
                data["device_id"] = agent_section["device_id"]
            if "auth_token" in agent_section:
                data["auth_token"] = agent_section["auth_token"]
            if "heartbeat_interval" in agent_section:
                data["heartbeat_interval"] = agent_section["heartbeat_interval"]
            if "max_reconnect_delay" in agent_section:
                data["max_reconnect_delay"] = agent_section["max_reconnect_delay"]
            if "log_level" in agent_section:
                data["log_level"] = agent_section["log_level"]

            if "terminal_timeout" in security_section:
                data["terminal_timeout"] = security_section["terminal_timeout"]
            if "max_file_size_mb" in security_section:
                data["max_file_size_mb"] = security_section["max_file_size_mb"]
            if "protected_patterns" in security_section:
                data["protected_patterns"] = security_section["protected_patterns"]
            if "audit_log_path" in security_section:
                data["audit_log_path"] = security_section["audit_log_path"]

            if "approved" in workspaces_section:
                data["approved_workspaces"] = workspaces_section["approved"]

        # If device_id wasn't in toml, generate one and persist later
        config = cls(**data)

        # Canonicalize workspaces
        normalized_workspaces: list[str] = []
        for ws in config.approved_workspaces:
            p = Path(ws).expanduser().resolve()
            normalized_workspaces.append(str(p))
        config.approved_workspaces = normalized_workspaces

        return config

    @classmethod
    def load(cls, config_path: str | Path = "forge-agent.toml") -> AgentConfig:
        """Alias for load_from_toml."""
        return cls.load_from_toml(config_path)

    def save_to_toml(self, config_path: str | Path) -> None:
        """Save current configuration state to a TOML file.

        Args:
            config_path: Path to target forge-agent.toml.
        """
        path = Path(config_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        payload = {
            "server": {
                "url": self.server_url,
            },
            "agent": {
                "device_id": self.device_id,
                "auth_token": self.auth_token,
                "heartbeat_interval": self.heartbeat_interval,
                "max_reconnect_delay": self.max_reconnect_delay,
                "log_level": self.log_level,
            },
            "security": {
                "terminal_timeout": self.terminal_timeout,
                "max_file_size_mb": self.max_file_size_mb,
                "protected_patterns": self.protected_patterns,
                "audit_log_path": self.audit_log_path,
            },
            "workspaces": {
                "approved": self.approved_workspaces,
            },
        }

        with open(path, "w", encoding="utf-8") as f:
            toml.dump(payload, f)

    def is_workspace_approved(self, path: str | Path) -> bool:
        """Check if a path falls within any approved workspace.

        Args:
            path: Target filesystem path.

        Returns:
            True if path is approved, False otherwise.
        """
        if not self.approved_workspaces:
            return False

        try:
            target_path = Path(path).resolve()
        except (OSError, RuntimeError):
            return False

        for ws in self.approved_workspaces:
            try:
                approved_root = Path(ws).resolve()
                if target_path == approved_root or approved_root in target_path.parents:
                    return True
            except (OSError, RuntimeError):
                continue
        return False

    def add_approved_workspace(self, path: str | Path) -> bool:
        """Add a directory to the approved workspaces list.

        Args:
            path: Workspace path to approve.

        Returns:
            True if added, False if already present or invalid.
        """
        resolved = str(Path(path).expanduser().resolve())
        if resolved not in self.approved_workspaces:
            self.approved_workspaces.append(resolved)
            return True
        return False
