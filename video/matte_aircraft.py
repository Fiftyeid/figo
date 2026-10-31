#!/usr/bin/env python3
"""Cut white-sweep aircraft shots out of their background.

`cutout.py` keys anything near-white, which eats white paint (T-4, Global
Hawk, US-2, tankers).  Aircraft need a smarter matte:

1. background = the region *reachable from the frame border* that is either
   near-white **or** close to the colour of that particular studio sweep
   (generators hand back cream backdrops too), with strong image edges
   blocking the flood — so white paint inside the airframe survives;
2. no hole filling: the gaps between rotor blades and under the wings are
   real background and must stay transparent;
3. leftover studio shadows are removed in a second pass
   (`clean_fleet.py`), then the white fringe is un-mixed.

Three fragile airframes (white trainer, flying boat, white drone) sit so
close to the backdrop that the optional repair passes would read as holes,
so they are keyed with the conservative profile.

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

# airframes whose paint sits right against the sweep: conservative profile
SAFE = {"t4", "us2", "rq4"}


def _border_ids(lab: np.ndarray) -> list[int]:
    ids = set(np.unique(np.concatenate([lab[0, :], lab[-1, :], lab[:, 0], lab[:, -1]])))
    ids.discard(0)
    return list(ids)


def _repair_sealed(alpha, lum, minc, sat, g):
    """Re-open backdrop the generator sealed inside the silhouette.

    The gap between a rotor disc and the tail boom sometimes comes back as
    flat white instead of backdrop; treat flat + very bright blobs as glass.
    """
    solid = alpha > 0.5
    holes = ndimage.binary_fill_holes(solid) & ~solid
    hl, hn = ndimage.label(holes)
    if not hn:
        return alpha
    hs = ndimage.sum(holes, hl, range(1, hn + 1))
    bright = (minc > 0.94) & (sat < 0.038)
    for i in range(hn):
        if hs[i] < 900:
            continue
        m = hl == i + 1
        if float(bright[m].mean()) > 0.55:
            alpha = np.where(m, 0.0, alpha)
    return alpha


def _kill_sky_panes(alpha, lum, minc, sat):
    """Drop backdrop that got sealed between a rotor disc and the tail boom.

    The tell is a big, *pure* white patch (lum > 0.985) touching paint that is
    clearly darker — real white paint always carries shading and sits next to
    more white paint, so it can never be caught here.
    """
    cand = (alpha > 0.5) & (minc > 0.955) & (sat < 0.035) & (lum > 0.985)
    lab, n = ndimage.label(cand, np.ones((3, 3)))
    if not n:
        return alpha
    sizes = ndimage.sum(cand, lab, range(1, n + 1))
    painted = alpha > 0.5
    for i in range(n):
        if sizes[i] < 2500:
            continue
        m = lab == i + 1
        ring = ndimage.binary_dilation(m, np.ones((25, 25))) & ~m & painted
        if ring.sum() < 400:
            continue
        if float(lum[ring].mean()) < 0.92:
            alpha = np.where(m, 0.0, alpha)
    return alpha


def _repair_panes(a, alpha, lum, minc, sat, ref):
    """Repaint flat white panes that are open to the backdrop.

    Where the generator leaves sky showing through a wing gap it comes back
    flat and bright; deleting it punches holes in white paint, so it is
    repainted with the colour of the paint that surrounds it.
    """
    std9 = np.sqrt(np.clip(
        ndimage.uniform_filter(lum * lum, 9) - ndimage.uniform_filter(lum, 9) ** 2,
        0, None))
    open_sky = ndimage.binary_dilation(alpha < 0.35, np.ones((7, 7)))
    cand = ((alpha > 0.5) & (minc > 0.90) & (sat < 0.055)
            & (std9 < 0.022) & open_sky)
    lab, npn = ndimage.label(cand, np.ones((3, 3)))
    if not npn:
        return a
    sz = ndimage.sum(cand, lab, range(1, npn + 1))
    paint = (alpha > 0.5) & ~cand
    if not paint.any():
        return a
    idx = ndimage.distance_transform_edt(~paint, return_distances=False,
                                         return_indices=True)
    near = a[idx[0], idx[1]]
    for i in range(npn):
        if sz[i] < 700:
            continue
        m = lab == i + 1
        a[m] = a[m] * 0.18 + near[m] * 0.82
    return a


def matte(path, bright=0.80, sat_max=0.085, tol=0.075, edge_thr=0.05,
          min_comp=90, safe=False):
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

    if not safe:
        alpha = _repair_sealed(alpha, lum, minc, sat, g)
        alpha = _kill_sky_panes(alpha, lum, minc, sat)

    # ---- 2c. drop sweep-coloured crumbs that hug the frame edge
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

    # ---- 2d. anything still the colour of the sweep is backdrop
    lab_c, nc = ndimage.label(alpha > 0.22, np.ones((3, 3)))
    if nc > 1:
        big = float((alpha > 0.22).sum()) * 0.30
        for i in range(1, nc + 1):
            m = lab_c == i
            if int(m.sum()) < 24 or int(m.sum()) > big:
                continue
            if float(np.abs(a[m].mean(axis=0) - ref).max()) < 0.055:
                alpha = np.where(m, 0.0, alpha)
                a = np.where(m[..., None], ref[None, None, :], a)

    # ---- 3. inpaint white blowouts inside the airframe (generator artefacts)
    sil = ndimage.binary_erosion(alpha > 0.5, np.ones((7, 7)))
    hole = sil & (alpha < 0.5)
    hl, hn = ndimage.label(hole)
    if hn:
        hs = ndimage.sum(hole, hl, range(1, hn + 1))
        small = [i + 1 for i in range(hn) if hs[i] < 1500]
        if small:
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
        key = os.path.splitext(name)[0]
        out = matte(os.path.join(args.src, name), safe=key in SAFE)
        al = np.asarray(out.split()[3], np.float32) / 255.0
        print(f"{name:16s} {out.width:4d}x{out.height:<4d} cover {al.mean():5.1%}")
        if not args.check:
            out.save(os.path.join(args.dst, key + ".png"))


if __name__ == "__main__":
    main()
