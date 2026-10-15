# -*- coding: utf-8 -*-
"""Companion files: script (markdown), Arabic subtitles (SRT), YouTube chapters/description, thumbnail."""
import json, os, re
from PIL import Image, ImageFilter, ImageDraw

from common import *
from script_data import SECTIONS
from mapgen import render_view, mapdata

OUT = os.path.join(ROOT, "output")
os.makedirs(OUT, exist_ok=True)
tl = json.load(open(os.path.join(BUILD, "timeline.json"), encoding="utf-8"))
SEC = {s["id"]: s for s in tl["sections"]}


def ts_srt(t):
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def ts_yt(t):
    t = int(t)
    m, s = divmod(t, 60)
    return f"{m:02d}:{s:02d}"


def c2t(sec, ci):
    cm = sec["cmap"]
    for k in range(len(cm) - 1):
        if cm[k][0] <= ci <= cm[k + 1][0]:
            c0, t0 = cm[k]
            c1, t1 = cm[k + 1]
            return t0 + (t1 - t0) * (ci - c0) / max(1, c1 - c0)
    return cm[-1][1]


def subtitles():
    cues = []
    for sec in tl["sections"]:
        text = sec["text"]
        # sentence chunks, then split long ones on commas
        parts = []
        for m in re.finditer(r"[^.!?؟…:]+[.!?؟…:]*", text):
            chunk = m.group(0)
            if len(chunk.strip()) < 2:
                continue
            if len(chunk) > 95:
                sub, pos = [], m.start()
                acc = ""
                acc_start = m.start()
                for piece in re.finditer(r"[^،,]+[،,]?", chunk):
                    if len(acc) + len(piece.group(0)) > 80 and acc.strip():
                        parts.append((acc_start, acc))
                        acc = ""
                        acc_start = m.start() + piece.start()
                    acc += piece.group(0)
                if acc.strip():
                    parts.append((acc_start, acc))
            else:
                parts.append((m.start(), chunk))
        for st, chunk in parts:
            s = chunk.strip()
            lead = len(chunk) - len(chunk.lstrip())
            t0 = c2t(sec, st + lead)
            t1 = c2t(sec, st + len(chunk.rstrip()))
            cues.append([t0, t1, s])
    # tidy: min duration, no overlap
    for i, c in enumerate(cues):
        c[1] = max(c[1], c[0] + 1.0)
        if i + 1 < len(cues):
            c[1] = min(c[1] + 0.25, cues[i + 1][0] - 0.04)
    with open(os.path.join(OUT, "subtitles_ar.srt"), "w", encoding="utf-8") as f:
        for i, (a, b, s) in enumerate(cues, 1):
            # wrap to two lines if long
            if len(s) > 48:
                words = s.split()
                half, acc, l1 = len(s) / 2, 0, []
                for w_ in words:
                    if acc + len(w_) > half and l1:
                        break
                    l1.append(w_)
                    acc += len(w_) + 1
                s = " ".join(l1) + "\n" + " ".join(words[len(l1):])
            f.write(f"{i}\n{ts_srt(a)} --> {ts_srt(b)}\n{s}\n\n")
    return len(cues)


def chapters_and_description():
    lines = ["00:00 المقدمة"]
    names = {s["id"]: s["title"] for s in SECTIONS}
    for s in tl["sections"][1:]:
        title = names[s["id"]]
        if s["id"] == "outro":
            title = "الخلاصة + معلومة أخيرة"
        lines.append(f"{ts_yt(max(0, s['start'] - 0.3))} {title}")
    desc = f"""# عنوان مقترح
ليه محافظات مصر اتسمّت بالأسماء دي؟ | ٢٧ محافظة .. ٢٧ حكاية

# الوصف
تخيّل إن فيه محافظة اسمها جاي من كوكب، ومحافظة اسمها معناه «البحر» ومفيهاش بحر، ومحافظة اسمها ممكن يكون جاي من غلطة في دفاتر المساحة!
في الفيديو ده بنلف مصر كلها، محافظة محافظة، ونعرف حكاية اسم كل واحدة فيهم: من الفرعوني للقبطي لليوناني للعربي، ومن الحكام والملوك للجغرافيا والأساطير.

## فصول الفيديو
""" + "\n".join(lines) + """

## مصادر للاستزادة
- محمد رمزي — القاموس الجغرافي للبلاد المصرية من عهد قدماء المصريين إلى سنة ١٩٤٥
- المقريزي — المواعظ والاعتبار بذكر الخطط والآثار
- ويكيبيديا (عربي/إنجليزي): صفحات محافظات مصر
- بيانات الخرائط: Natural Earth (ملكية عامة)

## وسوم مقترحة
#محافظات_مصر #أصل_الأسماء #تاريخ_مصر #معلومات #مصر
"""
    open(os.path.join(OUT, "youtube_description_ar.md"), "w", encoding="utf-8").write(desc)
    return lines


def script_markdown():
    names = {s["id"]: s["title"] for s in SECTIONS}
    md = ["# سكريبت التعليق الصوتي — ليه محافظات مصر اتسمّت بالأسماء دي؟", "",
          f"المدة النهائية: {ts_yt(tl['duration'])} دقيقة — {len(SECTIONS)} مقطع — اللهجة: مصري عامي", ""]
    for s in SECTIONS:
        sec = SEC[s["id"]]
        md.append(f"## {names[s['id']]}  `({ts_yt(sec['start'])} → {ts_yt(sec['end'])})`")
        md.append("")
        md.append(s["text"].replace("\n", "\n\n"))
        md.append("")
    open(os.path.join(ROOT, "script", "script_ar.md"), "w", encoding="utf-8").write("\n".join(md))


def thumbnail():
    TW, TH = 1280, 720
    bg = ken_burns_source(os.path.join(ASSETS, "images", "intro_mars_desert.jpg"), zoom_max=1.0, darken=0.35)
    bg = bg.resize((TW, TH), Image.LANCZOS).convert("RGBA")
    # colourful governorates map on the left
    r = render_view(30.8, 26.9, 15.0, size=(760, 720), ss=2)
    md = mapdata()
    base = r["base"].copy()
    d = ImageDraw.Draw(base)
    pal = [(255, 201, 60), (46, 196, 182), (255, 127, 80), (120, 160, 255), (186, 160, 255), (52, 195, 143),
           (255, 160, 200)]
    mask = Image.new("L", base.size, 0)
    dm = ImageDraw.Draw(mask)
    for k, (code, g) in enumerate(sorted(md.govs.items())):
        for ext, holes in r["view"].poly_px(g["geom"], 1):
            if len(ext) >= 3:
                d.polygon(ext, fill=tuple(int(v * 0.9) for v in pal[k % len(pal)]), outline=(255, 255, 255))
                dm.polygon(ext, fill=255)
    mask = mask.filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.GaussianBlur(1.5))
    egypt = base.convert("RGBA")
    egypt.putalpha(mask)
    egypt = glow(egypt, radius=18, strength=0.9, color=(255, 200, 80))
    bg.alpha_composite(egypt, (-60, -36))
    # text block (right)
    t1 = text_image("أسماء المحافظات", "display", 100, WHITE, stroke=8, stroke_fill=INK, shadow=10)
    t2 = glow(text_image("جت منين؟!", "display", 190, GOLD, stroke=10, stroke_fill=INK, shadow=12), 26, 0.9,
              (255, 150, 20))
    paste_center(bg, t1, 905, 150)
    paste_center(bg, t2, 905, 320)
    chips = [("الفيوم = البحر؟!", (46, 196, 182)), ("القاهرة = المريخ؟!", CORAL), ("بني سويف = غلطة!", (186, 160, 255))]
    y = 490
    for txt, col in chips:
        c = chip(txt, col, "black", 46)
        paste_center(bg, c, 905, y)
        y += c.height + 16
    badge = chip("٢٧ محافظة", GOLD, "black", 44)
    paste_center(bg, badge, 140, 660)
    bg.convert("RGB").save(os.path.join(OUT, "thumbnail.jpg"), quality=92)


if __name__ == "__main__":
    print("cues:", subtitles())
    print("\n".join(chapters_and_description()))
    script_markdown()
    thumbnail()
    print("done")
