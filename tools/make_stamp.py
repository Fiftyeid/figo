#!/usr/bin/env python3
"""
Build a clean (transparent-background) rendition of the "Ability / قدرة" stamp
artwork, so it can be overlaid on a PDF instead of the black-background PNG.

    python tools/make_stamp.py "شركة قدرة للتنمية" \
        "والحلول التكنولوجية للتعليم" \
        --en1 "Ability For Development" \
        --en2 "And Technological Solutions For Education" \
        --ar3 "س.ت: ١١٤٤٩٩   ب.ض: ٥٥٧-٦٦٩" \
        -o stamp.png

The three Arabic strings are supplied by the user (they are company data, not
something to guess).  Arabic shaping is done with arabic-reshaper + python-bidi
because Pillow here is built without libraqm.
"""

from __future__ import annotations

import argparse
import os
import sys

from PIL import Image, ImageDraw, ImageFont

try:
    import arabic_reshaper
    from bidi.algorithm import get_display
except ImportError:  # pragma: no cover
    arabic_reshaper = None
    get_display = None

HERE = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(HERE, "fonts")
FONT_AR = os.path.join(FONT_DIR, "Amiri-Bold.ttf")
FONT_AR_LIGHT = os.path.join(FONT_DIR, "Amiri-Regular.ttf")
FONT_EN = os.path.join(FONT_DIR, "Amiri-Bold.ttf")
FONT_EN_LIGHT = os.path.join(FONT_DIR, "Amiri-Regular.ttf")

BLUE = (68, 114, 196, 255)          # sampled from the supplied artwork
BLUE_DARK = (40, 80, 170, 255)


def has_arabic(s: str) -> bool:
    return any("\u0600" <= c <= "\u06ff" for c in s)


def shape(s: str) -> str:
    if has_arabic(s):
        if arabic_reshaper is None:
            raise RuntimeError("pip install arabic-reshaper python-bidi")
        return get_display(arabic_reshaper.reshape(s))
    return s


def fit(draw, text, path, target_size, max_width):
    """Largest font size <= target_size whose text fits max_width."""
    size = target_size
    while size > 6:
        font = ImageFont.truetype(path, size)
        w = draw.textbbox((0, 0), text, font=font)[2]
        if w <= max_width:
            return font
        size -= 1
    return ImageFont.truetype(path, 6)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("ar1", help="top Arabic line, e.g. \"شركة قدرة للتنمية\"")
    ap.add_argument("ar2", help="second Arabic line")
    ap.add_argument("en1", default="", nargs="?", help="first English line")
    ap.add_argument("en2", default="", nargs="?", help="second English line")
    ap.add_argument("--ar3", default="", help="optional bottom Arabic line (IDs)")
    ap.add_argument("--width", type=int, default=1400)
    ap.add_argument("--out", "-o", default="stamp.png")
    ap.add_argument("--bg-key", default="none",
                    help="none (transparent) | black | white - key out a bg colour")
    args = ap.parse_args()

    W = args.width
    pad = int(W * 0.02)
    maxw = W - 2 * pad

    # (text, font path, ideal size, colour) -- sizes are relative to width
    specs = [
        (shape(args.ar1), FONT_AR, int(W * 0.085), BLUE),
        (shape(args.ar2), FONT_AR_LIGHT, int(W * 0.055), BLUE),
        (args.en1, FONT_EN, int(W * 0.062), BLUE),
        (args.en2, FONT_EN_LIGHT, int(W * 0.046), BLUE),
    ]
    if args.ar3:
        specs.append((shape(args.ar3), FONT_AR_LIGHT, int(W * 0.042), BLUE))

    probe = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    rows = []
    total_h = 0
    gap = int(W * 0.018)
    for text, path, size, colour in specs:
        if not text:
            continue
        font = fit(probe, text, path, size, maxw)
        bb = probe.textbbox((0, 0), text, font=font)
        rows.append((text, font, colour, bb))
        total_h += (bb[3] - bb[1]) + gap

    H = total_h + 2 * pad - gap
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    y = pad
    for text, font, colour, bb in rows:
        x = (W - (bb[2] - bb[0])) / 2 - bb[0]
        draw.text((x, y - bb[1]), text, font=font, fill=colour)
        y += (bb[3] - bb[1]) + gap

    if args.bg_key in ("black", "white"):
        import numpy as np
        arr = np.asarray(img).copy()
        rgb = arr[..., :3].astype(int)
        dist = rgb.max(axis=2) if args.bg_key == "black" else 255 - rgb.min(axis=2)
        arr[..., 3] = dist
        img = Image.fromarray(arr)

    img.save(args.out)
    print(f"wrote {args.out} ({img.width}x{img.height})")
    return 0


if __name__ == "__main__":
    sys.exit(main())