#!/usr/bin/env python3
"""Thumbnail for the countdown cut: one huge rank numeral, one airframe, 19 ticks.

The chapter film's thumbnail is a dark hero on a warm sweep under one wide
headline. This one has to read as a *different video* at 320 px while still
belonging to the same channel, so it flips the composition instead of the
palette: the film's own white cyclorama, the numeral that drives the countdown
as the dominant shape on the left, and the progress bar from the video along
the bottom. Same type, same stage, different sentence.

    python3 video/thumbnail_countdown.py
    python3 video/thumbnail_countdown.py --num 07 --asset ch47j --out build/alt.jpg
"""
from __future__ import annotations

import argparse
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from engine import config as C                      # noqa: E402
from engine import pixels as P                      # noqa: E402
from engine.scenes import Stage, camera, fit, paste_rgba, tw   # noqa: E402

ROOT = os.path.dirname(HERE)
ASSETS = os.path.join(ROOT, "assets", "fleet")

W, H = 1280, 720                    # authored in 1920x1080, downsampled on save
RED = (188, 0, 45)


def stage() -> Image.Image:
    """The film's own cyclorama, pushed in slightly so it is not dead flat."""
    return camera(Stage().frame(), 1.04, cy=C.H * 0.56)


def place(frame: Image.Image, key: str, cx: int, box_w: int, box_h: int,
          baseline: int, shadow_k: float = 0.55) -> tuple:
    """Paste one airframe with the film's contact shadow. Returns its box."""
    path = os.path.join(ASSETS, f"{key}.png")
    spr = fit(path, box_w, box_h)
    x, y = int(cx - spr.width / 2), int(baseline - spr.height)

    rgb, m = P.shadow(path, spr.height, spread=56, opacity=0.18)
    sw = int(spr.width * 1.10)
    sh = max(10, int(m.height * 0.13))
    m2 = m.resize((max(8, sw), sh), Image.BILINEAR).point(lambda v: int(v * shadow_k))
    frame.paste(rgb.getpixel((0, 0)),
                (int(cx - m2.width / 2), int(baseline - m2.height * 0.34)), m2)
    paste_rgba(frame, spr, (x, y))
    return x, y, x + spr.width, y + spr.height


def ticks(frame: Image.Image, n: int, lit: int, x0: int, y: int,
          w: int = 34, gap: int = 10, h: int = 7) -> None:
    """The film's progress bar, run to the last entry."""
    d = ImageDraw.Draw(frame, "RGBA")
    for k in range(n):
        on = k < lit
        col = C.CHARCOAL if k == lit - 1 else (RED if on else (206, 211, 217))
        d.rectangle([x0 + k * (w + gap), y, x0 + k * (w + gap) + w, y + h],
                    fill=col + (255 if on else 170,))


def compose(num: str, asset: str, kicker: str, word: str, out: str,
            total: int = 19) -> str:
    f = stage()

    # ---- left column: kicker, numeral, word, red rule
    P.draw_text(f, (C.SAFE + 4, 150), kicker, "bold", 46, C.INK_DIM,
                tracking=11, anchor="lt")

    num_size = int(P.fit_size(num, "black", 560, 620, -16))
    P.draw_text(f, (C.SAFE - 6, 224), num, "black", num_size, C.INK,
                tracking=-16, anchor="lt")

    word_y = 224 + int(num_size * 1.00)
    P.draw_text(f, (C.SAFE + 4, word_y), word, "black", 104, C.INK,
                tracking=-3, anchor="lt")

    d = ImageDraw.Draw(f, "RGBA")
    d.rectangle([C.SAFE + 4, word_y + 150, C.SAFE + 184, word_y + 162], fill=RED + (255,))

    # ---- right half: the airframe, wheels on the floor line
    place(f, asset, 1232, 1330, 800, 1024)

    # ---- bottom: the video's own progress bar, run to the last entry
    span = total * 64 + (total - 1) * 12
    ticks(f, total, total, (C.W - span) // 2, 1038, w=64, gap=12, h=9)

    _finish(f, out)
    print(f"  {out}  numeral {num_size}px  word {tw(word, 'black', 104, -3)}px")
    return out


def _finish(f: Image.Image, out: str) -> Image.Image:
    """Full 1920x1080 master + a light unsharp, sized to stay under 2 MB."""
    img = f.convert("RGB")
    a = np.asarray(img).astype(np.float32)
    blur = np.asarray(img.filter(ImageFilter.GaussianBlur(1.6))).astype(np.float32)
    img = Image.fromarray(np.clip(a + (a - blur) * 0.55, 0, 255).astype(np.uint8), "RGB")
    img.save(out.replace(".jpg", ".png"))
    for q in (95, 92, 88, 84, 80):
        img.save(out, quality=q, subsampling=0)
        if os.path.getsize(out) < 2_000_000:
            break
    return img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--num", default="19")
    ap.add_argument("--asset", default="f15j")
    ap.add_argument("--kicker", default="JAPAN  ·  2026")
    ap.add_argument("--word", default="AIRCRAFT")
    ap.add_argument("--out", default=os.path.join(ROOT, "deliverables",
                                                  "thumb_japan_countdown.jpg"))
    args = ap.parse_args()
    compose(args.num, args.asset, args.kicker, args.word, args.out)


if __name__ == "__main__":
    main()
