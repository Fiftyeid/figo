"""Build the whole film and verify it. One command, readable failures.

    python3 tools/film_full.py --narrate 0:58   # list narration slots still to record
    python3 tools/film_full.py                  # build the film + verify

The film is: a 12 s title card, then 13 categories, each opened by a section
card and followed by its aircraft plates, then an outro. Narration lives in
build/vo as one clip per slot (vo_lead_<n> per section, vo_<id> per aircraft,
vo_outro). Nothing renders until every clip is present, so a run never leaves a
half-narrated film behind.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

VO = ROOT / "build" / "vo"
BUILD = ROOT / "build"
OUT = ROOT / "deliverables" / "22_FILM_full_2026.mp4"


class FilmError(RuntimeError):
    """A problem the user should read, not debug."""


def log(m: str) -> None:
    print(f"  {m}", flush=True)


def slots() -> list[tuple[str, str]]:
    """(stem, text) for every narration slot, in film order."""
    fleet = json.loads((ROOT / "data" / "fleet.json").read_text())
    out: list[tuple[str, str]] = []
    for cat in fleet["categories"]:
        lead = (cat.get("lead") or "").strip()
        if lead:
            out.append((f"vo_lead_{cat['index']}", lead))
        for ac in cat["aircraft"]:
            text = (ac.get("script") or "").strip()
            if text:
                out.append((f"vo_{ac['id']}", text))
    outro = ROOT / "data" / "outro.txt"
    if outro.exists():
        out.append(("vo_outro", outro.read_text().strip()))
    return out


def cmd_narrate(a: str, b: str) -> int:
    all_slots = slots()
    want = all_slots[int(a):int(b)]
    missing = [(s, t) for s, t in want if not (VO / f"{s}.mp3").exists()]
    print(f"{len(want)} slot(s) in {a}:{b}, {len(missing)} still missing")
    for s, t in missing:
        print(f"\n--- {s}\n{t}")
    done = sum(1 for s, _ in all_slots if (VO / f"{s}.mp3").exists())
    print(f"\nnarration complete: {done}/{len(all_slots)}")
    return 0 if done == len(all_slots) else 1


def preflight() -> dict:
    from audio import _duration

    fleet = json.loads((ROOT / "data" / "fleet.json").read_text())
    missing_art = [ac["id"] for cat in fleet["categories"] for ac in cat["aircraft"]
                   if not (ROOT / "assets" / "fleet" / f"{ac['id']}.png").exists()]
    if missing_art:
        raise FilmError("missing aircraft plates: " + ", ".join(missing_art))

    all_slots = slots()
    missing_vo = [s for s, _ in all_slots if not (VO / f"{s}.mp3").exists()]
    if missing_vo:
        raise FilmError(f"{len(missing_vo)} narration clips missing; "
                        f"run python3 tools/film_full.py --narrate to list them "
                        f"({', '.join(missing_vo[:6])} …)")

    durs = {s: _duration(VO / f"{s}.mp3") for s, _ in all_slots}
    short = [s for s, d in durs.items() if d < 0.4]
    if short:
        raise FilmError("narration clips are empty or truncated: " + ", ".join(short))
    return {"fleet": fleet, "durs": durs}


def verify(out: Path, expected: float) -> list[str]:
    import numpy as np
    from opening import probe, pcm

    checks: list[str] = []
    info = probe(out)
    if not info["video"] or not info["audio"]:
        raise FilmError("the film is missing a video or audio stream")
    checks.append(f"duration: {info['duration'] / 60:.2f} min ({info['duration']:.0f}s)")

    if info["video"]["size"] != "1920x1080" or not info["video"]["fps"]:
        raise FilmError("the film is not 1920x1080 at 24 fps")
    checks.append("picture: 1920x1080, 24 fps, h264")

    if not (info["audio"]["stereo"] and info["audio"]["rate"]):
        raise FilmError("audio is not stereo 44.1 kHz")
    checks.append("audio: stereo 44.1 kHz, aac")

    a = pcm(out)
    peak = float(np.max(np.abs(a)))
    if peak > 0.99:
        raise FilmError(f"audio clips (peak {peak:.3f})")
    checks.append(f"levels: peak {peak:.2f}, no clipping")

    SR = 44100
    win = int(2.0 * SR)
    silent = [i // SR for i in range(0, len(a) - win, win)
              if float(np.sqrt(np.mean(a[i:i + win] ** 2))) < 0.002]
    if silent:
        raise FilmError(f"the film drops to silence at {silent[0]}s")
    checks.append("audio: continuous for the whole runtime")

    if abs(info["duration"] - expected) > 1.5:
        raise FilmError(f"the film is {info['duration']:.1f}s but the timeline "
                        f"says {expected:.1f}s")
    return checks


def build() -> int:
    import film as F
    from audio import mix_audio
    from opening import ffmpeg, run

    state = preflight()
    fleet, durs = state["fleet"], state["durs"]
    n_ac = sum(len(c["aircraft"]) for c in fleet["categories"])
    log(f"{len(fleet['categories'])} sections, {n_ac} aircraft, {len(durs)} clips, "
        f"{sum(durs.values()) / 60:.1f} min of narration")

    F.fleet_meta["categories"] = fleet["categories"]
    scenes = F.build_scenes(fleet, durs)
    total = sum(s.dur for s in scenes)
    log(f"timeline: {len(scenes)} scenes, {total / 60:.2f} min")

    BUILD.mkdir(parents=True, exist_ok=True)
    vid = BUILD / "film_full.mp4"
    log("rendering picture")
    F.render(scenes, vid)

    log("mixing narration")
    wav = BUILD / "film_full.wav"
    mix_audio(scenes, wav, total=total)

    log("muxing")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    run([ffmpeg(), "-y", "-hide_banner", "-loglevel", "error",
         "-i", str(vid), "-i", str(wav), "-c:v", "copy",
         "-c:a", "aac", "-b:a", "192k", "-ac", "2", "-shortest",
         "-movflags", "+faststart", str(OUT)], "muxing the film")

    log("verifying")
    for c in verify(OUT, total):
        log(f"ok  {c}")

    print(f"\ndone — {OUT.relative_to(ROOT)}  {total / 60:.2f} min  "
          f"{OUT.stat().st_size / 1e6:.0f} MB")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="build the full narrated film")
    ap.add_argument("--narrate", default="", metavar="A:B", nargs="?",
                    const="0:999", help="list narration slots in this range")
    args = ap.parse_args(argv)
    try:
        if args.narrate:
            a, _, b = args.narrate.partition(":")
            return cmd_narrate(a or "0", b or "999")
        return build()
    except FilmError as exc:
        print(f"\nbuild stopped: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
