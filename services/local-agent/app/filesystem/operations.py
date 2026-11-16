"""Filesystem operations with security validation."""
import os
import stat
import difflib
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

from app.security.path_validator import PathValidator
from app.security.audit import AuditLogger

logger = logging.getLogger(__name__)

# Directories to skip during listing
IGNORED_DIRS = {".git", "node_modules", "__pycache__", ".next", "venv", ".venv", "dist", "build", ".tox", ".pytest_cache"}


def compute_unified_diff(old: str, new: str, path: str) -> Dict[str, Any]:
    """Build a unified diff between two text blobs.

    Returns the diff text plus added/removed line counts so a caller can show a
    human-readable preview before any bytes are written to disk.
    """
    old_lines = old.splitlines(keepends=True)
    new_lines = new.splitlines(keepends=True)
    diff_lines = list(
        difflib.unified_diff(old_lines, new_lines, fromfile=f"a/{path}", tofile=f"b/{path}")
    )
    additions = sum(1 for ln in diff_lines if ln.startswith("+") and not ln.startswith("+++"))
    deletions = sum(1 for ln in diff_lines if ln.startswith("-") and not ln.startswith("---"))
    return {
        "diff": "".join(diff_lines),
        "additions": additions,
        "deletions": deletions,
    }


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

    async def apply_edit(
        self,
        path: str,
        content: str,
        dry_run: bool = False,
        create_parents: bool = True,
        **kwargs,
    ) -> Dict[str, Any]:
        """Apply an edit that replaces a file's full contents, returning a unified diff.

        This is the approval-gated write primitive used by the engineering loop:
        - With ``dry_run=True`` it computes the diff against the current file WITHOUT
          writing, so the change can be shown to the user for approval first.
        - With ``dry_run=False`` it writes and returns the same diff, plus the previous
          contents (``old_content``) so the caller can keep an undo buffer.

        Protected files (.env, keys, ...) are refused, and the path must resolve inside
        an approved workspace root — both enforced here, not by the model.
        """
        # Check protected patterns first so a blocked edit returns a clean error for the
        # approval UI rather than raising out of path containment validation.
        if self.validator.is_protected(path):
            return {"success": False, "error": f"Protected file: {path}"}
        self.validator.validate(path)

        p = Path(path)
        existed = p.exists()
        if existed and not p.is_file():
            return {"success": False, "error": f"Not a file: {path}"}

        old_content = ""
        if existed:
            size = p.stat().st_size
            if size > self.max_file_size:
                return {"success": False, "error": f"File too large to edit: {size} bytes (max: {self.max_file_size})"}
            try:
                old_content = p.read_text(encoding="utf-8", errors="replace")
            except Exception as e:
                return {"success": False, "error": f"Could not read existing file: {e}"}

        diff_info = compute_unified_diff(old_content, content, path)
        result = {
            "success": True,
            "path": path,
            "dry_run": dry_run,
            "created": not existed,
            "old_content": old_content,
            "unchanged": old_content == content,
            **diff_info,
        }

        if dry_run:
            return result

        if create_parents:
            p.parent.mkdir(parents=True, exist_ok=True)
        if not p.parent.exists():
            return {"success": False, "error": f"Parent directory does not exist: {p.parent}"}

        try:
            p.write_text(content, encoding="utf-8")
            self.audit.log("apply_edit", path, True, {"existed": existed, "size": len(content),
                                                      "additions": diff_info["additions"],
                                                      "deletions": diff_info["deletions"]})
            result["size"] = len(content)
            return result
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def revert_file(
        self,
        path: str,
        original_content: Optional[str] = None,
        was_created: bool = False,
        **kwargs,
    ) -> Dict[str, Any]:
        """Undo a previous ``apply_edit`` using the caller's saved undo buffer.

        - ``was_created=True``: the edit created the file, so reverting deletes it.
        - otherwise ``original_content`` (captured as ``old_content`` from apply_edit)
          is written back verbatim.
        """
        if self.validator.is_protected(path):
            return {"success": False, "error": f"Protected file: {path}"}
        self.validator.validate(path)

        p = Path(path)

        if was_created:
            if p.exists():
                try:
                    p.unlink()
                except Exception as e:
                    return {"success": False, "error": str(e)}
            self.audit.log("revert_file", path, True, {"action": "delete"})
            return {"success": True, "path": path, "reverted": True, "action": "deleted"}

        if original_content is None:
            return {"success": False, "error": "No original content provided to revert to"}

        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(original_content, encoding="utf-8")
            self.audit.log("revert_file", path, True, {"action": "restore", "size": len(original_content)})
            return {"success": True, "path": path, "reverted": True, "action": "restored"}
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
