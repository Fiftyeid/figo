# -*- coding: utf-8 -*-
"""Design system + drawing helpers (Arabic text via Pillow+raqm)."""
import os, math, functools
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
ASSETS = os.path.join(ROOT, "assets")
BUILD = os.path.join(ROOT, "build")
FONTS = os.path.join(ASSETS, "fonts")

W, H = 1920, 1080
FPS = 25

# ---------------------------------------------------------------- palette
BG0 = (9, 13, 28)
BG1 = (20, 28, 54)
GOLD = (255, 201, 60)
GOLD_D = (214, 150, 20)
TEAL = (46, 196, 182)
CORAL = (255, 107, 87)
WHITE = (245, 247, 250)
MUTED = (154, 164, 191)
INK = (12, 16, 30)

ERA = {
    "مصري قديم": (233, 185, 73),
    "قبطي": (93, 173, 226),
    "يوناني": (186, 160, 255),
    "روماني": (186, 160, 255),
    "عربي": (52, 195, 143),
    "عثماني": (255, 127, 80),
    "حديث": (255, 201, 60),
}

FONT_FILES = {
    "display": "Lalezar_400Regular.ttf",
    "black": "Cairo_900Black.ttf",
    "bold": "Cairo_700Bold.ttf",
    "semi": "Cairo_600SemiBold.ttf",
    "taj": "Tajawal_700Bold.ttf",
    "tajm": "Tajawal_500Medium.ttf",
    "amiri": "Amiri_700Bold.ttf",
}


@functools.lru_cache(maxsize=256)
def font(kind, size):
    return ImageFont.truetype(os.path.join(FONTS, FONT_FILES[kind]), int(size),
                              layout_engine=ImageFont.Layout.RAQM)


def is_rtl(s):
    return any("\u0600" <= ch <= "\u06ff" or "\u0750" <= ch <= "\u077f" for ch in s)


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


# ---------------------------------------------------------------- text
def text_image(s, kind="bold", size=60, fill=WHITE, stroke=0, stroke_fill=INK,
               shadow=0, shadow_color=(0, 0, 0, 160), pad=None, direction=None):
    """Render a single line to a tight RGBA image (handles Arabic shaping/bidi)."""
    f = font(kind, size)
    direction = direction or ("rtl" if is_rtl(s) else "ltr")
    d0 = ImageDraw.Draw(Image.new("RGBA", (8, 8)))
    bbox = d0.textbbox((0, 0), s, font=f, stroke_width=stroke, direction=direction)
    pad = pad if pad is not None else int(size * 0.12) + stroke + shadow * 2
    w = bbox[2] - bbox[0] + 2 * pad
    h = bbox[3] - bbox[1] + 2 * pad
    img = Image.new("RGBA", (max(1, w), max(1, h)), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    org = (pad - bbox[0], pad - bbox[1])
    if shadow:
        sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ds = ImageDraw.Draw(sh)
        ds.text((org[0] + shadow * 0.6, org[1] + shadow), s, font=f, fill=shadow_color,
                stroke_width=stroke, stroke_fill=shadow_color, direction=direction)
        sh = sh.filter(ImageFilter.GaussianBlur(shadow))
        img = Image.alpha_composite(img, sh)
        d = ImageDraw.Draw(img)
    d.text(org, s, font=f, fill=fill, stroke_width=stroke, stroke_fill=stroke_fill, direction=direction)
    return img


def wrap_lines(s, kind, size, max_w):
    """Greedy word wrap for RTL/LTR text, returns list of lines."""
    words = s.split()
    lines, cur = [], ""
    f = font(kind, size)
    d0 = ImageDraw.Draw(Image.new("RGBA", (8, 8)))
    for w_ in words:
        t = (cur + " " + w_).strip()
        bb = d0.textbbox((0, 0), t, font=f, direction="rtl" if is_rtl(t) else "ltr")
        if bb[2] - bb[0] > max_w and cur:
            lines.append(cur)
            cur = w_
        else:
            cur = t
    if cur:
        lines.append(cur)
    return lines


def paragraph_image(s, kind="bold", size=48, fill=WHITE, max_w=1400, line_gap=0.25,
                    align="center", stroke=0, stroke_fill=INK, shadow=0):
    lines = wrap_lines(s, kind, size, max_w)
    ims = [text_image(l, kind, size, fill, stroke=stroke, stroke_fill=stroke_fill, shadow=shadow) for l in lines]
    lh = int(size * (1.0 + line_gap)) + int(size * 0.35)
    wmax = max(i.width for i in ims)
    out = Image.new("RGBA", (wmax, lh * (len(ims) - 1) + ims[-1].height), (0, 0, 0, 0))
    for k, im in enumerate(ims):
        if align == "center":
            x = (wmax - im.width) // 2
        elif align == "right":
            x = wmax - im.width
        else:
            x = 0
        out.alpha_composite(im, (x, k * lh))
    return out


# ---------------------------------------------------------------- shapes
def rounded_rect(size, radius, fill, outline=None, width=0):
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, size[0] - 1, size[1] - 1], radius=radius, fill=fill,
                        outline=outline, width=width)
    return img


def glow(img, radius=18, strength=1.0, color=None):
    """Return img with a soft glow behind it (same size + margin)."""
    m = radius * 2
    big = Image.new("RGBA", (img.width + 2 * m, img.height + 2 * m), (0, 0, 0, 0))
    a = img.split()[-1]
    if color is None:
        base = img
    else:
        base = Image.new("RGBA", img.size, color + (255,))
        base.putalpha(a)
    g = Image.new("RGBA", big.size, (0, 0, 0, 0))
    g.alpha_composite(base, (m, m))
    g = g.filter(ImageFilter.GaussianBlur(radius))
    if strength != 1.0:
        r, gg, b, aa = g.split()
        aa = aa.point(lambda v: min(255, int(v * strength)))
        g = Image.merge("RGBA", (r, gg, b, aa))
    g.alpha_composite(img, (m, m))
    return g


def chip(text, color, kind="black", size=64, fg=INK, padx=36, pady=10, radius=None, outline=None):
    t = text_image(text, kind, size, fg, pad=4)
    w, h = t.width + 2 * padx, t.height + 2 * pady
    r = radius if radius is not None else h // 2
    base = rounded_rect((w, h), r, color + (255,) if len(color) == 3 else color,
                        outline=outline, width=4 if outline else 0)
    base.alpha_composite(t, ((w - t.width) // 2, (h - t.height) // 2 - 2))
    return base


def arrow_left(length=90, thick=12, head=34, color=WHITE):
    """An arrow pointing LEFT (RTL reading order: from right to left)."""
    w, h = length, head * 2
    img = Image.new("RGBA", (w * 4, h * 4), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    s = 4
    cy = h * s / 2
    d.rectangle([head * s * 0.8, cy - thick * s / 2, w * s, cy + thick * s / 2], fill=color + (255,))
    d.polygon([(0, cy), (head * s * 1.1, cy - head * s * 0.95), (head * s * 1.1, cy + head * s * 0.95)],
              fill=color + (255,))
    return img.resize((w, h), Image.LANCZOS)


def with_alpha(img, a):
    """Multiply alpha of RGBA image by a in [0,1]."""
    if a >= 0.999:
        return img
    if a <= 0.001:
        return None
    r, g, b, al = img.split()
    al = al.point(lambda v, a=a: int(v * a))
    return Image.merge("RGBA", (r, g, b, al))


def scaled(img, s):
    if abs(s - 1.0) < 1e-3:
        return img
    w, h = max(1, int(img.width * s)), max(1, int(img.height * s))
    return img.resize((w, h), Image.BILINEAR)


def paste_center(base, layer, cx, cy, alpha=1.0, scale=1.0):
    if layer is None:
        return
    lay = scaled(layer, scale)
    lay = with_alpha(lay, alpha)
    if lay is None:
        return
    x = int(round(cx - lay.width / 2))
    y = int(round(cy - lay.height / 2))
    _safe_composite(base, lay, x, y)


def paste_at(base, layer, x, y, alpha=1.0):
    if layer is None:
        return
    lay = with_alpha(layer, alpha)
    if lay is None:
        return
    _safe_composite(base, lay, int(round(x)), int(round(y)))


def _safe_composite(base, lay, x, y):
    bx0, by0 = max(0, x), max(0, y)
    bx1, by1 = min(base.width, x + lay.width), min(base.height, y + lay.height)
    if bx1 <= bx0 or by1 <= by0:
        return
    crop = lay.crop((bx0 - x, by0 - y, bx1 - x, by1 - y))
    base.alpha_composite(crop, (bx0, by0))


# ---------------------------------------------------------------- backgrounds
def gradient_bg(size=(W, H), top=BG1, bottom=BG0, radial=True, seed=0):
    w, h = size
    y = np.linspace(0, 1, h)[:, None]
    x = np.linspace(0, 1, w)[None, :]
    t = np.clip(y, 0, 1)
    if radial:
        r = np.sqrt((x - 0.5) ** 2 * 1.4 + (y - 0.42) ** 2)
        t = np.clip(r * 1.25, 0, 1)
    c0 = np.array(top, np.float32)
    c1 = np.array(bottom, np.float32)
    img = c0[None, None, :] * (1 - t[..., None]) + c1[None, None, :] * t[..., None]
    rng = np.random.default_rng(seed)
    img += rng.normal(0, 1.6, img.shape)  # anti-banding dither
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), "RGB")


def starfield(size=(W, H), n=380, seed=1, color=(210, 220, 255)):
    rng = np.random.default_rng(seed)
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for _ in range(n):
        x, y = rng.uniform(0, size[0]), rng.uniform(0, size[1])
        r = rng.choice([0.8, 1.0, 1.2, 1.6, 2.2], p=[0.35, 0.3, 0.2, 0.1, 0.05])
        a = int(rng.uniform(60, 220))
        d.ellipse([x - r, y - r, x + r, y + r], fill=color + (a,))
    return img.filter(ImageFilter.GaussianBlur(0.6))


def vignette(size=(W, H), strength=0.55):
    w, h = size
    y = np.linspace(-1, 1, h)[:, None]
    x = np.linspace(-1, 1, w)[None, :]
    r = np.sqrt(x ** 2 * 0.9 + y ** 2 * 1.1)
    a = np.clip((r - 0.55) / 0.9, 0, 1) ** 1.6 * strength
    arr = np.zeros((h, w, 4), np.uint8)
    arr[..., 3] = (a * 255).astype(np.uint8)
    return Image.fromarray(arr, "RGBA")


def grade_image(img, warmth=0.0, contrast=1.06, sat=1.05, darken=0.0):
    a = np.asarray(img.convert("RGB")).astype(np.float32) / 255.0
    lum = (a * np.array([0.299, 0.587, 0.114], np.float32)).sum(-1, keepdims=True)
    a = lum + (a - lum) * sat
    a = (a - 0.5) * contrast + 0.5
    if warmth:
        a[..., 0] *= 1 + warmth * 0.06
        a[..., 2] *= 1 - warmth * 0.06
    if darken:
        a *= (1 - darken)
    return Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8), "RGB")


def ken_burns_source(path, zoom_max=1.14, darken=0.0, blur=0):
    """Load image, cover-crop to 16:9 and pre-scale to (W,H)*zoom_max."""
    im = Image.open(path).convert("RGB")
    tw, th = int(W * zoom_max), int(H * zoom_max)
    r = max(tw / im.width, th / im.height)
    im = im.resize((int(im.width * r + 0.5), int(im.height * r + 0.5)), Image.LANCZOS)
    x0 = (im.width - tw) // 2
    y0 = (im.height - th) // 2
    im = im.crop((x0, y0, x0 + tw, y0 + th))
    im = grade_image(im, warmth=0.3, darken=darken)
    if blur:
        im = im.filter(ImageFilter.GaussianBlur(blur))
    return im


def view_transform(src, cx, cy, zoom, out=(W, H)):
    """Crop a view (center cx,cy in src px; zoom relative to out size) -> out."""
    ow, oh = out
    sw, sh = ow / zoom, oh / zoom
    x0, y0 = cx - sw / 2, cy - sh / 2
    a = sw / ow
    e = sh / oh
    return src.transform(out, Image.AFFINE, (a, 0, x0, 0, e, y0), resample=Image.BILINEAR)
