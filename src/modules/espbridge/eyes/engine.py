"""EyeEngine -- threaded renderer for the mood / gesture / activity layers, plus the shared
eye math every layer builds on (ease / smoothstep / lid_openness / rounded_rect / look).
One move at a time (blink or gesture); a separate eased pose glides gaze + size.

This module imports nothing else from the package at load time (the registries are pulled in
lazily, inside EyeEngine), so any effect file can `from ..engine import smoothstep` freely."""
from __future__ import annotations

import math
import random
import threading
import time

from PIL import Image, ImageDraw

_TAU_GAZE, _TAU_SIZE = 0.09, 0.11            # gaze / eye-size settle time-constants
_AUTO = ({"left", "right"}, 0.20, 1)         # spontaneous blink (eyes, dur, reps)
_MASK = ({"left", "right"}, 0.24, 1)         # blink that hides a mood's lid swap


# ----------------------------------------------------------- shared eye math
def ease(cur, tgt, dt, tau):
    """Frame-rate-independent exponential approach of cur -> tgt."""
    return tgt + (cur - tgt) * math.exp(-dt / tau)


def smoothstep(k):
    """Hermite ease 0..1 with flat ends; clamps out-of-range input."""
    k = max(0.0, min(1.0, k))
    return k * k * (3 - 2 * k)


def lid_openness(u, reps, close=0.34):
    """Eyelid openness over a blink, 1->0->1 x reps; asymmetric -- snaps shut, eases open."""
    seg = (max(0.0, min(1.0, u)) * reps) % 1.0
    if seg < close:
        return 1.0 - smoothstep(seg / close)              # fast close
    return smoothstep((seg - close) / (1.0 - close))      # slower open


def rounded_rect(d, x, y, w, h, r, fill):
    """Rounded rect, clamped radius; rounds size once so a sub-pixel drift slides it rigidly."""
    if w <= 0 or h <= 0:
        return
    x0, y0 = round(x), round(y)
    x1, y1 = x0 + round(w) - 1, y0 + round(h) - 1
    if x1 < x0 or y1 < y0:
        return
    rr = max(0, min(int(r), (x1 - x0) // 2, (y1 - y0) // 2))
    if rr <= 0:
        d.rectangle([x0, y0, x1, y1], fill=fill)
    else:
        d.rounded_rectangle([x0, y0, x1, y1], radius=rr, fill=fill)


def look(dx, dy, bias=0.0):
    """A glance motion: dart to (dx, dy), parallax-swell the near eye, hold, then return.
    Returns a gesture motion fn(p, env); shared by the look_left/right/up/down gestures."""
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


class EyeEngine:
    def __init__(self, show, *, width=128, height=64, fps=30,
                 eye_w=36, eye_h=36, radius=12, gap=10,
                 set_brightness=None, bright=255,          # bright = panel brightness, max by default
                 clock=time.monotonic):                    # swap for a virtual clock to render offline
        from .actions import ACTIONS                       # pulled in here (not at module top) so effect
        from .gestures import GESTURES                     # files can import the eye math above without
        from .moods import MOODS                           # a circular import back through the registries
        self.MOODS, self.GESTURES, self.ACTIONS = MOODS, GESTURES, ACTIONS

        self._show, self._clock = show, clock
        self._set_brightness, self._bright = set_brightness, bright
        self._cur_bright = None                          # unset -> first frame pushes it
        self.W, self.H, self.fps = width, height, max(5, fps)
        self.eye_w, self.eye_h, self.radius, self.gap = eye_w, eye_h, radius, gap
        self.base_lx = (width - (2 * eye_w + gap)) // 2
        self.base_ly = (height - eye_h) // 2
        self._img = Image.new("1", (width, height), 0)   # one reused frame buffer
        self._draw = ImageDraw.Draw(self._img)

        self.gx = self.gy = 0.0                          # eased pose (thread-only)
        self.ew, self.eh = float(eye_w), float(eye_h)
        self._last = 0.0                                  # time of the previous step (for dt)

        self._lock = threading.Lock()                    # guards the fields below
        self.mood = "neutral"
        self._pending = None                             # mood waiting for the layer to free
        self.look_x = self.look_y = 0.0                  # resting gaze target
        self._blink = self._gesture = self._activity = None
        self._activity_start = 0.0                        # clock time the current activity began
        self._next_blink = self._next_idle = 0.0
        self._stop = threading.Event()
        self._thread = None

    # ------------------------------------------------------------------ API
    def start(self):
        if not (self._thread and self._thread.is_alive()):
            self._stop.clear()
            self._thread = threading.Thread(target=self._loop, name="eye-engine", daemon=True)
            self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=1.5)

    def set_mood(self, mood):
        m = mood.lower() if mood and mood.lower() in self.MOODS else "neutral"
        with self._lock:
            if m == self.mood:
                self._pending = None
            elif self._blink or self._gesture:           # busy -> apply (masked) once free
                self._pending = m
            else:
                self.mood = m
                self._begin_blink(self._clock(), _MASK)

    def play_gesture(self, name):
        """Play a commanded blink/gesture; preempts whatever's on the moving layer."""
        g = self.GESTURES.get((name or "none").lower())
        if g is None:                                    # "none" / unknown -> no-op
            return
        now = self._clock()
        with self._lock:
            if g.blink:
                self._begin_blink(now, (g.blink[0], g.dur, g.blink[1]))
            else:                                        # enveloped motion
                self._blink = None
                self._gesture = {"kind": g.name, "start": now, "dur": g.dur}
                self._next_blink = now + g.dur + random.uniform(2, 6)   # no spontaneous blink piling on

    def set_activity(self, name):
        """Loop a status animation ('idle'/unknown stops it); also wears a fitting face."""
        act = (name or "idle").lower()
        a = self.ACTIONS.get(act)
        if a and a.mood:
            self.set_mood(a.mood)                        # takes the lock itself
        with self._lock:
            self._activity = act if a else None
            self._activity_start = self._clock()

    # ----------------------------------------------------------- frame loop
    def _begin_blink(self, now, spec):
        """Start a blink, clearing the moving layer; reschedule the next spontaneous blink
        for after it ends so one never piles on this move (caller holds the lock)."""
        eyes, dur, reps = spec
        self._gesture = None
        self._blink = {"eyes": set(eyes), "start": now, "dur": dur, "reps": reps}
        self._next_blink = now + dur + random.uniform(2, 6)

    def reset_timers(self, now):
        """Seed the step clock and the next spontaneous blink/glance (call before stepping)."""
        self._last = now
        self._next_blink = now + random.uniform(2, 6)
        self._next_idle = now + random.uniform(1.5, 5)

    def step(self, now):
        """Advance one frame to time `now` and return the rendered buffer (no hardware push)."""
        dt = min(0.1, now - self._last)                   # clamp so a stall can't teleport the eyes
        self._last = now
        mood, act, look_at = self._schedule(now)
        self._ease_pose(now, dt, mood, act, look_at)
        return self._render(now)

    def _loop(self):
        self.reset_timers(self._clock())
        frame = 1.0 / self.fps
        while not self._stop.is_set():
            now = self._clock()
            try:
                self._show(self.step(now))
            except Exception:
                pass                                      # a bad effect frame or BLE hiccup -> skip it, keep the loop alive
            time.sleep(max(0.0, frame - (self._clock() - now)))

    def _schedule(self, now):
        """Locked: retire finished moves, fire the next auto blink/glance, snapshot state."""
        with self._lock:
            if self._blink and now - self._blink["start"] > self._blink["dur"]:
                self._blink = None
            if self._gesture and now - self._gesture["start"] > self._gesture["dur"]:
                self._gesture = None
            if self._activity:                               # let an activity that defines `expired` self-end
                expired = self.ACTIONS[self._activity].expired
                if expired and expired(now, self._activity_start):
                    self._activity = None                    # it decided it's done -> back to normal
            free = not (self._blink or self._gesture)
            if free and self._pending:                    # masked deferred mood swap
                self.mood, self._pending = self._pending, None
                self._begin_blink(now, _MASK)
            elif free and now >= self._next_blink:        # spontaneous blink (unless mood holds still)
                if self.MOODS[self.mood].still:
                    self._next_blink = now + random.uniform(2, 6)   # zen: just reschedule, no blink
                else:
                    self._begin_blink(now, _AUTO)                   # reschedules _next_blink itself
            elif free and self._activity is None and now >= self._next_idle:   # idle glance
                centered = random.random() < 0.3
                self.look_x, self.look_y = (0.0, 0.0) if centered else \
                    (random.uniform(-16, 16), random.uniform(-7, 7))
                if not centered and random.random() < 0.4:        # eyes tend to blink as they dart
                    self._begin_blink(now, _AUTO)
                self._next_idle = now + random.uniform(1.5, 5)
            if self.MOODS[self.mood].still:               # a still mood holds its gaze centred (zen)
                self.look_x = self.look_y = 0.0
            return self.mood, self._activity, (self.look_x, self.look_y)

    def _ease_pose(self, now, dt, mood, act, look_at):
        """Push brightness, then glide gaze + eye-size toward target."""
        spec = self.MOODS[mood]
        want = self._bright if spec.bright is None else spec.bright
        bright = min(want, self._bright)                              # emote may dim, capped at max
        if self._set_brightness and bright != self._cur_bright:
            try:
                self._set_brightness(bright)
                self._cur_bright = bright
            except Exception:
                pass                                      # BLE hiccup -- retry next frame
        if act:
            a = self.ACTIONS[act]
            tx, ty, hmult = a.pose(now) if a.pose else (0.0, 0.0, 1.0)
        else:
            tx, ty, hmult = look_at[0], look_at[1], 1.0
        self.gx = ease(self.gx, tx, dt, _TAU_GAZE)
        self.gy = ease(self.gy, ty, dt, _TAU_GAZE)
        self.ew = ease(self.ew, self.eye_w + spec.dw, dt, _TAU_SIZE)
        self.eh = ease(self.eh, (self.eye_h + spec.dh) * hmult, dt, _TAU_SIZE)

    # --------------------------------------------------------- motion + draw
    @staticmethod
    def _breath(now, amp):
        """Slow breath -> (vertical bob px, eye-height multiplier)."""
        period, bob_px, swell = 3.7, 1.0, 0.018           # s/cycle, px rise/fall, height swell
        w = 2 * math.pi / period
        bob = math.sin(now * w) * bob_px * amp
        return bob, 1.0 + swell * math.sin(now * w - 0.5) * amp   # swell lags the bob -> "inflate"

    @staticmethod
    def _drift(now):
        """Slow incommensurate gaze wander so a resting face never locks -> (x, y) px."""
        ax, ay = 0.5, 0.32                                # px wander amplitudes
        x = (math.sin(now * 0.61) + 0.5 * math.sin(now * 1.07 + 1.2)) * ax
        y = (math.sin(now * 0.73 + 2.0) + 0.5 * math.sin(now * 1.31)) * ay
        return x, y

    def _idle_life(self, now, spec, busy):
        """Breath always + a slow gaze wander at rest -> (x, y incl. bob, breath mult)."""
        calm = spec.still
        amp = 0.4 if busy else (0.55 if calm else 1.0)
        bob, breath = self._breath(now, amp)
        if busy or calm:
            return 0.0, bob, breath                       # no wander while busy / meditating
        dx, dy = self._drift(now)
        return dx, bob + dy, breath

    @staticmethod
    def _blink_lids(b, now):
        """Per-eye openness (snaps shut, eases open); (1, 1) at rest."""
        if not b:
            return 1.0, 1.0
        o = lid_openness((now - b["start"]) / b["dur"], b["reps"])
        ol = o if "left" in b["eyes"] else 1.0
        or_ = o if "right" in b["eyes"] else 1.0
        return ol, or_

    def _gesture_move(self, g, now):
        """Gesture motion -> (dx, dy, conv, w-scale, h-scale, bias); rest with none."""
        if not g:
            return 0.0, 0.0, 0.0, 1.0, 1.0, 0.0
        ph = min(1.0, (now - g["start"]) / g["dur"])
        ret = self.GESTURES[g["kind"]].motion(ph, math.sin(ph * math.pi))   # env = sin fades it in/out
        return (*ret[:5], ret[5] if len(ret) > 5 else 0.0)

    @staticmethod
    def _tilt(spec, now):
        """Per-eye y-skew: static tilt + optional animated `sway` (woozy seesaw)."""
        tilt = spec.tilt
        if spec.sway:
            amp, spd = spec.sway
            tilt += amp * math.sin(now * spd)
        return tilt

    def _draw_eye(self, sx, y0, openness, right, tilt, bias, conv, sw, sh, breath, paint):
        """Draw one eye: parallax + gesture scale + breath, shut centred, then mood lids."""
        es = 1.0 + (bias if right else -bias)             # parallax: the near eye swells
        w = max(2.0, self.ew * sw * es)
        ho = max(2.0, self.eh * sh * es * breath)         # open height (before the blink)
        h = max(2.0, ho * openness)
        ex = sx + (self.eye_w - w) / 2 + (-conv if right else conv)
        ey = y0 + (tilt if right else -tilt) + (self.eye_h - h) / 2   # blink shrinks toward centre
        r = min(w, h) * self.radius / self.eye_w
        rounded_rect(self._draw, ex, ey, w, h, r, 1)
        if paint:                                         # lids are the eye's shape -> keep them through a blink
            paint(self._draw, ex, ey, w, h, r, right)

    def _draw_extras(self, now, spec, act):
        """Mood decor, then the activity overlay."""
        d = self._draw
        if spec.decor:
            spec.decor(d, self.W, self.H, now, self.gx, self.gy)
        a = self.ACTIONS.get(act)
        if a and a.overlay:
            a.overlay(d, self.W, self.H, now, self.gx, self.gy)      # pass gaze so a prop rides the face

    def _render(self, now):
        with self._lock:                                 # snapshot; dicts are never mutated in place
            mood, act, b, g = self.mood, self._activity, self._blink, self._gesture
        spec = self.MOODS[mood]

        ol, or_ = self._blink_lids(b, now)
        dx, dy, conv, sw, sh, gbias = self._gesture_move(g, now)
        tilt = self._tilt(spec, now)
        bias = spec.bias + gbias                         # + = right eye bigger, left smaller
        lifex, lifey, breath = self._idle_life(now, spec, g is not None or act is not None)

        self._draw.rectangle([0, 0, self.W - 1, self.H - 1], fill=0)   # clear the reused buffer
        if not spec.bare:                                              # 'bare' (cool) draws no eyes
            x0 = self.base_lx + self.gx + dx + lifex                   # left eye's slot origin
            y0 = self.base_ly + self.gy + dy + lifey
            paint = spec.paint
            for sx, openness, right in ((x0, ol, False),
                                        (x0 + self.eye_w + self.gap, or_, True)):
                self._draw_eye(sx, y0, openness, right, tilt, bias, conv, sw, sh, breath, paint)
        self._draw_extras(now, spec, act)
        return self._img
