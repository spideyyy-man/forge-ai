"""Filesystem operations with security validation."""
import os
import stat
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

from app.security.path_validator import PathValidator
from app.security.audit import AuditLogger

logger = logging.getLogger(__name__)

# Directories to skip during listing
IGNORED_DIRS = {".git", "node_modules", "__pycache__", ".next", "venv", ".venv", "dist", "build", ".tox", ".pytest_cache"}


class FileSystemOperations:
    """Secure filesystem operations."""

    def __init__(self, path_validator: PathValidator, audit_logger: AuditLogger, config):
        self.validator = path_validator
        self.audit = audit_logger
        self.config = config
        self.max_file_size = getattr(config, 'max_file_size_mb', 50) * 1024 * 1024

    async def list_directory(self, path: str, recursive: bool = False, max_depth: int = 3, **kwargs) -> Dict[str, Any]:
        """List directory contents."""
        self.validator.validate(path)
        p = Path(path)

        if not p.exists():
            return {"success": False, "error": f"Directory not found: {path}"}
        if not p.is_dir():
            return {"success": False, "error": f"Not a directory: {path}"}

        entries = []
        try:
            for item in sorted(p.iterdir()):
                if item.name.startswith('.') and item.name not in ('.env.example', '.gitignore'):
                    if item.name in ('.git', '.next', '.venv'):
                        continue

                if item.name in IGNORED_DIRS:
                    entry_type = "directory"
                    entries.append({"name": item.name, "type": entry_type, "skipped": True})
                    continue

                try:
                    st = item.stat()
                    entry = {
                        "name": item.name,
                        "type": "directory" if item.is_dir() else "file",
                        "size": st.st_size if item.is_file() else None,
                        "modified": datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).isoformat(),
                    }
                    entries.append(entry)
                except PermissionError:
                    entries.append({"name": item.name, "type": "unknown", "error": "permission denied"})

        except PermissionError:
            return {"success": False, "error": f"Permission denied: {path}"}

        self.audit.log("list_directory", path, True)
        return {"success": True, "path": path, "entries": entries, "count": len(entries)}

    async def read_file(self, path: str, start_line: Optional[int] = None, end_line: Optional[int] = None, **kwargs) -> Dict[str, Any]:
        """Read file contents."""
        self.validator.validate(path)
        p = Path(path)

        if not p.exists():
            return {"success": False, "error": f"File not found: {path}"}
        if not p.is_file():
            return {"success": False, "error": f"Not a file: {path}"}
        if self.validator.is_protected(path):
            return {"success": False, "error": f"Protected file: {path}"}

        size = p.stat().st_size
        if size > self.max_file_size:
            return {"success": False, "error": f"File too large: {size} bytes (max: {self.max_file_size})"}

        try:
            content = p.read_text(encoding="utf-8", errors="replace")
            if start_line is not None or end_line is not None:
                lines = content.split("\n")
                start = (start_line or 1) - 1
                end = end_line or len(lines)
                content = "\n".join(lines[start:end])
                total_lines = len(lines)
            else:
                total_lines = content.count("\n") + 1

            self.audit.log("read_file", path, True)
            return {
                "success": True,
                "path": path,
                "content": content,
                "size": size,
                "total_lines": total_lines,
                "encoding": "utf-8",
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def write_file(self, path: str, content: str, create_parents: bool = False, **kwargs) -> Dict[str, Any]:
        """Write content to a file."""
        self.validator.validate(path)
        if self.validator.is_protected(path):
            return {"success": False, "error": f"Protected file: {path}"}

        p = Path(path)
        if create_parents:
            p.parent.mkdir(parents=True, exist_ok=True)

        if not p.parent.exists():
            return {"success": False, "error": f"Parent directory does not exist: {p.parent}"}

        try:
            existed = p.exists()
            p.write_text(content, encoding="utf-8")
            self.audit.log("write_file", path, True, {"existed": existed, "size": len(content)})
            return {"success": True, "path": path, "size": len(content), "created": not existed}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def create_file(self, path: str, content: str = "", **kwargs) -> Dict[str, Any]:
        """Create a new file."""
        self.validator.validate(path)
        p = Path(path)

        if p.exists():
            return {"success": False, "error": f"File already exists: {path}"}

        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
            self.audit.log("create_file", path, True)
            return {"success": True, "path": path}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def create_directory(self, path: str, **kwargs) -> Dict[str, Any]:
        """Create a directory."""
        self.validator.validate(path)
        try:
            Path(path).mkdir(parents=True, exist_ok=True)
            self.audit.log("create_directory", path, True)
            return {"success": True, "path": path}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def rename_file(self, old_path: str, new_path: str, **kwargs) -> Dict[str, Any]:
        """Rename a file or directory."""
        self.validator.validate(old_path)
        self.validator.validate(new_path)
        try:
            Path(old_path).rename(Path(new_path))
            self.audit.log("rename_file", old_path, True, {"new_path": new_path})
            return {"success": True, "old_path": old_path, "new_path": new_path}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def move_file(self, src: str, dst: str, **kwargs) -> Dict[str, Any]:
        """Move a file or directory."""
        return await self.rename_file(src, dst)

    async def delete_file(self, path: str, require_confirmation: bool = True, **kwargs) -> Dict[str, Any]:
        """Delete a file."""
        self.validator.validate(path)
        if self.validator.is_protected(path):
            return {"success": False, "error": f"Protected file: {path}"}

        p = Path(path)
        if not p.exists():
            return {"success": False, "error": f"Not found: {path}"}

        try:
            if p.is_file():
                p.unlink()
            elif p.is_dir():
                import shutil
                shutil.rmtree(p)
            self.audit.log("delete_file", path, True)
            return {"success": True, "path": path, "deleted": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def get_file_metadata(self, path: str, **kwargs) -> Dict[str, Any]:
        """Get file metadata."""
        self.validator.validate(path)
        p = Path(path)

        if not p.exists():
            return {"success": False, "error": f"Not found: {path}"}

        try:
            st = p.stat()
            return {
                "success": True,
                "path": path,
                "name": p.name,
                "extension": p.suffix,
                "size": st.st_size,
                "is_file": p.is_file(),
                "is_directory": p.is_dir(),
                "is_symlink": p.is_symlink(),
                "created": datetime.fromtimestamp(st.st_ctime, tz=timezone.utc).isoformat(),
                "modified": datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).isoformat(),
                "permissions": oct(st.st_mode),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
