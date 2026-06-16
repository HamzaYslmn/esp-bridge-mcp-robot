"""EyeEngine -- threaded renderer for the mood / gesture / activity layers.
One move at a time (blink or gesture); a separate eased pose glides gaze + size."""
from __future__ import annotations

import math
import random
import threading
import time

from PIL import Image, ImageDraw

from .activities import ACT_MOOD, ACTIVITIES, OVERLAYS, pose
from .gestures import BLINKS, GESTURE_FACE, GESTURE_FX, GESTURES_FN
from .moods import MOODS
from .primitives import ease, lid_openness, rounded_rect

_TAU_GAZE, _TAU_SIZE = 0.09, 0.11            # gaze / eye-size settle time-constants
_AUTO = ({"left", "right"}, 0.20, 1)         # spontaneous blink (eyes, dur, reps)
_MASK = ({"left", "right"}, 0.24, 1)         # blink that hides a mood's lid swap


class EyeEngine:
    def __init__(self, show, *, width=128, height=64, fps=30,
                 eye_w=36, eye_h=36, radius=12, gap=10,
                 set_brightness=None, bright=255,          # bright = panel brightness, max by default
                 clock=time.monotonic):                    # swap for a virtual clock to render offline
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
        self._restore_mood = None                        # mood to restore after a face-swapping gesture
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
        m = mood.lower() if mood and mood.lower() in MOODS else "neutral"
        with self._lock:
            self._restore_mood = None                    # explicit change cancels a gesture-restore
            if m == self.mood:
                self._pending = None
            elif self._blink or self._gesture:           # busy -> apply (masked) once free
                self._pending = m
            else:
                self.mood = m
                self._begin_blink(self._clock(), _MASK)

    def play_gesture(self, name):
        """Play a commanded blink/gesture; preempts whatever's on the moving layer."""
        name = (name or "none").lower()
        now = self._clock()
        with self._lock:
            if self._restore_mood is not None:           # interrupting a face-gesture -> restore its mood
                self.mood, self._restore_mood = self._restore_mood, None
            if name in BLINKS:
                self._begin_blink(now, BLINKS[name])
            elif name in GESTURES_FN:
                dur = GESTURES_FN[name][0]
                self._blink = None
                self._gesture = {"kind": name, "start": now, "dur": dur}
                self._next_blink = now + dur + random.uniform(2, 6)   # no spontaneous blink piling on
                if name in GESTURE_FACE:                  # wear another mood for the gesture, restore when done
                    self._restore_mood = self.mood
                    self.mood, self._pending = GESTURE_FACE[name], None

    def set_activity(self, name):
        """Loop a status animation ('idle' stops it); also wears a fitting face."""
        name = (name or "idle").lower()
        act = name if name in ACTIVITIES and name != "idle" else None
        if act in ACT_MOOD:
            self.set_mood(ACT_MOOD[act])                 # takes the lock itself
        with self._lock:
            self._activity = act

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
        mood, act, look = self._schedule(now)
        self._ease_pose(now, dt, mood, act, look)
        return self._render(now)

    def _loop(self):
        self.reset_timers(self._clock())
        frame = 1.0 / self.fps
        while not self._stop.is_set():
            now = self._clock()
            img = self.step(now)
            try:
                self._show(img)
            except Exception:
                pass                                      # transient BLE/I2C hiccup -- keep going
            time.sleep(max(0.0, frame - (self._clock() - now)))

    def _schedule(self, now):
        """Locked: retire finished moves, fire the next auto blink/glance, snapshot state."""
        with self._lock:
            if self._blink and now - self._blink["start"] > self._blink["dur"]:
                self._blink = None
            if self._gesture and now - self._gesture["start"] > self._gesture["dur"]:
                self._gesture = None
                if self._restore_mood is not None:        # face-gesture done -> restore the mood
                    self.mood, self._restore_mood = self._restore_mood, None
            free = not (self._blink or self._gesture)
            if free and self._pending:                    # masked deferred mood swap
                self.mood, self._pending = self._pending, None
                self._begin_blink(now, _MASK)
            elif free and now >= self._next_blink:        # spontaneous blink (unless mood holds still)
                if MOODS[self.mood].get("still"):
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
            if MOODS[self.mood].get("still"):             # a still mood holds its gaze centred (zen)
                self.look_x = self.look_y = 0.0
            return self.mood, self._activity, (self.look_x, self.look_y)

    def _ease_pose(self, now, dt, mood, act, look):
        """Push brightness, then glide gaze + eye-size toward target."""
        spec = MOODS[mood]
        bright = min(spec.get("bright", self._bright), self._bright)   # emote may dim, capped at max
        if self._set_brightness and bright != self._cur_bright:
            try:
                self._set_brightness(bright)
                self._cur_bright = bright
            except Exception:
                pass                                      # BLE hiccup -- retry next frame
        if act:
            tx, ty, hmult = pose(act, now)
        else:
            tx, ty, hmult = look[0], look[1], 1.0
        self.gx = ease(self.gx, tx, dt, _TAU_GAZE)
        self.gy = ease(self.gy, ty, dt, _TAU_GAZE)
        self.ew = ease(self.ew, self.eye_w + spec.get("dw", 0), dt, _TAU_SIZE)
        self.eh = ease(self.eh, (self.eye_h + spec.get("dh", 0)) * hmult, dt, _TAU_SIZE)

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
        calm = spec.get("still")
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

    @staticmethod
    def _gesture_move(g, now):
        """Gesture motion -> (dx, dy, conv, w-scale, h-scale, bias); rest with none."""
        if not g:
            return 0.0, 0.0, 0.0, 1.0, 1.0, 0.0
        ph = min(1.0, (now - g["start"]) / g["dur"])
        ret = GESTURES_FN[g["kind"]][1](ph, math.sin(ph * math.pi))   # env = sin fades it in/out
        return (*ret[:5], ret[5] if len(ret) > 5 else 0.0)

    @staticmethod
    def _tilt(spec, now):
        """Per-eye y-skew: static tilt + optional animated `sway` (woozy seesaw)."""
        tilt = spec.get("tilt", 0.0)
        if spec.get("sway"):
            amp, spd = spec["sway"]
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

    def _draw_extras(self, now, spec, act, g):
        """Mood decor, the activity overlay, then any gesture FX."""
        d = self._draw
        if spec.get("decor"):
            spec["decor"](d, self.W, self.H, now, self.gx, self.gy)
        if act in OVERLAYS:
            OVERLAYS[act](d, self.W, self.H, now, self.gx, self.gy)   # pass gaze so a prop rides the face
        if g and g["kind"] in GESTURE_FX:                            # e.g. the glitch corruption
            ph = min(1.0, (now - g["start"]) / g["dur"])
            GESTURE_FX[g["kind"]](d, self.W, self.H, ph, math.sin(ph * math.pi))

    def _render(self, now):
        with self._lock:                                 # snapshot; dicts are never mutated in place
            mood, act, b, g = self.mood, self._activity, self._blink, self._gesture
        spec = MOODS[mood]

        ol, or_ = self._blink_lids(b, now)
        dx, dy, conv, sw, sh, gbias = self._gesture_move(g, now)
        tilt = self._tilt(spec, now)
        bias = spec.get("bias", 0.0) + gbias             # + = right eye bigger, left smaller
        lifex, lifey, breath = self._idle_life(now, spec, g is not None or act is not None)

        self._draw.rectangle([0, 0, self.W - 1, self.H - 1], fill=0)   # clear the reused buffer
        if not spec.get("bare"):                                       # 'bare' (cool) draws no eyes
            x0 = self.base_lx + self.gx + dx + lifex                   # left eye's slot origin
            y0 = self.base_ly + self.gy + dy + lifey
            paint = spec.get("paint")
            for sx, openness, right in ((x0, ol, False),
                                        (x0 + self.eye_w + self.gap, or_, True)):
                self._draw_eye(sx, y0, openness, right, tilt, bias, conv, sw, sh, breath, paint)
        self._draw_extras(now, spec, act, g)
        return self._img
