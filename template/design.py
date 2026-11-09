"""Design system for the catalogue films: palette, type, paper, chrome.

Everything visual is derived from this module so a new episode keeps the same
look. Change T, PAPER or ACCENT to re-skin the whole series.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
W, H = 1920, 1080
FPS = 24

# ---------------------------------------------------------------- palette
PAPER = (247, 244, 236)          # warm ivory field
PAPER_HI = (253, 251, 246)
INK = (18, 20, 23)               # near-black
INK_70 = (78, 82, 88)
INK_45 = (132, 136, 142)
INK_25 = (196, 195, 190)
INK_35 = (150, 152, 150)
RULE = (222, 219, 210)
RED = (196, 26, 32)              # catalogue accent
RED_DEEP = (150, 18, 24)

FONTS = {
    "display": "ArchivoBlack-Regular.ttf",
    "cond-semi": "BarlowCondensed-SemiBold.ttf",
    "cond-med": "BarlowCondensed-Medium.ttf",
    "cond-light": "BarlowCondensed-Light.ttf",
    "body": "Barlow-Light.ttf",
    "body-bold": "Barlow-SemiBold.ttf",
    "mono": "IBMPlexMono-Regular.ttf",
    "mono-med": "IBMPlexMono-Medium.ttf",
    "plex-cond-bold": "IBMPlexSansCondensed-Bold.ttf",
}


@lru_cache(maxsize=256)
def font(key: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(ROOT / "assets" / "fonts" / FONTS[key]), size)


# ------------------------------------------------------------------- text
@lru_cache(maxsize=4096)
def text_sprite(s: str, fkey: str, size: int, color: tuple, track: float = 0.0) -> Image.Image:
    """Pre-rendered text with letter-spacing, as an RGBA sprite."""
    f = font(fkey, size)
    pad = int(size * 0.45) + 8
    if not s:
        return Image.new("RGBA", (1, 1), (0, 0, 0, 0))
    widths = [f.getlength(ch) for ch in s]
    total = sum(widths) + track * max(0, len(s) - 1)
    # metrics via a temp draw
    tmp = Image.new("L", (1, 1))
    d = ImageDraw.Draw(tmp)
    asc, desc = d.textbbox((0, 0), s, font=f)[:2], None
    l, t, r, b = d.textbbox((0, 0), s, font=f)
    img = Image.new("RGBA", (int(total) + pad * 2, b + pad * 2 + 4), (0, 0, 0, 0))
    dr = ImageDraw.Draw(img)
    x = float(pad)
    for ch, w in zip(s, widths):
        dr.text((x, pad), ch, font=f, fill=color + (255,))
        x += w + track
    return img


def put(img: Image.Image, spr: Image.Image, xy, alpha: float = 1.0) -> None:
    """Composite a sprite at a top-left position (floats allowed)."""
    if alpha <= 0.001 or spr.width < 1:
        return
    if alpha < 0.999:
        spr = spr.copy()
        spr.putalpha(spr.getchannel("A").point(lambda v: int(v * alpha)))
    img.alpha_composite(spr, (int(round(xy[0])), int(round(xy[1]))))


def ink_offset(fkey: str, size: int) -> int:
    """Distance from a sprite's top edge down to the text baseline."""
    f = font(fkey, size)
    return int(size * 0.45) + 8 + f.getmetrics()[0]


def text(img, s, xy, fkey="mono", size=16, color=INK, track=0.0, alpha=1.0,
         anchor="lt") -> None:
    spr = text_sprite(s, fkey, size, color, track)
    x, y = xy
    if anchor[0] == "c":
        x -= spr.width / 2
    elif anchor[0] == "r":
        x -= spr.width
    if anchor[1] == "c":
        y -= spr.height / 2
    elif anchor[1] == "b":
        y -= spr.height
    elif anchor[1] == "s":          # baseline
        y -= ink_offset(fkey, size)
    put(img, spr, (x, y), alpha)


def measure(s: str, fkey: str, size: int, track: float = 0.0) -> tuple[int, int]:
    spr = text_sprite(s, fkey, size, (0, 0, 0), track)
    return spr.width, spr.height


def wrap(s: str, fkey: str, size: int, max_w: float, track: float = 0.0) -> list[str]:
    f = font(fkey, size)
    words = s.split()
    lines, cur = [], ""
    for w in words:
        trial = f"{cur} {w}".strip()
        if f.getlength(trial) + track * len(trial) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


# ------------------------------------------------------------------ paper
def _grain(img: Image.Image, sigma: float = 2.6, seed: int = 11) -> Image.Image:
    a = np.asarray(img.convert("RGB")).astype(np.float32)
    rng = np.random.default_rng(seed)
    hh, ww = H // 2 + 1, W // 2 + 1
    n = rng.normal(0, sigma * 2.0, (hh, ww)).astype(np.float32)
    n = np.repeat(np.repeat(n, 2, axis=0), 2, axis=1)[:H, :W]
    a = np.clip(a + n[..., None], 0, 255)
    return Image.fromarray(a.astype(np.uint8), "RGB").convert("RGBA")


@lru_cache(maxsize=8)
def reference_plate() -> Image.Image:
    """The paper field every catalogue page sits on."""
    img = Image.new("RGBA", (W, H), PAPER + (255,))
    # soft corner falloff so the sheet is not dead flat
    corners = Image.new("RGBA", (W // 2, H // 2), (255, 255, 255, 0))
    d = ImageDraw.Draw(corners)
    r = 210
    for cx, cy in ((0, 0), (W // 2, 0), (0, H // 2), (W // 2, H // 2)):
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(255, 253, 246, 22))
    corners = corners.resize((W, H), Image.BICUBIC).filter(ImageFilter.GaussianBlur(190))
    img = Image.alpha_composite(img, corners)
    return _grain(img, 2.4, 11)


def plate_grain(img: Image.Image, sigma: float = 1.7, seed: int = 31) -> None:
    """Per-frame noise, in place, so static pages do not look like stills."""
    a = np.asarray(img.convert("RGB")).astype(np.float32)
    rng = np.random.default_rng(seed)
    n = rng.normal(0, sigma * 2.0, (H // 2 + 1, W // 2 + 1)).astype(np.float32)
    n = np.repeat(np.repeat(n, 2, axis=0), 2, axis=1)[:H, :W]
    img.paste(Image.fromarray(np.clip(a + n[..., None], 0, 255).astype(np.uint8), "RGB"))


# ----------------------------------------------------------------- chrome
def hairline(img, xy, w, color=RULE, thick=1, alpha=1.0) -> None:
    if w <= 0:
        return
    layer = Image.new("RGBA", (int(w) + 2, thick + 2), (0, 0, 0, 0))
    ImageDraw.Draw(layer).rectangle([0, 0, int(w), thick - 1], fill=color + (255,))
    put(img, layer, xy, alpha)


def box(img, xy, w, h, fill=None, outline=None, thick=1, alpha=1.0) -> None:
    layer = Image.new("RGBA", (int(w), int(h)), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    if fill:
        d.rectangle([0, 0, int(w) - 1, int(h) - 1], fill=fill + (255,))
    if outline:
        d.rectangle([0, 0, int(w), int(h)], outline=outline + (255,), width=thick)
    put(img, layer, xy, alpha)


def top_chrome(img, left: str, right: str, y: int = 24) -> None:
    """The two running headers every catalogue page carries."""
    text(img, left, (86, y), "mono", 11, INK_45, 4.0)
    text(img, right, (W - 86, y - 8), "mono", 11, INK_45, 4.0, anchor="rt")
    hairline(img, (86, y + 26), 26, RED, 3)


def bottom_chrome(img, timecode: str, label: str, progress: float,
                 label_x: int = 300) -> None:
    y = H - 62
    hairline(img, (86, y - 14), W - 172, RULE, 1)
    box(img, (86, y + 4), 9, 9, fill=RED)
    text(img, timecode, (110, y - 4), "mono", 15, INK_70, 2.0)
    text(img, label.upper(), (label_x, y - 4), "mono", 13, INK_45, 4.5)
    # progress rail
    rail_y = y + 30
    hairline(img, (86, rail_y), W - 172, RULE, 2)
    hairline(img, (86, rail_y), max(2, int((W - 172) * min(1.0, progress))), RED, 2)
    box(img, (86 + (W - 172) * min(1.0, progress) - 3, rail_y - 4), 7, 7, fill=RED)


def chip(img, xy, s: str, fkey: str, size: int, color: tuple, fill: tuple,
         track: float = 0.0, pad_x: int = 22, pad_y: int = 12) -> tuple[int, int]:
    """A solid chip whose label sits optically centred on its ink, not its box."""
    spr = text_sprite(s, fkey, size, color, track)
    bb = spr.getchannel("A").getbbox() or (0, 0, spr.width, spr.height)
    iw, ih = bb[2] - bb[0], bb[3] - bb[1]
    w, h = int(iw + pad_x * 2), int(ih + pad_y * 2)
    box(img, xy, w, h, fill=fill)
    put(img, spr, (xy[0] + pad_x - bb[0], xy[1] + pad_y - bb[1]))
    return w, h


def text_centered(img, s: str, center, fkey="display", size=40, color=(255, 255, 255),
                  track: float = 0.0, alpha: float = 1.0) -> None:
    """Draw text centred on the *ink* of the glyphs, not on the sprite box.

    Matters inside solid chips: a box-centred glyph sits low because every sprite
    carries a font-metric margin above the cap height.
    """
    spr = text_sprite(s, fkey, size, color, track)
    bb = spr.getchannel("A").getbbox()
    if not bb:
        return
    cx = (bb[0] + bb[2]) / 2
    cy = (bb[1] + bb[3]) / 2
    put(img, spr, (center[0] - cx, center[1] - cy), alpha)
