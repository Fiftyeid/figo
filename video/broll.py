#!/usr/bin/env python3
"""Import real field footage as chapter inserts (b-roll).

The engine never ships footage — licensing and size are yours to own. Drop a
clip here and the matching chapter opens with it, full screen, graded and
captioned, before cutting back to the studio scene.

    python3 video/broll.py ~/Downloads/m249_fire.mp4 mg_fire
    python3 video/broll.py clips/ --list

Clips are normalised to 1920x1080 / 30 fps and trimmed to 4.5 s, then the
renderer extracts frames into build/broll/<name>/ on the next build.

Good sources (check the licence on each file, and credit it):
  * DVIDS (U.S. Department of Defense) — public domain
  * Wikimedia Commons — CC BY / CC BY-SA
  * NATO / national ministry channels — usually CC BY
Update the on-screen credit in content.py (`broll.credit`) to match.
"""
from __future__ import annotations

import argparse
import glob
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from build import FFMPEG, ROOT as _ROOT  # noqa: E402

BROLL = os.path.join(ROOT, "broll")


def normalise(src: str, name: str) -> str:
    os.makedirs(BROLL, exist_ok=True)
    dst = os.path.join(BROLL, name + ".mp4")
    vf = ("scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,setsar=1")
    subprocess.run(
        [FFMPEG, "-y", "-loglevel", "error", "-i", src, "-t", "4.5", "-vf", vf,
         "-r", "30", "-an", "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", dst],
        check=True,
    )
    size = os.path.getsize(dst) / 1e6
    print(f"  {name:16s} -> broll/{name}.mp4   ({size:.1f} MB, 4.5 s)")
    return dst


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src", nargs="?", help="video file, or a folder of clips")
    ap.add_argument("name", nargs="?", help="clip name used in content.py (e.g. mg_fire)")
    ap.add_argument("--list", action="store_true", help="show clips already imported")
    args = ap.parse_args()

    if args.list or not args.src:
        have = sorted(glob.glob(os.path.join(BROLL, "*.mp4")))
        if not have:
            print("  no clips yet — nothing will be inserted, chapters stay in the studio")
        for p in have:
            print("  ", os.path.basename(p))
        print("\n  chapters wired for inserts:",
              ", ".join(["07 nvg_field", "10 mg_fire", "13 ration_heat", "16 drone_launch"]))
        return

    if os.path.isdir(args.src):
        for p in sorted(glob.glob(os.path.join(args.src, "*.mp4"))):
            normalise(p, os.path.splitext(os.path.basename(p))[0])
    else:
        normalise(args.src, args.name or os.path.splitext(os.path.basename(args.src))[0])


if __name__ == "__main__":
    main()
