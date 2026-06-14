"""Pip's entry point -- animated OLED robot.

Runs as an MCP server by default (ROBOT_MCP=true) so Claude Code can drive it;
set ROBOT_MCP=false for the local Ollama chat loop. Installed as the `pip-robot`
console script, so `uvx --from git+<repo> pip-robot` runs it with no checkout.

    pip-robot                 # MCP server (default)
    ROBOT_MCP=false pip-robot # chat with Pip
    pip-robot demo            # cycle every emotion on the panel
    pip-robot --no-display    # no hardware (test)
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# emoji-safe console on Windows (cp1254 etc.) for our own logging
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from dotenv import load_dotenv

_SRC = Path(__file__).resolve().parent.parent   # the repo's src/ when run from a checkout
load_dotenv(Path.cwd() / ".env")                # .env beside wherever you launched (uvx)
load_dotenv(_SRC / ".env")                       # repo's src/.env, if present
load_dotenv(_SRC / ".env.example")               # repo defaults; no-op once installed

from modules.assistant.robot import Robot


def main():
    args = sys.argv[1:]
    mcp = os.getenv("ROBOT_MCP", "true").lower() in ("1", "true", "yes", "on")
    with Robot(no_display="--no-display" in args) as robot:
        if "demo" in args:
            robot.demo()
        elif mcp:
            from modules.mcp_server import serve
            serve(robot)   # MCP over stdio; Claude Code spawns and owns this process
        else:
            robot.run_chat()


if __name__ == "__main__":
    main()
