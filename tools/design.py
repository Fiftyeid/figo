"""Design system for the U.S. Naval Aviation catalogue film.

Editorial / technical-plate aesthetic: warm white paper, hairline rules,
condensed display type, letterspaced mono labels, one red accent.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
FONTS = ROOT / "assets" / "fonts"

W, H = 1920, 1080
M = 104           # outer margin
TOP = 64          # top rule

# ---------------------------------------------------------------- palette
PAPER = (253, 253, 250)
PAPER_HI = (255, 255, 255)
INK = (21, 24, 28)
INK_70 = (82, 87, 94)
INK_45 = (139, 143, 148)
INK_25 = (198, 199, 198)
RULE = (223, 222, 216)
RULE_SOFT = (233, 232, 226)
RED = (198, 32, 34)
RED_DEEP = (150, 22, 24)
RED_TINT = (243, 226, 226)

# ---------------------------------------------------------------- fonts
_FONT_FILES = {
    "disp-bold": "BarlowCondensed-Bold.ttf",
    "disp-semi": "BarlowCondensed-SemiBold.ttf",
    "disp-med": "BarlowCondensed-Medium.ttf",
    "disp-light": "BarlowCondensed-Light.ttf",
    "sans-light": "Barlow-Light.ttf",
    "sans": "Barlow-Medium.ttf",
    "sans-semi": "Barlow-SemiBold.ttf",
    "mono": "IBMPlexMono-Regular.ttf",
    "mono-med": "IBMPlexMono-Medium.ttf",
    "black": "ArchivoBlack-Regular.ttf",
    "cond-bold": "IBMPlexSansCondensed-Bold.ttf",
}


@lru_cache(maxsize=4096)
def font(key: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONTS / _FONT_FILES[key]), size)


def tw(draw: ImageDraw.ImageDraw, text: str, f: ImageFont.FreeTypeFont) -> float:
    return draw.textlength(text, font=f)


# ------------------------------------------------------- cached text sprites
@lru_cache(maxsize=20000)
def text_sprite(text: str, fkey: str, size: int, color: tuple, track: float = 0.0,
                shadow: bool = False, stroke: int = 0, stroke_fill: tuple | None = None) -> Image.Image:
    """Rendered text as an RGBA sprite (cached) so per-frame compositing is cheap."""
    f = font(fkey, size)
    tmp = ImageDraw.Draw(Image.new("RGBA", (8, 8)))
    if track:
        widths = [tmp.textlength(ch, font=f) for ch in text]
        total = sum(widths) + track * max(0, len(text) - 1)
        asc, desc = f.getmetrics()
        img = Image.new("RGBA", (int(total) + 4, asc + desc + 4), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        x = 2
        for ch, w in zip(text, widths):
            d.text((x, 2), ch, font=f, fill=color + (255,),
                   stroke_width=stroke, stroke_fill=(stroke_fill or color) + (255,))
            x += w + track
    else:
        l, t, r, b = tmp.textbbox((0, 0), text, font=f, stroke_width=stroke)
        pad = stroke + 2
        img = Image.new("RGBA", (max(1, int(r - l) + 2 * pad), max(1, int(b - t) + 2 * pad)),
                        (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.text((pad - l, pad - t), text, font=f, fill=color + (255,),
               stroke_width=stroke, stroke_fill=(stroke_fill or color) + (255,))
    if shadow:
        a = img.getchannel("A").filter(ImageFilter.GaussianBlur(6))
        sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
        sh.putalpha(a.point(lambda v: int(v * 0.30)))
        out = Image.new("RGBA", img.size, (0, 0, 0, 0))
        out.alpha_composite(sh, (0, 3))
        out.alpha_composite(img)
        img = out
    return img


def put(img: Image.Image, sprite: Image.Image, xy: tuple[float, float],
        alpha: float = 1.0) -> None:
    if alpha <= 0.004:
        return
    if alpha < 0.999:
        s = sprite.copy()
        s.putalpha(s.getchannel("A").point(lambda v: int(v * alpha)))
        sprite = s
    img.alpha_composite(sprite, (int(round(xy[0])), int(round(xy[1]))))


def text(img, s, xy, fkey="mono", size=16, color=INK, track=0.0, alpha=1.0,
         anchor="lt", shadow=False, stroke=0, stroke_fill=None):
    """Draw cached text. anchor: l/c/r + t/m/b (e.g. 'ct', 'rm', 'lb')."""
    spr = text_sprite(s, fkey, size, tuple(color), track, shadow, stroke,
                      tuple(stroke_fill) if stroke_fill else None)
    ax, ay = anchor[0], anchor[1]
    x, y = xy
    if ax == "c":
        x -= spr.width / 2
    elif ax == "r":
        x -= spr.width
    if ay == "m":
        y -= spr.height / 2
    elif ay == "b":
        y -= spr.height
    put(img, spr, (x, y), alpha)
    return spr.width


def wrap(draw, s: str, fkey: str, size: int, max_w: float, track: float = 0.0):
    f = font(fkey, size)
    words, lines, cur = s.split(), [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        probe = draw.textlength(trial, font=f) + track * max(0, len(trial) - 1)
        if probe <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def fit_size(draw, s: str, fkey: str, max_w: float, start: int, minimum: int,
             track_ratio: float = 0.0) -> int:
    size = start
    while size > minimum:
        f = font(fkey, size)
        w = draw.textlength(s, font=f) + track_ratio * size * max(0, len(s) - 1)
        if w <= max_w:
            return size
        size -= 2
    return minimum


# ---------------------------------------------------------------- ornaments
def hairline(img, xy, w, color=RULE, thick=1, alpha=1.0):
    if w < 1 or alpha <= 0.004:
        return
    x, y = xy
    if alpha < 0.999:
        color = tuple(int(c * alpha + PAPER[i] * (1 - alpha)) for i, c in enumerate(color))
    ImageDraw.Draw(img).rectangle([x, y, x + w - 1, y + thick - 1], fill=color)


def box(img, xy, w, h, fill=None, outline=None, thick=1, alpha=1.0):
    """Filled / outlined rectangle with optional transparency."""
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    a = int(255 * alpha)
    if fill:
        d.rectangle([xy[0], xy[1], xy[0] + w - 1, xy[1] + h - 1],
                    fill=tuple(fill) + (a,))
    if outline:
        for k in range(thick):
            d.rectangle([xy[0] + k, xy[1] + k, xy[0] + w - 1 - k, xy[1] + h - 1 - k],
                        outline=tuple(outline) + (a,))
    img.alpha_composite(layer)


def tick_corners(img, xy, w, h, color=INK_25, size=16, thick=2, alpha=1.0):
    x, y = xy
    c = color
    for (px, py, dx, dy) in ((x, y, 1, 1), (x + w, y, -1, 1), (x, y + h, 1, -1), (x + w, y + h, -1, -1)):
        hairline(img, (px if dx > 0 else px - size, py), size, c, thick, alpha)
        x0 = px if dx > 0 else px - thick + 1
        ImageDraw.Draw(img).rectangle([x0, py if dy > 0 else py - size, x0 + thick - 1,
                                       (py + size - 1) if dy > 0 else py], fill=c)


# ---------------------------------------------------------------- backdrop
@lru_cache(maxsize=8)
def grid_plate(step: int = 60, opacity: float = 0.35) -> Image.Image:
    """Warm paper with a faint drafted grid + soft corner glow."""
    # vignette base first: edges settle a touch darker than the centre
    vig = Image.new("L", (W // 4, H // 4), 0)
    dv = ImageDraw.Draw(vig)
    dv.ellipse([-W // 16, -H // 10, W // 4 + W // 16, H // 4 + H // 10], fill=120)
    vig = vig.resize((W, H), Image.BICUBIC).filter(ImageFilter.GaussianBlur(70))
    img = Image.composite(Image.new("RGBA", (W, H), PAPER + (255,)),
                          Image.new("RGBA", (W, H), (240, 237, 230, 255)), vig)
    d = ImageDraw.Draw(img)
    minor = tuple(int(PAPER[i] + (196 - PAPER[i]) * 0.085 * opacity) for i in range(3))
    major = tuple(int(PAPER[i] + (170 - PAPER[i]) * 0.16 * opacity) for i in range(3))
    for x in range(0, W + 1, step):
        d.line([(x, 0), (x, H)], fill=minor + (255,))
    for y in range(0, H + 1, step):
        d.line([(0, y), (W, y)], fill=minor + (255,))
    for x in range(0, W + 1, step * 5):
        d.line([(x, 0), (x, H)], fill=major + (255,))
    for y in range(0, H + 1, step * 5):
        d.line([(0, y), (W, y)], fill=major + (255,))

    # paper grain gives the plate an analogue, printed feel
    return _grain(img, 2.2, 7)


def chrome(img: Image.Image, progress: float = 0.0, timecode: str = "",
           section: str = "", counter: str = "") -> None:
    """Persistent frame furniture: top rule, footer rule, timecode, progress."""
    d = ImageDraw.Draw(img)
    hairline(img, (M, TOP), W - 2 * M, RULE)
    hairline(img, (M, TOP), 72, RED, 3)

    text(img, "U.S. NAVAL AVIATION", (M, 26), "mono-med", 14, INK_45, 5.5)
    text(img, "FLEET CATALOGUE · 2026", (W - M, 26), "mono-med", 14, INK_45, 5.5, anchor="rt")

    # footer: rule, then a row of metadata, then the progress rail
    fy = H - 84
    hairline(img, (M, fy), W - 2 * M, RULE)
    ry = fy + 22
    if timecode:
        d.rectangle([M, ry + 2, M + 7, ry + 9], fill=RED)
        text(img, timecode, (M + 20, ry - 3), "mono-med", 16, INK, 2.6)
    if section:
        text(img, section.upper(), (M + 168, ry - 2), "mono", 13, INK_45, 3.6)
    if counter:
        text(img, counter, (W - M, ry - 3), "mono-med", 16, INK, 2.6, anchor="rt")

    py = H - 34
    track_w = W - 2 * M
    hairline(img, (M, py), track_w, RULE, 2)
    p = min(1.0, max(0.0, progress))
    if p > 0:
        hairline(img, (M, py), max(3, track_w * p), RED, 2)
        x = M + track_w * p
        d.rectangle([x - 1.5, py - 4, x + 1.5, py + 5], fill=RED)


def plate_label(img, xy, w, label: str, value: str, alpha=1.0):
    """Small caption block: letterspaced label over a value."""
    x, y = xy
    text(img, label, (x, y), "mono", 12, INK_45, 3.2, alpha=alpha)
    text(img, value, (x, y + 18), "disp-med", 26, INK, 0.6, alpha=alpha)


def status_chip(img, xy, label, color=RED, alpha=1.0, fkey="mono-med", size=14,
                dark_text=False, track=3.0):
    """Solid badge with letterspaced caps; returns (width, height)."""
    pad_x, pad_y = 15, 9
    tmp = ImageDraw.Draw(Image.new("RGBA", (8, 8)))
    f = font(fkey, size)
    w = tmp.textlength(label, font=f) + track * max(0, len(label) - 1) + 2 * pad_x + 2
    h = size + 2 * pad_y + 2
    box(img, xy, w, h, fill=color, alpha=alpha)
    text(img, label, (xy[0] + pad_x, xy[1] + pad_y), fkey, size,
         PAPER_HI if not dark_text else INK, track, alpha)
    return w, h


@lru_cache(maxsize=48)
def _glow_sprite(w: int, h: int) -> Image.Image:
    sm = Image.new("L", (240, 240), 0)
    ImageDraw.Draw(sm).ellipse([18, 18, 222, 222], fill=255)
    sm = sm.filter(ImageFilter.GaussianBlur(46)).resize((w, h), Image.BICUBIC)
    layer = Image.new("RGBA", (w, h), (255, 255, 255, 0))
    layer.putalpha(sm.point(lambda v: int(v * 0.55)))
    return layer


def glow(img: Image.Image, centre, rx: float, ry: float, strength: float = 0.5) -> None:
    """Soft white pool of light under a subject, lifting it off the paper."""
    if strength <= 0.01:
        return
    w, h = int(rx * 2), int(ry * 2)
    spr = _glow_sprite(w, h)
    if strength < 0.999:
        spr = spr.copy()
        spr.putalpha(spr.getchannel("A").point(lambda v: int(v * strength)))
    img.alpha_composite(spr, (int(centre[0] - rx), int(centre[1] - ry)))


# ---------------------------------------------------------------- title plate
@lru_cache(maxsize=4)
def intro_plate() -> Image.Image:
    """Pure white card, with only soft blurred gradients in the corners.

    Matches the reference intro: white field, no grid, no moving background
    elements, just gentle corner falloff so the type sits in a pool of light.
    """
    img = Image.new("RGBA", (W, H), (255, 255, 255, 255))
    corners = Image.new("RGBA", (W // 2, H // 2), (255, 255, 255, 0))
    d = ImageDraw.Draw(corners)
    r = 210
    for (cx, cy) in ((0, 0), (W // 2, 0), (0, H // 2), (W // 2, H // 2)):
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(250, 249, 246, 24))
    corners = corners.resize((W, H), Image.BICUBIC).filter(ImageFilter.GaussianBlur(190))
    img = Image.alpha_composite(img, corners)

    return _grain(img, 2.6, 11)


def _grain(img: Image.Image, sigma: float = 2.2, seed: int = 7) -> Image.Image:
    """Signed luminance grain that leaves mean brightness untouched."""
    a = np.asarray(img.convert("RGB")).astype(np.float32)
    rng = np.random.default_rng(seed)
    hh, ww = H // 2 + 1, W // 2 + 1
    n = rng.normal(0, sigma * 2.0, (hh, ww)).astype(np.float32)
    n = np.repeat(np.repeat(n, 2, axis=0), 2, axis=1)[:H, :W]
    # soften the 2x2 blocks so the grain reads as film, not as blocks
    n = (n + np.roll(n, 1, 0) + np.roll(n, 1, 1) + np.roll(np.roll(n, 1, 0), 1, 1)) / 4.0
    a = np.clip(a + n[..., None], 0, 255)
    return Image.fromarray(a.astype(np.uint8), "RGB").convert("RGBA")


def sweep_text(img, xy, text_s, t, start, dur, strength=0.9, anchor="cm"):
    """Type with a light band travelling left → right across the glyphs."""
    spr = text_s
    x, y = xy
    if anchor[0] == "c":
        x -= spr.width / 2
    if anchor[1] == "m":
        y -= spr.height / 2

    # travel from before the first glyph to past the last
    p = (t - start) / max(dur, 1e-6)
    p = max(0.0, min(1.0, p))
    band_c = -0.35 + 1.7 * p
    bw = 0.42
    step = 6
    w, h = spr.size
    mask = Image.new("L", (w, h), 0)
    md = ImageDraw.Draw(mask)
    for gx in range(0, w, step):
        u = gx / max(w - 1, 1)
        dist = abs(u - band_c) / bw
        v = max(0.0, 1.0 - dist) ** 1.8
        if v > 0.004:
            md.rectangle([gx, 0, gx + step, h], fill=int(255 * v))

    sheen = Image.new("RGBA", (w, h), (255, 255, 255, 255))
    a = Image.composite(mask, Image.new("L", (w, h), 0), spr.getchannel("A"))
    sheen.putalpha(a.point(lambda v: int(v * strength)))
    img.alpha_composite(sheen, (int(x), int(y)))


# ------------------------------------------------------- reference-matched kit
IVORY_HI = (245, 239, 228)
IVORY_LO = (252, 247, 237)
FLOOR = (250, 245, 235)
SLAB = (17, 17, 17)
SLAB_RED = (156, 30, 30)
RIBBON = (176, 38, 34)
GRID = (222, 214, 200)
RED_TITLE = (232, 51, 42)
REG_LABEL = (46, 43, 38)       # register caps — near-ink so they read at 1080p

OP_NAMES = {"USN": "Navy", "USMC": "Marine Corps", "USN / USMC": "Navy / Marines",
            "USMC / USN": "Marines / Navy"}


@lru_cache(maxsize=4)
def reference_plate(horizon: int = 700) -> Image.Image:
    """Ivory catalogue backdrop: soft vertical sweep, horizon, floor grid."""
    y = np.arange(H, dtype=np.float32)[:, None]
    t = np.clip(y / float(horizon), 0, 1) ** 0.85
    top = np.array(IVORY_HI, np.float32)
    bot = np.array(IVORY_LO, np.float32)
    col = top + (bot - top) * t
    col[y[:, 0] > horizon] = np.array(FLOOR, np.float32)
    a = np.repeat(col[:, None, :], W, axis=1)

    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    below = yy >= horizon
    depth = np.clip((yy - horizon) / max(1.0, H - horizon), 0, 1)
    cx = W * 0.5
    vp_y = horizon - 520.0
    spacing = 132.0
    gx = (xx - cx) / np.maximum(yy - vp_y, 1.0)
    gxa = np.abs((gx / (spacing / 620.0)) % 1.0 - 0.5)
    glow_w = 0.6 + 0.9 * depth
    vgrid = np.clip(1.0 - gxa * 620.0 / (18.0 * glow_w), 0, 1)
    f = 1.0 / np.maximum(1.0 - depth * 0.86, 1e-3)
    hz = np.abs((f * 2.6) % 1.0 - 0.5)
    hgrid = np.clip(1.0 - hz * 2.0 / 0.24, 0, 1)
    grid = (vgrid * 0.55 + hgrid * 0.45) * below * 0.55
    a = a + (np.array(GRID, np.float32) - a) * grid[..., None] * 0.5

    seam = np.exp(-((yy - horizon) / 26.0) ** 2) * 6.0
    a = np.clip(a + seam[..., None], 0, 255)
    return _grain(Image.fromarray(a.astype(np.uint8), "RGB").convert("RGBA"), 2.0, 23)


def plate_grain(img: Image.Image, sigma: float = 1.7, seed: int = 31) -> None:
    """Per-frame film grain, so the static ivory plate never looks like a still."""
    a = np.asarray(img.convert("RGB")).astype(np.float32)
    rng = np.random.default_rng(seed)
    n = rng.normal(0, sigma * 2.0, (H // 2 + 1, W // 2 + 1)).astype(np.float32)
    n = np.repeat(np.repeat(n, 2, axis=0), 2, axis=1)[:H, :W]
    n = (n + np.roll(n, 1, 0) + np.roll(n, 1, 1) + np.roll(np.roll(n, 1, 0), 1, 1)) / 4.0
    a = np.clip(a + n[..., None], 0, 255)
    img.paste(Image.fromarray(a.astype(np.uint8), "RGB").convert("RGBA"), (0, 0))


def title_slab(img, xy, label: str, fkey: str = "black", size: int = 60,
               track: float = -0.4, alpha: float = 1.0, pad_x: int = 22,
               pad_y: int = 10, spine: int = 5) -> tuple[int, int]:
    """Black slab, red spine on its left edge, reversed-out title."""
    if alpha <= 0.004:
        return (0, 0)
    spr = text_sprite(label, fkey, size, (255, 255, 255), track)
    w = spr.width + pad_x * 2
    h = spr.height + pad_y * 2 - 4
    x, y = int(xy[0]), int(xy[1])
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    a8 = int(255 * alpha)
    d.rectangle([x, y, x + w - 1, y + h - 1], fill=SLAB + (a8,))
    d.rectangle([x, y, x + spine - 1, y + h - 1], fill=SLAB_RED + (a8,))
    img.alpha_composite(layer)
    put(img, spr, (x + pad_x + 2, y + pad_y - 2), alpha)
    return (w, h)


def category_ribbon(img, xy, label: str, fkey: str = "cond-bold", size: int = 21,
                    track: float = 2.6, alpha: float = 1.0,
                    pad_x: int = 16, pad_y: int = 6) -> tuple[int, int]:
    """Red ribbon with tracked reversed-out caps — the 'CATEGORY · YEAR' strip."""
    if alpha <= 0.004:
        return (0, 0)
    spr = text_sprite(label, fkey, size, (255, 255, 255), track)
    w = spr.width + pad_x * 2
    h = spr.height + pad_y * 2 - 3
    x, y = int(xy[0]), int(xy[1])
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(layer).rectangle([x, y, x + w - 1, y + h - 1],
                                    fill=RIBBON + (int(255 * alpha),))
    img.alpha_composite(layer)
    put(img, spr, (x + pad_x, y + pad_y - 2), alpha)
    return (w, h)


def register_item(img, right_x: float, top_y: float, label: str, value: str,
                  unit: str = "", alpha: float = 1.0, label_size: int = 17,
                  value_size: int = 34) -> tuple[float, float]:
    """One readout of the top-right register: bold mono caps over a heavy figure.

    The reference sets the caps small; at 1080p that reads as dust, so the label
    is a size up and semibold, with hair-spaced tracking kept intact.
    """
    if alpha <= 0.004:
        return (0, 0)
    text(img, label, (right_x, top_y), "mono-med", label_size, REG_LABEL, 2.8, alpha,
         anchor="rt")
    vs = text_sprite(value, "cond-bold", value_size, INK, 0.4)
    uw, us = 0, None
    if unit:
        us = text_sprite(unit, "cond-bold", 18, INK, 0.6)
        uw = 4
    total = vs.width + (us.width + uw if us else 0)
    x, y = int(right_x - total), int(top_y + 47)
    put(img, vs, (x, y), alpha)
    if us:
        put(img, us, (x + vs.width + uw, y + vs.height - us.height - 2), alpha)
    return (total, 47 + vs.height)
