"""Unit tests for Model Context Protocol (MCP) Tool Registry."""

import pytest

from durable_agent.mcp.protocol import MCPToolCall, MCPToolDefinition, MCPToolParameter
from durable_agent.mcp.registry import MCPToolRegistry


@pytest.mark.asyncio
async def test_mcp_tool_registration_and_execution() -> None:
    registry = MCPToolRegistry()

    def calc_vwap(volume: float, price: float) -> float:
        return round(volume * price, 2)

    definition = MCPToolDefinition(
        name="calculate_vwap",
        description="Calculates volume-weighted asset value",
        parameters=[
            MCPToolParameter(name="volume", type="float", description="Total shares traded"),
            MCPToolParameter(name="price", type="float", description="Execution price"),
        ],
    )

    registry.register(definition, calc_vwap)

    assert registry.get_tool("calculate_vwap") is not None
    assert len(registry.list_tools()) == 1

    call = MCPToolCall(tool_name="calculate_vwap", arguments={"volume": 100.0, "price": 150.5})
    res = await registry.execute(call)

    assert res.success is True
    assert res.output == 15050.0
    assert res.execution_time_ms >= 0.0


@pytest.mark.asyncio
async def test_mcp_unregistered_tool_returns_error() -> None:
    registry = MCPToolRegistry()
    call = MCPToolCall(tool_name="unknown_tool", arguments={})
    res = await registry.execute(call)

    assert res.success is False
    assert res.error is not None
    assert "not registered" in res.error.lower()
