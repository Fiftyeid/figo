#!/usr/bin/env python3
"""Render JAPAN AIR FLEET 2026 on the HIKKA engine.

    python3 video/build_fleet.py                 # full 1080p30 render
    python3 video/build_fleet.py --poster 03     # one still, for a thumbnail
    python3 video/build_fleet.py --only 01,02    # a couple of chapters
    python3 video/build_fleet.py --audio-only    # mix + subtitles only

Narration clips live in audio/vo_jp/<id>.mp3 (intro.mp3 for the hook) and
drive every chapter length, exactly like the duel film.
"""
from __future__ import annotations

import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import build as B  # noqa: E402
from engine import config as C  # noqa: E402
from engine import subs  # noqa: E402
from engine.fleet import FleetRenderer  # noqa: E402
from content_japan import INTRO_NARRATION, SECTIONS as JP_SECTIONS  # noqa: E402

ROOT = os.path.dirname(HERE)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vo", default=os.path.join(ROOT, "audio", "vo_jp"))
    ap.add_argument("--assets", default=os.path.join(ROOT, "assets"))
    ap.add_argument("--out", default=os.path.join(ROOT, "deliverables", "hikka_japan_fleet_2026.mp4"))
    ap.add_argument("--only", default="")
    ap.add_argument("--poster", default="", help="render one still: intro | 01..08 | end")
    ap.add_argument("--poster-out", default="")
    ap.add_argument("--audio-only", action="store_true")
    ap.add_argument("--draft", action="store_true", help="960x540 proof render")
    ap.add_argument("--no-subs", action="store_true")
    args = ap.parse_args()

    only = set(x.strip() for x in args.only.split(",") if x.strip())
    segs, total = B.build_timeline(args.vo, only or None, JP_SECTIONS)
    os.makedirs(os.path.join(ROOT, "build"), exist_ok=True)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    print(f"  timeline: {len(segs)} segments, {total/60:.1f} min")

    mix_path = os.path.join(ROOT, "build", "mix_fleet.wav")
    B.mix_audio(segs, total, args.vo, mix_path)
    print("  audio mixed ->", os.path.basename(mix_path))

    if not args.no_subs:
        made = subs.export(segs, os.path.join(ROOT, "deliverables"),
                           INTRO_NARRATION, "", stem="hikka_japan_fleet_2026")
        for m in made:
            print("  subs ->", m)

    if args.poster:
        out = args.poster_out or os.path.join(ROOT, "deliverables", f"poster_jp_{args.poster}.png")
        B.poster(segs, total, args.assets, args.poster, out, sections=JP_SECTIONS,
                 renderer_cls=FleetRenderer, intro_narration=INTRO_NARRATION)
        return

    if not args.audio_only:
        w, h = (960, 540) if args.draft else (C.W, C.H)
        B.render(segs, total, args.assets, args.out, w=w, h=h, only=only or None,
                 sections=JP_SECTIONS, renderer_cls=FleetRenderer,
                 intro_narration=INTRO_NARRATION, mix_path=mix_path)


if __name__ == "__main__":
    main()
