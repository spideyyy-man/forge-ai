"""Tests for the real verify -> self-repair wiring in the workflow."""
import pytest

import app.agents.workflow as wf


@pytest.fixture
def base_state():
    return {
        "task_id": "t", "user_id": "u", "device_id": "dev", "workspace_path": "/ws",
        "description": "do it", "modified_files": ["/ws/a.py"], "retry_count": 0, "max_retries": 2,
    }


async def test_verification_skipped_when_no_files_changed(monkeypatch, base_state):
    base_state["modified_files"] = []
    called = {"n": 0}

    async def fake_exec(*a, **k):
        called["n"] += 1
        return {"success": True}

    monkeypatch.setattr(wf, "execute_remote_tool", fake_exec)
    out = await wf.verification_node(base_state)
    assert out["verification_passed"] is True
    assert called["n"] == 0  # no tests run when nothing changed


async def test_verification_skipped_when_no_framework(monkeypatch, base_state):
    async def fake_exec(device_id, tool, args):
        return {"success": False, "error": "No test framework detected", "status": "no_tests"}

    monkeypatch.setattr(wf, "execute_remote_tool", fake_exec)
    out = await wf.verification_node(base_state)
    # A valid change is not failed just because the project has no tests.
    assert out["verification_passed"] is True


async def test_verification_fails_and_captures_output(monkeypatch, base_state):
    async def fake_exec(device_id, tool, args):
        assert tool == "run_tests"
        return {"success": False, "exit_code": 1, "test_command": "pytest",
                "stdout": "collected 2 items\n", "stderr": "E   assert 1 == 2\n"}

    monkeypatch.setattr(wf, "execute_remote_tool", fake_exec)
    out = await wf.verification_node(base_state)
    assert out["verification_passed"] is False
    assert "assert 1 == 2" in out["error"]
    assert "pytest" in out["error"]


async def test_verification_passes_on_green_tests(monkeypatch, base_state):
    async def fake_exec(device_id, tool, args):
        return {"success": True, "exit_code": 0, "test_command": "pytest", "stdout": "2 passed\n"}

    monkeypatch.setattr(wf, "execute_remote_tool", fake_exec)
    out = await wf.verification_node(base_state)
    assert out["verification_passed"] is True
    assert out["error"] is None


def test_should_repair_routing():
    assert wf.should_repair({"verification_passed": True}) == "completed"
    assert wf.should_repair({"verification_passed": False, "retry_count": 0, "max_retries": 2}) == "repair"
    assert wf.should_repair({"verification_passed": False, "retry_count": 2, "max_retries": 2}) == "completed"


async def test_repair_node_sets_repair_context():
    out = await wf.repair_node({"retry_count": 0, "max_retries": 2, "error": "boom: tests failed"})
    assert out["retry_count"] == 1
    assert out["repair_context"] == "boom: tests failed"
