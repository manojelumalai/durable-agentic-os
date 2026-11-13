"""Model Context Protocol (MCP) data specifications for tool discovery and execution."""

from typing import Any

from pydantic import BaseModel, Field


class MCPToolParameter(BaseModel):
    name: str
    type: str
    description: str
    required: bool = True
    default: Any = None


class MCPToolDefinition(BaseModel):
    name: str
    description: str
    parameters: list[MCPToolParameter] = Field(default_factory=list)


class MCPToolCall(BaseModel):
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class MCPToolResult(BaseModel):
    tool_name: str
    success: bool
    output: Any
    error: str | None = None
    execution_time_ms: float = 0.0
