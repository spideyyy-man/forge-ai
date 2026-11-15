"""Git operations."""
import logging
from typing import Optional, Dict, Any, List
from pathlib import Path

from app.security.path_validator import PathValidator
from app.security.audit import AuditLogger

logger = logging.getLogger(__name__)


class GitOperations:
    """Git operations with security validation."""

    def __init__(self, path_validator: PathValidator, audit_logger: AuditLogger):
        self.validator = path_validator
        self.audit = audit_logger

    def _get_repo(self, repo_path: str):
        """Get a git.Repo object."""
        try:
            from git import Repo, InvalidGitRepositoryError
            return Repo(repo_path)
        except ImportError:
            raise RuntimeError("GitPython not installed")
        except Exception as e:
            raise ValueError(f"Not a git repository: {repo_path} - {e}")

    async def status(self, repo_path: str, **kwargs) -> Dict[str, Any]:
        """Get git status."""
        self.validator.validate(repo_path)
        try:
            repo = self._get_repo(repo_path)
            branch_name = "HEAD detached"
            try:
                if not repo.head.is_detached:
                    branch_name = str(repo.active_branch)
            except TypeError:
                branch_name = "unknown"

            staged_files = []
            try:
                if repo.head.is_valid():
                    staged_files = [item.a_path for item in repo.index.diff("HEAD")][:50]
            except Exception:
                pass

            return {
                "success": True,
                "branch": branch_name,
                "is_dirty": repo.is_dirty(),
                "untracked_files": repo.untracked_files[:50],
                "changed_files": [item.a_path for item in repo.index.diff(None)][:50],
                "staged_files": staged_files,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def diff(self, repo_path: str, staged: bool = False, file: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Get git diff."""
        self.validator.validate(repo_path)
        try:
            repo = self._get_repo(repo_path)
            if staged:
                diff_text = repo.git.diff("--staged", file) if file else repo.git.diff("--staged")
            else:
                diff_text = repo.git.diff(file) if file else repo.git.diff()
            return {"success": True, "diff": diff_text}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def log(self, repo_path: str, limit: int = 20, file: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Get git log."""
        self.validator.validate(repo_path)
        try:
            repo = self._get_repo(repo_path)
            commits = []
            for commit in repo.iter_commits(max_count=limit, paths=file):
                commits.append({
                    "hash": commit.hexsha[:8],
                    "full_hash": commit.hexsha,
                    "message": commit.message.strip(),
                    "author": str(commit.author),
                    "date": commit.committed_datetime.isoformat(),
                })
            return {"success": True, "commits": commits}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def branch(self, repo_path: str, **kwargs) -> Dict[str, Any]:
        """List branches."""
        self.validator.validate(repo_path)
        try:
            repo = self._get_repo(repo_path)
            current = "HEAD"
            try:
                if not repo.head.is_detached:
                    current = str(repo.active_branch)
            except TypeError:
                pass
            branches = [str(b) for b in repo.branches]
            return {"success": True, "current": current, "branches": branches}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def checkout(self, repo_path: str, branch_name: str, create: bool = False, **kwargs) -> Dict[str, Any]:
        """Checkout a branch."""
        self.validator.validate(repo_path)
        try:
            repo = self._get_repo(repo_path)
            if create:
                repo.git.checkout("-b", branch_name)
            else:
                repo.git.checkout(branch_name)
            self.audit.log("git_checkout", repo_path, True, {"branch": branch_name})
            return {"success": True, "branch": branch_name}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def commit(self, repo_path: str, message: str, files: Optional[List[str]] = None, **kwargs) -> Dict[str, Any]:
        """Create a git commit."""
        self.validator.validate(repo_path)
        try:
            repo = self._get_repo(repo_path)
            if files:
                repo.index.add(files)
            else:
                repo.git.add("-A")
            commit = repo.index.commit(message)
            self.audit.log("git_commit", repo_path, True, {"hash": commit.hexsha[:8]})
            return {"success": True, "hash": commit.hexsha[:8], "message": message}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def create_checkpoint(self, repo_path: str, message: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Create a checkpoint commit."""
        msg = message or f"[FORGE AI] Checkpoint"
        return await self.commit(repo_path, msg)
