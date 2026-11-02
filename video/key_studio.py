#!/usr/bin/env python3
"""Key generated studio plates: sweep and painted shadow both go.

The plates are a grey airframe on a near-white sweep with a soft drop shadow
painted on the floor. Luminance alone separates them cleanly — the airframe
sits far below the shadow — so this pass uses a soft luminance ramp instead of
a flood:

    alpha = 1 below LO, 0 above HI, linear in between

then keeps only the connected components big enough to be the aircraft, and
fills any enclosed holes. That also deletes the stray ceiling corners some
plates came back with, because they are small and unconnected.

    python3 video/key_studio.py assets_raw/aircraft assets/versus
    python3 video/key_studio.py --lo 0.86 --hi 0.94     # a paler airframe
"""
from __future__ import annotations

import argparse
import os

import numpy as np
from PIL import Image
from scipy import ndimage


def key(path: str, level: float = 0.935) -> Image.Image:
    """Backdrop = the pure-white sweep, reached from the frame border.

    Two things the plates do that a single threshold misses:

    * a soft shadow sits on the floor *beside* the airframe, so it survives a
      white-only flood as a wide, thin island well below the paint;
    * the cockpit canopy is bright and enclosed by paint, so it must not be
      treated as backdrop just because it is white.

    So: flood the near-white from the border, then keep only the components
    that live in the same vertical band as the airframe. A shadow band, a
    stray ceiling corner and a floor puddle all fail that test.
    """
    im = Image.open(path).convert("RGB")
    rgb = np.asarray(im).astype(np.float32) / 255.0
    lum = 0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]

    white = lum >= level
    lab, n = ndimage.label(white, np.ones((3, 3)))
    bg = np.zeros_like(white)
    if n:
        border = set(np.unique(np.concatenate(
            [lab[0, :], lab[-1, :], lab[:, 0], lab[:, -1]])).tolist())
        border.discard(0)
        bg = np.isin(lab, list(border))

    solid = ~bg
    solid = ndimage.binary_fill_holes(solid)          # canopy is enclosed: keep
    solid = ndimage.binary_opening(solid, np.ones((3, 3)), iterations=1)

    # keep the components that share the airframe's vertical band
    lab2, n2 = ndimage.label(solid, np.ones((3, 3)))
    if n2 > 1:
        sizes = ndimage.sum(solid, lab2, range(1, n2 + 1))
        main = int(np.argmax(sizes)) + 1
        ys, _ = np.where(lab2 == main)
        y0, y1 = ys.min(), ys.max()
        span = max(1, y1 - y0)
        keep = [main]
        for i in range(1, n2 + 1):
            if i == main or sizes[i - 1] < 1200:
                continue
            ci, _ = np.where(lab2 == i)
            overlap = min(ci.max(), y1) - max(ci.min(), y0)
            if overlap / span > 0.45:                 # tall enough to be paint
                keep.append(i)
        solid = np.isin(lab2, keep)

    soft = ndimage.gaussian_filter(solid.astype(np.float32), 0.8)
    alpha = np.clip((soft - 0.15) / 0.70, 0, 1)

    # un-mix the pale fringe so the edge is paint, not background bleed
    fringe = (alpha > 0.02) & (alpha < 0.95)
    for c in range(3):
        ch = rgb[..., c]
        ch = np.where(fringe,
                      np.clip((ch - (1 - alpha) * 0.98) / np.maximum(alpha, 1e-3), 0, 1), ch)
        rgb[..., c] = ch

    out = Image.fromarray((np.clip(np.dstack([rgb, alpha[..., None]]), 0, 1) * 255)
                          .astype(np.uint8), "RGBA")
    bb = out.split()[3].getbbox()
    return out.crop(bb) if bb else out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src", nargs="?", default="assets_raw/aircraft")
    ap.add_argument("dst", nargs="?", default="assets/versus")
    ap.add_argument("--level", type=float, default=0.870)
    args = ap.parse_args()
    os.makedirs(args.dst, exist_ok=True)
    for name in sorted(os.listdir(args.src)):
        if not name.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
            continue
        out = key(os.path.join(args.src, name), args.level)
        a = np.asarray(out.split()[3], np.float32) / 255.0
        print(f"  {name:14s} {out.width:4d}x{out.height:<4d} cover {a.mean():5.1%}")
        out.save(os.path.join(args.dst, os.path.splitext(name)[0] + ".png"))


if __name__ == "__main__":
    main()
