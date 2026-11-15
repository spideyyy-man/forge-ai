"""Text search using ripgrep or Python fallback."""
import asyncio
import os
import re
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any

from app.security.path_validator import PathValidator

logger = logging.getLogger(__name__)


class TextSearch:
    """Search text in files."""

    def __init__(self, path_validator: PathValidator):
        self.validator = path_validator

    async def search(self, root_path: str, query: str, file_patterns: Optional[List[str]] = None, max_results: int = 100, **kwargs) -> Dict[str, Any]:
        """Search for text in files."""
        self.validator.validate(root_path)

        # Try ripgrep first
        try:
            res = await self._rg_search(root_path, query, file_patterns, max_results)
            if res.get("success"):
                return res
        except Exception:
            pass

        return await self._python_search(root_path, query, file_patterns, max_results)

    async def _rg_search(self, root_path: str, query: str, patterns: Optional[List[str]], max_results: int) -> Dict[str, Any]:
        """Search using ripgrep."""
        cmd = ["rg", "--json", "-m", str(max_results), query, root_path]
        if patterns:
            for p in patterns:
                cmd.extend(["-g", p])

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()

        results = []
        import json
        for line in stdout.decode(errors="replace").splitlines():
            try:
                data = json.loads(line)
                if data.get("type") == "match":
                    match_data = data["data"]
                    results.append({
                        "file": match_data["path"]["text"],
                        "line": match_data["line_number"],
                        "text": match_data["lines"]["text"].strip(),
                    })
            except (json.JSONDecodeError, KeyError):
                continue

        return {"success": True, "results": results[:max_results], "count": len(results), "engine": "ripgrep"}

    async def _python_search(self, root_path: str, query: str, patterns: Optional[List[str]], max_results: int) -> Dict[str, Any]:
        """Fallback Python search."""
        results = []
        skip_dirs = {".git", "node_modules", "__pycache__", ".next", "venv", ".venv", "dist", "build"}

        try:
            pattern = re.compile(re.escape(query), re.IGNORECASE)
        except re.error:
            return {"success": False, "error": "Invalid search pattern"}

        for root, dirs, files in os.walk(root_path):
            dirs[:] = [d for d in dirs if d not in skip_dirs]
            for file in files:
                if len(results) >= max_results:
                    break
                filepath = Path(root) / file
                try:
                    content = filepath.read_text(encoding="utf-8", errors="ignore")
                    for i, line in enumerate(content.splitlines(), 1):
                        if pattern.search(line):
                            results.append({
                                "file": str(filepath),
                                "line": i,
                                "text": line.strip()[:200],
                            })
                            if len(results) >= max_results:
                                break
                except (PermissionError, UnicodeDecodeError, OSError):
                    continue

        return {"success": True, "results": results, "count": len(results), "engine": "python"}
