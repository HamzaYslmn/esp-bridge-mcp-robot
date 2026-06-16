"""GESTURES -- one-shot moves played over the face: blinks (BLINKS) + enveloped
motions (GESTURES_FN). A motion may register a GESTURE_FX painter (e.g. glitch)."""
from __future__ import annotations

import math

from PIL import ImageChops

from .primitives import smoothstep

_PI = math.pi

# name -> (eyes, duration, closes); the lids always shut centred
BLINKS = {
    "blink":        ({"left", "right"}, 0.20, 1),
    "double_blink": ({"left", "right"}, 0.44, 2),
    "wink":         ({"right"}, 0.6, 1),
    "wink_left":    ({"left"}, 0.6, 1),
    "wink_right":   ({"right"}, 0.6, 1),
}


def _look(dx, dy, bias=0.0):
    """A glance: dart to (dx, dy), parallax-swell the near eye, hold, then return."""
    def fn(p, e):
        if p < 0.22:        # quick dart out
            hold = p / 0.22
        elif p > 0.80:      # quick return
            hold = (1.0 - p) / 0.20
        else:               # hold the look
            hold = 1.0
        hold = smoothstep(hold)               # ease the ramps
        s = 1.0 - 0.12 * hold                 # mild foreshorten (parallax carries the turn)
        return dx * hold, dy * hold, 0.0, s, s, bias * hold
    return fn


# name -> (duration, fn(ph, env) -> dx, dy, conv, scale_w, scale_h[, bias]); env fades it in/out
GESTURES_FN = {
    # -- gaze: glance somewhere; side looks parallax-swell the near eye --
    "look_left":   (1.2, _look(-8, 0, -0.2)),
    "look_right":  (1.2, _look(8, 0, 0.2)),
    "look_up":     (1.2, _look(0, -10)),
    "look_down":   (1.2, _look(0, 10)),
    # -- directional blinks: glance up/down as the lids snap shut, then reopen --
    "blink_down":  (0.5, lambda p, e: (0.0, 7 * e, 0.0, 1.0, 1.0 - 0.9 * e)),
    "blink_up":    (0.5, lambda p, e: (0.0, -7 * e, 0.0, 1.0, 1.0 - 0.9 * e)),
    "scan":        (1.3, lambda p, e: (math.sin(p * _PI * 2) * 16 * e, 0.0, 0.0, 1.0, 1.0)),   # darting back-and-forth
    "scan_sweep":  (1.6, lambda p, e: (-math.sin(p * _PI * 2) * 15, 0.0, 0.0, 1.0, 1.0)),      # one smooth sensor sweep
    # -- affirm / deny / acknowledge (decaying envelope -> punch, then settle) --
    "nod":         (1.4, lambda p, e: (0.0, math.sin(p * _PI * 4) * 7 * e * (1.0 - 0.42 * p), 0.0, 1.0, 1.0)),    # nods settling -- yes
    "refuse":      (1.2, lambda p, e: (math.sin(p * _PI * 6) * 9 * e * (1.0 - 0.45 * p), 0.0, 0.0, 1.0, 1.0)),    # shakes settling -- no
    "acknowledge": (0.45, lambda p, e: (0.0, e * 8, 0.0, 1.0, 1.0)),                           # one crisp dip -- "on it"
    # -- expressive wobbles --
    "laugh":       (1.4, lambda p, e: (0.0, -abs(math.sin(p * _PI * 4)) * 7 * e, 0.0, 1.0, 1.0 - 0.4 * e)),
    "excited":     (0.9, lambda p, e: (0.0, -abs(math.sin(p * _PI * 5)) * 8 * e, 0.0, 1.0 + 0.22 * e, 1.0 + 0.22 * e)),
    "roll":        (0.9, lambda p, e: (math.cos(p * _PI * 2) * 11 * e, math.sin(p * _PI * 2) * 7 * e, 0.0, 1.0, 1.0)),
    "shiver":      (0.7, lambda p, e: (math.sin(p * _PI * 16) * 3 * e, math.cos(p * _PI * 22) * 2 * e, 0.0, 1.0, 1.0)),
    "pop":         (0.5, lambda p, e: (0.0, 0.0, 0.0, 1.0 + 0.35 * e, 1.0 + 0.35 * e)),
    "squint":      (1.3, lambda p, e: (0.0, 0.0, 0.0, 1.0, 1.0 - 0.6 * e)),
    "cross_eyes":  (0.9, lambda p, e: (0.0, 0.0, 9.0 * e, 1.0, 1.0)),
}


# ---- glitch crash-fit: corruption effects tear the eyes apart (Watch Dogs style) ----
# Each shares (d, img, W, H, p, seed, amp); img None -> the pixel-movers no-op.
_GLITCH_DUR = 1.4   # seconds -- a sustained fit, then it settles back


def _datamosh(d, img, W, H, p, seed, amp):
    """Yank a few horizontal slices of the frame sideways -- the classic datamosh tear."""
    if img is None:
        return
    for k in range(3):
        y = (seed * 13 + k * 29) % (H - 4)
        h = 2 + (seed + k) % 4
        dx = (seed * 7 + k * 17) % (2 * amp + 1) - amp
        strip = img.crop((0, y, W, y + h))
        img.paste(0, (0, y, W, y + h))                       # clear the band, then drop it back shifted
        img.paste(strip, (dx, y))


def _displace_blocks(d, img, W, H, p, seed, amp):
    """Shove a couple of rectangular blocks off-register."""
    if img is None:
        return
    for k in range(2):
        bw, bh = 16 + (seed * 5 + k * 11) % 22, 6 + (seed * 3 + k * 7) % 12
        x = (seed * 9 + k * 23) % max(1, W - bw)
        y = (seed * 4 + k * 19) % max(1, H - bh)
        dx = (seed * 7 + k * 13) % (2 * amp + 1) - amp
        img.paste(img.crop((x, y, x + bw, y + bh)), (x + dx, y))


def _scanlines(d, img, W, H, p, seed, amp):
    """Carve CRT scanlines and drop a chunky static band over them."""
    for y in range(seed % 3, H, 3):
        d.line([0, y, W, y], fill=0, width=1)
    u, by = 4, int(abs(math.sin(seed * 0.13)) * (H // 4)) * 4
    for c in range(W // u):
        if math.sin(c * 12.9898 + seed * 78.233) * 43758.5453 % 1.0 > 0.5:
            d.rectangle([c * u, by, c * u + u - 1, by + u - 1], fill=1)


def _ghost(d, img, W, H, p, seed, amp):
    """OR an offset copy of the frame on top -- double-vision ghosting."""
    if img is None:
        return
    img.paste(ImageChops.lighter(img, ImageChops.offset(img, amp, 0)), (0, 0))


def _code_rain(d, img, W, H, p, seed, amp):
    """Stream short vertical dashes down the screen -- Matrix code-rain."""
    for col in range(6):
        x = 6 + col * (W - 12) // 5
        head = (p * (20 + (seed + col * 7) % 14) + col * 3.3) % (H + 10) - 5
        for j in range(4):
            y = int(head - j * 5)
            if 0 <= y < H:
                d.line([x, y, x, y + 3], fill=1, width=1)


def _invert_flash(d, img, W, H, p, seed, amp):
    """Flip the whole frame for a hard glitch pop."""
    if img is None:
        return
    img.paste(ImageChops.invert(img.convert("L")).convert("1"), (0, 0))


# the gesture plays through these beats in order; None = a clean flicker gap between bursts
_GLITCH_BEATS = (_datamosh, _scanlines, None, _displace_blocks, _code_rain, None,
                 _datamosh, _ghost, _invert_flash, None, _displace_blocks, _scanlines,
                 None, _code_rain, _datamosh, None, _ghost, _displace_blocks, None,
                 _scanlines, _datamosh, None)


def _glitch_jolt(p, e):
    """Eye motion: chunky sideways/vertical kicks on active beats, dead still on the gaps."""
    f = int(p * len(_GLITCH_BEATS)) % len(_GLITCH_BEATS)
    if _GLITCH_BEATS[f] is None:                             # clean beat -> hold steady
        return 0.0, 0.0, 0.0, 1.0, 1.0
    jx = math.sin(f * 12.9898) * 43758.5453 % 1.0            # per-beat pseudo-random 0..1
    jy = math.sin(f * 91.37) * 43758.5453 % 1.0
    dx = (round(jx * 4) - 2) * 3 * e                         # chunky horizontal kick (steps of 3px)
    dy = (round(jy * 2) - 1) * 2 * e                         # smaller vertical jump
    sw = 1.0 + (round(jx * 2) - 1) * 0.16 * e                # brief width stretch/squash
    return dx, dy, 0.0, sw, 1.0


def _glitch_effects(d, W, H, p, e):
    """Paint this beat's corruption onto the live frame (no-op on a clean beat)."""
    f = int(p * len(_GLITCH_BEATS)) % len(_GLITCH_BEATS)
    effect = _GLITCH_BEATS[f]
    if effect is None:
        return
    effect(d, getattr(d, "_image", None), W, H, p, f * 7 + 1, max(2, int(8 * e)))


GESTURES_FN["glitch"] = (_GLITCH_DUR, _glitch_jolt)          # crash fit -- corruption tears the eyes

# gesture-time painters: name -> fn(d, W, H, ph, env), drawn on top of the face
GESTURE_FX = {"glitch": _glitch_effects}

# while a gesture plays, wear another mood's eye-look (name -> mood whose paint to borrow)
GESTURE_FACE = {}

GESTURES = ("none",) + tuple(BLINKS) + tuple(GESTURES_FN)
