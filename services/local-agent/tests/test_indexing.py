"""Tests for the codebase indexer's stats + search."""
from app.indexing.indexer import CodebaseIndexer


def test_index_stats_and_search(tmp_path):
    (tmp_path / "a.py").write_text("def foo():\n    return 1\n\nclass Bar:\n    pass\n")
    (tmp_path / "b.ts").write_text("export function baz() { return 2 }\n")
    db = tmp_path / "idx.db"

    idx = CodebaseIndexer(db_path=str(db))
    res = idx.index_workspace(str(tmp_path))
    assert res["success"] is True
    assert res["indexed_files"] == 2

    stats = idx.index_stats()
    assert stats["success"] is True
    assert stats["files"] == 2
    assert stats["symbols"] >= 2          # at least foo() and Bar
    assert stats["total_lines"] >= 4
    langs = {l["language"] for l in stats["languages"]}
    assert ".py" in langs and ".ts" in langs

    hits = idx.search_symbols("foo")
    assert any(h["name"] == "foo" for h in hits)

    # A re-run with no changes indexes nothing new but stats are unchanged.
    res2 = idx.index_workspace(str(tmp_path))
    assert res2["indexed_files"] == 0
    assert idx.index_stats()["files"] == 2
