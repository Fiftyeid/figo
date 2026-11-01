#!/usr/bin/env python3
"""Motion study: five ways to move from one airframe to the next.

The cold open has to feel like an edit, not an effect, so this renders the
same short roster five times — once per transition — back to back, so one
can be picked by eye and then wired into `FleetRenderer.draw_hook`.

    python3 video/motion_study.py                 # build/motion_study.mp4
    python3 video/motion_study.py --w 1280 --h 720
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import build as B  # noqa: E402
from engine import config as C  # noqa: E402
from engine import pixels as P  # noqa: E402
from engine.fleet import FleetRenderer, _paleness  # noqa: E402
from engine.scenes import fit, paste_rgba  # noqa: E402
from content_japan import INTRO_NARRATION, SECTIONS as S  # noqa: E402

ROOT = os.path.dirname(HERE)

PICKS = ["fleet/f15j", "fleet/f35", "fleet/p1", "fleet/ch47j"]
SLOT = 0.55
STYLES = [
    ("A", "HARD CUT", "قطع مباشر"),
    ("B", "PUSH", "دفع أفقي"),
    ("C", "WIPE", "مسح"),
    ("D", "DISSOLVE", "تلاشي"),
    ("E", "CONVEYOR", "شريط متحرك"),
]
BASE = 806
BOX = (1472, 528)


# ---------------------------------------------------------------- one card
def draw_card(f, path, cx, baseline, alpha=1.0, lift=0.0, scale=1.0, blur=0.0):
    """An airframe on the showroom: wall wash, contact shadow, sprite."""
    if alpha <= 0.01 or not path:
        return
    spr = fit(path, int(BOX[0] * scale), int(BOX[1] * scale))
    if blur > 0.2:
        spr = spr.filter(ImageFilter.GaussianBlur(blur))
    x, y = int(cx - spr.width / 2), int(baseline - spr.height - lift)

    halo = Image.new("L", (spr.width + 120, spr.height + 120), 0)
    halo.paste(spr.split()[3].point(lambda v: 255 if v > 120 else 0), (60, 60))
    halo = halo.filter(ImageFilter.GaussianBlur(34))
    strength = (0.16 + 0.34 * _paleness(path)) * alpha
    if x > -spr.width and x < C.W:
        f.paste((150, 154, 160), (x - 60, y - 60), halo.point(lambda v: int(v * strength)))

    if x > -spr.width and x < C.W:
        rgb, m = P.shadow(path, spr.height, spread=56, opacity=0.18)
        sw = int(spr.width * 1.14)
        sh = max(10, int(m.height * 0.12))
        m2 = m.resize((max(8, sw), sh), Image.BILINEAR)
        m2 = m2.point(lambda v: int(v * alpha * 0.55))
        f.paste(rgb.getpixel((0, 0)),
                (int(cx - m2.width / 2), int(baseline - m2.height * 0.30)), m2)

    paste_rgba(f, spr, (x, y), alpha)


def _i(t, slot=SLOT):
    return int(t / slot), (t % slot) / slot


# ---------------------------------------------------------------- styles
def frame_cut(r, t):
    """A: no transition at all — the new airframe is simply there."""
    i, p = _i(t)
    f = r.stage.frame()
    draw_card(f, r.asset(PICKS[i % len(PICKS)]), C.W / 2, BASE)
    return f


def frame_push(r, t):
    """B: the next airframe shoves the current one off to the left."""
    i, p = _i(t)
    e = C.ease_out_expo(C.clamp(p / 0.30))
    off = C.W * (1 - e)
    f = r.stage.frame()
    draw_card(f, r.asset(PICKS[i % len(PICKS)]), C.W / 2 - off, BASE)
    draw_card(f, r.asset(PICKS[(i + 1) % len(PICKS)]), C.W / 2 + C.W - off, BASE)
    return f


def frame_wipe(r, t):
    """C: a hard edge sweeps across and leaves the next airframe behind it."""
    i, p = _i(t)
    f = r.stage.frame()
    draw_card(f, r.asset(PICKS[i % len(PICKS)]), C.W / 2, BASE)
    if i + 1 >= len(PICKS):
        return f
    e = C.ease_in_out(C.clamp(p / 0.28))
    if e <= 0.005:
        return f
    layer = Image.new("RGBA", (C.W, C.H), (0, 0, 0, 0))
    draw_card(layer, r.asset(PICKS[(i + 1) % len(PICKS)]), C.W / 2, BASE)
    x = int(C.W * e)
    m = ImageChops.multiply(layer.split()[3],
                            Image.new("L", (C.W, C.H), 0).crop((0, 0, x, C.H)).resize((C.W, C.H))
                            if False else _bar(x))
    f.paste(layer.convert("RGB"), (0, 0), m)
    ImageDraw.Draw(f, "RGBA").line([(x, 0), (x, C.H)], fill=(26, 29, 34, 45), width=3)
    return f


def _bar(x):
    m = Image.new("L", (C.W, C.H), 0)
    if x > 0:
        ImageDraw.Draw(m).rectangle([0, 0, x, C.H], fill=255)
    return m


def frame_dissolve(r, t):
    """D: cross-fade, with a short scale drift so it isn't a dead mix."""
    i, p = _i(t)
    e = C.ease_in_out(C.clamp(p / 0.34))
    f = r.stage.frame()
    draw_card(f, r.asset(PICKS[i % len(PICKS)]), C.W / 2, BASE, alpha=1 - e,
              scale=1.0 + 0.02 * e, blur=6 * e)
    if i + 1 < len(PICKS):
        draw_card(f, r.asset(PICKS[(i + 1) % len(PICKS)]), C.W / 2, BASE, alpha=e,
                  scale=0.985 + 0.015 * e, blur=6 * (1 - e))
    return f


def frame_conveyor(r, t):
    """E: one continuous right-to-left conveyor — the roster never stops."""
    f = r.stage.frame()
    span = C.W * 1.06
    for i in range(len(PICKS) + 1):
        cx = C.W / 2 + (i - t / SLOT) * span
        if -span < cx - C.W / 2 < span:
            draw_card(f, r.asset(PICKS[i % len(PICKS)]), cx, BASE)
    return f


FRAMES = {"A": frame_cut, "B": frame_push, "C": frame_wipe,
          "D": frame_dissolve, "E": frame_conveyor}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "build", "motion_study.mp4"))
    ap.add_argument("--w", type=int, default=C.W)
    ap.add_argument("--h", type=int, default=C.H)
    args = ap.parse_args()

    segs, total = B.build_timeline(os.path.join(ROOT, "audio", "vo_jp"), None, S, hook=None)
    r = FleetRenderer(S, INTRO_NARRATION, os.path.join(ROOT, "assets"), segs, total)
    r._seg_dur = SLOT * len(PICKS)

    block = SLOT * len(PICKS)          # each style runs one full pass
    n_frames = int(round(block * len(STYLES) * C.FPS))
    cmd = [B.FFMPEG, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{args.w}x{args.h}", "-r", str(C.FPS), "-i", "-",
           "-c:v", "libx264", "-preset", "fast", "-crf", "19", "-pix_fmt", "yuv420p",
           "-movflags", "+faststart", args.out]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    t0 = time.time()
    for f in range(n_frames):
        t = f / C.FPS
        s = min(len(STYLES) - 1, int(t / block))
        key, name, ar = STYLES[s]
        local = t - s * block
        base = r.stage.frame()
        r._global_t = t
        base = FRAMES[key](r, local) or base
        P.draw_pill(base, 54, 44, f"{key}   {name}", size=19, fg=C.PAPER, bg=C.CHARCOAL,
                    tracking=4, pad_x=18, pad_y=10)
        P.draw_text(base, (C.W - 54, 56), f"{s + 1} / {len(STYLES)}", "bold", 16,
                    C.INK_FAINT, tracking=4, anchor="rt")
        if (args.w, args.h) != (C.W, C.H):
            base = base.resize((args.w, args.h), Image.LANCZOS)
        proc.stdin.write(np.asarray(base, dtype=np.uint8).tobytes())
        if f % 30 == 0:
            print(f"\r  {f}/{n_frames}", end="", flush=True)
    proc.stdin.close()
    proc.wait()
    print(f"\n  {args.out}  ({n_frames} frames, {time.time()-t0:.0f}s)")


if __name__ == "__main__":
    main()
