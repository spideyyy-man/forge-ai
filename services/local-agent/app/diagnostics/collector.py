"""System diagnostics collector."""
import platform
import shutil
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class DiagnosticCollector:
    """Collect system diagnostics."""

    def __init__(self, config):
        self.config = config

    async def collect(self, **kwargs) -> Dict[str, Any]:
        """Collect comprehensive diagnostics."""
        import psutil

        tools = {}
        for tool in ["node", "npm", "python", "pip", "git", "rg", "docker", "cargo", "go", "java"]:
            tools[tool] = shutil.which(tool) is not None

        disk_path = "C:\\" if platform.system() == "Windows" else "/"
        try:
            disk_percent = psutil.disk_usage(disk_path).percent
        except Exception:
            disk_percent = 0.0

        return {
            "success": True,
            "system": {
                "os": platform.system(),
                "os_version": platform.version(),
                "architecture": platform.machine(),
                "python_version": platform.python_version(),
                "hostname": platform.node(),
            },
            "resources": {
                "cpu_count": psutil.cpu_count(),
                "cpu_percent": psutil.cpu_percent(),
                "memory_total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
                "memory_available_gb": round(psutil.virtual_memory().available / (1024**3), 2),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_usage_percent": disk_percent,
            },
            "tools": tools,
            "workspaces": self.config.approved_workspaces,
        }
