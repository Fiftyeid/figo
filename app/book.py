"""بناء ملف الداخل (Interior PDF) الجاهز للطباعة على KDP."""
from __future__ import annotations

from pathlib import Path

from PIL import Image
from reportlab.lib.colors import Color, HexColor, black
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

from . import config as C
from . import kdp, lineart, store, textkit as T

INK = black
MUTED = Color(0.25, 0.25, 0.25)

COPY = {
    "ar": {
        "label": "كتاب تلوين",
        "belongs": "هذا الكتاب ملك",
        "name_line": "الاسم",
        "rights": "جميع الحقوق محفوظة.",
        "edition": "الطبعة الأولى",
        "notice": "هذا الكتاب مخصّص للاستخدام الشخصي. يُمنع نسخ الصفحات أو توزيعها "
                  "أو استخدامها تجاريًا دون إذن كتابي من المؤلف.",
        "printed": "طُبع عند الطلب بواسطة Amazon KDP.",
        "by": "بقلم",
        "pages_of_fun": "صفحة من المرح والتلوين",
    },
    "en": {
        "label": "COLORING BOOK",
        "belongs": "This book belongs to",
        "name_line": "Name",
        "rights": "All rights reserved.",
        "edition": "First Edition",
        "notice": "This book is for personal use only. No part of this book may be "
                  "reproduced or distributed for commercial purposes without written "
                  "permission from the author.",
        "printed": "Printed on demand by Amazon KDP.",
        "by": "by",
        "pages_of_fun": "pages of fun to color",
    },
}


def _copy(project: dict) -> dict:
    return COPY.get((project.get("language") or "ar")[:2], COPY["en"])


def _font_for(text: str, bold: bool = False, serif: bool = False) -> str:
    if T.is_rtl(text) or not serif:
        return T.FONT_BOLD if bold else T.FONT_REGULAR
    return T.FONT_SERIF_BOLD if bold else T.FONT_SERIF


def fit_size(text: str, width: float, font: str, start: float, minimum: float, max_lines: int = 3) -> float:
    size = start
    while size > minimum:
        if len(T.wrap(text, font, size, width)) <= max_lines:
            return size
        size -= 1
    return minimum


# ---------------------------------------------------------------------------
# الصور
# ---------------------------------------------------------------------------
def art_for(project: dict, page: dict, box_w_in: float, box_h_in: float, persist: bool = True) -> Image.Image:
    """يعيد صورة الصفحة بالمقاس المطلوب بالبكسل (300 DPI).

    لا نكتب فوق ملف الرسمة الأصلي إلا إذا كان المقاس المطلوب هو مقاس صندوق
    المحتوى القياسي (كي لا تُستبدل الرسمة الكبيرة بنسخة مصغّرة للغلاف).
    """
    target = (max(1, int(round(box_w_in * C.DPI))), max(1, int(round(box_h_in * C.DPI))))
    canonical = tuple(
        max(1, int(round(v * C.DPI)))
        for v in kdp.art_box_inches(project, bool((page.get("caption") or "").strip()))
    )
    paths = store.page_paths(project["id"], page["id"])
    if paths["art"].exists():
        try:
            img = Image.open(paths["art"])
            img.load()
            if img.size == target:
                return img.convert("1", dither=Image.Dither.NONE)
        except Exception:
            pass
    if not paths["source"].exists():
        raise FileNotFoundError(f"صورة الصفحة {page['id']} مفقودة")
    src = lineart.open_image(paths["source"])
    s = page.get("settings", {})
    detail = C.STYLES.get(project.get("style", "medium"), C.STYLES["medium"])["detail"]
    art = lineart.to_line_art(
        src,
        thickness=int(s.get("thickness", 2)),
        threshold=int(s.get("threshold", 150)),
        mode=s.get("mode", "auto"),
        detail=detail,
    )
    composed = lineart.compose_page(art, target[0], target[1])
    if persist and target == canonical:
        paths["art"].parent.mkdir(parents=True, exist_ok=True)
        composed.save(paths["art"], optimize=True)
    return composed


# ---------------------------------------------------------------------------
# صفحات
# ---------------------------------------------------------------------------
def _title_page(c, project: dict, geo: dict) -> None:
    txt = _copy(project)
    box = geo["box"]
    x, y, w, h = box["x"] * inch, box["y"] * inch, box["w"] * inch, box["h"] * inch
    T.frame(c, x, y, w, h, inset=0.10 * inch, width=1.2)
    T.frame(c, x, y, w, h, inset=0.22 * inch, width=0.5)

    title = project.get("title") or "Coloring Book"
    subtitle = project.get("subtitle") or ""
    author = project.get("author") or ""

    # شريط علوي
    label = txt["label"]
    T.draw_line(c, x + w / 2, y + h - 0.72 * inch, label.upper(), T.FONT_REGULAR, 10, INK, "center",
                char_space=0 if T.is_rtl(label) else 2.4)
    T.rule(c, x + w / 2 - 0.55 * inch, y + h - 0.90 * inch, x + w / 2 + 0.55 * inch, 0.8)

    title_font = _font_for(title, bold=True)
    size = fit_size(title, w - 1.1 * inch, title_font, 46, 24, max_lines=3)
    lines = T.wrap(title, title_font, size, w - 1.1 * inch)
    block_h = len(lines) * size * 1.22
    ty = y + h * 0.62 + block_h / 2
    for line in lines:
        T.draw_line(c, x + w / 2, ty, line, title_font, size, INK, "center")
        ty -= size * 1.22

    base = y + h * 0.62 - block_h / 2 - 0.28 * inch
    T.rule(c, x + w / 2 - 0.35 * inch, base, x + w / 2 + 0.35 * inch, 1.6)

    if subtitle:
        sub_font = _font_for(subtitle)
        sub_size = fit_size(subtitle, w - 1.6 * inch, sub_font, 19, 12, max_lines=2)
        sy = base - 0.46 * inch
        for line in T.wrap(subtitle, sub_font, sub_size, w - 1.6 * inch):
            T.draw_line(c, x + w / 2, sy, line, sub_font, sub_size, MUTED, "center")
            sy -= sub_size * 1.4

    if author:
        af = _font_for(author, bold=True)
        T.draw_line(c, x + w / 2, y + 0.95 * inch, txt["by"].upper() if not T.is_rtl(author) else txt["by"],
                    T.FONT_REGULAR, 10, MUTED, "center", char_space=1.5 if not T.is_rtl(author) else 0)
        T.draw_line(c, x + w / 2, y + 0.62 * inch, author, af, 16, INK, "center")


def _copyright_page(c, project: dict, geo: dict) -> None:
    txt = _copy(project)
    box = geo["box"]
    x, y, w = box["x"] * inch, box["y"] * inch, box["w"] * inch
    author = project.get("author") or ""
    year = project.get("year") or ""
    title = project.get("title") or ""

    T.rule(c, x + w / 2 - 0.30 * inch, y + 2.95 * inch, x + w / 2 + 0.30 * inch, 1.0)
    cy = y + 2.55 * inch
    for line in T.wrap(f"© {year} {author}. {txt['rights']}", T.FONT_REGULAR, 10, w - 1.4 * inch):
        T.draw_line(c, x + w / 2, cy, line, T.FONT_REGULAR, 10, INK, "center")
        cy -= 16
    cy -= 6
    T.draw_line(c, x + w / 2, cy, txt["edition"], _font_for(txt["edition"]), 10, INK, "center")
    cy -= 26
    cy = T.draw_paragraph(c, txt["notice"], x + 0.7 * inch, cy, w - 1.4 * inch,
                          _font_for(txt["notice"]), 8.5, 13, MUTED, "center")
    cy -= 10
    T.draw_line(c, x + w / 2, cy, txt["printed"], _font_for(txt["printed"]), 8.5, MUTED, "center")


def _belongs_page(c, project: dict, geo: dict) -> None:
    txt = _copy(project)
    box = geo["box"]
    x, y, w, h = box["x"] * inch, box["y"] * inch, box["w"] * inch, box["h"] * inch
    T.frame(c, x, y, w, h, inset=0.28 * inch, width=0.8)
    label = txt["belongs"]
    T.draw_line(c, x + w / 2, y + h * 0.66, label, _font_for(label, bold=True), 22, INK, "center")
    T.draw_line(c, x + w / 2, y + h * 0.58, txt["name_line"], T.FONT_REGULAR, 9, MUTED, "center", char_space=1.6)
    c.setStrokeColor(INK)
    c.setLineWidth(1.0)
    c.line(x + 0.9 * inch, y + h * 0.50, x + w - 0.9 * inch, y + h * 0.50)
    c.line(x + 0.9 * inch, y + h * 0.40, x + w - 0.9 * inch, y + h * 0.40)
    fun = f"{len(kdp.art_pages(project))} {txt['pages_of_fun']}"
    T.draw_line(c, x + w / 2, y + h * 0.24, fun, _font_for(fun), 11, MUTED, "center")


def _art_page(c, project: dict, page: dict, geo: dict, metrics: list) -> None:
    box = geo["box"]
    caption = (page.get("caption") or "").strip()
    cap_h = 0.40 if (project.get("captions") and caption) else 0.0
    art_h = box["h"] - cap_h
    img = art_for(project, page, box["w"], art_h)
    x = box["x"] * inch
    y = (box["y"] + cap_h) * inch
    c.drawImage(
        ImageReader(img),
        x,
        y,
        width=box["w"] * inch,
        height=art_h * inch,
        preserveAspectRatio=False,
        anchor="c",
    )
    if cap_h:
        font = _font_for(caption)
        T.draw_line(c, x + box["w"] * inch / 2, (box["y"] + 0.10) * inch, caption, font, 11.5, INK, "center")

    dpi = img.width / box["w"] if box["w"] else 0
    overflow = caption and T.string_width(caption, _font_for(caption), 11.5) > box["w"] * inch
    metrics.append({
        "page_id": page["id"],
        "dpi": round(min(dpi, img.height / art_h) if art_h else dpi, 1),
        "is_bw": img.mode == "1",
        "ink": round(lineart.ink_ratio(img), 4),
        "overflow": bool(overflow),
        "px": list(img.size),
    })


# ---------------------------------------------------------------------------
# البناء
# ---------------------------------------------------------------------------
def build_interior(project: dict, out_path: str | Path) -> dict:
    T.register_fonts()
    plan = kdp.plan_pages(project)
    geo = kdp.interior_margins(project)
    pw, ph = geo["page_w"] * inch, geo["page_h"] * inch
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    c = canvas.Canvas(str(out_path), pagesize=(pw, ph), pageCompression=1)
    c.setTitle(project.get("title") or "Coloring Book")
    c.setAuthor(project.get("author") or "")
    c.setSubject("Coloring book interior — Amazon KDP ready")
    c.setCreator(f"{C.APP_NAME} ({C.APP_NAME_LATIN}) {C.APP_VERSION}")

    metrics: list[dict] = []
    pages_by_id = {p["id"]: p for p in project.get("pages", [])}
    for spec in plan:
        kind = spec["kind"]
        if kind == "title":
            _title_page(c, project, geo)
        elif kind == "copyright":
            _copyright_page(c, project, geo)
        elif kind == "belongs":
            _belongs_page(c, project, geo)
        elif kind == "art":
            page = pages_by_id.get(spec["page_id"])
            if page and page.get("status") == "ready":
                _art_page(c, project, page, geo, metrics)
        c.showPage()
    c.save()

    return {
        "file": str(out_path),
        "pages": len(plan),
        "width": geo["page_w"],
        "height": geo["page_h"],
        "metrics": metrics,
        "margins": geo,
    }
