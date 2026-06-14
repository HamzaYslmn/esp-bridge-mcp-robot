"""Render every mood, gesture and activity into one labelled showcase GIF.

    uv run docs/make_gif.py               # writes docs/pip-eyes.gif

Headless: drives the real eye engine with a capture callback (no hardware),
samples the latest frame at a fixed rate, scales it up and adds a caption.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from modules.espbridge.eyes import ACTIVITIES, EMOTIONS, GESTURES, EyeEngine  # noqa: E402
from modules.espbridge.eyes.gestures import BLINKS, GESTURES_FN  # noqa: E402

W, H = 128, 64
SCALE = 3          # pixel zoom for the eyes
BAR = 28           # caption strip height (px, unscaled)
SAMPLE_FPS = 14    # frames sampled per second for the GIF
MOOD_SEC = 0.9     # dwell per mood
ACT_SEC = 1.6      # dwell per activity
GEST_PAD = 0.4     # extra time after a gesture's own duration
OUT = ROOT / "docs" / "pip-eyes.gif"

_latest = {}
_frames = []       # (eye image, caption)


def _gesture_dur(name):
    if name in BLINKS:
        return BLINKS[name][1]
    return GESTURES_FN[name][0]


def _load_font(size=16):
    for name in ("arial.ttf", "DejaVuSans.ttf", "LiberationSans-Regular.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _record(caption, seconds):
    """Sample the latest rendered frame at SAMPLE_FPS for `seconds`."""
    for _ in range(max(1, int(seconds * SAMPLE_FPS))):
        time.sleep(1.0 / SAMPLE_FPS)
        f = _latest.get("f")
        if f is not None:
            _frames.append((f, caption))


def _compose(eye, caption, font):
    big = eye.convert("L").resize((W * SCALE, H * SCALE), Image.NEAREST)
    canvas = Image.new("L", (W * SCALE, H * SCALE + BAR), 0)
    canvas.paste(big, (0, 0))
    d = ImageDraw.Draw(canvas)
    tw = d.textlength(caption, font=font)
    d.text(((W * SCALE - tw) / 2, H * SCALE + (BAR - 16) / 2), caption, fill=255, font=font)
    return canvas


def main():
    eyes = EyeEngine(lambda img: _latest.__setitem__("f", img.copy()), fps=30)
    eyes.start()
    try:
        eyes.set_activity("idle")
        eyes.set_mood("neutral")
        _record("Pip", 1.0)

        for m in EMOTIONS:                       # static expressions
            eyes.set_mood(m)
            _record(f"mood: {m}", MOOD_SEC)

        eyes.set_mood("neutral")
        for g in GESTURES:                       # one-shot motions
            if g == "none":
                continue
            eyes.play_gesture(g)
            _record(f"gesture: {g}", max(0.8, _gesture_dur(g) + GEST_PAD))

        for a in ACTIVITIES:                     # looping statuses
            if a == "idle":
                continue
            eyes.set_activity(a)
            _record(f"activity: {a}", ACT_SEC)
        eyes.set_activity("idle")
    finally:
        eyes.stop()

    print(f"composing {len(_frames)} frames...")
    font = _load_font()
    imgs = [_compose(eye, cap, font) for eye, cap in _frames]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    imgs[0].save(OUT, save_all=True, append_images=imgs[1:], optimize=True,
                 duration=int(1000 / SAMPLE_FPS), loop=0)
    kb = OUT.stat().st_size / 1024
    print(f"wrote {OUT.relative_to(ROOT)}  ({len(imgs)} frames, {kb:.0f} KB)")


if __name__ == "__main__":
    main()
