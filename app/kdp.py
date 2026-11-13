"""محرّك قواعد KDP: الهوامش، أحجام الصفحات، الكعب، وفحص المطابقة."""
from __future__ import annotations

import math
from typing import Any

from . import config as C


class KdpError(ValueError):
    pass


# ---------------------------------------------------------------------------
# قياسات أساسية
# ---------------------------------------------------------------------------
def trim(key: str) -> dict:
    if key not in C.TRIM_SIZES:
        raise KdpError(f"مقاس قطع غير مدعوم: {key}")
    return C.TRIM_SIZES[key]


def gutter_for(pages: int) -> float:
    """الحد الأدنى للهامش الداخلي حسب عدد الصفحات (KDP)."""
    for lo, hi, val in C.GUTTER_TABLE:
        if lo <= pages <= hi:
            return val
    return C.GUTTER_TABLE[-1][2]


def _clamp_even(pages: int) -> int:
    return max(C.MIN_PAGES, pages if pages % 2 == 0 else pages + 1)


def interior_page_size(trim_key: str, bleed: bool) -> tuple[float, float]:
    t = trim(trim_key)
    if bleed:
        # KDP: أعلى وأسفل وخارج +0.125 بوصة
        return t["w"] + C.BLEED, t["h"] + 2 * C.BLEED
    return t["w"], t["h"]


def interior_margins(project: dict) -> dict:
    """هوامش التصميم الفعلية بالبوصة + صندوق المحتوى."""
    pages = total_pages(project)
    bleed = bool(project.get("bleed"))
    trim_key = project.get("trim", "8.5x11")
    t = trim(trim_key)
    pw, ph = interior_page_size(trim_key, bleed)

    kdp_gutter = gutter_for(pages)
    inside = kdp_gutter + C.DESIGN_GUTTER_PAD
    outside = C.DESIGN_OUTSIDE if not bleed else C.DESIGN_OUTSIDE
    top = C.DESIGN_TOP
    bottom = C.DESIGN_BOTTOM
    # نضمن عدم تجاوز الحد الأدنى أبدًا
    min_out = C.MIN_OUTSIDE_BLEED if bleed else C.MIN_OUTSIDE_NO_BLEED
    outside = max(outside, min_out + 0.05)
    top = max(top, min_out + 0.05)
    bottom = max(bottom, min_out + 0.05)

    content_w = pw - inside - outside
    content_h = ph - top - bottom
    return {
        "page_w": pw,
        "page_h": ph,
        "trim_w": t["w"],
        "trim_h": t["h"],
        "inside": inside,
        "outside": outside,
        "top": top,
        "bottom": bottom,
        "kdp_gutter": kdp_gutter,
        # صندوق المحتوى بإحداثيات PDF (من الأسفل يسارًا)
        "box": {
            "x": inside,
            "y": bottom,
            "w": content_w,
            "h": content_h,
        },
        "safe_ok": content_w > 2.0 and content_h > 2.0,
    }


def cover_geometry(pages: int, trim_key: str, paper: str) -> dict:
    """هندسة الغلاف الكامل: خلفي + كعب + أمامي + نزف."""
    t = trim(trim_key)
    paper_info = C.PAPER_TYPES.get(paper, C.PAPER_TYPES["white"])
    spine = round(pages * paper_info["thickness"], 4)
    width = C.BLEED + t["w"] + spine + t["w"] + C.BLEED
    height = C.BLEED + t["h"] + C.BLEED

    back_x = C.BLEED
    spine_x = back_x + t["w"]
    front_x = spine_x + spine
    trim_top = height - C.BLEED

    barcode_x2 = back_x + t["w"] - C.BARCODE_OFFSET
    barcode_x1 = barcode_x2 - C.BARCODE_W
    barcode_y1 = C.BLEED + C.BARCODE_OFFSET
    barcode_y2 = barcode_y1 + C.BARCODE_H

    return {
        "width": width,
        "height": height,
        "spine": spine,
        "trim_w": t["w"],
        "trim_h": t["h"],
        "trim_top": trim_top,
        "back": {"x": back_x, "y": C.BLEED, "w": t["w"], "h": t["h"]},
        "spine_box": {"x": spine_x, "y": C.BLEED, "w": spine, "h": t["h"]},
        "front": {"x": front_x, "y": C.BLEED, "w": t["w"], "h": t["h"]},
        "barcode": {
            "x": barcode_x1,
            "y": barcode_y1,
            "w": C.BARCODE_W,
            "h": C.BARCODE_H,
        },
        "spine_text_allowed": pages >= C.MIN_SPINE_TEXT_PAGES and spine >= 0.25,
        "paper_label": paper_info["label"],
    }


# ---------------------------------------------------------------------------
# تخطيط صفحات الكتاب
# ---------------------------------------------------------------------------
def art_pages(project: dict) -> list[dict]:
    return [p for p in project.get("pages", []) if p.get("status") == "ready"]


def plan_pages(project: dict) -> list[dict]:
    """يبني تسلسل صفحات الكتاب: تمهيد + (رسمة + ظهر أبيض) ..."""
    fm = project.get("front_matter", {})
    single_sided = bool(project.get("single_sided", True))
    out: list[dict] = []

    if fm.get("title_page", True):
        out.append({"kind": "title"})
    if fm.get("copyright_page", True):
        out.append({"kind": "copyright"})
    if fm.get("belongs_page", True):
        out.append({"kind": "belongs"})
    if fm.get("blank_after_front", True):
        out.append({"kind": "blank"})

    arts = art_pages(project)
    for i, page in enumerate(arts):
        out.append({"kind": "art", "page_id": page["id"], "index": i})
        if single_sided:
            out.append({"kind": "blank"})

    # دائمًا عدد صفحات زوجي، وبحد أدنى 24
    target = _clamp_even(total_pages(project))
    while len(out) < C.MIN_PAGES:
        out.append({"kind": "blank"})
    if len(out) % 2 == 1:
        out.append({"kind": "blank"})
    return out


def total_pages(project: dict) -> int:
    """عدد صفحات الكتاب المتوقع (قبل الحشو النهائي)."""
    fm = project.get("front_matter", {})
    front = sum(
        1
        for k in ("title_page", "copyright_page", "belongs_page", "blank_after_front")
        if fm.get(k, True)
    )
    single_sided = bool(project.get("single_sided", True))
    arts = len(art_pages(project))
    pages = front + arts * (2 if single_sided else 1)
    return _clamp_even(pages)


def spine_width(project: dict) -> float:
    return cover_geometry(
        total_pages(project), project.get("trim", "8.5x11"), project.get("paper", "white")
    )["spine"]


# ---------------------------------------------------------------------------
# الفحص
# ---------------------------------------------------------------------------
def _check(cid: str, label: str, status: str, detail: str = "", fix: str = "") -> dict:
    return {"id": cid, "label": label, "status": status, "detail": detail, "fix": fix}


def validate(project: dict, page_stats: list[dict] | None = None) -> dict:
    """يفحص المشروع مقابل متطلبات KDP ويعيد تقريرًا منظمًا."""
    checks: list[dict] = []
    page_stats = page_stats or []
    pages = total_pages(project)
    bleed = bool(project.get("bleed"))
    trim_key = project.get("trim", "8.5x11")
    t = trim(trim_key)
    m = interior_margins(project)
    cov = cover_geometry(pages, trim_key, project.get("paper", "white"))
    arts = art_pages(project)

    # 1) مقاس القطع
    checks.append(
        _check(
            "trim",
            "مقاس القطع مدعوم في KDP",
            "pass",
            f'{t["label"]} — {t["note"]}',
        )
    )

    # 2) عدد الصفحات
    if pages < C.MIN_PAGES:
        checks.append(
            _check(
                "page_count",
                "الحد الأدنى لعدد الصفحات (24)",
                "fail",
                f"الكتاب سيحتوي {pages} صفحة فقط.",
                "أضف صفحات رسمات (وصفحاتها الخلفية) حتى تصل إلى 24 صفحة على الأقل.",
            )
        )
    elif pages > C.MAX_PAGES:
        checks.append(
            _check(
                "page_count",
                "الحد الأقصى لعدد الصفحات (828)",
                "fail",
                f"{pages} صفحة تتجاوز الحد.",
                "قلّل عدد الصفحات أو اختر ورقًا/مقاسًا آخر.",
            )
        )
    elif pages < 40:
        checks.append(
            _check(
                "page_count",
                "عدد الصفحات",
                "warn",
                f"{pages} صفحة — مسموح لكنه أقل من 40 صفحة (الكتب الرقيقة قد تبدو غير مريحة).",
                "أضف المزيد من الرسمات لتحسين القيمة والشكل.",
            )
        )
    else:
        checks.append(_check("page_count", "عدد الصفحات", "pass", f"{pages} صفحة (رقم زوجي)."))

    # 3) الهامش الداخلي
    checks.append(
        _check(
            "gutter",
            "الهامش الداخلي (gutter)",
            "pass",
            f"المطلوب {gutter_for(pages):.3f}\" — المستخدم {m['inside']:.3f}\".",
        )
    )

    # 4) هوامش الخارج/الأعلى/الأسفل
    min_out = C.MIN_OUTSIDE_BLEED if bleed else C.MIN_OUTSIDE_NO_BLEED
    worst = min(m["outside"], m["top"], m["bottom"])
    checks.append(
        _check(
            "outside_margins",
            f"هوامش الخارج والأعلى والأسفل (الحد {min_out}\")",
            "pass" if worst >= min_out else "fail",
            f"أقل هامش مستخدم {worst:.3f}\".",
            "" if worst >= min_out else "زد الهوامش الخارجية في إعدادات المشروع.",
        )
    )

    # 5) النزف
    checks.append(
        _check(
            "bleed",
            "إعداد النزف (Bleed)",
            "pass",
            (
                f'مفعّل — مقاس الصفحة {m["page_w"]:.3f}" × {m["page_h"]:.3f}" (نزف 0.125" من الخارج والأعلى والأسفل).'
                if bleed
                else f'غير مفعّل — مقاس الصفحة {m["page_w"]:.3f}" × {m["page_h"]:.3f}" = مقاس القطع تمامًا.'
            ),
            "فعّل النزف إذا كانت الرسومات تلمس حافة الصفحة.",
        )
    )

    # 6) صور بدقة 300 DPI
    if page_stats:
        low = [p for p in page_stats if p.get("dpi", 0) < 300]
        checks.append(
            _check(
                "dpi",
                "دقة الصور (300 DPI)",
                "pass" if not low else "warn",
                f"{len(page_stats)} صفحة مفحوصة، {len(low)} أقل من 300 DPI.",
                "أعد توليد الصفحات الضعيفة بدقة أعلى.",
            )
        )

        # 7) أسود وأبيض نقي
        colored = [p for p in page_stats if not p.get("is_bw", True)]
        checks.append(
            _check(
                "bw",
                "الصفحات بالأبيض والأسود فقط",
                "pass" if not colored else "warn",
                "كل الصفحات 1-bit (أسود/أبيض)." if not colored else f"{len(colored)} صفحة تحتوي تدرّجات رمادية.",
                "أعد المعالجة بأداة تحويل الخطوط (threshold) لإزالة الرمادي.",
            )
        )

        # 8) كثافة الحبر
        heavy = [p for p in page_stats if p.get("ink", 0) > 0.45]
        if heavy:
            checks.append(
                _check(
                    "ink",
                    "كثافة الحبر",
                    "warn",
                    f"{len(heavy)} صفحة سوداء بنسبة عالية (>45%) — قد تظهر آثار على الوجه الآخر.",
                    "قلّل سماكة الخطوط أو استخدم الطباعة على وجه واحد.",
                )
            )
        else:
            checks.append(_check("ink", "كثافة الحبر", "pass", "ضمن الحدود المريحة للطباعة."))

        # 9) الملف الشخصي للصور
        checks.append(
            _check(
                "image_count",
                "عدد الرسمات",
                "pass" if len(arts) >= 10 else "warn",
                f"{len(arts)} رسمة جاهزة.",
                "أضف رسمات أكثر لقيمة أفضل للقارئ.",
            )
        )

        # 10) وضع الصورة داخل المنطقة الآمنة
        overflow = [p for p in page_stats if p.get("overflow")]
        checks.append(
            _check(
                "safe_zone",
                "بقاء الرسومات داخل الهوامش",
                "pass" if not overflow else "fail",
                "كل الرسومات داخل صندوق المحتوى الآمن." if not overflow else f"{len(overflow)} صفحة تتجاوز الهوامش.",
                "صغّر حجم الرسمة أو أعد بناء الكتاب.",
            )
        )

    # 11) الغلاف
    checks.append(
        _check(
            "cover_size",
            "قياس الغلاف الكامل",
            "pass",
            f'{cov["width"]:.3f}" × {cov["height"]:.3f}" — كعب {cov["spine"]:.3f}" ({cov["paper_label"]}).',
        )
    )
    checks.append(
        _check(
            "barcode",
            "منطقة الباركود 2\" × 1.2\"",
            "pass",
            "محجوزة فارغة في أسفل يمين الغلاف الخلفي بمسافة 0.25\" من الحواف.",
        )
    )
    if pages < C.MIN_SPINE_TEXT_PAGES:
        checks.append(
            _check(
                "spine_text",
                "نص على الكعب",
                "pass",
                f"عدد الصفحات {pages} < 80، لذلك لن نضع نصًا على الكعب (شرط KDP).",
            )
        )
    else:
        checks.append(
            _check(
                "spine_text",
                "نص على الكعب",
                "pass",
                f"مسموح ({pages} صفحة) — الكعب {cov['spine']:.3f}\" مع مسافة أمان 0.0625\" من كل حافة.",
            )
        )

    # 12) البيانات الوصفية
    if not (project.get("title") or "").strip():
        checks.append(_check("title", "عنوان الكتاب", "fail", "العنوان فارغ.", "أدخل عنوانًا للكتاب."))
    else:
        checks.append(_check("title", "العنوان والوصف", "pass", project["title"]))

    kws = [k for k in project.get("keywords", []) if str(k).strip()]
    if len(kws) > 7:
        checks.append(
            _check("keywords", "الكلمات المفتاحية", "warn", f"{len(kws)} كلمة (الحد 7).", "احتفظ بسبع كلمات فقط.")
        )
    elif len(kws) < 5:
        checks.append(
            _check("keywords", "الكلمات المفتاحية", "warn", f"{len(kws)} كلمة فقط.", "أضف 7 كلمات مفتاحية دقيقة.")
        )
    else:
        checks.append(_check("keywords", "الكلمات المفتاحية", "pass", f"{len(kws)} كلمة مفتاحية."))

    desc = (project.get("description") or "").strip()
    if len(desc) < 200:
        checks.append(
            _check("description", "وصف الكتاب", "warn", f"{len(desc)} حرفًا.", "اكتب 600–1500 حرف لوصف تسويقي فعّال.")
        )
    elif len(desc) > 4000:
        checks.append(
            _check("description", "وصف الكتاب", "fail", f"{len(desc)} حرفًا (الحد 4000).", "اختصر الوصف.")
        )
    else:
        checks.append(_check("description", "وصف الكتاب", "pass", f"{len(desc)} حرفًا."))

    # 13) إفصاح المحتوى المُنشأ بالذكاء الاصطناعي
    checks.append(
        _check(
            "ai_disclosure",
            "إفصاح المحتوى بالذكاء الاصطناعي",
            "warn" if project.get("ai_generated") else "pass",
            (
                "الصور مُنشأة بالذكاء الاصطناعي — يجب الإجابة بـ«نعم» على سؤال KDP عن المحتوى المُنشأ بالذكاء الاصطناعي."
                if project.get("ai_generated")
                else "محتوى محلي/يدوي — لا حاجة لإفصاح."
            ),
            "أجب بصدق في صفحة النشر داخل KDP؛ الإفصاح لا يمنع النشر.",
        )
    )

    checks.append(
        _check(
            "fonts",
            "الخطوط مدمجة في PDF",
            "pass",
            "كل النصوص مرسومة بخطوط مدمجة (DejaVu) داخل الملف.",
        )
    )

    fails = sum(1 for c in checks if c["status"] == "fail")
    warns = sum(1 for c in checks if c["status"] == "warn")
    score = max(0, 100 - fails * 20 - warns * 4)
    return {
        "checks": checks,
        "fails": fails,
        "warns": warns,
        "status": "fail" if fails else ("warn" if warns else "pass"),
        "score": score,
        "pages": pages,
        "cover": cov,
        "margins": m,
    }


def art_box_inches(project: dict, has_caption: bool = False) -> tuple[float, float]:
    """أبعاد صندوق الرسمة بالبوصة (مع خصم مساحة التعليق إن وُجد)."""
    m = interior_margins(project)
    cap = 0.40 if (project.get("captions") and has_caption) else 0.0
    return m["box"]["w"], m["box"]["h"] - cap
