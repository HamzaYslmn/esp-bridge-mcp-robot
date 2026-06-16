"""One-shot moves. Add one: drop `<name>.py` here exposing `GESTURE = Gesture(...)`, then slot
its name into the curated order below. A gesture is either a `blink` (lid-only) or a `motion`."""
from importlib import import_module

# -- curated order; blinks first, then enveloped motions --
_ORDER = (
    # blinks (lid-only)
    "blink", "double_blink", "wink", "wink_left", "wink_right",
    # gaze glances + directional blinks + sweeps
    "look_left", "look_right", "look_up", "look_down", "blink_down", "blink_up",
    "scan", "scan_sweep",
    # affirm / deny / acknowledge
    "nod", "refuse", "acknowledge",
    # expressive wobbles
    "laugh", "excited", "roll", "shiver", "pop", "squint", "cross_eyes",
)

GESTURES = {n: import_module(f"{__name__}.{n}").GESTURE for n in _ORDER}   # name -> Gesture, in order
