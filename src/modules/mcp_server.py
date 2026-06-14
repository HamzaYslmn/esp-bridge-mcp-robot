"""MCP server: exposes the robot's tools to Claude Code over stdio.

Claude Code spawns this process itself (`.mcp.json` is `{type: stdio, command: uv …}`)
and owns its lifecycle, talking JSON-RPC over stdin/stdout. Nothing else may write to
stdout or it corrupts the protocol -- our logs go to stderr.
"""
from __future__ import annotations

from fastmcp import FastMCP


def serve(robot, name="pip-robot"):
    """Run the FastMCP server over stdio so Claude Code can drive Pip's tools."""
    mcp = FastMCP(name)
    for fn in robot.tools:
        mcp.tool(fn)
    mcp.run(transport="stdio")
