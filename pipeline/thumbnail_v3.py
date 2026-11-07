"""YouTube thumbnail v3 — reference look with a short worn-condensed HOOK word.

Typeface: Anton (SIL OFL) — heavy condensed display sans, the closest free match
to the reference thumbnail's lettering (Druk/Anton family).

usage:
  python3 pipeline/thumbnail_v3.py --hook "ACTIVE" --kicker "EVERY RUSSIAN TANK & ARMORED VEHICLE  ·  52 MACHINES" \
      --vehicle 2s43 --out output/thumb-test-a.jpg
"""
import argparse
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import render as R                      # noqa: E402
from thumbnail_v2 import (              # noqa: E402
    studio_bg, contact_shadow, edge_fix, distress, W, H, INK,
)

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT = os.path.join(HERE, "assets", "fonts", "Anton-Regular.ttf")
FALLBACK = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FACE = FONT if os.path.exists(FONT) else FALLBACK


# ---------------------------------------------------------------- type
def _font(size):
    return ImageFont.truetype(FACE, size)


def line_at_cap(text, cap, tracking=0, stroke=2):
    """Render one line whose capital height == cap px (Anton 'H' ratio based)."""
    probe = _font(200)
    h_ref = probe.getbbox("H", stroke_width=0)[3] - probe.getbbox("H", stroke_width=0)[1]
    size = max(8, int(round(cap * 200.0 / h_ref)))
    f = _font(size)
    pad = 24 + stroke
    box = f.getbbox(text, stroke_width=stroke)
    w = int(f.getlength(text) + tracking * (len(text) - 1)) + 2 * pad
    h = box[3] - box[1] + 2 * pad
    layer = Image.new("RGBA", (max(2, w), max(2, h)), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    x, y = pad, pad - box[1]
    for ch in text:
        d.text((x, y), ch, font=f, fill=INK + (255,), stroke_width=stroke,
               stroke_fill=INK + (255,))
        x += f.getlength(ch) + tracking
    return layer.crop(layer.getbbox())


def fit_line(text, target_w, tracking=0, stroke=2, cap_room=400):
    """Grow the cap height until the line fills target_w."""
    lo, hi, best = 20, cap_room, None
    while lo <= hi:
        mid = (lo + hi) // 2
        lay = line_at_cap(text, mid, tracking, stroke)
        if lay.width <= target_w:
            best = lay
            lo = mid + 1
        else:
            hi = mid - 1
    return best if best is not None else line_at_cap(text, 20, tracking, stroke)


def spread_line(text, cap, target_w, stroke=3, lo=-10, hi=140):
    """Widen the tracking at a fixed cap height until the line reaches target_w."""
    best = line_at_cap(text, cap, lo, stroke)
    while lo <= hi:
        mid = (lo + hi) // 2
        lay = line_at_cap(text, cap, mid, stroke)
        if lay.width <= target_w:
            best = lay
            lo = mid + 1
        else:
            hi = mid - 1
    return best


def tracked_line(text, cap, tracking, stroke=1):
    return line_at_cap(text, cap, tracking, stroke)


# ---------------------------------------------------------------- page
def build(vehicle, out, hook, kicker, vh, gap_after_hook, top, cap=0, spread=False, spread_w=1246, ktrack=6, kcap=30):
    canvas = studio_bg()

    veh = edge_fix(R.cutout(R.render_path("renders", vehicle), 1200))
    vw = int(veh.width * vh / veh.height)
    veh = veh.resize((vw, vh), Image.LANCZOS)
    vx = (W - vw) // 2
    vy = H - vh + 52
    canvas.alpha_composite(contact_shadow((W, H), vx + vw // 2, vy + vh - 38,
                                          int(vw * 0.46), 22), (0, 0))
    canvas.alpha_composite(veh, (vx, vy))

    if spread:
        big = spread_line(hook, cap or 200, spread_w, stroke=3)
    elif cap:
        big = line_at_cap(hook, cap, tracking=-8, stroke=3)
    else:
        big = fit_line(hook, 1246, tracking=-8, stroke=3)
    big = distress(big, 0.32, seed=11)
    small = tracked_line(kicker, kcap, tracking=ktrack, stroke=1)

    y = top
    canvas.alpha_composite(big, ((W - big.width) // 2, y))
    y += big.height + gap_after_hook
    canvas.alpha_composite(small, ((W - small.width) // 2, y))

    # vignette
    vig = Image.new("L", (W, H), 0)
    vd = ImageDraw.Draw(vig)
    vd.ellipse([-W * 0.30, -H * 0.45, W * 1.30, H * 1.25], fill=255)
    vig = vig.filter(ImageFilter.GaussianBlur(120))
    shade = Image.new("RGBA", (W, H), (120, 106, 86, 60))
    shade.putalpha(Image.eval(vig, lambda v: int((255 - v) * 0.35)))
    canvas = Image.alpha_composite(canvas, shade)

    d = ImageDraw.Draw(canvas)
    d.rectangle([0, 0, W - 1, H - 1], outline=(205, 196, 178, 255), width=2)

    os.makedirs(os.path.dirname(out), exist_ok=True)
    canvas.convert("RGB").save(out, quality=94)
    print("wrote", out, "hook-h", big.height, "hook-w", big.width)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--vehicle", default="2s43")
    ap.add_argument("--out", default="work/thumb-test.jpg")
    ap.add_argument("--hook", default="ACTIVE SERVICE")
    ap.add_argument("--kicker", default="EVERY RUSSIAN TANK & ARMORED VEHICLE  ·  52 MACHINES")
    ap.add_argument("--vh", type=int, default=470)
    ap.add_argument("--gap", type=int, default=10)
    ap.add_argument("--top", type=int, default=18)
    ap.add_argument("--cap", type=int, default=0)
    ap.add_argument("--spread", action="store_true")
    ap.add_argument("--spread-w", type=int, default=1246)
    ap.add_argument("--ktrack", type=int, default=6)
    ap.add_argument("--kcap", type=int, default=30)
    a = ap.parse_args()
    build(a.vehicle, a.out, a.hook, a.kicker, a.vh, a.gap, a.top, a.cap, a.spread, a.spread_w, a.ktrack, a.kcap)
