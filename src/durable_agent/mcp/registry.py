"""Dynamic Model Context Protocol (MCP) Tool Registry."""

import logging
import time
from collections.abc import Callable
from typing import Any

from durable_agent.mcp.protocol import MCPToolCall, MCPToolDefinition, MCPToolResult

logger = logging.getLogger(__name__)


class MCPToolRegistry:
    """Registry maintaining active tool definitions and dynamic execution handlers."""

    def __init__(self) -> None:
        self._tools: dict[str, MCPToolDefinition] = {}
        self._handlers: dict[str, Callable[..., Any]] = {}

    def register(self, definition: MCPToolDefinition, handler: Callable[..., Any]) -> None:
        """Register a tool definition and its executable handler."""
        self._tools[definition.name] = definition
        self._handlers[definition.name] = handler
        logger.info(f"Registered MCP tool: {definition.name}")

    def get_tool(self, name: str) -> MCPToolDefinition | None:
        return self._tools.get(name)

    def list_tools(self) -> list[MCPToolDefinition]:
        return list(self._tools.values())

    async def execute(self, call: MCPToolCall) -> MCPToolResult:
        """Execute tool call dynamically with latency tracking."""
        handler = self._handlers.get(call.tool_name)
        if not handler:
            return MCPToolResult(
                tool_name=call.tool_name,
                success=False,
                output=None,
                error=f"Tool '{call.tool_name}' not registered in MCP registry",
            )

        start = time.perf_counter()
        try:
            res = handler(**call.arguments)
            if hasattr(res, "__await__"):
                output = await res
            else:
                output = res

            elapsed_ms = (time.perf_counter() - start) * 1000
            return MCPToolResult(
                tool_name=call.tool_name,
                success=True,
                output=output,
                execution_time_ms=round(elapsed_ms, 2),
            )
        except Exception as e:
            elapsed_ms = (time.perf_counter() - start) * 1000
            logger.error(f"Error executing MCP tool {call.tool_name}: {e}")
            return MCPToolResult(
                tool_name=call.tool_name,
                success=False,
                output=None,
                error=str(e),
                execution_time_ms=round(elapsed_ms, 2),
            )
