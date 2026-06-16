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
`build_tools`; add a face by dropping one self-contained file in `eyes/moods/`,
`eyes/gestures/`, or `eyes/actions/` (each exposes a single `MOOD`/`GESTURE`/`ACTION` —
see `eyes/spec.py`), then list its name in that folder's `__init__.py` order tuple
(that tuple is the curated order — menus, showcase, LLM enum). Shared bits: `painters.py`
(lid carvers), `primitives.py` (draw/math), `engine.py` (renderer). Eyeball a face
headless with `uv run docs/make_gif.py <face>` (writes a 5-frame `docs/<face>_preview.png`,
gitignored); no args rebuilds the showcase `docs/pip-eyes.gif`.

## MCP

The MCP server runs over **stdio** (FastMCP `transport="stdio"`, the default). `.mcp.json`
is `{type: stdio, command: uv, args: [run, src/main.py]}`, so Claude Code *spawns* the
process itself and owns its lifecycle — one instance per session, which keeps it the sole
owner of the BLE link (stop it before running the demo). Because stdio uses **stdout** for
JSON-RPC, nothing may print to stdout — all logs go to stderr. No port, no HTTP.

## Face — keep Pip alive (do this, don't just read it)

You are the only thing that can move Pip's face — via the `set_face`/`set_activity` MCP
tools. The MCP server owns the BLE link alone, so a hook can't drive the face; a
`SessionStart` hook only *reminds* you to. Treat it as a hard habit, not a nicety:

- **First reply of a session** → greet: `set_face("attentive", "blink_up")`.
- **Before any slow step** (search, build, tests, long edit) → `set_activity(...)` with
  the matching activity; `set_activity("idle")` when it ends.
- **Clean finish / win** → `set_face("happy", "nod")`; **snag or error** →
  `set_activity("glitch")` or `set_face("worried")`.
- Vary the emotion — never repeat the same face twice in a row.

Delegate to the `pip-face` subagent (Haiku, cheap) when you don't want it to block
coding; otherwise call the tool inline.
