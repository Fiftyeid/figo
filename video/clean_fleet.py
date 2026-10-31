#!/usr/bin/env python3
"""Second pass over fleet cutouts: drop leftover baked studio shadows.

Some product shots carry a soft grey shadow painted onto the white sweep.
Left in, it reads as dirt on the showroom floor.  A shadow is bright,
neutral, low-contrast and only ever in the lower half of the frame; white
paint is bright and neutral but sits behind edges, so a 7 px local-contrast
test tells the two apart.

    python3 video/clean_fleet.py            # in place, assets/fleet
    python3 video/clean_fleet.py --check    # report only
"""
from __future__ import annotations

import argparse
import os

import numpy as np
from PIL import Image
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def clean(path, lo=0.72, satmax=0.062, stdmax=0.026, min_blob=1800):
    im = Image.open(path).convert("RGBA")
    a = np.asarray(im).astype(np.float32) / 255.0
    rgb, al = a[..., :3], a[..., 3]
    lum = 0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]
    sat = rgb.max(axis=2) - rgb.min(axis=2)
    m7 = ndimage.uniform_filter(lum, 7)
    var7 = ndimage.uniform_filter(lum * lum, 7) - m7 * m7
    std7 = np.sqrt(np.clip(var7, 0, None))
    yy = np.arange(a.shape[0], dtype=np.float32)[:, None] / a.shape[0]
    below = np.repeat(np.clip((yy - 0.42) / 0.35, 0, 1), a.shape[1], axis=1)

    cand = ((al > 0.35) & (lum > lo) & (lum < 0.995) & (sat < satmax)
            & (std7 < stdmax) & (below > 0.35))
    cand = ndimage.binary_opening(cand, np.ones((3, 3)))
    lab, n = ndimage.label(cand, np.ones((3, 3)))
    if not n:
        return im
    sz = ndimage.sum(cand, lab, range(1, n + 1))
    blob = np.isin(lab, [i + 1 for i in range(n) if sz[i] > min_blob])
    field = ndimage.gaussian_filter(blob.astype(np.float32), 10)
    al = al * (1.0 - np.clip(field * 2.2, 0, 1))
    out = np.dstack([rgb, al])
    return Image.fromarray((out * 255).astype(np.uint8), "RGBA")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("d", nargs="?", default=os.path.join(ROOT, "assets", "fleet"))
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    for n in sorted(os.listdir(args.d)):
        if not n.endswith(".png"):
            continue
        src = os.path.join(args.d, n)
        out = clean(src)
        cov = float(np.asarray(out.split()[3], np.float32).mean() / 255.0)
        print(f"{n:14s} cover {cov:5.1%}")
        if not args.check:
            out.save(src)


if __name__ == "__main__":
    main()
