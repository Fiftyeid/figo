"""Pixel plumbing: white-background matting, sprites, text, flags, shadows.

Everything expensive is cached here, because the renderer is a Python loop
over ~10k frames and every millisecond counts.
"""
from __future__ import annotations

import math
import os
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from . import config as C


# ============================================================ matting
def matte_white(img: Image.Image) -> Image.Image:
    """Turn a photo shot on a pure white sweep into an RGBA cutout.

    Alpha is a soft function of the *minimum* channel, which is the classic
    trick for white-background product shots: any pixel that is fully white
    becomes transparent, any pixel that has ink in it stays solid.  Interior
    holes (specular highlights) are refilled so the object never gets pinholes.
    Edge pixels get their white contamination un-mixed.
    """
    rgb = img.convert("RGB")
    a = np.asarray(rgb).astype(np.float32) / 255.0
    minc = a.min(axis=2)
    sat = a.max(axis=2) - a.min(axis=2)

    # background test: bright AND neutral
    bg = (minc > 0.945) & (sat < 0.05)
    alpha = np.clip((0.93 - minc) / 0.28, 0.0, 1.0)
    alpha[bg] = 0.0

    # keep everything that is a large connected island = the subject
    try:
        from scipy import ndimage

        solid = alpha > 0.55
        lab, n = ndimage.label(solid)
        if n:
            sizes = ndimage.sum(solid, lab, range(1, n + 1))
            keep = (np.argsort(sizes)[::-1][:2] + 1)  # subject (+ shadow blob)
            solid = np.isin(lab, keep)
            solid = ndimage.binary_closing(solid, np.ones((9, 9)))
            filled = ndimage.binary_fill_holes(solid)
            holes = filled & ~solid
            if holes.any():
                hlab, hn = ndimage.label(holes)
                for hi in range(1, hn + 1):
                    hm = hlab == hi
                    if hm.sum() < 40:
                        filled[hm] = False   # dust speck, ignore
                        continue
                    if float(minc[hm].mean()) > 0.90:
                        filled[hm] = False   # white gap inside a trigger guard etc.
            solid = filled
            # grow the "definitely solid" core slightly, then feather
            core = ndimage.binary_erosion(solid, np.ones((5, 5)))
            alpha = np.maximum(alpha, core.astype(np.float32))
    except Exception:  # scipy missing: keep the cheap version
        pass

    # un-mix white fringe
    af = np.repeat(alpha[..., None], 3, axis=2)
    safe = np.maximum(af, 1e-3)
    col = np.clip((a - (1.0 - af)) / safe, 0.0, 1.0)
    col = np.where(af > 0.02, col, a)

    out = np.dstack([col * 255.0, alpha * 255.0]).astype(np.uint8)
    im = Image.fromarray(out, "RGBA")
    bbox = im.split()[3].getbbox()
    if bbox:
        pad = 6
        im = im.crop(
            (
                max(0, bbox[0] - pad),
                max(0, bbox[1] - pad),
                min(im.width, bbox[2] + pad),
                min(im.height, bbox[3] + pad),
            )
        )
    return im


def prepare_cutouts(raw_dir: str, out_dir: str) -> list[str]:
    os.makedirs(out_dir, exist_ok=True)
    made = []
    for name in sorted(os.listdir(raw_dir)):
        if not name.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
            continue
        stem = os.path.splitext(name)[0]
        dst = os.path.join(out_dir, stem + ".png")
        src = Image.open(os.path.join(raw_dir, name))
        matte_white(src).save(dst)
        made.append(dst)
    return made


# ============================================================ caches
@lru_cache(maxsize=128)
def cutout(path: str) -> Image.Image:
    return Image.open(path).convert("RGBA")


@lru_cache(maxsize=400)
def scaled(path: str, height: int) -> Image.Image:
    """Cutout scaled so its *content* is `height` px tall (quantised)."""
    src = cutout(path)
    height = max(8, int(round(height / 2)) * 2)
    w = max(8, int(round(src.width * height / src.height / 2)) * 2)
    # premultiplied resize kills the white halo around cut edges
    return src.convert("RGBa").resize((w, height), Image.LANCZOS).convert("RGBA")


@lru_cache(maxsize=400)
def shadow(path: str, height: int, spread: int = 26, opacity: float = 0.30) -> Image.Image:
    """Soft elliptical-ish contact shadow generated from the alpha channel."""
    src = scaled(path, height)
    pad = spread * 2 + 30
    canvas = Image.new("L", (src.width + pad * 2, src.height + pad * 2), 0)
    a = src.split()[3]
    canvas.paste(a, (pad, pad))
    # squash the alpha so it reads as a floor shadow, not a silhouette
    small = canvas.resize((max(2, canvas.width // 3), max(2, canvas.height // 7)), Image.BILINEAR)
    blob = small.resize(canvas.size, Image.BICUBIC).filter(ImageFilter.GaussianBlur(spread))
    arr = np.asarray(blob).astype(np.float32) * opacity
    blob = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "L")
    rgb = Image.new("RGB", blob.size, (18, 21, 26))
    return rgb, blob


@lru_cache(maxsize=200)
def reflection(path: str, height: int, opacity: float = 0.16) -> tuple:
    src = scaled(path, height)
    flip = src.transpose(Image.FLIP_TOP_BOTTOM)
    flip = flip.resize((flip.width, max(2, int(flip.height * 0.34))), Image.BILINEAR)
    flip = flip.filter(ImageFilter.GaussianBlur(2.0))
    a = np.asarray(flip.split()[3]).astype(np.float32)
    h = a.shape[0]
    fade = np.linspace(opacity, 0.0, h).reshape(-1, 1)
    a = np.clip(a * fade, 0, 255).astype(np.uint8)
    rgb = Image.fromarray(np.asarray(flip.convert("RGB")), "RGB")
    return rgb, Image.fromarray(a, "L")


# ------------------------------------------------------------ shapes
@lru_cache(maxsize=600)
def rounded(w: int, h: int, r: int, color: tuple, ss: int = 3) -> tuple:
    w, h = max(1, int(w)), max(1, int(h))
    im = Image.new("RGBA", (w * ss, h * ss), color + (255,))
    mask = Image.new("L", (w * ss, h * ss), 0)
    d = ImageDraw.Draw(mask)
    d.rounded_rectangle([0, 0, w * ss - 1, h * ss - 1], radius=r * ss, fill=255)
    im.putalpha(mask)
    im = im.resize((w, h), Image.LANCZOS)
    return im.convert("RGB"), im.split()[3]


@lru_cache(maxsize=120)
def hex_badge(size: int, color: tuple, label: str, fg: tuple = C.PAPER) -> tuple:
    ss = 3
    s = size * ss
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    pts = [
        (s * 0.5, s * 0.04),
        (s * 0.96, s * 0.27),
        (s * 0.96, s * 0.73),
        (s * 0.5, s * 0.96),
        (s * 0.04, s * 0.73),
        (s * 0.04, s * 0.27),
    ]
    d.polygon(pts, fill=color + (255,))
    f = C.font("bold", int(s * 0.40))
    tw = d.textlength(label, font=f)
    d.text((s / 2 - tw / 2, s * 0.28), label, font=f, fill=fg)
    im = im.resize((size, size), Image.LANCZOS)
    return im.convert("RGB"), im.split()[3]


# ------------------------------------------------------------ text
@lru_cache(maxsize=900)
def text_img(
    text: str,
    weight: str,
    size: int,
    color: tuple,
    tracking: float = 0.0,
    align: str = "left",
) -> Image.Image:
    """Render a single line with manual letter tracking, on transparent RGBA."""
    f = C.font(weight, size)
    probe = ImageDraw.Draw(Image.new("L", (4, 4)))
    widths = [probe.textlength(ch, font=f) for ch in text]
    asc, desc = f.getmetrics()
    total = sum(widths) + tracking * max(0, len(text) - 1)
    canvas_w = int(math.ceil(total)) + 8
    canvas_h = asc + desc + 8
    im = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    x = 4.0
    if align == "center":
        x = (canvas_w - total) / 2
    elif align == "right":
        x = canvas_w - total - 4
    for ch, w in zip(text, widths):
        d.text((x, 4), ch, font=f, fill=color + (255,))
        x += w + tracking
    return im


def draw_text(
    frame: Image.Image,
    xy: tuple,
    text: str,
    weight: str = "bold",
    size: int = 40,
    color: tuple = C.INK,
    tracking: float = 0.0,
    anchor: str = "lt",
    alpha: float = 1.0,
) -> tuple:
    """Paste a text sprite onto an RGB frame. Returns (x, y, w, h)."""
    if alpha <= 0.01 or not text:
        return (xy[0], xy[1], 0, 0)
    im = text_img(text, weight, size, color, tracking)
    x, y = xy
    if anchor[0] == "m":
        x -= im.width / 2
    elif anchor[0] == "r":
        x -= im.width
    if anchor[1] == "m":
        y -= im.height / 2
    elif anchor[1] == "b":
        y -= im.height
    mask = im.split()[3]
    if alpha < 0.995:
        mask = mask.point(lambda v: int(v * alpha))
    frame.paste(im.convert("RGB"), (int(x), int(y)), mask)
    return (int(x), int(y), im.width, im.height)


def text_width(text: str, weight: str, size: int, tracking: float = 0.0) -> float:
    f = C.font(weight, size)
    probe = ImageDraw.Draw(Image.new("L", (4, 4)))
    return sum(probe.textlength(ch, font=f) for ch in text) + tracking * max(0, len(text) - 1)


def fit_size(text: str, weight: str, max_w: float, start: int, tracking: float = 0.0,
             minimum: int = 12) -> int:
    size = start
    while size > minimum and text_width(text, weight, size, tracking) > max_w:
        size -= 2
    return size


# ------------------------------------------------------------ flags
@lru_cache(maxsize=16)
def flag(size: int, country: str, round_: bool = True) -> Image.Image:
    ss = 3
    s = size * ss
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if country == "us":
        d.rectangle([0, 0, s, s], fill=(255, 255, 255, 255))
        stripe = s / 7.0
        for i in range(7):
            if i % 2 == 0:
                d.rectangle([0, i * stripe, s, (i + 1) * stripe], fill=(178, 34, 52, 255))
        d.rectangle([0, 0, s * 0.42, s * 0.54], fill=(24, 48, 96, 255))
    elif country == "jp":
        # white field, red sun disc, faint keyline so it reads on white chrome
        d.rectangle([0, 0, s, s], fill=(250, 250, 250, 255))
        r = s * 0.30
        d.ellipse([s / 2 - r, s / 2 - r, s / 2 + r, s / 2 + r], fill=(188, 0, 45, 255))
    else:
        d.rectangle([0, 0, s, s], fill=(206, 38, 38, 255))
        # one big star + four small, stylised
        def star(cx, cy, r, rot=-90):
            pts = []
            for k in range(10):
                ang = math.radians(rot + k * 36)
                rr = r if k % 2 == 0 else r * 0.42
                pts.append((cx + rr * math.cos(ang), cy + rr * math.sin(ang)))
            return pts

        d.polygon(star(s * 0.30, s * 0.32, s * 0.17), fill=(250, 214, 60, 255))
        for cx, cy in [(0.50, 0.19), (0.56, 0.32), (0.47, 0.44), (0.62, 0.44)]:
            d.polygon(star(s * cx, s * cy, s * 0.058), fill=(250, 214, 60, 255))
    if round_:
        mask = Image.new("L", (s, s), 0)
        ImageDraw.Draw(mask).ellipse([0, 0, s - 1, s - 1], fill=255)
        im.putalpha(mask)
    im = im.resize((size, size), Image.LANCZOS)
    return im


def draw_flag_chip(frame, x, y, size, country, label, accent, alpha=1.0, align="left",
                   dark=False):
    """Flag + three-letter code in a pill: the visual ID of each side."""
    tw = text_width(label, "bold", int(size * 0.52), tracking=2)
    pad = int(size * 0.36)
    chip_w = int(size + pad * 2 + tw + 6)
    chip_h = int(size + pad * 0.7)
    fg = C.PAPER if dark else C.INK
    bg = accent if dark else (246, 247, 249)
    if align == "right":
        x -= chip_w
    rgb, m = rounded(chip_w, chip_h, chip_h // 2, bg)
    if alpha < 0.995:
        m = m.point(lambda v: int(v * alpha))
    frame.paste(rgb, (int(x), int(y)), m)
    fl = flag(size, country)
    if alpha < 0.995:
        m2 = fl.split()[3].point(lambda v: int(v * alpha))
        frame.paste(fl.convert("RGB"), (int(x + pad * 0.7), int(y + (chip_h - size) / 2)), m2)
    else:
        frame.paste(fl.convert("RGB"), (int(x + pad * 0.7), int(y + (chip_h - size) / 2)), fl.split()[3])
    draw_text(
        frame,
        (x + pad * 0.7 + size + pad * 0.55, y + chip_h / 2),
        label,
        "bold",
        int(size * 0.52),
        C.PAPER if dark else accent,
        tracking=2,
        anchor="lm",
        alpha=alpha,
    )
    return chip_w


def draw_pill(frame, x, y, text, size=22, fg=C.PAPER, bg=C.CHARCOAL, tracking=2.4,
              pad_x=26, pad_y=16, alpha=1.0, align="left"):
    tw = text_width(text, "bold", size, tracking)
    w = int(tw + pad_x * 2)
    h = int(size * 1.0 + pad_y * 2)
    if align == "center":
        x -= w / 2
    elif align == "right":
        x -= w
    rgb, m = rounded(w, h, h // 2, bg)
    if alpha < 0.995:
        m = m.point(lambda v: int(v * alpha))
    frame.paste(rgb, (int(x), int(y)), m)
    draw_text(frame, (x + pad_x, y + h / 2), text, "bold", size, fg, tracking, anchor="lm", alpha=alpha)
    return w, h


# ------------------------------------------------------------ misc
def dashed_line(draw, p0, p1, fill, width=2, dash=12, gap=8):
    x0, y0 = p0
    x1, y1 = p1
    dist = math.hypot(x1 - x0, y1 - y0)
    if dist < 1:
        return
    ux, uy = (x1 - x0) / dist, (y1 - y0) / dist
    pos = 0.0
    while pos < dist:
        end = min(pos + dash, dist)
        draw.line([(x0 + ux * pos, y0 + uy * pos), (x0 + ux * end, y0 + uy * end)],
                  fill=fill, width=width)
        pos = end + gap


def line(draw, p0, p1, fill, width=2, progress=1.0):
    if progress >= 1.0:
        draw.line([p0, p1], fill=fill, width=width)
    elif progress > 0:
        x0, y0 = p0
        x1, y1 = p1
        draw.line([p0, (x0 + (x1 - x0) * progress, y0 + (y1 - y0) * progress)],
                  fill=fill, width=width)


def dot(draw, xy, r, fill):
    draw.ellipse([xy[0] - r, xy[1] - r, xy[0] + r, xy[1] + r], fill=fill)
