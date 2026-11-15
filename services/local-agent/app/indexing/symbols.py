"""AST-assisted symbol extractor for code understanding."""
import ast
import re
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class SymbolExtractor:
    """Extracts classes, methods, functions, and imports from source code."""

    @staticmethod
    def extract_python_symbols(code: str, file_path: str = "") -> List[Dict[str, Any]]:
        """Parse Python AST to extract function and class declarations."""
        symbols = []
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                    args = [a.arg for a in node.args.args]
                    symbols.append({
                        "name": node.name,
                        "kind": "async_function" if isinstance(node, ast.AsyncFunctionDef) else "function",
                        "line": node.lineno,
                        "file": file_path,
                        "parameters": args,
                        "docstring": ast.get_docstring(node),
                    })
                elif isinstance(node, ast.ClassDef):
                    symbols.append({
                        "name": node.name,
                        "kind": "class",
                        "line": node.lineno,
                        "file": file_path,
                        "docstring": ast.get_docstring(node),
                    })
        except SyntaxError:
            # Fallback to regex symbol extraction for incomplete or non-standard syntax
            symbols.extend(SymbolExtractor._regex_fallback(code, file_path, is_python=True))
        return symbols

    @staticmethod
    def extract_typescript_symbols(code: str, file_path: str = "") -> List[Dict[str, Any]]:
        """Extract functions, classes, interfaces and export declarations in TS/JS."""
        symbols = []
        lines = code.splitlines()

        # Regular expressions for common TypeScript/JavaScript patterns
        patterns = [
            (r"export\s+class\s+([A-Za-z0-9_]+)", "class"),
            (r"class\s+([A-Za-z0-9_]+)", "class"),
            (r"export\s+interface\s+([A-Za-z0-9_]+)", "interface"),
            (r"interface\s+([A-Za-z0-9_]+)", "interface"),
            (r"export\s+type\s+([A-Za-z0-9_]+)", "type"),
            (r"export\s+(?:async\s+)?function\s+([A-Za-z0-9_]+)", "function"),
            (r"const\s+([A-Za-z0-9_]+)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>", "arrow_function"),
            (r"export\s+const\s+([A-Za-z0-9_]+)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>", "arrow_function"),
        ]

        for i, line in enumerate(lines, 1):
            for regex, kind in patterns:
                match = re.search(regex, line)
                if match:
                    symbols.append({
                        "name": match.group(1),
                        "kind": kind,
                        "line": i,
                        "file": file_path,
                        "signature": line.strip()[:100],
                    })
                    break

        return symbols

    @staticmethod
    def _regex_fallback(code: str, file_path: str, is_python: bool) -> List[Dict[str, Any]]:
        symbols = []
        pattern = r"def\s+([A-Za-z0-9_]+)\s*\(" if is_python else r"function\s+([A-Za-z0-9_]+)\s*\("
        for i, line in enumerate(code.splitlines(), 1):
            m = re.search(pattern, line)
            if m:
                symbols.append({
                    "name": m.group(1),
                    "kind": "function",
                    "line": i,
                    "file": file_path,
                })
        return symbols
