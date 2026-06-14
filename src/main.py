"""Pip -- animated OLED robot.

Runs as an MCP server by default (ROBOT_MCP=true) so Claude Code can drive it;
set ROBOT_MCP=false for the local Ollama chat loop.

    uv run src/main.py                       # MCP server (default)
    ROBOT_MCP=false uv run src/main.py       # chat with Pip
    uv run src/main.py demo                  # cycle every emotion on the panel
    uv run src/main.py --no-display          # no hardware (test)
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# emoji-safe console on Windows (cp1254 etc.); JSON-RPC over stdio is utf-8 anyway
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from dotenv import load_dotenv

_HERE = Path(__file__).parent
load_dotenv(_HERE / ".env")            # .env if present
load_dotenv(_HERE / ".env.example")    # fill missing keys with defaults (never overrides)

from modules.assistant.robot import Robot

def main():
    args = sys.argv[1:]
    mcp = os.getenv("ROBOT_MCP", "true").lower() in ("1", "true", "yes", "on")
    with Robot(no_display="--no-display" in args) as robot:
        if "demo" in args:
            robot.demo()
        elif mcp:
            from mcp_server import build_mcp
            build_mcp(robot.tools).run()
        else:
            robot.run_chat()


if __name__ == "__main__":
    main()
