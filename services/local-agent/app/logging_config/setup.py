"""Structured logging configuration with Rich console output and JSON file logging."""

from __future__ import annotations

import json
import logging
import re
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.logging import RichHandler

# Regex patterns for sensitive data redaction
SENSITIVE_PATTERNS = [
    re.compile(r"(bearer\s+)[a-zA-Z0-9_\-\.]{15,}", re.IGNORECASE),
    re.compile(r"(token[=:\s]+)['\"]?[a-zA-Z0-9_\-\.]{15,}['\"]?", re.IGNORECASE),
    re.compile(r"(api[_-]?key[=:\s]+)['\"]?[a-zA-Z0-9_\-\.]{15,}['\"]?", re.IGNORECASE),
    re.compile(r"(password[=:\s]+)['\"]?[^\s'\"]+['\"]?", re.IGNORECASE),
    re.compile(r"(secret[=:\s]+)['\"]?[a-zA-Z0-9_\-\.]{15,}['\"]?", re.IGNORECASE),
    re.compile(r"-----BEGIN [A-Z ]+ PRIVATE KEY-----[^-]+-----END [A-Z ]+ PRIVATE KEY-----", re.DOTALL),
]


def redact_sensitive_data(message: str) -> str:
    """Redact sensitive patterns such as tokens, API keys, and passwords from logs."""
    redacted = message
    for pattern in SENSITIVE_PATTERNS:
        redacted = pattern.sub(r"\1[REDACTED]" if r"\1" in pattern.pattern else "[REDACTED_SECRET]", redacted)
    return redacted


class RedactingFilter(logging.Filter):
    """Logging filter that sanitizes sensitive text from log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = redact_sensitive_data(record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = {k: redact_sensitive_data(str(v)) for k, v in record.args.items()}
            elif isinstance(record.args, tuple):
                record.args = tuple(redact_sensitive_data(str(arg)) for arg in record.args)
        return True


class JsonLogFormatter(logging.Formatter):
    """Formats log records as structured JSON lines."""

    def format(self, record: logging.LogRecord) -> str:
        log_payload: dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "name": record.name,
            "message": redact_sensitive_data(record.getMessage()),
            "module": record.module,
            "func_name": record.funcName,
            "line_no": record.lineno,
        }
        if record.exc_info:
            log_payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_payload, default=str)


def setup_logging(
    log_level: str = "INFO",
    log_file: str | Path | None = None,
    max_bytes: int = 10 * 1024 * 1024,
    backup_count: int = 5,
) -> None:
    """Configure the root logger with Rich console handler and optional rotating JSON file handler.

    Args:
        log_level: Logging level ('DEBUG', 'INFO', 'WARNING', 'ERROR').
        log_file: Optional path to log file.
        max_bytes: Max size in bytes before log file rotation (default: 10MB).
        backup_count: Number of rotated backup files to keep.
    """
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Clear existing handlers
    while root_logger.handlers:
        root_logger.handlers.pop()

    redactor = RedactingFilter()

    # Rich Console Handler
    console = Console(stderr=True)
    rich_handler = RichHandler(
        console=console,
        show_time=True,
        show_path=False,
        rich_tracebacks=True,
        tracebacks_show_locals=False,
    )
    rich_handler.setLevel(numeric_level)
    rich_handler.addFilter(redactor)
    root_logger.addHandler(rich_handler)

    # File Handler
    if log_file:
        file_path = Path(log_file)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            file_path,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(JsonLogFormatter())
        file_handler.addFilter(redactor)
        root_logger.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    """Get a named logger with proper hierarchy."""
    return logging.getLogger(f"forge_agent.{name}")
