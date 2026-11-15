"""Process management."""
import logging
from typing import Dict, Any, List
import psutil

logger = logging.getLogger(__name__)


class ProcessManager:
    """Manage and monitor processes."""

    def __init__(self):
        self._tracked = {}

    async def list_processes(self, **kwargs) -> Dict[str, Any]:
        """List running processes."""
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'status']):
            try:
                info = proc.info
                processes.append({
                    "pid": info['pid'],
                    "name": info['name'],
                    "cpu_percent": info['cpu_percent'],
                    "memory_percent": round(info['memory_percent'] or 0, 2),
                    "status": info['status'],
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        return {"success": True, "processes": processes[:50], "total": len(processes)}

    async def terminate_process(self, pid: int) -> Dict[str, Any]:
        """Terminate a process by PID."""
        try:
            proc = psutil.Process(pid)
            proc.terminate()
            return {"success": True, "pid": pid}
        except psutil.NoSuchProcess:
            return {"success": False, "error": f"Process {pid} not found"}
        except psutil.AccessDenied:
            return {"success": False, "error": f"Access denied for process {pid}"}

    def cleanup(self):
        """Cleanup tracked processes."""
        self._tracked.clear()
