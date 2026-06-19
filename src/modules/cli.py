"""Pip's entry point -- animated OLED robot.

Runs as an MCP server by default (ROBOT_MCP=true) so Claude Code can drive it;
set ROBOT_MCP=false for the local Ollama chat loop. Installed as the `pip-robot`
console script, so `uvx --from git+<repo> pip-robot` runs it with no checkout.

    pip-robot                 # MCP server (default)
    pip-robot ollama          # chat with Pip (local Ollama)
    ROBOT_MCP=false pip-robot # same, via env
    pip-robot demo            # menu: play any mood / gesture / activity
    pip-robot demo g13        # render a 30s GIF of menu item 13 (develop with no OLED)
    pip-robot --no-display    # no board: emulate the 128x64 OLED in a desktop window
    pip-robot demo --no-display  # play the demo menu live in that window
"""
from __future__ import annotations

import os
import signal
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

from modules.robot import Robot


def _on(name, default=""):
    return os.getenv(name, default).lower() in ("1", "true", "yes", "on")


def main():
    args = sys.argv[1:]
    mcp = _on("ROBOT_MCP", "true")
    # No board on this machine? Pass --no-display, or set ROBOT_NO_DISPLAY=true so the MCP
    # server Claude Code spawns runs against the on-screen OLED emulator (no CLI flag needed).
    no_display = _on("ROBOT_NO_DISPLAY") or "--no-display" in args
    robot = Robot(no_display=no_display).start()   # start() begins animating + feeds (kept out of __init__)
    # Ctrl+C with the Tk emulator up: on Windows Tcl grabs the console (WindowDisplay re-traps it);
    # on Unix re-assert Python's handler so a terminal Ctrl+C still raises KeyboardInterrupt here.
    if no_display and sys.platform != "win32":
        signal.signal(signal.SIGINT, signal.default_int_handler)
    try:
        if "demo" in args:
            from modules.demo import demo
            cap = next((a for a in args if a != "demo" and a[:1] == "g"), None)   # demo g13
            demo(robot, capture=cap)
        elif "ollama" in args or "chat" in args or not mcp:
            from modules.assistant.brain import chat
            chat(robot)
        else:
            from modules.mcp_server import serve
            serve(robot)   # MCP over stdio; Claude Code spawns and owns this process
    except KeyboardInterrupt:
        pass
    finally:
        robot.shutdown()
        os._exit(0)        # the daemon Tk thread's live Tcl interpreter can hang a normal exit
                           # (so Ctrl+C looks dead) -- force the process down after cleanup


if __name__ == "__main__":
    main()
