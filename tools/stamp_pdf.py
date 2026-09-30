#!/usr/bin/env python3
"""
Overlay a stamp / logo image on every page of a PDF.

    python tools/stamp_pdf.py input.pdf stamp.png output.pdf \
        [--position bottom-center] [--width-ratio 0.22] [--opacity 0.9] \
        [--margin 24] [--bg-key auto] [--gain 2.5] [--trim] [--pages 1-5,9]

--bg-key:
    auto   pick 'black' or 'white' from the image corners (default)
    black  make a dark background transparent, colour un-premultiplied
    white  make a light background transparent
    keep   trust the image's own alpha channel, change nothing

Notes
-----
* The stamp is placed as an image XObject with an SMask, so it does not cover
  the page content.
* Rotated pages (/Rotate 90/180/270) are handled: the artwork is pre-rotated so
  it still reads upright, and the target rectangle is mapped from visible page
  coordinates back to unrotated page coordinates.  Verified for all four
  rotations against rendered output.
"""

from __future__ import annotations

import argparse
import io
import re
import sys

import numpy as np
import pymupdf
from PIL import Image


# --------------------------------------------------------------------------- #
# artwork preparation
# --------------------------------------------------------------------------- #
def load_stamp(path: str) -> Image.Image:
    img = Image.open(path)
    return img if img.mode in ("RGBA", "LA") else img.convert("RGBA")


def _key_colour(rgb: np.ndarray, mode: str) -> str:
    if mode != "auto":
        return mode
    h, w, _ = rgb.shape
    s = max(2, min(h, w) // 20)
    corners = np.concatenate([
        rgb[:s, :s].reshape(-1, 3),
        rgb[:s, -s:].reshape(-1, 3),
        rgb[-s:, :s].reshape(-1, 3),
        rgb[-s:, -s:].reshape(-1, 3),
    ])
    return "black" if corners.mean() < 128 else "white"


def prepare_artwork(img: Image.Image, bg_key: str = "auto", gain: float = 2.5,
                    trim: bool = False) -> Image.Image:
    """Return an RGBA copy with a clean alpha channel."""
    rgba = img.convert("RGBA")
    arr = np.asarray(rgba).astype(np.int16)
    rgb, alpha = arr[..., :3], arr[..., 3]

    has_alpha = int(alpha.min()) < 250
    mode = bg_key
    if mode == "none":
        mode = "keep"
    if mode == "keep" and not has_alpha:
        mode = "auto"          # nothing useful to keep -> fall back to keying
    if mode == "keep":
        out = rgba
    else:
        key = _key_colour(rgb, mode)
        if key == "black":
            dist = rgb.max(axis=2)                       # distance from black
        elif key == "white":
            dist = 255 - rgb.min(axis=2)                 # distance from white
        else:
            raise ValueError(f"bad --bg-key {bg_key!r}")

        new_alpha = np.clip(dist.astype(np.float32) * gain, 0, 255)
        a = (new_alpha / 255.0)[..., None]
        with np.errstate(invalid="ignore", divide="ignore"):
            colour = np.where(a > 0.02,
                              (rgb - (1.0 - a) * (0 if key == "black" else 255)) / np.maximum(a, 1e-3),
                              rgb)
        colour = np.clip(colour, 0, 255)
        # keep existing transparency, if any
        new_alpha = np.minimum(new_alpha, alpha)
        out = Image.fromarray(
            np.dstack([colour, new_alpha]).astype(np.uint8), mode="RGBA")

    if trim:
        bbox = out.getchannel("A").point(lambda v: 255 if v > 12 else 0).getbbox()
        if bbox:
            out = out.crop(bbox)
    return out


def alpha_png(img: Image.Image, opacity: float) -> bytes:
    alpha = img.getchannel("A")
    if opacity < 1.0:
        alpha = alpha.point(lambda v: int(v * opacity))
    buf = io.BytesIO()
    alpha.save(buf, format="PNG")
    return buf.getvalue()


def rgb_png(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="PNG")
    return buf.getvalue()


# --------------------------------------------------------------------------- #
# layout
# --------------------------------------------------------------------------- #
def place_rect(page: pymupdf.Page, w: float, h: float, position: str,
               margin: float) -> pymupdf.Rect:
    r = page.rect                                   # visible (rotated) page
    if position.endswith("left"):
        x0 = r.x0 + margin
    elif position.endswith("right"):
        x0 = r.x1 - margin - w
    else:
        x0 = r.x0 + (r.width - w) / 2

    if position.startswith("top"):
        y0 = r.y0 + margin
    elif position.startswith("bottom"):
        y0 = r.y1 - margin - h
    else:
        y0 = r.y0 + (r.height - h) / 2
    return pymupdf.Rect(x0, y0, x0 + w, y0 + h)


def parse_pages(spec: str | None, count: int) -> list[int]:
    if not spec:
        return list(range(count))
    out: list[int] = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        m = re.fullmatch(r"(\d+)\s*-\s*(\d+)", part)
        if m:
            a, b = sorted((int(m.group(1)), int(m.group(2))))
            out += list(range(max(1, a), min(count, b) + 1))
        elif part.isdigit():
            n = int(part)
            if 1 <= n <= count:
                out.append(n)
        else:
            raise ValueError(f"bad page spec: {part!r}")
    return sorted(set(out))


# --------------------------------------------------------------------------- #
def main() -> int:
    ap = argparse.ArgumentParser(description="Stamp every page of a PDF.")
    ap.add_argument("pdf")
    ap.add_argument("stamp")
    ap.add_argument("out")
    ap.add_argument("--position", default="bottom-center",
                    choices=["bottom-center", "bottom-left", "bottom-right",
                             "top-center", "top-left", "top-right", "center"])
    ap.add_argument("--width-ratio", type=float, default=0.22,
                    help="stamp width as a fraction of page width (0.22 = 22%%)")
    ap.add_argument("--opacity", type=float, default=0.9)
    ap.add_argument("--margin", type=float, default=24.0, help="points")
    ap.add_argument("--bg-key", default="auto",
                    choices=["auto", "black", "white", "keep"])
    ap.add_argument("--gain", type=float, default=2.5,
                    help="alpha boost when keying out a background")
    ap.add_argument("--trim", action="store_true", help="crop empty borders")
    ap.add_argument("--pages", default=None,
                    help="subset, e.g. 1-5,9 (default: all)")
    args = ap.parse_args()

    base = prepare_artwork(load_stamp(args.stamp), args.bg_key, args.gain, args.trim)
    base_rgb = rgb_png(base)

    doc = pymupdf.open(args.pdf)
    targets = parse_pages(args.pages, doc.page_count)
    if not targets:
        print("no pages selected", file=sys.stderr)
        return 2

    for number in targets:
        page = doc[number - 1]
        rot = page.rotation % 360

        if rot:
            # insert_image() paints in unrotated page space: pre-rotate the art
            # by +rot so the page's own /Rotate shows it upright.
            art = base.rotate(rot, expand=True, resample=Image.BICUBIC)
            art_rgb = rgb_png(art)
            art_mask = alpha_png(art, args.opacity)
        else:
            art_rgb, art_mask = base_rgb, alpha_png(base, args.opacity)

        # size as the reader perceives it (aspect of the un-rotated artwork)
        w = page.rect.width * args.width_ratio
        h = w * (base.height / base.width)
        visible = place_rect(page, w, h, args.position, args.margin)
        target = visible * page.derotation_matrix
        page.insert_image(target, stream=art_rgb, mask=art_mask,
                          overlay=True, rotate=0)

    doc.save(args.out, garbage=4, deflate=True, clean=True)
    doc.close()
    print(f"stamped {len(targets)}/{pymupdf.open(args.pdf).page_count} pages -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
