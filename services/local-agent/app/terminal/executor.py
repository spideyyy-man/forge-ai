"""Command execution with security policy."""
import asyncio
import logging
import time
from typing import Optional, Dict, Any

from app.security.command_policy import CommandPolicy
from app.security.audit import AuditLogger

logger = logging.getLogger(__name__)


class CommandExecutor:
    """Execute commands with security policy enforcement."""

    def __init__(self, policy: CommandPolicy, audit: AuditLogger, config):
        self.policy = policy
        self.audit = audit
        self.timeout = getattr(config, 'terminal_timeout', 300)

    async def execute(self, command: str, cwd: Optional[str] = None, timeout: Optional[int] = None, env: Optional[Dict[str, str]] = None, **kwargs) -> Dict[str, Any]:
        """Execute a command and return the result."""
        effective_timeout = timeout or self.timeout

        # Check command policy
        risk = self.policy.classify(command)
        if not self.policy.is_allowed(command):
            self.audit.log("execute_command", command, False, {"reason": "blocked", "risk": risk.value})
            return {
                "success": False,
                "error": f"Command blocked by security policy (risk: {risk.value})",
                "command": command,
                "risk_level": risk.value,
            }

        self.audit.log("execute_command", command, True, {"risk": risk.value, "cwd": cwd})

        start = time.time()
        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
                env=env,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=effective_timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.communicate()
                elapsed = (time.time() - start) * 1000
                return {
                    "success": False,
                    "error": f"Command timed out after {effective_timeout}s",
                    "command": command,
                    "duration_ms": elapsed,
                }

            elapsed = (time.time() - start) * 1000
            return {
                "success": process.returncode == 0,
                "command": command,
                "exit_code": process.returncode,
                "stdout": stdout.decode("utf-8", errors="replace") if stdout else "",
                "stderr": stderr.decode("utf-8", errors="replace") if stderr else "",
                "duration_ms": elapsed,
            }

        except Exception as e:
            elapsed = (time.time() - start) * 1000
            return {
                "success": False,
                "error": str(e),
                "command": command,
                "duration_ms": elapsed,
            }
