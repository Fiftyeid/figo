"""Design tokens + small helpers shared by every scene.

The whole look is defined here: palette, type ramp, easing and the
"virtual showroom" dimensions.  Change a value here and the entire
video re-styles.
"""
from __future__ import annotations

import math
import os
from functools import lru_cache

from PIL import ImageFont

# ---------------------------------------------------------------- fonts
_MPL_TTF = os.path.join(
    os.path.dirname(__import__("matplotlib").__file__), "mpl-data", "fonts", "ttf"
)
FONT_FILES = {
    "bold": "DejaVuSans-Bold.ttf",
    "black": "DejaVuSans-Bold.ttf",
    "reg": "DejaVuSans.ttf",
    "mono": "DejaVuSansMono.ttf",
    "mono_bold": "DejaVuSansMono-Bold.ttf",
    "cond": "DejaVuSansCondensed-Bold.ttf",
    "cond_reg": "DejaVuSansCondensed.ttf",
    "display": "DejaVuSansDisplay.ttf",
    "serif": "DejaVuSerif.ttf",
}
# fall back gracefully if a condensed face is missing on this box
for _k, _v in list(FONT_FILES.items()):
    if not os.path.exists(os.path.join(_MPL_TTF, _v)):
        FONT_FILES[_k] = "DejaVuSans-Bold.ttf" if "reg" not in _k else "DejaVuSans.ttf"


@lru_cache(maxsize=256)
def font(weight: str, size: int) -> ImageFont.FreeTypeFont:
    path = os.path.join(_MPL_TTF, FONT_FILES.get(weight, FONT_FILES["bold"]))
    return ImageFont.truetype(path, max(6, int(size)))


# ---------------------------------------------------------------- canvas
W, H = 1920, 1080
FPS = 30
SAFE = 90  # horizontal safe margin

# ---------------------------------------------------------------- palette
BG_TOP = (250, 251, 252)
BG_HORIZON = (233, 236, 239)
BG_BOTTOM = (209, 213, 218)
GRID_INK = (255, 255, 255)
GRID_SHADE = (150, 158, 168)

INK = (22, 25, 29)          # charcoal, titles
INK_DIM = (104, 112, 122)   # secondary
INK_FAINT = (150, 158, 168)
PAPER = (255, 255, 255)

CHARCOAL = (26, 29, 34)
CHARCOAL_SOFT = (46, 51, 58)

US_NAVY = (21, 45, 88)
US_BLUE = (36, 88, 158)
US_LIGHT = (188, 206, 232)

CN_RED = (196, 34, 34)
CN_RED_DEEP = (150, 22, 22)
CN_YELLOW = (242, 196, 52)
CN_LIGHT = (240, 202, 190)

ACCENT_BY_SIDE = {"left": US_NAVY, "right": CN_RED}
ACCENT_SOFT = {"left": US_BLUE, "right": CN_RED_DEEP}

# ---------------------------------------------------------------- easing


def clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return lo if v < lo else hi if v > hi else v


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def ease_out(t: float) -> float:
    t = clamp(t)
    return 1 - (1 - t) ** 3


def ease_in_out(t: float) -> float:
    t = clamp(t)
    return 4 * t * t * t if t < 0.5 else 1 - (-2 * t + 2) ** 3 / 2


def ease_out_expo(t: float) -> float:
    t = clamp(t)
    return 1.0 if t >= 1 else 1 - 2 ** (-10 * t)


def ease_out_back(t: float, s: float = 1.35) -> float:
    t = clamp(t)
    return 1 + (s + 1) * (t - 1) ** 3 + s * (t - 1) ** 2


def ramp(t: float, start: float, dur: float, ease=ease_out) -> float:
    """0 before `start`, 1 after `start+dur`, eased in between."""
    if dur <= 0:
        return 1.0 if t >= start else 0.0
    return ease((t - start) / dur)


def pulse(t: float, start: float, dur: float) -> float:
    """A 0->1->0 bell, useful for flashes."""
    u = clamp((t - start) / dur)
    return math.sin(math.pi * u) if 0 < u < 1 else 0.0


# ---------------------------------------------------------------- layout
TOP_BAR_Y = 62
DIVIDER_X = W // 2
ITEM_BASELINE = 706          # where showroom objects rest
SPEC_Y = 792                 # spec rail
NAME_Y = 726                 # product name
BOTTOM_BAR_Y = 946
BOTTOM_BAR_H = 96
