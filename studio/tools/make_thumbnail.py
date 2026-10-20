#!/usr/bin/env python3
"""
Vellum Logs — Sleepy Thumbnail Engine
-------------------------------------
Renders 1280x720 YouTube thumbnails in the "sleepy history" visual language:
warm hazy art + heavy soft-shadow slab type + optional 432 Hz pill.

Usage:
    python3 make_thumbnail.py <config.json>

Config schema (all keys optional unless stated):
{
  "background": "art/bg-01-constantinople.png",   # required
  "output":     "out/ep01.png",                    # required
  "blocks": [                                      # required, drawn top -> bottom
      {"text": "100 SLEEPY FACTS", "size": 132, "y": 0.055, "weight": 900,
       "color": "#ffffff", "stroke": 9, "align": "center", "tracking": 0.9},
      {"text": "ABOUT THE", "size": 62, "y": 0.545, "weight": 700, "align": "center"},
      {"text": "FALL OF\\nCONSTANTINOPLE", "size": 118, "y": 0.63, "weight": 900,
       "align": "center", "line_gap": 1.06}
  ],
  "pill":  {"text": "432 Hz", "y": 0.285, "align": "center", "icon": "wave"},
  "brand": {"text": "VELLUM LOGS", "y": 0.925, "align": "right"},
  "warmth": 0.22, "grain": 7, "vignette": 0.55, "blur": 0.6
}
"""
import json
import math
import os
import random
import sys

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

W, H = 1280, 720
HERE = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(HERE, "..", "fonts")

FONTS = {
    "black": "RobotoSlab-900.ttf",
    "bold": "RobotoSlab-700.ttf",
    "sans": "Inter-400.ttf",
    "sans600": "Inter-600.ttf",
    "sans700": "Inter-700.ttf",
}


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def font(name, size):
    return ImageFont.truetype(os.path.join(FONT_DIR, FONTS[name]), size)


def text_width(draw, txt, fnt, tracking=0.0):
    if not tracking:
        return draw.textbbox((0, 0), txt, font=fnt)[2]
    total = 0
    for ch in txt:
        total += draw.textlength(ch, font=fnt) + tracking * fnt.size
    return total - tracking * fnt.size


def draw_tracked(draw, xy, txt, fnt, fill, tracking=0.0, stroke=0, stroke_fill=None):
    x, y = xy
    if not tracking:
        draw.text((x, y), txt, font=fnt, fill=fill, stroke_width=stroke,
                  stroke_fill=stroke_fill)
        return
    for ch in txt:
        draw.text((x, y), ch, font=fnt, fill=fill, stroke_width=stroke,
                  stroke_fill=stroke_fill)
        x += draw.textlength(ch, font=fnt) + tracking * fnt.size


def fit_size(draw, txt, font_name, target_w, start, tracking=0.0, min_size=20):
    size = start
    while size > min_size:
        f = font(font_name, size)
        if text_width(draw, txt, f, tracking) <= target_w:
            return f
        size -= 2
    return font(font_name, min_size)


# --------------------------------------------------------------------------- #
# background treatment
# --------------------------------------------------------------------------- #
def treat_background(img, warmth=0.22, blur=0.6, vignette=0.55):
    img = img.convert("RGB")

    # contain + cover crop
    ratio = max(W / img.width, H / img.height)
    img = img.resize((int(img.width * ratio) + 1, int(img.height * ratio) + 1),
                     Image.LANCZOS)
    left = (img.width - W) // 2
    top = int((img.height - H) * 0.42)
    img = img.crop((left, top, left + W, top + H))

    if blur:
        img = img.filter(ImageFilter.GaussianBlur(blur))

    # warm, low-contrast grade
    img = ImageEnhance.Color(img).enhance(0.86)
    img = ImageEnhance.Contrast(img).enhance(0.90)
    img = ImageEnhance.Brightness(img).enhance(1.00)

    warm = Image.new("RGB", (W, H), (255, 176, 92))
    img = Image.blend(img, Image.composite(warm, img, Image.new("L", (W, H), 60)), warmth)

    # additive glow from the bottom (firelight / lamp feel)
    glow = Image.new("L", (W, H), 0)
    gd = ImageDraw.Draw(glow)
    gd.ellipse([-W * 0.35, H * 0.45, W * 1.35, H * 1.65], fill=90)
    glow = glow.filter(ImageFilter.GaussianBlur(120))
    warm_layer = Image.new("RGB", (W, H), (255, 168, 96))
    img = Image.composite(warm_layer, img, glow.point(lambda v: int(v * 0.35)))

    # vignette (edges)
    mask = Image.new("L", (W, H), 0)
    md = ImageDraw.Draw(mask)
    md.rectangle([0, 0, W, H], fill=255)
    md.ellipse([-W * 0.18, -H * 0.30, W * 1.18, H * 1.30], fill=0)
    mask = mask.filter(ImageFilter.GaussianBlur(160))
    dark = Image.new("RGB", (W, H), (18, 12, 8))
    img = Image.composite(dark, img, mask.point(lambda v: int(v * vignette)))

    # top & bottom scrims so white type always reads
    scrim = Image.new("L", (W, H), 0)
    sd = ImageDraw.Draw(scrim)
    for i in range(int(H * 0.30)):
        v = int(118 * (1 - i / (H * 0.30)) ** 1.9)
        sd.line([(0, i), (W, i)], fill=v)
    for i in range(int(H * 0.38)):
        y = H - 1 - i
        v = int(165 * (1 - i / (H * 0.38)) ** 1.8)
        sd.line([(0, y), (W, y)], fill=v)
    scrim = scrim.filter(ImageFilter.GaussianBlur(30))
    img = Image.composite(Image.new("RGB", (W, H), (16, 10, 7)), img,
                          scrim.point(lambda v: int(v * 0.80)))
    return img


def add_grain(img, amount=7, seed=4):
    rnd = random.Random(seed)
    noise = Image.effect_noise((W, H), 26).convert("L")
    noise = noise.point(lambda v: 128 + (v - 128) * amount / 26)
    return Image.blend(img, Image.merge("RGB", (noise, noise, noise)), 0.045)


# --------------------------------------------------------------------------- #
# decorations
# --------------------------------------------------------------------------- #
def draw_moon(draw, cx, cy, r, color=(255, 236, 199)):
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color)
    cut = r * 1.02
    draw.ellipse([cx - r * 0.72 - cut, cy - r * 1.18, cx - r * 0.72 + cut,
                  cy + r * 1.18], fill=(0, 0, 0, 0))


def draw_wave(draw, x, y, w, h, color="#1b1408", bars=13):
    step = w / bars
    for i in range(bars):
        t = i / (bars - 1)
        amp = abs(math.sin(t * math.pi * 2.6)) * 0.72 + 0.18
        bh = h * amp
        bx = x + i * step
        draw.rounded_rectangle([bx, y + (h - bh) / 2, bx + step * 0.52,
                                y + (h + bh) / 2],
                               radius=step * 0.26, fill=color)


def pill(draw, img, text, cy, size=40, align="center", icon="wave"):
    f = font("sans700", size)
    pad_x, pad_y = int(size * 0.62), int(size * 0.34)
    icon_w = int(size * 1.25) if icon else 0
    gap = int(size * 0.30) if icon else 0
    tw = draw.textlength(text, font=f)
    pw = int(tw + pad_x * 2 + icon_w + gap)
    ph = int(size + pad_y * 2)
    if align == "center":
        x0 = (W - pw) // 2
    elif align == "right":
        x0 = W - pw - 60
    else:
        x0 = 60
    y0 = int(cy - ph / 2)

    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.rounded_rectangle([x0, y0 + 6, x0 + pw, y0 + ph + 6], radius=ph // 2,
                         fill=(0, 0, 0, 150))
    shadow = shadow.filter(ImageFilter.GaussianBlur(14))
    img.alpha_composite(shadow)

    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    ld.rounded_rectangle([x0, y0, x0 + pw, y0 + ph], radius=ph // 2,
                         fill=(250, 246, 236, 255),
                         outline=(30, 20, 10, 90), width=2)
    img.alpha_composite(layer)

    if icon == "wave":
        draw_wave(draw, x0 + pad_x, y0 + ph * 0.26, icon_w, ph * 0.48)
    draw.text((x0 + pad_x + icon_w + gap, y0 + pad_y - size * 0.08), text,
              font=f, fill=(27, 20, 8))
    return ph


# --------------------------------------------------------------------------- #
# text rendering with soft shadow + stroke
# --------------------------------------------------------------------------- #
def render_block(img, draw, b):
    raw = b["text"]
    lines = raw.split("\n")
    size = b.get("size", 96)
    weight = b.get("weight", 900)
    fname = "black" if weight >= 800 else "bold" if weight >= 700 else "sans700"
    tracking = b.get("tracking", 0)
    color = hex_rgb(b.get("color", "#ffffff"))
    stroke = int(b.get("stroke", 0))
    stroke_col = hex_rgb(b.get("stroke_color", "#1a1208"))
    align = b.get("align", "center")
    anchor_x = b.get("x", None)
    max_w = b.get("max_width", 0.90) * W
    line_gap = b.get("line_gap", 1.08)
    shadow = b.get("shadow", 0.72)

    # shrink to fit the widest line
    probe = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    widest = max(lines, key=lambda l: text_width(probe, l, font(fname, size), tracking))
    while text_width(probe, widest, font(fname, size), tracking) > max_w and size > 18:
        size -= 2
    f = font(fname, size)
    lh = int(size * line_gap)
    total_h = lh * len(lines)
    y0 = int(b["y"] * H)

    # ---- soft shadow layer (blurred) ----
    def line_x(lw):
        if anchor_x is not None:
            return anchor_x * W if align != "right" else W - anchor_x * W - lw
        if align == "center":
            return (W - lw) / 2
        if align == "right":
            return W - lw - 60
        return 60

    if shadow:
        sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        sd = ImageDraw.Draw(sh)
        for i, line in enumerate(lines):
            lw = text_width(sd, line, f, tracking)
            x = line_x(lw)
            sd.text((x, y0 + i * lh), line, font=f,
                    fill=(0, 0, 0, int(165 * shadow)), stroke_width=stroke + 3,
                    stroke_fill=(0, 0, 0, int(120 * shadow)))
        sh = sh.filter(ImageFilter.GaussianBlur(9))
        img.alpha_composite(sh)

    # ---- sharp text ----
    for i, line in enumerate(lines):
        lw = text_width(draw, line, f, tracking)
        x = line_x(lw)
        draw_tracked(draw, (x, y0 + i * lh), line, f, color, tracking,
                     stroke, stroke_col)
    return total_h


# --------------------------------------------------------------------------- #
# main render
# --------------------------------------------------------------------------- #
def render(cfg):
    root = os.path.abspath(os.path.join(HERE, ".."))
    bg_path = cfg["background"] if os.path.isabs(cfg["background"]) else os.path.join(root, cfg["background"])
    img = Image.open(bg_path)
    img = treat_background(img, cfg.get("warmth", 0.22),
                           cfg.get("blur", 0.6), cfg.get("vignette", 0.55)
                           ).convert("RGBA")
    draw = ImageDraw.Draw(img)

    if cfg.get("pill"):
        p = cfg["pill"]
        pill(draw, img, p["text"], p["y"] * H, size=p.get("size", 40),
             align=p.get("align", "center"), icon=p.get("icon", "wave"))

    for b in cfg.get("blocks", []):
        render_block(img, draw, b)

    if cfg.get("brand"):
        br = cfg["brand"]
        txt = br.get("text", "VELLUM LOGS")
        f = font("sans600", br.get("size", 22))
        tracking = 0.14
        tw = text_width(draw, txt, f, tracking)
        size = br.get("size", 22)
        gap = size * 1.15
        if br.get("align", "right") == "right":
            x_txt = W - 46 - tw
            x_moon = x_txt - gap
        else:
            x_moon = 46 + size * 0.55
            x_txt = x_moon + gap
        y = int(br["y"] * H)
        cy = y + size * 0.62
        r = size * 0.52

        # soft shadow under moon + wordmark
        sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        sd = ImageDraw.Draw(sh)
        sd.ellipse([x_moon - r, cy - r + 2, x_moon + r, cy + r + 2], fill=(0, 0, 0, 170))
        sd.text((x_txt, y), txt, font=f, fill=(0, 0, 0, 170),
                stroke_width=3, stroke_fill=(0, 0, 0, 150))
        sh = sh.filter(ImageFilter.GaussianBlur(7))
        img.alpha_composite(sh)

        # sample the local background tone so the crescent "cuts" into the scene
        patch = img.crop((int(x_moon - r * 2), int(cy - r * 2),
                          int(x_moon + r * 2), int(cy + r * 2))).convert("RGB")
        patch = patch.resize((1, 1), Image.LANCZOS)
        cut = patch.getpixel((0, 0))
        d2 = ImageDraw.Draw(img)
        d2.ellipse([x_moon - r, cy - r, x_moon + r, cy + r], fill=(255, 228, 172, 255))
        d2.ellipse([x_moon - r + r * 0.55, cy - r * 1.25,
                    x_moon + r * 2.1, cy + r * 1.25], fill=cut + (255,))

        draw.text((x_txt, y), txt, font=f, fill=(255, 242, 219),
                  stroke_width=2, stroke_fill=(26, 17, 9))

    out = add_grain(img.convert("RGB"), cfg.get("grain", 7))
    out_path = cfg["output"]
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    out.save(out_path, quality=95)
    print("✓", out_path, out.size)
    return out_path


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    with open(sys.argv[1], encoding="utf-8") as fh:
        render(json.load(fh))
