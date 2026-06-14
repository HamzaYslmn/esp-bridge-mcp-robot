"""Robot -- wires the OLED face, animation engine and tools; runs the chat loop."""
from __future__ import annotations

import os
import time

from modules.assistant.tools import build_tools
from modules.espbridge.display import NullDisplay, connect_display
from modules.espbridge.eyes import ACTIVITIES, EMOTIONS, GESTURES, EyeEngine


class Robot:
    def __init__(self, *, no_display=False):
        self.bridge_mgr = None
        if no_display:
            self.oled = NullDisplay()
        else:
            try:
                self.bridge_mgr, self.oled = connect_display()
            except Exception as e:  # no board / no bridge -> face-only stub
                print(f"[robot] no display ({e}); running face-only", flush=True)
                self.oled = NullDisplay()

        self.eyes = EyeEngine(self.oled.show, width=self.oled.width,
                             height=self.oled.height, fps=int(os.getenv("ROBOT_FPS", "24")))
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

    def demo(self):
        """Interactive menu: pick an emotion, gesture or activity to play."""
        moods = list(EMOTIONS)
        gestures = [g for g in GESTURES if g != "none"]
        activities = [a for a in ACTIVITIES if a != "idle"]
        items = ([("mood", m) for m in moods] + [("gesture", g) for g in gestures]
                 + [("activity", a) for a in activities])

        def show_menu():
            print("\n=== Pip demo menu ===")
            for i, (kind, name) in enumerate(items, 1):
                print(f"  {i:>2}. [{kind}] {name}")
            print("  a. play all (2s each)   q. quit")

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
