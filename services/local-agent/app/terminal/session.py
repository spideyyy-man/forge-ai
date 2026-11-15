"""Terminal session management."""
import asyncio
import logging
from typing import Dict, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


class TerminalSession:
    def __init__(self, session_id: str, cwd: str):
        self.id = session_id
        self.cwd = cwd
        self.process = None
        self.output_buffer = ""

    async def start(self):
        """Start the terminal session."""
        self.process = await asyncio.create_subprocess_shell(
            "cmd.exe" if __import__("sys").platform == "win32" else "/bin/bash",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=self.cwd,
        )

    async def send_input(self, text: str):
        if self.process and self.process.stdin:
            self.process.stdin.write(text.encode())
            await self.process.stdin.drain()

    async def terminate(self):
        if self.process:
            try:
                self.process.terminate()
            except ProcessLookupError:
                pass


class SessionManager:
    """Manage terminal sessions."""

    def __init__(self, config, max_sessions: int = 10):
        self.sessions: Dict[str, TerminalSession] = {}
        self.max_sessions = max_sessions
        self.config = config

    async def create_session(self, cwd: str) -> Dict:
        if len(self.sessions) >= self.max_sessions:
            return {"success": False, "error": f"Max sessions ({self.max_sessions}) reached"}

        session_id = str(uuid4())
        session = TerminalSession(session_id, cwd)
        await session.start()
        self.sessions[session_id] = session
        return {"success": True, "session_id": session_id}

    async def terminate_session(self, session_id: str) -> bool:
        session = self.sessions.pop(session_id, None)
        if session:
            await session.terminate()
            return True
        return False

    def list_sessions(self) -> list:
        return [{"id": s.id, "cwd": s.cwd} for s in self.sessions.values()]

    async def cleanup(self):
        for session in list(self.sessions.values()):
            await session.terminate()
        self.sessions.clear()
