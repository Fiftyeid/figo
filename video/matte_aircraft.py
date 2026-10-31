#!/usr/bin/env python3
"""Cut white-sweep aircraft shots out of their background.

`cutout.py` keys anything near-white, which eats white paint (T-4, Global
Hawk, tankers).  Aircraft need a smarter matte:

1. the background is only the near-white region *reachable from the frame
   border* and a strong image edge blocks the flood, so white paint inside
   the silhouette survives;
2. leftover studio shadows (light + neutral blobs) are dropped;
3. pure-white patches that ended up inside the silhouette (generator
   artefacts, specular blowouts) are inpainted from their neighbours.

    python3 video/matte_aircraft.py                 # assets_raw/aircraft -> assets/fleet
    python3 video/matte_aircraft.py --check
"""
from __future__ import annotations

import argparse
import os

import numpy as np
from PIL import Image
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def _propagate(seed: np.ndarray, mask: np.ndarray) -> np.ndarray:
    return ndimage.binary_propagation(seed, mask=mask)


def matte(path, bright=0.80, sat_max=0.085, edge_thr=0.05):
    img = Image.open(path).convert("RGB")
    a = np.asarray(img).astype(np.float32) / 255.0
    minc = a.min(axis=2)
    sat = a.max(axis=2) - a.min(axis=2)
    lum = 0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2]

    # ---- 1. background = whitish, border-connected, flood stopped by edges
    g = np.hypot(ndimage.sobel(lum, 0), ndimage.sobel(lum, 1)) / 4.0
    whitish = (minc > bright) & (sat < sat_max) & (g <= edge_thr)
    seed = np.zeros_like(whitish)
    seed[0, :] = seed[-1, :] = seed[:, 0] = seed[:, -1] = True
    bg = _propagate(seed & whitish, whitish)
    bg = ndimage.binary_dilation(bg, np.ones((3, 3)))

    alpha = (~bg).astype(np.float32)
    alpha = ndimage.gaussian_filter(alpha, 0.7)
    alpha = np.clip((alpha - 0.30) / 0.60, 0, 1)

    # ---- 2. keep real parts, bin studio shadows and dust
    solid = alpha > 0.5
    lab, n = ndimage.label(solid, np.ones((3, 3)))
    keep = np.zeros(n + 1, bool)
    if n:
        sizes = ndimage.sum(solid, lab, range(1, n + 1))
        biggest = int(np.argmax(sizes)) + 1
        for i in range(1, n + 1):
            if i == biggest:
                keep[i] = True
                continue
            m = lab == i
            if sizes[i - 1] < 90:                      # dust
                continue
            light = float(lum[m].mean()) > 0.80 and float(sat[m].mean()) < 0.06
            if light:                                   # baked floor shadow
                continue
            keep[i] = True
        alpha = np.where(keep[lab], alpha, 0.0)

    # ---- 2b. eat the rest of the baked studio shadow
    # floor shadows are bright, neutral and almost texture-free; airframes are
    # never all three at once, so this only removes the smudge under the gear.
    rgb = a
    lum3 = ndimage.uniform_filter(lum, 3)
    var = ndimage.uniform_filter(lum * lum, 3) - lum3 * lum3
    std = np.sqrt(np.clip(var, 0, None))
    shadow = (alpha > 0.05) & (lum > 0.74) & (sat < 0.055) & (std < 0.022)
    shadow = ndimage.binary_opening(shadow, np.ones((3, 3)))
    field = ndimage.gaussian_filter(shadow.astype(np.float32), 9)
    alpha = alpha * (1.0 - 0.94 * np.clip(field, 0, 1))

    # ---- 3. inpaint white blowouts / artefacts inside the silhouette
    sil = ndimage.binary_fill_holes(alpha > 0.5)
    sil = ndimage.binary_erosion(sil, np.ones((5, 5)))
    hole = sil & (minc > 0.985) & (sat < 0.025)
    hl, hn = ndimage.label(hole)
    if hn:
        hs = ndimage.sum(hole, hl, range(1, hn + 1))
        # only patch small interiors; big enclosed gaps are real background
        hole = np.isin(hl, [i + 1 for i in range(hn) if hs[i] < 9000])
    if hole.any():
        good = ~hole & (alpha > 0.5)
        if good.any():
            idx = ndimage.distance_transform_edt(~good, return_distances=False,
                                                 return_indices=True)
            a = a[idx[0], idx[1]]
        alpha = np.maximum(alpha, (hole & sil).astype(np.float32))

    # ---- 4. un-mix the white fringe
    af = np.repeat(alpha[..., None], 3, axis=2)
    col = np.clip((a - (1.0 - af)) / np.maximum(af, 1e-3), 0, 1)
    col = np.where(af > 0.02, col, a)

    out = Image.fromarray(np.dstack([col * 255, alpha * 255]).astype(np.uint8), "RGBA")
    bb = out.split()[3].getbbox()
    if bb:
        p = 6
        out = out.crop((max(0, bb[0] - p), max(0, bb[1] - p),
                        min(out.width, bb[2] + p), min(out.height, bb[3] + p)))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src", nargs="?", default=os.path.join(ROOT, "assets_raw", "aircraft"))
    ap.add_argument("dst", nargs="?", default=os.path.join(ROOT, "assets", "fleet"))
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    os.makedirs(args.dst, exist_ok=True)
    for name in sorted(os.listdir(args.src)):
        if not name.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
            continue
        out = matte(os.path.join(args.src, name))
        al = np.asarray(out.split()[3], np.float32) / 255.0
        print(f"{name:16s} {out.width:4d}x{out.height:<4d} cover {al.mean():5.1%}")
        if not args.check:
            out.save(os.path.join(args.dst, os.path.splitext(name)[0] + ".png"))


if __name__ == "__main__":
    main()
