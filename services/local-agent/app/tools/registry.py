"""Central tool registry."""
import inspect
import logging
import time
from typing import Callable, Dict, Any, Optional
from collections import defaultdict

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Registry for all available tools."""

    def __init__(self):
        self._tools: Dict[str, Callable] = {}
        self._metrics: Dict[str, Dict[str, Any]] = defaultdict(lambda: {"calls": 0, "errors": 0, "total_ms": 0})

    def register(self, name: str, handler: Callable):
        """Register a tool handler."""
        self._tools[name] = handler
        logger.debug(f"Registered tool: {name}")

    async def execute(self, name: str, arguments: Dict[str, Any]) -> Any:
        """Execute a tool by name."""
        handler = self._tools.get(name)
        if not handler:
            raise ValueError(f"Unknown tool: {name}")

        self._metrics[name]["calls"] += 1
        start = time.time()

        try:
            if inspect.iscoroutinefunction(handler):
                result = await handler(**arguments)
            else:
                result = handler(**arguments)
            elapsed = (time.time() - start) * 1000
            self._metrics[name]["total_ms"] += elapsed
            return result
        except Exception as e:
            self._metrics[name]["errors"] += 1
            raise

    def list_tools(self) -> list[str]:
        """List all registered tools."""
        return list(self._tools.keys())

    def get_metrics(self) -> Dict[str, Any]:
        """Get tool execution metrics."""
        return dict(self._metrics)
