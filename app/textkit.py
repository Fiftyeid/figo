"""أدوات النصوص العربية والإنجليزية داخل PDF (تشكيل الحروف + لف الأسطر)."""
from __future__ import annotations

import re
from functools import lru_cache

import arabic_reshaper
from bidi.algorithm import get_display
from reportlab.lib.colors import Color, HexColor, black
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from . import config as C

AR_RE = re.compile(r"[\u0600-\u06FF]")
_registered = False

FONT_REGULAR = "MidadSans"
FONT_BOLD = "MidadSans-Bold"
FONT_SERIF = "MidadSerif"
FONT_SERIF_BOLD = "MidadSerif-Bold"


def register_fonts() -> None:
    global _registered
    if _registered:
        return
    pdfmetrics.registerFont(TTFont(FONT_REGULAR, str(C.FONTS_DIR / "DejaVuSans.ttf")))
    pdfmetrics.registerFont(TTFont(FONT_BOLD, str(C.FONTS_DIR / "DejaVuSans-Bold.ttf")))
    pdfmetrics.registerFont(TTFont(FONT_SERIF, str(C.FONTS_DIR / "DejaVuSerif.ttf")))
    pdfmetrics.registerFont(TTFont(FONT_SERIF_BOLD, str(C.FONTS_DIR / "DejaVuSerif-Bold.ttf")))
    _registered = True


@lru_cache(maxsize=2048)
def shape(text: str) -> str:
    """يحوّل العربية إلى أشكال الحروف بالترتيب البصري الصحيح."""
    if not text:
        return ""
    if not AR_RE.search(text):
        return text
    try:
        return get_display(arabic_reshaper.reshape(text))
    except Exception:
        return text


def is_rtl(text: str) -> bool:
    return bool(AR_RE.search(text or ""))


def string_width(text: str, font: str, size: float) -> float:
    return pdfmetrics.stringWidth(shape(text), font, size)


def wrap(text: str, font: str, size: float, max_width: float) -> list[str]:
    """لف النص مع احترام الأسطر اليدوية."""
    lines: list[str] = []
    for paragraph in str(text).split("\n"):
        words = paragraph.split(" ")
        current = ""
        for word in words:
            trial = f"{current} {word}".strip()
            if string_width(trial, font, size) <= max_width or not current:
                current = trial
            else:
                lines.append(current)
                current = word
        lines.append(current)
    return lines


def draw_line(
    c,
    x: float,
    y: float,
    text: str,
    font: str = FONT_REGULAR,
    size: float = 12,
    color=black,
    align: str = "center",
    char_space: float = 0,
):
    if not text:
        return
    c.setFillColor(color)
    t = shape(text)
    if char_space and is_rtl(text):
        char_space = 0
    if char_space:
        to = c.beginText()
        to.setFont(font, size)
        to.setFillColor(color)
        to.setCharSpace(char_space)
        width = pdfmetrics.stringWidth(t, font, size) + char_space * max(0, len(t) - 1)
        ox = x - width / 2 if align == "center" else (x - width if align == "right" else x)
        to.setTextOrigin(ox, y)
        to.textLine(t)
        c.drawText(to)
        return
    c.setFont(font, size)
    if align == "center":
        c.drawCentredString(x, y, t)
    elif align == "right":
        c.drawRightString(x, y, t)
    else:
        c.drawString(x, y, t)


def draw_paragraph(
    c,
    text: str,
    x: float,
    y_top: float,
    width: float,
    font: str = FONT_REGULAR,
    size: float = 12,
    leading: float | None = None,
    color=black,
    align: str | None = None,
) -> float:
    """يرسم فقرة ويعيد الإحداثي y بعد آخر سطر."""
    leading = leading or size * 1.45
    align = align or ("right" if is_rtl(text) else "left")
    y = y_top
    for line in wrap(text, font, size, width):
        if align == "center":
            draw_line(c, x + width / 2, y, line, font, size, color, "center")
        elif align == "right":
            draw_line(c, x + width, y, line, font, size, color, "right")
        else:
            draw_line(c, x, y, line, font, size, color, "left")
        y -= leading
    return y


def rule(c, x1: float, y: float, x2: float, width: float = 0.75, color=black):
    c.setStrokeColor(color)
    c.setLineWidth(width)
    c.line(x1, y, x2, y)


def frame(c, x: float, y: float, w: float, h: float, inset: float = 0, width: float = 0.75, color=black):
    c.setStrokeColor(color)
    c.setLineWidth(width)
    c.rect(x + inset, y + inset, w - 2 * inset, h - 2 * inset, stroke=1, fill=0)
