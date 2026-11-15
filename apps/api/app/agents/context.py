"""Build a compact, safe snapshot of the active workspace so the agent can reason
about the user's ACTUAL code instead of asking them to describe it.

Safety: everything is read strictly within the resolved workspace root (path
containment), heavy/noise directories are skipped, and both per-file and total
output are size-capped so the snapshot can't blow up the model context.
"""
import os
from pathlib import Path
from typing import List

# Directories that are noise or huge — never descend into these.
SKIP_DIRS = {
    "node_modules", ".git", "venv", ".venv", "env", "__pycache__", "dist", "build",
    ".next", ".turbo", ".nuxt", "coverage", ".idea", ".vscode", "site-packages",
    ".pytest_cache", ".mypy_cache", "target", "bin", "obj", ".cache", "out", "vendor",
}

# Files worth reading in full (capped) to understand a project at a glance.
KEY_FILES = {
    "readme.md", "readme", "readme.txt",
    "package.json", "requirements.txt", "pyproject.toml", "setup.py", "setup.cfg",
    "go.mod", "cargo.toml", "pom.xml", "build.gradle", "composer.json", "gemfile",
    "next.config.ts", "next.config.js", "vite.config.ts", "tsconfig.json",
    "dockerfile", "docker-compose.yml", "docker-compose.yaml", ".env.example",
    "makefile", "pubspec.yaml", "cargo.toml",
}

MAX_TREE_ENTRIES = 300
MAX_DEPTH = 3
MAX_FILE_BYTES = 3500
MAX_TOTAL_BYTES = 14000


def _is_contained(child: Path, root: Path) -> bool:
    try:
        child.resolve().relative_to(root)
        return True
    except Exception:
        return False


def build_repo_context(root_path: str) -> str:
    """Return a text snapshot (structure + key files) of the workspace, or "" if unreadable."""
    if not root_path or root_path == ".":
        return ""
    try:
        root = Path(root_path).resolve()
    except Exception:
        return ""
    if not root.exists() or not root.is_dir():
        return ""

    lines: List[str] = [f"PROJECT ROOT: {root}", "", "STRUCTURE (directories and files, truncated):"]

    # 1) Bounded directory tree.
    entries = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS and not d.startswith("."))
        rel = os.path.relpath(dirpath, root)
        depth = 0 if rel == "." else rel.count(os.sep) + 1
        if depth > MAX_DEPTH:
            dirnames[:] = []
            continue
        indent = "  " * depth
        if rel != ".":
            lines.append(f"{indent}{os.path.basename(dirpath)}/")
            entries += 1
        for f in sorted(filenames)[:40]:
            lines.append(f"{indent}  {f}")
            entries += 1
            if entries >= MAX_TREE_ENTRIES:
                break
        if entries >= MAX_TREE_ENTRIES:
            lines.append("  … (structure truncated)")
            break

    # 2) Key files, read in full (capped), within containment and total budget.
    lines.append("")
    lines.append("KEY FILES:")
    total = 0
    seen = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        rel = os.path.relpath(dirpath, root)
        depth = 0 if rel == "." else rel.count(os.sep) + 1
        if depth > MAX_DEPTH:
            dirnames[:] = []
            continue
        for f in sorted(filenames):
            if f.lower() not in KEY_FILES and not f.lower().startswith("readme"):
                continue
            p = Path(dirpath) / f
            if not _is_contained(p, root):
                continue
            try:
                data = p.read_text(encoding="utf-8", errors="ignore")[:MAX_FILE_BYTES]
            except Exception:
                continue
            relf = os.path.relpath(p, root)
            block = f"\n--- {relf} ---\n{data.strip()}\n"
            if total + len(block) > MAX_TOTAL_BYTES:
                lines.append("… (key-file context truncated — budget reached)")
                return "\n".join(lines)
            total += len(block)
            seen += 1
            lines.append(block)

    if seen == 0:
        lines.append("(no README/manifest files found at the top levels)")
    return "\n".join(lines)
