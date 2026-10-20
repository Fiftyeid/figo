#!/usr/bin/env python3
"""
Vellum Logs — build the render manifest from the narration that actually exists.

The picture follows the voice. This script measures every narration clip in
`narration/order.json`, works out which chapter it belongs to, and lays out
shots so that:

  * every chapter starts and ends exactly when its narration does,
  * each shot on a still lasts about `--shot-length` seconds (slow by design),
  * images are cycled inside a chapter so consecutive shots differ,
  * camera moves alternate (push in / pull out, drift left / right / still).

    python3 tools/build_manifest.py --available      # only narrated chapters
    python3 tools/build_manifest.py                  # the whole episode
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys

import imageio_ffmpeg

FF = imageio_ffmpeg.get_ffmpeg_exe()
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ATEMPO = 0.82
PAD = 0.8
FADE = 0.9

# Every picture in the film, in the order the story walks through them.
CHAPTER_ART = {
    "0":    ["bg-01-constantinople"],
    "I":    ["bg-10-lamps-city", "bg-01-constantinople"],
    "II":   ["bg-04-walls-dusk", "bg-13-masonry", "bg-20-breach"],
    "III":  ["bg-05-ottoman-camp", "bg-04-walls-dusk"],
    "IV":   ["bg-19-chain", "bg-18-ships-overland", "bg-08-moon-sea"],
    "V":    ["bg-05-ottoman-camp", "bg-20-breach", "bg-13-masonry"],
    "VI":   ["bg-06-hagia-sophia", "bg-07-prayer-crowd"],
    "VII":  ["bg-14-street-night", "bg-10-lamps-city"],
    "VIII": ["bg-04-walls-dusk", "bg-21-rooftop-dawn", "bg-01-constantinople"],
    "IX":   ["bg-08-moon-sea", "bg-14-street-night", "bg-10-lamps-city"],
    "X":    ["bg-21-rooftop-dawn", "bg-11-dawn-blacksea", "bg-20-breach"],
    "XI":   ["bg-02-scriptorium", "bg-15-harbour-night"],
    "XII":  ["bg-17-ship-cabin", "bg-02-scriptorium"],
    "XIII": ["bg-08-moon-sea"],
    "A":    ["bg-12-cistern", "bg-23-cistern-wall", "bg-22-aqueduct"],
    "B":    ["bg-13-masonry", "bg-04-walls-dusk"],
    "C":    ["bg-02-scriptorium"],
    "D":    ["bg-14-street-night"],
    "E":    ["bg-15-harbour-night", "bg-08-moon-sea"],
    "F":    ["bg-16-gate", "bg-04-walls-dusk"],
    "G":    ["bg-17-ship-cabin", "bg-08-moon-sea"],
}

CHAPTER_TITLE = {
    "0": "00 · Welcome & Settle",
    "I": "I · The City at Dusk",
    "II": "II · The Wall",
    "III": "III · The Camp Outside",
    "IV": "IV · The Ships in the Horn",
    "V": "V · The Guns",
    "VI": "VI · The Last Liturgy",
    "VII": "VII · The People in the Streets",
    "VIII": "VIII · The Emperor's Last Walk",
    "IX": "IX · The Hours Before Dawn",
    "X": "X · The First Light",
    "XI": "XI · What Was Saved",
    "XII": "XII · What the Log Remembers",
    "XIII": "XIII · Sleep",
    "A": "Interlude · The Water Below",
    "B": "Interlude · The Names in the Stone",
    "C": "Interlude · The Scriptorium",
    "D": "Interlude · The Dogs of the City",
    "E": "Interlude · The Road Out",
    "F": "Interlude · The Marble Emperor",
    "G": "Interlude · The Witness",
}


def duration(path: str) -> float:
    p = subprocess.run([FF, "-i", path], capture_output=True, text=True)
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", p.stderr)
    if not m:
        return 0.0
    return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))


def clip_chapters() -> dict[str, str]:
    """clip id → chapter tag, from the plans and the original demo chunks."""
    out: dict[str, str] = {}
    for name, default in (("narration/plan_rest.json", "V"),
                          ("narration/plan_interludes.json", "A"),
                          ("narration/plan_n.json", "II"),
                          ("narration/plan_n_tail.json", "III")):
        path = os.path.join(ROOT, name)
        if not os.path.exists(path):
            continue
        for c in json.load(open(path, encoding="utf-8")):
            out[c["clip"]] = c["chapter"]
    # the demo clips: c1 is the welcome, c2–c7 are the first half of chapter I
    out.setdefault("c1", "0")
    for i in range(2, 8):
        out.setdefault(f"c{i}", "I")
    for i in range(8, 18):          # chapter IV, up to the first gun
        out.setdefault(f"c{i}", "IV")
    return out


def shot_plan(images: list[str], total: float, target: float) -> list[dict]:
    n = max(len(images), int(round(total / target)))
    n = max(1, min(n, 8))
    lengths = [total / n] * n
    shots = []
    for k in range(n):
        img = images[k % len(images)]
        push = k % 2 == 0
        z0, z1 = (1.0, 1.06) if push else (1.06, 1.0)
        pan = ["left", "right", "none", "left"][k % 4]
        shots.append({
            "image": f"../art/_graded/{img}.jpg",
            "duration": round(lengths[k] + (FADE * (n - 1) / n), 3),
            "zoom": [z0, z1],
            "pan": pan,
        })
    # make the shot sum exact: sum(d) - FADE*(n-1) == total
    return shots


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--available", action="store_true",
                    help="stop at the last chapter whose clips are all narrated")
    ap.add_argument("--simulate", action="store_true",
                    help="estimate the duration of clips that are not narrated yet")
    ap.add_argument("--shot-length", type=float, default=110.0)
    ap.add_argument("--out", default="scripts/ep01_full.manifest.json")
    ap.add_argument("--narration", default="narration/narration_full.wav")
    ap.add_argument("--output", default="exports/EP01_The_Last_Night_of_Constantinople.mp4")
    args = ap.parse_args()

    order = json.load(open(os.path.join(ROOT, "narration/order.json"), encoding="utf-8"))
    tags = clip_chapters()
    plan_words: dict[str, int] = {}
    for name in ("plan_rest.json", "plan_interludes.json", "plan_n.json",
                 "plan_n_tail.json"):
        path = os.path.join(ROOT, "narration", name)
        if os.path.exists(path):
            for c in json.load(open(path, encoding="utf-8")):
                plan_words[c["clip"]] = c["words"]

    chapters: list[tuple[str, float, list[str]]] = []
    missing = 0
    for clip in order:
        path = os.path.join(ROOT, "narration", clip + ".mp3")
        tag = tags.get(clip, "?")
        if not os.path.exists(path):
            missing += 1
            if args.available:
                break
            if not args.simulate:
                continue
            words = plan_words.get(clip, 260)
            done = words * 60.0 / 177.0 / ATEMPO + PAD
        else:
            done = duration(path) / ATEMPO + PAD
        if chapters and chapters[-1][0] == tag:
            chapters[-1] = (tag, chapters[-1][1] + done, chapters[-1][2] + [clip])
        else:
            chapters.append((tag, done, [clip]))

    if args.available and missing:
        print(f"  (narration missing for {missing} clips — building the narrated part)")

    movements = []
    for tag, dur, clips in chapters:
        art = CHAPTER_ART.get(tag)
        if not art:
            sys.exit(f"no art mapped for chapter {tag}")
        movements.append({
            "title": CHAPTER_TITLE.get(tag, tag),
            "duration": round(dur, 2),
            "segments": shot_plan(art, dur, args.shot_length),
            "narration_clips": clips,
        })

    total = sum(mv["duration"] for mv in movements)
    manifest = {
        "title": "The Last Night of Constantinople",
        "output": args.output,
        "narration": args.narration,
        "ambient": "assets/ambient_432.wav",
        "loudness_cache": "narration/.loudness.json",
        "width": 1920, "height": 1080, "fps": 24,
        "fade_in": 3.0, "dip": 2.5, "transition": FADE, "outro": 40.0,
        "movements": movements,
    }
    path = os.path.join(ROOT, args.out)
    json.dump(manifest, open(path, "w", encoding="utf-8"), indent=1, ensure_ascii=False)

    shots = sum(len(mv["segments"]) for mv in movements)
    print(f"✓ {args.out}")
    print(f"  {len(movements)} movements · {shots} shots · {total/60:.1f} min of narration")
    for mv in movements:
        print(f"    {mv['duration']/60:5.1f} min  {len(mv['segments']):2d} shots  "
              f"{mv['title']}")


if __name__ == "__main__":
    main()
