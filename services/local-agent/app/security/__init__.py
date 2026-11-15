"""Security module for path validation, command risk policy, and audit logging."""

from app.security.audit import AuditEvent, AuditLogger, audit_logger
from app.security.command_policy import CommandPolicy, CommandRisk, classify_command, is_command_allowed
from app.security.path_validator import (
    PathValidator,
    canonicalize_path,
    check_symlink_escape,
    check_traversal,
    is_protected_file,
    validate_path,
)

__all__ = [
    "PathValidator",
    "validate_path",
    "canonicalize_path",
    "check_traversal",
    "check_symlink_escape",
    "is_protected_file",
    "CommandRisk",
    "CommandPolicy",
    "classify_command",
    "is_command_allowed",
    "AuditLogger",
    "AuditEvent",
    "audit_logger",
]
