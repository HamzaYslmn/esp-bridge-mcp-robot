"""Locked-in compute + a sweeping spinner -- processing."""
import math

from ..spec import Action


def _pose(now):   # locked-in, computing -- a tight steady focus
    return math.sin(now * 1.4) * 4, -2 + math.sin(now * 0.7), 0.92


def _overlay(d, W, H, now, ox=0.0, oy=0.0):  # a sleek arc sweeps around a ring -- "processing"
    cx, cy, rad = W // 2, H - 11, 8
    a0 = int(now * 200) % 360
    d.arc([cx - rad, cy - rad, cx + rad, cy + rad], start=a0, end=a0 + 210, fill=1, width=2)


ACTION = Action("processing", mood="wired", pose=_pose, overlay=_overlay)
