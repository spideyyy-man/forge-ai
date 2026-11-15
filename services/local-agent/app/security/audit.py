"""Structured JSON audit logger for file operations, terminal commands, and agent events."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from app.security.command_policy import CommandRisk


class AuditEvent(BaseModel):
    """Pydantic model representing an immutable audit log entry."""

    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO-8601 UTC timestamp",
    )
    event_type: str = Field(
        description="Category: file_operation, terminal_command, connection, auth, git",
    )
    action: str = Field(
        description="Action performed, e.g., read_file, execute_command, write_file",
    )
    target: str = Field(
        description="Resource targeted (path, command line, remote address)",
    )
    risk_level: str = Field(
        default=CommandRisk.SAFE.value,
        description="Risk level evaluation",
    )
    success: bool = Field(
        default=True,
        description="Whether the action succeeded or was permitted",
    )
    details: dict[str, Any] = Field(
        default_factory=dict,
        description="Supplementary structured metadata",
    )
    device_id: str = Field(
        default="",
        description="Device identifier running the agent",
    )


class AuditLogger:
    """Manages appending and querying structured JSONL audit logs with automatic rotation."""

    def __init__(
        self,
        log_path: str | Path = "forge-audit.jsonl",
        max_bytes: int = 20 * 1024 * 1024,
        backup_count: int = 5,
        device_id: str = "",
    ) -> None:
        """Initialize the audit logger.

        Args:
            log_path: Target path for the JSONL audit file.
            max_bytes: Rotation size threshold in bytes.
            backup_count: Number of rotated files to retain.
            device_id: Device ID to tag on every event.
        """
        self.log_path = Path(log_path)
        self.device_id = device_id
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

        self._logger = logging.getLogger("forge.audit")
        self._logger.setLevel(logging.INFO)
        self._logger.propagate = False

        # Configure rotating file handler for audit logs
        if not self._logger.handlers:
            handler = RotatingFileHandler(
                self.log_path,
                maxBytes=max_bytes,
                backupCount=backup_count,
                encoding="utf-8",
            )
            handler.setFormatter(logging.Formatter("%(message)s"))
            self._logger.addHandler(handler)

    def log(
        self,
        event_or_action: AuditEvent | str,
        target: str | None = None,
        success: bool = True,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Append an audit event to the audit log. Supports both AuditEvent and positional arguments."""
        if isinstance(event_or_action, AuditEvent):
            event = event_or_action
        else:
            action = str(event_or_action)
            event_type = "file_operation"
            if action.startswith("git"):
                event_type = "git"
            elif action in ("execute_command", "kill_process", "list_processes"):
                event_type = "terminal_command"
            elif action in ("connect", "disconnect", "auth"):
                event_type = "connection"

            event = AuditEvent(
                event_type=event_type,
                action=action,
                target=str(target or ""),
                risk_level=CommandRisk.SAFE.value,
                success=success,
                details=details or {},
                device_id=self.device_id,
            )

        if not event.device_id and self.device_id:
            event.device_id = self.device_id
        payload = event.model_dump()
        self._logger.info(json.dumps(payload, default=str))

    def log_file_operation(
        self,
        action: str,
        path: str,
        success: bool = True,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Helper to log filesystem operations."""
        event = AuditEvent(
            event_type="file_operation",
            action=action,
            target=path,
            risk_level=CommandRisk.LOW.value if action in ("read", "list") else CommandRisk.MEDIUM.value,
            success=success,
            details=details or {},
            device_id=self.device_id,
        )
        self.log(event)

    def log_terminal_command(
        self,
        command: str,
        risk_level: CommandRisk,
        success: bool = True,
        exit_code: int | None = None,
        duration_ms: float = 0.0,
        cwd: str | None = None,
    ) -> None:
        """Helper to log terminal command executions."""
        event = AuditEvent(
            event_type="terminal_command",
            action="execute_command",
            target=command,
            risk_level=risk_level.value,
            success=success,
            details={
                "exit_code": exit_code,
                "duration_ms": duration_ms,
                "cwd": cwd,
            },
            device_id=self.device_id,
        )
        self.log(event)

    def log_connection_event(
        self,
        action: str,
        remote_url: str,
        success: bool = True,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Helper to log WebSocket connection state changes."""
        event = AuditEvent(
            event_type="connection",
            action=action,
            target=remote_url,
            risk_level=CommandRisk.SAFE.value,
            success=success,
            details=details or {},
            device_id=self.device_id,
        )
        self.log(event)


# Global singleton instance for easy import across modules
audit_logger = AuditLogger()
