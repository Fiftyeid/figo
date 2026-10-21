#!/usr/bin/env python3
"""
Vellum Logs — publish pack generator
------------------------------------
Turns a render manifest into everything you paste into YouTube:

    publish/<slug>.description.txt   the full description, chapters included
    publish/<slug>.chapters.txt      just the timestamp block
    publish/<slug>.title.txt         the chosen title (plus the alternates)
    publish/<slug>.tags.txt          comma-separated tag line
    publish/<slug>.metadata.json     YouTube Data API v3 ready (snippet + status)

The timestamps are read from the manifest, never typed by hand. If the film is
re-rendered with more narration, re-run this and the chapters move with it.

    python3 tools/make_publish.py scripts/ep01_part_a.manifest.json \
        --slug ep01_part1 --preset ep01_part1

Presets live in PRESETS below. A preset is only the writing — the timings,
runtime and shot counts always come from the manifest.
"""
from __future__ import annotations

import argparse
import json
import os
from datetime import date

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# --------------------------------------------------------------------------
# preset: everything that is prose. {runtime}, {chapters}, {n_shots},
# {n_movements} and {date} are filled in from the manifest.
# --------------------------------------------------------------------------
PRESETS = {
    "ep01_part1": {
        "title": "The Last Night of Constantinople, 1453 — Sleepy History — Fall Asleep to History — No Adverts",
        "alternates": [
            "The Last Night of Constantinople (Part One) — A Sleepy History Log — 432 Hz",
            "Fall Asleep to the Last Night of Constantinople — Sleepy History — No Adverts",
            "The Last Night of an Empire — Constantinople, 1453 — Sleepy History",
        ],
        "hook": (
            "Fall asleep while exploring the last night of Constantinople. On the evening of "
            "28 May 1453 the lamps are lit for the last time in a city that has stood for a "
            "thousand years — and we walk it slowly, from the water at dusk, along the "
            "Theodosian Walls, across the ditch into the camp outside, past the great gun no "
            "one wants to look at, and into the candlelight of Hagia Sophia."
        ),
        "fascinated": (
            "Whether you're fascinated by the Byzantine Empire, the fall of Constantinople, "
            "medieval daily life, or simply want something calm and real to fall asleep to, "
            "this quiet history documentary moves at the pace of a long evening."
        ),
        "ideal": [
            "Falling asleep to Byzantine and medieval history",
            "Bedtime history for adults",
            "Slow learning about the fall of Constantinople",
            "Background audio for reading, studying, or rest",
            "Anyone who likes rain, candles, and old maps",
            "Nights when you don't want to be talked at",
        ],
        "includes": [
            "The city at dusk, seen from the water",
            "The Theodosian Walls and the men who kept watch",
            "The camp outside, and the great bombard",
            "The ships in the Golden Horn, dragged over land",
            "The last liturgy in Hagia Sophia",
            "The names still cut into the stone",
        ],
        "sources": [
            "Steven Runciman, The Fall of Constantinople 1453",
            "Roger Crowley, 1453: The Holy War for Constantinople",
            "Donald M. Nicol, The Last Centuries of Byzantium",
            "Jonathan Harris, The End of Byzantium",
            "Contemporary accounts: Nicolò Barbaro, George Sphrantzes, Leonard of Chios",
        ],
        "keywords": "sleepy history, history for sleep, fall asleep to history",
        "hashtags": ["#SleepyHistory", "#HistoryForSleep", "#FallAsleepToHistory",
                     "#ByzantineEmpire", "#VellumLogs"],
        "tags": [
            "sleepy history", "history for sleep", "fall asleep to history",
            "fall of constantinople", "byzantine empire documentary",
            "calm history documentary", "bedtime history", "medieval history for sleep",
            "constantinople 1453", "hagia sophia", "sleep documentary", "432 hz",
        ],
        "pinned": "What should the Keeper open next? Tell me a place and I will find its last night.",
        "note": "Part One ends on the line about the stone. The music carries the last 40 seconds.",
    },
    "ep01_full": {
        "title": "The Last Night of Constantinople, 1453 — A Sleepy History Log — Fall Asleep to History — No Adverts",
        "alternates": [
            "The Last Night of Constantinople — A Sleepy History Log — Fall Asleep to History",
            "The Complete Log: The Last Night of Constantinople — Fall Asleep to History — No Adverts",
            "The Last Night of an Empire — Constantinople, 1453 — Sleepy History",
        ],
        "hook": (
            "Fall asleep while exploring the last night of Constantinople. From the lamps being "
            "lit at dusk to the first grey light over the Bosphorus, we walk the whole night "
            "slowly — the walls, the camp, the ships, the guns, the last liturgy, the dogs "
            "asleep in the warm street, and the small ordinary things people do on the last "
            "night of a world."
        ),
        "fascinated": (
            "Whether you're fascinated by the Byzantine Empire, the fall of Constantinople, "
            "medieval daily life, or simply want something calm and real to fall asleep to, "
            "this quiet history documentary moves at the pace of a long night."
        ),
        "ideal": [
            "Falling asleep to Byzantine and medieval history",
            "Bedtime history for adults",
            "Slow learning about the fall of Constantinople",
            "Background audio for reading, studying, or rest",
            "Anyone who likes rain, candles, and old maps",
            "A whole night that does not need you to stay awake for it",
        ],
        "includes": [
            "The city at dusk, seen from the water",
            "The Theodosian Walls and the men who kept watch",
            "The camp outside, and the great bombard",
            "The ships in the Golden Horn, dragged over land",
            "The last liturgy in Hagia Sophia",
            "The emperor's last walk",
            "The hours before dawn, and the first light",
            "What was saved, and what a log remembers",
        ],
        "sources": [
            "Steven Runciman, The Fall of Constantinople 1453",
            "Roger Crowley, 1453: The Holy War for Constantinople",
            "Donald M. Nicol, The Last Centuries of Byzantium",
            "Jonathan Harris, The End of Byzantium",
            "Contemporary accounts: Nicolò Barbaro, George Sphrantzes, Leonard of Chios",
        ],
        "keywords": "sleepy history, history for sleep, fall asleep to history",
        "hashtags": ["#SleepyHistory", "#HistoryForSleep", "#FallAsleepToHistory",
                     "#ByzantineEmpire", "#VellumLogs"],
        "tags": [
            "sleepy history", "history for sleep", "fall asleep to history",
            "fall of constantinople", "byzantine empire documentary",
            "calm history documentary", "bedtime history", "medieval history for sleep",
            "constantinople 1453", "hagia sophia", "3 hours history", "432 hz",
        ],
        "pinned": "What should the Keeper open next? Tell me a place and I will find its last night.",
        "note": "Full episode. Chapters are generated from the final manifest — never type them.",
    },
}


def hhmmss(seconds: float) -> str:
    s = int(round(seconds))
    return f"{s // 3600}:{(s % 3600) // 60:02d}:{s % 60:02d}"


def build(manifest_path: str, slug: str, preset_name: str) -> dict:
    preset = PRESETS[preset_name]
    man = json.load(open(manifest_path, encoding="utf-8"))
    movements = man["movements"]

    chapters, t = [], 0.0
    for mv in movements:
        chapters.append((t, mv["title"]))
        t += mv["duration"]
    runtime = t
    shots = sum(len(mv["segments"]) for mv in movements)

    chapter_block = "\n".join(f"{hhmmss(s)} {title}" for s, title in chapters)

    description = "\n".join([
        "☕ If these nights help you rest → https://buymeacoffee.com/vellumlogs",
        "",
        f"💤 {preset['hook']}",
        "",
        "🎧 432 Hz ambient bed · no adverts in this video · soft narration throughout.",
        "",
        "Enjoy with no adverts and 432 hz background music for sleep.",
        "",
        preset["fascinated"],
        "",
        "There are no loud sounds, no rush, and no flashing edits. Just one calm voice, "
        "a real city, and the small ordinary things people do on the last night of a world.",
        "",
        "😴 This relaxing history video is ideal for:",
        *[f"- {x}" for x in preset["ideal"]],
        "",
        "📜 Includes:",
        *[f"- {x}" for x in preset["includes"]],
        "",
        f"⏱️ {runtime / 60:.0f} minutes · {len(movements)} chapters · {shots} slow shots, "
        "0.9 s cross-fades, no cuts.",
        "",
        "🕰️ Chapters:",
        chapter_block,
        "",
        "📚 Sources:",
        *[f"- {s}" for s in preset["sources"]],
        "",
        "🕯️ Subscribe to Vellum Logs — a new log every week, read in a low voice.",
        "",
        preset["keywords"],
        "",
        " ".join(preset["hashtags"]),
        "",
    ])

    meta = {
        "snippet": {
            "title": preset["title"],
            "description": description,
            "tags": preset["tags"],
            "categoryId": "27",          # Education
            "defaultLanguage": "en",
            "defaultAudioLanguage": "en",
        },
        "status": {
            "privacyStatus": "private",
            "license": "youtube",
            "embeddable": True,
            "publicStatsViewable": True,
            "selfDeclaredMadeForKids": False,
        },
        "recordingDetails": {"recordingDate": f"{date.today().isoformat()}T00:00:00Z"},
        "local": {
            "slug": slug,
            "manifest": os.path.relpath(manifest_path, ROOT),
            "runtime_seconds": round(runtime, 2),
            "runtime": hhmmss(runtime),
            "movements": len(movements),
            "shots": shots,
            "chapters": [{"start": hhmmss(s), "title": ti} for s, ti in chapters],
            "title_alternates": preset["alternates"],
            "pinned_comment": preset["pinned"],
            "note": preset["note"],
        },
    }

    outdir = os.path.join(ROOT, "publish")
    os.makedirs(outdir, exist_ok=True)
    files = {
        "description": ("description.txt", description),
        "chapters": ("chapters.txt", chapter_block + "\n"),
        "title": ("title.txt", preset["title"] + "\n\n" + "\n".join(preset["alternates"]) + "\n"),
        "tags": ("tags.txt", ", ".join(preset["tags"]) + "\n"),
        "metadata": ("metadata.json", json.dumps(meta, indent=2, ensure_ascii=False) + "\n"),
    }
    for _, (name, body) in files.items():
        open(os.path.join(outdir, f"{slug}.{name}"), "w", encoding="utf-8").write(body)

    print(f"✓ publish/{slug}.*  ·  {hhmmss(runtime)}  ·  {len(movements)} chapters  ·  {shots} shots")
    for s, ti in chapters:
        print(f"    {hhmmss(s)}  {ti}")
    return meta


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("manifest")
    ap.add_argument("--slug", required=True)
    ap.add_argument("--preset", default="ep01_part1", choices=sorted(PRESETS))
    a = ap.parse_args()
    build(os.path.join(a.manifest) if os.path.isabs(a.manifest) else os.path.join(ROOT, a.manifest),
          a.slug, a.preset)
