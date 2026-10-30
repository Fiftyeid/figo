"""Tiny easing / keyframe helpers."""
from __future__ import annotations

import math


def clamp(x, a=0.0, b=1.0):
    return a if x < a else (b if x > b else x)


def lerp(a, b, t):
    return a + (b - a) * t


def out_cubic(t):
    t = clamp(t)
    return 1 - (1 - t) ** 3


def in_cubic(t):
    t = clamp(t)
    return t ** 3


def in_out(t):
    t = clamp(t)
    return 3 * t * t - 2 * t * t * t


def out_back(t, s=1.6):
    t = clamp(t)
    return 1 + (s + 1) * (t - 1) ** 3 + s * (t - 1) ** 2


def out_expo(t):
    t = clamp(t)
    return 1.0 if t >= 1 else 1 - 2 ** (-10 * t)


def pulse(t, a=0.0, b=1.0):
    """0 outside [a,b], smooth 0->1->0 inside."""
    if t <= a or t >= b:
        return 0.0
    x = (t - a) / (b - a)
    return math.sin(math.pi * x) ** 0.8


def ramp(t, t0, dur):
    """Normalised progress of a segment starting at t0."""
    if dur <= 0:
        return 1.0 if t >= t0 else 0.0
    return clamp((t - t0) / dur)


def window(t, t0, t1, fin=0.28, fout=0.22):
    """alpha for an element visible between t0..t1 with fade in/out."""
    if t < t0 or t > t1:
        return 0.0
    a = ramp(t, t0, fin)
    b = 1.0 - ramp(t, t1 - fout, fout)
    return min(a, b)
