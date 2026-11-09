"""Turn a white-background object render into a sprite that sits on the paper.

The template works with catalogue-style plates: the subject photographed (or
rendered) on a plain, near-white backdrop. Instead of tracing a hard silhouette —
which leaves the studio sweep and its shadow behind as grey rectangles — the
image's own luminance becomes the alpha channel. Light paper turns transparent,
the subject keeps its shading, and the soft shadow under it fades into the ivory
page exactly the way it did on white.

This is why any replacement artwork works: a tank, a ship, a jacket, a phone —
photograph it on white and the template blends it in with no masking.
"""
from __future__ import annotations

import numpy as np
from PIL import Image, ImageFilter

# luminance that means "pure page" and luminance that means "solid subject";
# measured per image so a dim or bright plate keys the same way
KEY_PAGE_OFFSET = 1.0
KEY_SOLID_OFFSET = 99.0


def plate(path: str, key_white: float | None = None,
          key_solid: float | None = None, feather: float = 1.5) -> Image.Image:
    """Luminance-keyed RGBA sprite from a white-background image."""
    im = Image.open(path).convert("RGB")
    if feather > 0:
        im = im.filter(ImageFilter.GaussianBlur(feather))
    src = np.asarray(im).astype(np.float32)
    lum = src.mean(axis=2)

    if key_white is None:                       # the page tone of *this* plate
        edges = np.concatenate([lum[0], lum[-1], lum[:, 0], lum[:, -1]])
        key_white = float(np.percentile(edges, 60)) + KEY_PAGE_OFFSET
    if key_solid is None:
        key_solid = key_white - KEY_SOLID_OFFSET

    alpha = np.clip((key_white - lum) / max(1e-6, key_white - key_solid), 0.0, 1.0)
    # sensor/film grain in the plate would otherwise veil the whole page with a
    # faint white rectangle, so anything below the noise floor becomes fully clear
    FLOOR = 0.34
    alpha = np.clip((alpha - FLOOR) / (1.0 - FLOOR), 0.0, 1.0)
    alpha = alpha ** 0.86                     # keep mid-tones a touch denser

    # un-mix the white backdrop so colours stay true where the subject is faint:
    # composite = a*colour + (1-a)*white  ->  colour = (src - (1-a)*white) / a
    safe = np.maximum(alpha[..., None], 0.22)
    true = np.clip((src - 255.0 * (1.0 - alpha[..., None])) / safe, 0, 255)
    rgb = np.where(alpha[..., None] > 0.02, true, src)

    img = Image.fromarray(np.dstack([rgb.astype(np.uint8),
                                     (alpha * 255).astype(np.uint8)]), "RGBA")
    bb = _bbox(img)
    if bb:
        pad = 8
        img = img.crop((max(0, bb[0] - pad), max(0, bb[1] - pad),
                        min(img.width, bb[2] + pad), min(img.height, bb[3] + pad)))
    return img


def _bbox(img: Image.Image) -> tuple | None:
    return img.getchannel("A").point(lambda v: 255 if v > 8 else 0).getbbox()


def contact_shadow(sprite: Image.Image, blur: int = 22, opacity: int = 30):
    """Optional elliptical shadow for artwork that arrives with a hard cut-out.

    Plates shot on white already carry their own shadow, so the renderer only
    calls this when a recipe asks for it.
    """
    from PIL import ImageDraw
    w, h = sprite.size
    a = np.asarray(sprite.getchannel("A"))
    cols = np.where((a > 200).any(axis=0))[0]
    if len(cols) < 4:
        return None
    x0, x1 = int(np.percentile(cols, 2)), int(np.percentile(cols, 98))
    eh = max(10, int(h * 0.05))
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).ellipse([x0, h - eh, x1, h], fill=opacity * 255 // 100)
    mask = mask.filter(ImageFilter.GaussianBlur(blur * 0.6))
    out = Image.new("RGBA", (w, h), (27, 30, 34, 255))
    out.putalpha(mask)
    return out
