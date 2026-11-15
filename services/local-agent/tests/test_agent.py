"""Unit tests for FORGE AI Local Agent components."""
import pytest
import asyncio
from pathlib import Path

from app.config import AgentConfig
from app.tools.registry import ToolRegistry
from app.security.path_validator import PathValidator
from app.security.command_policy import CommandPolicy, CommandRisk
from app.security.audit import AuditLogger
from app.filesystem.operations import FileSystemOperations
from app.diagnostics.collector import DiagnosticCollector
from app.terminal.process_manager import ProcessManager
from app.terminal.executor import CommandExecutor


@pytest.mark.asyncio
async def test_tool_registry():
    registry = ToolRegistry()
    
    async def sample_tool(a: int, b: int):
        return a + b

    registry.register("add", sample_tool)
    assert "add" in registry.list_tools()
    
    res = await registry.execute("add", {"a": 2, "b": 3})
    assert res == 5
    
    metrics = registry.get_metrics()
    assert metrics["add"]["calls"] == 1


@pytest.mark.asyncio
async def test_path_validator_and_filesystem(tmp_path: Path):
    validator = PathValidator([str(tmp_path)])
    audit = AuditLogger(log_path=tmp_path / "audit.jsonl")
    config = AgentConfig()
    
    fs = FileSystemOperations(validator, audit, config)
    
    # Create file
    test_file = tmp_path / "hello.txt"
    create_res = await fs.create_file(str(test_file), "Hello World!")
    assert create_res["success"] is True
    
    # Read file
    read_res = await fs.read_file(str(test_file))
    assert read_res["success"] is True
    assert read_res["content"] == "Hello World!"
    
    # List directory
    list_res = await fs.list_directory(str(tmp_path))
    assert list_res["success"] is True
    assert list_res["count"] >= 1
    
    # Delete file
    del_res = await fs.delete_file(str(test_file))
    assert del_res["success"] is True
    assert not test_file.exists()


@pytest.mark.asyncio
async def test_command_policy_and_executor(tmp_path: Path):
    policy = CommandPolicy(max_allowed_risk=CommandRisk.MEDIUM)
    audit = AuditLogger(log_path=tmp_path / "audit.jsonl")
    config = AgentConfig()
    executor = CommandExecutor(policy, audit, config)
    
    # Safe/Low risk command
    res = await executor.execute("python --version")
    assert res["success"] is True
    
    # Critical command blocked
    blocked_res = await executor.execute("sudo rm -rf /")
    assert blocked_res["success"] is False
    assert "blocked" in blocked_res["error"].lower()


@pytest.mark.asyncio
async def test_diagnostics():
    config = AgentConfig()
    collector = DiagnosticCollector(config)
    diag = await collector.collect()
    
    assert diag["success"] is True
    assert "system" in diag
    assert "resources" in diag
    assert "tools" in diag


@pytest.mark.asyncio
async def test_process_manager():
    pm = ProcessManager()
    proc_list = await pm.list_processes()
    assert proc_list["success"] is True
    assert len(proc_list["processes"]) > 0
