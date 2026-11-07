"""YouTube thumbnail — 'reference' look: warm cream studio, big worn black
condensed headline, photographic exhibit cropped at the bottom edge.

usage:  python3 pipeline/thumbnail_v2.py [--vehicle 2s43] [--out output/thumbnail-v2.jpg]
"""
import argparse
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy import ndimage

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import render as R  # noqa: E402

W, H = 1280, 720
CREAM_TOP = (247, 244, 236)
CREAM_BOT = (233, 227, 215)
TILE = (214, 206, 190)
INK = (14, 12, 10)
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


# ---------------------------------------------------------------- background
def studio_bg():
    bg = Image.new("RGB", (W, H), CREAM_TOP)
    d = ImageDraw.Draw(bg)
    for y in range(H):
        t = y / (H - 1)
        col = tuple(int(CREAM_TOP[i] + (CREAM_BOT[i] - CREAM_TOP[i]) * t) for i in range(3))
        d.line([(0, y), (W, y)], fill=col)

    grid = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    g = ImageDraw.Draw(grid)
    step, off = 210, -50
    x = off
    while x < W:
        g.line([(x, 0), (x, H)], fill=TILE + (120,), width=2)
        x += step
    y = 96
    while y < H:
        g.line([(0, y), (W, y)], fill=TILE + (120,), width=2)
        y += step
    bg = Image.alpha_composite(bg.convert("RGBA"), grid)

    # floor: slightly warmer + a soft falloff so the exhibit sits in the room
    floor = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    fd = ImageDraw.Draw(floor)
    fd.rectangle([0, 470, W, H], fill=(226, 219, 204, 90))
    floor = floor.filter(ImageFilter.GaussianBlur(1))
    return Image.alpha_composite(bg, floor)


def contact_shadow(size, cx, cy, rw, rh, blur=40, opacity=105):
    sh = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(sh)
    d.ellipse([cx - rw, cy - rh, cx + rw, cy + rh], fill=(86, 74, 58, opacity))
    return sh.filter(ImageFilter.GaussianBlur(blur))


# ---------------------------------------------------------------- type
def measure(text, size):
    f = ImageFont.truetype(FONT, size)
    box = f.getbbox(text)
    return box[2] - box[0], box[3] - box[1], box


def make_line(text, max_w, max_h, xscale, tracking=0, stroke=3):
    """Heavy condensed line: heavy strokes, then squeezed horizontally to fill width."""
    size, chosen = 40, None
    while size < 420:
        f = ImageFont.truetype(FONT, size)
        adv = f.getlength(text) + tracking * (len(text) - 1) + stroke * 2
        box = f.getbbox(text, stroke_width=stroke)
        gh = box[3] - box[1]
        if adv * xscale > max_w or gh > max_h:
            break
        chosen = size
        size += 2
    size = chosen or 40
    f = ImageFont.truetype(FONT, size)
    pad = 30 + stroke
    box = f.getbbox(text, stroke_width=stroke)
    w = int(f.getlength(text) + tracking * (len(text) - 1)) + 2 * pad
    h = box[3] - box[1] + 2 * pad
    layer = Image.new("RGBA", (max(2, w), max(2, h)), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    x = pad
    y = pad - box[1]
    for ch in text:
        d.text((x, y), ch, font=f, fill=INK + (255,), stroke_width=stroke, stroke_fill=INK + (255,))
        x += f.getlength(ch) + tracking
    layer = layer.crop(layer.getbbox())
    return layer.resize((max(1, int(layer.width * xscale)), layer.height), Image.LANCZOS)


def distress(layer, strength=0.35, seed=3):
    a = np.array(layer).astype(np.float32)
    h, w = a.shape[:2]
    rng = np.random.default_rng(seed)
    mask = np.ones((h, w), np.float32)
    n = int(h * w / 2400 * strength)
    ys = rng.integers(0, h, n)
    xs = rng.integers(0, w, n)
    rs = rng.integers(1, 3, n)
    vals = np.where(rng.random(n) < 0.5, 0.0, 0.7)
    for y, x, r, v in zip(ys, xs, rs, vals):
        mask[max(0, y - r):y + r + 1, max(0, x - r):x + r + 1] *= v
    mask = ndimage.gaussian_filter(mask, 0.5)
    a[..., 3] = np.clip(a[..., 3] * mask, 0, 255)
    return Image.fromarray(a.astype(np.uint8))


# ---------------------------------------------------------------- exhibit
def edge_fix(img, alpha_t=0.92):
    """Bleed the subject's own colour into its soft edge so the render's white
    backdrop never reads as a halo on the cream wall."""
    a = np.array(img).astype(np.float32)
    rgb, alpha = a[..., :3], a[..., 3] / 255.0
    solid = alpha > alpha_t
    if solid.any():
        idx = ndimage.distance_transform_edt(~solid, return_distances=False, return_indices=True)
        bleed = rgb[tuple(idx)]
        edge = (alpha > 0.02) & (~solid)
        rgb[edge] = bleed[edge]
    a[..., :3] = rgb
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def build(vehicle, out):
    canvas = studio_bg()

    veh = edge_fix(R.cutout(R.render_path("renders", vehicle), 1200))
    vh = 560
    vw = int(veh.width * vh / veh.height)
    veh = veh.resize((vw, vh), Image.LANCZOS)
    vx = (W - vw) // 2 + 10
    vy = H - vh + 58                      # cropped by the bottom edge
    canvas.alpha_composite(contact_shadow((W, H), vx + vw // 2, vy + vh - 40,
                                          int(vw * 0.46), 24), (0, 0))
    canvas.alpha_composite(veh, (vx, vy))

    l1 = distress(make_line("EVERY RUSSIAN TANK", 1246, 128, 0.80, tracking=1), 0.35, seed=11)
    l2 = distress(make_line("& ARMORED VEHICLE", 1246, 128, 0.80, tracking=1), 0.35, seed=17)
    sub = make_line("IN ACTIVE SERVICE  ·  52 MACHINES", 620, 30, 0.86, tracking=5, stroke=1)

    y = 14
    for line in (l1, l2):
        canvas.alpha_composite(line, ((W - line.width) // 2, y))
        y += line.height + 2
    canvas.alpha_composite(sub, ((W - sub.width) // 2, y + 6))

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
    canvas.convert("RGB").save(os.path.splitext(out)[0] + ".png")
    print("wrote", out)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--vehicle", default="2s43")
    ap.add_argument("--out", default="output/thumbnail-v2.jpg")
    a = ap.parse_args()
    build(a.vehicle, a.out)
