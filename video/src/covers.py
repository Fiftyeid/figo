# -*- coding: utf-8 -*-
"""
Covers / thumbnails (1080x1920) for the 8 Shorts/Reels.

Original vertical art (assets/covers/<id>.jpg, same painterly look as the long video)
+ series chip + the governorate name in gold + the hook in a coloured pill, styled like the
long video's thumbnail.  Everything that matters sits inside the centre crops the platforms use
for grids/browse (4:5 on YouTube browse surfaces, 3:4 on the Instagram/TikTok profile grid)
and above the bottom band where the Shorts shelf prints the title.

  python3 covers.py              -> output/shorts_covers/NN_<id>.jpg (+ build/qa/covers_*.jpg)
  python3 covers.py <id> ...     -> only those

The same image is appended as the last frames of every Short (shorts.py), so it can be picked
as the YouTube thumbnail from the frame selector on channels that can't upload one yet.
"""
import os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from common import ROOT, ASSETS, BUILD, GOLD, WHITE, INK, TEAL, CORAL, text_image, chip, glow, grade_image, clamp

VW, VH = 1080, 1920
SRC = os.path.join(ASSETS, "covers")
OUT = os.path.join(ROOT, "output", "shorts_covers")
QA = os.path.join(BUILD, "qa")
LAV = (186, 160, 255)
BLUE = (93, 173, 226)
SERIES = "أصل أسماء محافظات مصر"

# name (gold), hook (pill), pill colour, vertical layout (chip / name / pill centres), art offset
COVERS = {
    "cairo":    dict(name="القاهرة", hook="اتسمّت على كوكب؟!", color=CORAL),
    "benisuef": dict(name="بني سويف", hook="اسمها غلطة في دفتر؟!", color=LAV),
    "faiyum":   dict(name="الفيوم", hook="اسمها يعني «البحر»!", color=TEAL),
    "redsea":   dict(name="البحر الأحمر", hook="وهو لونه أزرق؟!", color=BLUE),
    "luxor":    dict(name="الأقصر", hook="معابد.. ولا قصور؟!", color=CORAL),
    "giza":     dict(name="الجيزة", hook="الأهرامات\nأقدم من اسمها!", color=TEAL),
    "sohag":    dict(name="سوهاج", hook="حكاية «سو هاج»\nحقيقة ولا نكتة؟", color=LAV),
    "dakahlia": dict(name="الدقهلية", hook="اسمها جاي من دمياط؟!", color=CORAL, zoom=1.07, dy=-70),
}
Y_CHIP, Y_NAME, Y_PILL = 336, 526, 734     # pill centre for one line; +52 per extra line


def background(sid, dy=0, zoom=1.0):
    im = Image.open(os.path.join(SRC, sid + ".jpg")).convert("RGB")
    s = max(VW / im.width, VH / im.height) * zoom
    im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    x0 = (im.width - VW) // 2
    y0 = int(clamp((im.height - VH) // 2 + dy, 0, im.height - VH))
    im = im.crop((x0, y0, x0 + VW, y0 + VH))
    im = im.filter(ImageFilter.UnsharpMask(radius=2, percent=55, threshold=2))
    im = grade_image(im, contrast=1.05, sat=1.06)
    # dark band behind the text at the top + a light one at the bottom (Shorts shelf title)
    y = np.arange(VH, dtype=np.float32)
    top = np.clip(1 - (y - 140) / 980, 0, 1) ** 1.5 * 0.80
    bot = np.clip((y - 1480) / 440, 0, 1) ** 1.6 * 0.42
    a = np.maximum(top, bot)[:, None, None]
    arr = np.asarray(im).astype(np.float32) * (1 - a) + np.array(INK, np.float32) * a
    return Image.fromarray(arr.clip(0, 255).astype(np.uint8)).convert("RGBA")


def name_image(name, max_w=1000, size=280):
    while True:
        im = text_image(name, "display", size, GOLD, stroke=11, stroke_fill=INK, shadow=14)
        if im.width <= max_w or size <= 150:
            break
        size -= 8
    return glow(im, radius=28, strength=0.55)


def pill(text, color, max_w=990, size=96, padx=46, pady=12):
    """Rounded label like the long video's thumbnail chips; '\\n' in text = extra line."""
    lines = text.split("\n")
    while True:
        ims = [text_image(l, "black", size, INK, pad=4) for l in lines]
        w = max(i.width for i in ims) + 2 * padx
        if w <= max_w or size <= 60:
            break
        size -= 4
    pitch = int(size * 1.36)
    hmax = max(i.height for i in ims)
    h = pitch * (len(ims) - 1) + hmax + 2 * pady
    p = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(p).rounded_rectangle([0, 0, w - 1, h - 1], radius=min(h // 2, (hmax + 2 * pady) // 2),
                                        fill=color + (255,))
    for k, t in enumerate(ims):
        p.alpha_composite(t, ((w - t.width) // 2, pady + k * pitch + (hmax - t.height) // 2 - 2))
    m = 40
    out = Image.new("RGBA", (p.width + 2 * m, p.height + 2 * m), (0, 0, 0, 0))
    sh = Image.new("RGBA", p.size, (0, 0, 0, 255))
    sh.putalpha(p.getchannel("A").point(lambda v: int(v * 0.6)))
    out.alpha_composite(sh, (m + 6, m + 14))
    out = out.filter(ImageFilter.GaussianBlur(14))
    out.alpha_composite(p, (m, m))
    return out


def series_chip():
    c = chip(SERIES, GOLD, kind="black", size=40, fg=INK, padx=30, pady=4)
    m = 24
    out = Image.new("RGBA", (c.width + 2 * m, c.height + 2 * m), (0, 0, 0, 0))
    sh = Image.new("RGBA", c.size, (0, 0, 0, 255))
    sh.putalpha(c.getchannel("A").point(lambda v: int(v * 0.5)))
    out.alpha_composite(sh, (m, m + 8))
    out = out.filter(ImageFilter.GaussianBlur(10))
    out.alpha_composite(c, (m, m))
    return out


def put(base, layer, cy):
    base.alpha_composite(layer, ((VW - layer.width) // 2, int(cy - layer.height / 2)))


def make_cover(sid):
    c = COVERS[sid]
    im = background(sid, c.get("dy", 0), c.get("zoom", 1.0))
    put(im, series_chip(), c.get("y_chip", Y_CHIP))
    put(im, name_image(c["name"]), c.get("y_name", Y_NAME))
    put(im, pill(c["hook"], c["color"]), c.get("y_pill", Y_PILL + 52 * c["hook"].count("\n")))
    return im.convert("RGB")


def out_path(sid):
    from shorts import index_of
    return os.path.join(OUT, f"{index_of(sid):02d}_{sid}.jpg")


def overview(ids, path=os.path.join(OUT, "all_covers.jpg"), tw=360, th=640, gap=12):
    """All covers side by side (shown at the top of output/shorts_ar.md)."""
    cols = 4
    rows = (len(ids) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * tw + (cols + 1) * gap, rows * th + (rows + 1) * gap), INK)
    for k, sid in enumerate(ids):
        im = Image.open(out_path(sid)).convert("RGB").resize((tw, th), Image.LANCZOS)
        sheet.paste(im, (gap + (k % cols) * (tw + gap), gap + (k // cols) * (th + gap)))
    sheet.save(path, quality=86, optimize=True)
    return path


def qa_sheet(ids):
    """Contact sheet with the crop guides: 4:5 (YouTube browse), 3:4 (IG/TikTok grid), Shorts-shelf title band."""
    tw, th = 270, 480
    sheet = Image.new("RGB", (tw * 4, th * ((len(ids) + 3) // 4)), (30, 30, 30))
    for k, sid in enumerate(ids):
        im = Image.open(out_path(sid)).convert("RGB")
        d = ImageDraw.Draw(im)
        for h, col in ((1350, (255, 0, 0)), (1440, (0, 255, 0))):
            y0 = (VH - h) // 2
            d.rectangle([2, y0, VW - 3, y0 + h], outline=col, width=5)
        d.rectangle([0, int(VH * 0.80), VW, VH], outline=(0, 160, 255), width=5)
        sheet.paste(im.resize((tw, th), Image.LANCZOS), ((k % 4) * tw, (k // 4) * th))
    os.makedirs(QA, exist_ok=True)
    p = os.path.join(QA, "covers_guides.jpg")
    sheet.save(p, quality=85)
    return p


if __name__ == "__main__":
    from shorts import SHORTS
    ids = sys.argv[1:] or [s["id"] for s in SHORTS]
    os.makedirs(OUT, exist_ok=True)
    for sid in ids:
        p = out_path(sid)
        make_cover(sid).save(p, quality=92, subsampling=0, optimize=True)
        print(p, os.path.getsize(p) // 1024, "KB")
    print(qa_sheet(ids))
    if len(ids) == len(SHORTS):
        print(overview(ids))
