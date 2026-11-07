"""Assemble the film: render scene stills, cut them to the narration timeline,
mix the score, encode a 1080p master, and emit SRT + YouTube packaging.

usage:  python3 pipeline/build.py [--until SECONDS] [--out FILE]
"""
import argparse
import json
import os
import subprocess
import sys

import imageio_ffmpeg

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import render as R  # noqa: E402
import audio_timeline as AT  # noqa: E402

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
N_CAT = 8


def srt_time(t):
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = int(t % 60)
    ms = int(round((t - int(t)) * 1000))
    if ms == 1000:
        s, ms = s + 1, 0
    return "%02d:%02d:%02d,%03d" % (h, m, s, ms)


def wrap(text, width=58):
    words, lines, cur = text.split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 <= width:
            cur = (cur + " " + w).strip()
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return "\n".join(lines[:2])


def render_scenes(tl, scenes, data):
    os.makedirs("work/scenes", exist_ok=True)
    frames = []
    for i, s in enumerate(scenes):
        name = "work/scenes/%03d_%s.png" % (i, s["kind"])
        if s["kind"] == "vehicle":
            if not os.path.exists(R.render_path("renders", s["vid"])):
                continue
            img = R.scene_vehicle(s["vehicle"], s["category"], s["index"], tl["total_vehicles"], "renders")
        elif s["kind"] == "section":
            members = [v for v in data["vehicles"] if v["cat"] == s["cat"]]
            img = R.scene_section(s["category"], members, int(s["category"]["index"]), N_CAT)
        elif s["kind"] == "intro":
            img = R.scene_intro(None, tl["total_vehicles"], "renders")
        else:
            img = R.scene_outro(None, tl["total_vehicles"], "renders")
        img.save(name)
        frames.append((name, s))
    return frames


def build_srt(frames):
    meta = json.load(open("data/vehicles.json"))["meta"]
    lines = []
    for i, (_, s) in enumerate(frames):
        if s["kind"] == "vehicle":
            txt = s["vehicle"]["vo"]
        elif s["kind"] == "section":
            txt = s["category"]["vo"]
        elif s["kind"] == "intro":
            txt = meta["intro_vo"]
        else:
            txt = meta["outro_vo"]
        lines.append("%d\n%s --> %s\n%s\n" % (i + 1, srt_time(s["a0"]), srt_time(s["a1"]), wrap(txt)))
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="output/russian-armor-inventory.mp4")
    ap.add_argument("--crf", default="21")
    ap.add_argument("--until", type=float, default=0)
    args = ap.parse_args()

    os.makedirs("work", exist_ok=True)
    tl = AT.build_timeline()
    data = json.load(open("data/vehicles.json"))
    cats = {c["id"]: c for c in data["categories"]}
    vmap = {v["id"]: v for v in data["vehicles"]}
    for s in tl["scenes"]:
        if s["kind"] == "vehicle":
            s["vehicle"] = vmap[s["vid"]]
            s["category"] = cats[s["cat"]]
        elif s["kind"] == "section":
            s["category"] = cats[s["cat"]]

    scenes = tl["scenes"]
    if args.until:
        scenes = [s for s in scenes if s["t0"] < args.until]
        scenes[-1]["t1"] = args.until
        scenes[-1]["dur"] = args.until - scenes[-1]["t0"]

    frames = render_scenes(tl, scenes, data)
    print("scenes rendered:", len(frames), "of", len(scenes))

    with open("work/concat.txt", "w") as f:
        for path, s in frames:
            f.write("file '%s'\n" % os.path.abspath(path))
            f.write("duration %.3f\n" % s["dur"])
        f.write("file '%s'\n" % os.path.abspath(frames[-1][0]))

    clips = sorted(f for f in os.listdir("audio") if f.startswith("clip") and f.endswith(".mp3"))
    with open("work/voice.txt", "w") as f:
        for c in clips:
            f.write("file '%s'\n" % os.path.abspath(os.path.join("audio", c)))
    subprocess.run([FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", "work/voice.txt",
                    "-c:a", "pcm_s16le", "work/voice.wav"], check=True, capture_output=True)

    total = frames[-1][1]["t1"]
    subprocess.run([sys.executable, os.path.join(HERE, "music.py"), str(total + 1)], check=True)

    vf = ("scale=1920:1080:force_original_aspect_ratio=decrease,"
          "pad=1920:1080:(ow-iw)/2:(oh-ih)/2:white,fps=30,"
          "fade=t=in:st=0:d=0.5:color=white,"
          "fade=t=out:st=%.2f:d=0.8:color=white,format=yuv420p" % (total - 0.9))

    cmd = [FFMPEG, "-y",
           "-f", "concat", "-safe", "0", "-i", "work/concat.txt",
           "-i", "work/voice.wav",
           "-i", "work/music.wav",
           "-filter_complex",
           "[1:a]highpass=f=70,acompressor=threshold=0.09:ratio=3:attack=8:release=180,"
           "loudnorm=I=-18:TP=-2:LRA=9[v];"
           "[2:a]volume=0.085,lowpass=f=6000[m];"
           "[v][m]amix=inputs=2:duration=first:dropout_transition=0,"
           "aformat=sample_fmts=fltp:channel_layouts=stereo,"
           "loudnorm=I=-16:TP=-1.5:LRA=11,"
           "afade=t=in:st=0:d=1.2,afade=t=out:st=%.2f:d=1.6[a]" % (total - 1.8),
           "-map", "0:v", "-map", "[a]",
           "-vf", vf,
           "-c:v", "libx264", "-preset", "medium", "-crf", args.crf,
           "-profile:v", "high", "-level", "4.1", "-pix_fmt", "yuv420p",
           "-r", "30", "-g", "60",
           "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
           "-movflags", "+faststart", "-t", "%.3f" % total,
           args.out]

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    print("encoding...")
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr[-3000:])
        raise SystemExit("encode failed")

    base = os.path.splitext(args.out)[0]
    with open(base + ".srt", "w") as f:
        f.write(build_srt(frames))

    chapters = "\n".join("%s %s" % (srt_time(s["a0"])[3:8], s["category"]["title"].title())
                         for s in tl["scenes"] if s["kind"] == "section")
    pack = f"""# YouTube packaging

**Title**

Every Russian Tank & Armored Vehicle in Active Service (Full Breakdown)

**Thumbnail**

output/thumbnail.jpg

**Description**

All {tl['total_vehicles']} tanks, armored cars, tank destroyers, APCs, IFVs, self-propelled guns and
engineering vehicles currently in Russian service — in one technical inventory.
Each machine: what it is, when it entered service, what it carries, and how it is
actually being used in the war in Ukraine.

00:00 Intro
{chapters}

Specifications are compiled from open sources and are approximate.
Loss figures refer only to visually confirmed vehicles, so real totals are higher.

No footage: every vehicle is a rendered still, presented as a technical exhibit.

**Chapters**

{chapters}

**Tags**

russian tanks, t-90m, t-72b3, t-80bvm, bmp-3, btr-80, 2s19 msta-s, tos-1a,
bmpt terminator, russian armor, armored vehicles explained, military vehicles,
ukraine war armor, tank inventory, armored personnel carrier, self-propelled
artillery, military documentary, defense analysis
"""
    with open(base + "-packaging.md", "w") as f:
        f.write(pack)

    for f in ("work/voice.wav", "work/music.wav"):
        if os.path.exists(f):
            os.remove(f)
    print("done:", args.out)


if __name__ == "__main__":
    main()
