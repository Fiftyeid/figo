"""بناء ملفات النشر النهائية + حزمة ZIP + بيانات KDP الوصفية."""
from __future__ import annotations

import json
import zipfile
from datetime import date
from pathlib import Path

from . import book, config as C, cover as cover_mod, kdp, pipeline, store

OUT_FILES = {
    "interior": "interior.pdf",
    "cover": "cover.pdf",
    "cover_proof": "cover-proof.pdf",
    "zip": "kdp-package.zip",
}


def _slug(text: str) -> str:
    keep = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in (text or "coloring-book"))
    keep = "-".join(filter(None, keep.split("-")))
    return (keep or "coloring-book")[:40]


def _royalty(project: dict) -> dict:
    price = float(project.get("price") or 0)
    cost = float(project.get("printing_cost") or 0)
    royalty = max(0.0, price * 0.60 - cost)
    return {"price": round(price, 2), "cost": round(cost, 2), "royalty": round(royalty, 2)}


def metadata_text(project: dict, validation: dict) -> str:
    cov = validation["cover"]
    r = _royalty(project)
    kws = [k for k in project.get("keywords", []) if str(k).strip()]
    kw_lines = "\n".join(f"  {i + 1}. {k}" for i, k in enumerate(kws)) or "  —"
    page_count = validation["pages"]
    ai = "نعم (صور مُنشأة/مُعالجة بالذكاء الاصطناعي)" if project.get("ai_generated") else "لا"
    return f"""بيانات الكتاب لـ Amazon KDP
{'=' * 46}

العنوان (Title):            {project.get('title', '')}
العنوان الفرعي (Subtitle):  {project.get('subtitle', '') or '—'}
المؤلف (Author):            {project.get('author', '')}
اللغة (Language):           {'العربية' if str(project.get('language', 'ar')).startswith('ar') else 'English'}
تاريخ الإعداد:              {date.today().isoformat()}

الوصف (Description)
{'-' * 46}
{(project.get('description') or '').strip() or '—'}

الكلمات المفتاحية (7 Keywords)
{'-' * 46}
{kw_lines}

التصنيفات (Categories)
{'-' * 46}
{chr(10).join('  • ' + c for c in project.get('categories', [])) or '  —'}

المواصفات الفنية
{'-' * 46}
مقاس القطع:                 {C.TRIM_SIZES[project.get('trim', '8.5x11')]['label']}
نوع الورق:                  {C.PAPER_TYPES.get(project.get('paper', 'white'), C.PAPER_TYPES['white'])['label']}
عدد الصفحات النهائي:        {page_count} صفحة (رقم زوجي)
الطباعة على وجه واحد:       {'نعم' if project.get('single_sided') else 'لا'}
النزف (Bleed):              {'مفعّل — 0.125"' if project.get('bleed') else 'غير مفعّل'}
مقاس الصفحة الداخلية:       {validation['margins']['page_w']:.3f}" × {validation['margins']['page_h']:.3f}"
الهامش الداخلي (gutter):     {validation['margins']['inside']:.3f}"
مقاس الغلاف الكامل:          {cov['width']:.3f}" × {cov['height']:.3f}"
عرض الكعب (Spine):           {cov['spine']:.4f}"
منطقة الباركود:             2" × 1.2" أسفل يمين الغلاف الخلفي (تُترك فارغة)

التسعير والعمولة (تقديري)
{'-' * 46}
سعر البيع:                  ${r['price']:.2f}
تكلفة الطباعة (أدخلها من KDP): ${r['cost']:.2f}
العمولة التقديرية (60%):     ${r['royalty']:.2f}

إفصاح المحتوى بالذكاء الاصطناعي
{'-' * 46}
{ai}
عند النشر، أجب بصدق عن سؤال KDP: "هل يتضمن محتواك محتوى مُنشأ بالذكاء الاصطناعي؟"
الإفصاح لا يمنع النشر، لكن عدم الإفصاح قد يؤدي إلى إيقاف الحساب.

ملاحظة: تُحسب تكلفة الطباعة والعمولة النهائية داخل KDP حسب السوق والعملة.
"""


def checklist_text(project: dict, validation: dict) -> str:
    cov = validation["cover"]
    pages = validation["pages"]
    return f"""# قائمة النشر على Amazon KDP

## 1) قبل الرفع
- [ ] راجع كل صفحة تلوين (لا خطوط رمادية، لا نصوص داخل الرسومات).
- [ ] تأكد أن عدد الصفحات = **{pages}** (رقم زوجي، والحد الأدنى 24).
- [ ] تأكد أن الصور بدقة **300 DPI** (المولّد يفعل ذلك تلقائيًا).
- [ ] راجع بيانات العنوان والوصف والكلمات المفتاحية (7 كلمات كحد أقصى).
- [ ] جهّز صورة غلاف مصغّرة (Ebook) إذا أردت بيع نسخة كيندل.
- [ ] أجب عن سؤال المحتوى المُنشأ بالذكاء الاصطناعي بصدق.

## 2) رفع الداخل (Interior)
- ملف: `interior.pdf`
- مقاس الصفحة: {validation['margins']['page_w']:.3f}" × {validation['margins']['page_h']:.3f}"
- عدد الصفحات: {pages}
- نوع الورق المقترح: {C.PAPER_TYPES.get(project.get('paper', 'white'), C.PAPER_TYPES['white'])['label']}
- اختر نفس مقاس القطع في KDP: {C.TRIM_SIZES[project.get('trim', '8.5x11')]['label']}
- {'فعّل خيار "Bleed" لأن الملف يحتوي نزفًا.' if project.get('bleed') else 'اترك خيار "Bleed" غير مفعّل.'}

## 3) رفع الغلاف (Cover)
- ملف: `cover.pdf`
- القياس الكامل: **{cov['width']:.3f}" × {cov['height']:.3f}"** (يشمل نزف 0.125" من كل جهة)
- عرض الكعب: **{cov['spine']:.4f}"** = {pages} × {C.PAPER_TYPES.get(project.get('paper', 'white'), C.PAPER_TYPES['white'])['thickness']}"
- لا تضف هامشًا إضافيًا: القياس أعلاه نهائي وجاهز.
- منطقة الباركود 2" × 1.2" محجوزة وفارغة أسفل يمين الغلاف الخلفي.
- استخدم `cover-proof.pdf` للمعاينة فقط (يحتوي خطوطًا إرشادية ولا يُرفع).

## 4) المراجعة النهائية
- [ ] افتح المعاينة (Previewer) في KDP وافحص كل صفحة.
- [ ] تأكد من عدم قص أي نص أو رسمة عند الحواف.
- [ ] افحص الغلاف الخلفي: الباركود غير مغطّى بأي عنصر.
- [ ] تأكد أن النص على الكعب غير مستخدم إن كان الكتاب أقل من 80 صفحة.
- [ ] اطلب نسخة مطبوعة (Proof copy) قبل النشر إن أمكن.

## 5) بعد النشر
- [ ] اربط الكتاب بسلسلة (Series) إذا كان جزءًا من مجموعة.
- [ ] أضف وصفًا تسويقيًا وجملة "Look Inside".
- [ ] راقب التعليقات وحدّث الإصدار عند الحاجة.

> ملاحظات مطابقة آلية: {validation['fails']} مشكلة حرجة، {validation['warns']} تنبيه،
> درجة المطابقة {validation['score']}/100.
"""


def render_previews(project_id: str, out_dir: Path, validation: dict) -> dict:
    """ينتج صور معاينة PNG للغلاف وصفحات من الداخل (إن توفر pypdfium2)."""
    previews = {}
    try:
        import pypdfium2 as pdfium
    except Exception:
        return previews
    try:
        doc = pdfium.PdfDocument(str(out_dir / OUT_FILES["cover"]))
        img = doc[0].render(scale=1.4).to_pil()
        img.thumbnail((1400, 1400))
        img.save(out_dir / "preview-cover.png")
        previews["cover"] = "preview-cover.png"
    except Exception:
        pass
    try:
        doc = pdfium.PdfDocument(str(out_dir / OUT_FILES["interior"]))
        for i in [0, 4, 6, 8]:
            if i < len(doc):
                img = doc[i].render(scale=1.0).to_pil()
                img.thumbnail((900, 900))
                img.save(out_dir / f"preview-page-{i}.png")
        previews["pages"] = True
    except Exception:
        pass
    return previews


def build_all(project_id: str) -> dict:
    project = store.load_project(project_id)
    out_dir = store.project_dir(project_id) / "out"
    out_dir.mkdir(parents=True, exist_ok=True)

    interior = book.build_interior(project, out_dir / OUT_FILES["interior"])
    cover = cover_mod.build_cover(project, out_dir / OUT_FILES["cover"], proof=False)
    cover_proof = cover_mod.build_cover(project, out_dir / OUT_FILES["cover_proof"], proof=True)

    stats = pipeline.all_stats(project)
    validation = kdp.validate(project, stats)
    validation["interior"] = {
        "pages": interior["pages"],
        "width": interior["width"],
        "height": interior["height"],
    }
    validation["cover_pdf"] = {
        "width": cover["width"],
        "height": cover["height"],
        "spine": cover["spine"],
    }

    meta = metadata_text(project, validation)
    checklist = checklist_text(project, validation)
    readme = f"""{C.APP_NAME} — {C.APP_NAME_LATIN} Studio {C.APP_VERSION}
{'=' * 50}

محتويات الحزمة:
  interior.pdf      ملف الداخل الجاهز للطباعة (300 DPI، أبيض وأسود).
  cover.pdf         الغلاف الكامل (خلفي + كعب + أمامي) مع نزف 0.125".
  cover-proof.pdf   نسخة معاينة بالخطوط الإرشادية — لا تُرفع إلى KDP.
  metadata.txt      بيانات العنوان والوصف والكلمات المفتاحية والتسعير.
  kdp-checklist.md  خطوات النشر والتحقق قبل الرفع.

مقاس القطع: {C.TRIM_SIZES[project.get('trim', '8.5x11')]['label']}
عدد الصفحات: {validation['pages']}
مقاس الغلاف: {cover['width']:.3f}" × {cover['height']:.3f}" — الكعب {cover['spine']:.4f}"

تنبيه: إذا أضفت أو حذفت صفحات بعد التصدير، أعد التصدير لأن عرض الكعب يتغير.
"""

    (out_dir / "metadata.txt").write_text(meta, "utf-8")
    (out_dir / "kdp-checklist.md").write_text(checklist, "utf-8")
    (out_dir / "README.txt").write_text(readme, "utf-8")

    previews = render_previews(project_id, out_dir, validation)

    slug = _slug(project.get("title", ""))
    zip_path = out_dir / OUT_FILES["zip"]
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for name in (OUT_FILES["interior"], OUT_FILES["cover"], OUT_FILES["cover_proof"],
                     "metadata.txt", "kdp-checklist.md", "README.txt"):
            f = out_dir / name
            if f.exists():
                zf.write(f, arcname=f"{slug}/{name}")
        for p in sorted(out_dir.glob("preview-*.png")):
            zf.write(p, arcname=f"{slug}/previews/{p.name}")
        zf.writestr(f"{slug}/project.json", json.dumps(project, ensure_ascii=False, indent=2))

    sizes = {k: (out_dir / v).stat().st_size for k, v in OUT_FILES.items() if (out_dir / v).exists()}
    return {
        "files": {
            "interior": f"/api/projects/{project_id}/file/{OUT_FILES['interior']}",
            "cover": f"/api/projects/{project_id}/file/{OUT_FILES['cover']}",
            "cover_proof": f"/api/projects/{project_id}/file/{OUT_FILES['cover_proof']}",
            "zip": f"/api/projects/{project_id}/file/{OUT_FILES['zip']}",
            "metadata": f"/api/projects/{project_id}/file/metadata.txt",
            "checklist": f"/api/projects/{project_id}/file/kdp-checklist.md",
            "preview_cover": f"/api/projects/{project_id}/file/preview-cover.png",
        },
        "sizes": sizes,
        "validation": validation,
        "previews": previews,
        "zip_name": f"{slug}-kdp.zip",
    }
