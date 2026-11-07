"""Assemble the film: render scene stills, cut them to the narration timeline,
mix the score, encode a 1080p master, and emit SRT + YouTube packaging.

usage:  python3 pipeline/build.py [--until SECONDS] [--out FILE]
"""
import argparse
import json
import os
import subprocess
import sys

from PIL import Image, ImageDraw
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


def wrap(text, width=42):
    """Wrap to a list of lines (no truncation)."""
    words, lines, cur = text.split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 <= width:
            cur = (cur + " " + w).strip()
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def cue_chunks(text, width=42, per_cue=2):
    """Split narration into subtitle cues of at most `per_cue` lines."""
    lines = wrap(text, width)
    return [lines[i:i + per_cue] for i in range(0, len(lines), per_cue)]


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
    """Full subtitles: long narration is split across cues, never truncated;
    each cue's share of the scene time follows its share of the text."""
    meta = json.load(open("data/vehicles.json"))["meta"]
    cues = []
    for _, s in frames:
        if s["kind"] == "vehicle":
            txt = s["vehicle"]["vo"]
        elif s["kind"] == "section":
            txt = s["category"]["vo"]
        elif s["kind"] == "intro":
            txt = meta["intro_vo"]
        elif s["kind"] in ("note", "losses"):
            txt = " ".join(s["lines"])
        else:
            txt = meta["outro_vo"]
        chunks = cue_chunks(txt)
        lens = [len(" ".join(c)) for c in chunks]
        span = max(0.4, s["a1"] - s["a0"])
        t = s["a0"]
        for c, ln in zip(chunks, lens):
            d = span * ln / sum(lens)
            cues.append((t, t + d, "\n".join(c)))
            t += d
    out = []
    for i, (a, b, txt) in enumerate(cues):
        out.append("%d\n%s --> %s\n%s\n" % (i + 1, srt_time(a), srt_time(b), txt))
    return "\n".join(out)


# ------------------------------------------------------------------ appendix
NOTE_SECS = 18.0
WIPE_SECS = 0.5            # transition between sections, per the style brief
WIPE_FPS = 30
WIPE_FRAMES = int(WIPE_SECS * WIPE_FPS)

APPENDIX = [
    {"kind": "note", "title": "METHODOLOGY", "lines": [
        "Every vehicle here is confirmed in Russian service in 2026.",
        "One representative variant per family; sub-variants are grouped.",
        "Specifications are compiled from open sources and are approximate.",
        "Nothing in this film comes from classified material.",
    ]},
    {"kind": "losses", "title": "LOSSES  ·  VISUALLY CONFIRMED",
     "rows": [("T-72 family", 1815, "1,815"),
              ("BMP-2", 2000, "2,000+"),
              ("BTR series", 1000, "1,000+")],
     "source": "ORYX  ·  FEBRUARY 2026",
     "note": "Counts cover destroyed, damaged, captured and abandoned vehicles. "
             "Only visually confirmed losses are counted, so real totals are higher.",
     "lines": ["Oryx, February 2026: T-72 family 1,815 confirmed losses. "
               "BMP-2 over 2,000. BTR series over 1,000."]},
    {"kind": "note", "title": "READING THE NUMBERS", "lines": [
        "Entered service: the year the type was adopted, not the first prototype.",
        "Combat weight: loaded, as fielded, not empty.",
        "Crew: the vehicle's own crew; dismounts are counted separately.",
        "Loss figures circulating online count only visually confirmed vehicles.",
    ]},
    {"kind": "note", "title": "SOURCES & LIMITS", "lines": [
        "Open sources: manufacturer data, ministry releases, reference works.",
        "Figures differ between sources; numbers here are mid-range estimates.",
        "Production and loss totals are published by neither side.",
        "These are inventories, not assessments of combat effectiveness.",
    ]},
]


def appendix_scenes(t_start):
    """Video-only end cards appended after the sign-off."""
    out = []
    for k, spec in enumerate(APPENDIX, 1):
        sc = dict(spec)
        sc.update(kind=spec["kind"], cat=None, vid=None, index=k,
                  a0=t_start, a1=t_start + NOTE_SECS,
                  t0=t_start, t1=t_start + NOTE_SECS, dur=NOTE_SECS)
        out.append(sc)
        t_start += NOTE_SECS
    return out


def make_wipe(a_path, b_path, out_dir):
    """Render a 0.5 s left-to-right wipe from card A into card B."""
    os.makedirs(out_dir, exist_ok=True)
    A = Image.open(a_path).convert("RGB")
    B = Image.open(b_path).convert("RGB")
    W, H = A.size
    for f in range(WIPE_FRAMES):
        x = int(W * (f + 1) / WIPE_FRAMES)
        canvas = A.copy()
        canvas.paste(B.crop((0, 0, x, H)), (0, 0))
        d = ImageDraw.Draw(canvas)
        d.line([(x, 0), (x, H)], fill=(204, 0, 0), width=3)
        canvas.save(os.path.join(out_dir, "%03d.png" % f))
    return out_dir


def write_outputs(args, tl, frames):
    """Write .srt and the YouTube packaging file next to the master."""
    base = os.path.splitext(args.out)[0]
    with open(base + ".srt", "w") as f:
        f.write(build_srt(frames))

    chapters = "\n".join("%s %s" % (srt_time(s["a0"])[3:8], s["category"]["title"].title())
                         for s in tl["scenes"] if s["kind"] == "section")
    notes = [s for _, s in frames if s["kind"] == "note"]
    notes_line = ""
    if notes:
        notes_line = "%s End notes · methodology & sources\n" % srt_time(notes[0]["a0"])[3:8]

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
{notes_line}
Specifications are compiled from open sources and are approximate.
Loss figures refer only to visually confirmed vehicles, so real totals are higher.

No footage: every vehicle is a rendered still, presented as a technical exhibit.

**Chapters**

00:00 Intro
{chapters}
{notes_line}
**Tags**

russian tanks, t-90m, t-72b3, t-80bvm, bmp-3, btr-80, 2s19 msta-s, tos-1a,
bmpt terminator, russian armor, armored vehicles explained, military vehicles,
ukraine war armor, tank inventory, armored personnel carrier, self-propelled
artillery, military documentary, defense analysis
"""
    with open(base + "-packaging.md", "w") as f:
        f.write(pack)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="output/russian-armor-inventory.mp4")
    ap.add_argument("--crf", default="21")
    ap.add_argument("--until", type=float, default=0)
    ap.add_argument("--srt-only", action="store_true",
                    help="rewrite .srt + packaging from work/timeline.json (no encode)")
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

    if args.srt_only:
        frames = []
        for s in scenes:
            if s["kind"] == "vehicle":
                s["vehicle"] = vmap[s["vid"]]
                s["category"] = cats[s["cat"]]
            elif s["kind"] == "section":
                s["category"] = cats[s["cat"]]
            frames.append((None, s))
        for note in appendix_scenes(frames[-1][1]["t1"]):
            frames.append((None, note))
        write_outputs(args, tl, frames)
        return

    frames = render_scenes(tl, scenes, data)
    print("scenes rendered:", len(frames), "of", len(scenes))

    for sc in appendix_scenes(frames[-1][1]["t1"]):
        name = "work/scenes/%03d_appendix%d.png" % (len(frames), sc["index"])
        if sc["kind"] == "losses":
            R.scene_losses(sc["index"], len(APPENDIX), sc["rows"], sc["source"],
                           sc["note"]).save(name)
        else:
            R.scene_note(sc["index"], len(APPENDIX), sc["title"], sc["lines"]).save(name)
        frames.append((name, sc))
    print("appendix cards:", len(APPENDIX), "last scene ends %.2fs" % frames[-1][1]["t1"])

    # ---- 0.5 s wipes into every section card (brief: transitions between sections)
    boundaries = [i for i, (_, sc) in enumerate(frames) if sc["kind"] == "section" and i > 0]
    for i in boundaries:
        frames[i - 1][1]["dur"] = max(2.0, frames[i - 1][1]["dur"] - WIPE_SECS)

    segments = []
    for i, (path, sc) in enumerate(frames):
        if i in boundaries:              # wipe INTO this card, before it starts
            wdir = "work/wipes/%03d" % i
            make_wipe(frames[i - 1][0], frames[i][0], wdir)
            segments.append({"type": "seq", "path": os.path.join(wdir, "%03d.png"),
                             "frames": WIPE_FRAMES})
        segments.append({"type": "still", "path": path,
                         "frames": max(1, int(round(sc["dur"] * 30)))})
    total = sum(g["frames"] for g in segments) / 30.0
    print("segments:", len(segments), "wipes:", len(boundaries), "total %.2fs" % total)

    clips = sorted(f for f in os.listdir("audio") if f.startswith("clip") and f.endswith(".mp3"))
    with open("work/voice.txt", "w") as f:
        for c in clips:
            f.write("file '%s'\n" % os.path.abspath(os.path.join("audio", c)))
    subprocess.run([FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", "work/voice.txt",
                    "-c:a", "pcm_s16le", "work/voice.wav"], check=True, capture_output=True)

    subprocess.run([sys.executable, os.path.join(HERE, "music.py"), str(total + 1)], check=True)

    ins = []
    for g in segments:
        if g["type"] == "still":
            ins += ["-loop", "1", "-framerate", "30", "-t", "%.4f" % (g["frames"] / 30.0),
                    "-i", os.path.abspath(g["path"])]
        else:
            ins += ["-framerate", "30", "-start_number", "0", "-i", os.path.abspath(g["path"])]

    n = len(segments)
    vi, mi = n, n + 1
    fc = ("".join("[%d:v]" % i for i in range(n)) + "concat=n=%d:v=1:a=0[vc];" % n +
          "[vc]scale=1920:1080:force_original_aspect_ratio=decrease,"
          "pad=1920:1080:(ow-iw)/2:(oh-ih)/2:white,fps=30,"
          "fade=t=in:st=0:d=0.5:color=white,"
          "fade=t=out:st=%.2f:d=0.8:color=white,format=yuv420p[vo];" % (total - 0.9) +
          "[%d:a]highpass=f=70,acompressor=threshold=0.09:ratio=3:attack=8:release=180," % vi +
          "loudnorm=I=-18:TP=-2:LRA=9[v];"
          "[%d:a]volume=0.085,lowpass=f=6000[m];" % mi +
          "[v][m]amix=inputs=2:duration=longest:dropout_transition=0,"
          "aformat=sample_fmts=fltp:channel_layouts=stereo,"
          "loudnorm=I=-16:TP=-1.5:LRA=11,"
          "afade=t=in:st=0:d=1.2,afade=t=out:st=%.2f:d=1.6[a]" % (total - 1.8))

    cmd = ([FFMPEG, "-y"] + ins +
           ["-i", os.path.abspath("work/voice.wav"),
            "-i", os.path.abspath("work/music.wav"),
            "-filter_complex", fc,
            "-map", "[vo]", "-map", "[a]",
            "-c:v", "libx264", "-preset", "medium", "-crf", args.crf,
            "-profile:v", "high", "-level", "4.1", "-pix_fmt", "yuv420p",
            "-r", "30", "-g", "60",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
            "-movflags", "+faststart", "-t", "%.3f" % total,
            args.out])

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    if os.environ.get("DUMP_CMD"):
        print("CMD:", " ".join(cmd))
    print("encoding...")
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr[-3000:])
        raise SystemExit("encode failed")

    write_outputs(args, tl, frames)


    for f in ("work/voice.wav", "work/music.wav"):
        if os.path.exists(f):
            os.remove(f)
    print("done:", args.out)


if __name__ == "__main__":
    main()
