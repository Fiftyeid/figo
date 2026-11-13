"""بناء الغلاف الكامل (خلفي + كعب + أمامي) بمواصفات KDP + نسخة إثبات بالخطوط الإرشادية."""
from __future__ import annotations

from pathlib import Path

from reportlab.lib.colors import Color, HexColor, white
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

from . import book, config as C, kdp, textkit as T

GUIDE = Color(0.55, 0.55, 0.58)
GUIDE_RED = Color(0.75, 0.25, 0.2)


def _lum(hex_color: str) -> float:
    h = (hex_color or "#ffffff").lstrip("#")
    if len(h) == 3:
        h = "".join(ch * 2 for ch in h)
    try:
        r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    except Exception:
        return 1.0
    return 0.299 * r + 0.587 * g + 0.114 * b


def _txt_color(bg: str) -> Color:
    return Color(0.06, 0.05, 0.05) if _lum(bg) > 0.5 else Color(0.97, 0.96, 0.94)


def _plate(c, x, y, w, h, bg, accent, radius=10):
    c.setFillColor(white)
    c.setStrokeColor(accent)
    c.setLineWidth(1.1)
    c.roundRect(x, y, w, h, radius, stroke=1, fill=1)


def build_cover(project: dict, out_path: str | Path, proof: bool = False) -> dict:
    T.register_fonts()
    plan = kdp.plan_pages(project)
    total = len(plan)
    geo = kdp.cover_geometry(total, project.get("trim", "8.5x11"), project.get("paper", "white"))
    W, H = geo["width"] * inch, geo["height"] * inch
    cov = project.get("cover", {})
    bg = cov.get("background", "#F6F1E7")
    accent = HexColor(cov.get("accent", "#B4562F"))
    ink_c = _txt_color(bg)
    back, spine, front = geo["back"], geo["spine_box"], geo["front"]

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(out_path), pagesize=(W, H), pageCompression=1)
    c.setTitle(f'{project.get("title","Coloring Book")} — cover')
    c.setAuthor(project.get("author", ""))
    c.setCreator(f"{C.APP_NAME} ({C.APP_NAME_LATIN}) {C.APP_VERSION}")

    # خلفية تمتد إلى النزف بالكامل
    c.setFillColor(HexColor(bg))
    c.rect(0, 0, W, H, stroke=0, fill=1)

    # إطار داخلي موحّد على الغلاف الأمامي والخلفي
    inset = 0.30 * inch
    c.setStrokeColor(accent)
    c.setLineWidth(1.2)
    for box in (back, front):
        c.rect(box["x"] * inch + inset, box["y"] * inch + inset,
               box["w"] * inch - 2 * inset, box["h"] * inch - 2 * inset, stroke=1, fill=0)
    c.setLineWidth(0.4)
    for box in (back, front):
        c.rect(box["x"] * inch + inset + 5, box["y"] * inch + inset + 5,
               box["w"] * inch - 2 * inset - 10, box["h"] * inch - 2 * inset - 10, stroke=1, fill=0)

    # ------------------------------------------------------------------ أمامي
    fx, fy = front["x"] * inch, front["y"] * inch
    fw, fh = front["w"] * inch, front["h"] * inch
    pad = 0.42 * inch
    title = project.get("title") or "Coloring Book"
    subtitle = project.get("subtitle") or ""
    author = project.get("author") or ""
    lang_ar = (project.get("language") or "ar").startswith("ar")
    label = "كتاب تلوين" if lang_ar else "COLORING BOOK"

    T.draw_line(c, fx + fw / 2, fy + fh - pad - 0.28 * inch, label.upper(),
                T.FONT_REGULAR, 10, accent, "center", char_space=0 if lang_ar else 2.6)
    c.setStrokeColor(accent)
    c.setLineWidth(1.2)
    c.line(fx + fw / 2 - 0.5 * inch, fy + fh - pad - 0.42 * inch,
           fx + fw / 2 + 0.5 * inch, fy + fh - pad - 0.42 * inch)

    title_font = T.FONT_BOLD if (lang_ar or not T.is_rtl(title)) else T.FONT_SERIF_BOLD
    tsize = book.fit_size(title, fw - 2 * pad - 0.3 * inch, title_font, 46, 24, max_lines=3)
    tlines = T.wrap(title, title_font, tsize, fw - 2 * pad)
    ty = fy + fh - pad - 0.95 * inch
    for line in tlines:
        T.draw_line(c, fx + fw / 2, ty, line, title_font, tsize, ink_c, "center")
        ty -= tsize * 1.18

    rule_y = ty + tsize * 0.28
    c.setStrokeColor(accent)
    c.setLineWidth(2.2)
    c.line(fx + fw / 2 - 0.55 * inch, rule_y, fx + fw / 2 + 0.55 * inch, rule_y)

    if subtitle:
        sub_font = T.FONT_REGULAR
        ssize = book.fit_size(subtitle, fw - 2 * pad, sub_font, 16, 10, max_lines=2)
        sy = rule_y - 0.30 * inch
        for line in T.wrap(subtitle, sub_font, ssize, fw - 2 * pad):
            T.draw_line(c, fx + fw / 2, sy, line, sub_font, ssize, ink_c, "center")
            sy -= ssize * 1.35
        plate_top = sy - 0.10 * inch
    else:
        plate_top = rule_y - 0.36 * inch

    # لوحة بيضاء لرسمة الغلاف
    plate_bottom = fy + 1.55 * inch
    px = fx + pad + 0.18 * inch
    pw = fw - 2 * (pad + 0.18 * inch)
    ph = max(1.2 * inch, plate_top - plate_bottom)
    _plate(c, px, plate_bottom, pw, ph, bg, accent, radius=8)
    page = None
    cover_id = (cov or {}).get("cover_page_id")
    pages = [p for p in project.get("pages", []) if p.get("status") == "ready"]
    if cover_id:
        page = next((p for p in pages if p["id"] == cover_id), None)
    if page is None and pages:
        page = pages[0]
    if page is not None:
        try:
            art = book.art_for(project, page, (pw / inch) - 0.40, (ph / inch) - 0.40, persist=False)
            aw, ah = art.size
            target_w = (pw - 0.40 * inch)
            target_h = (ph - 0.40 * inch)
            ratio = min(target_w / aw, target_h / ah)
            dw, dh = aw * ratio, ah * ratio
            c.drawImage(ImageReader(art), px + (pw - dw) / 2, plate_bottom + (ph - dh) / 2,
                        width=dw, height=dh, preserveAspectRatio=False)
        except Exception:
            pass

    if author:
        T.draw_line(c, fx + fw / 2, fy + 0.92 * inch, author, T.FONT_BOLD, 17, ink_c, "center")
        c.setStrokeColor(accent)
        c.setLineWidth(0.8)
        c.line(fx + fw / 2 - 0.4 * inch, fy + 0.76 * inch, fx + fw / 2 + 0.4 * inch, fy + 0.76 * inch)
        T.draw_line(c, fx + fw / 2, fy + 0.55 * inch,
                    "صفحات تلوين للاسترخاء والإبداع" if lang_ar else "Relax. Create. Color.",
                    T.FONT_REGULAR, 9, ink_c, "center")

    # ------------------------------------------------------------------- كعب
    sx = spine["x"] * inch
    sw = spine["w"] * inch
    c.setFillColor(accent)
    c.rect(sx, 0, max(sw, 0.2), H, stroke=0, fill=1)
    if geo["spine_text_allowed"] and sw > 0.25 * inch:
        c.setFillColor(accent)
        c.rect(sx, 0, sw, H, stroke=0, fill=1)
        c.saveState()
        c.translate(sx + sw / 2, H / 2)
        c.rotate(90)
        spine_label = title if len(title) <= 42 else title[:40] + "…"
        T.draw_line(c, 0, 4, spine_label, T.FONT_BOLD, 11, white, "center")
        if author:
            T.draw_line(c, 0, -10, author, T.FONT_REGULAR, 8.5, white, "center")
        c.restoreState()
    else:
        # كعب ملوّن بدون نص (KDP: لا نص على الكعب قبل 80 صفحة)
        c.setFillColor(accent)
        c.rect(sx, geo["spine_box"]["y"] * inch, max(sw, 1.0), geo["spine_box"]["h"] * inch,
               stroke=0, fill=1)

    # --------------------------------------------------------------- خلفي
    bx, by = back["x"] * inch, back["y"] * inch
    bw, bh = back["w"] * inch, back["h"] * inch
    bpad = 0.48 * inch
    bcx = bx + bpad
    bcw = bw - 2 * bpad

    rtl = T.is_rtl(title) or lang_ar
    ax = bcx + bcw if rtl else bcx
    T.draw_line(c, ax, by + bh - bpad - 0.18 * inch, title, T.FONT_BOLD, 15, ink_c,
                "right" if rtl else "left")
    c.setStrokeColor(accent)
    c.setLineWidth(1.2)
    c.line(bcx, by + bh - bpad - 0.32 * inch, bcx + 1.6 * inch, by + bh - bpad - 0.32 * inch)

    blurb = (cov.get("blurb") or "").strip()
    if not blurb:
        n = len(pages)
        blurb = (
            f"{n} رسمة تلوين كبيرة وواضحة، مصممة لتناسب يد الطفل وتشعل خياله. "
            "طباعة عالية الجودة بخطوط سميكة يسهل ملؤها بالألوان، مع صفحة فارغة بعد كل "
            "رسمة لتجنّب تسرّب الألوان إلى الرسومات الأخرى."
            if lang_ar
            else f"{n} big, bold coloring pages designed for small hands and big imaginations. "
                 "Thick clean outlines make coloring easy, and single-sided pages prevent "
                 "bleed-through onto the next drawing."
        )
    y = by + bh - bpad - 0.72 * inch
    y = T.draw_paragraph(c, blurb, bcx, y, bcw, T.FONT_REGULAR, 10.5, 16, ink_c,
                         "right" if T.is_rtl(blurb) else "left")

    # لمحة من الداخل: لوحتان مصغّرتان تملآن المساحة
    plate_bottom = by + 3.45 * inch
    plate_top = y - 0.16 * inch
    look_h = min(5.2 * inch, plate_top - plate_bottom)
    if look_h > 1.6 * inch and pages:
        T.draw_line(c, ax - 4, plate_top + 0.10 * inch, "لمحة من الداخل" if lang_ar else "LOOK INSIDE",
                    T.FONT_REGULAR, 8.5, accent, "right" if rtl else "left",
                    char_space=0 if lang_ar else 1.8)
        gap = 0.18 * inch
        cw = (bcw - gap) / 2
        py = plate_top - look_h
        for i, pg in enumerate(pages[:2]):
            cell_x = bcx + i * (cw + gap)
            _plate(c, cell_x, py, cw, look_h, bg, accent, radius=6)
            try:
                inner_w = (cw - 0.20 * inch) / inch
                inner_h = (look_h - 0.20 * inch) / inch
                art = book.art_for(project, pg, inner_w, inner_h, persist=False)
            except Exception:
                art = None
            if art is not None:
                aw, ah = art.size
                ratio = min((cw - 0.20 * inch) / aw, (look_h - 0.20 * inch) / ah)
                dw, dh = aw * ratio, ah * ratio
                c.drawImage(ImageReader(art), cell_x + (cw - dw) / 2, py + (look_h - dh) / 2,
                            width=dw, height=dh, preserveAspectRatio=False)

    # مزايا الكتاب
    bullets = (
        [f"{len(pages)} صفحة تلوين منفردة الوجه", "خطوط سميكة مناسبة للأطفال",
         "مناسب للأقلام الملونة والخشبية"]
        if lang_ar else
        [f"{len(pages)} single-sided coloring pages", "Extra-thick outlines for kids",
         "Works with crayons, markers and pencils"]
    )
    yb = by + 3.15 * inch
    c.setStrokeColor(accent)
    c.setLineWidth(1.0)
    c.line(bcx, yb + 16, bcx + bcw, yb + 16)
    for b in bullets:
        if rtl:
            T.draw_line(c, ax - 16, yb, b, T.FONT_REGULAR, 10, ink_c, "right")
            c.setFillColor(accent)
            c.circle(ax - 4, yb + 3.2, 2.0, stroke=0, fill=1)
        else:
            c.setFillColor(accent)
            c.circle(bcx + 3, yb + 3.2, 2.0, stroke=0, fill=1)
            T.draw_line(c, bcx + 12, yb, b, T.FONT_REGULAR, 10, ink_c, "left")
        yb -= 19

    # لمسة ختامية أسفل يسار الظهر
    gift = ("هدية مثالية للأطفال من 3 إلى 8 سنوات" if lang_ar
            else "A perfect gift for ages 3-8")
    gy = by + 2.10 * inch
    T.draw_line(c, bcx, gy, gift, T.FONT_BOLD, 9.5, accent, "left")
    c.setStrokeColor(accent)
    c.setLineWidth(0.6)
    c.line(bcx, gy - 7, bcx + T.string_width(gift, T.FONT_BOLD, 9.5), gy - 7)

    # توقيع أسفل يسار الظهر
    T.draw_line(c, bcx, by + 0.62 * inch,
                f'{C.APP_NAME} · {C.APP_NAME_LATIN}' if lang_ar else f"{C.APP_NAME_LATIN} Studio",
                T.FONT_REGULAR, 8, ink_c, "left")

    # منطقة الباركود: بيضاء تمامًا وخالية من أي عنصر
    bar = geo["barcode"]
    c.setFillColor(white)
    c.rect(bar["x"] * inch, bar["y"] * inch, bar["w"] * inch, bar["h"] * inch, stroke=0, fill=1)

    # ------------------------------------------------------------- الإثبات
    if proof:
        _draw_guides(c, geo, project)

    c.showPage()
    c.save()
    return {
        "file": str(out_path),
        "width": geo["width"],
        "height": geo["height"],
        "spine": geo["spine"],
        "geometry": geo,
        "proof": proof,
    }


def _dashed_rect(c, x, y, w, h, color=GUIDE, dash=(4, 3), width=0.6):
    c.saveState()
    c.setStrokeColor(color)
    c.setLineWidth(width)
    c.setDash(dash)
    c.rect(x, y, w, h, stroke=1, fill=0)
    c.restoreState()


def _draw_guides(c, geo: dict, project: dict):
    i = inch
    # حدود القطع
    for box in (geo["back"], geo["spine_box"], geo["front"]):
        _dashed_rect(c, box["x"] * i, box["y"] * i, box["w"] * i, box["h"] * i, GUIDE, (3, 3), 0.5)
    # منتصف الكعب
    sx = geo["spine_box"]["x"] * i
    sw = geo["spine_box"]["w"] * i
    c.setStrokeColor(GUIDE_RED)
    c.setLineWidth(0.5)
    c.line(sx + sw / 2, 0, sx + sw / 2, geo["height"] * i)

    # المنطقة الآمنة (0.25 بوصة داخل القطع)
    safe = 0.25 * i
    for box in (geo["back"], geo["front"]):
        _dashed_rect(c, box["x"] * i + safe, box["y"] * i + safe,
                     box["w"] * i - 2 * safe, box["h"] * i - 2 * safe, GUIDE, (6, 4), 0.5)

    # الباركود
    bar = geo["barcode"]
    c.setFillColor(Color(1, 1, 1, alpha=0.85))
    c.setStrokeColor(GUIDE_RED)
    c.setLineWidth(0.8)
    c.setDash(3, 2)
    c.rect(bar["x"] * i, bar["y"] * i, bar["w"] * i, bar["h"] * i, stroke=1, fill=1)
    c.setDash()
    T.draw_line(c, bar["x"] * i + bar["w"] * i / 2, bar["y"] * i + bar["h"] * i / 2 + 4,
                'منطقة الباركود 2" × 1.2" — تُترك فارغة', T.FONT_REGULAR, 6.5, GUIDE_RED, "center")
    T.draw_line(c, bar["x"] * i + bar["w"] * i / 2, bar["y"] * i + bar["h"] * i / 2 - 8,
                "BARCODE CLEAR ZONE", T.FONT_REGULAR, 6, GUIDE_RED, "center")

    # بيانات على الهامش النازف
    c.setFillColor(GUIDE)
    T.draw_line(c, 6, geo["height"] * i - 12,
                f'KDP · {geo["width"]:.3f}" × {geo["height"]:.3f}" · spine {geo["spine"]:.3f}" · '
                f'{project.get("trim")} · bleed 0.125"',
                T.FONT_REGULAR, 6.5, GUIDE, "left")
    T.draw_line(c, sx + sw / 2, 10, f"spine {geo['spine']:.3f}\"", T.FONT_REGULAR, 6, GUIDE_RED, "center")
