#!/usr/bin/env python3
"""Render War Factor motion-graphic layers from graphics_data.json.

Rules enforced here:
- Every number shown on screen is read from ../step1_research/sources.csv by its id.
- Each card's 'expected' value must equal the CSV value, or the script stops.
- Template tokens like {s24} are replaced with the CSV value for id 24.
- No logos, seals, or unit insignia are drawn.

Outputs (relative to this folder):
  layers/NN_<card>.png            transparent 1920x1080 RGBA layer per card
  layers/03_race_manned_2023_alpha.mov   animated race layer, ProRes 4444 with alpha (only if WF_ALPHA_MOV=1; about 200 MB, not kept in the repo)
  preview/NN_<card>_composite.png layer over a placeholder background
  preview/race_composite.mp4      animated race over the placeholder background
  ../step6_publish/thumbnail_1280x720.png   thumbnail (no logos, no footage)

Run: python3 build_graphics.py   (needs Pillow; ffmpeg on PATH for the videos)
"""
import csv
import json
import os
import re
import subprocess
import sys
import tempfile

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CSV_PATH = os.path.join(ROOT, "step1_research", "sources.csv")
THUMB_PATH = os.path.join(ROOT, "step6_publish", "thumbnail_1280x720.png")
LAYERS = os.path.join(HERE, "layers")
PREVIEW = os.path.join(HERE, "preview")

DATA = json.load(open(os.path.join(HERE, "graphics_data.json"), encoding="utf-8"))
PAL = json.load(open(os.path.join(HERE, "palette.json"), encoding="utf-8"))

W = PAL["canvas"]["width"]
H = PAL["canvas"]["height"]
FPS = PAL["canvas"]["fps"]
MX = PAL["layout"]["safe_margin_x"]
MY = PAL["layout"]["safe_margin_y"]
CHIP_H = 46
CHIP_Y = 900
CHIP_ROW_GAP = 58


def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


C = {k: hex_rgb(v) for k, v in PAL["colors"].items() if isinstance(v, str) and v.startswith("#")}
PANEL_ALPHA = PAL["colors"]["panel_alpha"]
F_BOLD = PAL["type"]["font_bold"]
F_REG = PAL["type"]["font_regular"]


def font(path, px):
    return ImageFont.truetype(path, px)


# ---------- source numbers (single point of truth: sources.csv) ----------

def load_sources():
    out = {}
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            try:
                out[int(r["id"])] = int(r["number"])
            except ValueError:
                pass  # text-only rows have no number
    return out


SRC = load_sources()
USED = []  # (card, source_id, expected, csv_value)


def check(card, sid, expected):
    if sid not in SRC:
        sys.exit(f"STOP: {card}: source id {sid} has no numeric value in sources.csv")
    if expected != SRC[sid]:
        sys.exit(f"STOP: {card}: expected {expected} but sources.csv id {sid} = {SRC[sid]}")
    USED.append((card, sid, expected, SRC[sid]))
    return SRC[sid]


def num(card, sid, expected, approx=False, prefix=""):
    v = check(card, sid, expected)
    s = f"{v:,}"
    if approx:
        s = "about " + s
    if prefix:
        s = prefix + " " + s
    return s


def subst(card, s):
    def rep(m):
        sid = int(m.group(1))
        if sid not in SRC:
            sys.exit(f"STOP: {card}: token {{s{sid}}} has no value in sources.csv")
        USED.append((card, sid, None, SRC[sid]))
        return f"{SRC[sid]:,}"
    return re.sub(r"\{s(\d+)\}", rep, s)


# ---------- drawing helpers ----------

def new_layer():
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    return img, ImageDraw.Draw(img)


def text(d, xy, s, px, color, bold=False, anchor="la"):
    d.text(xy, s, font=font(F_BOLD if bold else F_REG, px), fill=color, anchor=anchor)


def tlen(d, s, px, bold=False):
    return d.textlength(s, font=font(F_BOLD if bold else F_REG, px))


def headline(d, s):
    text(d, (MX, PAL["layout"]["headline_y"]), s, PAL["type"]["headline_px"], C["text_primary"], bold=True)


def chips(d, items):
    x, row = MX, 0
    f = font(F_REG, PAL["type"]["chip_px"])
    for c in items:
        w = d.textlength(c, font=f) + 36
        if x + w > W - MX:
            x = MX
            row += 1
        y = CHIP_Y + row * CHIP_ROW_GAP
        d.rounded_rectangle((x, y, x + w, y + CHIP_H), radius=PAL["layout"]["corner_radius"], fill=C["chip_fill"])
        d.text((x + 18, y + CHIP_H / 2), c, font=f, fill=C["chip_text"], anchor="lm")
        x += w + 14


def bar(d, x, y, w, h, color, alpha=255):
    if w <= 0:
        return
    d.rounded_rectangle((x, y, x + w, y + h), radius=10, fill=(*color, alpha))


def ease(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


# ---------- cards ----------

def card_big_figure(c):
    img, d = new_layer()
    headline(d, c["headline"])
    f = c["figure"]
    s = num(c["id"], f["source_id"], f["expected"])
    text(d, (W / 2, 470), s, PAL["type"]["big_figure_px"], C["branch_air_force"], bold=True, anchor="mm")
    text(d, (W / 2, 640), c["sub"], PAL["type"]["label_px"], C["text_secondary"], anchor="mm")
    chips(d, [subst(c["id"], x) for x in c["chips"]])
    return img


def card_two_bar_types(c):
    img, d = new_layer()
    headline(d, c["headline"])
    maxv = max(check(c["id"], b["source_id"], b["expected"]) for b in c["bars"])
    maxw = 1100
    for i, b in enumerate(c["bars"]):
        y = 300 + i * 280
        v = SRC[b["source_id"]]
        text(d, (MX, y), b["label"], PAL["type"]["label_px"], C["text_secondary"])
        bar(d, MX, y + 70, int(maxw * v / maxv), 110, C[b["color"]])
        val = num(c["id"], b["source_id"], b["expected"], approx=b.get("approx", False))
        text(d, (MX + int(maxw * v / maxv) + 28, y + 125), val, 64, C["text_primary"], bold=True, anchor="lm")
    chips(d, [subst(c["id"], x) for x in c["chips"]])
    return img


def race_frame(c, t):
    """t in seconds from the start of the animation; None = final state."""
    img, d = new_layer()
    headline(d, c["headline"])
    maxv = max(check(c["id"], b["source_id"], b["expected"]) for b in c["bars"])
    maxw = 1200
    anim = c["animate"]
    starts = [anim["bar_1_start_s"], anim["bar_2_start_s"]]
    for i, b in enumerate(c["bars"]):
        y = 300 + i * 260
        v = SRC[b["source_id"]]
        prog = 1.0 if t is None else ease((t - starts[i]) / anim["grow_s"])
        w = int(maxw * v / maxv * prog)
        text(d, (MX, y), b["label"], PAL["type"]["label_px"], C["text_secondary"])
        bar(d, MX, y + 70, w, 110, C[b["color"]])
        if prog >= 1.0:
            val = num(c["id"], b["source_id"], b["expected"], approx=b.get("approx", False))
            text(d, (MX + w + 28, y + 125), val, 64, C["text_primary"], bold=True, anchor="lm")
    text(d, (MX, 820), c["caveat"], 36, C["caveat"])
    chips(d, [subst(c["id"], x) for x in c["chips"]])
    return img


def card_stacked_split(c):
    img, d = new_layer()
    headline(d, c["headline"])
    tot = check(c["id"], c["total"]["source_id"], c["total"]["expected"])
    text(d, (MX, 300), c["definition_line"], PAL["type"]["label_px"], C["text_secondary"])
    full = 1500
    text(d, (MX, 380), num(c["id"], c["total"]["source_id"], c["total"]["expected"]) + " total", 64, C["text_primary"], bold=True)
    x = MX
    y = 470
    for p in c["parts"]:
        v = check(c["id"], p["source_id"], p["expected"])
        w = int(full * v / tot)
        bar(d, x, y, w, 120, C[p["color"]])
        if p["source_id"] == 2:
            text(d, (x + 24, y + 150), f"{p['label']}: {v:,}", 36, C["text_primary"])
        else:
            text(d, (W - MX, y + 150), f"{p['label']}: {v:,}", 36, C["text_primary"], anchor="ra")
        x += w
    chips(d, [subst(c["id"], x) for x in c["chips"]])
    return img


def card_type_list(c):
    img, d = new_layer()
    headline(d, c["headline"])
    rows = c["rows"]
    maxv = max(check(c["id"], r["source_id"], r["expected"]) for r in rows)
    top, bottom = 260, 840
    step = min(96, (bottom - top) / len(rows))
    for i, r in enumerate(rows):
        y = top + i * step
        v = SRC[r["source_id"]]
        text(d, (MX, y), r["label"], 36, C["text_secondary"])
        bar(d, 760, int(y) + 6, int(520 * v / maxv), 30, C["branch_army"] if c["id"].startswith("06") else C["branch_air_force"])
        val = num(c["id"], r["source_id"], r["expected"], approx=r.get("approx", False))
        text(d, (760 + int(520 * v / maxv) + 20, y), val, 36, C["text_primary"], bold=True)
    if c.get("note"):
        text(d, (MX, 860), c["note"], 32, C["text_secondary"])
    chips(d, [subst(c["id"], x) for x in c["chips"]])
    return img


def wrap(d, s, px, maxw):
    f = font(F_REG, px)
    words, lines, cur = s.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if d.textlength(t, font=f) <= maxw:
            cur = t
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def card_two_views(c):
    img, d = new_layer()
    headline(d, c["headline"])
    panels = [c["view_a"], c["view_b"], c["compare"]]
    pw, gap = 540, 60
    for i, p in enumerate(panels):
        x = MX + i * (pw + gap)
        y = 260
        d.rounded_rectangle((x, y, x + pw, y + 430), radius=PAL["layout"]["corner_radius"], fill=(22, 27, 34, PANEL_ALPHA))
        ty = y + 30
        for line in wrap(d, subst(c["id"], p["title"]), 30, pw - 60):
            text(d, (x + 30, ty), line, 30, C["text_secondary"])
            ty += 40
        approx = p.get("approx", False)
        if approx:
            text(d, (x + 30, y + 170), "about", 36, C[p["color"]])
        val = f"{SRC[p['source_id']]:,}"
        check(c["id"], p["source_id"], p["expected"])
        text(d, (x + 30, y + 215), val, 96, C[p["color"]], bold=True)
        if p.get("note"):
            ny = y + 340
            for line in wrap(d, subst(c["id"], p["note"]), 26, pw - 60):
                text(d, (x + 30, ny), line, 26, C["text_secondary"])
                ny += 34
    for i, cv in enumerate(c["caveats"]):
        text(d, (MX, 730 + i * 44), subst(c["id"], cv), 32, C["caveat"] if i == 0 else C["text_secondary"])
    chips(d, [subst(c["id"], x) for x in c["chips"]])
    return img


def card_combined(c):
    img, d = new_layer()
    headline(d, c["headline"])
    f = c["figure"]
    s = num(c["id"], f["source_id"], f["expected"], approx=f.get("approx", False))
    text(d, (W / 2, 430), s, 200, C["branch_navy_marine_combined"], bold=True, anchor="mm")
    for i, ln in enumerate(c["lines"]):
        text(d, (W / 2, 600 + i * 56), ln, 40, C["text_primary"] if i == 0 else C["caveat"], anchor="mm")
    chips(d, [subst(c["id"], x) for x in c["chips"]])
    return img


def card_context(c):
    img, d = new_layer()
    headline(d, c["headline"])
    f = c["figure"]
    s = num(c["id"], f["source_id"], f["expected"], prefix=f.get("prefix", ""))
    text(d, (W / 2, 450), s, 170, C["text_primary"], bold=True, anchor="mm")
    text(d, (W / 2, 610), subst(c["id"], c["sub"]), 42, C["text_secondary"], anchor="mm")
    check(c["id"], c["nations"]["source_id"], c["nations"]["expected"])
    text(d, (W / 2, 700), "Scale check, not a ranking.", 36, C["text_secondary"], anchor="mm")
    chips(d, [subst(c["id"], x) for x in c["chips"]])
    return img


def card_recap(c):
    img, d = new_layer()
    headline(d, c["headline"])
    for i, r in enumerate(c["cards"]):
        y = 250 + i * 100
        v = check(c["id"], r["source_id"], r["expected"])
        d.rounded_rectangle((MX, y, W - MX, y + 80), radius=12, fill=(22, 27, 34, PANEL_ALPHA))
        text(d, (MX + 30, y + 40), r["label"], 36, C["text_secondary"], anchor="lm")
        text(d, (W - MX - 30, y + 40), f"{v:,}", 44, C["text_primary"], bold=True, anchor="rm")
    chips(d, [subst(c["id"], x) for x in c["chips"]])
    return img


LAYOUTS = {
    "big_figure": card_big_figure,
    "two_bar_types": card_two_bar_types,
    "stacked_split": card_stacked_split,
    "type_list": card_type_list,
    "two_views": card_two_views,
    "combined_card": card_combined,
    "context": card_context,
    "recap": card_recap,
}


def background_placeholder():
    return Image.new("RGBA", (W, H), (*hex_rgb(PAL["colors"]["background_placeholder"]), 255))


def composite(layer):
    bg = background_placeholder()
    bg.alpha_composite(layer)
    return bg


def make_thumbnail():
    # 1280x720. No logos, seals, insignia, or footage. Text only.
    img = Image.new("RGB", (1280, 720), hex_rgb(PAL["colors"]["background_placeholder"]))
    d = ImageDraw.Draw(img)
    d.rectangle((0, 0, 1280, 12), fill=hex_rgb(PAL["colors"]["branch_air_force"]))
    fb = font(F_BOLD, 96)
    fm = font(F_BOLD, 54)
    fs = font(F_REG, 36)
    d.text((64, 110), "IT DEPENDS", font=fb, fill=hex_rgb(PAL["colors"]["text_primary"]))
    d.text((64, 230), "ON THE COUNT", font=fb, fill=hex_rgb(PAL["colors"]["branch_navy_marine_combined"]))
    af = f"Air Force {SRC[2]:,} manned"
    ar = f"Army about {SRC[24]:,} manned"
    d.text((64, 430), af, font=fm, fill=hex_rgb(PAL["colors"]["branch_air_force"]))
    d.text((64, 500), ar, font=fm, fill=hex_rgb(PAL["colors"]["branch_army"]))
    d.text((64, 600), "Manned aircraft, 2023. Sources differ: see description.", font=fs, fill=hex_rgb(PAL["colors"]["text_secondary"]))
    USED.append(("thumbnail", 2, 4959, SRC[2]))
    USED.append(("thumbnail", 24, 3900, SRC[24]))
    os.makedirs(os.path.dirname(THUMB_PATH), exist_ok=True)
    img.save(THUMB_PATH)


def render_race_video(card):
    """Animated race layer (alpha, ProRes 4444) and composite preview (H.264)."""
    seconds = card["animate"]["hold_until_s"]
    n = int(seconds * FPS)
    with tempfile.TemporaryDirectory() as tmp:
        for i in range(n):
            race_frame(card, i / FPS).save(os.path.join(tmp, f"f{i:04d}.png"))
        alpha = os.path.join(LAYERS, f"{card['id']}_alpha.mov")
        if os.environ.get("WF_ALPHA_MOV"):  # off by default: ~200 MB for 14 s
          subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS),
                        "-i", os.path.join(tmp, "f%04d.png"),
                        "-c:v", "prores_ks", "-profile:v", "4444", "-pix_fmt", "yuva444p10le",
                        alpha], check=True)
        comp = os.path.join(PREVIEW, "race_composite.mp4")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error",
                        "-f", "lavfi", "-i", f"color=c={PAL['colors']['background_placeholder']}:s={W}x{H}:r={FPS}",
                        "-framerate", str(FPS), "-i", os.path.join(tmp, "f%04d.png"),
                        "-filter_complex", "[0][1]overlay=shortest=1,format=yuv420p",
                        "-c:v", "libx264", "-crf", "20", "-preset", "medium", "-movflags", "+faststart",
                        comp], check=True)
    return alpha, comp


def main():
    os.makedirs(LAYERS, exist_ok=True)
    os.makedirs(PREVIEW, exist_ok=True)
    rendered = []
    for idx, card in enumerate(DATA["cards"], 1):
        if card["layout"] == "race":
            layer = race_frame(card, None)
            render_race_video(card)  # writes the animated alpha MOV and race_composite.mp4
        else:
            layer = LAYOUTS[card["layout"]](card)
        layer_path = os.path.join(LAYERS, f"{card['id']}.png")
        layer.save(layer_path)
        composite(layer).convert("RGB").save(os.path.join(PREVIEW, f"{card['id']}_composite.png"))
        rendered.append(card["id"])
    make_thumbnail()
    print("Rendered layers:", len(rendered))
    print("Checked numbers (card, id, graphic expected, CSV value):")
    for row in USED:
        if row[2] is not None:
            print(f"  {row[0]:<28} id {row[1]:<3} expected {row[2]:<6} csv {row[3]}")
    print("Token-only numbers (CSV):", sorted({r[1] for r in USED if r[2] is None}))


if __name__ == "__main__":
    main()
