# esp-bridge-mcp-robot

A small desk-robot ("Pip"): an ESP32 with a 128×64 OLED shows **expressive
animated eyes** and is controlled either from **Claude Code** (via a built-in MCP
server, default) or by a **local Ollama** model chatting in the terminal. The
ESP32 is reached wirelessly over **Bluetooth** via
[python-esp-bridge](https://github.com/HamzaYslmn/python-esp-bridge) (a.k.a.
ESPBridge) — flash the board once, then everything runs in Python on your computer.

<p align="center"><img src="docs/pip-eyes.gif" width="384" alt="Every Pip mood, gesture and activity"></p>

<p align="center"><img src="docs/coding.gif" width="384" alt="Pip reacting live while Claude Code works"></p>

- **Face** — procedural animated eyes (PIL): 23 emotions + 25 gestures +
  7 looping activities, auto-blink and idle glances, on a background thread.
- **Autonomous pins** — tell Pip what's wired to which pin; it drives any pin
  (servos, LEDs, motors, buzzers, sensors) through tool calls. No per-device code.
- **Two control paths** — Claude Code over MCP (drives the face + pins via tools),
  or a local Ollama model that returns a structured reply
  (`{"response", "emotion", "gesture"}`) and calls the pin/activity tools.

## What you need

| | |
|---|---|
| **A classic ESP32** dev board | The Bluetooth link needs a classic ESP32 (ESP-32S/D). On S3/C3/C6/H2 the bridge is USB-only, so wireless mode won't work. |
| **128×64 I²C OLED** | SSD1306 or SH1106 (the common 0.96″/1.3″ modules). |
| **A USB cable** | Only for the one-time firmware flash. After that, Bluetooth. |
| **[uv](https://docs.astral.sh/uv/)** | Python tooling (installs Python + deps). |
| Ollama *(optional)* | Only for local chat mode; not needed for Claude Code/MCP. |

### Wire the OLED to the ESP32

| OLED pin | ESP32 pin |
|---|---|
| VCC | 3V3 |
| GND | GND |
| SDA | GPIO **21** |
| SCL | GPIO **22** |

(Other pins are fine — set `ROBOT_OLED_SDA` / `ROBOT_OLED_SCL` in `.env` to match.)

## Setup

### 1. Install the project

```bash
uv sync
```

This installs the Python deps, including `python-esp-bridge[all]` — the Bluetooth
link, the OLED driver, the MCP server, and the firmware flasher (next step).

> Python 3.14 is pinned in `.python-version`. If `uv sync` fails on a missing
> wheel, run `uv python pin 3.12 && uv sync`.

### 2. Flash the ESPBridge firmware onto the ESP32 (once)

Pip talks to the board through ESPBridge firmware that must live on the ESP32.
You only do this **once** — afterwards the board is driven entirely from Python
over Bluetooth, no reflashing per project.

Plug the ESP32 in over **USB**, then flash the prebuilt firmware straight from the
host — no Arduino IDE needed. `uv sync` already pulled the flasher in (it ships in
`python-esp-bridge[all]`), so just run it; it lists the serial ports, you pick one,
and it writes the bundled image:

```bash
uv run espbridge flash           # lists ports, pick one, writes the firmware
uv run espbridge flash --erase   # wipe the whole flash first (clears stored name/NVS)
```

> Prefer not to install the project first? Flash straight from PyPI with uvx:
> `uvx --from "python-esp-bridge[flash]" espbridge flash`

<details>
<summary>Prefer to build it yourself? (Arduino IDE)</summary>

Install the **"python esp bridge"** library (Library Manager → search
*python esp bridge*), open *File → Examples → python esp bridge → Bridge*, set the
partition scheme to **Huge APP**, and click **Upload**. The whole sketch is one line:

```cpp
EspBridge.begin();              // default Bluetooth password: "espbridge"
// EspBridge.begin("yourpass"); // ...or set your own
```
</details>

The default firmware uses the Bluetooth password **`espbridge`**.

### 3. Verify the link and configure `.env`

Unplug USB (the board runs on its own power now) and confirm the host can reach it
over Bluetooth — this prints the chip, MAC, and capabilities:

```bash
uv run espbridge info         # uses password "espbridge" by default
```

Then create your config from the template:

```bash
cp src/.env.example src/.env
```

The defaults already match the default firmware (password `espbridge`, auto-pick
the first board). Only edit `src/.env` if you changed the firmware password or
have several boards:

```ini
ROBOT_PASSWORD=espbridge      # must match your EspBridge.begin(...)
ROBOT_BLE_TARGET=             # empty = first board; or a board name / MAC
```

> **Optional — faster, deterministic connects:** name the board `pip` and pin its
> MAC into `src/.env` with `uv run src/modules/espbridge/setup_board.py`. Handy if
> you have more than one bridge nearby.

### 4. (Chat mode only) install an Ollama model

Skip this if you're driving Pip from Claude Code.

```bash
ollama pull qwen3.5:4b
```

## Run

The mode is set by `ROBOT_MCP` in `.env` (default `true`).

```bash
uv run src/main.py                # default: MCP server — drive Pip from Claude Code
uv run src/main.py demo           # interactive menu: play any mood/gesture/activity
uv run src/main.py --no-display   # run with no board attached (just the engine)
```

- **Claude Code (MCP, default):** `.mcp.json` already registers `pip-robot` →
  `uv run src/main.py`. Open this folder in Claude Code and approve the server;
  Claude can then set Pip's face and drive any pin.
- **Local Ollama chat:** set `ROBOT_MCP=false` in `.env`, then `uv run src/main.py`
  and talk to Pip in the terminal.

## Configuration (`.env`, defaults in `.env.example`)

| Var | Default | Meaning |
|---|---|---|
| `ROBOT_MCP` | `true` | `true` = MCP server, `false` = Ollama chat |
| `ROBOT_MODEL` | `qwen3.5:4b` | Ollama model (chat mode) |
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama server |
| `ROBOT_BLE_TARGET` | _(auto)_ | Board name or MAC (empty = first board) |
| `ROBOT_PASSWORD` | `espbridge` | Firmware Bluetooth password (`EspBridge.begin(...)`) |
| `ROBOT_OLED_SDA` / `_SCL` | `21` / `22` | OLED I²C pins |
| `ROBOT_FPS` | `24` | Eye frame rate |

## Extending

Add a tool in `build_tools` (new hardware), or a new expression — an emotion in
`eyes/moods.py`, a gesture in `eyes/gestures.py`, an activity in
`eyes/activities.py` (one line each). **Both control paths pick it up with no
extra wiring:** Claude Code sees the new tool/vocabulary over MCP, and the Ollama
brain auto-derives its emotion/gesture choices from the same lists (and calls the
activity tool) — so a new face works in both modes the moment you add it.

Regenerate the showcase GIF above (every mood, gesture and activity) with
`uv run docs/make_gif.py`.

## Troubleshooting

- **No board found / connection fails** — make sure you flashed the firmware
  (step 2), the board is powered, and `ROBOT_PASSWORD` matches your firmware.
  `uv run espbridge info` should connect and print the chip/MAC.
- **Wireless doesn't work at all** — confirm it's a *classic* ESP32; S3/C3/C6/H2
  build the bridge USB-only.
- **Blank OLED** — check the SDA/SCL wiring matches `ROBOT_OLED_SDA`/`_SCL`.
- **`uv sync` fails on a wheel** — `uv python pin 3.12 && uv sync`.
