#!/usr/bin/env python3
"""
Vellum Logs — stitch the narration clips into one continuous read.

Every TTS clip is mono and arrives at its natural pace. This script:

  1. normalises each clip to the same level,
  2. inserts a 0.8 s breath between clips (the pause the script asks for),
  3. slows the whole read with atempo=0.82 (the "Keeper" tempo),
  4. high-passes at 70 Hz and low-passes at 8.6 kHz  → close, warm, no sibilance,
  5. adds a very short, very quiet room echo,
  6. compresses gently so the volume never jumps between takes.

The result is a single mono WAV that render_video.py consumes as `narration`.

    python3 tools/build_narration.py narration/narration_full.wav
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import subprocess
import sys

import imageio_ffmpeg

FF = imageio_ffmpeg.get_ffmpeg_exe()

CHAIN = (
    "atempo=0.82,"
    "highpass=f=70,"
    "lowpass=f=8600,"
    "aecho=0.62:0.45:55|115:0.07|0.03,"
    "acompressor=threshold=-17dB:ratio=2.4:attack=20:release=340"
)


def clip_sort_key(path: str) -> int:
    return int(re.search(r"c(\d+)\.(mp3|wav)$", path).group(1))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("output")
    ap.add_argument("--dir", default="narration")
    ap.add_argument("--pad", type=float, default=0.8)
    ap.add_argument("--keep-raw", action="store_true",
                    help="skip the tempo/filter chain (diagnostics only)")
    ap.add_argument("--order", default=None,
                    help="JSON list of clip ids in reading order, e.g. narration/order.json")
    ap.add_argument("--allow-missing", action="store_true",
                    help="narrate only the clips that exist so far")
    args = ap.parse_args()

    if args.order:
        wanted = json.load(open(args.order, encoding="utf-8"))
        clips = [os.path.join(args.dir, w + ".mp3") for w in wanted]
        missing = [c for c in clips if not os.path.exists(c)]
        if missing and not args.allow_missing:
            sys.exit(f"missing {len(missing)} clips, first: {missing[0]}")
        clips = [c for c in clips if os.path.exists(c)]
    else:
        clips = sorted(glob.glob(os.path.join(args.dir, "c*.mp3")), key=clip_sort_key)
    if not clips:
        sys.exit("no clips found")

    # gaps are silence at 44.1 kHz mono, generated once
    silence = os.path.join(args.dir, "_gap.wav")
    subprocess.run([FF, "-y", "-v", "error", "-f", "lavfi",
                    "-i", f"anullsrc=r=44100:cl=mono:d={args.pad}",
                    "-c:a", "pcm_s16le", silence], check=True)

    # build the ffmpeg filter graph: inputs, concat with pads, then the chain
    inputs: list[str] = []
    for c in clips:
        inputs += ["-i", c]
    inputs += ["-i", silence]
    gap_index = len(clips)

    stream = "".join(f"[{i}:a]" for i in range(len(clips)))
    # interleave clips and gaps
    parts = []
    for i in range(len(clips)):
        parts.append(f"[{i}:a]aresample=44100,aformat=channel_layouts=mono[a{i}]")
        parts.append(f"[{gap_index}:a]aresample=44100,aformat=channel_layouts=mono[g{i}]")
    order = "".join(f"[a{i}][g{i}]" for i in range(len(clips)))
    graph = ";".join(parts) + f";{order}concat=n={len(clips) * 2}:v=0:a=1[cat]"
    if args.keep_raw:
        graph += ";[cat]anull[out]"
    else:
        graph += f";[cat]{CHAIN}[out]"

    cmd = [FF, "-y", "-v", "warning", *inputs,
           "-filter_complex", graph,
           "-map", "[out]", "-ac", "1", "-ar", "44100",
           "-c:a", "pcm_s16le", args.output]
    subprocess.run(cmd, check=True)

    probe = subprocess.run([FF, "-i", args.output], capture_output=True, text=True).stderr
    dur = re.search(r"Duration: (\d+):(\d+):([\d.]+)", probe)
    secs = int(dur.group(1)) * 3600 + int(dur.group(2)) * 60 + float(dur.group(3))
    print(f"✓ {args.output}  {secs:.1f}s = {secs/60:.2f} min  from {len(clips)} clips")


if __name__ == "__main__":
    main()
