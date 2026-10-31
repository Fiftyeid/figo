"""Procedurally generated art: camouflage swatches and to-scale cartridges."""
from __future__ import annotations

import math
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw, ImageFilter


# ================================================================ camo
def _noise(h, w, scale, seed):
    rng = np.random.default_rng(seed)
    small = rng.random((max(2, h // scale), max(2, w // scale))).astype(np.float32)
    im = Image.fromarray((small * 255).astype(np.uint8), "L")
    im = im.resize((w, h), Image.BICUBIC).filter(ImageFilter.GaussianBlur(scale * 0.6))
    return np.asarray(im).astype(np.float32) / 255.0


@lru_cache(maxsize=8)
def _camouflage(side: str, w: int, h: int) -> Image.Image:
    if side == "left":  # OCP-ish: soft multi-terrain blotches
        base = np.array([176, 156, 116], dtype=np.float32)
        layers = [
            (np.array([122, 104, 74], dtype=np.float32), 0.56, 13, 1),
            (np.array([88, 92, 62], dtype=np.float32), 0.50, 9, 2),
            (np.array([214, 198, 164], dtype=np.float32), 0.62, 17, 3),
            (np.array([144, 120, 84], dtype=np.float32), 0.68, 6, 4),
        ]
        img = np.repeat(np.repeat(base[None, None, :], h, axis=0), w, axis=1)
        for col, thresh, sc, seed in layers:
            n = _noise(h, w, sc, seed)
            mask = np.clip((n - thresh) * 7.0, 0, 1)[..., None]
            img = img * (1 - mask) + col * mask
        # fine grain
        rng = np.random.default_rng(11)
        img += rng.normal(0, 5, (h, w, 1))
    else:  # Xingkong-21-ish: digital pixel field
        cell = max(6, w // 46)
        rng = np.random.default_rng(7)
        gh, gw = h // cell + 2, w // cell + 2
        n = rng.random((gh, gw)).astype(np.float32)
        n = np.asarray(
            Image.fromarray((n * 255).astype(np.uint8), "L").resize((gw, gh), Image.BILINEAR)
        ).astype(np.float32) / 255.0
        n = (n + rng.random((gh, gw)) * 0.55) / 1.55
        pal = np.array(
            [
                [58, 84, 84],
                [96, 122, 116],
                [140, 158, 148],
                [44, 62, 66],
                [176, 186, 172],
            ],
            dtype=np.float32,
        )
        idx = np.clip((n * len(pal)).astype(int), 0, len(pal) - 1)
        small = pal[idx]
        im = Image.fromarray(small.astype(np.uint8), "RGB").resize((w, h), Image.NEAREST)
        img = np.asarray(im).astype(np.float32)
        # subtle fabric shading
        yy = np.linspace(0, 1, h, dtype=np.float32)[:, None, None]
        img = img * (0.93 + 0.12 * (1 - yy))
    # studio light falloff so it reads as fabric, not wallpaper
    xs = np.linspace(-1, 1, w, dtype=np.float32)[None, :]
    ys = np.linspace(-1, 1, h, dtype=np.float32)[:, None]
    light = 1.06 - 0.16 * np.sqrt(xs ** 2 * 0.7 + ys ** 2)
    img = np.clip(img * light[..., None], 0, 255)

    im = Image.fromarray(img.astype(np.uint8), "RGB").convert("RGBA")
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, w - 1, h - 1], radius=26, fill=255)
    im.putalpha(mask)
    return im


def camouflage(side: str, w: int, h: int) -> Image.Image:
    return _camouflage(side, int(w), int(h))


# ================================================================ cartridge
@lru_cache(maxsize=16)
def _cartridge(cal_mm: float, h: int) -> Image.Image:
    """Schematic cartridge drawn at relative scale, lying left to right."""
    h = max(24, int(h))
    L = int(h * 5.6)
    ss = 2
    W, Hh = L * ss, int(h * 1.35) * ss
    im = Image.new("RGBA", (W, Hh), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)

    cy = Hh / 2
    r = Hh * 0.30                    # case radius
    brass = (188, 148, 84)
    brass_d = (132, 101, 55)
    bullet = (150, 116, 74)
    bullet_l = (186, 152, 104)

    x_case0 = W * 0.34
    x_case1 = W * 0.995
    x_shoulder = W * 0.24
    x_neck = W * 0.21
    x_tip = W * 0.01

    # case body
    d.rounded_rectangle([x_case0, cy - r, x_case1, cy + r], radius=r * 0.22,
                        fill=brass + (255,))
    brass_l = (206, 168, 104, 255)
    d.rectangle([x_case0, cy - r * 0.42, x_case1, cy - r * 0.06], fill=brass_l)
    # rim + primer
    d.rounded_rectangle([x_case1 - r * 0.30, cy - r * 1.06, x_case1, cy + r * 1.06],
                        radius=r * 0.18, fill=brass_d + (255,))
    d.ellipse([x_case1 - r * 0.24, cy - r * 0.42, x_case1 + r * 0.06, cy + r * 0.42],
              fill=(120, 96, 60, 255))
    # shoulder
    d.polygon(
        [
            (x_shoulder, cy - r * 0.62),
            (x_case0 + 2, cy - r),
            (x_case0 + 2, cy + r),
            (x_shoulder, cy + r * 0.62),
        ],
        fill=brass + (255,),
    )
    # neck
    d.rectangle([x_neck, cy - r * 0.62, x_shoulder + 2, cy + r * 0.62], fill=brass + (255,))
    # bullet ogive
    d.polygon(
        [
            (x_tip, cy),
            (x_neck + W * 0.035, cy - r * 0.60),
            (x_neck, cy - r * 0.62),
            (x_neck, cy + r * 0.62),
            (x_neck + W * 0.035, cy + r * 0.60),
        ],
        fill=bullet + (255,),
    )
    d.line([(x_neck, cy - r * 0.30), (x_neck + W * 0.03, cy - r * 0.28)],
           fill=bullet_l + (255,), width=max(2, int(r * 0.18)))

    im = im.resize((L, int(h * 1.35)), Image.LANCZOS)

    # faint floor shadow baked in
    sh = Image.new("L", im.size, 0)
    ImageDraw.Draw(sh).ellipse(
        [im.width * 0.05, im.height * 0.80, im.width * 0.98, im.height * 0.99], fill=60
    )
    sh = sh.filter(ImageFilter.GaussianBlur(10))
    out = Image.new("RGBA", im.size, (0, 0, 0, 0))
    out.paste((24, 27, 32), (0, 0), sh)
    out.alpha_composite(im)
    return out


def cartridge(cal_mm: float, h: int) -> Image.Image:
    return _cartridge(round(float(cal_mm), 1), int(h))
