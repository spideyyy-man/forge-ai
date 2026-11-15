"""Command security classification and execution policy enforcement."""

from __future__ import annotations

import re
import shlex
from enum import Enum


class CommandRisk(str, Enum):
    """Risk tiers for terminal command execution."""

    SAFE = "SAFE"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


# Commands strictly classified as CRITICAL (forbidden in normal agent mode)
CRITICAL_PATTERNS = [
    re.compile(r"\b(sudo|su|runas|doas)\b", re.IGNORECASE),
    re.compile(r"\b(mkfs|fdisk|parted|diskpart)\b", re.IGNORECASE),
    re.compile(r"\b(chmod\s+(-R\s+)?777)\b", re.IGNORECASE),
    re.compile(r"\b(format\s+[a-z]:)\b", re.IGNORECASE),
    re.compile(r"\b(dd\s+if=.*of=)\b", re.IGNORECASE),
    re.compile(r"\b(Set-ExecutionPolicy\s+Bypass)\b", re.IGNORECASE),
    re.compile(r"\b(shutdown|reboot|init\s+0|halt)\b", re.IGNORECASE),
    re.compile(r"\b(net\s+user|net\s+localgroup\s+administrators)\b", re.IGNORECASE),
    re.compile(r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:", re.IGNORECASE),  # fork bomb
]

# Commands classified as HIGH risk (destructive or database/service altering)
HIGH_PATTERNS = [
    re.compile(r"\b(rm\s+(-rf|-fr|--recursive))\b", re.IGNORECASE),
    re.compile(r"\b(del\s+/[sfq])\b", re.IGNORECASE),
    re.compile(r"\b(rmdir\s+/[sq])\b", re.IGNORECASE),
    re.compile(r"\b(drop\s+database|drop\s+table|truncate\s+table)\b", re.IGNORECASE),
    re.compile(r"\b(taskkill\s+/f)\b", re.IGNORECASE),
    re.compile(r"\b(kill\s+-9)\b", re.IGNORECASE),
    re.compile(r"\b(git\s+reset\s+--hard)\b", re.IGNORECASE),
    re.compile(r"\b(git\s+clean\s+-fdx)\b", re.IGNORECASE),
    re.compile(r"\b(git\s+push\s+.*--force)\b", re.IGNORECASE),
]

# Commands classified as MEDIUM risk (package managers, network writes, commits, builds)
MEDIUM_PATTERNS = [
    re.compile(r"\b(npm|yarn|pnpm|bun)\s+(install|add|remove|update|build)\b", re.IGNORECASE),
    re.compile(r"\b(pip|poetry|uv|conda)\s+(install|uninstall|update|add|remove)\b", re.IGNORECASE),
    re.compile(r"\b(cargo\s+(build|add|remove|update))\b", re.IGNORECASE),
    re.compile(r"\b(go\s+(get|build|install))\b", re.IGNORECASE),
    re.compile(r"\b(git\s+(commit|push|merge|rebase|stash|pull|checkout|switch))\b", re.IGNORECASE),
    re.compile(r"\b(docker|docker-compose|podman)\b", re.IGNORECASE),
    re.compile(r"\b(curl|wget)\b", re.IGNORECASE),
]

# Commands classified as LOW risk (search, inspect, info)
LOW_PATTERNS = [
    re.compile(r"\b(git\s+(log|diff|status|branch|show|remote))\b", re.IGNORECASE),
    re.compile(r"\b(find|grep|ripgrep|rg|fd|where|which)\b", re.IGNORECASE),
    re.compile(r"\b(head|tail|less|more|wc)\b", re.IGNORECASE),
    re.compile(r"\b(node\s+-v|python\s+--version|git\s+--version)\b", re.IGNORECASE),
]

# Commands classified as SAFE (pure read-only or harmless diagnostic)
SAFE_PATTERNS = [
    re.compile(r"^\s*(ls|dir)(\s+.*)?$", re.IGNORECASE),
    re.compile(r"^\s*(cat|type)(\s+.*)?$", re.IGNORECASE),
    re.compile(r"^\s*(echo|print)(\s+.*)?$", re.IGNORECASE),
    re.compile(r"^\s*(pwd|cd)(\s+.*)?$", re.IGNORECASE),
    re.compile(r"^\s*(pytest|npm\s+test|cargo\s+test|go\s+test|vitest|jest)(\s+.*)?$", re.IGNORECASE),
    re.compile(r"^\s*git\s+(status|log|diff|branch)(\s+.*)?$", re.IGNORECASE),
    re.compile(r"^\s*(whoami|date|time)(\s+.*)?$", re.IGNORECASE),
]


def classify_command(command: str) -> CommandRisk:
    """Classify the risk level of an arbitrary command string.

    Args:
        command: Full command line string.

    Returns:
        CommandRisk classification.
    """
    cmd_stripped = command.strip()
    if not cmd_stripped:
        return CommandRisk.SAFE

    # Check CRITICAL first
    for pattern in CRITICAL_PATTERNS:
        if pattern.search(cmd_stripped):
            return CommandRisk.CRITICAL

    # Check HIGH
    for pattern in HIGH_PATTERNS:
        if pattern.search(cmd_stripped):
            return CommandRisk.HIGH

    # Check SAFE patterns
    for pattern in SAFE_PATTERNS:
        if pattern.match(cmd_stripped):
            return CommandRisk.SAFE

    # Check LOW patterns
    for pattern in LOW_PATTERNS:
        if pattern.search(cmd_stripped):
            return CommandRisk.LOW

    # Check MEDIUM patterns
    for pattern in MEDIUM_PATTERNS:
        if pattern.search(cmd_stripped):
            return CommandRisk.MEDIUM

    # Default unclassified commands to MEDIUM for precaution
    return CommandRisk.MEDIUM


class PolicyCheckResult(tuple):
    """Result of command policy check. Can be unpacked as (bool, str) or evaluated as bool."""

    def __new__(cls, allowed: bool, reason: str):
        return super().__new__(cls, (allowed, reason))

    def __bool__(self) -> bool:
        return bool(self[0])

    @property
    def allowed(self) -> bool:
        return bool(self[0])

    @property
    def reason(self) -> str:
        return str(self[1])


class CommandPolicy:
    """Enforces execution policies and permission checks for terminal commands."""

    def __init__(
        self,
        max_allowed_risk: CommandRisk = CommandRisk.MEDIUM,
        allowlist: list[str] | None = None,
        blocklist: list[str] | None = None,
    ) -> None:
        """Initialize command policy.

        Args:
            max_allowed_risk: Highest risk level permitted (default: MEDIUM).
            allowlist: Explicit command regexes/strings always allowed.
            blocklist: Explicit command regexes/strings always blocked.
        """
        self.max_allowed_risk = max_allowed_risk
        self.allowlist = allowlist or []
        self.blocklist = blocklist or []

        self._risk_hierarchy = {
            CommandRisk.SAFE: 0,
            CommandRisk.LOW: 1,
            CommandRisk.MEDIUM: 2,
            CommandRisk.HIGH: 3,
            CommandRisk.CRITICAL: 4,
        }

    def classify(self, command: str) -> CommandRisk:
        """Classify the risk level of a command."""
        return classify_command(command)

    def is_allowed(self, command: str) -> PolicyCheckResult:
        """Check if command is permitted by policy.

        Args:
            command: Command string to test.

        Returns:
            PolicyCheckResult: (is_allowed: bool, reason: str) that evaluates truthy if allowed.
        """
        cmd_stripped = command.strip()
        if not cmd_stripped:
            return PolicyCheckResult(True, "Empty command")

        # Check explicit blocklist
        for pattern in self.blocklist:
            if re.search(pattern, cmd_stripped, re.IGNORECASE):
                return PolicyCheckResult(False, f"Command matched blocklist pattern: {pattern}")

        # Check explicit allowlist
        for pattern in self.allowlist:
            if re.search(pattern, cmd_stripped, re.IGNORECASE):
                return PolicyCheckResult(True, f"Command matched allowlist pattern: {pattern}")

        risk = classify_command(cmd_stripped)
        allowed_score = self._risk_hierarchy[self.max_allowed_risk]
        current_score = self._risk_hierarchy[risk]

        if current_score <= allowed_score:
            return PolicyCheckResult(True, f"Risk level {risk.value} is within allowed limit {self.max_allowed_risk.value}")
        else:
            return PolicyCheckResult(False, f"Risk level {risk.value} exceeds allowed limit {self.max_allowed_risk.value}")


def is_command_allowed(
    command: str,
    max_risk: CommandRisk = CommandRisk.MEDIUM,
) -> bool:
    """Convenience helper to check if a command is allowed."""
    policy = CommandPolicy(max_allowed_risk=max_risk)
    allowed, _ = policy.is_allowed(command)
    return allowed
