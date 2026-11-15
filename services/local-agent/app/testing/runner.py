"""Test runner with framework auto-detection."""
import logging
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class TestRunner:
    """Run tests, linters, and builds."""

    def __init__(self, executor):
        self.executor = executor

    async def discover(self, project_path: str, **kwargs) -> Dict[str, Any]:
        """Discover test framework and test files."""
        p = Path(project_path)
        frameworks = []

        # Python - pytest
        if (p / "pytest.ini").exists() or (p / "pyproject.toml").exists() or (p / "setup.cfg").exists():
            test_files = list(p.rglob("test_*.py")) + list(p.rglob("*_test.py"))
            if test_files or (p / "tests").exists():
                frameworks.append({
                    "name": "pytest",
                    "language": "python",
                    "command": "pytest",
                    "test_files": [str(f.relative_to(p)) for f in test_files[:20]],
                })

        # JavaScript - jest/vitest/mocha
        pkg_json = p / "package.json"
        if pkg_json.exists():
            import json
            try:
                pkg = json.loads(pkg_json.read_text(encoding="utf-8"))
                scripts = pkg.get("scripts", {})
                deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}

                if "vitest" in deps:
                    frameworks.append({"name": "vitest", "language": "javascript", "command": "npx vitest run"})
                elif "jest" in deps:
                    frameworks.append({"name": "jest", "language": "javascript", "command": "npx jest"})
                elif "mocha" in deps:
                    frameworks.append({"name": "mocha", "language": "javascript", "command": "npx mocha"})
                elif "test" in scripts:
                    frameworks.append({"name": "npm-test", "language": "javascript", "command": "npm test"})
            except Exception:
                pass

        # Go
        if list(p.rglob("*_test.go")):
            frameworks.append({"name": "go-test", "language": "go", "command": "go test ./..."})

        # Rust
        if (p / "Cargo.toml").exists():
            frameworks.append({"name": "cargo-test", "language": "rust", "command": "cargo test"})

        return {
            "success": True,
            "project_path": project_path,
            "frameworks": frameworks,
            "has_tests": len(frameworks) > 0,
        }

    async def run_tests(self, project_path: str, test_command: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Run tests."""
        if not test_command:
            discovery = await self.discover(project_path)
            if discovery.get("frameworks"):
                test_command = discovery["frameworks"][0]["command"]
            else:
                return {"success": False, "error": "No test framework detected", "status": "no_tests"}

        result = await self.executor.execute(test_command, cwd=project_path, timeout=300)
        result["test_command"] = test_command
        return result

    async def run_linter(self, project_path: str, linter_command: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Run linter."""
        if not linter_command:
            p = Path(project_path)
            if (p / "package.json").exists():
                linter_command = "npx eslint . --max-warnings 0"
            elif (p / "pyproject.toml").exists():
                linter_command = "ruff check ."
            else:
                return {"success": False, "error": "No linter detected"}

        return await self.executor.execute(linter_command, cwd=project_path, timeout=120)

    async def run_build(self, project_path: str, build_command: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Run build."""
        if not build_command:
            p = Path(project_path)
            if (p / "package.json").exists():
                build_command = "npm run build"
            elif (p / "Cargo.toml").exists():
                build_command = "cargo build"
            else:
                return {"success": False, "error": "No build system detected"}

        return await self.executor.execute(build_command, cwd=project_path, timeout=600)
