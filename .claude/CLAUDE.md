# CLAUDE.md

Guidance for Claude Code working in this repo.

## What this is

"Pip" — a desk robot: an ESP32 + 128×64 OLED showing animated emotive eyes,
reached over **Bluetooth** via **python-esp-bridge** (`python-esp-bridge[all]`).
Two control paths: **Claude Code over MCP** (default) or a **local Ollama** model
chatting in the terminal.

## Coding rules

- **Comments**: lean one-liners — short and clear. No paragraphs.
- **YAGNI / DRY / KISS**: build only what's used, share logic, keep it simple.
- **Names** self-explain — prefer verbs (`play_gesture`, `connect_display`, `build_tools`).
- No AI attribution in commits/PRs.

## Tooling & commands

**uv**; Python pinned to 3.14 (`pyproject.toml` allows ≥3.11). If `uv sync`
fails on a wheel: `uv python pin 3.12 && uv sync`.

```bash
uv sync
uv run src/main.py                   # MCP server (default; ROBOT_MCP=true)
ROBOT_MCP=false uv run src/main.py   # local Ollama chat over BLE
uv run src/main.py --no-display      # no hardware
ollama pull qwen3.5:4b               # chat model
```

## Layout & imports

All source lives under `src/`. Running `src/main.py` puts `src/` on `sys.path`,
so imports are absolute from there (`from modules.assistant.robot import Robot`).
No `config.py` — settings come from `os.getenv` after `.env`/`.env.example` load.
`modules/espbridge` is ours; the installed `espbridge` is the library —
fully-qualified imports keep them apart, no shadowing.

## Architecture

- `main.py` — load env, build `Robot`, run MCP or `run_chat()` per `ROBOT_MCP`.
- `mcp_server.py` — `build_mcp(tools)`: the FastMCP server.
- `modules/assistant/robot.py` — `Robot` wires display + eyes + tools; owns the
  Ollama loop + teardown.
- `modules/assistant/tools.py` — `build_tools(eyes, bridge)`: `set_face`,
  `set_activity`, `notify` + generic pin tools. MCP exposes all; the Ollama brain
  drops `set_face` (emotion/gesture come from its structured reply instead).
- `modules/assistant/brain.py` — `Brain`: persona + history + `REPLY_SCHEMA`; each
  turn returns `{response, emotion, gesture}` and applies it.
- `modules/llm/ollama_llm.py` — Ollama client; two-phase `response()` (an `act`
  tool loop, then a schema-constrained `speak` call).
- `modules/espbridge/eyes/` — eye engine by layer: `engine.py`, `moods.py`,
  `gestures.py`, `activities.py`, `primitives.py`.
- `modules/espbridge/display.py` — `connect_display`, `NullDisplay`.

Add a capability in `build_tools`; add an emotion/gesture/activity with one line
in the matching `eyes/` file. Both control paths pick up new tools automatically.

## MCP

`.mcp.json` registers `pip-robot` → `uv run src/main.py` (`ROBOT_MCP=true`), so
Claude Code drives the face + pins with no Ollama.

## Live face — Pip reacts to every message

A `UserPromptSubmit` hook (`.claude/hooks/pip_react.py`) fires on **every message
you send** and nudges me to spawn the **`pip-face`** subagent in the background.
Pip reacts each turn automatically — I just describe the moment; `pip-face` owns
the full emotion/gesture/activity vocabulary, picks the face, and calls the
`pip-robot` MCP. I never call `set_face` / `set_activity` myself.

**Mood rule.** Coding (reading / editing / testing here) → Pip holds **`smoking`**
the whole way; one-shot gestures still play on top, but no busy activity. Plain
chatting (no code in flight) → any fitting mood, gesture, or activity. End the
turn by sending `pip-face` **"finished, idle"** so it doesn't spin.

## Re-syncing

`uv sync` / `uv run` will fail with a Windows file lock if an old MCP server
(`espbridge-mcp.exe` / `main.py`) is still running — stop it (or restart Claude
Code) before syncing. The face hook uses `uv run --no-sync` to avoid this.
