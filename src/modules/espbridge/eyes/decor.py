"""DECOR -- props drawn around the face (not the eyes): hearts, mug, cloud, shades...
Used by a mood's `decor` key or an activity overlay. Signature (d, W, H, now, ox, oy);
ox/oy is the eased gaze, for props that track it."""
from __future__ import annotations

import math

from .primitives import draw_formula, heart, smoothstep, sparkle


def lovely(d, W, H, now, ox=0.0, oy=0.0):  # little hearts & sparkles scattered around -- smitten
    spots = ((0.50, 0.07), (0.24, 0.14), (0.76, 0.12), (0.05, 0.40), (0.95, 0.42),
             (0.07, 0.74), (0.93, 0.72), (0.28, 0.90), (0.72, 0.88))
    for i, (fx, fy) in enumerate(spots):
        (heart if i % 2 == 0 else sparkle)(d, fx * W, fy * H, 9 if i % 2 == 0 else 4)


def coffee(d, W, H, now, ox=0.0, oy=0.0):  # a steaming mug, bottom-right -- "wired / caffeinated"
    cx, cy = W - 20, H - 11
    d.rounded_rectangle([cx, cy, cx + 12, cy + 9], radius=2, fill=1)              # cup body
    d.arc([cx + 11, cy + 1, cx + 17, cy + 8], start=-80, end=80, fill=1, width=2)  # handle
    for i in range(2):                                                            # two rising steam curls
        sx = cx + 3 + i * 6
        pts = [(sx + math.sin(f * 5 - now * 3) * 2.5, cy - 1 - f * 9) for f in (j / 6 for j in range(7))]
        d.line(pts, fill=1, width=1, joint="curve")


def sweat(d, W, H, now, ox=0.0, oy=0.0):  # a nervous bead wells up by the brow then slides -- "nervous"
    t = (now * 0.8) % 1.0
    x, y, s = W - 16 + int(ox), 8 + t * 11, 3
    d.ellipse([x - s * 0.7, y - s * 0.3, x + s * 0.7, y + s], fill=1)             # rounded body
    d.polygon([(x, y - s - 3), (x - s * 0.6, y - s * 0.2), (x + s * 0.6, y - s * 0.2)], fill=1)  # pointed top


def cloud(d, W, H, now, ox=0.0, oy=0.0):  # a little rain cloud drizzles overhead -- "gloomy"
    cx, cy = W // 2 + int(ox), 7
    for dx, r in ((-7, 4), (0, 5), (7, 4)):                                       # three lumps + flat base
        d.ellipse([cx + dx - r, cy - r, cx + dx + r, cy + r], fill=1)
    d.rectangle([cx - 11, cy, cx + 11, cy + 3], fill=1)
    for i in range(4):                                                            # falling rain streaks
        t = (now * 1.5 + i / 4) % 1.0
        rx, ry = cx - 9 + i * 6, cy + 5 + t * 12
        d.line([rx, ry, rx - 1, ry + 3], fill=1, width=1)


def vein(d, W, H, now, ox=0.0, oy=0.0):  # a cross-shaped popping anger vein throbs by the brow -- furious
    cx, cy = 16 + int(ox), 8
    s = 5 + (math.sin(now * 9) + 1)                                               # throb 5..7
    for a in (45, 135, 225, 315):                                                # four inward chevrons (the 💢 cross)
        ax, ay = math.cos(math.radians(a)), math.sin(math.radians(a))
        ex, ey = cx + ax * s, cy + ay * s
        d.line([ex, ey, ex - ax * 3 - ay * 2, ey - ay * 3 + ax * 2], fill=1, width=1)
        d.line([ex, ey, ex - ax * 3 + ay * 2, ey - ay * 3 - ax * 2], fill=1, width=1)


def sleep(d, W, H, now, ox=0.0, oy=0.0):  # "z z Z" drift up and grow -- sleepy
    for i in range(3):
        t = (now * 0.5 + i / 3) % 1.0
        x, y = W // 2 + 16 + i * 6 + int(ox), H // 2 - 2 - t * 22
        d.text((x, y), "Z" if i == 2 else "z", fill=1)


# pixel-art "deal-with-it" shades; '#' = dark lens block, gaps inside a lens = the gleam
_SHADES_ART = (
    "################################",   # connected top bar
    "###############  ###############",   # center bridge notch
    " ## # ########    ## # ######## ",   # gleam streaks, lower-left of each lens
    "  ## # #######     ## # ######  ",
    "   ## # #####       ## # ####   ",
    "    ########         #######    ",   # angled lens bottoms
)
_SHADES_BLOCKS = [(c, r) for r, row in enumerate(_SHADES_ART)  # block (col, row) coords, scanned once
                  for c, ch in enumerate(row) if ch == "#"]


def cool(d, W, H, now, ox=0.0, oy=0.0):  # pixel-art shades, no eyes -- wanders side to side like eyes
    u = 3                                                      # pixel-block size (96x48 -> leaves room to wander)
    sway = round(math.sin(now * 0.7) * 9 + math.sin(now * 1.7) * 4)   # organic side-to-side wander
    x0 = (W - len(_SHADES_ART[0]) * u) // 2 + sway
    y0 = (H - len(_SHADES_ART) * u) // 2 + round(math.sin(now * 0.9) * 2)  # a small vertical bob
    for c, r in _SHADES_BLOCKS:
        px, py = x0 + c * u, y0 + r * u
        d.rectangle([px, py, px + u - 1, py + u - 1], fill=1)


def devil(d, W, H, now, ox=0.0, oy=0.0):  # two sharply-angled horns + a clean swaying tail -- "devil"
    d.polygon([(30, 21), (41, 18), (18, 2)], fill=1)          # left horn, angled up-left
    d.polygon([(W - 30, 21), (W - 41, 18), (W - 18, 2)], fill=1)  # right horn, angled up-right
    bx, by = W - 6, H - 1                                      # tail from the bottom-right corner
    tx, ty = W - 13 + math.sin(now * 2.2) * 3, H - 23          # tip sways gently
    d.line([(bx, by), (W - 16, H - 12), (tx, ty)], fill=1, width=2, joint="curve")
    d.polygon([(tx - 3, ty + 2), (tx + 3, ty + 2), (tx, ty - 5)], fill=1)  # spade barb


def zen(d, W, H, now, ox=0.0, oy=0.0):  # cherry blossoms on a living breeze -- "in flow"
    # each leaf falls at its own terminal speed and is carried right by the wind: light ones hang
    # and blow clear across (off the right edge), heavy ones drop to the floor. The breeze always
    # blows -- swelling gusts, soft lulls, never stalling -- so the leaves stream, never a waterfall.
    SHAPE = ((0.0, 1.05), (-0.5, 0.4), (-0.68, -0.3), (-0.5, -0.82), (-0.22, -0.98),  # notched sakura petal:
             (0.0, -0.46), (0.22, -0.98), (0.5, -0.82), (0.68, -0.3), (0.5, 0.4))     # pointed stem, V-notch at the tip
    G0 = 6.5                                                        # steady breeze (px/s), always rightward
    WIND = ((1.8, 0.10, 0.0), (0.9, 0.29, 1.7), (0.5, 0.73, 4.2))   # gusts (amp px/s, omega, phase); sum 3.2 < G0
    def push(t0, t1):                                              # px the breeze carries a leaf between two times
        s = G0 * (t1 - t0)
        for a, w, p in WIND:
            s += a * (math.cos(w * t0 + p) - math.cos(w * t1 + p)) / w
        return s
    windv = G0 + sum(a * math.sin(w * now + p) for a, w, p in WIND)  # live wind -> wider flutter in gusts
    for i in range(9):                                             # spawn slots; ~3-5 on screen at once
        T = 14.0 + i % 4 * 2.0                                     # this slot's spawn cycle (14..20s)
        u = now / T + i * 0.41
        cyc, el = int(u), (u - int(u)) * T                        # cycle index + seconds since this leaf spawned
        r = lambda n: (math.sin((i * 9 + cyc * 131 + n * 7.1) * 12.9898) * 43758.5453) % 1.0  # re-rolled each spawn
        m = r(0)                                                   # weight: 0 light .. 1 heavy
        vfall = 6.0 + m * 10.0                                     # terminal fall (px/s): light hangs, heavy drops
        sail = 0.5 + (1 - m) * 1.7 + r(1) * 0.7                    # wind catch: light catches more + its own "sail"
        lag = m * 0.6 + r(2) * 0.6                                 # heavy lags the gust; each feels it at its own moment
        fph = el * (2.0 + (1 - m) * 3.0) + r(3) * 6              # falling-leaf flutter phase (light = faster)
        x = -10 + r(4) * W * 0.35 + sail * push(now - lag - el, now - lag) \
            + math.sin(fph) * (1.8 + (1 - m) * 3.2) * (0.6 + windv * 0.07)   # spawn-left + wind drift + flutter sway
        y = -7 + r(5) * 5 + vfall * el + math.sin(fph * 0.5) * 1.6 * (1 - m)  # fall from the top + a faint flutter bob
        if x > W + 9 or y > H + 9:                                # off the right or the floor -> gone till it respawns
            continue
        ang = el * (0.5 + (1 - m) * 1.3) * (1 if r(6) > 0.5 else -1) + math.cos(fph) * 0.6 + r(7) * 6  # tumble + rock
        fore = 0.4 + 0.6 * abs(math.cos(el * (0.7 + (1 - m)) + r(8) * 6))    # pinch thin when edge-on -> a 3D flash
        wid, lng, bend = (2.4 + r(1) * 1.8) * fore, 3.0 + r(2) * 3.0, (r(6) - 0.5) * 0.9  # size + aspect + comma bow
        ca, sa = math.cos(ang), math.sin(ang)
        pts = []
        for px, py in SHAPE:
            bx, by = (px + bend * py * py) * wid, py * lng          # bow into a comma, then stretch to size/aspect
            pts.append((x + bx * ca - by * sa, y + bx * sa + by * ca))
        d.polygon(pts, fill=1)


def kawaii(d, W, H, now, ox=0.0, oy=0.0):  # rosy blush hatch + twinkles -- "kawaii"
    for cx in (14, W - 24):                                    # a blush patch under each eye -- tracks the gaze
        for i in range(3):
            d.line([cx + i * 4 + ox, H - 12 + oy, cx + 3 + i * 4 + ox, H - 7 + oy], fill=1, width=1)
    for fx, fy, s in ((0.07, 0.16, 4), (0.93, 0.18, 4), (0.5, 0.06, 3)):
        sparkle(d, fx * W, fy * H, s)                          # ambient twinkles stay put


# ---- activity props: the looping icon a busy activity wears (wired in activities.py OVERLAYS) ----
def cigarette(d, W, H, now, ox=0.0, oy=0.0, drag_chance=50):  # a lit cigarette at the lips, riding with the face -- "chill"
    # default: held at the lips with a thin curl. A drag (drag_chance% / 10s) plays four beats:
    # inhale (curl thins, ember glows), lower it, exhale a plume, raise it back home.
    win, tloc, dur = int(now / 10), now % 10, 4.2
    drag = win * 2654435761 % 997 < drag_chance / 100 * 997               # this 10s window: drag_chance% (uniform hash)
    p = tloc / dur if drag and tloc < dur else None                      # drag progress 0..1 (None -> just chilling)
    inh, awy, exh = 0.20, 0.42, 0.80                                     # beat ends: inhale | lower | exhale | (raise back)
    if p is None:
        away = inhale = 0.0
    elif p < inh:                                                        # drawing the breath in, cig still at the lips
        away, inhale = 0.0, smoothstep(p / inh)
    elif p < awy:                                                        # lowering it away from the lips
        away, inhale = smoothstep((p - inh) / (awy - inh)), 0.0
    elif p < exh:                                                        # held away while exhaling
        away, inhale = 1.0, 0.0
    else:                                                               # raising it back home
        away, inhale = 1.0 - smoothstep((p - exh) / (1 - exh)), 0.0

    dx, dy = away * -14, away * 3                                        # lowered down-inward, clear of the lips
    hx, hy = W * 0.58 + ox + dx, H - 10 + oy + dy                        # filter end (at the lips when home)
    tx, ty = W * 0.74 + ox + dx, H - 7 + oy + dy                         # burning ember tip
    d.line([hx, hy, tx, ty], fill=1, width=4)                           # short, thick stick
    glow = 2 + 2 * inhale                                               # ember flares as the breath is drawn in
    d.ellipse([tx - glow, ty - glow, tx + glow, ty + glow], fill=1)     # glowing ember tip

    def curl(s):                                                        # one slow laminar curl off the ember, scaled 0..1
        if s <= 0.03:
            return
        pts = [(tx + math.sin(f * 4.5 - now * 0.9) * (f * f * 8) * s, ty - 2 - f * (ty - 4) * s)
               for f in (i / 15 for i in range(16))]                   # shrinks toward the ember as s -> 0
        d.line(pts, fill=1, width=2, joint="curve")

    if p is None:
        curl(1.0)                                                      # at rest -> the full curl
    elif p < inh:
        curl(1.0 - inhale)                                             # inhale -> the curl thins away to nothing
    elif p < exh:                                                      # lowered/away -> a thin smolder trails the ember
        pts = [(tx + math.sin(f * 5 - now * 1.4) * (1 + f * 4), ty - 1 - f * 16)
               for f in (i / 9 for i in range(10))]
        d.line(pts, fill=1, width=1, joint="curve")
    else:
        curl(1.0 - away)                                              # raising it back -> the curl builds up again

    if p is not None and awy <= p < exh:                              # exhale -> a soft plume pours from the lips (they stay put)
        mx, my = W * 0.6 + ox, H - 13 + oy
        eq = (p - awy) / (exh - awy)                                  # 0..1 across the exhale
        rise = smoothstep(eq) * 1.7
        fade = 1.0 if eq < 0.4 else smoothstep((1.0 - eq) / 0.6)      # dissipates gently over a long tail
        for i in range(22):
            f = i / 21.0
            front = rise - f * 0.9
            if front <= 0:
                continue
            cxl = mx + math.sin(f * 3.4 + p * 4) * (2 + f * 11)
            spread = 3 + f * 16
            base = (2.5 + f * 8) * min(1.0, front * 2.4) * fade       # fade shrinks every puff toward the end
            for j in (-1, 0, 1):                                      # a few puffs across the width -> a full, soft plume
                bx, by = cxl + j * spread * 0.5, my - f * (my + 2) - rise * 3
                rad = base * (1.0 - 0.28 * abs(j))
                if rad > 0.5:
                    d.ellipse([bx - rad, by - rad, bx + rad, by + rad], fill=1)


def formulas(d, W, H, now, ox=0.0, oy=0.0):  # nerdy tokens drift up -- "thinking" ('^' = superscript)
    tokens = ("E=mc^2", "a^2+b^2=c^2", "F=ma", "v=d/t", "2^10", "i^2=-1", "dx/dt",
              "3.14", "1.618", "9.8", "42", "404", "1337", "O(n)", "?")
    for i in range(4):
        t = (now * 0.4 + i / 4) % 1.0                   # 0..1 rise progress
        y = H - 10 - t * (H - 16)                       # float up the screen
        ti = (i * 3 + int(now * 0.4 + i / 4)) % len(tokens)
        x = 6 + i * (W - 50) / 3 + math.sin(now * 1.1 + i * 2) * 5
        draw_formula(d, x, y, tokens[ti])


def headphones(d, W, H, now, ox=0.0, oy=0.0):  # band + an ear cup each side -- "listening"
    cw, ch = 11, 22
    cy = H // 2 - ch // 2
    d.rounded_rectangle([2, cy, 2 + cw, cy + ch], radius=4, fill=1)          # left cup
    d.rounded_rectangle([W - 3 - cw, cy, W - 3, cy + ch], radius=4, fill=1)  # right cup
    d.arc([8, 1, W - 9, H - 12], start=180, end=360, fill=1, width=3)        # headband


def magnifier(d, W, H, now, ox=0.0, oy=0.0):  # a magnifying glass sweeps across -- "searching"
    rad = 6
    cx = W / 2 + math.sin(now * 1.6) * (W / 2 - 12)
    cy = H - 11 + math.sin(now * 3.2) * 2
    d.ellipse([cx - rad, cy - rad, cx + rad, cy + rad], outline=1, width=2)  # lens rim
    hx, hy = cx + rad * 0.7, cy + rad * 0.7
    d.line([hx, hy, hx + 5, hy + 5], fill=1, width=2)                        # handle


def hammer(d, W, H, now, ox=0.0, oy=0.0):  # winds up slow, strikes an anvil hard, big sparks -- "working"
    ax, ay = W // 2 + 4, H - 6                        # anvil strike point
    px, py = ax - 6, H - 18                           # wrist pivot, above-left
    raised, struck = math.radians(-38), math.radians(82)
    t = (now * 0.8) % 1.0                             # slow, deliberate rhythm
    th = (struck + (raised - struck) * (t / 0.7) if t < 0.7      # long slow wind-up
          else raised + (struck - raised) * ((t - 0.7) / 0.3))   # snap down to strike
    hx, hy = px + 12 * math.cos(th), py + 12 * math.sin(th)
    nx, ny = -math.sin(th), math.cos(th)             # crossbar dir, perpendicular to handle
    d.line([px, py, hx, hy], fill=1, width=2)        # handle
    d.line([hx - 6 * nx, hy - 6 * ny, hx + 6 * nx, hy + 6 * ny], fill=1, width=5)  # head
    d.rectangle([ax - 7, ay, ax + 7, ay + 3], fill=1)  # anvil / work piece
    if t < 0.25:                                      # impact: strong spark, fades on recoil
        s = 1.0 - t / 0.25                            # 1 right after the hit -> 0
        L = 5 + 11 * s
        for k in range(5):                            # upward fan of sparks
            a = math.radians(-160 + k * 35)
            d.line([ax, ay - 1, ax + math.cos(a) * L, ay - 1 + math.sin(a) * L], fill=1, width=2)


def typing(d, W, H, now, ox=0.0, oy=0.0):  # two small chibi hands tap the keys -- "editing"
    base = H - 3                                          # key row the fingertips reach
    for i, cx in enumerate((18, W - 18)):               # left & right hand, near the edges
        tap = round((math.sin(now * 8 + i * math.pi) + 1) / 2 * 3)   # alternating peck
        cy = base - 6 + tap                             # whole hand dips to press
        thumb = cx + (7 if i == 0 else -7)              # thumb tucked toward the centre
        d.ellipse([thumb - 2, cy - 3, thumb + 3, cy + 2], fill=1)    # thumb nub
        d.rounded_rectangle([cx - 7, cy - 5, cx + 7, cy + 2], radius=3, fill=1)  # back of hand
        for k in range(4):                              # four little fingertips on the keys
            fx = cx - 5 + k * 4
            d.ellipse([fx - 2, cy, fx + 2, cy + 5], fill=1)
        for k in range(3):                              # notches between the fingers
            nx = cx - 3 + k * 4
            d.line([nx, cy + 1, nx, cy + 5], fill=0, width=1)


def spinner(d, W, H, now, ox=0.0, oy=0.0):  # a sleek arc sweeps around a ring -- "processing"
    cx, cy, rad = W // 2, H - 11, 8
    a0 = int(now * 200) % 360
    d.arc([cx - rad, cy - rad, cx + rad, cy + rad], start=a0, end=a0 + 210, fill=1, width=2)


def link_dots(d, W, H, now, ox=0.0, oy=0.0):  # three dots pulse in sequence -- "connecting"
    cy = H - 11
    for i in range(3):
        t = (math.sin(now * 4 - i * 1.1) + 1) / 2          # staggered 0..1 pulse
        s = 1.5 + 2.5 * t
        x = W / 2 - 10 + i * 10
        d.ellipse([x - s / 2, cy - s / 2, x + s / 2, cy + s / 2], fill=1)


def bug(d, W, H, now, ox=0.0, oy=0.0):  # a beetle skitters along the bottom, legs twitching -- "debugging"
    cx = W / 2 + math.sin(now * 1.4) * (W / 2 - 14)
    cy = H - 8
    face = 1 if math.cos(now * 1.4) >= 0 else -1          # head leads the way it scuttles
    d.ellipse([cx - 6, cy - 4, cx + 6, cy + 4], fill=1)  # shell
    hx = cx + face * 6
    d.ellipse([hx - 2, cy - 2, hx + 2, cy + 2], fill=1)  # head
    d.line([cx, cy - 4, cx, cy + 4], fill=0, width=1)    # wing split
    for k in (-1, 1):                                     # six twitching legs, top & bottom rows
        for j in range(3):
            px = cx - 4 + j * 4
            wig = math.sin(now * 14 + j + (k + 1)) * 1.5
            d.line([px, cy + k * 3, px + wig, cy + k * 6], fill=1, width=1)
    d.line([hx, cy - 1, hx + face * 3, cy - 4], fill=1, width=1)  # antennae
    d.line([hx, cy + 1, hx + face * 3, cy - 2], fill=1, width=1)


def _cube(d, cx, cy, s):
    # one small 3D cube: white faces + black edges, so it reads over the eyes AND the dark bg
    h, o = s / 2, s * 0.42                                            # half-side, iso depth (up-right)
    x0, y0, x1, y1 = cx - h, cy - h, cx + h, cy + h
    d.polygon([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], fill=1, outline=0)                  # front face
    d.polygon([(x0, y0), (x0 + o, y0 - o), (x1 + o, y0 - o), (x1, y0)], fill=1, outline=0)  # top face
    d.polygon([(x1, y0), (x1 + o, y0 - o), (x1 + o, y1 - o), (x1, y1)], fill=1, outline=0)  # right face


def cubes(d, W, H, now, ox=0.0, oy=0.0):  # 3 cubes fly in, stack, then tumble off -- "building"
    s, step, hold, fall, gap = 10, 0.5, 0.15, 0.6, 0.2               # cube size + phase timings
    asm = 3 * step
    T = asm + hold + fall + gap
    cyc, lp = int(now / T), now % T
    cx = W / 2
    slot_y = (H - 9, H - 9 - (s + 2), H - 9 - 2 * (s + 2))           # stack bottom -> top
    rnd = lambda a: (math.sin(a * 12.9898) * 43758.5453) % 1.0       # deterministic pseudo-random
    for i in range(3):
        ty = slot_y[i]
        if lp < asm:                                                 # assembling, one cube at a time
            start = i * step
            if lp < start:
                continue                                             # this cube hasn't entered yet
            k = smoothstep(min(1.0, (lp - start) / step))            # eased fly-in 0..1
            dirn = int(rnd(cyc * 9.7 + i * 4.3) * 3)                 # 0 left / 1 right / 2 top
            sx, sy = (-14, ty) if dirn == 0 else (W + 14, ty) if dirn == 1 else (cx, -14)
            x, y = sx + (cx - sx) * k, sy + (ty - sy) * k
        elif lp < asm + hold:                                        # the finished tower stands a beat
            x, y = cx, ty
        else:                                                        # collapse: spread out + gravity
            tc = (lp - asm - hold) / fall
            x, y = cx + (i - 1) * (38 + i * 12) * tc, ty + 70 * tc * tc
        _cube(d, x, y, s)


def flask(d, W, H, now, ox=0.0, oy=0.0):  # test tube on 3 independent rhythms: shake/bubble/gas -- "testing"
    env = lambda n, thr, soft: max(0.0, min(1.0, (n - thr) / soft))  # slow signal -> 0..1, off below thr
    shake = env(math.sin(now * 0.8) + math.sin(now * 1.9 + 1.0), 0.85, 0.3)        # bursts of the jitters
    bubl = env(math.sin(now * 0.5 + 0.7) + math.sin(now * 1.27 + 2.4), -0.2, 0.55)  # the gentle baseline simmer
    gasl = env(math.sin(now * 0.41) + math.sin(now * 0.93 + 1.6), 0.65, 0.5)        # spells of venting gas
    jx = math.sin(now * 42) * 2.0 * shake                          # shake jitter, scaled by its envelope
    cx, top, bot, hw = W - 10 + jx, H - 30, H - 4, 5              # tube centre/top/bottom/half-width
    liq = top + 11                                                # liquid surface
    d.line([cx - hw, top, cx - hw, bot - hw], fill=1)            # left wall
    d.line([cx + hw, top, cx + hw, bot - hw], fill=1)            # right wall
    d.arc([cx - hw, bot - 2 * hw, cx + hw, bot], start=0, end=180, fill=1)  # rounded bottom
    d.rectangle([cx - hw + 1, liq, cx + hw - 1, bot - hw], fill=1)         # liquid column
    d.ellipse([cx - hw + 1, bot - 2 * hw, cx + hw - 1, bot], fill=1)       # fill the rounded base
    d.rectangle([cx - hw - 1, top - 4, cx + hw + 1, top], fill=1)          # cap / stopper
    d.line([cx - hw - 1, top - 2, cx + hw + 1, top - 2], fill=0)           # groove on the cap
    for i in range(3):                                           # bubbles rise only during a bubbling spell
        bt = (now * (0.6 + i * 0.17) + i * 0.31) % 1.0          # 0 at the base -> 1 at the surface
        by = (bot - hw) - bt * (bot - hw - liq)
        bx = cx + math.sin(now * 3 + i * 2) * (hw - 2.5)
        r = (0.8 + (i % 2)) * bubl                              # size fades in/out with the spell
        if r > 0.45:
            d.ellipse([bx - r, by - r, bx + r, by + r], fill=0)
    if gasl > 0.05:                                             # thin gas wisps only while venting
        for mx, wdt, spd, off in ((cx - 2, 1, 0.33, 0.0), (cx + 3, 2, 0.25, 0.55)):
            p = (now * spd + off) % 1.0                          # one emission cycle
            ln = (3 + min(p / 0.82, 1.0) * 21) * gasl           # grows short -> long, fades with the spell
            lift = max(0.0, (p - 0.82) / 0.18) * (ln + 8)      # then it breaks free and climbs off
            pts = [(mx + math.sin(f * 3.6 + now * 1.8) * (0.5 + f * 2.6), (top - 4 - lift) - f * ln)
                   for f in (j / 7 for j in range(8))]          # gentle drift, wider toward the tip
            d.line(pts, fill=1, width=wdt, joint="curve")


def rocket(d, W, H, now, ox=0.0, oy=0.0):  # 3-2-1 countdown, liftoff, smoke trail, banks off-top -- "deploying"
    step, fly, gap = 0.7, 2.8, 0.5                       # countdown s/digit, slow arc, breath
    t0 = 3 * step
    ph = now % (t0 + fly + gap)
    if ph < t0:                                          # T-minus: tick a 7-seg digit down at the pad
        n = 3 - int(ph / step)
        cx, cy, e = W - 12, H - 12, 6.5                 # centre + half-height of the digit
        x0, y0, x1, y1, ym = cx - e * 0.55, cy - e, cx + e * 0.55, cy + e, cy
        lit = {1: "bc", 2: "abged", 3: "abgcd"}[n]      # segments on for 3/2/1
        for s, a, b in (("a", (x0, y0), (x1, y0)), ("b", (x1, y0), (x1, ym)), ("c", (x1, ym), (x1, y1)),
                        ("d", (x0, y1), (x1, y1)), ("e", (x0, ym), (x0, y1)), ("f", (x0, y0), (x0, ym)),
                        ("g", (x0, ym), (x1, ym))):
            if s in lit:
                d.line([a, b], fill=1, width=2)
        return
    tf = (ph - t0) / fly
    if tf >= 1.0:                                        # gap -- pad's clear, nothing to draw
        return
    # normalized path: climb the right lane, then bank left across the top (eased moves overlap)
    pos = lambda u: (0.90 + (-0.20 - 0.90) * smoothstep((u - 0.45) / 0.55),
                     1.12 + (0.12 - 1.12) * smoothstep(u / 0.55))
    fx, fy = pos(tf)
    cx, cy = fx * W, fy * H
    nx, ny = pos(min(1.0, tf + 0.02))                   # heading from the path tangent
    ang = math.atan2(ny * H - cy, nx * W - cx)
    ca, sa = math.cos(ang), math.sin(ang)
    R = lambda px, py: (cx + px * ca - py * sa, cy + px * sa + py * ca)  # local (nose +x) -> screen
    for k in range(1, 9):                                # a cloud of smoke trailing behind
        if tf - k * 0.05 < 0:
            break
        sx, sy = pos(tf - k * 0.05)
        sx, sy, rad = sx * W, sy * H, 1.0 + k * 0.7
        j = math.sin(k * 2.3) * rad * 0.4               # deterministic puffiness
        if k <= 3:
            d.ellipse([sx - rad, sy - rad, sx + rad, sy + rad], fill=1)
        else:
            d.ellipse([sx - rad + j, sy - rad - j, sx + rad + j, sy + rad - j], outline=1)
    flame = 4 + (math.sin(now * 24) + 1) * 2            # flickering exhaust
    d.polygon([R(-5, -2), R(-5, 2), R(-5 - flame, 0)], fill=1)     # exhaust plume
    d.polygon([R(-4, -3), R(-8, -6), R(-4, -1)], fill=1)          # top fin
    d.polygon([R(-4, 3), R(-8, 6), R(-4, 1)], fill=1)             # bottom fin
    d.polygon([R(3, -3), R(3, 3), R(-5, 3), R(-5, -3)], fill=1)   # body
    d.polygon([R(8, 0), R(3, -3), R(3, 3)], fill=1)              # nose cone
    wx, wy = R(0, 0)
    d.ellipse([wx - 1.5, wy - 1.5, wx + 1.5, wy + 1.5], fill=0)  # porthole


def prompt(d, W, H, now, ox=0.0, oy=0.0):  # a terminal prompt with a blinking block cursor -- "waiting"
    bx, by = W / 2 - 8, H - 14                            # prompt origin
    d.line([bx, by + 1, bx + 4, by + 5], fill=1, width=2)   # '>' chevron, upper stroke
    d.line([bx, by + 9, bx + 4, by + 5], fill=1, width=2)   # '>' chevron, lower stroke
    if (now * 1.5) % 1.0 < 0.5:                           # blink the cursor ~ once a second
        d.rectangle([bx + 8, by, bx + 6, by + 10], fill=1)  # block cursor
