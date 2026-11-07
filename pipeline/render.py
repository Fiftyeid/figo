"""
FIGO — "Russian Armor: Technical Inventory"
Frame renderer.

Design language: clean white "technical display unit".
- Pure white field, hairline structure, no shadows, no gradients.
- Type in red / white / ink only.
- Every vehicle still is treated as an exhibit: cut out, centred, annotated.
"""
import json
import os

from PIL import Image, ImageDraw, ImageFont
import numpy as np
from scipy import ndimage

W, H = 1920, 1080
MARGIN = 72

RED = (200, 30, 30)
INK = (20, 20, 20)
GREY = (138, 138, 138)
HAIR = (222, 222, 222)
WHITE = (255, 255, 255)

FONT_DIR = "/usr/share/fonts/truetype/dejavu"
F_BOLD = os.path.join(FONT_DIR, "DejaVuSans-Bold.ttf")
F_REG = os.path.join(FONT_DIR, "DejaVuSans.ttf")

_font_cache = {}


def font(path, size):
    key = (path, size)
    if key not in _font_cache:
        _font_cache[key] = ImageFont.truetype(path, size)
    return _font_cache[key]


def text_width(draw, s, f, tracking=0):
    if not s:
        return 0
    return draw.textlength(s, font=f) + tracking * (len(s) - 1)


def tracked(draw, xy, s, f, fill, tracking=0, anchor="la"):
    s = s.upper()
    total = text_width(draw, s, f, tracking)
    x, y = xy
    if anchor[0] == "r":
        x -= total
    elif anchor[0] == "m":
        x -= total / 2
    for ch in s:
        draw.text((x, y), ch, font=f, fill=fill)
        x += draw.textlength(ch, font=f) + tracking
    return total


def fit_font(draw, s, path, max_w, start, tracking=0, min_size=18):
    size = start
    while size > min_size:
        f = font(path, size)
        if text_width(draw, s.upper(), f, tracking) <= max_w:
            return f
        size -= 2
    return font(path, min_size)


def hairline(draw, xy, fill=HAIR, width=1):
    draw.line(xy, fill=fill, width=width)


# ---------------------------------------------------------------- image prep
def render_path(renders_dir, vid):
    p = os.path.join(renders_dir, vid + ".png")
    if os.path.exists(p):
        return p
    j = os.path.join(renders_dir, vid + ".jpg")
    if os.path.exists(j):
        return j
    return p


def cutout(path, target_h=900):
    """Cut the vehicle out of its white studio background, kill cast shadows,
    return an RGBA image cropped to the subject."""
    im = Image.open(path).convert("RGB")
    scale = target_h / im.height
    im = im.resize((int(im.width * scale), target_h), Image.LANCZOS)

    a = np.asarray(im).astype(np.float32) / 255.0
    lum = a.max(axis=2)
    sat = np.where(lum > 0.01, (a.max(axis=2) - a.min(axis=2)) / np.maximum(lum, 0.01), 0)

    bg_like = ((lum > 0.93) & (sat < 0.09)) | ((lum > 0.855) & (sat < 0.055))
    lbl, n = ndimage.label(bg_like)
    border = np.zeros_like(bg_like, dtype=bool)
    border[0, :] = border[-1, :] = True
    border[:, 0] = border[:, -1] = True
    keep = np.unique(lbl[border & bg_like])
    bg = np.isin(lbl, keep[keep > 0])

    # eat the soft cast shadow that hugs the subject
    for _ in range(2):
        dist = ndimage.distance_transform_edt(~bg)
        bg = bg | ((dist < 55) & (sat < 0.16) & (lum > 0.78))

    alpha = (~bg).astype(np.float32)
    alpha = ndimage.binary_closing(alpha > 0.5, np.ones((5, 5))).astype(np.float32)
    alpha = ndimage.binary_fill_holes(alpha > 0.5).astype(np.float32)
    alpha = ndimage.gaussian_filter(alpha, 1.2)
    alpha = np.clip((alpha - 0.25) / 0.5, 0, 1)

    out = np.dstack([a * 255.0, alpha * 255.0])
    rgba = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), "RGBA")
    bbox = rgba.getbbox()
    if bbox:
        rgba = rgba.crop(bbox)
    return rgba


def place(canvas, img, box):
    x0, y0, x1, y1 = box
    bw, bh = x1 - x0, y1 - y0
    r = min(bw / img.width, bh / img.height)
    w, h = int(img.width * r), int(img.height * r)
    img = img.resize((w, h), Image.LANCZOS)
    px, py = x0 + (bw - w) // 2, y0 + (bh - h) // 2
    canvas.alpha_composite(img, (px, py))
    return px, py, w, h


def silhouette_edges(img):
    a = np.asarray(img.split()[-1])
    rows = []
    for y in range(a.shape[0]):
        idx = np.where(a[y] > 60)[0]
        rows.append((int(idx[0]), int(idx[-1])) if len(idx) else None)
    return rows


# ---------------------------------------------------------------- furniture
def frame(draw):
    c = 46
    for (x, y, dx, dy) in [
        (MARGIN - 18, MARGIN - 18, 1, 1),
        (W - MARGIN + 18, MARGIN - 18, -1, 1),
        (MARGIN - 18, H - MARGIN + 18, 1, -1),
        (W - MARGIN + 18, H - MARGIN + 18, -1, -1),
    ]:
        draw.line([(x, y), (x + dx * c, y)], fill=RED, width=2)
        draw.line([(x, y), (x, y + dy * c)], fill=RED, width=2)


def header(draw, category=None, index=None, total=None):
    f_lab = font(F_BOLD, 18)
    draw.rectangle([MARGIN, 62, MARGIN + 13, 75], fill=RED)
    tracked(draw, (MARGIN + 28, 58), "RUSSIAN ARMOR  ·  TECHNICAL INVENTORY", f_lab, RED, tracking=4)

    if index is not None:
        f_num = font(F_BOLD, 30)
        f_tot = font(F_BOLD, 17)
        s_num, s_tot = str(index).zfill(2), "/ %d" % total
        tw_tot = text_width(draw, s_tot, f_tot, 1)
        tracked(draw, (W - MARGIN, 56), s_tot, f_tot, GREY, tracking=1, anchor="ra")
        tracked(draw, (W - MARGIN - tw_tot - 12, 50), s_num, f_num, RED, tracking=1, anchor="ra")

    hairline(draw, [(MARGIN, 104), (W - MARGIN, 104)], HAIR, 1)
    draw.rectangle([MARGIN, 102, MARGIN + 150, 105], fill=RED)

    if category:
        f_cat = font(F_BOLD, 16)
        tw = text_width(draw, category, f_cat, 3)
        pad = 18
        draw.rectangle([MARGIN, 120, MARGIN + tw + pad * 2, 120 + 34], fill=RED)
        tracked(draw, (MARGIN + pad, 129), category, f_cat, WHITE, tracking=3)


def footer(draw, left_lines=None, right_lines=None):
    hairline(draw, [(MARGIN, H - 100), (W - MARGIN, H - 100)], HAIR, 1)
    f = font(F_BOLD, 14)
    if left_lines:
        x = MARGIN
        for i, s in enumerate(left_lines):
            col = RED if i == 0 else GREY
            w = tracked(draw, (x, H - 84), s, f, col, tracking=2)
            x += w + 34
            if i < len(left_lines) - 1:
                draw.line([(x - 20, H - 79), (x - 20, H - 68)], fill=HAIR, width=1)
    if right_lines:
        x = W - MARGIN
        for s in reversed(right_lines):
            w = tracked(draw, (x, H - 84), s, f, GREY, tracking=2, anchor="ra")
            x -= w + 30


# ---------------------------------------------------------------- scenes
def scene_vehicle(v, cat, index, total, renders_dir):
    canvas = Image.new("RGBA", (W, H), WHITE + (255,))
    draw = ImageDraw.Draw(canvas)
    frame(draw)
    header(draw, category="%s · %s" % (cat["index"], cat["title"]), index=index, total=total)

    veh = cutout(render_path(renders_dir, v["id"]), 980)
    box = (MARGIN - 16, 160, W - MARGIN + 16, 736)
    px, py, pw, ph = place(canvas, veh, box)

    scaled = veh.resize((pw, ph), Image.LANCZOS)
    rows = silhouette_edges(scaled)
    edges = lambda fy: rows[min(len(rows) - 1, max(0, int(ph * fy)))]

    tags = v.get("tags", [])
    f_tag = font(F_BOLD, 15)
    for i, (fy, side) in enumerate([(0.30, 1), (0.60, -1)]):
        if i >= len(tags):
            break
        e = edges(fy)
        if not e:
            continue
        ex = (px + e[1]) if side > 0 else (px + e[0])
        ey = py + int(ph * fy)
        lbl = "0%d  %s" % (i + 1, tags[i])
        if side > 0:
            lx = W - MARGIN
            tw = text_width(draw, lbl, f_tag, 2)
            draw.line([(ex + 4, ey), (lx - tw - 14, ey)], fill=RED, width=1)
            draw.rectangle([ex + 2, ey - 3, ex + 8, ey + 3], fill=RED)
            tracked(draw, (lx, ey - 24), lbl, f_tag, RED, tracking=2, anchor="ra")
        else:
            lx = MARGIN
            draw.line([(ex - 4, ey), (lx + 96, ey)], fill=RED, width=1)
            draw.rectangle([ex - 8, ey - 3, ex - 2, ey + 3], fill=RED)
            tracked(draw, (lx, ey - 24), lbl, f_tag, RED, tracking=2)

    f_name = fit_font(draw, v["name"], F_BOLD, 1180, 88, tracking=1)
    tracked(draw, (MARGIN, 748), v["name"], f_name, RED, tracking=1)

    hairline(draw, [(MARGIN, 866), (W - MARGIN, 866)], HAIR, 1)
    draw.rectangle([MARGIN, 864, MARGIN + 120, 869], fill=RED)

    specs = [("ENTERED SERVICE", v["year"]), ("CREW", v["crew"]),
             ("COMBAT WEIGHT", v["weight"]), ("MAIN ARMAMENT", v["armament"])]
    f_lab = font(F_BOLD, 13)
    for i, (lab, val) in enumerate(specs):
        x = MARGIN + i * 452
        tracked(draw, (x, 892), lab, f_lab, RED, tracking=2)
        f_val = fit_font(draw, val, F_BOLD, 400, 30, tracking=0)
        draw.text((x, 918), val, font=f_val, fill=INK)

    footer(draw, left_lines=["SECTION %s · %s" % (cat["index"], cat["title"])],
           right_lines=["OPEN SOURCES · APPROXIMATE"])
    return canvas.convert("RGB")


def scene_section(cat, vehicles, index, total):
    canvas = Image.new("RGBA", (W, H), WHITE + (255,))
    draw = ImageDraw.Draw(canvas)
    frame(draw)
    header(draw, index=index, total=total)

    f_big = font(F_BOLD, 300)
    tracked(draw, (MARGIN - 12, 172), cat["index"], f_big, RED, tracking=-6)

    f_title = fit_font(draw, cat["title"], F_BOLD, 1060, 74, tracking=1)
    tracked(draw, (MARGIN, 500), cat["title"], f_title, INK, tracking=1)

    f_sub = font(F_BOLD, 17)
    tracked(draw, (MARGIN, 600), cat["subtitle"], f_sub, RED, tracking=4)
    hairline(draw, [(MARGIN, 640), (MARGIN + 620, 640)], HAIR, 1)

    x = 1180
    tracked(draw, (x, 172), "IN THIS SECTION", font(F_BOLD, 14), RED, tracking=3)
    row_h = min(62, int(560 / max(1, len(vehicles))))
    f_item = font(F_BOLD, 27 if row_h >= 56 else 24)
    y = 210
    for i, v in enumerate(vehicles):
        tracked(draw, (x, y), "%02d" % (i + 1), font(F_BOLD, 15), GREY, tracking=1)
        draw.text((x + 44, y - 4), v["name"], font=f_item, fill=INK)
        hairline(draw, [(x, y + row_h - 20), (W - MARGIN, y + row_h - 20)], HAIR, 1)
        y += row_h

    f_cnt = font(F_BOLD, 15)
    tracked(draw, (MARGIN, 700), "%d VEHICLES IN THIS SECTION" % len(vehicles), f_cnt, GREY, tracking=3)

    draw.rectangle([MARGIN, H - 214, 1130, H - 148], fill=RED)
    f_b1 = font(F_BOLD, 20)
    tracked(draw, (MARGIN + 28, H - 188), "SECTION %s OF %d" % (cat["index"], total), f_b1, WHITE, tracking=4)

    footer(draw, left_lines=["TECHNICAL INVENTORY"],
           right_lines=["%02d / %d" % (index, total)])
    return canvas.convert("RGB")


def scene_intro(meta, total, renders_dir):
    canvas = Image.new("RGBA", (W, H), WHITE + (255,))
    draw = ImageDraw.Draw(canvas)
    frame(draw)
    header(draw, index=0, total=total)

    hero = cutout(render_path(renders_dir, "t90m"), 980)
    hw = int(hero.width * 640 / hero.height)
    hero = hero.resize((hw, 640), Image.LANCZOS)
    canvas.alpha_composite(hero, (W - MARGIN - hw + 30, 300))

    f1 = font(F_BOLD, 92)
    tracked(draw, (MARGIN, 214), "EVERY RUSSIAN", f1, INK, tracking=1)
    tracked(draw, (MARGIN, 316), "TANK & ARMORED", f1, RED, tracking=1)
    tracked(draw, (MARGIN, 418), "VEHICLE", f1, RED, tracking=1)

    hairline(draw, [(MARGIN, 546), (MARGIN + 520, 546)], HAIR, 1)
    draw.rectangle([MARGIN, 544, MARGIN + 120, 549], fill=RED)

    f2 = font(F_BOLD, 24)
    tracked(draw, (MARGIN, 578), "IN ACTIVE SERVICE TODAY", f2, INK, tracking=5)

    f3 = font(F_BOLD, 16)
    tracked(draw, (MARGIN, 640), "52 MACHINES   ·   8 CATEGORIES   ·   1947 — 2023", f3, GREY, tracking=3)

    footer(draw, left_lines=["TECHNICAL INVENTORY"],
           right_lines=["OPEN SOURCES · SPECIFICATIONS APPROXIMATE"])
    return canvas.convert("RGB")


def scene_outro(meta, total, renders_dir):
    canvas = Image.new("RGBA", (W, H), WHITE + (255,))
    draw = ImageDraw.Draw(canvas)
    frame(draw)
    header(draw, index=total, total=total)

    f1 = font(F_BOLD, 150)
    tracked(draw, (W // 2, 300), "52", f1, RED, tracking=0, anchor="ma")
    f2 = font(F_BOLD, 40)
    tracked(draw, (W // 2, 500), "VEHICLES  ·  8 CATEGORIES", f2, INK, tracking=6, anchor="ma")

    hairline(draw, [(W // 2 - 300, 590), (W // 2 + 300, 590)], HAIR, 1)
    draw.rectangle([W // 2 - 60, 588, W // 2 + 60, 592], fill=RED)

    f3 = font(F_REG, 22)
    for i, line in enumerate(["Specifications are drawn from open sources and are approximate.",
                              "Loss figures circulating online count only visually confirmed vehicles."]):
        draw.text((W // 2, 626 + i * 38), line, font=f3, fill=GREY, anchor="ma")

    f4 = font(F_BOLD, 20)
    tracked(draw, (W // 2, 760), "SUBSCRIBE FOR THE NEXT INVENTORY", f4, RED, tracking=5, anchor="ma")
    footer(draw, left_lines=["RUSSIAN ARMOR · TECHNICAL INVENTORY"],
           right_lines=["END OF INVENTORY"])
    return canvas.convert("RGB")
