#!/usr/bin/env python3
"""Frame-by-frame breakdown of any local video, for style matching.

Two outputs from one pass: a contact sheet you can eyeball in a second, and the
individual full-resolution frames for the ones that matter. The sheet is
labelled with the source timecode, so a shot list can be written straight off
it.

    python3 video/frames.py reference.mp4
    python3 video/frames.py reference.mp4 --n 24 --cols 6
    python3 video/frames.py reference.mp4 --at 0.2 3.5 12 47.25
    python3 video/frames.py reference.mp4 --every 2.0        # one frame per 2 s

Frames land in build/frames/<stem>/, the sheet in build/frames/<stem>_sheet.png.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BUILD = os.path.join(ROOT, "build", "frames")


def ffmpeg() -> str:
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"


def duration(path: str) -> float:
    exe = ffmpeg()
    out = subprocess.run([exe, "-i", path], capture_output=True, text=True).stderr
    for line in out.splitlines():
        if "Duration:" in line:
            hh, mm, ss = line.split("Duration:")[1].split(",")[0].strip().split(":")
            return int(hh) * 3600 + int(mm) * 60 + float(ss)
    raise SystemExit(f"could not read duration of {path}")


def probe(path: str) -> str:
    exe = ffmpeg()
    out = subprocess.run([exe, "-i", path], capture_output=True, text=True).stderr
    for line in out.splitlines():
        if "Stream #0:0" in line and "Video:" in line:
            return line.split("Video:")[1].split(",")[0].strip()
    return "unknown"


def grab(path: str, times: list[float], out_dir: str) -> list[str]:
    exe = ffmpeg()
    os.makedirs(out_dir, exist_ok=True)
    made = []
    for t in times:
        dest = os.path.join(out_dir, f"t{t:08.2f}.png")
        subprocess.run([exe, "-y", "-loglevel", "error", "-ss", f"{t:.3f}",
                        "-i", path, "-frames:v", "1", dest], check=False)
        if os.path.exists(dest):
            made.append(dest)
    return made


def sheet(frames: list[str], times: list[float], out: str,
          cols: int = 5, cell_w: int = 480) -> str:
    ims = [Image.open(f).convert("RGB") for f in frames]
    cell_h = int(cell_w * ims[0].height / ims[0].width)
    rows = (len(ims) + cols - 1) // cols
    pad, bar = 6, 26
    W = cols * cell_w + (cols - 1) * pad
    H = rows * (cell_h + bar) + (rows - 1) * pad
    canvas = Image.new("RGB", (W, H), (18, 20, 24))
    d = ImageDraw.Draw(canvas)
    try:
        font = ImageFont.truetype(
            os.path.join(os.path.dirname(__import__("matplotlib").__file__),
                         "mpl-data", "fonts", "ttf", "DejaVuSans-Bold.ttf"), 18)
    except Exception:
        font = ImageFont.load_default()
    for i, (im, t) in enumerate(zip(ims, times)):
        x = (i % cols) * (cell_w + pad)
        y = (i // cols) * (cell_h + bar + pad)
        canvas.paste(im.resize((cell_w, cell_h), Image.LANCZOS), (x, y))
        label = f"{int(t // 60):02d}:{t % 60:05.2f}"
        d.text((x + 8, y + cell_h + 4), label, font=font, fill=(235, 238, 242))
    canvas.save(out)
    print(f"  sheet {out}  ({len(ims)} frames, {cols} per row)")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--n", type=int, default=20, help="evenly spaced frames")
    ap.add_argument("--at", type=float, nargs="*", help="exact times, in seconds")
    ap.add_argument("--every", type=float, help="one frame every N seconds")
    ap.add_argument("--cols", type=int, default=5)
    ap.add_argument("--cell", type=int, default=480)
    args = ap.parse_args()

    if not os.path.exists(args.video):
        raise SystemExit(f"no such file: {args.video}")

    dur = duration(args.video)
    if args.at:
        times = sorted(args.at)
    elif args.every:
        times = [i * args.every for i in range(int(dur / args.every) + 1)]
    else:
        n = max(1, args.n)
        times = [dur * (i + 0.5) / n for i in range(n)]

    stem = os.path.splitext(os.path.basename(args.video))[0]
    out_dir = os.path.join(BUILD, stem)
    print(f"  {args.video}  {dur:.2f}s  {probe(args.video)}")
    made = grab(args.video, times, out_dir)
    sheet(made, times[:len(made)], os.path.join(BUILD, f"{stem}_sheet.png"),
          args.cols, args.cell)


if __name__ == "__main__":
    main()
