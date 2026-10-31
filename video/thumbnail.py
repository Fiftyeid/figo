#!/usr/bin/env python3
"""YouTube thumbnail generator (1280x720).

    python3 video/thumbnail.py            # writes both variants
    python3 video/thumbnail.py --light    # just the studio version
    python3 video/thumbnail.py --dark     # just the cinematic version

Design rules it follows (thumbnails are read at 320 px wide):
  * one hook, three words max per block  -> "32 KG" / "VS" / "30 KG"
  * both faces read left-to-right as a comparison
  * headline strip at the bottom carries the actual topic
  * same palette + flags as the film, so the series stays recognisable
"""
from __future__ import annotations

import argparse
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from engine import config as C          # noqa: E402
from engine import pixels as P          # noqa: E402
from engine.content import META, SIDES  # noqa: E402

ROOT = os.path.dirname(HERE)
TW, TH = 1280, 720
US = SIDES["left"]["accent"]
CN = SIDES["right"]["accent"]


# ------------------------------------------------------------------ helpers
def fit_h(path, h):
    src = P.cutout(path)
    w = int(round(src.width * h / src.height / 2)) * 2
    return src.convert("RGBa").resize((w, max(8, h)), Image.LANCZOS).convert("RGBA")


def shadow_under(size, spread=18, opacity=70):
    w, h = size
    m = Image.new("L", (w + 80, 60), 0)
    ImageDraw.Draw(m).ellipse([40, 18, w + 40, 54], fill=opacity)
    return m.filter(ImageFilter.GaussianBlur(spread))


def grad_v(size, top, bottom):
    w, h = size
    ys = np.linspace(0, 1, h, dtype=np.float32)[:, None]
    t = np.array(top, dtype=np.float32)
    b = np.array(bottom, dtype=np.float32)
    arr = t + (b - t) * ys
    return Image.fromarray(np.repeat(arr[:, None, :], w, axis=1).astype(np.uint8), "RGB")


def radial(size, color, centre=(0.5, 0.45), radius=1.0, strength=1.0):
    w, h = size
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.sqrt(((xx / w) - centre[0]) ** 2 + ((yy / h) - centre[1]) ** 2) / radius
    a = np.clip(1 - d, 0, 1) ** 1.8 * strength
    layer = Image.new("RGB", size, color)
    return layer, Image.fromarray((a * 255).astype(np.uint8), "L")


def text(frame, xy, s, weight="bold", size=60, color=C.INK, tracking=0, anchor="lt",
         alpha=1.0):
    return P.draw_text(frame, xy, s, weight, size, color, tracking, anchor, alpha)


def tw(s, weight="bold", size=60, tracking=0):
    return P.text_img(s, weight, size, C.INK, tracking).width - 8


def hex_badge(size, fill, label, fg=C.PAPER, ring=None):
    ss = 3
    s = size * ss
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    pts = [(s * .5, s * .03), (s * .97, s * .27), (s * .97, s * .73),
           (s * .5, s * .97), (s * .03, s * .73), (s * .03, s * .27)]
    d.polygon(pts, fill=fill + (255,))
    if ring:
        d.line(pts + [pts[0]], fill=ring + (255,), width=int(s * 0.045), joint="curve")
    f = C.font("bold", int(s * 0.33))
    wtxt = d.textlength(label, font=f)
    d.text((s / 2 - wtxt / 2, s * 0.33), label, font=f, fill=fg + (255,))
    return im.resize((size, size), Image.LANCZOS)


def flag_round(size, country):
    return P.flag(size, country)


# ------------------------------------------------------------------ variants
def _figure(path, height):
    return fit_h(path, height)


def _place_figure(f, spr, cx, baseline, shadow_opacity=80, glow=None):
    if glow:
        layer = Image.new("RGBA", (spr.width + 90, spr.height + 90), (0, 0, 0, 0))
        sil = Image.new("L", layer.size, 0)
        sil.paste(spr.split()[3], (45, 45))
        sil = sil.filter(ImageFilter.GaussianBlur(26))
        col = Image.new("RGB", layer.size, glow)
        f.paste(col, (cx - spr.width // 2 - 45, baseline - spr.height - 45),
                sil.point(lambda v: int(v * 0.85)))
    sh = shadow_under(spr.size, spread=16, opacity=shadow_opacity)
    f.paste((12, 14, 18), (cx - spr.width // 2 - 40, baseline - 6), sh)
    f.paste(spr.convert("RGB"), (cx - spr.width // 2, baseline - spr.height),
            spr.split()[3])


def _number_block(f, value, unit, accent, x, y, size=150, anchor="lt", label=None,
                  label_color=(70, 78, 88), label_right=None):
    text(f, (x, y), value, "bold", size, accent, tracking=-3, anchor=anchor)
    w = tw(value, "bold", size, -3)
    x0 = x if anchor == "lt" else x - w
    text(f, (x0 + w + 10, y + size * 0.52), unit, "bold", int(size * 0.34), accent,
         tracking=2, anchor="lt")
    if label:
        if label_right is not None:
            text(f, (label_right, y + size + 8), label, "bold", 24, label_color,
                 tracking=5, anchor="rt")
        else:
            text(f, (x, y + size + 8), label, "bold", 24, label_color, tracking=5,
                 anchor=anchor)


def _headline(f, title, sub, right_top, right_bottom, bar=(18, 21, 26), sub_col=(150, 158, 168),
              title_size=60):
    bar_h = 142
    ImageDraw.Draw(f, "RGBA").rectangle([0, TH - bar_h, TW, TH], fill=bar + (247,))
    text(f, (56, TH - bar_h + 18), title, "bold", title_size, C.PAPER, tracking=5)
    text(f, (56, TH - bar_h + 88), sub, "bold", 28, sub_col, tracking=7)
    text(f, (TW - 56, TH - bar_h + 24), right_top, "bold", 25, C.PAPER, tracking=4,
         anchor="rt")
    text(f, (TW - 56, TH - bar_h + 62), right_bottom, "reg", 18, sub_col, tracking=4,
         anchor="rt")
    ImageDraw.Draw(f, "RGBA").rectangle([0, TH - 7, TW // 2, TH], fill=US + (255,))
    ImageDraw.Draw(f, "RGBA").rectangle([TW // 2, TH - 7, TW, TH], fill=CN + (255,))


def build_light():
    """Studio poster: numbers on the outer edges, two figures, clear headline."""
    f = grad_v((TW, TH), (250, 251, 253), (205, 210, 217)).convert("RGB")
    d = ImageDraw.Draw(f, "RGBA")
    # soft national washes hugging each edge (no hard geometry)
    for colour, x0, x1 in ((US, 0, TW * 0.46), (CN, TW, TW * 0.54)):
        for i in range(26):
            a = int(12.0 * (26 - i) / 26)
            xx0 = x0 + (i / 26) * (x1 - x0)
            xx1 = x0 + ((i + 1) / 26) * (x1 - x0)
            d.rectangle([min(xx0, xx1), 0, max(xx0, xx1), TH], fill=colour + (a,))
    # floor + centre light
    d.line([(0, 664), (TW, 664)], fill=(120, 128, 138, 45), width=2)
    glow = Image.new("L", (TW // 2, TH // 2), 0)
    ImageDraw.Draw(glow).ellipse([TW // 7, 10, TW // 4 + TW // 8, TH // 2], fill=95)
    f.paste((255, 255, 255), (0, 0),
            glow.resize((TW, TH), Image.BICUBIC).filter(ImageFilter.GaussianBlur(45)))

    a = _figure(os.path.join(ROOT, "assets", "soldier_us.png"), 432)
    b = _figure(os.path.join(ROOT, "assets", "soldier_cn.png"), 432)
    _place_figure(f, a, 452, 566)
    _place_figure(f, b, 828, 566)

    _number_block(f, "32", "KG", US, 56, 214, size=150, label="U.S. ARMY")
    w30 = tw("30", "bold", 150, -3)
    _number_block(f, "30", "KG", CN, TW - 56 - w30 - 76, 214, size=150, label="PLA",
                  label_right=TW - 56)

    badge = hex_badge(136, (24, 27, 32), "VS", C.PAPER, ring=(255, 255, 255))
    f.paste(badge.convert("RGB"), (TW // 2 - 68, 292), badge.split()[3])

    for country, x, label, accent, anc in (("us", 56, "USA", US, "lt"),
                                           ("cn", TW - 56, "CHINA", CN, "rt")):
        fl = flag_round(46, country)
        fx = x if anc == "lt" else x - fl.width
        f.paste(fl.convert("RGB"), (fx, 44), fl.split()[3])
        text(f, (fx + 62 if anc == "lt" else fx - 14, 54), label, "bold", 30, accent,
             tracking=5, anchor=anc)
    _headline(f, "WHAT A SOLDIER", "ACTUALLY CARRIES", "18 ITEMS · 13 WITH GEAR",
              "GEAR COMPARED · EP.02")
    return f


def build_dark():
    """Cinematic poster: dark, glowing figures, same layout so the pair reads."""
    f = grad_v((TW, TH), (24, 28, 36), (7, 9, 13)).convert("RGB")
    for colour, centre in (((34, 58, 112), (0.12, 0.40)), ((112, 24, 24), (0.88, 0.40))):
        layer, mask = radial((TW, TH), colour, centre=centre, radius=0.46, strength=0.9)
        f.paste(layer, (0, 0), mask)
    _, vig = radial((TW, TH), (0, 0, 0), centre=(0.5, 0.42), radius=0.95, strength=1.0)
    f.paste((0, 0, 0), (0, 0), vig.point(lambda v: int(v * 0.8)))
    pool = Image.new("L", (TW // 2, TH // 2), 0)
    ImageDraw.Draw(pool).ellipse([TW // 10, 20, TW // 4 + TW // 10, TH // 2], fill=105)
    f.paste((86, 100, 126), (0, 0),
            pool.resize((TW, TH), Image.BICUBIC).filter(ImageFilter.GaussianBlur(55)))

    a = _figure(os.path.join(ROOT, "assets", "soldier_us.png"), 452)
    b = _figure(os.path.join(ROOT, "assets", "soldier_cn.png"), 452)
    _place_figure(f, a, 452, 572, shadow_opacity=160, glow=(44, 86, 172))
    _place_figure(f, b, 828, 572, shadow_opacity=160, glow=(176, 40, 32))

    _number_block(f, "32", "KG", (146, 182, 246), 56, 214, size=150, label="U.S. ARMY",
                  label_color=(150, 170, 200))
    w30 = tw("30", "bold", 150, -3)
    _number_block(f, "30", "KG", (255, 106, 90), TW - 56 - w30 - 76, 214, size=150,
                  label="PLA", label_color=(226, 176, 168), label_right=TW - 56)

    badge = hex_badge(140, (10, 12, 16), "VS", C.PAPER, ring=C.PAPER)
    f.paste(badge.convert("RGB"), (TW // 2 - 70, 288), badge.split()[3])

    for country, x, label, accent, anc in (("us", 56, "USA", (206, 218, 240), "lt"),
                                           ("cn", TW - 56, "CHINA", (246, 194, 188), "rt")):
        fl = flag_round(46, country)
        fx = x if anc == "lt" else x - fl.width
        f.paste(fl.convert("RGB"), (fx, 42), fl.split()[3])
        text(f, (fx + 62 if anc == "lt" else fx - 14, 52), label, "bold", 30, accent,
             tracking=5, anchor=anc)
    _headline(f, "WHAT A SOLDIER", "ACTUALLY CARRIES", "USA vs CHINA",
              "GEAR COMPARED · EP.02", bar=(4, 5, 8), sub_col=(146, 154, 164))
    return f


def save(img, name):
    out = os.path.join(ROOT, "deliverables", name)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    img.convert("RGB").save(out, quality=95)
    print("  ->", out, img.size)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--light", action="store_true")
    ap.add_argument("--dark", action="store_true")
    a = ap.parse_args()
    both = not (a.light or a.dark)
    if both or a.light:
        save(build_light(), "thumbnail_studio.png")
    if both or a.dark:
        save(build_dark(), "thumbnail_cinematic.png")


if __name__ == "__main__":
    main()
