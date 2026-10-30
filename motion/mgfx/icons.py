"""Material Symbols icon lookup (glyph name -> codepoint)."""
from __future__ import annotations

import json
import os

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_PATH = os.path.join(HERE, "fonts", "icon_codepoints.json")
_MAP: dict[str, int] | None = None


def _load() -> dict[str, int]:
    global _MAP
    if _MAP is None:
        if os.path.exists(_PATH):
            raw = json.load(open(_PATH, encoding="utf-8"))
            _MAP = {k: int(v, 16) for k, v in raw.items()}
        else:
            _MAP = {}
    return _MAP


def codepoint(name: str) -> int | None:
    m = _load()
    if name in m:
        return m[name]
    return m.get(resolve(name))


ALIASES = {
    "crescent": "dark_mode",
    "moon": "dark_mode",
    "night": "bedtime",
    "kaba": "mosque",
    "book": "menu_book",
    "people": "groups",
    "pray": "volunteer_activism",
    "fire": "local_fire_department",
    "battle": "swords",
    "war": "swords",
    "grave": "grass",
    "victory": "military_tech",
    "crown": "workspace_premium",
    "heart": "favorite",
    "spark": "auto_awesome",
    "sound": "graphic_eq",
    "history": "history_edu",
    "time": "timer",
    "locate": "location_on",
    "location_on": "place",
    "question_answer": "forum",
    "terrain": "landscape",
    "nights_stay": "bedtime",
    "sword": "swords",
    "grave": "grass",
}


def resolve(name: str) -> str:
    return ALIASES.get(name, name)
