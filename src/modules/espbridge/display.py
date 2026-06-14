"""Connect to the ESP32's OLED over python-esp-bridge (Bluetooth). Env-driven."""
from __future__ import annotations

import os


class NullDisplay:
    """Stand-in panel for running with no board attached."""

    width, height = 128, 64

    def show(self, image=None):
        pass

    def clear(self):
        pass


def connect_display():
    """Open the BLE bridge + OLED from env settings. Returns (bridge, oled)."""
    try:
        import espbridge
        from espbridge.drivers.oled import OLED
    except ImportError as e:
        raise RuntimeError("python-esp-bridge not installed -- run `uv sync`.") from e

    target = os.getenv("ROBOT_BLE_TARGET")
    pw = os.getenv("ROBOT_PASSWORD") or None
    if target and ":" in target:                       # a MAC -> direct, fast connect
        bridge = espbridge.connect(mac=target, password=pw)
    else:                                               # a name, or auto-pick first board
        bridge = espbridge.connect(ble=target or True, password=pw)
    oled = OLED(bridge, sda=int(os.getenv("ROBOT_OLED_SDA", "21")),
                scl=int(os.getenv("ROBOT_OLED_SCL", "22")), width=128, height=64)
    return bridge, oled
