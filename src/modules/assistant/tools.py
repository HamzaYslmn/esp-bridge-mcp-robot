"""Robot capabilities as plain functions, shared by the Ollama brain and the MCP server.
Each takes simple args so any caller (a model, or Claude Code) can drive the face and any ESP32
pin. The valid face/activity names are read straight from the eye registries, so adding or moving
an effect never touches this file -- the folder __init__ order tuples are the one source of truth
(see eyes/spec.py)."""
from __future__ import annotations

from modules.espbridge.eyes import (
    ACTIONS, GESTURES, LOOPING, MOODS, PLAYABLE, REACTIONS, VIBES, WIDGETS)

_MOODS = ", ".join(MOODS)
_MOVES = ", ".join(("none", *GESTURES, *REACTIONS))           # one-shot: idle glances + reflexes
_ACTIVITIES = ", ".join(("idle", *ACTIONS, *VIBES, *WIDGETS))  # looping: statuses + vibes + HUDs


def build_tools(eyes, mgr=None):
    """Tool functions bound to this robot's eyes and ESP32 bridge. `mgr` is a self-healing
    BridgeManager (or None for face-only); pin tools fetch the live bridge each call, so they
    survive a BLE reconnect."""

    def face(name: str, gesture: str = "none") -> str:
        n = (name or "").lower()
        if n in MOODS:
            eyes.set_mood(n)                    # a held expression
        elif n in PLAYABLE and n not in LOOPING:
            eyes.play_gesture(n)                # a one-shot passed as the main name
        else:
            eyes.set_activity(n)                # a looping activity/vibe/HUD, or "idle"/unknown -> stop
        eyes.play_gesture(gesture)              # optional one-shot overlay; no-op on "none"/unknown
        return f"face: {name}" + ("" if (gesture or "none") == "none" else f"+{gesture}")
    face.__doc__ = (
        "Put something on Pip's face -- pass any effect name and Pip does the right thing: a mood "
        "is held, a looping activity/vibe/HUD runs until you change it, and the optional one-shot "
        "`gesture` plays over the top. Pass name='idle' to clear back to the resting face.\n\n"
        f"name: a held mood -- {_MOODS}; or a loop (runs until changed) -- {_ACTIVITIES}.\n"
        f"gesture: an optional move played once (default 'none'). One of: {_MOVES}."
    )

    def notify(reason: str = "") -> str:
        """Grab the human's attention: Pip turns to face you and pulses an alert. Call when you
        need the user to look over -- a question, a permission to grant, a finished task, a snag.

        reason: optional short note on why (shown in the log only).
        """
        eyes.set_mood("alert")
        eyes.play_gesture("scan_sweep")         # sweep around, looking for you
        return f"notify: {reason or 'attention'}"

    tools = [face, notify]
    if mgr is None:
        return tools

    def digital_read(pin: int) -> str:
        """Read a digital input pin with an internal pull-up (button, switch)."""
        b = mgr.bridge()
        b.gpio.mode(pin, "input_pullup")
        return f"pin {pin} = {b.gpio.read(pin)}"

    def set_servo(pin: int, angle: int) -> str:
        """Move a servo on a pin to an angle from 0 to 180 degrees."""
        angle = max(0, min(180, angle))
        mgr.bridge().pwm.servo(pin, angle)
        return f"servo {pin} -> {angle} deg"

    return tools + [digital_read, set_servo]
