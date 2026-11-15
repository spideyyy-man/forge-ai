"""Privacy Engine: Secret redaction, .forgeignore enforcement, and local-only filtering."""
import re
import fnmatch
from typing import List, Dict, Any, Optional

# Secret patterns to detect and redact before transmission
SECRET_PATTERNS = [
    (r"(?i)(api[_-]?key|secret|token|password|auth|bearer)\s*[:=]\s*['\"]([A-Za-z0-9_\-\.]{8,})['\"]", r"\1: '***REDACTED***'"),
    (r"ghp_[0-9a-zA-Z]{36}", "***REDACTED_GITHUB_TOKEN***"),
    (r"xox[baprs]-[0-9a-zA-Z]{10,48}", "***REDACTED_SLACK_TOKEN***"),
    (r"sk-[a-zA-Z0-9]{20,}", "***REDACTED_API_KEY***"),
    (r"AIza[0-9A-Za-z\-_]{35}", "***REDACTED_GOOGLE_API_KEY***"),
]

DEFAULT_FORGE_IGNORE = [
    ".env",
    ".env.*",
    "*.pem",
    "*.key",
    "id_rsa",
    "id_ed25519",
    "credentials.json",
    "*.p12",
    "*.pfx",
]


class PrivacyEngine:
    """Enforces project privacy rules, redacts credentials, and guards local data."""

    @staticmethod
    def is_path_sensitive(file_path: str, custom_ignore: Optional[List[str]] = None) -> bool:
        """Check if file should be excluded from cloud models."""
        patterns = DEFAULT_FORGE_IGNORE + (custom_ignore or [])
        filename = file_path.replace("\\", "/").split("/")[-1]
        for pattern in patterns:
            if fnmatch.fnmatch(filename, pattern):
                return True
        return False

    @staticmethod
    def redact_secrets(text: str) -> str:
        """Scan text and redact sensitive secrets, tokens, and keys."""
        cleaned = text
        for pattern, replacement in SECRET_PATTERNS:
            cleaned = re.sub(pattern, replacement, cleaned)
        return cleaned

    @staticmethod
    def sanitize_context_for_cloud(
        files: List[Dict[str, str]],
        privacy_mode: str = "CLOUD_ASSISTED",
        custom_ignore: Optional[List[str]] = None,
    ) -> List[Dict[str, str]]:
        """Filter and redact file contexts based on project privacy policy."""
        if privacy_mode == "LOCAL_ONLY":
            # In local-only mode, source code is strictly withheld from external clouds
            return []

        sanitized = []
        for file in files:
            path = file.get("path", "")
            if PrivacyEngine.is_path_sensitive(path, custom_ignore):
                continue

            content = file.get("content", "")
            sanitized.append({
                "path": path,
                "content": PrivacyEngine.redact_secrets(content),
            })
        return sanitized
