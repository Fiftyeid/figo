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
    ap.add_argument("--showroom", action="store_true", help="reference-style two-panel cut")
    ap.add_argument("--light", action="store_true")
    ap.add_argument("--dark", action="store_true")
    ap.add_argument("--japan", action="store_true", help="EP.03 JAPAN AIR FLEET 2026")
    a = ap.parse_args()
    picked = a.showroom or a.light or a.dark or a.japan
    if a.japan:
        save(build_japan(), "thumbnail_japan.png")
        return
    if not picked or a.showroom:
        save(build_showroom(), "thumbnail_showroom.png")
    if not picked or a.light:
        save(build_light(), "thumbnail_studio.png")
    if not picked or a.dark:
        save(build_dark(), "thumbnail_cinematic.png")



# ============================================================ showroom cut
# Reference-driven layout: two white panels, huge distressed stencil country
# names, one soldier per side surrounded by gear on museum stands, glossy
# reflective floor.
FLOOR = 600
PANEL = TW // 2


def _crop_alpha(im, thr=96):
    a = im.split()[3].point(lambda v: 255 if v > thr else 0)
    bb = a.getbbox()
    return im.crop(bb) if bb else im


def _mount(name, size, upright=True):
    """Crop an asset to the object and stand it up (muzzle to the ceiling)."""
    im = _crop_alpha(Image.open(os.path.join(ROOT, "assets", name + ".png")).convert("RGBA"))
    if upright:
        im = im.transpose(Image.ROTATE_270)
    s = size / im.height
    return im.resize((max(8, int(round(im.width * s))), size), Image.LANCZOS)


def _distress(rgba, seed=1, cell=7, thr=0.22, chunk=0.13, scratches=5):
    """Chew the letterform with hard-edged speckle, like a photocopied stencil."""
    w, h = rgba.size
    rng = np.random.default_rng(seed)
    # fine, blocky speckle (nearest upscale keeps the edges crisp)
    small = Image.fromarray((rng.random((h // cell + 1, w // cell + 1)) * 255).astype(np.uint8))
    fine = np.asarray(small.resize((w, h), Image.NEAREST), np.float32)
    pixel = np.asarray(Image.fromarray((rng.random((h, w)) * 255).astype(np.uint8)),
                       np.float32)
    n = (fine * 0.62 + pixel * 0.38) / 255.0
    # a few big bites out of the strokes
    c = max(2, h // 16)
    blob = Image.fromarray((rng.random((c, w // 16 + 1)) * 255).astype(np.uint8))
    blob = np.asarray(blob.resize((w, h), Image.BICUBIC).filter(ImageFilter.GaussianBlur(2.5)),
                      np.float32) / 255.0
    keep = ((n > thr) & (blob > chunk)).astype(np.float32)
    keep = np.asarray(Image.fromarray((keep * 255).astype(np.uint8))
                      .filter(ImageFilter.GaussianBlur(0.6)), np.float32) / 255.0
    a = np.asarray(rgba.split()[3], np.float32) / 255.0
    mask = Image.fromarray((np.clip(a * (0.06 + 0.94 * keep), 0, 1) * 255).astype(np.uint8), "L")

    d = ImageDraw.Draw(mask)
    for _ in range(scratches):
        x0, y0 = int(rng.integers(0, w)), int(rng.integers(0, h))
        d.line([(x0, y0), (x0 + int(rng.integers(-w // 2, w // 2)),
                           y0 + int(rng.integers(-h // 2, h // 2)))],
               fill=0, width=int(rng.integers(1, 3)))
    for _ in range(26):                                  # paint spatter
        r = int(rng.integers(1, 5))
        x, y = int(rng.integers(0, w)), int(rng.integers(0, h))
        d.ellipse([x - r, y - r, x + r, y + r], fill=0)
    out = rgba.copy()
    out.putalpha(mask)
    return out


def _stencil(label, max_w, size=176):
    """Heavy stencil word: height stays fixed, width is condensed to fit."""
    raw = _crop_alpha(P.text_img(label, "cond", size, (16, 16, 17), 3), thr=8)
    im = _distress(raw, seed=sum(label.encode()) * 7 % 900 + 11)
    if im.width > max_w:
        k = max(0.52, max_w / im.width)
        im = im.resize((int(im.width * k), im.height), Image.LANCZOS)
    return im


def _stand(f, cx, top, base):
    d = ImageDraw.Draw(f, "RGBA")
    d.rectangle([cx - 3, top, cx + 3, base - 4], fill=(28, 28, 31, 255))
    d.ellipse([cx - 28, base - 10, cx + 28, base + 4], fill=(22, 22, 25, 255))
    d.ellipse([cx - 22, base - 9, cx + 22, base - 1], fill=(64, 66, 70, 255))


SHOWROOM = {
    "left": dict(label="USA", text_w=344, soldier=("soldier_us", 400, 445),
                 gear=[("mg_us", 80, 340), ("gl_us", 240, 300), ("m7", 560, 320)]),
    "right": dict(label="CHINA", text_w=316, soldier=("soldier_cn", 905, 445),
                  gear=[("qbz191", 712, 300), ("gl_cn", 1090, 300),
                        ("optic_cn", 1215, 350)]),
}


def build_showroom():
    f = grad_v((TW, TH), (247, 247, 247), (242, 243, 244)).convert("RGB")
    yy = np.arange(TH, dtype=np.float32)
    ts = 0.60 * np.exp(-yy / 150.0)
    soft = Image.fromarray(np.repeat((ts * 255)[:, None].astype(np.uint8), TW, axis=1), "L")
    f.paste(grad_v((TW, TH), (208, 209, 212), (231, 231, 231)), (0, 0), soft)
    # two wall panels with the faintest tonal shift
    d = ImageDraw.Draw(f, "RGBA")
    d.rectangle([0, 0, PANEL, TH], fill=(255, 255, 255, 26))
    d.rectangle([PANEL, 0, TW, TH], fill=(0, 0, 0, 5))

    # recessed ceiling lights
    for cx in (188, 318, 448, 828, 958, 1088):
        glow = Image.new("L", (250, 210), 0)
        ImageDraw.Draw(glow).ellipse([55, 16, 195, 120], fill=190)
        glow = glow.filter(ImageFilter.GaussianBlur(26))
        f.paste((255, 251, 241), (cx - 125, 0), glow)
        d.ellipse([cx - 9, 10, cx + 9, 26], fill=(255, 253, 246, 255))
        d.ellipse([cx - 6, 12, cx + 6, 24], fill=(232, 226, 212, 255))

    # floor
    fl = grad_v((TW, TH - FLOOR), (232, 233, 235), (214, 216, 219))
    f.paste(fl, (0, FLOOR))
    d.line([(0, FLOOR), (TW, FLOOR)], fill=(196, 198, 202, 255), width=2)
    d.line([(0, FLOOR + 2), (TW, FLOOR + 2)], fill=(255, 255, 255, 190), width=2)

    objects = Image.new("RGBA", (TW, TH), (0, 0, 0, 0))
    wall_sh = Image.new("L", (TW, TH), 0)
    wsd = ImageDraw.Draw(wall_sh)
    for _, cfg in SHOWROOM.items():
        _, sx, sh = cfg["soldier"]
        wsd.ellipse([sx - 96, FLOOR - sh - 8, sx + 96, FLOOR + 10], fill=48)
        for gname, gx, gh in cfg["gear"]:
            wsd.ellipse([gx - gh * 0.42, FLOOR - gh - 6, gx + gh * 0.42, FLOOR + 8], fill=46)
    f.paste((146, 148, 152), (0, 0), wall_sh.filter(ImageFilter.GaussianBlur(26)))

    for side, cfg in SHOWROOM.items():
        # stencil country name
        stencil = _stencil(cfg["label"], cfg["text_w"])
        cx = PANEL // 2 if side == "left" else PANEL + PANEL // 2
        tx, ty = cx - stencil.width // 2, 30
        f.paste(stencil.convert("RGB"), (tx, ty), stencil.split()[3])
        spray = Image.new("RGBA", (TW, TH), (0, 0, 0, 0))
        sdraw = ImageDraw.Draw(spray)
        rng = np.random.default_rng(sum(cfg["label"].encode()) + 3)
        for _ in range(220):
            px = tx + rng.integers(-26, stencil.width + 26)
            py = ty + rng.integers(-14, stencil.height + 18)
            r = int(rng.integers(1, 3))
            sdraw.ellipse([px - r, py - r, px + r, py + r],
                          fill=(24, 24, 26, int(rng.integers(18, 70))))
        f.paste(spray.convert("RGB"), (0, 0), spray.split()[3])

        # gear on stands first, the soldier in front of it
        for gname, gx, gh in cfg["gear"]:
            g = _mount(gname, gh, upright=True)
            _stand(objects, gx, FLOOR - gh + 14, FLOOR)
            objects.paste(g, (gx - g.width // 2, FLOOR - g.height), g.split()[3])
        name, sx, sh = cfg["soldier"]
        spr = _mount(name, sh, upright=False)
        objects.paste(spr, (sx - spr.width // 2, FLOOR - spr.height), spr.split()[3])

    # contact shadows, then the objects themselves
    sh_layer = Image.new("L", (TW, TH), 0)
    sd = ImageDraw.Draw(sh_layer)
    for side, cfg in SHOWROOM.items():
        for _, gx, gh in cfg["gear"]:
            sd.ellipse([gx - gh * 0.20, FLOOR - 7, gx + gh * 0.20, FLOOR + 9], fill=120)
        _, sx, sh = cfg["soldier"]
        sd.ellipse([sx - 74, FLOOR - 12, sx + 74, FLOOR + 12], fill=150)
    sh_layer = sh_layer.filter(ImageFilter.GaussianBlur(7))
    f.paste((96, 99, 104), (0, 0), sh_layer)

    # mirrored floor reflection: mirror about the floor line, then fade down
    above = objects.crop((0, 0, TW, FLOOR))
    refl = above.transpose(Image.FLIP_TOP_BOTTOM).filter(ImageFilter.GaussianBlur(1.2))
    h = TH - FLOOR
    ramp = np.clip(1.0 - np.linspace(0, 1, h) ** 1.55, 0, 1) * 0.72
    rmask = Image.fromarray(np.repeat((ramp * 255)[:, None].astype(np.uint8), TW, axis=1), "L")
    a = refl.split()[3].crop((0, 0, TW, h))
    f.paste(refl.convert("RGB").crop((0, 0, TW, h)), (0, FLOOR),
            Image.composite(a, Image.new("L", (TW, h), 0), rmask))

    f.paste(objects.convert("RGB"), (0, 0), objects.split()[3])

    # centre seam + gentle vignette + a whisper of grain
    d = ImageDraw.Draw(f, "RGBA")
    d.rectangle([PANEL - 1, 0, PANEL + 1, TH], fill=(198, 200, 204, 210))
    _, vig = radial((TW, TH), (0, 0, 0), centre=(0.5, 0.44), radius=1.02, strength=1.0)
    f.paste((24, 22, 20), (0, 0), vig.point(lambda v: int(v * 0.14)))
    return f


# ============================================================ EP.03  JAPAN
JP_FLOOR = 618
JP_LINEUP = (
    # (asset, cx, width) — left to right, biggest in the middle
    ("fleet/f15j", 236, 462),
    ("fleet/f35", 646, 500),
    ("fleet/ch47j", 1052, 452),
)


def build_japan():
    """JAPAN AIR FLEET 2026 — one wall, one fleet, one number."""
    f = grad_v((TW, TH), (247, 247, 248), (242, 243, 244)).convert("RGB")
    yy = np.arange(TH, dtype=np.float32)
    ts = 0.62 * np.exp(-yy / 150.0)
    soft = Image.fromarray(np.repeat((ts * 255)[:, None].astype(np.uint8), TW, axis=1), "L")
    f.paste(grad_v((TW, TH), (206, 207, 210), (232, 232, 233)), (0, 0), soft)

    d = ImageDraw.Draw(f, "RGBA")
    for cx in (150, 360, 570, 780, 990, 1200):
        glow = Image.new("L", (230, 200), 0)
        ImageDraw.Draw(glow).ellipse([50, 14, 180, 112], fill=188)
        glow = glow.filter(ImageFilter.GaussianBlur(24))
        f.paste((255, 251, 241), (cx - 115, 0), glow)
        d.ellipse([cx - 8, 9, cx + 8, 24], fill=(255, 253, 246, 255))

    fl = grad_v((TW, TH - JP_FLOOR), (232, 233, 235), (212, 214, 217))
    f.paste(fl, (0, JP_FLOOR))
    d.line([(0, JP_FLOOR), (TW, JP_FLOOR)], fill=(196, 198, 202, 255), width=2)
    d.line([(0, JP_FLOOR + 2), (TW, JP_FLOOR + 2)], fill=(255, 255, 255, 190), width=2)

    # the word, distressed, straight from the showroom engine
    stencil = _stencil("JAPAN", 1120)
    tx, ty = TW // 2 - stencil.width // 2, 22
    f.paste(stencil.convert("RGB"), (tx, ty), stencil.split()[3])
    spray = Image.new("RGBA", (TW, TH), (0, 0, 0, 0))
    sdraw = ImageDraw.Draw(spray)
    rng = np.random.default_rng(88)
    for _ in range(240):
        px = tx + rng.integers(-26, stencil.width + 26)
        py = ty + rng.integers(-14, stencil.height + 18)
        r = int(rng.integers(1, 3))
        sdraw.ellipse([px - r, py - r, px + r, py + r],
                      fill=(24, 24, 26, int(rng.integers(18, 70))))
    f.paste(spray.convert("RGB"), (0, 0), spray.split()[3])

    objects = Image.new("RGBA", (TW, TH), (0, 0, 0, 0))
    for name, cx, w in JP_LINEUP:
        spr = _mount(name, 520, upright=False)
        spr = spr.resize((w, max(2, int(spr.height * w / spr.width))), Image.LANCZOS)
        objects.paste(spr, (cx - spr.width // 2, JP_FLOOR - spr.height), spr.split()[3])

    sh = Image.new("L", (TW, TH), 0)
    sd = ImageDraw.Draw(sh)
    for name, cx, w in JP_LINEUP:
        sd.ellipse([cx - w * 0.62, JP_FLOOR - 6, cx + w * 0.62, JP_FLOOR + 10], fill=110)
    sh = sh.filter(ImageFilter.GaussianBlur(9))
    f.paste((96, 99, 104), (0, 0), sh)

    above = objects.crop((0, 0, TW, JP_FLOOR))
    refl = above.transpose(Image.FLIP_TOP_BOTTOM).filter(ImageFilter.GaussianBlur(1.3))
    h_ = TH - JP_FLOOR
    ramp = np.clip(1.0 - np.linspace(0, 1, h_) ** 1.5, 0, 1) * 0.66
    rmask = Image.fromarray(np.repeat((ramp * 255)[:, None].astype(np.uint8), TW, axis=1), "L")
    a = refl.split()[3].crop((0, 0, TW, h_))
    f.paste(refl.convert("RGB").crop((0, 0, TW, h_)), (0, JP_FLOOR),
            Image.composite(a, Image.new("L", (TW, h_), 0), rmask))
    f.paste(objects.convert("RGB"), (0, 0), objects.split()[3])

    # the promise, as two pills under the word — no banner across the mirror
    lead = "EVERY AIRCRAFT  ·  2026"
    lw = int(tw(lead, "bold", 26, 3.0) + 84)
    pw = 186
    total = lw + 18 + pw
    x0 = TW // 2 - total // 2
    dark = Image.new("RGBA", (lw, 56), (0, 0, 0, 0))
    ImageDraw.Draw(dark).rounded_rectangle([0, 0, lw - 1, 55], 28, fill=(18, 21, 26, 255))
    f.paste(dark.convert("RGB"), (x0, 214), dark.split()[3])
    text(f, (x0 + lw // 2, 242), lead, "bold", 26, (255, 255, 255), tracking=3.0, anchor="mm")
    red = Image.new("RGBA", (pw, 56), (0, 0, 0, 0))
    ImageDraw.Draw(red).rounded_rectangle([0, 0, pw - 1, 55], 28, fill=(188, 0, 45, 255))
    f.paste(red.convert("RGB"), (x0 + lw + 18, 214), red.split()[3])
    text(f, (x0 + lw + 18 + pw // 2, 242), "19 TYPES", "bold", 26, (255, 255, 255),
         tracking=2, anchor="mm")

    _, vig = radial((TW, TH), (0, 0, 0), centre=(0.5, 0.44), radius=1.02, strength=1.0)
    f.paste((24, 22, 20), (0, 0), vig.point(lambda v: int(v * 0.13)))
    return f


if __name__ == "__main__":
    main()
