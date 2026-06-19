"""Robot -- the body Pip lives in: wires the OLED face, animation engine and tools.

Construction is side-effect-free (no threads, no I/O). Call start() to begin animating
and wire the background feeds. The chat loop lives in assistant/brain.py, the demo menu
in demo.py -- Robot itself just is the body.
"""
from __future__ import annotations

import os
import time

from modules.assistant.tools import build_tools
from modules.espbridge import gps
from modules.espbridge.display import NullDisplay, WindowDisplay, connect_display
from modules.espbridge.eyes import EyeEngine
from modules.espbridge.eyes.actions import ping_pong
from modules.espbridge.eyes.vibes import solarflare
from modules.espbridge.eyes.widgets import battery_gauge, weather


class Robot:
    def __init__(self, *, no_display=False):
        self.bridge_mgr = None
        self.oled = self._connect_oled(no_display)
        self.eyes = EyeEngine(self.oled.show, width=self.oled.width,
                              height=self.oled.height, fps=int(os.getenv("ROBOT_FPS", "24")),
                              set_brightness=self.oled.contrast,
                              bright=int(os.getenv("ROBOT_BRIGHTNESS", "255")))
        self.tools = build_tools(self.eyes, self.bridge_mgr)
        self._started = False

    def start(self):
        """Begin animating and wire the background feeds. Idempotent; call once before running.
        Kept out of __init__ so building a Robot has no side effects (threads, BLE, network)."""
        if self._started:
            return self
        self._started = True
        self.eyes.start()
        self._workers()
        return self

    def _connect_oled(self, no_display):
        """Pick the display backend: an on-screen window, the real OLED over BLE, or a headless stub."""
        if no_display:
            return WindowDisplay()               # emulate the 128x64 OLED on screen -- no board
        try:
            self.bridge_mgr, oled = connect_display()
            return oled
        except Exception as e:                   # no board / no bridge -> face-only stub
            print(f"[robot] no display ({e}); running face-only", flush=True)
            return NullDisplay()

    def _workers(self):
        """Start the background feeds that keep Pip alive on its own -- real-world data wired to looping
        effects. Daemon threads / one-shot binds; nothing here blocks."""
        weather.bind(gps.locate)                 # weather uses the host's real location, IP as fallback
        solarflare.watch(lambda: self.eyes.set_activity("solarflare"))   # yesterday's real M+ flares, replayed today
        if self.bridge_mgr is None:              # the rest read the physical board -> only with a link
            return
        ping_pong.bind(lambda: self.bridge_mgr.bridge().ping())          # real RTT off the live link
        pin = int(os.getenv("PIP_BATTERY_PIN", "34"))            # GPIO34: ADC1, input-only
        chg_pin = os.getenv("PIP_CHARGE_PIN")                    # e.g. TP4056 CHRG pin; unset = unknown
        def read_mv():
            b = self.bridge_mgr.bridge()
            b.adc.config(pin, atten=11)                         # ~3.3V range; idempotent, survives reconnect
            return b.adc.read_mv(pin)
        def charging():
            b = self.bridge_mgr.bridge()
            b.gpio.mode(int(chg_pin), "input_pullup")           # CHRG is open-drain: pulled low while charging
            return not b.gpio.read(int(chg_pin))
        battery_gauge.bind(read_mv, charging if chg_pin else None)

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
        return self.start()

    def __exit__(self, *exc):
        self.shutdown()
