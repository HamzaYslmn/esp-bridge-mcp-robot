# CLAUDE.md

"Pip" — a desk robot: ESP32 + 128×64 OLED with animated eyes, over Bluetooth via
`python-esp-bridge[all]`. Driven by **Claude Code over MCP** (default) or a local
**Ollama** chat (`ROBOT_MCP=false`).

## Rules

Lean one-liner comments. YAGNI / DRY / KISS. Verb-y self-explaining names. No AI
attribution in commits/PRs.

## Run — uv, Python ≥3.13

```bash
uv sync
uv run src/main.py                   # MCP server over stdio (default); Claude Code spawns this via .mcp.json
ROBOT_MCP=false uv run src/main.py   # Ollama chat
uv run src/main.py --no-display      # no hardware
```

## Layout

Source under `src/`; imports are absolute from there (`from modules.…`). The same
package installs as `modules`, so `uvx --from git+<repo> pip-robot` runs it with no
checkout. Settings come from `os.getenv` (every read has a code default). Our
`modules/espbridge` ≠ the installed `espbridge` library. Add a capability in
`build_tools`; add a face with one line in the matching `eyes/` file.

## MCP

The MCP server runs over **stdio** (FastMCP `transport="stdio"`, the default). `.mcp.json`
is `{type: stdio, command: uv, args: [run, src/main.py]}`, so Claude Code *spawns* the
process itself and owns its lifecycle — one instance per session, which keeps it the sole
owner of the BLE link (stop it before running the demo). Because stdio uses **stdout** for
JSON-RPC, nothing may print to stdout — all logs go to stderr. No port, no HTTP.

## Face

Pip's face is driven by the `set_activity`/`set_face` MCP tools — Claude Code calls them
directly while it works. No hooks, no side-channel.
