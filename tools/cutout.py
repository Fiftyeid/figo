"""Studio-white background knockout + grounding shadow for aircraft renders.

The generated plates are photographed on a seamless near-white studio sweep,
so the background can be removed by a flood fill from the frame border, then
feathered so the aircraft sits cleanly on the film's grid background.
"""
from __future__ import annotations

import numpy as np
from PIL import Image, ImageFilter


def _bg_mask(rgb: np.ndarray, white_min: int = 228, sat_max: int = 16) -> np.ndarray:
    """Pixels that could belong to the white sweep (near-white, low saturation)."""
    r, g, b = rgb[..., 0].astype(np.int16), rgb[..., 1].astype(np.int16), rgb[..., 2].astype(np.int16)
    mn = np.minimum(np.minimum(r, g), b)
    mx = np.maximum(np.maximum(r, g), b)
    return (mn >= white_min) & ((mx - mn) <= sat_max)


def _flood_from_border(candidate: np.ndarray) -> np.ndarray:
    """Grow a region from the border through the candidate mask (4-connected)."""
    h, w = candidate.shape
    reached = np.zeros((h, w), bool)
    reached[0, :] = candidate[0, :]
    reached[-1, :] = candidate[-1, :]
    reached[:, 0] |= candidate[:, 0]
    reached[:, -1] |= candidate[:, -1]
    while True:
        grown = reached.copy()
        grown[1:, :] |= reached[:-1, :]
        grown[:-1, :] |= reached[1:, :]
        grown[:, 1:] |= reached[:, :-1]
        grown[:, :-1] |= reached[:, 1:]
        grown &= candidate
        if grown.sum() == reached.sum():
            return reached
        reached = grown


def cutout(path: str, pad: int = 6) -> Image.Image:
    """Return an RGBA crop of the aircraft with the studio sweep removed."""
    im = Image.open(path).convert("RGB")
    rgb = np.asarray(im)
    bg = _flood_from_border(_bg_mask(rgb))

    alpha = np.where(bg, 0.0, 1.0)
    a = Image.fromarray((alpha * 255).astype(np.uint8), "L")
    # kill the white halo: pull the matte in slightly, then feather back out
    a = a.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(1.1))

    # un-premultiply the studio white bleed on soft edges so no glowing rim remains
    af = np.asarray(a).astype(np.float32) / 255.0
    edge = (af > 0.02) & (af < 0.985)
    src = rgb.astype(np.float32)
    with np.errstate(divide="ignore", invalid="ignore"):
        un = (src - 255.0 * (1.0 - af[..., None])) / np.maximum(af[..., None], 1e-3)
    src[edge] = np.clip(un[edge], 0, 255)

    out = np.dstack([src.astype(np.uint8), (af * 255).astype(np.uint8)])
    img = Image.fromarray(out, "RGBA")

    bbox = img.getchannel("A").point(lambda v: 255 if v > 12 else 0).getbbox()
    if bbox:
        x0, y0, x1, y1 = bbox
        img = img.crop((max(0, x0 - pad), max(0, y0 - pad),
                        min(img.width, x1 + pad), min(img.height, y1 + pad)))
    return img


def ground_shadow(sprite: Image.Image, blur: int = 26, opacity: int = 46) -> Image.Image:
    """Soft elliptical contact shadow derived from the sprite's own silhouette."""
    w, h = sprite.size
    mask = sprite.getchannel("A").resize((max(1, w), max(1, int(h * 0.30))), Image.LANCZOS)
    mask = mask.filter(ImageFilter.GaussianBlur(blur * 0.35))
    sh = Image.new("RGBA", (w, int(h * 0.30)), (0, 0, 0, 0))
    sh.putalpha(mask.point(lambda v: int(v * opacity / 255)))
    black = Image.new("RGBA", sh.size, (23, 26, 30, 255))
    black.putalpha(sh.getchannel("A"))
    return black.filter(ImageFilter.GaussianBlur(blur * 0.5))
