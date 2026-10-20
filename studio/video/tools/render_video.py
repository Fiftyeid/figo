#!/usr/bin/env python3
"""
Vellum Logs — Sleepy Video Renderer
-----------------------------------
Turns a manifest (images + narration track) into a finished, upload-ready
"sleepy history" video: slow Ken Burns drift, 0.9 s cross-fades, warm film
grade, 432 Hz bed, -16 LUFS narration, silent fade-out.

    python3 tools/render_video.py scripts/ep01.manifest.json
    python3 tools/render_video.py scripts/ep01.manifest.json --preview

Manifest schema
---------------
{
  "title":  "The Last Night of Constantinople",
  "output": "out/ep01.mp4",
  "narration": "out/ep01_narration.wav",
  "ambient":  "assets/ambient_432.wav",
  "width": 1920, "height": 1080, "fps": 24,
  "fade_in": 2.0, "outro": 45,
  "segments": [
     {"image": "art/bg-01.png", "duration": 62.0, "chapter": "I. The Wall at Dusk"},
     ...
  ]
}
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile

try:
    import imageio_ffmpeg
    FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
except Exception:                                    # pragma: no cover
    FFMPEG = shutil.which("ffmpeg") or "ffmpeg"

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def run(cmd: list[str], quiet=True):
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        sys.stderr.write("\n".join(cmd) + "\n")
        sys.stderr.write(p.stderr[-4000:])
        raise SystemExit(f"ffmpeg failed ({p.returncode})")
    if not quiet:
        print(p.stderr[-1500:])
    return p


def resolve(p: str) -> str:
    return p if os.path.isabs(p) else os.path.join(ROOT, p)


def probe_duration(path: str) -> float:
    p = subprocess.run([FFMPEG, "-i", path], capture_output=True, text=True)
    for line in p.stderr.splitlines():
        if "Duration:" in line:
            hms = line.split("Duration:")[1].split(",")[0].strip()
            h, m, s = hms.split(":")
            return int(h) * 3600 + int(m) * 60 + float(s)
    return 0.0


# --------------------------------------------------------------------------- #
# 1. one silent Ken Burns clip per image
# --------------------------------------------------------------------------- #
def render_clip(image: str, duration: float, out: str, width: int, height: int,
                fps: int, zoom_from: float, zoom_to: float, pan: str):
    """Slow push/pan on a still. Rendered at 2x then downscaled -> silky motion."""
    frames = max(2, int(round(duration * fps)))
    d_expr = f"'min({zoom_to},1+({zoom_to}-1)*on/{frames})'" if zoom_to > zoom_from \
        else f"'max({zoom_to},{zoom_from}-{zoom_from-zoom_to}*on/{frames})'"

    if pan == "left":
        x_expr = f"'iw/2-(iw/zoom/2)-((iw*0.02)*on/{frames})'"
    elif pan == "right":
        x_expr = f"'iw/2-(iw/zoom/2)+((iw*0.02)*on/{frames})'"
    else:
        x_expr = "'iw/2-(iw/zoom/2)'"
    y_expr = "'ih/2-(ih/zoom/2)'"

    vf = (
        f"scale={width*2}:-2,"
        f"zoompan=z={d_expr}:x={x_expr}:y={y_expr}:d={frames}:s={width}x{height}:fps={fps},"
        # warm, low-contrast grade + fine grain (the "sleepy film" look)
        f"eq=brightness=0.005:contrast=0.94:saturation=0.88:gamma=1.02,"
        f"colorbalance=rs=0.045:gs=0.012:bs=-0.035:rm=0.03:bm=-0.02,"
        f"noise=alls=4:allf=t+u,"
        f"vignette=PI/5.2,"
        f"format=yuv420p"
    )
    run([FFMPEG, "-y", "-loop", "1", "-i", image, "-t", f"{duration:.3f}",
         "-vf", vf, "-r", str(fps), "-c:v", "libx264", "-preset", "veryfast",
         "-crf", "23", "-pix_fmt", "yuv420p", "-an", out])


# --------------------------------------------------------------------------- #
# 2. xfade the clips together
# --------------------------------------------------------------------------- #
def stitch(clips: list[str], durations: list[float], transition: float,
           out: str, fps: int):
    if len(clips) == 1:
        run([FFMPEG, "-y", "-i", clips[0], "-c", "copy", out])
        return

    inputs = []
    for c in clips:
        inputs += ["-i", c]

    filt, prev, acc = [], "[0:v]", durations[0]
    for i in range(1, len(clips)):
        off = acc - transition
        label = f"[v{i}]"
        filt.append(
            f"{prev}[{i}:v]xfade=transition=fade:duration={transition}:offset={off:.3f}{label}"
        )
        prev = label
        acc = off + transition + (durations[i] - transition)
    filt.append(f"{prev}setsar=1,format=yuv420p[vout]")

    run([FFMPEG, "-y", *inputs, "-filter_complex", ";".join(filt),
         "-map", "[vout]", "-r", str(fps), "-c:v", "libx264", "-preset", "veryfast",
         "-crf", "23", "-pix_fmt", "yuv420p", "-an", out])


# --------------------------------------------------------------------------- #
# 3. audio bed + narration + fades
# --------------------------------------------------------------------------- #
def mix_audio(narration: str, ambient: str, video_len: float, out: str,
              fade_in: float, outro: float, target_i=-16.0):
    total = video_len + outro
    fade_out_start = max(0.0, total - max(6.0, outro * 0.6))

    filt = [
        f"[0:a]loudnorm=I={target_i}:TP=-1.5:LRA=11,"
        f"adelay={int(fade_in*1000)}|{int(fade_in*1000)},apad=whole_dur={total:.2f}[nar]",
        f"[1:a]volume=0.30,loudnorm=I=-27:TP=-6:LRA=6,"
        f"atrim=0:{total:.2f},apad=whole_dur={total:.2f}[amb]",
        f"[nar][amb]amix=inputs=2:duration=longest:normalize=0,"
        f"afade=t=in:st=0:d={max(1.0, fade_in):.2f},"
        f"afade=t=out:st={fade_out_start:.2f}:d={max(4.0, outro*0.6):.2f},"
        f"alimiter=limit=0.87,"
        f"aformat=channel_layouts=stereo[aout]",
    ]
    run([FFMPEG, "-y", "-i", narration, "-stream_loop", "-1", "-i", ambient,
         "-filter_complex", ";".join(filt), "-map", "[aout]",
         "-c:a", "pcm_s16le", "-ar", "48000", out])


def mux(video: str, audio: str, out: str, total: float, fade_in: float,
        outro: float, title: str):
    fade_out = max(0.0, total - 4.0)
    vf = (f"setsar=1,fade=t=in:st=0:d={max(0.5, fade_in):.2f},"
          f"fade=t=out:st={fade_out:.2f}:d=4,"
          f"format=yuv420p")
    run([FFMPEG, "-y", "-i", video, "-i", audio,
         "-map", "0:v", "-map", "1:a", "-vf", vf, "-t", f"{total:.2f}",
         "-c:v", "libx264", "-preset", "medium", "-crf", "22",
         "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
         "-metadata", f"title={title}", out])


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("manifest")
    ap.add_argument("--preview", action="store_true",
                    help="720p/fast preset, keeps temp clips")
    args = ap.parse_args()

    with open(args.manifest, encoding="utf-8") as fh:
        m = json.load(fh)

    W = 1280 if args.preview else m.get("width", 1920)
    H = 720 if args.preview else m.get("height", 1080)
    fps = m.get("fps", 24)
    transition = m.get("transition", 0.9)
    fade_in = m.get("fade_in", 2.0)
    outro = m.get("outro", 45.0)

    segments = m["segments"]
    tmp = tempfile.mkdtemp(prefix="vellum_")
    print(f"→ {len(segments)} segments  {W}x{H}@{fps}")

    clips, durations = [], []
    for i, seg in enumerate(segments):
        img = resolve(seg["image"])
        if not os.path.exists(img):
            raise SystemExit(f"missing image: {img}")
        dur = float(seg["duration"])
        clip = os.path.join(tmp, f"c{i:03d}.mp4")
        pan = seg.get("pan", "none")
        z0, z1 = seg.get("zoom", [1.0, 1.10])
        render_clip(img, dur, clip, W, H, fps, z0, z1, pan)
        clips.append(clip)
        durations.append(dur)
        print(f"   [{i+1:02d}/{len(segments)}] {os.path.basename(img)}  {dur:.1f}s")

    stitched = os.path.join(tmp, "stitched.mp4")
    stitch(clips, durations, transition, stitched, fps)
    video_len = sum(durations) - transition * (len(durations) - 1)
    print(f"→ stitched {video_len/60:.1f} min")

    narration = resolve(m["narration"])
    ambient = resolve(m.get("ambient", "assets/ambient_432.wav"))
    audio = os.path.join(tmp, "mix.wav")
    mix_audio(narration, ambient, video_len, audio, fade_in, outro)

    if not args.preview and os.environ.get("KEEP_TMP") != "1":
        pass  # temp cleaned by OS; keep for debugging when KEEP_TMP=1
    out = resolve(m["output"])
    os.makedirs(os.path.dirname(out), exist_ok=True)
    mux(stitched, audio, out, video_len + outro, fade_in, outro,
        m.get("title", "Vellum Logs"))
    size = os.path.getsize(out) / 1e6
    print(f"✓ {out}  {size:.1f} MB  ({(video_len+outro)/60:.1f} min)")


if __name__ == "__main__":
    main()
