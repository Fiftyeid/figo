"""Vertical Shorts cut (1080x1920) — same design system, one card per narrator line.

Each card's duration is driven by its own narration clip, so sync is exact.
"""
import glob
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
W, H = 1080, 1920
M = 60

CARDS = [
    ("intro", None, None),
    ("t90m", "T-90M PRORYV", "MAIN BATTLE TANK · 2020"),
    ("t72b3", "T-72B3", "MAIN BATTLE TANK · 2011"),
    ("bmpt", "BMPT TERMINATOR", "TANK SUPPORT · 2018"),
    ("bmp3", "BMP-3", "INFANTRY FIGHTING VEHICLE · 1987"),
    ("tos1a", "TOS-1A", "THERMOBARIC ARTILLERY · 2001"),
    ("2s7", "2S7 PION", "SELF-PROPELLED GUN · 1975"),
    ("btr80", "BTR-80", "APC · 1986"),
    ("typhoon_k", "TYPHOON-K", "MRAP TRUCK · 2014"),
    ("outro", None, None),
]


def card_frame(kind, name, meta, idx, renders_dir):
    from PIL import Image, ImageDraw
    canvas = Image.new("RGBA", (W, H), R.WHITE + (255,))
    d = ImageDraw.Draw(canvas)

    # frame marks
    for (x, y, dx, dy) in [(M - 24, 120, 1, 1), (W - M + 24, 120, -1, 1),
                           (M - 24, H - 120, 1, -1), (W - M + 24, H - 120, -1, -1)]:
        d.line([(x, y), (x + dx * 40, y)], fill=R.RED, width=3)
        d.line([(x, y), (x, y + dy * 40)], fill=R.RED, width=3)

    # top band
    d.rectangle([0, 200, W, 268], fill=R.RED)
    R.tracked(d, (M, 220), "RUSSIAN ARMOR · SHORTS", R.font(R.F_BOLD, 26), R.WHITE, tracking=5)
    if idx:
        R.tracked(d, (W - M, 222), "%02d/08" % idx, R.font(R.F_BOLD, 24), R.WHITE, tracking=2, anchor="ra")

    if kind == "intro":
        f = R.font(R.F_BOLD, 108)
        R.tracked(d, (M, 560), "52", f, R.RED, tracking=0)
        f2 = R.font(R.F_BOLD, 62)
        R.tracked(d, (M, 720), "RUSSIAN", f2, R.INK, tracking=2)
        R.tracked(d, (M, 800), "ARMORED", f2, R.RED, tracking=2)
        R.tracked(d, (M, 880), "VEHICLES", f2, R.RED, tracking=2)
        R.hairline(d, [(M, 1000), (M + 420, 1000)], R.HAIR, 2)
        R.tracked(d, (M, 1030), "THE EIGHT THAT MATTER", R.font(R.F_BOLD, 34), R.GREY, tracking=4)
        hero = R.cutout(R.render_path(renders_dir, "t90m"), 940)
        hh = 760
        hero = hero.resize((int(hero.width * hh / hero.height), hh), Image.LANCZOS)
        canvas.alpha_composite(hero, ((W - hero.width) // 2, 1100))
    elif kind == "outro":
        f = R.font(R.F_BOLD, 76)
        R.tracked(d, (W // 2, 620), "FULL INVENTORY", f, R.INK, tracking=2, anchor="ma")
        R.tracked(d, (W // 2, 720), "52 MACHINES", f, R.RED, tracking=2, anchor="ma")
        R.hairline(d, [(W // 2 - 300, 850), (W // 2 + 300, 850)], R.HAIR, 2)
        f3 = R.font(R.F_BOLD, 34)
        R.tracked(d, (W // 2, 890), "8 CATEGORIES · 13 MINUTES", f3, R.GREY, tracking=3, anchor="ma")
        R.tracked(d, (W // 2, 1500), "LINK IN THE DESCRIPTION", R.font(R.F_BOLD, 30), R.RED, tracking=4, anchor="ma")
    else:
        veh = R.cutout(R.render_path(renders_dir, kind), 900)
        box = (M - 30, 330, W - M + 30, 1180)
        px, py, pw, ph = R.place(canvas, veh, box)
        f_name = R.fit_font(d, name, R.F_BOLD, W - 2 * M, 104, tracking=1)
        R.tracked(d, (M, 1250), name, f_name, R.RED, tracking=1)
        R.tracked(d, (M, 1390), meta, R.font(R.F_BOLD, 30), R.GREY, tracking=3)
        R.hairline(d, [(M, 1470), (W - M, 1470)], R.HAIR, 2)
        d.rectangle([M, 1468, M + 140, 1473], fill=R.RED)
        d.rectangle([0, 1700, W, 1772], fill=R.RED)
        R.tracked(d, (M, 1718), "52 MACHINES · FULL INVENTORY", R.font(R.F_BOLD, 26), R.WHITE, tracking=3)
    return canvas.convert("RGB")


def build(out="output/shorts-8-vehicles.mp4"):
    os.makedirs("work/shorts", exist_ok=True)
    frames, idx = [], 0
    with open("work/shorts_concat.txt", "w") as f:
        for i, (kind, name, meta) in enumerate(CARDS):
            cid = "audio/shorts/s%02d.mp3" % (i + 1)
            dur = AT.duration(cid) + 0.55
            if kind == "intro":
                dur += 0.6
            vi = None
            if kind not in ("intro", "outro"):
                vi = [c[0] for c in CARDS if c[0] not in ("intro", "outro")].index(kind) + 1
            img = card_frame(kind, name, meta, vi, "renders")
            path = "work/shorts/%02d.png" % i
            img.save(path)
            f.write("file '%s'\nduration %.3f\n" % (os.path.abspath(path), dur))
            frames.append(path)
        f.write("file '%s'\nduration 1.0\n" % os.path.abspath(frames[-1]))

    with open("work/shorts_voice.txt", "w") as f:
        for i in range(len(CARDS)):
            f.write("file '%s'\n" % os.path.abspath("audio/shorts/s%02d.mp3" % (i + 1)))

    subprocess.run([FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", "work/shorts_voice.txt",
                    "-c:a", "pcm_s16le", "work/shorts_voice.wav"], check=True, capture_output=True)
    total = AT.duration("work/shorts_voice.wav") + 0.55 * len(CARDS)

    # score: reuse the film bed, trimmed
    subprocess.run([sys.executable, os.path.join(HERE, "music.py"), str(total + 2)], check=True)

    vf = ("scale=1080:1920:force_original_aspect_ratio=decrease,"
          "pad=1080:1920:(ow-iw)/2:(oh-ih)/2:white,fps=30,"
          "fade=t=in:st=0:d=0.4:color=white,fade=t=out:st=%.2f:d=0.6:color=white,"
          "format=yuv420p" % (total - 0.7))

    cmd = [FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", "work/shorts_concat.txt",
           "-i", "work/shorts_voice.wav", "-i", "work/music.wav",
           "-filter_complex",
           "[1:a]highpass=f=70,loudnorm=I=-18:TP=-2:LRA=9[v];"
           "[2:a]volume=0.07,lowpass=f=6000[m];"
           "[v][m]amix=inputs=2:duration=first:dropout_transition=0,"
           "aformat=sample_fmts=fltp:channel_layouts=stereo,"
           "loudnorm=I=-15:TP=-1.2:LRA=11,afade=t=in:st=0:d=0.5,afade=t=out:st=%.2f:d=0.9[a]"
           % (total - 1.0),
           "-map", "0:v", "-map", "[a]", "-vf", vf,
           "-c:v", "libx264", "-preset", "medium", "-crf", "20",
           "-profile:v", "high", "-pix_fmt", "yuv420p", "-r", "30",
           "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
           "-movflags", "+faststart", "-t", "%.3f" % total, out]
    os.makedirs("output", exist_ok=True)
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr[-2500:])
        raise SystemExit("shorts encode failed")
    for f in ("work/shorts_voice.wav", "work/music.wav"):
        if os.path.exists(f):
            os.remove(f)
    print("done:", out, "%.1fs" % total)


if __name__ == "__main__":
    build()
