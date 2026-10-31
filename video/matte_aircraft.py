#!/usr/bin/env python3
"""Cut white-sweep aircraft shots out of their background.

`cutout.py` keys anything near-white, which eats white paint (T-4, Global
Hawk, US-2, tankers).  Aircraft need a smarter matte:

1. background = the region *reachable from the frame border* that is either
   near-white **or** close to the corner colour of that particular studio
   sweep (some generators hand back cream / off-white backdrops), with strong
   image edges blocking the flood — so white paint inside the airframe
   survives;
2. no hole filling: the gaps between rotor blades and under the wings are
   real background and must stay transparent;
3. leftover studio shadows are removed in a second pass
   (`clean_fleet.py`), then the white fringe is un-mixed.

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


def _border_ids(lab: np.ndarray) -> list[int]:
    ids = set(np.unique(np.concatenate([lab[0, :], lab[-1, :], lab[:, 0], lab[:, -1]])))
    ids.discard(0)
    return list(ids)


def matte(path, bright=0.80, sat_max=0.085, tol=0.075, edge_thr=0.05, min_comp=90):
    img = Image.open(path).convert("RGB")
    a = np.asarray(img).astype(np.float32) / 255.0
    minc = a.min(axis=2)
    sat = a.max(axis=2) - a.min(axis=2)
    lum = 0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2]

    # ---- 1. background: border-connected, white or sweep-coloured, edge-free
    border = np.concatenate([a[:4].reshape(-1, 3), a[-4:].reshape(-1, 3),
                             a[:, :4].reshape(-1, 3), a[:, -4:].reshape(-1, 3)])
    ref = np.median(border, axis=0)
    dist = np.abs(a - ref[None, None, :]).max(axis=2)
    g = np.hypot(ndimage.sobel(lum, 0), ndimage.sobel(lum, 1)) / 4.0
    free = g <= edge_thr
    # some sweeps come back warm/cream rather than white: keep a hue test next
    # to the absolute one, or the vignetted corners survive as squares.
    warm = (a[..., 0] - a[..., 2]) > 0.035
    bgish = free & (((minc > bright) & (sat < sat_max)) | (dist < tol)
                    | ((minc > 0.78) & (sat < 0.12) & warm & (lum > 0.80)))

    lab_bg, _ = ndimage.label(bgish, np.ones((3, 3)))
    bg = np.isin(lab_bg, _border_ids(lab_bg))
    bg = ndimage.binary_dilation(bg, np.ones((3, 3)))

    alpha = (~bg).astype(np.float32)
    alpha = ndimage.gaussian_filter(alpha, 0.7)
    alpha = np.clip((alpha - 0.30) / 0.60, 0, 1)

    # ---- 2. keep real parts, bin dust and stray studio blobs
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
            if sizes[i - 1] < min_comp:
                continue
            m = lab == i
            # a bright, neutral blob this small is a baked floor shadow
            if float(lum[m].mean()) > 0.80 and float(sat[m].mean()) < 0.06:
                continue
            keep[i] = True
        alpha = np.where(keep[lab], alpha, 0.0)

    # ---- 2b. re-open background the generator sealed inside the silhouette
    # (the gap between a rotor disc and the tail boom comes back as flat white)
    solid = alpha > 0.5
    holes = ndimage.binary_fill_holes(solid) & ~solid
    hl, hn = ndimage.label(holes)
    if hn:
        hs = ndimage.sum(holes, hl, range(1, hn + 1))
        lum7 = ndimage.uniform_filter(lum, 7)
        v7 = ndimage.uniform_filter(lum * lum, 7) - lum7 * lum7
        std7 = np.sqrt(np.clip(v7, 0, None))
        brightm = (minc > 0.94) & (sat < 0.038)
        for i in range(hn):
            if hs[i] < 900:
                continue
            m = hl == i + 1
            if float(brightm[m].mean()) > 0.45:
                alpha = np.where(m, 0.0, alpha)

    # ---- 2c. drop sweep-coloured crumbs that hug the frame edge
    # (vignetted corners of a cream backdrop, cropped product-shot borders:
    #  smooth, same hue family as the sweep, and never part of the airframe)
    lab_e, ne = ndimage.label(alpha > 0.5, np.ones((3, 3)))
    if ne > 1:
        touch = set(np.unique(np.concatenate([lab_e[0, :], lab_e[-1, :],
                                              lab_e[:, 0], lab_e[:, -1]])))
        touch.discard(0)
        sizes_e = ndimage.sum(alpha > 0.5, lab_e, range(1, ne + 1))
        biggest_e = float(sizes_e.max())
        std7 = np.sqrt(np.clip(
            ndimage.uniform_filter(lum * lum, 7)
            - ndimage.uniform_filter(lum, 7) ** 2, 0, None))
        for i in touch:
            m = lab_e == i
            if float(m.sum()) > biggest_e * 0.25:
                continue
            close = float(np.abs(a[m].mean(axis=0) - ref).max()) < 0.16
            smooth = float(std7[m].mean()) < 0.028
            if close and smooth:
                alpha = np.where(m, 0.0, alpha)
                a = np.where(m[..., None], ref[None, None, :], a)

    # ---- 2c-bis. anything that is still the colour of the sweep is backdrop
    # (vignetted corners, cropped product-shot borders, semi-transparent panes)
    lab_c, nc = ndimage.label(alpha > 0.22, np.ones((3, 3)))
    if nc > 1:
        for i in range(1, nc + 1):
            m = lab_c == i
            area = int(m.sum())
            if area < 24:
                continue
            mean = a[m].mean(axis=0)
            if float(np.abs(mean - ref).max()) < 0.055:
                alpha = np.where(m, 0.0, alpha)
                a = np.where(m[..., None], ref[None, None, :], a)

    # ---- 2d. sealed background panes
    # the generator often fills the gap between a rotor disc / wing and the
    # fuselage with *pure* white (lum ~0.999) instead of with the backdrop.
    # Real white paint still carries shading (lum < 0.99) and its rim is
    # interior paint, not an aircraft outline, so both tests separate them.
    cand_w = (alpha > 0.6) & (minc > 0.93) & (sat < 0.05)
    lab_w, nw = ndimage.label(cand_w, np.ones((3, 3)))
    if nw:
        sizes_w = ndimage.sum(cand_w, lab_w, range(1, nw + 1))
        for i in range(nw):
            if sizes_w[i] < 2500:
                continue
            m = lab_w == i + 1
            if float(lum[m].mean()) < 0.988:
                continue
            ring = ndimage.binary_dilation(m, np.ones((9, 9))) & ~m
            if float((g[ring] > 0.06).mean()) < 0.35:
                continue
            alpha = np.where(m, 0.0, alpha)

    # ---- 2e. white panes that are open to the backdrop
    # Where the generator leaves sky showing through a wing or rotor gap it
    # comes back as flat, bright, low-contrast pixels touching the backdrop.
    # Deleting them punches holes in white paint, so they are *repainted*
    # with the colour of the paint that surrounds them instead.
    std9 = np.sqrt(np.clip(
        ndimage.uniform_filter(lum * lum, 9) - ndimage.uniform_filter(lum, 9) ** 2,
        0, None))
    open_to_sky = ndimage.binary_dilation(alpha < 0.35, np.ones((7, 7)))
    cand_p = ((alpha > 0.5) & (minc > 0.90) & (sat < 0.055)
              & (std9 < 0.022) & open_to_sky)
    lab_p, npn = ndimage.label(cand_p, np.ones((3, 3)))
    if npn:
        sz_p = ndimage.sum(cand_p, lab_p, range(1, npn + 1))
        paint = (alpha > 0.5) & ~cand_p
        if paint.any():
            idx = ndimage.distance_transform_edt(~paint, return_distances=False,
                                                 return_indices=True)
            near_col = a[idx[0], idx[1]]
            for i in range(npn):
                if sz_p[i] < 700:
                    continue
                m = lab_p == i + 1
                take = near_col[m]
                # soften towards the surrounding paint so the patch has shading
                k = 0.82
                a[m] = a[m] * (1 - k) + take * k
            lum = 0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2]

    # ---- 3. inpaint white blowouts *inside* the airframe (generator artefacts)
    sil = ndimage.binary_erosion(alpha > 0.5, np.ones((7, 7)))
    hole = sil & (alpha < 0.5)
    hl, hn = ndimage.label(hole)
    if hn:
        hs = ndimage.sum(hole, hl, range(1, hn + 1))
        small = [i + 1 for i in range(hn) if hs[i] < 1500]
        if small:
            a2 = a.copy()
            good = ~np.isin(hl, small)
            idx = ndimage.distance_transform_edt(good, return_distances=False,
                                                 return_indices=True)
            a2 = a[idx[0], idx[1]]
            a = np.where(np.isin(hl, small)[..., None], a2, a)
            alpha = np.where(np.isin(hl, small), 1.0, alpha)

    alpha = ndimage.gaussian_filter(alpha, 0.6)

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
