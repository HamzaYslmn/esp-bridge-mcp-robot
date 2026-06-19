"""Interactive demo menu -- pick any mood / gesture / activity to play, or save a GIF.
Dev tooling next to the launcher (cli.py dispatches it); drives a started Robot's eyes."""
from __future__ import annotations

import time

from modules.espbridge.eyes import ACTIONS, GESTURES, MOODS, REACTIONS, VIBES, WIDGETS


def _menu_items():
    """The flat (kind, name) list the demo menu numbers index into. One-shots (gestures,
    reactions) then loops (activities, vibes, widgets) sit contiguous, so the columns map."""
    return ([("mood", m) for m in MOODS]
            + [("gesture", g) for g in GESTURES]
            + [("reaction", r) for r in REACTIONS]
            + [("activity", a) for a in ACTIONS]
            + [("vibe", v) for v in VIBES]
            + [("widget", w) for w in WIDGETS])


def _capture(token, items):
    """Render a 30s GIF for a 'gNN'/'gNAME' token -- develop the face with no OLED."""
    body = token[1:]
    if body.isdigit() and 1 <= int(body) <= len(items):
        kind, name = items[int(body) - 1]
    else:
        match = next((it for it in items if it[1] == body), None)
        if not match:
            print(f"can't GIF {token!r} (use gNN or gNAME from the menu)")
            return
        kind, name = match
    from modules.espbridge.eyes.record import record_gif
    print(f"-> rendering 30s GIF of {kind}: {name} ...")
    print(f"wrote {record_gif(name)}")


def demo(robot, capture=None):
    """Interactive menu: pick an emotion, gesture or activity to play."""
    eyes = robot.eyes
    items = _menu_items()
    if capture:                                  # non-interactive: render one GIF and exit
        _capture(capture, items)
        return
    moods = [n for k, n in items if k == "mood"]
    gestures = [n for k, n in items if k == "gesture"]
    reactions = [n for k, n in items if k == "reaction"]
    activities = [n for k, n in items if k == "activity"]
    vibes = [n for k, n in items if k == "vibe"]
    widgets = [n for k, n in items if k == "widget"]

    def show_menu():
        # six side-by-side columns (one per folder); the printed number indexes into `items`,
        # so each column's offset is the running total of the columns before it.
        nm, ng, nr, na, nv = (len(moods), len(gestures), len(reactions),
                              len(activities), len(vibes))
        cols = [("MOODS", moods, 0),
                ("GESTURES", gestures, nm),
                ("REACTIONS", reactions, nm + ng),
                ("ACTIONS", activities, nm + ng + nr),
                ("VIBES", vibes, nm + ng + nr + na),
                ("WIDGETS", widgets, nm + ng + nr + na + nv)]
        w = max(len(n) for _, n in items)                       # widest name
        cw = w + 4                                              # "NN. " prefix + name
        total = cw * len(cols) + 3 * (len(cols) - 1)            # name cells + " | " gutters
        cell = lambda i, n: f"{i:>2}. {n:<{w}}"
        print("\n  " + "=" * total)
        print("  " + " Pip demo menu".ljust(total))
        print("  " + "=" * total)
        print("  " + " | ".join(f"{t:<{cw}}" for t, _, _ in cols))
        print("  " + "-+-".join("-" * cw for _ in cols))
        for r in range(max(len(c[1]) for c in cols)):
            cells = [cell(off + r + 1, lst[r]) if r < len(lst) else " " * cw
                     for _, lst, off in cols]
            while len(cells) > 1 and not cells[-1].strip():     # drop trailing empty columns
                cells.pop()
            print("  " + " | ".join(cells))
        print("  " + "=" * total)
        print("  a = play all (2s each)    gNN = save 30s GIF    q = quit    (number or name)")

    def play(kind, name):
        print(f"-> {kind}: {name}")
        if kind == "mood":
            eyes.set_activity("idle")
            eyes.set_mood(name)
        elif kind in ("gesture", "reaction"):    # both are one-shot moves
            eyes.play_gesture(name)
        else:                                    # activity, vibe or widget -- all loop
            eyes.set_mood("neutral")
            eyes.set_activity(name)

    show_menu()
    while True:
        try:
            choice = input("demo> ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not choice:
            show_menu()
            continue
        if choice in {"q", "quit", "exit"}:
            break
        if choice == "a":
            for kind, name in items:
                play(kind, name)
                time.sleep(2.0)
            eyes.set_activity("idle")
            continue
        if len(choice) > 1 and choice[0] == "g" and \
                (choice[1:].isdigit() or any(it[1] == choice[1:] for it in items)):
            _capture(choice, items)
            continue
        match = None
        if choice.isdigit() and 1 <= int(choice) <= len(items):
            match = items[int(choice) - 1]
        else:
            match = next((it for it in items if it[1] == choice), None)
        if match:
            play(*match)
        else:
            print(f"unknown: {choice!r} (enter a number, name, 'a', or 'q')")
    eyes.set_activity("idle")
