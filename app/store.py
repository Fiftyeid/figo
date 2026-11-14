"""تخزين المشاريع على القرص (JSON + ملفات صور) وإعدادات التطبيق."""
from __future__ import annotations

import json
import os
import shutil
import threading
import time
import uuid
from pathlib import Path
from typing import Any

from . import config as C

_lock = threading.RLock()

DEFAULT_PROJECT = {
    "title": "كتاب تلوين",
    "subtitle": "",
    "author": "اسم المؤلف",
    "language": "ar",
    "trim": "8.5x11",
    "paper": "white",
    "bleed": False,
    "single_sided": True,
    "style": "medium",
    "audience": "kids_mid",
    "theme": "animals",
    "provider": "procedural",
    "thickness": 2,
    "threshold": 150,
    "captions": False,
    "description": "",
    "keywords": [],
    "categories": ["Children's Books > Coloring Books"],
    "price": 8.99,
    "printing_cost": 2.30,
    "ai_generated": True,
    "front_matter": {
        "title_page": True,
        "copyright_page": True,
        "belongs_page": True,
        "blank_after_front": True,
    },
    "cover": {
        "background": "#F6F1E7",
        "accent": "#B4562F",
        "cover_page_id": None,
        "blurb": "",
        "show_title_on_spine": True,
    },
}


def _now() -> float:
    return time.time()


# ---------------------------------------------------------------------------
# إعدادات التطبيق (المفاتيح تُحفظ محليًا فقط)
# ---------------------------------------------------------------------------
def load_settings() -> dict:
    if C.SETTINGS_FILE.exists():
        try:
            return json.loads(C.SETTINGS_FILE.read_text("utf-8"))
        except Exception:
            return {}
    return {}


def save_settings(data: dict) -> dict:
    with _lock:
        current = load_settings()
        current.update(data or {})
        C.SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        C.SETTINGS_FILE.write_text(json.dumps(current, ensure_ascii=False, indent=2), "utf-8")
        return current


def public_settings() -> dict:
    """إعدادات آمنة للعرض: نُخفي المفاتيح ونكشف وجودها فقط."""
    s = load_settings()
    keys = s.get("api_keys", {})
    return {
        "has_keys": {k: bool(v) for k, v in keys.items()},
        "local_sd_url": s.get("local_sd_url", "http://127.0.0.1:7860"),
        "freellmapi_url": s.get("freellmapi_url", C.FREELLMAPI_URL),
        "freellmapi_model": s.get("freellmapi_model", C.FREELLMAPI_TEXT_MODEL),
        "freellmapi_image_model": s.get("freellmapi_image_model", C.FREELLMAPI_IMAGE_MODEL),
        "text_provider": s.get("text_provider", "auto"),
        "model": s.get("model", ""),
        "last_project": s.get("last_project", ""),
    }


# ---------------------------------------------------------------------------
# المشاريع
# ---------------------------------------------------------------------------
def project_dir(pid: str) -> Path:
    return C.PROJECTS_DIR / pid


def _sanitize_name(pid: str) -> str:
    if not pid or "/" in pid or "\\" in pid or ".." in pid:
        raise ValueError("معرّف مشروع غير صالح")
    return pid


def new_project(data: dict | None = None) -> dict:
    data = data or {}
    pid = uuid.uuid4().hex[:12]
    project = json.loads(json.dumps(DEFAULT_PROJECT))
    for k, v in data.items():
        if k in project and v is not None:
            if isinstance(project[k], dict) and isinstance(v, dict):
                project[k].update(v)
            else:
                project[k] = v
    project["id"] = pid
    project["created"] = _now()
    project["updated"] = _now()
    project["pages"] = []
    project_dir(pid).mkdir(parents=True, exist_ok=True)
    (project_dir(pid) / "pages").mkdir(exist_ok=True)
    (project_dir(pid) / "out").mkdir(exist_ok=True)
    save_project(project)
    save_settings({"last_project": pid})
    return project


def list_projects() -> list[dict]:
    items = []
    for d in sorted(C.PROJECTS_DIR.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True):
        f = d / "project.json"
        if f.exists():
            try:
                p = json.loads(f.read_text("utf-8"))
                items.append({
                    "id": p.get("id"),
                    "title": p.get("title"),
                    "author": p.get("author"),
                    "pages": len([x for x in p.get("pages", []) if x.get("status") == "ready"]),
                    "updated": p.get("updated"),
                    "trim": p.get("trim"),
                })
            except Exception:
                continue
    return items


def load_project(pid: str) -> dict:
    pid = _sanitize_name(pid)
    f = project_dir(pid) / "project.json"
    if not f.exists():
        raise FileNotFoundError("المشروع غير موجود")
    return json.loads(f.read_text("utf-8"))


def save_project(project: dict) -> dict:
    with _lock:
        project["updated"] = _now()
        d = project_dir(_sanitize_name(project["id"]))
        d.mkdir(parents=True, exist_ok=True)
        (d / "project.json").write_text(
            json.dumps(project, ensure_ascii=False, indent=2), "utf-8"
        )
        return project


def update_project(pid: str, patch: dict) -> dict:
    with _lock:
        p = load_project(pid)
        for k, v in (patch or {}).items():
            if k in ("id", "created", "pages"):
                continue
            if isinstance(p.get(k), dict) and isinstance(v, dict):
                p[k].update(v)
            else:
                p[k] = v
        return save_project(p)


def delete_project(pid: str) -> None:
    d = project_dir(_sanitize_name(pid))
    if d.exists():
        shutil.rmtree(d, ignore_errors=True)


# ---------------------------------------------------------------------------
# الصفحات
# ---------------------------------------------------------------------------
def page_paths(pid: str, page_id: str) -> dict:
    base = project_dir(_sanitize_name(pid)) / "pages" / page_id
    return {
        "source": base.with_suffix(".source.png"),
        "art": base.with_suffix(".art.png"),
        "thumb": base.with_suffix(".thumb.png"),
    }


def create_page(
    pid: str,
    *,
    prompt: str,
    theme: str,
    caption: str = "",
    provider: str = "",
    procedural_style: str = "",
    settings: dict | None = None,
):
    with _lock:
        project = load_project(pid)
        page = {
            "id": uuid.uuid4().hex[:10],
            "prompt": prompt,
            "theme": theme,
            "caption": caption,
            "provider": provider or project.get("provider", "procedural"),
            "procedural_style": procedural_style,
            "status": "queued",
            "error": "",
            "settings": {
                "thickness": project.get("thickness", 2),
                "threshold": project.get("threshold", 150),
                "mode": "auto",
                **(settings or {}),
            },
            "created": _now(),
        }
        project["pages"].append(page)
        save_project(project)
        return page


def update_page(pid: str, page_id: str, patch: dict) -> dict:
    with _lock:
        project = load_project(pid)
        for page in project["pages"]:
            if page["id"] == page_id:
                for k, v in patch.items():
                    if k == "settings" and isinstance(v, dict):
                        page["settings"].update(v)
                    elif k not in ("id",):
                        page[k] = v
                save_project(project)
                return page
        raise KeyError("الصفحة غير موجودة")


def get_page(pid: str, page_id: str) -> dict:
    project = load_project(pid)
    for page in project["pages"]:
        if page["id"] == page_id:
            return page
    raise KeyError("الصفحة غير موجودة")


def delete_page(pid: str, page_id: str) -> None:
    with _lock:
        project = load_project(pid)
        project["pages"] = [p for p in project["pages"] if p["id"] != page_id]
        save_project(project)
        for path in page_paths(pid, page_id).values():
            path.unlink(missing_ok=True)


def reorder_pages(pid: str, order: list[str]) -> dict:
    with _lock:
        project = load_project(pid)
        index = {p["id"]: p for p in project["pages"]}
        new = [index[i] for i in order if i in index]
        new += [p for p in project["pages"] if p["id"] not in order]
        project["pages"] = new
        return save_project(project)
