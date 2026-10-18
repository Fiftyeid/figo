# -*- coding: utf-8 -*-
"""Design system + drawing helpers for "World's Fastest Military Helicopter Explained"."""
import os, math, functools
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
ASSETS = os.path.join(ROOT, "assets")
BUILD = os.path.join(ROOT, "build")
FONTS = os.path.join(ASSETS, "fonts")
IMAGES = os.path.join(ASSETS, "images")

W, H = 1920, 1080
FPS = 25

# ---------------------------------------------------------------- palette (dark military HUD)
BG0 = (7, 10, 16)
BG1 = (16, 23, 34)
GRID = (40, 62, 82)
AMBER = (255, 176, 32)
RED = (255, 70, 58)
CYAN = (70, 200, 255)
GREEN = (84, 222, 140)
WHITE = (240, 244, 248)
MUTED = (140, 152, 168)
INK = (6, 9, 14)

FONT_FILES = {
    "title": "Anton-Regular.ttf",
    "cx": "BarlowCondensed-ExtraBold.ttf",
    "cb": "BarlowCondensed-Bold.ttf",
    "cs": "BarlowCondensed-SemiBold.ttf",
    "body": "Barlow-SemiBold.ttf",
    "bodym": "Barlow-Medium.ttf",
    "mono": "ShareTechMono-Regular.ttf",
}


@functools.lru_cache(maxsize=256)
def font(kind, size):
    return ImageFont.truetype(os.path.join(FONTS, FONT_FILES[kind]), int(size),
                              layout_engine=ImageFont.Layout.BASIC)


# ---------------------------------------------------------------- easing
def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def ease_out_cubic(x):
    x = clamp(x)
    return 1 - (1 - x) ** 3


def ease_in_out(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)


def ease_out_back(x, s=1.70158):
    x = clamp(x)
    x -= 1
    return x * x * ((s + 1) * x + s) + 1


def lerp(a, b, t):
    return a + (b - a) * t


def appear(t, t0, dur=0.35):
    """(alpha, progress) of an element that pops in at t0."""
    p = clamp((t - t0) / dur)
    return ease_out_cubic(p), p


# ---------------------------------------------------------------- text
def text_image(s, kind="cb", size=60, fill=WHITE, stroke=0, stroke_fill=INK, shadow=0,
               shadow_color=(0, 0, 0, 170), tracking=0, pad=None):
    """Render a single line to a tight RGBA image. tracking = extra px between letters."""
    f = font(kind, size)
    d0 = ImageDraw.Draw(Image.new("RGBA", (8, 8)))
    if tracking:
        widths = [d0.textlength(ch, font=f) + tracking for ch in s]
        tw = int(sum(widths) - tracking)
    else:
        tw = int(d0.textlength(s, font=f))
    asc, desc = f.getmetrics()
    pad = pad if pad is not None else int(size * 0.10) + stroke + shadow * 2
    img = Image.new("RGBA", (max(1, tw + 2 * pad), asc + desc + 2 * pad), (0, 0, 0, 0))

    def draw_on(im, col, dx=0, dy=0, sw=0, sf=None):
        d = ImageDraw.Draw(im)
        if tracking:
            x = pad + dx
            for ch, wch in zip(s, widths):
                d.text((x, pad + dy), ch, font=f, fill=col, stroke_width=sw, stroke_fill=sf)
                x += wch
        else:
            d.text((pad + dx, pad + dy), s, font=f, fill=col, stroke_width=sw, stroke_fill=sf)

    if shadow:
        sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
        draw_on(sh, shadow_color, shadow * 0.5, shadow, stroke, shadow_color)
        img = Image.alpha_composite(img, sh.filter(ImageFilter.GaussianBlur(shadow)))
    draw_on(img, fill, 0, 0, stroke, stroke_fill)
    return img


def wrap_lines(s, kind, size, max_w):
    f = font(kind, size)
    d0 = ImageDraw.Draw(Image.new("RGBA", (8, 8)))
    lines, cur = [], ""
    for w_ in s.split():
        t = (cur + " " + w_).strip()
        if d0.textlength(t, font=f) > max_w and cur:
            lines.append(cur)
            cur = w_
        else:
            cur = t
    if cur:
        lines.append(cur)
    return lines


def paragraph_image(s, kind="body", size=44, fill=WHITE, max_w=1200, line_gap=1.25, align="left", shadow=0):
    lines = wrap_lines(s, kind, size, max_w)
    ims = [text_image(l, kind, size, fill, shadow=shadow) for l in lines]
    lh = int(size * line_gap)
    wmax = max(i.width for i in ims)
    out = Image.new("RGBA", (wmax, lh * (len(ims) - 1) + ims[-1].height), (0, 0, 0, 0))
    for k, im in enumerate(ims):
        x = (wmax - im.width) // 2 if align == "center" else (wmax - im.width if align == "right" else 0)
        out.alpha_composite(im, (x, k * lh))
    return out


# ---------------------------------------------------------------- shapes
def rounded_rect(size, radius, fill, outline=None, width=0):
    img = Image.new("RGBA", (max(1, int(size[0])), max(1, int(size[1]))), (0, 0, 0, 0))
    ImageDraw.Draw(img).rounded_rectangle([0, 0, img.width - 1, img.height - 1], radius=radius, fill=fill,
                                          outline=outline, width=width)
    return img


def glow(img, radius=16, strength=1.0, color=None):
    m = radius * 2
    big = Image.new("RGBA", (img.width + 2 * m, img.height + 2 * m), (0, 0, 0, 0))
    base = img if color is None else Image.new("RGBA", img.size, color + (255,))
    if color is not None:
        base.putalpha(img.getchannel("A"))
    big.alpha_composite(base, (m, m))
    g = big.filter(ImageFilter.GaussianBlur(radius))
    if strength != 1.0:
        a = g.getchannel("A").point(lambda v: min(255, int(v * strength)))
        g.putalpha(a)
    g.alpha_composite(img, (m, m))
    return g


def with_alpha(img, a):
    if a >= 0.999:
        return img
    im = img.copy()
    im.putalpha(im.getchannel("A").point(lambda v: int(v * a)))
    return im


def paste_at(base, layer, x, y, alpha=1.0):
    if alpha <= 0.002:
        return
    base.alpha_composite(with_alpha(layer, alpha), (int(round(x)), int(round(y))))


def paste_center(base, layer, cx, cy, alpha=1.0, scale=1.0):
    if scale != 1.0:
        layer = layer.resize((max(1, int(layer.width * scale)), max(1, int(layer.height * scale))), Image.BILINEAR)
    paste_at(base, layer, cx - layer.width / 2, cy - layer.height / 2, alpha)


def chip(text, color, kind="cb", size=40, fg=INK, padx=22, pady=6, tracking=2):
    t = text_image(text, kind, size, fg, tracking=tracking, pad=2)
    w, h = t.width + 2 * padx, t.height + 2 * pady
    base = rounded_rect((w, h), 6, color + (255,))
    base.alpha_composite(t, ((w - t.width) // 2, (h - t.height) // 2))
    return base


def hud_corners(size, color=(255, 255, 255), alpha=150, L=46, width=3, inset=40):
    w, h = size
    im = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c = color + (alpha,)
    for (x, y, sx, sy) in ((inset, inset, 1, 1), (w - inset, inset, -1, 1), (inset, h - inset, 1, -1),
                           (w - inset, h - inset, -1, -1)):
        d.line([(x, y), (x + sx * L, y)], fill=c, width=width)
        d.line([(x, y), (x, y + sy * L)], fill=c, width=width)
    return im


def grid_bg(size=(W, H), step=60, seed=0):
    """Dark blueprint background with a fine grid and a soft radial light."""
    w, h = size
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    r = np.sqrt(((xx - w * 0.5) / w) ** 2 + ((yy - h * 0.45) / h) ** 2)
    k = np.clip(1 - r * 1.25, 0, 1)[..., None]
    base = np.array(BG0, np.float32) * (1 - k) + np.array(BG1, np.float32) * k
    im = Image.fromarray(base.astype(np.uint8), "RGB").convert("RGBA")
    d = ImageDraw.Draw(im)
    for x in range(0, w, step):
        d.line([(x, 0), (x, h)], fill=GRID + (38 if x % (step * 4) else 70,), width=1)
    for y in range(0, h, step):
        d.line([(0, y), (w, y)], fill=GRID + (38 if y % (step * 4) else 70,), width=1)
    return im


# ---------------------------------------------------------------- photo look
def grade_image(img, contrast=1.08, sat=1.06, warmth=0.0, teal=0.0, darken=0.0):
    a = np.asarray(img.convert("RGB")).astype(np.float32) / 255.0
    lum = (a * np.array([0.299, 0.587, 0.114], np.float32)).sum(-1, keepdims=True)
    a = lum + (a - lum) * sat
    a = (a - 0.5) * contrast + 0.5
    if warmth:
        a[..., 0] *= 1 + warmth * 0.06
        a[..., 2] *= 1 - warmth * 0.06
    if teal:   # teal shadows / warm highlights
        sh = np.clip(1 - lum * 1.6, 0, 1)
        a[..., 0] -= teal * 0.05 * sh[..., 0]
        a[..., 2] += teal * 0.06 * sh[..., 0]
    if darken:
        a *= (1 - darken)
    return Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8), "RGB")


@functools.lru_cache(maxsize=4)
def vignette(size=(W, H), strength=0.5):
    w, h = size
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    r = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2)
    a = np.clip((r - 0.55) / 0.85, 0, 1) ** 1.6 * strength
    im = Image.new("RGBA", size, (0, 0, 0, 0))
    im.putalpha(Image.fromarray((a * 255).astype(np.uint8), "L"))
    return im


@functools.lru_cache(maxsize=1)
def grain_bank(n=6, size=(W // 2, H // 2), amount=10, seed=5):
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(n):
        g = rng.normal(0, amount, (size[1], size[0])).astype(np.float32)
        im = Image.fromarray(np.clip(g + 128, 0, 255).astype(np.uint8), "L").resize((W, H), Image.BILINEAR)
        out.append(im)
    return out


def add_grain(rgb_img, t, strength=0.06):
    return rgb_img


@functools.lru_cache(maxsize=16)
def load_photo(key, zoom_max=1.18, contrast=1.08, sat=1.06, warmth=0.0, teal=0.25, darken=0.0, blur=0):
    im = Image.open(os.path.join(IMAGES, key + ".jpg")).convert("RGB")
    tw, th = int(W * zoom_max), int(H * zoom_max)
    r = max(tw / im.width, th / im.height)
    im = im.resize((int(im.width * r + 0.5), int(im.height * r + 0.5)), Image.LANCZOS)
    x0, y0 = (im.width - tw) // 2, (im.height - th) // 2
    im = im.crop((x0, y0, x0 + tw, y0 + th))
    im = im.filter(ImageFilter.UnsharpMask(radius=2, percent=40, threshold=2))
    im = grade_image(im, contrast, sat, warmth, teal, darken)
    if blur:
        im = im.filter(ImageFilter.GaussianBlur(blur))
    return im


def view(src, cx, cy, zoom, out=(W, H)):
    """Crop a view centred at (cx, cy) (fractions of src) at zoom (1 = src scaled to fill out)."""
    ow, oh = out
    base = max(ow / src.width, oh / src.height)
    sw, sh = ow / (base * zoom), oh / (base * zoom)
    x0 = clamp(cx * src.width - sw / 2, 0, src.width - sw)
    y0 = clamp(cy * src.height - sh / 2, 0, src.height - sh)
    return src.transform(out, Image.AFFINE, (sw / ow, 0, x0, 0, sh / oh, y0), resample=Image.BILINEAR)


def fmt_int(v):
    return f"{int(round(v)):,}"
