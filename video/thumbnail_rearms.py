#!/usr/bin/env python3
"""Reference-style thumbnail: keyed studio hero + one enormous black headline.

The look: a dark airframe photographed front-three-quarter on a warm white
sweep with a faint tile grid, cropped so the wings run to both edges, and a
single line of very heavy condensed caps across the top.  The jet is keyed
out of the generated plate and re-staged on a drawn backdrop, so nothing at
the frame edge can seam — the backdrop is infinite by construction.

    python3 video/thumbnail_rearms.py                     # JAPAN REARMS
    python3 video/thumbnail_rearms.py --text "19 AIRCRAFT" --out build/alt.jpg
"""
from __future__ import annotations

import argparse
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

ROOT = os.path.dirname(HERE)
FONT = os.path.join(os.path.dirname(__import__("matplotlib").__file__),
                    "mpl-data", "fonts", "ttf", "DejaVuSans-Bold.ttf")

W, H = 1280, 720
INK = (10, 10, 11)
HINOMARU = (186, 12, 40)


# ---------------------------------------------------------------- backdrop
def sweep(w: int, h: int, horizon: float = 0.66) -> Image.Image:
    """Warm white cyc: pale wall, floor that falls off to the frame bottom."""
    ys = np.arange(h, dtype=np.float32)[:, None] / h
    wall = np.array((250, 248, 245), dtype=np.float32)
    floor = np.array((236, 231, 224), dtype=np.float32)
    edge = np.array((205, 198, 190), dtype=np.float32)

    t = np.clip((ys - horizon) / (1 - horizon), 0, 1)
    band = wall + (floor - wall) * np.clip(t * 4, 0, 1)
    band = band + (edge - band) * np.clip((t - 0.55) / 0.45, 0, 1) ** 1.6
    img = np.repeat(band[:, None, :], w, axis=1)

    # a soft pool of light behind the aircraft, so the wall is not dead flat
    xs = np.arange(w, dtype=np.float32)[None, :] / w
    d = ((xs - 0.5) / 0.52) ** 2 + ((ys - 0.42) / 0.55) ** 2
    img = np.clip(img + (np.clip(1 - d, 0, 1) ** 1.8 * 9)[..., None], 0, 255)
    return Image.fromarray(img.astype(np.uint8), "RGB")


def tile_grid(canvas: Image.Image, horizon: float = 0.66, step: int = 118) -> None:
    """Faint studio-floor tiles: only below the horizon, fading with depth."""
    w, h = canvas.size
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    vx, vy = w / 2, h * horizon
    for i in range(-14, 15):
        xb = vx + i * step
        d.line([(vx + (xb - vx) * 0.03, vy), (vx + (xb - vx) * 2.4, h + 200)],
               fill=(255, 255, 255, 26), width=2)
        d.line([(vx + (xb - vx) * 0.03 + 2, vy + 1), (vx + (xb - vx) * 2.4 + 2, h + 200)],
               fill=(120, 112, 102, 12), width=2)
    depth, k = 0.0, 1.0
    while True:
        depth += 0.10 * k
        k *= 1.22
        y = vy + (h - vy) * (depth ** 1.7)
        if y > h + 4:
            break
        a = int(10 + 26 * min(1.0, depth))
        d.line([(0, y), (w, y)], fill=(255, 255, 255, a), width=2)
        d.line([(0, y + 2), (w, y + 2)], fill=(120, 112, 102, int(a * 0.5)), width=2)

    fade = Image.new("L", (w, h), 0)
    fd = ImageDraw.Draw(fade)
    for y in range(int(h * horizon) - 30, int(h * horizon) + 120):
        fd.line([(0, y), (w, y)],
                fill=int(255 * max(0.0, (y - (h * horizon - 30)) / 150.0)))
    fd.rectangle([0, int(h * horizon) + 120, w, h], fill=255)
    overlay.putalpha(Image.composite(overlay.split()[3], Image.new("L", (w, h), 0), fade))
    canvas.alpha_composite(overlay) if canvas.mode == "RGBA" else \
        canvas.paste(Image.alpha_composite(canvas.convert("RGBA"), overlay).convert("RGB"), (0, 0))


# ---------------------------------------------------------------- keying
def body_box(plate: Image.Image) -> tuple:
    """Bounding box of the dark airframe body inside its own studio plate.

    Uses a hard luminance threshold so the pale wingtips and the tile lines
    do not drag the box around; the box is then what everything else is
    anchor-relative to.
    """
    a = np.asarray(plate.convert("RGB")).astype(np.float32)
    lum = 0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2]
    ys, xs = np.where(lum < 120)
    return int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())


def place_plate(canvas_w: int, canvas_h: int, plate: Image.Image, box: tuple,
                width_f: float, bottom_f: float, cx_f: float = 0.5) -> Image.Image:
    """Scale the whole studio plate so the airframe hits a target size.

    Anchoring on the measured body box means the aircraft lands exactly where
    the layout wants it, and because the plate is scaled as one piece the
    floor, tiles and shadow stay welded to the airframe — nothing to seam.
    """
    x0, y0, x1, y1 = box
    scale = (width_f * canvas_w) / max(1, (x1 - x0))
    pw, ph = int(plate.width * scale), int(plate.height * scale)
    plate = plate.resize((pw, ph), Image.LANCZOS)

    body_cx = ((x0 + x1) / 2) * scale
    body_b = y1 * scale
    ox = int(canvas_w * cx_f - body_cx)
    oy = int(canvas_h * bottom_f - body_b)

    canvas = Image.new("RGB", (canvas_w, canvas_h), (255, 255, 255))
    canvas.paste(plate, (ox, oy))
    return canvas


def roundel_on_plate(plate: Image.Image, box: tuple, fx: float, fy: float,
                     r_frac: float, squash: float = 0.60, tilt: float = -6.0,
                     lit: float = 0.70) -> Image.Image:
    """Hinomaru painted on the skin, before scaling, so it rides the airframe.

    The disc is multiplied by the skin underneath it, so it picks up the
    panel shading, the highlight along the nose and the edge falloff — a flat
    red ellipse on a lit fuselage reads as a sticker, which is the tell.
    """
    x0, y0, x1, y1 = box
    bw, bh = x1 - x0, y1 - y0
    cx, cy = x0 + bw * fx, y0 + bh * fy
    r = bh * r_frac
    pad = int(r * 3)
    size = pad * 2

    disc = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ImageDraw.Draw(disc).ellipse([pad - r, pad - r * squash, pad + r, pad + r * squash],
                                 fill=HINOMARU + (255,))
    disc = disc.rotate(tilt, resample=Image.BICUBIC, expand=False)
    m = np.asarray(disc.split()[3]).astype(np.float32) / 255.0

    out = plate.convert("RGB").copy()
    px, py = int(cx) - pad, int(cy) - pad
    skin = np.asarray(out.crop((px, py, px + size, py + size))).astype(np.float32) / 255.0
    # skin shading as a multiplier, normalised so mid-grey keeps full red
    shade = np.clip(skin.mean(axis=2) / 0.34, 0.45, 1.30)
    red = np.array(HINOMARU, dtype=np.float32) / 255.0
    paint = np.clip(red[None, None, :] * shade[..., None], 0, 1)
    paint = skin * (1 - lit) + paint * lit
    blended = skin * (1 - m[..., None]) + paint * m[..., None]
    patch = Image.fromarray((np.clip(blended, 0, 1) * 255).astype(np.uint8), "RGB")
    out.paste(patch, (px, py))
    return out


# ---------------------------------------------------------------- headline
def headline(text: str, max_w: int, cap_h: int, squeeze: float,
             tracking: float) -> Image.Image:
    """Biggest heavy line that fits, then condensed on the horizontal axis."""
    size = int(cap_h * 2.2)
    while size > 20:
        line = _line(text, size, tracking)
        if int(line.width * squeeze) <= max_w and line.height <= cap_h:
            return line.resize((max(1, int(line.width * squeeze)), line.height), Image.LANCZOS)
        size -= 2
    line = _line(text, 40, tracking)
    return line.resize((max(1, int(line.width * squeeze)), line.height), Image.LANCZOS)


def _line(text: str, size: int, tracking: float) -> Image.Image:
    f = ImageFont.truetype(FONT, size)
    probe = ImageDraw.Draw(Image.new("L", (4, 4)))
    widths = [probe.textlength(ch, font=f) for ch in text]
    asc, desc = f.getmetrics()
    total = sum(widths) + tracking * size * max(0, len(text) - 1)
    im = Image.new("RGBA", (int(total) + 40, asc + desc + 20), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    x = 20.0
    for ch, w in zip(text, widths):
        d.text((x, 10), ch, font=f, fill=INK + (255,))
        x += w + tracking * size
    return im.crop(im.getbbox())


def compose(hero: str, text: str, out: str, width_f: float = 0.96,
            bottom_f: float = 0.84, cap_f: float = 0.225, squeeze: float = 0.87,
            tracking: float = -0.045, top_f: float = 0.018, side_f: float = 0.028,
            mark: tuple | None = None, lift: float = 0.10) -> str:
    plate = Image.open(hero).convert("RGB")
    box = body_box(plate)

    if mark:
        fx, fy, r_body, squash, tilt = mark      # r_body: fraction of body height
        plate = roundel_on_plate(plate, box, fx, fy, r_body, squash, tilt)

    canvas = place_plate(W, H, plate, box, width_f, bottom_f)

    # lift: darken the top of the frame a touch so a black headline always
    # separates from a pale wall, exactly like the reference's blown-out top
    if lift > 0:
        arr = np.asarray(canvas).astype(np.float32) / 255.0
        ys = np.arange(H, dtype=np.float32)[:, None] / H
        ramp = np.clip(1.0 - ys / 0.62, 0, 1) ** 0.8 * lift
        arr = np.clip(arr * (1.0 - ramp[..., None]) + (1.0 * ramp[..., None]), 0, 1)
        canvas = Image.fromarray((arr * 255).astype(np.uint8), "RGB")

    line = headline(text, int(W * (1 - 2 * side_f)), int(H * cap_f), squeeze, tracking)
    canvas.paste(line, ((W - line.width) // 2, int(H * top_f)), line)

    canvas.save(out.replace(".jpg", ".png"))
    canvas.save(out, quality=95, subsampling=0)
    print(f"  {out}  headline {line.width}x{line.height}  "
          f"(cap {line.height / H:.1%})  body {box[2]-box[0]}x{box[3]-box[1]}px")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hero", default=os.path.join(ROOT, "build", "hero_f35_studio.png"))
    ap.add_argument("--text", default="JAPAN REARMS")
    ap.add_argument("--out", default=os.path.join(ROOT, "deliverables", "thumb_japan_rearms.jpg"))
    ap.add_argument("--width", type=float, default=0.96, help="airframe body width / frame width")
    ap.add_argument("--bottom", type=float, default=0.84, help="where the tyres sit")
    ap.add_argument("--cap", type=float, default=0.225, help="headline cap height / frame")
    ap.add_argument("--squeeze", type=float, default=0.87)
    ap.add_argument("--tracking", type=float, default=-0.045)
    ap.add_argument("--top", type=float, default=0.018)
    ap.add_argument("--side", type=float, default=0.028)
    ap.add_argument("--lift", type=float, default=0.10)
    ap.add_argument("--mark", default="", help="fx,fy,r_frac,squash,tilt on the airframe")
    args = ap.parse_args()
    mark = tuple(float(v) for v in args.mark.split(",")) if args.mark else None
    compose(args.hero, args.text, args.out, args.width, args.bottom, args.cap,
            args.squeeze, args.tracking, args.top, args.side, mark, args.lift)


if __name__ == "__main__":
    main()
