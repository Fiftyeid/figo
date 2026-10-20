#!/usr/bin/env python3
"""
Vellum Logs — the narration queue.

Two jobs, deliberately boring:

  --next N      print the exact text of the next N clips that have no audio yet,
                verbatim from the chunk plans, so nothing is ever retyped by hand.
  --verify      compare every recorded clip against its expected length and
                flag the ones that are too short (i.e. text went missing).

The measured pace of voice-00 is 189 words per minute at source. A clip whose
audio is more than 12 % shorter than its text implies has lost a sentence.

    python3 tools/next_batch.py --next 10
    python3 tools/next_batch.py --verify
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
WPM = 189.0
TOLERANCE = 0.12

PLANS = ("plan_n.json", "plan_n_tail.json", "plan_rest.json", "plan_interludes.json")


def load_plans() -> dict[str, dict]:
    out: dict[str, dict] = {}
    for name in PLANS:
        path = os.path.join(ROOT, "narration", name)
        if os.path.exists(path):
            for c in json.load(open(path, encoding="utf-8")):
                out[c["clip"]] = c
    return out


def duration(path: str) -> float:
    p = subprocess.run([FF, "-i", path], capture_output=True, text=True)
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", p.stderr)
    if not m:
        return 0.0
    return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--next", type=int, default=0)
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--skip", nargs="*", default=[], help="clip ids to ignore in --next")
    args = ap.parse_args()

    order = json.load(open(os.path.join(ROOT, "narration/order.json"), encoding="utf-8"))
    plans = load_plans()

    if args.verify:
        bad = []
        total = 0.0
        for clip in order:
            path = os.path.join(ROOT, "narration", clip + ".mp3")
            if not os.path.exists(path):
                continue
            d = duration(path)
            total += d
            sent = os.path.join(ROOT, "narration", "sent", clip + ".txt")
            if os.path.exists(sent):
                text = len(open(sent, encoding="utf-8").read().split())
            else:
                text = plans.get(clip, {}).get("words")
            if not text:
                continue
            expect = text * 60.0 / WPM
            ratio = d / expect
            flag = "  <-- SHORT" if ratio < 1 - TOLERANCE else ""
            if flag:
                bad.append((clip, d, expect, ratio))
            print(f"{clip:5s} {d:7.1f}s  expected {expect:7.1f}s  "
                  f"{ratio*100:5.1f}%{flag}")
        print(f"\n{total/60:.1f} min recorded · {len(bad)} clips need re-recording")
        for clip, d, e, r in bad:
            print(f"   {clip}: {d:.0f}s vs {e:.0f}s")
        return

    if args.next:
        queue = [c for c in order
                 if c not in args.skip
                 and not os.path.exists(os.path.join(ROOT, "narration", c + ".mp3"))]
        picks = queue[:args.next]
        for clip in picks:
            c = plans.get(clip)
            print(f"\n===== {clip} · chapter {c['chapter'] if c else '?'} · "
                  f"{c['words'] if c else '?'} words =====")
            print(c["text"] if c else "(no plan entry)")
        print(f"\n{len(picks)} of {len(queue)} remaining")
        return

    ap.print_help()


if __name__ == "__main__":
    main()
