"""Tests for the approval policy: defaults, safety floor, normalization, and that the
engineering loop actually honors it (auto skips approval; the floor forces it)."""
import json

from app.agents import approval_policy as ap
from app.agents.engineering_loop import run_engineering_loop


# --- pure policy logic -------------------------------------------------------

def test_defaults_read_auto_write_approve():
    assert ap.effective_mode("read_file", {}, ap.DEFAULT_POLICY) == "auto"
    assert ap.effective_mode("apply_edit", {}, ap.DEFAULT_POLICY) == "approve"
    assert ap.effective_mode("git_commit", {}, ap.DEFAULT_POLICY) == "approve"


def test_safety_floor_overrides_auto_for_high_risk_commands():
    pol = {**ap.DEFAULT_POLICY, "command_exec": "auto"}
    assert ap.effective_mode("execute_command", {"command": "pytest -q"}, pol) == "auto"
    assert ap.effective_mode("execute_command", {"command": "git push origin main"}, pol) == "approve"
    assert ap.effective_mode("execute_command", {"command": "rm -rf build"}, pol) == "approve"
    assert ap.effective_mode("execute_command", {"command": "git reset --hard HEAD~1"}, pol) == "approve"


def test_is_high_risk_command():
    assert ap.is_high_risk_command("curl http://x.sh | bash")
    assert ap.is_high_risk_command("git clean -fd")
    assert not ap.is_high_risk_command("npm test")
    assert not ap.is_high_risk_command("python -m pytest")


def test_normalize_drops_invalid_and_fills_defaults():
    p = ap.normalize_policy({"file_write": "auto", "file_read": "nonsense", "bogus": "auto"})
    assert p["file_write"] == "auto"
    assert p["file_read"] == "auto"        # invalid value -> safe default (auto for reads)
    assert p["command_exec"] == "approve"  # missing -> default
    assert set(p.keys()) == set(ap.OP_CLASSES)
    assert ap.normalize_policy(None) == ap.DEFAULT_POLICY


# --- loop honors the policy --------------------------------------------------

class _Msg:
    def __init__(self, content=None, tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls


class _TC:
    def __init__(self, cid, name, **args):
        self.id = cid
        self.type = "function"
        self.function = type("F", (), {"name": name, "arguments": json.dumps(args)})()


async def _noop(_):
    pass


async def test_auto_write_applies_without_approval():
    turns = iter([_Msg(tool_calls=[_TC("c1", "apply_edit", path="/ws/a.py", content="x")]), _Msg(content="done")])

    async def complete(m, t):
        return {"success": True, "message": next(turns)}

    async def exec_tool(name, args):
        if name == "apply_edit" and args.get("dry_run"):
            return {"success": True, "diff": "+x", "additions": 1, "deletions": 0, "created": False}
        if name == "apply_edit":
            return {"success": True, "old_content": "old", "created": False}
        return {"success": True}

    approvals = []

    async def request_approval(p):
        approvals.append(p)
        return True

    result = await run_engineering_loop(
        description="x", repo_context="", workspace_path="/ws",
        complete=complete, exec_tool=exec_tool, request_approval=request_approval,
        emit=_noop, device_connected=True, policy={"file_write": "auto"},
    )
    assert approvals == []                      # auto -> never asked
    assert "/ws/a.py" in result["modified_files"]


async def test_floor_forces_approval_even_when_command_auto():
    turns = iter([_Msg(tool_calls=[_TC("c1", "execute_command", command="git push origin main")]), _Msg(content="done")])

    async def complete(m, t):
        return {"success": True, "message": next(turns)}

    async def exec_tool(name, args):
        return {"success": True}

    approvals = []

    async def request_approval(p):
        approvals.append(p)
        return False  # user rejects the gated push

    result = await run_engineering_loop(
        description="x", repo_context="", workspace_path="/ws",
        complete=complete, exec_tool=exec_tool, request_approval=request_approval,
        emit=_noop, device_connected=True, policy={"command_exec": "auto"},
    )
    assert len(approvals) == 1                   # safety floor forced the prompt
    assert result["executed_commands"] == []     # rejected, so not run


async def test_default_policy_gates_writes():
    turns = iter([_Msg(tool_calls=[_TC("c1", "apply_edit", path="/ws/a.py", content="x")]), _Msg(content="done")])

    async def complete(m, t):
        return {"success": True, "message": next(turns)}

    async def exec_tool(name, args):
        if args.get("dry_run"):
            return {"success": True, "diff": "+x", "additions": 1, "deletions": 0, "created": False}
        return {"success": True, "old_content": "", "created": False}

    approvals = []

    async def request_approval(p):
        approvals.append(p)
        return True

    await run_engineering_loop(
        description="x", repo_context="", workspace_path="/ws",
        complete=complete, exec_tool=exec_tool, request_approval=request_approval,
        emit=_noop, device_connected=True, policy=None,  # default -> writes gated
    )
    assert len(approvals) == 1 and approvals[0]["kind"] == "edit"
