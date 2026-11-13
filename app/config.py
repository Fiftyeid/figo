"""إعدادات المشروع ومواصفات أمازون KDP.

كل الأرقام مطابقة لدليل KDP الرسمي للكتب الورقية (Paperback Submission Guidelines).
كل الأبعاد بالبوصة (inch) لأن KDP يعمل بالبوصة.
"""
from __future__ import annotations

import os
from pathlib import Path

APP_NAME = "مِداد"
APP_NAME_LATIN = "Midad"
APP_VERSION = "1.0.0"
APP_TAGLINE = "استوديو كتب التلوين — متوافق مع Amazon KDP"

BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent
DATA_DIR = Path(os.environ.get("MIDAD_DATA_DIR", ROOT_DIR / "data"))
PROJECTS_DIR = DATA_DIR / "projects"
FONTS_DIR = BASE_DIR / "assets" / "fonts"
STATIC_DIR = BASE_DIR / "static"
SETTINGS_FILE = DATA_DIR / "settings.json"
DIST_DIR = ROOT_DIR / "releases"

for _p in (DATA_DIR, PROJECTS_DIR):
    _p.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# مقاسات القطع (Trim sizes) المسموحة في KDP للكتب الورقية
# ---------------------------------------------------------------------------
TRIM_SIZES = {
    "8.5x11": {"w": 8.5, "h": 11.0, "label": '8.5" × 11"', "note": "الأشهر لكتب التلوين"},
    "8x10": {"w": 8.0, "h": 10.0, "label": '8" × 10"', "note": "شائع جدًا"},
    "8.5x8.5": {"w": 8.5, "h": 8.5, "label": '8.5" × 8.5"', "note": "مربّع للأطفال"},
    "8.25x8.25": {"w": 8.25, "h": 8.25, "label": '8.25" × 8.25"', "note": "مربّع"},
    "8x8": {"w": 8.0, "h": 8.0, "label": '8" × 8"', "note": "كتاب أطفال صغير"},
    "7.5x9.25": {"w": 7.5, "h": 9.25, "label": '7.5" × 9.25"', "note": "اقتصادي"},
    "7x10": {"w": 7.0, "h": 10.0, "label": '7" × 10"', "note": "خفيف"},
    "6x9": {"w": 6.0, "h": 9.0, "label": '6" × 9"', "note": "كتاب جيب"},
}

# أنواع الورق ← سمك الصفحة الواحدة (بوصة) — معادلة KDP لعرض الكعب
PAPER_TYPES = {
    "white": {"thickness": 0.002252, "label": "ورق أبيض — حبر أسود", "short": "أبيض"},
    "cream": {"thickness": 0.0025, "label": "ورق كريمي — حبر أسود", "short": "كريمي"},
    "color_standard": {"thickness": 0.002252, "label": "ورق أبيض — ألوان عادية", "short": "ألوان"},
    "color_premium": {"thickness": 0.002347, "label": "ورق أبيض — ألوان فاخرة", "short": "ألوان فاخرة"},
}

# حدود KDP
MIN_PAGES = 24
MAX_PAGES = 828
BLEED = 0.125            # الهامش النازف المطلوب من كل جهة
MIN_OUTSIDE_NO_BLEED = 0.25
MIN_OUTSIDE_BLEED = 0.375
MIN_SPINE_TEXT_PAGES = 80   # KDP يطبع نص الكعب فقط للكتب فوق 79 صفحة
SPINE_TEXT_SAFETY = 0.0625
BARCODE_W = 2.0
BARCODE_H = 1.2
BARCODE_OFFSET = 0.25     # من حافة القطع والكعب
MIN_COVER_FONT_PT = 7
MAX_COVER_BYTES = 650 * 1024 * 1024

# جدول الهامش الداخلي (gutter) حسب عدد الصفحات — KDP
GUTTER_TABLE = [
    (24, 150, 0.375),
    (151, 300, 0.5),
    (301, 500, 0.625),
    (501, 700, 0.75),
    (701, 828, 0.875),
]

# هوامش التصميم الافتراضية (أوسع من الحد الأدنى لنتيجة أنيقة)
DESIGN_OUTSIDE = 0.5
DESIGN_TOP = 0.5
DESIGN_BOTTOM = 0.5
DESIGN_GUTTER_PAD = 0.125   # نضيف هامش أمان فوق الحد الأدنى

DPI = 300
THUMB_MAX = 640

PROVIDERS = {
    "procedural": {"label": "محرّك محلي (بدون إنترنت)", "needs_key": False},
    "openai": {"label": "OpenAI — gpt-image-1", "needs_key": True},
    "stability": {"label": "Stability AI — Stable Image", "needs_key": True},
    "replicate": {"label": "Replicate — FLUX", "needs_key": True},
    "local_sd": {"label": "Stable Diffusion محلي (A1111 API)", "needs_key": False},
}

# أنماط الرسم (تتحكم في تعقيد الخطوط)
STYLES = {
    "simple": {"label": "بسيط (٣–٦ سنوات)", "detail": 0.55, "thickness": 3},
    "medium": {"label": "متوسط (٦–١٠ سنوات)", "detail": 0.8, "thickness": 2},
    "detailed": {"label": "مفصّل (للبالغين)", "detail": 1.2, "thickness": 2},
}

CORS_ORIGINS = ["*"]
