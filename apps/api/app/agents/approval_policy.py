"""Approval policy: which agent operation classes auto-run vs. require approval.

Enforced in trusted code (the engineering loop), never by the model. A safety floor
forces approval for high-risk shell commands (git push, destructive deletes, history
rewrites, piped installers, …) regardless of the user's chosen policy.
"""
import re
from typing import Any, Dict

# Operation classes the user can tune. Order is the display order in the UI.
OP_CLASSES = ["file_read", "file_write", "command_exec", "git_commit"]
MODES = ("auto", "approve")

# Safe defaults: only reading is automatic; anything that changes state asks first.
DEFAULT_POLICY: Dict[str, str] = {
    "file_read": "auto",
    "file_write": "approve",
    "command_exec": "approve",
    "git_commit": "approve",
}

# Map each loop tool to its operation class.
TOOL_CLASS: Dict[str, str] = {
    "read_file": "file_read",
    "list_directory": "file_read",
    "search_text": "file_read",
    "git_status": "file_read",
    "git_diff": "file_read",
    "apply_edit": "file_write",
    "execute_command": "command_exec",
    "git_commit": "git_commit",
}

# Safety floor: commands matching these always require approval, even when
# command_exec is set to "auto". Defence-in-depth alongside the local agent's own
# risk classifier — not a complete sandbox.
_HIGH_RISK_PATTERNS = [
    r"\brm\s+-[a-z]*r",            # rm -rf / -r
    r"\brmdir\b", r"\bdel\s+/", r"\bformat\b", r"\bmkfs\b",
    r"\bgit\s+push\b",
    r"\bgit\s+reset\s+--hard\b",
    r"\bgit\s+clean\b",
    r"\bgit\s+rebase\b",
    r"\bgit\s+checkout\s+--",
    r"\bgit\s+branch\s+-D\b",
    r"\bdrop\s+(table|database)\b",
    r"\btruncate\s+table\b",
    r"\bshutdown\b", r"\breboot\b",
    r">\s*/dev/sd",
    r":\(\)\s*\{",                 # fork bomb
    r"\bchmod\s+-R\b",
    r"\b(curl|wget)\b.*\|\s*(ba)?sh",  # piped installer
]
_HIGH_RISK_RE = re.compile("|".join(_HIGH_RISK_PATTERNS), re.IGNORECASE)


def is_high_risk_command(command: str) -> bool:
    """True when a shell command looks destructive/high-risk (always gated)."""
    return bool(command and _HIGH_RISK_RE.search(command))


def normalize_policy(raw: Any) -> Dict[str, str]:
    """Coerce arbitrary input into a valid policy. Unknown keys dropped; invalid or
    missing modes fall back to the safe default for that class."""
    out = dict(DEFAULT_POLICY)
    if isinstance(raw, dict):
        for cls in OP_CLASSES:
            value = raw.get(cls)
            if isinstance(value, str) and value in MODES:
                out[cls] = value
    return out


def effective_mode(tool_name: str, args: Dict[str, Any], policy: Dict[str, str]) -> str:
    """Return 'auto' or 'approve' for a specific tool call, applying the safety floor.

    Unknown tools are treated as command_exec (i.e. approval by default)."""
    cls = TOOL_CLASS.get(tool_name, "command_exec")
    # Floor: high-risk shell commands always require approval.
    if cls == "command_exec" and is_high_risk_command(str(args.get("command", ""))):
        return "approve"
    mode = policy.get(cls, DEFAULT_POLICY.get(cls, "approve"))
    return mode if mode in MODES else "approve"
