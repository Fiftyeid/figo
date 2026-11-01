#!/usr/bin/env python3
"""COUNTDOWN: the fleet as a ranked list.

Different edit, same stage.  The EP.03 film is a tour — chapter after chapter
of a roster.  This is the other YouTube format: a count, one airframe per
beat, a huge rank number, and a single line of label under it.  Every cut is
a hard cut with its own dolly, exactly like the EP.03 cold open, so the two
films feel like the same channel without being the same edit.

    python3 video/countdown.py --proof            # 8-entry motion proof
    python3 video/countdown.py --still 3          # one frame
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import build as B  # noqa: E402
from engine import config as C  # noqa: E402
from engine import pixels as P  # noqa: E402
from engine.fleet import FleetRenderer, _hook_halo, _paleness  # noqa: E402
from engine.scenes import camera, fit, paste_rgba  # noqa: E402

ROOT = os.path.dirname(HERE)

BASE = 806
BOX = (1472, 528)
JP_RED = (188, 0, 45)

# proof line-up: real SINCE dates already used in EP.03, oldest first.
PROOF = [
    ("fleet/f15j", "F-15J EAGLE", "SINCE 1981"),
    ("fleet/c130", "C-130H HERCULES", "SINCE 1984"),
    ("fleet/ch47j", "CH-47J CHINOOK", "SINCE 1986"),
    ("fleet/t4", "KAWASAKI T-4", "SINCE 1988"),
    ("fleet/f2", "MITSUBISHI F-2", "SINCE 2000"),
    ("fleet/kc767", "KC-767", "SINCE 2008"),
    ("fleet/c2", "KAWASAKI C-2", "SINCE 2016"),
    ("fleet/f35", "F-35 LIGHTNING II", "B MODELS 2025"),
]


def _airframe(f, path, cx, baseline, zoom_alpha=1.0):
    spr = fit(path, BOX[0], BOX[1])
    x, y = int(cx - spr.width / 2), int(baseline - spr.height)

    halo, pad = _hook_halo(path, BOX[0], BOX[1])
    strength = 0.16 + 0.34 * _paleness(path)
    f.paste((150, 154, 160), (x - pad, y - pad), halo.point(lambda v: int(v * strength)))

    rgb, m = P.shadow(path, spr.height, spread=56, opacity=0.18)
    sw = int(spr.width * 1.14)
    sh = max(10, int(m.height * 0.12))
    m2 = m.resize((max(8, sw), sh), Image.BILINEAR).point(lambda v: int(v * 0.55))
    f.paste(rgb.getpixel((0, 0)), (int(cx - m2.width / 2),
                                  int(baseline - m2.height * 0.30)), m2)
    paste_rgba(f, spr, (x, y))


class CountdownRenderer(FleetRenderer):
    """One rank per beat: number, airframe, label.  Nothing else."""

    def __init__(self, entries, assets_dir):
        super().__init__([], "", assets_dir, [], 0.0)
        self.entries = entries
        self.n = len(entries)

    def frame(self, local: float, total: float) -> Image.Image:
        slot = total / self.n
        i = min(self.n - 1, int(local / slot))
        u = local - i * slot
        p = C.clamp(u / slot)
        key, name, meta = self.entries[i]

        f = self.stage.frame()
        path = self.asset(key)
        if path:
            _airframe(f, path, C.DIVIDER_X, BASE)

        # the move: alternating dolly, so consecutive beats never feel alike
        z = 1.0 + 0.045 * (C.ease_in_out(p) if i % 2 == 0 else 1.0 - C.ease_in_out(p))
        f = camera(f, z, cy=C.H * 0.52)

        self._chrome(f, i, name, meta, p, slot)
        return f

    # ------------------------------------------------------------ chrome
    def _chrome(self, f, i, name, meta, p, slot):
        rank = f"{i + 1:02d}"
        total = f"{self.n:02d}"

        # rank number, left rail: big enough to read at thumbnail size
        e = C.ramp(p, 0.0, 0.22, C.ease_out_expo)
        size = 208
        ny = 300 - (1 - e) * 26
        P.draw_text(f, (C.SAFE + 6, ny), rank, "black", size, C.INK, tracking=-6,
                    anchor="lt", alpha=e)
        P.draw_text(f, (C.SAFE + 10, ny + size + 2), total, "bold", 34, C.INK_FAINT,
                    tracking=4, anchor="lt", alpha=e)

        d = ImageDraw.Draw(f, "RGBA")
        d.line([(C.SAFE, ny - 26), (C.SAFE + 150, ny - 26)],
               fill=JP_RED + (int(230 * e),), width=5)

        # label under the aircraft, centred
        le = C.ramp(p, 0.06, 0.26, C.ease_out_expo)
        nsize = P.fit_size(name, "bold", 1040, 56, 4)
        ly = 844 - (1 - le) * 14
        P.draw_text(f, (C.DIVIDER_X, ly), name, "bold", nsize, C.INK, tracking=3,
                    anchor="mt", alpha=le)
        P.draw_text(f, (C.DIVIDER_X, ly + nsize + 14), meta, "bold", 22, C.INK_DIM,
                    tracking=8, anchor="mt", alpha=le)

        # a tick per entry along the bottom: the count made visible
        w, gap = 34, 10
        span = self.n * w + (self.n - 1) * gap
        x0 = C.DIVIDER_X - span / 2
        y = 986
        for k in range(self.n):
            on = k <= i
            col = (C.CHARCOAL if k == i else (JP_RED if on else (206, 211, 217)))
            d.rectangle([x0 + k * (w + gap), y, x0 + k * (w + gap) + w, y + 6],
                        fill=col + (255 if on else 150,))


def render(entries, out, w=C.W, h=C.H, fps=C.FPS, per=2.4, only_frames=None):
    r = CountdownRenderer(entries, os.path.join(ROOT, "assets"))
    total = per * len(entries)
    n = int(total * fps)
    cmd = [B.FFMPEG, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{w}x{h}", "-r", str(fps), "-i", "-",
           "-c:v", "libx264", "-preset", "fast", "-crf", "20", "-pix_fmt", "yuv420p",
           "-movflags", "+faststart", out]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    t0 = time.time()
    for k in range(n):
        f = r.frame(k / fps, total)
        if f.size != (w, h):
            f = f.resize((w, h), Image.LANCZOS)
        proc.stdin.write(np.asarray(f, dtype=np.uint8).tobytes())
        if k % 30 == 0:
            print(f"\r  {k}/{n}", end="", flush=True)
    proc.stdin.close()
    proc.wait()
    print(f"\n  {out}  ({n} frames, {time.time()-t0:.0f}s)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--proof", action="store_true")
    ap.add_argument("--still", type=float, default=None, help="seconds into the proof")
    ap.add_argument("--per", type=float, default=2.4, help="seconds per entry")
    ap.add_argument("--w", type=int, default=1280)
    ap.add_argument("--h", type=int, default=720)
    ap.add_argument("--out", default=os.path.join(ROOT, "build", "countdown_proof.mp4"))
    args = ap.parse_args()

    if args.still is not None:
        r = CountdownRenderer(PROOF, os.path.join(ROOT, "assets"))
        total = args.per * len(PROOF)
        r.frame(args.still, total).save(
            os.path.join(ROOT, "build", "countdown_still.png"))
        print("  build/countdown_still.png")
        return

    render(PROOF, args.out, args.w, args.h, per=args.per)


if __name__ == "__main__":
    main()
