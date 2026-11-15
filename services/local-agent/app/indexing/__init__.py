"""Expose codebase discovery, symbol extraction, and indexing."""
from app.indexing.discovery import ProjectDiscovery
from app.indexing.symbols import SymbolExtractor
from app.indexing.indexer import CodebaseIndexer

__all__ = ["ProjectDiscovery", "SymbolExtractor", "CodebaseIndexer"]
