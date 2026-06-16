"""Robot -- wires the OLED face, animation engine and tools; runs the chat loop."""
from __future__ import annotations

import os
import time

from modules.assistant.tools import build_tools
from modules.espbridge.display import NullDisplay, WindowDisplay, connect_display
from modules.espbridge.eyes import ACTIONS, GESTURES, MOODS, EyeEngine


class Robot:
    def __init__(self, *, no_display=False):
        self.bridge_mgr = None
        if no_display:
            self.oled = WindowDisplay()      # emulate the 128x64 OLED on screen -- no board
        else:
            try:
                self.bridge_mgr, self.oled = connect_display()
            except Exception as e:  # no board / no bridge -> face-only stub
                print(f"[robot] no display ({e}); running face-only", flush=True)
                self.oled = NullDisplay()

        self.eyes = EyeEngine(self.oled.show, width=self.oled.width,
                             height=self.oled.height, fps=int(os.getenv("ROBOT_FPS", "24")),
                             set_brightness=self.oled.contrast,
                             bright=int(os.getenv("ROBOT_BRIGHTNESS", "255")))
        self.eyes.start()
        self.tools = build_tools(self.eyes, self.bridge_mgr)

    def run_chat(self):
        """Local Ollama chat loop in the terminal."""
        from modules.assistant.brain import Brain
        brain = Brain(self.tools, self.eyes)
        print("--- Pip is awake --- (say 'bye' or Ctrl-C to sleep)\n")
        while True:
            try:
                text = input("you> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if not text:
                continue
            if text.lower() in {"bye", "exit", "quit", "q"}:
                break
            self.eyes.play_gesture("blink")
            self.eyes.set_activity("thinking")   # busy face; model may switch it
            try:
                reply = brain.respond(text)
            finally:
                self.eyes.set_activity("idle")    # never leave it stuck busy
            print(f"Pip> {reply}\n")

    def _menu_items(self):
        """The flat (kind, name) list the demo menu numbers index into."""
        return ([("mood", m) for m in MOODS]
                + [("gesture", g) for g in GESTURES]
                + [("activity", a) for a in ACTIONS])

    def _capture(self, token, items):
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
        print(f"wrote {record_gif(kind, name)}")

    def demo(self, capture=None):
        """Interactive menu: pick an emotion, gesture or activity to play."""
        items = self._menu_items()
        if capture:                                  # non-interactive: render one GIF and exit
            self._capture(capture, items)
            return
        moods = [n for k, n in items if k == "mood"]
        gestures = [n for k, n in items if k == "gesture"]
        activities = [n for k, n in items if k == "activity"]

        def show_menu():
            # three side-by-side columns; the printed number is the index into `items`
            cols = [("MOODS", moods, 0),
                    ("GESTURES", gestures, len(moods)),
                    ("ACTIVITIES", activities, len(moods) + len(gestures))]
            w = max(len(n) for _, n in items)                       # widest name
            cw = w + 4                                              # "NN. " prefix + name
            total = cw * 3 + 6                                      # plus two " | " gutters
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
                self.eyes.set_activity("idle")
                self.eyes.set_mood(name)
            elif kind == "gesture":
                self.eyes.play_gesture(name)
            else:
                self.eyes.set_mood("neutral")
                self.eyes.set_activity(name)

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
                self.eyes.set_activity("idle")
                continue
            if len(choice) > 1 and choice[0] == "g" and \
                    (choice[1:].isdigit() or any(it[1] == choice[1:] for it in items)):
                self._capture(choice, items)
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
        self.eyes.set_activity("idle")

    def shutdown(self):
        self.eyes.set_mood("sleepy")
        time.sleep(0.4)
        self.eyes.stop()
        try:
            self.oled.clear()
        except Exception:
            pass
        if self.bridge_mgr is not None:
            self.bridge_mgr.shutdown()   # closes the link

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.shutdown()
