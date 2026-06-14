"""Connect to the ESP32's OLED over python-esp-bridge (Bluetooth). Env-driven, BLE-only."""
from __future__ import annotations

import os


class NullDisplay:
    """Stand-in panel for running with no board attached."""

    width, height = 128, 64

    def show(self, image=None):
        pass

    def clear(self):
        pass


class Display:
    """OLED bound to BridgeManager's live link. BLE has no in-place reconnect, so the
    manager heals a drop by handing back a *new* Bridge; the OLED cached the old one,
    so we rebind it here. Render-loop errors are already tolerated by EyeEngine."""

    def __init__(self, mgr, *, sda, scl, width=128, height=64):
        from espbridge.drivers.oled import OLED
        self._OLED, self._mgr = OLED, mgr
        self._kw = {"sda": sda, "scl": scl, "width": width, "height": height}
        self.width, self.height = width, height
        self._bridge = mgr.bridge()                 # first connect (raises -> face-only)
        self._oled = OLED(self._bridge, **self._kw)

    def _panel(self):
        b = self._mgr.bridge()                      # live link, reconnecting on demand
        if b is not self._bridge:                   # healed as a new Bridge -> rebind
            self._bridge, self._oled = b, self._OLED(b, **self._kw)
        return self._oled

    def show(self, image=None):
        self._panel().show(image)

    def clear(self):
        self._panel().clear()


def connect_display():
    """Open a self-healing, BLE-only bridge + OLED from env. Returns (manager, display)."""
    try:
        import espbridge
    except ImportError as e:
        raise RuntimeError("python-esp-bridge not installed -- run `uv sync`.") from e

    target = os.getenv("ROBOT_BLE_TARGET")
    pw = os.getenv("ROBOT_PASSWORD", "espbridge") or None   # firmware password; empty = none
    # A target (name or MAC) goes through `ble=` so the link is BLE-only: no silent
    # USB-serial (COM) fallback, and reconnects stay on Bluetooth. Bare True auto-picks.
    mgr = espbridge.BridgeManager(ble=target or True, password=pw)
    return mgr, Display(mgr,
                        sda=int(os.getenv("ROBOT_OLED_SDA", "21")),
                        scl=int(os.getenv("ROBOT_OLED_SCL", "22")))
