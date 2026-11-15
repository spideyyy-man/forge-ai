"""Incremental codebase indexer with SQLite persistence."""
import os
import sqlite3
import hashlib
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from app.indexing.discovery import ProjectDiscovery, IGNORED_DIRS
from app.indexing.symbols import SymbolExtractor

logger = logging.getLogger(__name__)


class CodebaseIndexer:
    """Indexes source files, tracks content hashes, and enables rapid symbol retrieval."""

    def __init__(self, db_path: str = ".forge_index.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS file_index (
                    file_path TEXT PRIMARY KEY,
                    content_hash TEXT,
                    language TEXT,
                    line_count INTEGER,
                    updated_at REAL
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS symbol_index (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    kind TEXT,
                    file_path TEXT,
                    line INTEGER,
                    signature TEXT,
                    FOREIGN KEY (file_path) REFERENCES file_index(file_path) ON DELETE CASCADE
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_symbol_name ON symbol_index (name)")
            conn.commit()

    @staticmethod
    def _compute_hash(content: str) -> str:
        return hashlib.sha256(content.encode("utf-8", errors="ignore")).hexdigest()

    def index_workspace(self, root_path: str, force_reindex: bool = False) -> Dict[str, Any]:
        """Incrementally index workspace files, only reprocessing modified files."""
        root = Path(root_path)
        if not root.exists() or not root.is_dir():
            return {"success": False, "error": f"Invalid path: {root_path}"}

        discovery = ProjectDiscovery.inspect_repository(root_path)

        indexed_files = 0
        skipped_files = 0
        extracted_symbols_total = 0

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            for current_root, dirs, files in os.walk(root):
                dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]

                for file in files:
                    ext = os.path.splitext(file)[1].lower()
                    if ext not in [".py", ".ts", ".tsx", ".js", ".jsx"]:
                        continue

                    full_path = str(Path(current_root) / file)
                    rel_path = os.path.relpath(full_path, root_path)

                    try:
                        content = Path(full_path).read_text(encoding="utf-8", errors="ignore")
                    except Exception:
                        continue

                    content_hash = self._compute_hash(content)

                    # Check if unchanged
                    cursor.execute("SELECT content_hash FROM file_index WHERE file_path = ?", (rel_path,))
                    row = cursor.fetchone()

                    if row and row[0] == content_hash and not force_reindex:
                        skipped_files += 1
                        continue

                    # Delete existing symbols for updated file
                    cursor.execute("DELETE FROM symbol_index WHERE file_path = ?", (rel_path,))

                    # Extract symbols
                    symbols = []
                    if ext == ".py":
                        symbols = SymbolExtractor.extract_python_symbols(content, rel_path)
                    elif ext in [".ts", ".tsx", ".js", ".jsx"]:
                        symbols = SymbolExtractor.extract_typescript_symbols(content, rel_path)

                    for sym in symbols:
                        cursor.execute(
                            "INSERT INTO symbol_index (name, kind, file_path, line, signature) VALUES (?, ?, ?, ?, ?)",
                            (sym["name"], sym["kind"], rel_path, sym["line"], sym.get("signature", "")),
                        )
                        extracted_symbols_total += 1

                    line_count = len(content.splitlines())
                    cursor.execute(
                        """INSERT OR REPLACE INTO file_index (file_path, content_hash, language, line_count, updated_at)
                           VALUES (?, ?, ?, ?, datetime('now'))""",
                        (rel_path, content_hash, ext, line_count),
                    )
                    indexed_files += 1

            conn.commit()

        return {
            "success": True,
            "root_path": root_path,
            "indexed_files": indexed_files,
            "unmodified_skipped_files": skipped_files,
            "symbols_extracted": extracted_symbols_total,
            "architecture": discovery,
        }

    def search_symbols(self, query: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Search symbol index across codebase."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT name, kind, file_path, line, signature 
                   FROM symbol_index 
                   WHERE name LIKE ? 
                   ORDER BY length(name) ASC LIMIT ?""",
                (f"%{query}%", limit),
            )
            rows = cursor.fetchall()

            return [
                {
                    "name": r[0],
                    "kind": r[1],
                    "file_path": r[2],
                    "line": r[3],
                    "signature": r[4],
                }
                for r in rows
            ]
