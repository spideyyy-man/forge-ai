"""Path validation and security enforcement for workspace containment."""

from __future__ import annotations

import fnmatch
import os
from pathlib import Path


def canonicalize_path(path: str | Path) -> str:
    """Resolve symlinks and return a normalized, absolute filesystem path.

    Args:
        path: Path string or Path object.

    Returns:
        Canonical absolute path string.
    """
    p = Path(path).expanduser()
    try:
        # Resolve symlinks and relative components
        return str(p.resolve())
    except (OSError, RuntimeError):
        # Fall back to absolute if file doesn't exist yet
        return str(p.absolute())


def check_traversal(path: str | Path) -> bool:
    """Check if path string contains malicious directory traversal patterns.

    Args:
        path: Raw or normalized path string.

    Returns:
        True if traversal pattern detected (unsafe), False if safe.
    """
    raw_str = str(path)
    # Check for null byte injection
    if "\x00" in raw_str:
        return True

    # Check for Windows Alternate Data Streams (:$)
    if "::$DATA" in raw_str.upper():
        return True

    # Normalize forward and backward slashes
    parts = raw_str.replace("\\", "/").split("/")
    if ".." in parts:
        # If relative traversal parts exist before canonicalization
        # that could be intentional if safely resolved, but we flag if it resolves outside root
        pass

    return False


def check_symlink_escape(path: str | Path, approved_roots: list[str | Path]) -> bool:
    """Check if a symlink target points outside all approved workspace roots.

    Args:
        path: Path to inspect.
        approved_roots: List of approved workspace directories.

    Returns:
        True if the symlink escapes approved roots (unsafe), False if safe.
    """
    target = Path(path)
    if not target.is_symlink():
        return False

    try:
        real_target = target.resolve()
        for root in approved_roots:
            approved = Path(root).resolve()
            if real_target == approved or approved in real_target.parents:
                return False
        # Symlink target is not within any approved root
        return True
    except (OSError, RuntimeError):
        return True


def is_protected_file(path: str | Path, patterns: list[str]) -> bool:
    """Check whether a file matches protected sensitive file patterns.

    Args:
        path: Path to inspect.
        patterns: List of glob patterns (e.g. ['.env', '*.pem']).

    Returns:
        True if file is protected, False otherwise.
    """
    p = Path(path)
    filename = p.name
    full_str = str(p)

    for pattern in patterns:
        if fnmatch.fnmatch(filename, pattern):
            return True
        if fnmatch.fnmatch(full_str, pattern):
            return True
        # Match against subparts like .env.production
        if pattern.startswith(".") and filename.startswith(pattern):
            return True
    return False


def validate_path(
    path: str | Path,
    approved_roots: list[str | Path],
    protected_patterns: list[str] | None = None,
    allow_nonexistent: bool = True,
) -> bool:
    """Validate that a path is safe, contained inside approved roots, and not protected.

    Args:
        path: Target filesystem path to validate.
        approved_roots: List of approved root directories.
        protected_patterns: Optional list of protected patterns.
        allow_nonexistent: Whether path is allowed to not exist yet (for new files).

    Returns:
        True if path is strictly valid and permitted, False otherwise.
    """
    if not approved_roots:
        return False

    if check_traversal(path):
        return False

    try:
        target = Path(path).expanduser()
        # If target doesn't exist yet, validate its existing parent directory
        if not target.exists():
            if not allow_nonexistent:
                return False
            # Find closest existing parent
            parent = target.parent
            while not parent.exists() and parent != parent.parent:
                parent = parent.parent
            canonical_target = Path(canonicalize_path(target))
        else:
            canonical_target = target.resolve()

        # Check symlink escapes
        if target.is_symlink() and check_symlink_escape(target, approved_roots):
            return False

        # Verify target is contained inside at least one approved root
        is_contained = False
        for root in approved_roots:
            approved = Path(root).resolve()
            if canonical_target == approved or approved in canonical_target.parents:
                is_contained = True
                break

        if not is_contained:
            return False

        # Verify not protected
        if protected_patterns and is_protected_file(canonical_target, protected_patterns):
            return False

        return True

    except (OSError, RuntimeError, ValueError):
        return False


class PathValidator:
    """Security validator for workspace path boundaries."""

    def __init__(
        self,
        approved_workspaces: list[str] | None = None,
        protected_patterns: list[str] | None = None,
    ) -> None:
        self.approved_workspaces = approved_workspaces if approved_workspaces is not None else []
        self.protected_patterns = protected_patterns or [
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
        ]

    def validate(self, path: str | Path, allow_nonexistent: bool = True) -> bool:
        """Validate path containment within approved workspaces.

        Raises:
            PermissionError: If path is not inside approved workspaces or is invalid.
        """
        if not self.approved_workspaces:
            raise PermissionError(f"No approved workspaces configured. Access denied to path: {path}")

        if not validate_path(path, self.approved_workspaces, self.protected_patterns, allow_nonexistent=allow_nonexistent):
            raise PermissionError(f"Path outside approved workspaces or invalid: {path}")
        return True

    def is_valid(self, path: str | Path, allow_nonexistent: bool = True) -> bool:
        """Check if path is valid without raising an exception."""
        if not self.approved_workspaces:
            return False
        return validate_path(path, self.approved_workspaces, self.protected_patterns, allow_nonexistent=allow_nonexistent)

    def is_protected(self, path: str | Path) -> bool:
        """Check if path matches protected patterns."""
        return is_protected_file(path, self.protected_patterns)

