# CLAUDE.md

Guidance for Claude Code working in this repository.

## What this is

A desk-robot assistant ("Pip"): an ESP32 + 128x64 OLED shows animated emotive
eyes, controlled from Claude Code over a built-in MCP server (default) or by a
**local Ollama** model in the terminal. The board is reached over **Bluetooth**
through **python-esp-bridge** (`python-esp-bridge[all]` from PyPI).

## Coding rules (follow these)

- **Comments**: streamlined one-liners — short, simple, easy to understand. No
  paragraph-long explanations.
- **YAGNI**: no speculative params, options, or abstractions. Only build what's used.
- **DRY**: no duplicate code; refactor to share logic. Avoid copy-paste.
- **KISS**: keep it simple, stupid. Avoid over-engineering; prefer clarity.
- **Names**: function and variable names self-explain; prefer clear verbs
  (`play_gesture`, `connect_display`, `build_tools`).
- No AI attribution in commits/PRs (user global rule).

## Tooling

- **uv**. Python pinned to 3.14 (`.python-version`); `pyproject.toml` allows
  `>=3.11`. If `uv sync` fails on a missing wheel: `uv python pin 3.12 && uv sync`.

## Commands

```bash
uv sync
uv run src/main.py                   # MCP server (default; ROBOT_MCP=true)
ROBOT_MCP=false uv run src/main.py   # local Ollama chat over BLE
uv run src/main.py --no-display      # no hardware
ollama pull qwen3.5:4b               # chat-mode model
```

## Import style

All source lives under `src/` (`src/main.py`, `src/mcp_server.py`,
`src/modules/`, `src/.env.example`). Running `src/main.py` puts `src/` on
`sys.path`, so imports are absolute from there: `from modules.assistant.robot
import Robot`, `from mcp_server import build_mcp`. No `config.py` — settings are
read via `os.getenv` after `main.py` loads `.env`/`.env.example` from its own dir.

Note: `modules/espbridge` is our package; the installed library is the top-level
`espbridge` — fully-qualified imports keep them distinct, no shadowing.

## Architecture

- `src/main.py` — load env, build `Robot`, run MCP (`build_mcp(robot.tools).run()`)
  or `robot.run_chat()` based on `ROBOT_MCP`.
- `src/mcp_server.py` — `build_mcp(tools)`: the FastMCP server (separate file).
- `modules/assistant/robot.py` — `Robot` wires display + eyes + tools, owns
  `run_chat()` (Ollama loop) + teardown.
- `modules/assistant/tools.py` — `build_tools(eyes, bridge)`: `set_face`,
  `set_activity` + generic pin tools (digital_write/read, set_servo, set_pwm,
  play_tone, read_analog). The MCP server exposes all of them; the Ollama brain
  drops `set_face` (emotion/gesture come from its structured reply instead) and
  keeps `set_activity` + the pin tools.
- `modules/assistant/brain.py` — `Brain`: persona/system prompt + history +
  `REPLY_SCHEMA`. Each turn returns a structured `{response, emotion, gesture}`
  (emotion/gesture enums built from the eyes' own vocabulary) and applies it.
- `modules/llm/ollama_llm.py` — Ollama client + two-phase `response()`: an `act` tool
  loop, then a `speak` call with `format=schema` (grammar-constrained JSON). Tools
  and structured output can't share a call, hence two phases. Auto-managed history.
- `modules/espbridge/eyes/` — the eye engine, one module per layer:
  `engine.py` (`EyeEngine`, threaded PIL renderer), `moods.py` (`MOODS`/`EMOTIONS`),
  `gestures.py` (`GESTURES`), `activities.py` (`ACTIVITIES` + overlays),
  `primitives.py` (shared draw helpers). `__init__.py` re-exports the public names.
- `modules/espbridge/display.py` — `connect_display` (env-driven BLE bridge +
  OLED), `NullDisplay`.

The model controls any pin generically (no per-device functions) once the user
says what's wired where. Add a capability in `build_tools`; add an emotion with
one line in `eyes/moods.py` (a motion in `gestures.py`, a status in
`activities.py`). Both control paths pick up new tools automatically.

## MCP

`.mcp.json` registers `pip-robot` → `uv run src/main.py` with `ROBOT_MCP=true`,
so Claude Code drives the robot (face + pins) with no Ollama. The server is
`build_mcp(robot.tools)` from `src/mcp_server.py`.

## Live face — Pip reacts while you work

When working in this repo, mirror your state on the real robot as you go — Pip
should *react* to the coding, not sit blank. Hand this off to the **`pip-face`
Haiku subagent** (`subagent_type: "pip-face"`) so you code with one hand and it
emotes with the other:

- Spawn it **in the background** (`run_in_background: true`) with a one-line
  description of what you're doing/feeling. It picks the face and calls the
  `pip-robot` MCP; you keep coding without waiting on the BLE round-trip.
- Fire it at **transitions, not every step**: session start (wake up), switching
  between reading / writing / testing, on a win or a bug, a pause, and at the end.
- Examples (just describe the situation, it maps it): "exploring the eyes module"
  · "writing the notify tool" · "tests passed" · "stuck on a BLE error"
  · "taking a breather" · "finished, idle".
- Always end the turn by sending it **"finished, idle"** so Pip isn't left
  spinning a busy animation.

**Mood rule — coding vs. chatting.** While you're *writing code* (reading,
editing, or testing in this repo), Pip holds the **`smoking`** emotion the whole
way through — cool and unbothered while it works. So when the moment is a coding
one, just tell `pip-face` the situation as usual; it knows to keep the held face
`smoking`. One-shot gestures (nod, laugh, look) may still play on top for beats,
but the resting face stays smoking and it won't switch to a busy activity. When
you're only **chatting** (no code in flight — answering, planning out loud), Pip
is free to show whatever mood, gesture, or activity fits the moment.

Don't call the `set_face` / `set_activity` MCP tools yourself — delegate to
`pip-face`. The subagent owns the full emotion/gesture/activity vocabulary and
the state→face mapping; you only describe the moment, and the main thread stays
on code.

## Note: re-syncing

`uv sync` / `uv run` reconcile the venv and will fail with a Windows file lock if
a previously-launched MCP server (`espbridge-mcp.exe` / an old `main.py`) is still
running. Stop those processes (or restart Claude Code) before syncing.
