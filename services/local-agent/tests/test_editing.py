"""Tests for the approval-gated editing primitives (apply_edit / revert_file / git rollback)."""
import pytest
from pathlib import Path

from app.config import AgentConfig
from app.security.path_validator import PathValidator
from app.security.audit import AuditLogger
from app.filesystem.operations import FileSystemOperations, compute_unified_diff
from app.git_ops.operations import GitOperations


def _fs(tmp_path: Path) -> FileSystemOperations:
    validator = PathValidator([str(tmp_path)])
    audit = AuditLogger(log_path=tmp_path / "audit.jsonl")
    return FileSystemOperations(validator, audit, AgentConfig())


def test_compute_unified_diff_counts():
    info = compute_unified_diff("a\nb\nc\n", "a\nB\nc\nd\n", "x.txt")
    assert info["additions"] == 2   # 'B' and 'd'
    assert info["deletions"] == 1   # 'b'
    assert "+B" in info["diff"] and "-b" in info["diff"]


async def test_apply_edit_dry_run_does_not_write(tmp_path: Path):
    fs = _fs(tmp_path)
    target = tmp_path / "mod.py"
    target.write_text("print('old')\n", encoding="utf-8")

    res = await fs.apply_edit(str(target), "print('new')\n", dry_run=True)
    assert res["success"] is True
    assert res["dry_run"] is True
    assert res["additions"] == 1 and res["deletions"] == 1
    assert res["created"] is False
    # File on disk is untouched by a dry run.
    assert target.read_text(encoding="utf-8") == "print('old')\n"


async def test_apply_edit_writes_and_returns_undo_buffer(tmp_path: Path):
    fs = _fs(tmp_path)
    target = tmp_path / "mod.py"
    target.write_text("print('old')\n", encoding="utf-8")

    res = await fs.apply_edit(str(target), "print('new')\n", dry_run=False)
    assert res["success"] is True
    assert res["old_content"] == "print('old')\n"
    assert target.read_text(encoding="utf-8") == "print('new')\n"

    # Revert using the captured undo buffer restores the original bytes.
    rev = await fs.revert_file(str(target), original_content=res["old_content"])
    assert rev["success"] is True and rev["action"] == "restored"
    assert target.read_text(encoding="utf-8") == "print('old')\n"


async def test_apply_edit_new_file_then_revert_deletes(tmp_path: Path):
    fs = _fs(tmp_path)
    target = tmp_path / "pkg" / "new_file.py"

    res = await fs.apply_edit(str(target), "x = 1\n", dry_run=False)
    assert res["success"] is True and res["created"] is True
    assert target.exists()

    rev = await fs.revert_file(str(target), was_created=True)
    assert rev["success"] is True and rev["action"] == "deleted"
    assert not target.exists()


async def test_apply_edit_refuses_protected_file(tmp_path: Path):
    fs = _fs(tmp_path)
    env = tmp_path / ".env"
    env.write_text("SECRET=1\n", encoding="utf-8")

    res = await fs.apply_edit(str(env), "SECRET=hacked\n")
    assert res["success"] is False
    assert "protected" in res["error"].lower()
    # Untouched.
    assert env.read_text(encoding="utf-8") == "SECRET=1\n"


async def test_apply_edit_rejects_path_outside_workspace(tmp_path: Path):
    fs = _fs(tmp_path)
    outside = tmp_path.parent / "escape.txt"
    with pytest.raises(PermissionError):
        await fs.apply_edit(str(outside), "nope\n")


async def test_git_checkpoint_and_rollback(tmp_path: Path):
    from git import Repo

    repo = Repo.init(tmp_path)
    with repo.config_writer() as cw:
        cw.set_value("user", "name", "Test")
        cw.set_value("user", "email", "test@example.com")

    tracked = tmp_path / "app.py"
    tracked.write_text("print('v1')\n", encoding="utf-8")
    repo.index.add(["app.py"])
    base = repo.index.commit("initial")

    validator = PathValidator([str(tmp_path)])
    audit = AuditLogger(log_path=tmp_path / "audit.jsonl")
    git_ops = GitOperations(validator, audit)

    # Agent changes the file and checkpoints it.
    tracked.write_text("print('v2-broken')\n", encoding="utf-8")
    ckpt = await git_ops.create_checkpoint(str(tmp_path), "[FORGE AI] after edit")
    assert ckpt["success"] is True and ckpt["created"] is True

    # Roll back to the pre-edit commit; working tree returns to v1.
    rb = await git_ops.rollback(str(tmp_path), base.hexsha)
    assert rb["success"] is True
    assert tracked.read_text(encoding="utf-8") == "print('v1')\n"
