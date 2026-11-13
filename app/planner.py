"""مخطِّط الكتاب: يحوّل «عنوان + فكرة» إلى خطة كتاب كاملة.

- مع وجود مفتاح OpenAI: يستخدم نموذجًا لغويًا لتوليد خطة غنية (وصف، كلمات
  مفتاحية، أوامر رسم لكل صفحة، نص الغلاف الخلفي).
- بدون مفاتيح أو عند الفشل: مخطِّط محلي ذكي يبني الخطة من قوالب الموضوعات
  (يعمل دائمًا وبلا إنترنت).
"""
from __future__ import annotations

import json
import random
import re
from typing import Any

import httpx

from . import config as C, providers

# ---------------------------------------------------------------------------
# قوالب الموضوعات: (موضوع إنجليزي للرسم، تعليق عربي)
# ---------------------------------------------------------------------------
SCENES: dict[str, list[tuple[str, str]]] = {
    "animals": [
        ("a cute lion cub sitting on a rock", "شبل الأسد"),
        ("a happy baby elephant splashing water", "الفيل الصغير"),
        ("a playful panda eating bamboo", "الباندا المرحة"),
        ("a sleepy koala hugging a branch", "الكوالا النعسان"),
        ("a brave little fox in the forest", "الثعلب الشجاع"),
        ("a fluffy bunny in a flower meadow", "الأرنب في الحديقة"),
        ("a friendly giraffe eating leaves", "الزرافة الطويلة"),
        ("a curious monkey swinging on a vine", "القرد الفضولي"),
        ("a cute hedgehog with mushrooms", "القنفذ الصغير"),
        ("a smiling turtle on the beach", "السلحفاة السعيدة"),
        ("a puppy chasing a butterfly", "الجرو والفراشة"),
        ("a kitten playing with yarn", "القطة والكرة"),
    ],
    "dinosaurs": [
        ("a friendly T-rex waving hello", "ديناصور التيرانوصور"),
        ("a triceratops eating leaves", "التريسيراتوبس"),
        ("a stegosaurus with flower patterns", "ستيجوصور مزيّن"),
        ("a baby dinosaur hatching from an egg", "الديناصور الصغير"),
        ("a pterodactyl flying over mountains", "الديناصور الطائر"),
        ("a brachiosaurus reaching tall trees", "الديناصور العملاق"),
        ("dinosaurs playing near a volcano", "لعب الديناصورات"),
        ("a dinosaur family walking together", "عائلة الديناصورات"),
        ("a dinosaur riding a bicycle", "ديناصور على الدراجة"),
        ("a dinosaur under a starry sky", "ديناصور تحت النجوم"),
    ],
    "unicorns": [
        ("a cute unicorn with a flowing mane", "اليونيكورن الجميل"),
        ("a baby unicorn on a rainbow", "اليونيكورن والقرن"),
        ("a unicorn surrounded by stars", "اليونيكورن والنجوم"),
        ("a unicorn drinking from a waterfall", "اليونيكورن والشلال"),
        ("a unicorn with butterfly friends", "اليونيكورن والفراشات"),
        ("a unicorn wearing a flower crown", "تاج الزهور"),
        ("a flying unicorn over clouds", "اليونيكورن الطائر"),
        ("a unicorn in a magic garden", "الحديقة السحرية"),
        ("a unicorn sipping tea", "حفلة الشاي"),
        ("a unicorn under a big moon", "القمر الكبير"),
    ],
    "ocean": [
        ("a smiling sea turtle swimming", "السلحفاة البحرية"),
        ("a friendly octopus with big eyes", "الأخطبوط اللطيف"),
        ("a seahorse in a coral garden", "حصان البحر"),
        ("a whale spouting water", "الحوت الكبير"),
        ("a starfish on a sandy beach", "نجمة البحر"),
        ("a clownfish hiding in anemone", "السمكة المهرّج"),
        ("a dolphin jumping over waves", "الدولفين المرح"),
        ("a crab walking sideways", "السلطعون"),
        ("a jellyfish floating gracefully", "قنديل البحر"),
        ("a treasure chest on the seabed", "صندوق الكنز"),
    ],
    "space": [
        ("a cute astronaut floating in space", "رائد الفضاء"),
        ("a rocket blasting off with stars", "الصاروخ"),
        ("a friendly alien waving", "الكائن الفضائي"),
        ("a planet with rings and moons", "الكوكب والحلقات"),
        ("an astronaut walking on the moon", "على القمر"),
        ("a space dog in a helmet", "كلب الفضاء"),
        ("a satellite orbiting the earth", "القمر الصناعي"),
        ("a rocket flying past comets", "بين المذنبات"),
        ("a space station in orbit", "محطة الفضاء"),
        ("a child dreaming of stars", "حلم النجوم"),
    ],
    "flowers": [
        ("a bouquet of roses and leaves", "باقة الورود"),
        ("a sunflower with detailed petals", "زهرة الشمس"),
        ("a tulip garden with butterflies", "حديقة الزهور"),
        ("a wreath of wildflowers", "إكليل الزهور"),
        ("a potted plant on a windowsill", "النبتة في الأصيص"),
        ("a lotus flower on calm water", "زهرة اللوتس"),
        ("a branch of cherry blossom", "زهر الكرز"),
        ("a cactus with small flowers", "الصبارة المزهرة"),
        ("a floral heart arrangement", "قلب من الزهور"),
        ("a garden archway covered in vines", "قوس الحديقة"),
    ],
    "geometric": [
        ("a symmetrical mandala with petals", "ماندالا الأزهار"),
        ("a star-shaped geometric mandala", "نجمة هندسية"),
        ("a circular pattern with dots", "دائرة النقاط"),
        ("a hexagonal tessellation pattern", "الأشكال السداسية"),
        ("a spiral geometric composition", "اللولب الهندسي"),
        ("a diamond mandala with ornaments", "ماندالا الماس"),
        ("a kaleidoscope flower pattern", "زهرة المشكال"),
        ("a layered rosette design", "الوردة المتعددة"),
        ("a maze of triangles", "متاهة المثلثات"),
        ("a sunburst radial pattern", "الشمس المشعّة"),
    ],
    "vehicles": [
        ("a friendly dump truck", "الشاحنة القوية"),
        ("a happy school bus", "الباص المدرسي"),
        ("a tractor on a farm", "التراكتور"),
        ("a helicopter over clouds", "الهليكوبتر"),
        ("a sailboat on the sea", "القارب الشراعي"),
        ("a fire truck with a ladder", "سيارة الإطفاء"),
        ("a race car on a track", "سيارة السباق"),
        ("a train crossing a bridge", "القطار"),
        ("a hot air balloon in the sky", "المنطاد"),
        ("a bicycle with a basket", "الدراجة"),
    ],
    "festive": [
        ("birthday balloons and a cake", "عيد الميلاد"),
        ("wrapped gifts with ribbons", "الهدايا"),
        ("a decorated birthday cake", "كعكة العيد"),
        ("lanterns hanging in the sky", "الفوانيس"),
        ("a festive wreath with berries", "إكليل الاحتفال"),
        ("party hats and confetti", "حفلة صاخبة"),
        ("a gingerbread house", "بيت الزنجبيل"),
        ("stockings by a fireplace", "جوارب العيد"),
        ("a decorated tree with stars", "شجرة الزينة"),
        ("a gift box overflowing with hearts", "صندوق القلوب"),
    ],
}

THEME_WORDS: dict[str, list[str]] = {
    "animals": ["حيوان", "حيوانات", "قطة", "كلب", "أسد", "فيل", "باندا", "أرنب", "مزرعة", "غابة", "animal", "cat", "dog"],
    "dinosaurs": ["ديناصور", "ديناصورات", "تيرانوصور", "dinosaur", "trex", "rex"],
    "unicorns": ["يونيكورن", "حصان مجنح", "سحر", "قوس قزح", "unicorn", "rainbow", "magic"],
    "ocean": ["بحر", "محيط", "سمك", "سمكة", "حوت", "دولفين", "سلحفاة", "مرجان", "ocean", "sea", "fish"],
    "space": ["فضاء", "صاروخ", "كوكب", "نجوم", "قمر", "رائد", "مجرة", "space", "rocket", "planet"],
    "flowers": ["زهر", "زهور", "وردة", "ورود", "نبات", "حديقة", "طبيعة", "flower", "rose", "garden", "botanical"],
    "geometric": ["ماندالا", "هندسي", "زخرف", "أشكال", "نمط", "mandala", "geometric", "pattern"],
    "vehicles": ["سيارة", "شاحنة", "طائرة", "قطار", "دراجة", "مركبة", "قارب", "truck", "car", "train"],
    "festive": ["عيد", "حفلة", "هدية", "هدايا", "ميلاد", "احتفال", "فانوس", "party", "gift", "birthday"],
}

AR_THEME_LABEL = {
    "animals": "حيوانات لطيفة",
    "dinosaurs": "ديناصورات",
    "unicorns": "يونيكورن وسحر",
    "ocean": "عالم البحر",
    "space": "الفضاء",
    "flowers": "زهور ونباتات",
    "geometric": "ماندالا وأشكال هندسية",
    "vehicles": "سيارات ومركبات",
    "festive": "أعياد ومناسبات",
}

PALETTES = [
    {"key": "warm", "name": "دافئ كلاسيكي", "background": "#F6F1E7", "accent": "#B4562F"},
    {"key": "garden", "name": "طبيعي هادئ", "background": "#EAF0E6", "accent": "#3F6B4A"},
    {"key": "modern", "name": "حديث نظيف", "background": "#F5F5F2", "accent": "#2A2A2E"},
    {"key": "night", "name": "ليلي فخم", "background": "#212A36", "accent": "#D9A441"},
    {"key": "rose", "name": "وردي رقيق", "background": "#FBEDF0", "accent": "#B04A63"},
    {"key": "sky", "name": "سماوي", "background": "#E9F1F7", "accent": "#2C6A93"},
]


# ---------------------------------------------------------------------------
# أدوات
# ---------------------------------------------------------------------------
def detect_theme(text: str, fallback: str = "animals") -> str:
    low = (text or "").lower()
    best, score = fallback, 0
    for theme, words in THEME_WORDS.items():
        hits = sum(1 for w in words if w.lower() in low)
        if hits > score:
            best, score = theme, hits
    return best


AR_STOP = {
    "كتاب", "عن", "في", "من", "على", "مع", "هذا", "هذه", "التي", "الذي", "للأطفال",
    "الأطفال", "رسمة", "صفحة", "يكون", "جميع", "كل", "بين", "حتى", "أيضا", "أيضًا",
    "the", "and", "for", "with", "book", "pages",
}


def ar_count(n: int, singular: str = "رسمة", dual: str = "رسمتان", few: str = "رسمات", many: str = "رسمة") -> str:
    """صياغة عربية سليمة لعدد الرسومات."""
    if n == 1:
        return f"{singular} واحدة"
    if n == 2:
        return dual
    if 3 <= n <= 10:
        return f"{n} {few}"
    return f"{n} {many}"


def _keywords_from(idea: str, theme: str, title: str, language: str) -> list[str]:
    base = [AR_THEME_LABEL.get(theme, "تلوين"), "كتاب تلوين", title.strip()]
    words = [w for w in re.findall(r"[\u0600-\u06FFa-zA-Z]{3,}", idea or "")
             if w not in AR_STOP and w.strip() not in AR_STOP]
    seen, out = set(), []
    for w in base + words:
        w = w.strip()
        if not w or w in seen:
            continue
        seen.add(w)
        out.append(w)
        if len(out) == 7:
            break
    defaults = ["تلوين للأطفال", "رسم وتلوين", "هدية", "أنشطة فنية", "استرخاء"]
    for d in defaults:
        if len(out) >= 7:
            break
        if d not in seen:
            seen.add(d)
            out.append(d)
    return out[:7]


def _page_list(theme: str, count: int, idea: str, seed: int, audience: str) -> list[dict]:
    rng = random.Random(seed)
    scenes = SCENES.get(theme, SCENES["animals"])
    count = max(1, count)
    pages: list[dict] = []
    order = list(range(len(scenes)))
    rng.shuffle(order)
    extra_idea = idea.strip() if re.search(r"[A-Za-z]", idea or "") else ""
    for i in range(count):
        subject, caption = scenes[order[i % len(order)]]
        if i >= len(scenes):
            subject += f", variation {i // len(scenes) + 1}"
        if extra_idea:
            subject = f"{subject} ({extra_idea})"
        prompt = providers.build_prompt(
            theme=theme,
            custom_subject=subject,
            style="medium",
            audience=audience,
        )
        pages.append({"prompt": prompt, "caption": caption, "subject": subject})
    return pages


def local_plan(
    title: str,
    idea: str,
    *,
    language: str = "ar",
    audience: str = "kids_mid",
    style: str = "medium",
    art_pages: int = 12,
    theme: str | None = None,
) -> dict:
    theme = theme or detect_theme(f"{idea} {title}", "animals")
    label = AR_THEME_LABEL.get(theme, "تلوين")
    title = (title or "").strip() or f"كتاب تلوين {label}"
    count = max(1, min(40, int(art_pages)))
    subtitle = (f"{label} · {ar_count(count)} للتلوين" if language.startswith("ar")
                else f"{label} · {count} coloring pages")
    description = (
        f"{title} — كتاب تلوين يضم {ar_count(count)} من {label} مرسومة بخطوط واضحة وسميكة، "
        "في صفحة مستقلة لكل رسمة مع صفحة فارغة بعدها لمنع تسرّب الألوان. "
        "مقاس كبير مريح للتلوين بأقلام الخشب أو الماركر، ومناسب للأطفال والمبتدئين "
        "ولكل من يحب الاسترخاء بالفن. " + (idea.strip() + ". " if idea.strip() else "")
    ) if language.startswith("ar") else (
        f"{title} — {count} bold, clean coloring pages of {theme}. One drawing per page "
        "with a blank back page to prevent bleed-through. Large trim size, perfect for "
        "crayons and markers, and great for relaxing creativity."
    )
    return {
        "title": title,
        "subtitle": subtitle,
        "description": description.strip(),
        "keywords": _keywords_from(idea, theme, title, language),
        "categories": [f"Children's Books > Coloring Books"],
        "theme": theme,
        "language": language,
        "audience": audience,
        "style": style,
        "pages": _page_list(theme, count, idea, seed=random.randint(0, 10**6), audience=audience),
        "cover": {
            "blurb": (
                f"{ar_count(count)} من {label} بخطوط سميكة وواضحة، صفحة لكل رسمة مع ظهر فارغ، "
                "ومقاس كبير يمنح مساحة مريحة للتلوين. هدية مثالية لصغار الفنانين."
                if language.startswith("ar") else
                f"{count} bold {theme} coloring pages, one per sheet with blank backs. "
                "A perfect gift for young artists."
            )
        },
        "palettes": PALETTES,
        "planner": "local",
        "notes": "خطة محلية (بدون نموذج لغوي) — أضف مفتاح OpenAI لوصف وأفكار أكثر تخصيصًا.",
    }


# ---------------------------------------------------------------------------
# المخطِّط اللغوي (OpenAI)
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """You are a senior children's coloring-book publisher working for Amazon KDP.
Given a book idea, produce a commercially strong plan as STRICT JSON only:
{
 "title": "...", "subtitle": "...", "description": "600-1200 chars, marketing tone",
 "keywords": ["7 Amazon search phrases"],
 "theme": "one of: animals, dinosaurs, unicorns, ocean, space, flowers, geometric, vehicles, festive",
 "pages": [{"prompt": "English line-art image prompt", "caption": "short caption in the book language"}],
 "cover": {"blurb": "back-cover text ~350 chars"}
}
Rules:
- Exactly the requested number of pages, each a DIFFERENT scene, no repeats.
- Every page prompt must describe ONE focal subject, thick clean outlines, pure white
  background, no shading, no gray, no color, no text, centered composition.
- Captions: short (2-5 words), in the book language.
- Keywords must be real Amazon search terms, no brand names.
Return JSON only, no markdown fences."""


def openai_plan(
    title: str,
    idea: str,
    api_key: str,
    *,
    language: str = "ar",
    audience: str = "kids_mid",
    style: str = "medium",
    art_pages: int = 12,
    model: str = "gpt-4o-mini",
    timeout: float = 90.0,
) -> dict:
    if not api_key:
        raise providers.ProviderError("لا يوجد مفتاح OpenAI للتخطيط.")
    count = max(1, min(40, int(art_pages)))
    user = (
        f"Book title: {title or '(none yet — propose one)'}\n"
        f"Book idea: {idea}\n"
        f"Book language for title/subtitle/captions: {language}\n"
        f"Target audience: {audience}\n"
        f"Detail level: {style}\n"
        f"Number of coloring pages: {count}\n"
        f"Trim size: {C.TRIM_SIZES.get('8.5x11', {}).get('label', '8.5x11')}"
    )
    payload = {
        "model": model,
        "temperature": 0.85,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user},
        ],
    }
    try:
        with httpx.Client(timeout=timeout) as client:
            r = client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json=payload,
            )
            r.raise_for_status()
            data = r.json()
        content = data["choices"][0]["message"]["content"]
        plan = json.loads(content)
    except Exception as exc:  # noqa: BLE001
        raise providers.ProviderError(f"تعذّر التخطيط بالذكاء الاصطناعي: {exc}") from exc

    fallback = local_plan(
        title, idea, language=language, audience=audience, style=style, art_pages=count,
        theme=plan.get("theme"),
    )
    pages_in = plan.get("pages") or []
    pages = []
    for i, p in enumerate(pages_in[:count]):
        if isinstance(p, str):
            p = {"prompt": p, "caption": ""}
        prompt = (p.get("prompt") or "").strip()
        caption = (p.get("caption") or "").strip()
        if not prompt:
            continue
        if "outline" not in prompt.lower():
            prompt = (
                prompt.rstrip(".")
                + ". Black and white coloring book page, thick clean black outlines, "
                "pure white background, no shading, no gray, no color, no text, centered."
            )
        pages.append({"prompt": prompt, "caption": caption or fallback["pages"][i % len(fallback["pages"])]["caption"],
                      "subject": prompt[:120]})
    if len(pages) < count:
        pages += fallback["pages"][len(pages):count]

    kws = [str(k).strip() for k in (plan.get("keywords") or []) if str(k).strip()][:7]
    merged = {
        "title": (plan.get("title") or fallback["title"]).strip(),
        "subtitle": (plan.get("subtitle") or fallback["subtitle"]).strip(),
        "description": (plan.get("description") or fallback["description"]).strip(),
        "keywords": kws or fallback["keywords"],
        "categories": fallback["categories"],
        "theme": plan.get("theme") if plan.get("theme") in SCENES else fallback["theme"],
        "language": language,
        "audience": audience,
        "style": style,
        "pages": pages[:count],
        "cover": {"blurb": (plan.get("cover") or {}).get("blurb") or fallback["cover"]["blurb"]},
        "palettes": PALETTES,
        "planner": "openai",
        "notes": "تم التخطيط بنموذج لغوي (OpenAI). يمكنك تعديل الوصف والكلمات قبل التوليد.",
    }
    return merged


def plan_book(title: str, idea: str, options: dict, api_keys: dict) -> dict:
    """يخطّط الكتاب مستخدمًا OpenAI إن توفّر مفتاح، وإلا المخطِّط المحلي."""
    key = (api_keys or {}).get("openai", "")
    opts = {
        "language": options.get("language", "ar"),
        "audience": options.get("audience", "kids_mid"),
        "style": options.get("style", "medium"),
        "art_pages": int(options.get("art_pages", 12)),
    }
    use_ai = bool(key) and options.get("use_ai_planner", True)
    if use_ai:
        try:
            return openai_plan(title, idea, key, **opts)
        except Exception as exc:  # noqa: BLE001
            local = local_plan(title, idea, **opts)
            local["notes"] = f"تعذّر استخدام النموذج اللغوي ({exc}) — تم استخدام المخطِّط المحلي."
            return local
    return local_plan(title, idea, **opts)
