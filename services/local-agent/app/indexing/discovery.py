"""Codebase discovery: language classification, frameworks, and dependency parsing."""
import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

LANGUAGE_EXTENSIONS = {
    ".py": "Python",
    ".ts": "TypeScript",
    ".tsx": "TypeScript (React)",
    ".js": "JavaScript",
    ".jsx": "JavaScript (React)",
    ".go": "Go",
    ".rs": "Rust",
    ".java": "Java",
    ".cpp": "C++",
    ".c": "C",
    ".cs": "C#",
    ".rb": "Ruby",
    ".php": "PHP",
    ".html": "HTML",
    ".css": "CSS",
    ".sql": "SQL",
}

IGNORED_DIRS = {".git", "node_modules", ".next", "venv", "__pycache__", "dist", "build", ".venv"}


class ProjectDiscovery:
    """Discovers project structure, programming languages, and frameworks."""

    @staticmethod
    def inspect_repository(root_path: str) -> Dict[str, Any]:
        """Scan repository and extract architectural metadata."""
        root = Path(root_path)
        if not root.exists() or not root.is_dir():
            return {"success": False, "error": f"Invalid path: {root_path}"}

        languages_count: Dict[str, int] = {}
        detected_frameworks: List[str] = []
        dependencies: Dict[str, str] = {}
        total_files = 0

        # Scan files
        for current_root, dirs, files in os.walk(root):
            # Prune ignored directories
            dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]

            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in LANGUAGE_EXTENSIONS:
                    lang = LANGUAGE_EXTENSIONS[ext]
                    languages_count[lang] = languages_count.get(lang, 0) + 1
                    total_files += 1

        # Check Node.js / React / Next.js
        pkg_json = root / "package.json"
        if pkg_json.exists():
            try:
                pkg_data = json.loads(pkg_json.read_text(encoding="utf-8"))
                deps = {**pkg_data.get("dependencies", {}), **pkg_data.get("devDependencies", {})}
                dependencies.update(deps)

                if "next" in deps:
                    detected_frameworks.append("Next.js")
                if "react" in deps:
                    detected_frameworks.append("React")
                if "express" in deps:
                    detected_frameworks.append("Express.js")
                if "tailwindcss" in deps:
                    detected_frameworks.append("Tailwind CSS")
                if "vue" in deps:
                    detected_frameworks.append("Vue.js")
            except Exception as e:
                logger.warning(f"Failed parsing package.json: {e}")

        # Check Python / FastAPI / Django / Flask
        req_txt = root / "requirements.txt"
        pyproject = root / "pyproject.toml"
        if req_txt.exists():
            try:
                content = req_txt.read_text(encoding="utf-8")
                if "fastapi" in content.lower():
                    detected_frameworks.append("FastAPI")
                if "django" in content.lower():
                    detected_frameworks.append("Django")
                if "flask" in content.lower():
                    detected_frameworks.append("Flask")
                if "langgraph" in content.lower():
                    detected_frameworks.append("LangGraph")
            except Exception:
                pass

        if pyproject.exists():
            detected_frameworks.append("Poetry / PyProject")

        # Check Rust / Cargo
        if (root / "Cargo.toml").exists():
            detected_frameworks.append("Cargo / Rust")

        # Check Go
        if (root / "go.mod").exists():
            detected_frameworks.append("Go Modules")

        sorted_languages = sorted(languages_count.items(), key=lambda x: x[1], reverse=True)

        return {
            "success": True,
            "root_path": str(root),
            "total_source_files": total_files,
            "languages": [{"language": lang, "file_count": count} for lang, count in sorted_languages],
            "frameworks": list(set(detected_frameworks)),
            "dependencies_sample": list(dependencies.keys())[:30],
        }
