"""Turn data/fleet.json into a template recipe.

The fleet register is the source of truth for the episode: 13 categories, 44
airframes, their stats and their narration script. This converts it into the
recipe schema that template/build.py consumes, so the film can be rebuilt from
the template rather than from a one-off script.

    python3 recipes/from_fleet.py            # writes recipes/fleet_2026.json
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# which catalogue line each stat becomes on the item page (three fit best)
STAT_MAP = [
    ("OPERATOR", "Flown by"),
    ("CREW", "Crew"),
    ("MAX SPEED", "Max speed"),
    ("POWERPLANT", "Powerplant"),
    ("COMBAT RADIUS", "Combat radius"),
    ("ARMAMENT", "Armament"),
    ("INVENTORY", "In service"),
]

OPERATOR = {
    "USN": "Navy",
    "USMC": "Marine Corps",
    "USN / USMC": "Navy / Marines",
    "NAVY": "Navy",
}


def clean_stat(label: str, value: str) -> tuple[str, str]:
    v = str(value).strip()
    if v.upper() == "MACH 1.8":
        v = "Mach 1.8"
    elif v.upper().startswith("MACH"):
        v = "Mach " + v.upper().replace("MACH", "").strip()
    elif v.endswith(" NMI"):
        v = v.replace(" NMI", " nm")
    return label, v


def main() -> None:
    fleet = json.loads((ROOT / "data/fleet.json").read_text())
    cats = []

    for cat in fleet["categories"]:
        items = []
        for ac in cat["aircraft"]:
            specs = {k.upper(): v for k, v in ac.get("specs", [])}
            stats = []
            for key, label in STAT_MAP:
                if key == "OPERATOR":
                    stats.append({"label": label, "value": OPERATOR.get(
                        str(ac.get("operator", "")).upper(), ac.get("operator", ""))})
                elif key == "INVENTORY":
                    continue
                elif key in specs:
                    lab, val = clean_stat(label, specs[key])
                    stats.append({"label": lab, "value": val})
            inv = ac.get("inventory")
            if inv and len(stats) < 3:
                stats.append({"label": "In service",
                              "value": str(inv).replace(" AIRFRAMES", "").replace("≈", "≈")})

            items.append({
                "id": ac["id"],
                "name": ac["name"],
                "short": ac.get("short", ac["name"]),
                "year": str(ac.get("year", "")),
                "art": f"assets/fleet/{ac['id']}.png",
                "stats": stats[:3],
            })
        cats.append({
            "title": cat["title"].title(),
            "kicker": cat.get("kicker", "").title(),
            "lead": cat.get("lead", ""),
            "items": items,
        })

    meta = fleet["meta"]
    recipe = {
        "_comment": "FULL EPISODE — generated from data/fleet.json by recipes/from_fleet.py.",
        "meta": {
            "brand": "U.S. NAVAL AVIATION",
            "catalogue": "FLEET CATALOGUE · 2026",
            "channel": meta.get("channel", "Statewide USA").upper(),
            "subject": "aircraft",
            "title_1": "EVERY",
            "title_2": "AIRCRAFT",
            "subtitle": "IN U.S. NAVY & MARINE CORPS SERVICE",
            "footer": "FLEET CATALOGUE · 2026",
            "outro_title": "THAT IS THE\nWHOLE FLEET",
            "outro_stats": [["AIRCRAFT TYPES", meta.get("total_aircraft", 44)],
                            ["CATEGORIES", meta.get("total_categories", 13)],
                            ["RETIREMENTS TRACKED TO", 2032]],
            "sources": "SOURCES: U.S. NAVY · U.S. MARINE CORPS · FY2026 BUDGET DOCUMENTS",
            "credit": "CATALOGUE PRODUCED BY STATEWIDE USA",
            "intro_dur": 12.0,
            "outro_dur": 20.0,
            "vo_dir": "build/vo",
            "music": {"file": "assets/music/hitslab_tension.mp3", "gain": 0.55},
            "output": "FILM_2026_template",
        },
        "categories": cats,
    }
    out = ROOT / "recipes/fleet_2026.json"
    out.write_text(json.dumps(recipe, indent=2, ensure_ascii=False))
    n = sum(len(c["items"]) for c in cats)
    print(f"{out.relative_to(ROOT)} — {len(cats)} categories, {n} items")


if __name__ == "__main__":
    main()
