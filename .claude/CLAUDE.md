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
`build_tools`; add a face by dropping one self-contained file in one of the six effect
folders — `eyes/moods/` `gestures/` `reactions/` `actions/` `vibes/` `widgets/` (each exposes
a single `MOOD`/`GESTURE`/`REACTION`/`ACTION`/`VIBE`/`WIDGET` — see `eyes/spec.py`: a held mood,
a one-shot move, or a looping overlay that's a task status (action), pure decoration (vibe), or
live data (widget)), then list its name in that folder's `__init__.py` order tuple
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

**Tools** (`assistant/tools.py`, one plain function each, served verbatim by `mcp_server.py`):
`face(name, gesture)` and `notify(reason)` always; `digital_read(pin)` and `set_servo(pin, angle)`
only when a board is attached. `face` is the one visual entry point — pass **any** effect name and
the server routes it (a mood is held, a looping activity/vibe/HUD runs until changed, the optional
`gesture` plays once over the top; `name='idle'` clears, `name='vibe'` plays a random vibe). The valid names in each tool's description
are **generated from the eye registries** at build time — add or move an effect and the tool docs
update themselves; never hand-list names here. The same functions back the Ollama brain (`brain.py`).

## Face — keep Pip alive (do this, don't just read it)

**Both layers are automatic now — don't hand-drive either.**

- **Activity** (what Pip's *doing*): `mcp_tool` hooks in `.claude/settings.json` cover the
  Claude Code hook lifecycle (24 events). Each is **typed to how long it should read** — a
  looping activity `name` for a state that lingers, a *bare* held mood `name` for a mood that
  should dwell, and a mood `name` + one-shot `gesture` only for a genuinely fleeting beat (a
  quick nod/wink) — all through the single `face(name, gesture)` tool. A flashing gesture where
  Pip should *dwell* feels wrong, so those became
  actions/bare-moods. The everyday flow: `attentive`+`scan` on `UserPromptExpansion` (a slash
  command expanding -- rare, so no flood), `thinking` on `UserPromptSubmit`, per-tool activities
  on `PreToolUse` (editing / working / scanning / searching / connecting), `waiting` while you
  ask the user something (`PreToolUse` on `AskUserQuestion` — `Notification` does *not* fire for
  it), `processing` while a subagent runs (`SubagentStart`, **pip-face excluded** via
  `^(?!pip-face).*`), `debugging` on `PostToolUseFailure`, `glitch` on `StopFailure`, `idle` on
  `Stop`. Big lifecycle beats map to fitting existing effects: `boot_draw` (a boot-up vibe) on
  `SessionStart` startup, `happy`+`excited` on `TaskCompleted`, `zen` (a calm vibe) on
  `PreCompact`, and a **random vibe** — `face('vibe')`, a sentinel the tool expands to
  `random.choice(VIBES)` — as a farewell flourish on `SessionEnd`.
  **smoking** rides `Notification/idle_prompt` (Pip takes a break while you're away). The MCP
  elicitation double-fire is deduped to the dedicated `Elicitation` (→ `listening`) /
  `ElicitationResult`. Deliberately **unmapped** to avoid strobe / BLE-flood: `MessageDisplay`,
  `FileChanged`, `PostToolUse`, `PostToolBatch`, `InstructionsLoaded`.
  Each action wears its own fitting face (its `Action.mood`), so an activity never blends with
  the emotional mood.
- **Emotion & expression** (how Pip *feels*, woven through what you *say*): a `UserPromptSubmit`
  command hook (`.claude/hooks/dispatch_expression.py`) re-injects a two-part expression policy
  every message. (1) **Instant reaction** — dispatch the cheap **pip-face (Haiku)** subagent
  (Agent, `subagent_type='pip-face'`) in your first tool-call batch, in parallel with your real
  work; it sets an opening face reacting to the message right away. (2) **Emote while you speak** —
  as you write your reply, drive `face` *yourself* at each emotional beat, shifting the expression
  as your tone evolves (~2–5 beats a reply, one for a terse answer; a held mood `name` plus an
  optional `gesture` for a punctuation beat). Build on pip-face's opening, shift only on a genuine
  tonal change, **never strobe**. This is the layer that makes Pip a *conversational* companion
  rather than a frozen mood — the lifecycle activity faces (thinking/editing/…) still run on their
  own. (Yes, you now drive `face` inline — that's the point; this supersedes the old "never call
  `face` yourself" rule.)

All these hooks/subagents reuse this session's MCP connection, so they never open a second
BLE link.

**Beyond the expression policy above** (where you already drive `face` while you speak), two
situational *actions* are worth firing by hand when they fit a specific event mid-task:

- **A snag or error** → `face("glitch")`.
- **A win / a breather** → `face("smoking")` (a chilled break — it's an action).
