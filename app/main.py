"""خادم التطبيق المحلي (FastAPI) — الواجهة + واجهة برمجة التطبيقات."""
from __future__ import annotations

import io
import threading
import time
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import config as C, cover as cover_builder, export, jobs, kdp, pipeline, planner, providers, store, textkit
from . import book, lineart

app = FastAPI(title=f"{C.APP_NAME} — {C.APP_NAME_LATIN} Studio", version=C.APP_VERSION)
app.add_middleware(
    CORSMiddleware,
    allow_origins=C.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

textkit.register_fonts()


# ---------------------------------------------------------------------------
# نماذج الطلبات
# ---------------------------------------------------------------------------
class ProjectIn(BaseModel):
    title: str | None = None
    subtitle: str | None = None
    author: str | None = None
    language: str | None = None
    trim: str | None = None
    paper: str | None = None
    bleed: bool | None = None
    single_sided: bool | None = None
    style: str | None = None
    audience: str | None = None
    theme: str | None = None
    provider: str | None = None
    thickness: int | None = None
    threshold: int | None = None
    captions: bool | None = None
    description: str | None = None
    keywords: list[str] | None = None
    categories: list[str] | None = None
    price: float | None = None
    printing_cost: float | None = None
    ai_generated: bool | None = None
    front_matter: dict | None = None
    cover: dict | None = None


class GenerateIn(BaseModel):
    """كل الحقول اختيارية: ما لم يُرسل يُؤخذ من إعدادات المشروع."""
    pages: list[dict] | None = None
    count: int | None = None
    theme: str | None = None
    subject: str = ""
    style: str | None = None
    audience: str | None = None
    provider: str | None = None
    with_captions: bool | None = None
    caption_prefix: str = ""
    thickness: int | None = None
    mode: str | None = None


class PagePatch(BaseModel):
    caption: str | None = None
    settings: dict | None = None
    status: str | None = None


class OrderIn(BaseModel):
    order: list[str]


class WizardIn(BaseModel):
    title: str = ""
    idea: str = ""
    author: str = ""
    language: str = "ar"
    audience: str = "kids_mid"
    style: str = "medium"
    trim: str = "8.5x11"
    paper: str = "white"
    art_pages: int = 12
    single_sided: bool = True
    captions: bool = False
    provider: str = "procedural"
    use_ai_planner: bool = True
    plan: dict | None = None
    palette: dict | None = None
    generate_cover_options: bool = True


class CoverApplyIn(BaseModel):
    background: str
    accent: str
    blurb: str | None = None


class SettingsIn(BaseModel):
    api_keys: dict | None = None
    clear_keys: bool = False
    local_sd_url: str | None = None
    freellmapi_url: str | None = None
    freellmapi_model: str | None = None
    freellmapi_image_model: str | None = None
    text_provider: str | None = None


# ---------------------------------------------------------------------------
# بيانات مساعدة
# ---------------------------------------------------------------------------
def _project_or_404(pid: str) -> dict:
    try:
        return store.load_project(pid)
    except FileNotFoundError as exc:
        raise HTTPException(404, "المشروع غير موجود") from exc


def enrich(project: dict) -> dict:
    """يضيف حقولًا محسوبة تُستخدم في الواجهة."""
    project = dict(project)
    pages = project.get("pages", [])
    t = C.TRIM_SIZES.get(project.get("trim", "8.5x11"), C.TRIM_SIZES["8.5x11"])
    project["_meta"] = {
        "trim_label": t["label"],
        "trim_w": t["w"],
        "trim_h": t["h"],
        "page_count": kdp.total_pages(project),
        "art_count": len([p for p in pages if p.get("status") == "ready"]),
        "spine": kdp.spine_width(project),
        "cover": kdp.cover_geometry(
            kdp.total_pages(project), project.get("trim", "8.5x11"), project.get("paper", "white")
        ),
        "margins": kdp.interior_margins(project),
        "gutter_min": kdp.gutter_for(kdp.total_pages(project)),
        "ready": len([p for p in pages if p.get("status") == "ready"]),
    }
    out_dir = store.project_dir(project["id"]) / "out"
    names = {
        "interior": "interior.pdf",
        "cover": "cover.pdf",
        "cover_proof": "cover-proof.pdf",
        "zip": "kdp-package.zip",
        "metadata": "metadata.txt",
        "checklist": "kdp-checklist.md",
    }
    has_output = (out_dir / names["interior"]).exists() and (out_dir / names["cover"]).exists()
    project["_meta"]["has_output"] = has_output
    if has_output:
        project["_meta"]["outputs"] = {
            k: f"/api/projects/{project['id']}/file/{v}" for k, v in names.items() if (out_dir / v).exists()
        }
        project["_meta"]["built_at"] = max((out_dir / v).stat().st_mtime for v in names.values() if (out_dir / v).exists())
    return project


# ---------------------------------------------------------------------------
# المسارات العامة
# ---------------------------------------------------------------------------
@app.get("/api/meta")
def meta():
    return {
        "app": {
            "name": C.APP_NAME,
            "name_latin": C.APP_NAME_LATIN,
            "version": C.APP_VERSION,
            "tagline": C.APP_TAGLINE,
        },
        "trims": C.TRIM_SIZES,
        "papers": C.PAPER_TYPES,
        "styles": C.STYLES,
        "themes": providers.THEMES,
        "audiences": providers.AUDIENCES,
        "providers": C.PROVIDERS,
        "kdp": {
            "min_pages": C.MIN_PAGES,
            "max_pages": C.MAX_PAGES,
            "bleed": C.BLEED,
            "min_outside_no_bleed": C.MIN_OUTSIDE_NO_BLEED,
            "min_outside_bleed": C.MIN_OUTSIDE_BLEED,
            "spine_text_pages": C.MIN_SPINE_TEXT_PAGES,
            "barcode": [C.BARCODE_W, C.BARCODE_H],
            "gutter_table": C.GUTTER_TABLE,
            "dpi": C.DPI,
        },
        "settings": store.public_settings(),
    }


@app.get("/api/settings")
def get_settings():
    return store.public_settings()


@app.post("/api/settings")
def set_settings(payload: SettingsIn):
    current = store.load_settings()
    patch = {}
    for field, default in (
        ("local_sd_url", "http://127.0.0.1:7860"),
        ("freellmapi_url", C.FREELLMAPI_URL),
        ("freellmapi_model", C.FREELLMAPI_TEXT_MODEL),
        ("freellmapi_image_model", C.FREELLMAPI_IMAGE_MODEL),
        ("text_provider", "auto"),
    ):
        val = getattr(payload, field)
        if val is None:      # غير مُرسل أصلًا = لا تغيير
            continue
        patch[field] = str(val).strip() or default
    store.update_settings(patch=patch, keys=payload.api_keys or {},
                          clear_keys=bool(payload.clear_keys))
    return store.public_settings()


@app.get("/api/freellmapi/test")
def freellmapi_test(url: str = "", key: str = ""):
    """اختبار اتصال بخدمة FreeLLMAPI وإرجاع النماذج المتاحة."""
    settings = store.load_settings()
    key = key or (settings.get("api_keys", {}) or {}).get("freellmapi", "")
    url = url or settings.get("freellmapi_url", C.FREELLMAPI_URL)
    try:
        info = providers.freellmapi_models(url, key)
    except providers.ProviderError as exc:
        return {"ok": False, "error": str(exc)}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"خطأ غير متوقع: {exc}"}
    return {"ok": True, **info}


@app.get("/api/projects")
def projects_list():
    return store.list_projects()


@app.post("/api/projects")
def project_create(payload: ProjectIn):
    project = store.new_project(payload.dict(exclude_none=True))
    return enrich(project)


@app.get("/api/projects/{pid}")
def project_get(pid: str):
    return enrich(_project_or_404(pid))


@app.patch("/api/projects/{pid}")
def project_patch(pid: str, payload: ProjectIn):
    project = store.update_project(pid, payload.dict(exclude_none=True))
    return enrich(project)


@app.delete("/api/projects/{pid}")
def project_delete(pid: str):
    store.delete_project(pid)
    return {"ok": True}


# ---------------------------------------------------------------------------
# التوليد
# ---------------------------------------------------------------------------
@app.post("/api/projects/{pid}/generate")
def generate(pid: str, payload: GenerateIn):
    _project_or_404(pid)
    job = jobs.start_generation(pid, payload.dict(exclude_none=True))
    return job


@app.get("/api/jobs/{job_id}")
def job_get(job_id: str):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(404, "المهمة غير موجودة")
    return job


@app.post("/api/jobs/{job_id}/cancel")
def job_cancel(job_id: str):
    return {"ok": jobs.cancel(job_id)}


@app.get("/api/projects/{pid}/pages/{page_id}/thumb")
def page_thumb(pid: str, page_id: str, v: int = Query(0)):
    paths = store.page_paths(pid, page_id)
    if not paths["thumb"].exists():
        from PIL import Image

        if paths["art"].exists():
            lineart.thumbnail(Image.open(paths["art"])).save(paths["thumb"])
        else:
            raise HTTPException(404, "لا توجد معاينة")
    return FileResponse(paths["thumb"], media_type="image/png", headers={"Cache-Control": "no-cache"})


@app.get("/api/projects/{pid}/pages/{page_id}/full")
def page_full(pid: str, page_id: str):
    paths = store.page_paths(pid, page_id)
    target = paths["art"] if paths["art"].exists() else paths["source"]
    if not target.exists():
        raise HTTPException(404, "الصفحة غير موجودة")
    return FileResponse(target, media_type="image/png")


@app.post("/api/projects/{pid}/pages/{page_id}/regenerate")
def page_regenerate(pid: str, page_id: str):
    project = _project_or_404(pid)
    try:
        page = store.get_page(pid, page_id)
    except KeyError as exc:
        raise HTTPException(404, "الصفحة غير موجودة") from exc
    store.update_page(pid, page_id, {"status": "generating", "error": ""})
    try:
        project = store.load_project(pid)
        result = pipeline.generate_page(project, page, {})
        store.update_page(pid, page_id, {"status": "ready", "provider_label": result["provider_label"], "seed": result["seed"]})
    except Exception as exc:  # noqa: BLE001
        store.update_page(pid, page_id, {"status": "error", "error": str(exc)})
        raise HTTPException(400, str(exc)) from exc
    return enrich(store.load_project(pid))


@app.post("/api/projects/{pid}/pages/{page_id}/reprocess")
def page_reprocess(pid: str, page_id: str, payload: PagePatch):
    project = _project_or_404(pid)
    try:
        page = store.get_page(pid, page_id)
    except KeyError as exc:
        raise HTTPException(404, "الصفحة غير موجودة") from exc
    if payload.caption is not None:
        store.update_page(pid, page_id, {"caption": payload.caption})
    if payload.settings:
        store.update_page(pid, page_id, {"settings": payload.settings})
    project = store.load_project(pid)
    page = store.get_page(pid, page_id)
    try:
        pipeline.compose_art(project, page)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(400, f"تعذّرت المعالجة: {exc}") from exc
    return {"ok": True, "page_id": page_id}


@app.patch("/api/projects/{pid}/pages/{page_id}")
def page_patch(pid: str, page_id: str, payload: PagePatch):
    project = _project_or_404(pid)
    patch = payload.dict(exclude_none=True)
    store.update_page(pid, page_id, patch)
    project = store.load_project(pid)
    return enrich(project)


@app.delete("/api/projects/{pid}/pages/{page_id}")
def page_delete(pid: str, page_id: str):
    store.delete_page(pid, page_id)
    return enrich(store.load_project(pid))


@app.post("/api/projects/{pid}/pages/reorder")
def pages_reorder(pid: str, payload: OrderIn):
    store.reorder_pages(pid, payload.order)
    return enrich(store.load_project(pid))


@app.post("/api/projects/{pid}/import")
async def import_pages(pid: str, files: list[UploadFile] = File(...)):
    project = _project_or_404(pid)
    created = []
    for upload in files[:30]:
        raw = await upload.read()
        if not raw:
            continue
        page = store.create_page(
            pid,
            prompt=f"imported:{upload.filename}",
            theme="custom",
            provider="import",
            caption="",
            settings={"mode": "auto"},
        )
        try:
            project = store.load_project(pid)
            pipeline.import_image(project, page, raw)
            store.update_page(pid, page["id"], {"status": "ready", "provider_label": "صورة مستوردة"})
            created.append(page["id"])
        except Exception as exc:  # noqa: BLE001
            store.update_page(pid, page["id"], {"status": "error", "error": str(exc)})
    return {"created": created, "project": enrich(store.load_project(pid))}


# ---------------------------------------------------------------------------
# معالج إنشاء الكتاب بالذكاء الاصطناعي
# ---------------------------------------------------------------------------
@app.post("/api/wizard/plan")
def wizard_plan(payload: WizardIn):
    settings = store.load_settings()
    keys = (settings.get("api_keys") or {})
    plan = planner.plan_book(
        payload.title,
        payload.idea,
        {
            "language": payload.language,
            "audience": payload.audience,
            "style": payload.style,
            "art_pages": payload.art_pages,
            "use_ai_planner": payload.use_ai_planner,
        },
        keys,
        settings,
    )
    plan["has_ai_key"] = bool(keys.get("openai") or keys.get("freellmapi"))
    plan["has_freellmapi_key"] = bool(keys.get("freellmapi"))
    return {"plan": plan}


@app.post("/api/wizard/create")
def wizard_create(payload: WizardIn):
    settings = store.load_settings()
    plan = payload.plan or planner.plan_book(
        payload.title, payload.idea,
        {"language": payload.language, "audience": payload.audience,
         "style": payload.style, "art_pages": payload.art_pages,
         "use_ai_planner": payload.use_ai_planner},
        (settings.get("api_keys") or {}),
        settings,
    )
    palette = payload.palette or (plan.get("palettes") or [{}])[0]
    project = store.new_project({
        "title": (plan.get("title") or payload.title or "كتاب تلوين").strip(),
        "subtitle": plan.get("subtitle", ""),
        "author": payload.author or "استوديو مِداد",
        "language": payload.language,
        "trim": payload.trim,
        "paper": payload.paper,
        "single_sided": payload.single_sided,
        "captions": payload.captions,
        "style": payload.style,
        "audience": payload.audience,
        "theme": plan.get("theme", "animals"),
        "provider": payload.provider,
        "description": plan.get("description", ""),
        "keywords": plan.get("keywords", []),
        "categories": plan.get("categories", ["Children's Books > Coloring Books"]),
        "ai_generated": True,
        "cover": {
            "background": palette.get("background", "#F6F1E7"),
            "accent": palette.get("accent", "#B4562F"),
            "blurb": (plan.get("cover") or {}).get("blurb", ""),
            "cover_page_id": None,
        },
    })
    pages = plan.get("pages") or []
    job = jobs.start_generation(project["id"], {
        "pages": pages,
        "count": len(pages) or payload.art_pages,
        "theme": plan.get("theme", "animals"),
        "style": payload.style,
        "audience": payload.audience,
        "provider": payload.provider,
        "with_captions": payload.captions,
        "thickness": 2,
        "mode": "auto",
    })
    return {"project": enrich(store.load_project(project["id"])), "job": job,
            "generate_cover_options": payload.generate_cover_options}


@app.post("/api/projects/{pid}/cover-options")
def cover_options(pid: str):
    """ينشئ 3 أغلفة مقترحة (ألوان مختلفة) مع صور معاينة."""
    project = _project_or_404(pid)
    if not kdp.art_pages(project):
        raise HTTPException(400, "أضف رسمة واحدة على الأقل أولًا")
    out_dir = store.project_dir(pid) / "out"
    out_dir.mkdir(parents=True, exist_ok=True)
    palette_items = planner.PALETTES[:3]
    items = []
    for i, pal in enumerate(palette_items):
        variant = {**project, "cover": {**(project.get("cover") or {}),
                                        "background": pal["background"], "accent": pal["accent"]}}
        pdf_path = out_dir / f"cover-option-{i}.pdf"
        cover_builder.build_cover(variant, pdf_path, proof=False)
        png = out_dir / f"cover-option-{i}.png"
        try:
            import pypdfium2 as pdfium
            doc = pdfium.PdfDocument(str(pdf_path))
            img = doc[0].render(scale=1.15).to_pil()
            img.thumbnail((1100, 1100))
            img.save(png)
        except Exception:
            continue
        items.append({
            "name": pal["name"],
            "background": pal["background"],
            "accent": pal["accent"],
            "png": f"/api/projects/{pid}/file/cover-option-{i}.png",
        })
    return {"items": items}


@app.post("/api/projects/{pid}/cover-apply")
def cover_apply(pid: str, payload: CoverApplyIn):
    patch = {"cover": {"background": payload.background, "accent": payload.accent}}
    if payload.blurb is not None:
        patch["cover"]["blurb"] = payload.blurb
    project = store.update_project(pid, patch)
    out_dir = store.project_dir(pid) / "out"
    try:
        cover_builder.build_cover(project, out_dir / "cover.pdf", proof=False)
        cover_builder.build_cover(project, out_dir / "cover-proof.pdf", proof=True)
        export.render_previews(pid, out_dir, {})
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(500, f"تعذّر بناء الغلاف: {exc}") from exc
    return {"ok": True, "project": enrich(store.load_project(pid))}


# ---------------------------------------------------------------------------
# الفحص والتصدير
# ---------------------------------------------------------------------------
@app.get("/api/projects/{pid}/validate")
def validate(pid: str):
    project = _project_or_404(pid)
    report = kdp.validate(project, pipeline.all_stats(project))
    report["cover_geometry"] = kdp.cover_geometry(
        kdp.total_pages(project), project.get("trim", "8.5x11"), project.get("paper", "white")
    )
    return report


@app.post("/api/projects/{pid}/build")
def build(pid: str):
    project = _project_or_404(pid)
    if not kdp.art_pages(project):
        raise HTTPException(400, "أضف رسمة واحدة على الأقل قبل التصدير")
    try:
        result = export.build_all(pid)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(500, f"فشل التصدير: {exc}") from exc
    store.update_project(pid, {"last_export": time.time()})
    result["project"] = enrich(store.load_project(pid))
    return result


@app.get("/api/downloads")
def downloads():
    """حزم التوزيع الجاهزة (ZIP) الموجودة في مجلد dist/."""
    if not C.DIST_DIR.exists():
        return {"items": []}
    items = []
    for path in sorted(C.DIST_DIR.glob("*.zip")):
        items.append({
            "name": path.name,
            "size": path.stat().st_size,
            "url": f"/download/{path.name}",
        })
    return {"items": items}


@app.get("/download/{name}")
def download(name: str):
    dist = C.DIST_DIR.resolve()
    path = (dist / name).resolve()
    if dist not in path.parents or path.suffix != ".zip" or not path.exists():
        raise HTTPException(404, "الحزمة غير موجودة")
    return FileResponse(path, media_type="application/zip", filename=path.name)


@app.get("/api/projects/{pid}/file/{name}")
def project_file(pid: str, name: str, download: int = 0):
    out_dir = (store.project_dir(pid) / "out").resolve()
    path = (out_dir / name).resolve()
    if out_dir not in path.parents or not path.exists():
        raise HTTPException(404, "الملف غير موجود — أنشئ التصدير أولًا")
    media = {
        ".pdf": "application/pdf",
        ".png": "image/png",
        ".txt": "text/plain; charset=utf-8",
        ".md": "text/markdown; charset=utf-8",
        ".zip": "application/zip",
    }.get(path.suffix, "application/octet-stream")
    headers = {"Cache-Control": "no-cache"}
    if download or path.suffix in (".zip", ".txt", ".md"):
        headers["Content-Disposition"] = f'attachment; filename="{path.name}"'
    return FileResponse(path, media_type=media, headers=headers)


@app.post("/api/projects/{pid}/preview-image")
def preview_image(pid: str, kind: str = "cover"):
    """يعيد PNG للغلاف أو صفحة داخلية (معاينة سريعة داخل الواجهة)."""
    out_dir = store.project_dir(pid) / "out"
    name = "preview-cover.png" if kind == "cover" else "preview-page-0.png"
    path = out_dir / name
    if not path.exists():
        raise HTTPException(404, "أنشئ التصدير أولًا")
    return FileResponse(path, media_type="image/png")


# ---------------------------------------------------------------------------
# واجهة الاستخدام
# ---------------------------------------------------------------------------
@app.get("/api/health")
def health():
    return {"ok": True, "app": C.APP_NAME_LATIN, "version": C.APP_VERSION}


@app.get("/")
def index():
    return FileResponse(C.STATIC_DIR / "index.html", media_type="text/html")


app.mount("/static", StaticFiles(directory=str(C.STATIC_DIR)), name="static")


# ---------------------------------------------------------------------------
# مشروع عرض أوّلي (مرة واحدة فقط) حتى تعمل الواجهة فورًا
# ---------------------------------------------------------------------------
def _seed_demo() -> None:
    if store.list_projects():
        return
    demo = store.new_project({
        "title": "حديقة الزهور",
        "subtitle": "كتاب تلوين للاسترخاء والإبداع",
        "author": "استوديو مِداد",
        "language": "ar",
        "trim": "8.5x11",
        "paper": "white",
        "bleed": False,
        "single_sided": True,
        "theme": "flowers",
        "style": "medium",
        "captions": False,
        "description": (
            "كتاب تلوين يضم ١٠ رسمات زهور وماندالا مرسومة بعناية، بخطوط سميكة وواضحة "
            "تناسب الأقلام الملونة والخشبية. كل رسمة في صفحة مستقلة مع صفحة فارغة في الخلف "
            "لمنع تسرّب الألوان، ومقاس كبير 8.5 × 11 بوصة يمنح مساحة مريحة للتلوين. "
            "مناسب للبالغين والأطفال فوق ٦ سنوات، وهدية مثالية لمحبي الاسترخاء والفن."
        ),
        "keywords": ["كتاب تلوين", "زهور", "ماندالا", "تلوين للبالغين",
                     "كتاب تلوين للأطفال", "استرخاء", "فن"],
    })
    styles = ["floral", "mandala", "floral", "geometric", "mandala",
              "floral", "geometric", "mandala", "floral", "mandala"]
    pid = demo["id"]

    def worker():
        for i, st in enumerate(styles):
            try:
                project = store.load_project(pid)
                page = store.create_page(pid, prompt=f"{st} #{i + 1}", theme="flowers",
                                         provider="procedural", procedural_style=st,
                                         caption="")
                pipeline.generate_page(project, page, {})
                store.update_page(pid, page["id"], {"status": "ready", "provider_label": "محرّك محلي"})
            except Exception as exc:  # noqa: BLE001
                print("seed error:", exc)
            time.sleep(0.2)

    threading.Thread(target=worker, daemon=True).start()


_seed_demo()
