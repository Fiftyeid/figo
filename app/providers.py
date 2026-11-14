"""تكامل مع محرّكات الذكاء الاصطناعي + بناء الأوامر النصية (prompts)."""
from __future__ import annotations

import base64
import io
import json
import random
import time
from typing import Any

import httpx

from . import config as C


class ProviderError(RuntimeError):
    """خطأ قابل للعرض للمستخدم."""


# ---------------------------------------------------------------------------
# الموضوعات الجاهزة
# ---------------------------------------------------------------------------
THEMES = {
    "animals": {
        "label": "حيوانات لطيفة",
        "subject": "cute baby animals (lion cub, elephant, giraffe, panda, fox, bunny)",
        "procedural": "floral",
    },
    "dinosaurs": {
        "label": "ديناصورات",
        "subject": "friendly cartoon dinosaurs in playful scenes (T-rex, triceratops, stegosaurus)",
        "procedural": "geometric",
    },
    "unicorns": {
        "label": "يونيكورن وسحر",
        "subject": "cute unicorns, rainbows, stars and clouds",
        "procedural": "floral",
    },
    "ocean": {
        "label": "عالم البحر",
        "subject": "cute sea creatures (turtle, octopus, seahorse, fish, starfish, whale)",
        "procedural": "mandala",
    },
    "space": {
        "label": "الفضاء",
        "subject": "cute astronauts, rockets, planets and friendly aliens",
        "procedural": "geometric",
    },
    "mandala": {
        "label": "ماندالا",
        "subject": "intricate symmetrical mandala with floral and geometric motifs",
        "procedural": "mandala",
    },
    "flowers": {
        "label": "زهور ونباتات",
        "subject": "bouquet of flowers, leaves and botanical details",
        "procedural": "floral",
    },
    "geometric": {
        "label": "أشكال هندسية",
        "subject": "geometric tessellation and optical patterns",
        "procedural": "geometric",
    },
    "vehicles": {
        "label": "سيارات ومركبات",
        "subject": "friendly trucks, cars, tractors, airplanes and boats",
        "procedural": "geometric",
    },
    "festive": {
        "label": "أعياد ومناسبات",
        "subject": "festive scenes with gifts, balloons, lanterns and decorations",
        "procedural": "mandala",
    },
}

AUDIENCES = {
    "kids": "young children ages 3-6, very large simple shapes, extra thick outlines",
    "kids_mid": "children ages 6-10, medium detail, clear bold outlines",
    "teens": "teens and adults, moderate detail",
    "adults": "adults, detailed and intricate line work",
}

STYLE_HINT = {
    "simple": "minimal detail, extra thick bold outlines, large open areas to color",
    "medium": "balanced detail, thick clean outlines, a few decorative elements",
    "detailed": "intricate fine detail, thin crisp outlines, rich patterns",
}

NEGATIVE_PROMPT = (
    "color, colored, shading, shadow, gradient, grayscale, gray, greyscale, photo, "
    "realistic, 3d render, text, letters, watermark, signature, logo, frame, border, "
    "blurry, noise, low contrast, filled black areas, dark background"
)

LINE_ART_PROMPT = (
    "Black and white coloring book page for {audience}. Subject: {subject}. {style} "
    "Pure white background, crisp continuous black outlines, no shading, no gray tones, "
    "no color, not filled in, clean vector-like line art, centered composition, "
    "plenty of white space, full page, printable at 300 dpi, no text, no border."
)


def build_prompt(
    theme: str = "animals",
    custom_subject: str = "",
    style: str = "medium",
    audience: str = "kids_mid",
    variant: str = "",
) -> str:
    theme_info = THEMES.get(theme, THEMES["animals"])
    subject = custom_subject.strip() or theme_info["subject"]
    if variant:
        subject = f"{subject}, {variant}"
    return LINE_ART_PROMPT.format(
        audience=AUDIENCES.get(audience, AUDIENCES["kids_mid"]),
        subject=subject,
        style=STYLE_HINT.get(style, STYLE_HINT["medium"]),
    )


VARIANTS = [
    "different pose",
    "playing with a friend",
    "surrounded by decorative flowers",
    "with a simple background pattern",
    "holding a small object",
    "sitting on a rock",
    "wearing a cute accessory",
    "under a starry sky pattern",
]


# ---------------------------------------------------------------------------
# المحرّكات
# ---------------------------------------------------------------------------
def _base_url(url: str, default: str) -> str:
    base = (url or default).strip().rstrip("/")
    if not base.startswith("http"):
        base = "http://" + base
    if not base.endswith("/v1"):
        base += "/v1"
    return base


def freellmapi_models(url: str, key: str, timeout: float = 20.0) -> dict:
    """يقرأ كتالوج النماذج من FreeLLMAPI للتحقق من الاتصال ومعرفة النماذج المتاحة."""
    base = _base_url(url, C.FREELLMAPI_URL)
    if not key:
        raise ProviderError("أدخل المفتاح الموحّد من لوحة FreeLLMAPI (يبدأ بـ freellmapi-).")
    try:
        with httpx.Client(timeout=timeout) as client:
            r = client.get(f"{base}/models", headers={"Authorization": f"Bearer {key}"})
            if r.status_code in (401, 403):
                raise ProviderError(
                    "المفتاح الموحّد غير صحيح. انسخه من لوحة FreeLLMAPI على "
                    "http://localhost:3001 (صفحة Keys) — يبدأ بـ freellmapi-."
                )
            r.raise_for_status()
            data = r.json()
    except ProviderError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise ProviderError(
            f"تعذّر الوصول إلى FreeLLMAPI على {base}. شغّل الخدمة أولًا "
            "(desktop app أو docker أو npx freellmapi) وتأكد من المفتاح. "
            f"({exc.__class__.__name__})"
        ) from exc
    items = data.get("data") if isinstance(data, dict) else None
    ids = []
    for item in items or []:
        if isinstance(item, dict):
            ids.extend(str(item.get(k)) for k in ("id", "model", "name") if item.get(k))
        elif isinstance(item, str):
            ids.append(item)
    ids = sorted(set(ids))
    image_kw = ("flux", "image", "imagen", "dalle", "dall-e", "sdxl", "stable-diffusion",
                "kolors", "pollinations", "photo", "vision-image")
    image_models = [i for i in ids if any(k in i.lower() for k in image_kw)]
    return {
        "base_url": base,
        "count": len(ids),
        "models": ids[:60],
        "image_models": image_models[:30],
        "routed_via": r.headers.get("x-routed-via", ""),
    }


def _extract_image(resp: httpx.Response, timeout: float) -> bytes:
    """يستخرج بايتات الصورة من ردّ OpenAI-compatible (b64 / url / binary)."""
    ctype = (resp.headers.get("content-type") or "").lower()
    if ctype.startswith("image/"):
        return resp.content
    try:
        data = resp.json()
    except Exception:  # noqa: BLE001
        if resp.content[:4] in (b"\x89PNG", b"\xff\xd8\xff\xe0", b"\xff\xd8\xff\xe1"):
            return resp.content
        raise ProviderError("ردّ غير مفهوم من خدمة الصور.")
    if isinstance(data, dict):
        items = data.get("data") or data.get("images") or data.get("output")
        if isinstance(items, str):
            items = [items]
        if isinstance(items, dict):
            items = [items]
        for item in items or []:
            if isinstance(item, str):
                if item.startswith("http"):
                    with httpx.Client(timeout=timeout) as client:
                        img = client.get(item)
                        img.raise_for_status()
                        return img.content
                if item.startswith("data:") or len(item) > 500:
                    return base64.b64decode(item.split(",", 1)[-1])
            elif isinstance(item, dict):
                if item.get("b64_json"):
                    return base64.b64decode(item["b64_json"])
                url = item.get("url") or item.get("image") or item.get("image_url")
                if url:
                    if str(url).startswith("data:"):
                        return base64.b64decode(str(url).split(",", 1)[-1])
                    with httpx.Client(timeout=timeout) as client:
                        img = client.get(url)
                        img.raise_for_status()
                        return img.content
    raise ProviderError("لم تُرجع الخدمة أي صورة. جرّب موديل صور آخر أو أعد المحاولة.")


def _freellmapi(
    prompt: str,
    api_key: str,
    base_url: str,
    model: str,
    size: tuple[int, int],
    timeout: float,
) -> tuple[bytes, str]:
    base = _base_url(base_url, C.FREELLMAPI_URL)
    if not api_key:
        raise ProviderError(
            "أدخل المفتاح الموحّد لـ FreeLLMAPI أولًا (من لوحة التحكم على "
            "http://localhost:3001 → صفحة Keys)."
        )
    payload = {
        "model": (model or C.FREELLMAPI_IMAGE_MODEL).strip() or "auto",
        "prompt": prompt,
        "n": 1,
        "size": f"{size[0]}x{size[1]}",
        "response_format": "b64_json",
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "image/png, application/json",
    }
    try:
        with httpx.Client(timeout=timeout) as client:
            r = client.post(f"{base}/images/generations", headers=headers, json=payload)
            if r.status_code in (400, 422):
                # بعض المزوّدين لا يقبلون response_format أو size
                for drop in (["response_format"], ["size"], ["response_format", "size"]):
                    retry = {k: v for k, v in payload.items() if k not in drop}
                    r = client.post(f"{base}/images/generations", headers=headers, json=retry)
                    if r.status_code < 400:
                        break
            r.raise_for_status()
        used = r.headers.get("x-routed-via") or payload["model"]
        return _extract_image(r, timeout), f"FreeLLMAPI · {used}"
    except ProviderError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise _friendly_http_error(exc, "FreeLLMAPI") from exc


def generate(
    provider: str,
    prompt: str,
    api_key: str = "",
    local_url: str = "http://127.0.0.1:7860",
    size: tuple[int, int] = (2048, 2560),
    seed: int | None = None,
    timeout: float = 180.0,
    base_url: str = "",
    model: str = "",
) -> tuple[bytes, str]:
    """يعيد (بيانات الصورة، وصف المحرّك) أو يرفع ProviderError برسالة عربية."""
    provider = provider or "procedural"
    if provider == "openai":
        return _openai(prompt, api_key, timeout)
    if provider == "stability":
        return _stability(prompt, api_key, timeout, seed)
    if provider == "replicate":
        return _replicate(prompt, api_key, timeout, seed)
    if provider == "local_sd":
        return _local_sd(prompt, local_url, size, timeout, seed)
    if provider == "freellmapi":
        return _freellmapi(prompt, api_key, base_url, model, size, timeout)
    raise ProviderError("محرّك غير معروف.")


def _friendly_http_error(exc: Exception, label: str) -> ProviderError:
    if isinstance(exc, httpx.ConnectError):
        return ProviderError(f"تعذّر الاتصال بخدمة {label}. تحقق من الإنترنت أو من عنوان الخدمة.")
    if isinstance(exc, httpx.ReadTimeout):
        return ProviderError(f"انتهت مهلة الانتظار من {label}. أعد المحاولة.")
    if isinstance(exc, httpx.HTTPStatusError):
        code = exc.response.status_code
        body = exc.response.text[:300]
        if code in (401, 403):
            return ProviderError(f"مفتاح API غير صالح أو غير مصرّح لـ {label}.")
        if code == 429:
            return ProviderError(f"تجاوزت حدود الاستخدام لـ {label}. انتظر قليلًا ثم أعد المحاولة.")
        return ProviderError(f"{label} أعاد الخطأ {code}: {body}")
    return ProviderError(f"فشل الاتصال بـ {label}: {exc}")


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode()


def _openai(prompt: str, api_key: str, timeout: float, model: str = "gpt-image-1") -> tuple[bytes, str]:
    if not api_key:
        raise ProviderError("أدخل مفتاح OpenAI API أولًا (يُحفظ على جهازك فقط).")
    url = "https://api.openai.com/v1/images/generations"
    payload = {
        "model": model,
        "prompt": prompt,
        "size": "1024x1536",
        "n": 1,
        "quality": "high",
        "background": "opaque",
        "output_format": "png",
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    try:
        with httpx.Client(timeout=timeout) as client:
            r = client.post(url, headers=headers, json=payload)
            r.raise_for_status()
            data = r.json()
        item = data["data"][0]
        if item.get("b64_json"):
            return base64.b64decode(item["b64_json"]), "OpenAI gpt-image-1"
        if item.get("url"):
            with httpx.Client(timeout=timeout) as client:
                img = client.get(item["url"])
                img.raise_for_status()
                return img.content, "OpenAI gpt-image-1"
        raise ProviderError("لم تُرجع OpenAI أي صورة. حاول تعديل الوصف.")
    except ProviderError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise _friendly_http_error(exc, "OpenAI") from exc


def _stability(prompt: str, api_key: str, timeout: float, seed: int | None) -> tuple[bytes, str]:
    if not api_key:
        raise ProviderError("أدخل مفتاح Stability AI أولًا.")
    url = "https://api.stability.ai/v2beta/stable-image/generate/core"
    headers = {"Authorization": f"Bearer {api_key}", "Accept": "image/*"}
    files = {"prompt": (None, prompt), "negative_prompt": (None, NEGATIVE_PROMPT),
             "aspect_ratio": (None, "2:3"), "output_format": (None, "png")}
    if seed is not None:
        files["seed"] = (None, str(seed))
    try:
        with httpx.Client(timeout=timeout) as client:
            r = client.post(url, headers=headers, files=files)
            r.raise_for_status()
            return r.content, "Stability AI"
    except Exception as exc:  # noqa: BLE001
        raise _friendly_http_error(exc, "Stability AI") from exc


def _replicate(prompt: str, api_key: str, timeout: float, seed: int | None) -> tuple[bytes, str]:
    if not api_key:
        raise ProviderError("أدخل مفتاح Replicate أولًا.")
    url = "https://api.replicate.com/v1/models/black-forest-labs/flux-schnell/predictions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Prefer": "wait",
    }
    payload = {
        "input": {
            "prompt": prompt,
            "aspect_ratio": "2:3",
            "output_format": "png",
            "num_outputs": 1,
            "output_quality": 95,
        }
    }
    if seed is not None:
        payload["input"]["seed"] = seed
    try:
        with httpx.Client(timeout=timeout) as client:
            r = client.post(url, headers=headers, json=payload)
            r.raise_for_status()
            pred = r.json()
            deadline = time.time() + timeout
            while pred.get("status") in ("starting", "processing") and time.time() < deadline:
                time.sleep(2)
                poll = client.get(pred["urls"]["get"], headers={"Authorization": f"Bearer {api_key}"})
                poll.raise_for_status()
                pred = poll.json()
        if pred.get("status") != "succeeded":
            raise ProviderError(f"Replicate لم يُكمل الصورة (الحالة: {pred.get('status')}).")
        out = pred.get("output")
        img_url = out[0] if isinstance(out, list) and out else out if isinstance(out, str) else None
        if not img_url:
            raise ProviderError("لم تُرجع Replicate رابط صورة.")
        with httpx.Client(timeout=timeout) as client:
            img = client.get(img_url)
            img.raise_for_status()
            return img.content, "Replicate FLUX"
    except ProviderError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise _friendly_http_error(exc, "Replicate") from exc


def _local_sd(
    prompt: str,
    local_url: str,
    size: tuple[int, int],
    timeout: float,
    seed: int | None,
) -> tuple[bytes, str]:
    base = (local_url or "http://127.0.0.1:7860").rstrip("/")
    if not base.startswith("http"):
        base = "http://" + base
    payload = {
        "prompt": prompt,
        "negative_prompt": NEGATIVE_PROMPT,
        "width": int(size[0] // 8 * 8),
        "height": int(size[1] // 8 * 8),
        "steps": 30,
        "cfg_scale": 6.5,
        "sampler_name": "DPM++ 2M Karras",
        "seed": seed if seed is not None else -1,
    }
    try:
        with httpx.Client(timeout=timeout) as client:
            r = client.post(f"{base}/sdapi/v1/txt2img", json=payload)
            r.raise_for_status()
            data = r.json()
        imgs = data.get("images") or []
        if not imgs:
            raise ProviderError("Stable Diffusion المحلي لم يُرجع صورة.")
        raw = imgs[0].split(",", 1)[-1]
        return base64.b64decode(raw), "Stable Diffusion محلي"
    except ProviderError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise ProviderError(
            "تعذّر الوصول إلى Stable Diffusion المحلي. شغّل Automatic1111 مع الخيار "
            f"--api على العنوان {base} ثم أعد المحاولة. ({exc.__class__.__name__})"
        ) from exc


def procedural(style: str, seed: int, size: tuple[int, int], detail: float, thickness: int):
    """يولّد صفحة محليًا ويعيدها كبيانات PNG."""
    from . import lineart as L

    img = L.procedural_art(
        style=style,
        seed=seed,
        width=size[0],
        height=size[1],
        detail=detail,
        thickness=thickness,
    )
    buf = io.BytesIO()
    img.convert("L").save(buf, format="PNG")
    return buf.getvalue(), "محرّك محلي"
