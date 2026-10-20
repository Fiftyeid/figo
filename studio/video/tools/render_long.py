#!/usr/bin/env python3
"""
Vellum Logs — long-form renderer, single pass per movement.

Built for 2–3 hour sleep episodes. The demo renderer (render_video.py) encodes
the picture three times, which is fine for ten minutes and ruinous for three
hours. This one builds an entire movement — every shot, every dissolve — inside
a single ffmpeg process, so the picture is encoded exactly once.

Look
----
The stills are pre-graded in Python (see tools/grade_stills.py): warm, low
contrast, slightly desaturated, blacks lifted. That removes the expensive
per-frame colour work and buys roughly 2.5× the render speed.

Per frame we only do:
    zoompan  → the slow Ken Burns push (rendered from a 2304 px source)
    noise    → fine, temporal film grain
    vignette → the soft closed-in edges

    python3 tools/render_long.py scripts/ep01_full.manifest.json
    python3 tools/render_long.py scripts/ep01_full.manifest.json --only 0 1
    python3 tools/render_long.py script.json --fragment 2     # one movement only
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys

try:
    import imageio_ffmpeg
    FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
except Exception:                                    # pragma: no cover
    FFMPEG = shutil.which("ffmpeg") or "ffmpeg"

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def resolve(p: str) -> str:
    return p if os.path.isabs(p) else os.path.join(ROOT, p)


def run(cmd: list[str]) -> None:
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        sys.stderr.write("\n".join(cmd) + "\n" + p.stderr[-5000:])
        raise SystemExit(f"ffmpeg failed ({p.returncode})")


def probe_duration(path: str) -> float:
    p = subprocess.run([FFMPEG, "-i", path], capture_output=True, text=True)
    for line in p.stderr.splitlines():
        if "Duration:" in line:
            hms = line.split("Duration:")[1].split(",")[0].strip()
            h, m, s = hms.split(":")
            return int(h) * 3600 + int(m) * 60 + float(s)
    return 0.0


# --------------------------------------------------------------------------- #
def shot_filters(seg: dict, duration: float, fps: int, W: int, H: int,
                 fade_in: float, fade_out: float) -> str:
    """zoompan + grain + vignette + (optionally) fades, for one still."""
    frames = max(2, int(round(duration * fps)))
    z0, z1 = seg.get("zoom", [1.0, 1.08])
    if z1 >= z0:
        z = f"min({z1:.4f},{z0:.4f}+{z1 - z0:.4f}*on/{frames})"
    else:
        z = f"max({z1:.4f},{z0:.4f}-{z0 - z1:.4f}*on/{frames})"

    pan = seg.get("pan", "none")
    drift = seg.get("drift", 0.016)
    if pan == "left":
        x = f"iw/2-(iw/zoom/2)+({drift}*iw)*on/{frames}"
    elif pan == "right":
        x = f"iw/2-(iw/zoom/2)-({drift}*iw)*on/{frames}"
    else:
        x = "iw/2-(iw/zoom/2)"
    y = "ih/2-(ih/zoom/2)"

    chain = [
        f"zoompan=z='{z}':x='{x}':y='{y}':d={frames}:s={W}x{H}:fps={fps}",
        f"trim=duration={duration:.3f},setpts=PTS-STARTPTS",
        "noise=alls=4:allf=t+u",
        "format=yuv420p",
        f"settb=AVTB,fps={fps}",
    ]
    if fade_in > 0:
        chain.append(f"fade=t=in:st=0:d={fade_in:.2f}")
    if fade_out > 0:
        chain.append(f"fade=t=out:st={max(0.0, duration - fade_out):.2f}:d={fade_out:.2f}")
    return ",".join(chain)


def movement_key(mv: dict, W: int, H: int, fps: int, transition: float,
                 fade_in: float, fade_out: float) -> str:
    """Everything that changes the picture, in one short string."""
    import hashlib
    payload = json.dumps({
        "segs": [(s["image"], round(float(s["duration"]), 3), s.get("zoom"), s.get("pan"))
                 for s in mv["segments"]],
        "W": W, "H": H, "fps": fps, "tr": transition,
        "fi": round(fade_in, 2), "fo": round(fade_out, 2),
    }, sort_keys=True)
    return hashlib.sha1(payload.encode()).hexdigest()[:12]


def render_movement(mv: dict, out: str, W: int, H: int, fps: int,
                    transition: float, fade_in: float, fade_out: float) -> float:
    segs = mv["segments"]
    durs = [float(s["duration"]) for s in segs]
    inputs: list[str] = []
    for i, seg in enumerate(segs):
        img = resolve(seg["image"])
        if not os.path.exists(img):
            raise SystemExit(f"missing image {img}")
        inputs += ["-i", img]   # a single frame; zoompan generates the clip

    graph: list[str] = []
    for i, seg in enumerate(segs):
        first = i == 0
        last = i == len(segs) - 1
        graph.append(f"[{i}:v]{shot_filters(seg, durs[i], fps, W, H, 0, 0)}[s{i}]")

    prev, acc = "[s0]", durs[0]
    for i in range(1, len(segs)):
        off = acc - transition
        graph.append(f"{prev}[s{i}]xfade=transition=fade:duration={transition}:offset={off:.3f}[x{i}]")
        prev = f"[x{i}]"
        acc = off + durs[i]

    tail = []
    if fade_in > 0:
        tail.append(f"fade=t=in:st=0:d={fade_in:.2f}")
    if fade_out > 0:
        tail.append(f"fade=t=out:st={max(0.0, acc - fade_out):.2f}:d={fade_out:.2f}")
    tail += ["setsar=1", "format=yuv420p"]
    graph.append(f"{prev}" + ",".join(tail) + "[vout]")

    run([FFMPEG, "-y", *inputs, "-filter_complex", ";".join(graph),
         "-map", "[vout]", "-r", str(fps), "-c:v", "libx264", "-preset", "veryfast",
         "-crf", "20", "-pix_fmt", "yuv420p", "-an", out])
    return acc


def concat_video(parts: list[str], out: str, tmp: str) -> None:
    if len(parts) == 1:
        shutil.copyfile(parts[0], out)
        return
    listing = os.path.join(tmp, "concat.txt")
    with open(listing, "w", encoding="utf-8") as fh:
        for p in parts:
            fh.write(f"file '{os.path.abspath(p)}'\n")
    run([FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", listing,
         "-c", "copy", out])


def measure_loudness(path: str, cache: str | None = None) -> dict:
    if cache and os.path.exists(cache):
        with open(cache, encoding="utf-8") as fh:
            return json.load(fh)
    af = "loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json"
    p = subprocess.run([FFMPEG, "-i", path, "-af", af, "-f", "null", "-"],
                       capture_output=True, text=True)
    blob = p.stderr[p.stderr.rindex("{"):]
    blob = blob[:blob.rindex("}") + 1]
    data = json.loads(blob)
    if cache:
        with open(cache, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=1)
    return data


def build_master(narration: str, ambient: str, total: float, out: str,
                 fade_in: float, fade_out: float, cache: str | None) -> None:
    """Narration at -16 LUFS over a 432 Hz bed at -27 LUFS, stereo, limited."""
    m = measure_loudness(narration, cache)
    nar = (
        f"loudnorm=I=-16:TP=-1.5:LRA=11:linear=true:"
        f"measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
        f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:"
        f"offset={m['target_offset']},"
        f"aresample=48000,aformat=channel_layouts=stereo,"
        f"atrim=0:{total:.3f},apad=whole_dur={total:.3f}"
    )
    amb = (
        f"volume=0.30,loudnorm=I=-27:TP=-6:LRA=6,aresample=48000,"
        f"aformat=channel_layouts=stereo,atrim=0:{total:.3f},"
        f"apad=whole_dur={total:.3f}"
    )
    filt = [
        f"[0:a]{nar}[nar]",
        f"[1:a]{amb}[bed]",
        f"[nar][bed]amix=inputs=2:duration=longest:normalize=0[mix]",
        f"[mix]afade=t=in:st=0:d={fade_in:.2f},"
        f"afade=t=out:st={max(0.0, total - fade_out):.3f}:d={fade_out:.3f},"
        f"alimiter=limit=0.87:level=false,"
        f"aformat=channel_layouts=stereo:sample_fmts=fltp[aout]",
    ]
    run([FFMPEG, "-y", "-i", narration, "-stream_loop", "-1", "-i", ambient,
         "-filter_complex", ";".join(filt), "-map", "[aout]",
         "-c:a", "pcm_s16le", "-ar", "48000", out])


def mux(video: str, audio: str, out: str, title: str) -> None:
    run([FFMPEG, "-y", "-i", video, "-i", audio,
         "-map", "0:v", "-map", "1:a",
         "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
         "-movflags", "+faststart", "-metadata", f"title={title}",
         "-shortest", out])


# --------------------------------------------------------------------------- #
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("manifest")
    ap.add_argument("--only", nargs="*", type=int, help="render only these movements")
    ap.add_argument("--fragment", type=int, help="render one movement to <out>.partN.mp4")
    ap.add_argument("--preview", action="store_true")
    ap.add_argument("--no-fit", action="store_true",
                    help="use the written durations instead of fitting the picture "
                         "to the narration")
    ap.add_argument("--tmp", default=None, help="keep movement files in this folder")
    args = ap.parse_args()

    with open(args.manifest, encoding="utf-8") as fh:
        m = json.load(fh)

    W = 1280 if args.preview else m.get("width", 1920)
    H = 720 if args.preview else m.get("height", 1080)
    fps = m.get("fps", 24)
    transition = m.get("transition", 0.9)
    fade_in = m.get("fade_in", 2.0)
    dip = m.get("dip", 3.0)
    outro = m.get("outro", 12.0)
    narration = resolve(m["narration"])
    ambient = resolve(m.get("ambient", "assets/ambient_432.wav"))
    narration_len = probe_duration(narration)

    movements = m["movements"]
    planned = sum(mv["duration"] for mv in movements) - \
        transition * sum(len(mv["segments"]) - 1 for mv in movements)

    scale = 1.0
    if not args.no_fit and narration_len > 0:
        scale = (narration_len + outro) / planned
        if not 0.75 <= scale <= 1.35:
            print(f"  ! fit factor {scale:.3f} is far from 1 — check the manifest")
    total = planned * scale
    print(f"→ {len(movements)} movements · {planned/60:.1f} min planned · "
          f"narration {narration_len/60:.1f} min · fit ×{scale:.4f} → {total/60:.1f} min")

    tmp = args.tmp or os.path.join(ROOT, "out", "_movements")
    os.makedirs(tmp, exist_ok=True)
    print(f"  movements → {tmp}")

    def mpath(i: int) -> str:
        return os.path.join(tmp, f"mov{i:02d}.mp4")

    def keypath(i: int) -> str:
        return os.path.join(tmp, f"mov{i:02d}.key")

    todo = [args.fragment] if args.fragment is not None else \
        (args.only if args.only else list(range(len(movements))))

    for mi in todo:
        mv = movements[mi]
        last = mi == len(movements) - 1
        key = movement_key(mv, W, H, fps, transition, fade_in,
                           outro * 0.7 if last else dip)
        if (os.path.exists(mpath(mi)) and os.path.getsize(mpath(mi)) > 100_000
                and os.path.exists(keypath(mi))
                and open(keypath(mi)).read().strip() == key
                and args.fragment is None and not args.only):
            print(f"  ✓ movement {mi} unchanged")
            continue
        segs = mv["segments"]
        for s in segs:
            s["duration"] = float(s["duration"]) * scale
        durs = sum(float(s["duration"]) for s in segs) - transition * (len(segs) - 1)
        print(f"\n— movement {mi}: {mv.get('title','')}  {durs/60:.1f} min  "
              f"({len(segs)} shots)")
        got = render_movement(mv, mpath(mi), W, H, fps, transition, fade_in,
                              outro * 0.7 if last else dip)
        open(keypath(mi), "w").write(key)
        print(f"   done {got/60:.2f} min")

    if args.fragment is not None or args.only:
        print("\n(fragment mode — assembly skipped)")
        return

    missing = [i for i in range(len(movements)) if not os.path.exists(mpath(i))]
    if missing:
        raise SystemExit(f"movements still missing: {missing}")

    full = os.path.join(tmp, "picture.mp4")
    concat_video([mpath(i) for i in range(len(movements))], full, tmp)
    picture_len = probe_duration(full)
    print(f"\n→ picture {picture_len/60:.2f} min")

    master = os.path.join(tmp, "master.wav")
    build_master(narration, ambient, picture_len, master, fade_in,
                 max(6.0, outro), m.get("loudness_cache"))

    out = resolve(m["output"])
    os.makedirs(os.path.dirname(out), exist_ok=True)
    mux(full, master, out, m.get("title", "Vellum Logs"))
    print(f"\n✓ {out}  {os.path.getsize(out)/1e6:.0f} MB  "
          f"{probe_duration(out)/60:.1f} min")


if __name__ == "__main__":
    main()
