#!/usr/bin/env python3
"""Turn white-background photos into transparent cutouts.

    python3 video/cutout.py                       # assets_raw -> assets
    python3 video/cutout.py shots/ assets/        # custom dirs
    python3 video/cutout.py --check shots/        # just report alpha coverage

The matte works on the "shot on a pure white sweep" convention: any neutral,
near-white pixel becomes transparent, interior holes (trigger guards, helmet
straps) are put back, and edge pixels have their white contamination removed.
"""
from __future__ import annotations

import argparse
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from engine.pixels import matte_white  # noqa: E402

ROOT = os.path.dirname(HERE)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src", nargs="?", default=os.path.join(ROOT, "assets_raw"))
    ap.add_argument("dst", nargs="?", default=os.path.join(ROOT, "assets"))
    ap.add_argument("--check", action="store_true", help="report coverage, write nothing")
    args = ap.parse_args()

    os.makedirs(args.dst, exist_ok=True)
    for name in sorted(os.listdir(args.src)):
        if not name.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
            continue
        src = Image.open(os.path.join(args.src, name))
        out = matte_white(src)
        a = np.asarray(out.split()[3]).astype(np.float32) / 255.0
        cover = float((a > 0.5).mean())
        flag = "  <-- check: subject looks tiny or missing" if cover < 0.03 else ""
        print(f"{name:24s} {out.width:4d}x{out.height:<4d} coverage {cover:6.1%}{flag}")
        if not args.check:
            out.save(os.path.join(args.dst, os.path.splitext(name)[0] + ".png"))


if __name__ == "__main__":
    main()
