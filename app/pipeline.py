"""خط إنتاج الصفحة: توليد → حفظ المصدر → تحويل لخطوط → تكوين بالمقاس → معاينة."""
from __future__ import annotations

import io
import random
from pathlib import Path

from PIL import Image

from . import config as C, kdp, lineart, providers, store


def _box_px(project: dict, page: dict) -> tuple[int, int, float, float]:
    bw, bh = kdp.art_box_inches(project, bool((page.get("caption") or "").strip()))
    return int(round(bw * C.DPI)), int(round(bh * C.DPI)), bw, bh


def _settings(project: dict, page: dict) -> dict:
    s = page.get("settings") or {}
    return {
        "thickness": int(s.get("thickness", project.get("thickness", 2))),
        "threshold": int(s.get("threshold", project.get("threshold", 150))),
        "mode": s.get("mode", "auto"),
    }


def compose_art(project: dict, page: dict) -> Image.Image:
    """يحوّل صورة المصدر إلى صفحة تلوين بالمقاس النهائي ويحفظها."""
    paths = store.page_paths(project["id"], page["id"])
    if not paths["source"].exists():
        raise FileNotFoundError("لا توجد صورة مصدر لهذه الصفحة")
    src = lineart.open_image(paths["source"])
    opts = _settings(project, page)
    detail = C.STYLES.get(project.get("style", "medium"), C.STYLES["medium"])["detail"]
    art = lineart.to_line_art(
        src,
        thickness=opts["thickness"],
        threshold=opts["threshold"],
        mode=opts["mode"],
        detail=detail,
    )
    wpx, hpx, _, _ = _box_px(project, page)
    composed = lineart.compose_page(art, wpx, hpx)
    paths["art"].parent.mkdir(parents=True, exist_ok=True)
    composed.save(paths["art"], optimize=True)

    thumb = lineart.thumbnail(composed)
    thumb.save(paths["thumb"], optimize=True)
    return composed


def generate_page(project: dict, page: dict, options: dict | None = None) -> dict:
    """يولّد صورة الصفحة من المزوّد المطلوب ثم يحوّلها إلى خطوط."""
    options = options or {}
    paths = store.page_paths(project["id"], page["id"])
    paths["source"].parent.mkdir(parents=True, exist_ok=True)
    provider = page.get("provider") or project.get("provider", "procedural")
    style_key = project.get("style", "medium")
    style_info = C.STYLES.get(style_key, C.STYLES["medium"])
    seed = random.randint(0, 2**31 - 1)
    wpx, hpx, _, _ = _box_px(project, page)

    if provider == "procedural":
        theme = page.get("theme") or project.get("theme", "animals")
        proc_style = page.get("procedural_style") or providers.THEMES.get(theme, {}).get("procedural", "mandala")
        data, label = providers.procedural(
            proc_style,
            seed=seed,
            size=(wpx, hpx),
            detail=style_info["detail"],
            thickness=int(page.get("settings", {}).get("thickness", project.get("thickness", 2))),
        )
        used = f"محرّك محلي · {proc_style}"
    else:
        settings = store.load_settings()
        api_key = (settings.get("api_keys", {}) or {}).get(provider, "")
        data, used = providers.generate(
            provider,
            page.get("prompt") or providers.build_prompt(theme=page.get("theme", "animals")),
            api_key=api_key,
            local_url=settings.get("local_sd_url", "http://127.0.0.1:7860"),
            size=(1024, 1536) if provider in ("openai", "freellmapi") else (wpx, hpx),
            seed=seed,
            base_url=settings.get("freellmapi_url", C.FREELLMAPI_URL),
            model=settings.get("freellmapi_image_model", C.FREELLMAPI_IMAGE_MODEL),
        )

    paths["source"].write_bytes(data)
    compose_art(project, page)
    return {"provider_label": used, "seed": seed}


def import_image(project: dict, page: dict, data: bytes) -> None:
    """يستورد صورة جاهزة (من المستخدم) كصفحة تلوين."""
    paths = store.page_paths(project["id"], page["id"])
    paths["source"].parent.mkdir(parents=True, exist_ok=True)
    img = Image.open(io.BytesIO(data))
    img.load()
    img.convert("RGB").save(paths["source"], optimize=True)
    compose_art(project, page)


def stats(project: dict, page: dict) -> dict:
    paths = store.page_paths(project["id"], page["id"])
    if not paths["art"].exists():
        return {"dpi": 0, "is_bw": False, "ink": 0, "overflow": False}
    img = Image.open(paths["art"])
    bw, bh = kdp.art_box_inches(project, bool((page.get("caption") or "").strip()))
    return {
        "dpi": round(min(img.width / bw, img.height / bh), 1) if bw and bh else 0,
        "is_bw": img.mode == "1",
        "ink": round(lineart.ink_ratio(img), 4),
        "overflow": False,
    }


def all_stats(project: dict) -> list[dict]:
    out = []
    for page in project.get("pages", []):
        if page.get("status") != "ready":
            continue
        s = stats(project, page)
        s["page_id"] = page["id"]
        out.append(s)
    return out
