"""File search."""
import os
import fnmatch
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List

from app.security.path_validator import PathValidator

logger = logging.getLogger(__name__)


class FileSearch:
    """Search for files by name/pattern."""

    def __init__(self, path_validator: PathValidator):
        self.validator = path_validator

    async def search(self, root_path: str, pattern: str, file_type: Optional[str] = None, max_results: int = 100, **kwargs) -> Dict[str, Any]:
        """Search for files matching a pattern."""
        self.validator.validate(root_path)
        skip_dirs = {".git", "node_modules", "__pycache__", ".next", "venv", ".venv", "dist", "build"}
        results = []

        for root, dirs, files in os.walk(root_path):
            dirs[:] = [d for d in dirs if d not in skip_dirs]

            items = files if file_type == "file" else (dirs if file_type == "directory" else files + dirs)

            for item in items:
                if fnmatch.fnmatch(item.lower(), pattern.lower()):
                    full_path = Path(root) / item
                    results.append({
                        "path": str(full_path),
                        "name": item,
                        "type": "directory" if full_path.is_dir() else "file",
                    })
                    if len(results) >= max_results:
                        break
            if len(results) >= max_results:
                break

        return {"success": True, "results": results, "count": len(results)}
