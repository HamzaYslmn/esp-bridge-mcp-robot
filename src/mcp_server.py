"""MCP server: exposes the robot's tools (set_face + pins) to Claude Code."""
from __future__ import annotations

from fastmcp import FastMCP


def build_mcp(tools, name="pip-robot") -> FastMCP:
    mcp = FastMCP(name)
    for fn in tools:
        mcp.tool(fn)
    return mcp
