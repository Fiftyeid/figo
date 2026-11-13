"""مهام التوليد في الخلفية مع تتبّع التقدّم (لتحديث الواجهة الحيّة)."""
from __future__ import annotations

import random
import threading
import time
import traceback
import uuid

from . import config as C, pipeline, providers, store

_jobs: dict[str, dict] = {}
_lock = threading.Lock()


def snapshot(job: dict) -> dict:
    return {
        "id": job["id"],
        "project_id": job["project_id"],
        "status": job["status"],
        "total": job["total"],
        "done": job["done"],
        "failed": job["failed"],
        "message": job.get("message", ""),
        "items": job["items"][-24:],
        "cancel": job.get("cancel", False),
        "created": job["created"],
    }


def get(job_id: str) -> dict | None:
    with _lock:
        job = _jobs.get(job_id)
        return snapshot(job) if job else None


def cancel(job_id: str) -> bool:
    with _lock:
        job = _jobs.get(job_id)
        if not job:
            return False
        job["cancel"] = True
        return True


def recent(project_id: str) -> list[dict]:
    with _lock:
        items = [snapshot(j) for j in _jobs.values() if j["project_id"] == project_id]
    return sorted(items, key=lambda j: j["created"], reverse=True)[:5]


def start_generation(project_id: str, options: dict) -> dict:
    project = store.load_project(project_id)
    preset = options.get("pages") or []
    count = max(1, min(60, int(options.get("count", len(preset) or 10))))
    if preset:
        count = min(count, len(preset))
    job_id = uuid.uuid4().hex[:10]
    job = {
        "id": job_id,
        "project_id": project_id,
        "status": "running",
        "total": count,
        "done": 0,
        "failed": 0,
        "items": [],
        "message": "جارٍ التحضير…",
        "created": time.time(),
        "cancel": False,
    }
    with _lock:
        _jobs[job_id] = job

    thread = threading.Thread(target=_run, args=(job_id, options), daemon=True)
    thread.start()
    return snapshot(job)


PROC_LABELS = {"mandala": "ماندالا", "floral": "زهور", "geometric": "زخرفة هندسية"}


def _caption_for(theme: str, index: int, options: dict) -> str:
    custom = (options.get("caption_prefix") or "").strip()
    if not options.get("with_captions"):
        return ""
    if custom:
        return f"{custom} {index + 1}"
    if options.get("provider") == "procedural":
        label = PROC_LABELS.get(providers.THEMES.get(theme, {}).get("procedural", ""), "رسمة")
    else:
        label = providers.THEMES.get(theme, {}).get("label", "رسمة")
    return f"{label} {index + 1}"


def _run(job_id: str, options: dict) -> None:
    with _lock:
        job = _jobs[job_id]
    project_id = job["project_id"]
    theme = options.get("theme", "animals")
    style = options.get("style", "medium")
    audience = options.get("audience", "kids_mid")
    provider = options.get("provider", "procedural")
    subject = options.get("subject", "")
    count = job["total"]
    preset_pages = options.get("pages") or []

    try:
        for i in range(count):
            if job.get("cancel"):
                job["message"] = "تم الإلغاء"
                break
            project = store.load_project(project_id)
            preset = preset_pages[i] if i < len(preset_pages) else None
            if preset and preset.get("prompt"):
                prompt = preset["prompt"]
            else:
                prompt = providers.build_prompt(
                    theme=theme,
                    custom_subject=subject,
                    style=style,
                    audience=audience,
                    variant=providers.VARIANTS[i % len(providers.VARIANTS)] if provider != "procedural" else "",
                )
            if not options.get("with_captions"):
                caption = ""
            elif preset:
                caption = preset.get("caption") or _caption_for(theme, i, options)
            else:
                caption = _caption_for(theme, i, options)
            page = store.create_page(
                project_id,
                prompt=prompt,
                theme=theme,
                caption=caption,
                provider=provider,
                procedural_style=providers.THEMES.get(theme, {}).get("procedural", "mandala"),
                settings={"mode": options.get("mode", "auto"),
                          "thickness": options.get("thickness", project.get("thickness", 2))},
            )
            item = {"page_id": page["id"], "index": i, "status": "working", "error": ""}
            job["items"].append(item)
            job["message"] = f"جارٍ توليد الصفحة {i + 1} من {count}…"
            store.update_page(project_id, page["id"], {"status": "generating"})
            try:
                project = store.load_project(project_id)
                result = pipeline.generate_page(project, page, options)
                store.update_page(project_id, page["id"], {
                    "status": "ready",
                    "provider_label": result["provider_label"],
                    "seed": result["seed"],
                })
                item["status"] = "ready"
            except Exception as exc:  # noqa: BLE001
                message = str(exc) or exc.__class__.__name__
                store.update_page(project_id, page["id"], {"status": "error", "error": message})
                item["status"] = "error"
                item["error"] = message
                job["failed"] += 1
                # خطأ متكرر في المزوّد → نوقف المهمة بدل تكرار الفشل
                if job["failed"] >= 3 and job["done"] == 0:
                    job["message"] = f"توقفت المهمة: {message}"
                    break
            job["done"] += 1
        job["status"] = "cancelled" if job.get("cancel") else "done"
        if job["status"] == "done" and job["failed"] and job["done"] == job["failed"]:
            job["status"] = "error"
        job["message"] = job.get("message") if job["status"] == "cancelled" else "اكتمل التوليد"
    except Exception as exc:  # noqa: BLE001
        job["status"] = "error"
        job["message"] = f"خطأ غير متوقع: {exc}"
        traceback.print_exc()
    job["finished"] = time.time()
