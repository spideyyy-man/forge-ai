"""FORGE AI Local Workspace Agent — Main entry point."""
import asyncio
import signal
import logging
from typing import Optional

from app.config import AgentConfig
from app.connection.websocket_client import WebSocketClient
from app.tools.registry import ToolRegistry
from app.filesystem.operations import FileSystemOperations
from app.terminal.executor import CommandExecutor
from app.terminal.session import SessionManager
from app.terminal.process_manager import ProcessManager
from app.git_ops.operations import GitOperations
from app.search.text_search import TextSearch
from app.search.file_search import FileSearch
from app.testing.runner import TestRunner
from app.diagnostics.collector import DiagnosticCollector
from app.indexing.discovery import ProjectDiscovery
from app.indexing.indexer import CodebaseIndexer
from app.security.path_validator import PathValidator
from app.security.command_policy import CommandPolicy
from app.security.audit import AuditLogger
from app.logging_config.setup import setup_logging

logger = logging.getLogger(__name__)


class ForgeAgent:
    """Main FORGE AI Local Workspace Agent."""

    def __init__(self, config_path: str = "forge-agent.toml", server_url: Optional[str] = None, debug: bool = False):
        self.config = AgentConfig.load(config_path)
        if server_url:
            self.config.server_url = server_url
        if debug:
            self.config.log_level = "DEBUG"

        setup_logging(self.config.log_level)

        # Initialize security
        self.path_validator = PathValidator(self.config.approved_workspaces)
        self.command_policy = CommandPolicy()
        self.audit_logger = AuditLogger()

        # Initialize operations
        self.fs_ops = FileSystemOperations(self.path_validator, self.audit_logger, self.config)
        self.cmd_executor = CommandExecutor(self.command_policy, self.audit_logger, self.config)
        self.session_manager = SessionManager(self.config)
        self.process_manager = ProcessManager()
        self.git_ops = GitOperations(self.path_validator, self.audit_logger)
        self.text_search = TextSearch(self.path_validator)
        self.file_search = FileSearch(self.path_validator)
        self.test_runner = TestRunner(self.cmd_executor)
        self.diagnostics = DiagnosticCollector(self.config)
        self.indexer = CodebaseIndexer()

        # Initialize tool registry
        self.tool_registry = ToolRegistry()
        self._register_tools()

        # Resolve device credentials: explicit config wins, otherwise fall back to
        # the encrypted token store written during pairing (`run.py --pair`).
        self.device_id = self.config.device_id
        self.auth_token = self.config.auth_token
        if not self.auth_token:
            try:
                from app.authentication import token_store
                stored = token_store.load_token()
                if stored and stored.get("auth_token"):
                    self.device_id = stored.get("device_id", self.device_id)
                    self.auth_token = stored["auth_token"]
            except Exception as exc:
                logger.warning(f"Could not read stored credentials: {exc}")

        # WebSocket client
        self.ws_client = WebSocketClient(
            server_url=self.config.server_url,
            device_id=self.device_id,
            auth_token=self.auth_token,
            on_message=self._handle_message,
            heartbeat_interval=self.config.heartbeat_interval,
            max_reconnect_delay=self.config.max_reconnect_delay,
        )

        self._shutdown_event = asyncio.Event()

    def _register_tools(self):
        """Register all available tools."""
        # Filesystem tools
        self.tool_registry.register("list_directory", self.fs_ops.list_directory)
        self.tool_registry.register("read_file", self.fs_ops.read_file)
        self.tool_registry.register("write_file", self.fs_ops.write_file)
        self.tool_registry.register("create_file", self.fs_ops.create_file)
        self.tool_registry.register("create_directory", self.fs_ops.create_directory)
        self.tool_registry.register("rename_file", self.fs_ops.rename_file)
        self.tool_registry.register("move_file", self.fs_ops.move_file)
        self.tool_registry.register("delete_file", self.fs_ops.delete_file)
        self.tool_registry.register("get_file_metadata", self.fs_ops.get_file_metadata)

        # Terminal tools
        self.tool_registry.register("execute_command", self.cmd_executor.execute)
        self.tool_registry.register("list_processes", self.process_manager.list_processes)

        # Git tools
        self.tool_registry.register("git_status", self.git_ops.status)
        self.tool_registry.register("git_diff", self.git_ops.diff)
        self.tool_registry.register("git_log", self.git_ops.log)
        self.tool_registry.register("git_branch", self.git_ops.branch)
        self.tool_registry.register("git_checkout", self.git_ops.checkout)
        self.tool_registry.register("git_commit", self.git_ops.commit)
        self.tool_registry.register("git_create_checkpoint", self.git_ops.create_checkpoint)

        # Search tools
        self.tool_registry.register("search_text", self.text_search.search)
        self.tool_registry.register("search_files", self.file_search.search)

        # Testing tools
        self.tool_registry.register("discover_tests", self.test_runner.discover)
        self.tool_registry.register("run_tests", self.test_runner.run_tests)
        self.tool_registry.register("run_linter", self.test_runner.run_linter)
        self.tool_registry.register("run_build", self.test_runner.run_build)
        self.tool_registry.register("collect_diagnostics", self.diagnostics.collect)

        # Code Intelligence & Indexing tools
        self.tool_registry.register("inspect_project_architecture", lambda root_path: ProjectDiscovery.inspect_repository(root_path))
        self.tool_registry.register("index_workspace", lambda root_path, force=False: self.indexer.index_workspace(root_path, force_reindex=force))
        self.tool_registry.register("search_symbols", lambda query, limit=50: self.indexer.search_symbols(query, limit))

    async def _handle_message(self, message: dict):
        """Handle incoming WebSocket messages."""
        msg_type = message.get("type", "unknown")

        if msg_type == "tool_request":
            await self._handle_tool_request(message)
        elif msg_type == "ping":
            await self.ws_client.send({"type": "pong", "correlation_id": message.get("id")})
        else:
            logger.warning(f"Unknown message type: {msg_type}")

    async def _handle_tool_request(self, message: dict):
        """Execute a tool and send the response."""
        tool_name = message.get("tool_name", "")
        arguments = message.get("arguments", {})
        correlation_id = message.get("id", "")

        import time
        start = time.time()

        try:
            result = await self.tool_registry.execute(tool_name, arguments)
            elapsed = (time.time() - start) * 1000

            await self.ws_client.send({
                "type": "tool_response",
                "correlation_id": correlation_id,
                "success": True,
                "result": result,
                "execution_time_ms": elapsed,
            })
        except Exception as e:
            elapsed = (time.time() - start) * 1000
            logger.error(f"Tool execution error ({tool_name}): {e}")

            await self.ws_client.send({
                "type": "tool_response",
                "correlation_id": correlation_id,
                "success": False,
                "error": str(e),
                "execution_time_ms": elapsed,
            })

    async def run(self):
        """Run the agent."""
        logger.info("FORGE AI Local Agent starting...")
        logger.info(f"Server: {self.config.server_url}")
        logger.info(f"Approved workspaces: {self.config.approved_workspaces}")

        if not self.auth_token:
            logger.error(
                "This agent is not paired yet. Open FORGE AI in your browser, click "
                "'Connect Agent' to get a pairing code and device ID, then run:\n"
                "    python run.py --pair <CODE> --device-id <DEVICE_ID>"
            )
            return

        # Setup signal handlers
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, lambda: self._shutdown_event.set())
            except NotImplementedError:
                # Windows doesn't support add_signal_handler for all signals
                pass

        try:
            # Start WebSocket connection
            ws_task = asyncio.create_task(self.ws_client.connect())
            shutdown_task = asyncio.create_task(self._shutdown_event.wait())

            done, pending = await asyncio.wait(
                [ws_task, shutdown_task],
                return_when=asyncio.FIRST_COMPLETED,
            )

            for task in pending:
                task.cancel()

        except KeyboardInterrupt:
            pass
        finally:
            logger.info("FORGE AI Local Agent shutting down...")
            await self.ws_client.disconnect()
            await self.session_manager.cleanup()
            self.process_manager.cleanup()
            logger.info("Shutdown complete.")
