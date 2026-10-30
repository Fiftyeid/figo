"""QC helper: render a 1s slice around a given time and grab a frame."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_final as bf, storyboard as sb
from mgfx.render import render
from mgfx.assgen import ts
import subprocess

def sec(t):
    h, m, s = t.split(":"); return int(h)*3600 + int(m)*60 + float(s)

def shift_ass(src, dst, off):
    out = []
    for line in open(src, encoding="utf-8"):
        if line.startswith("Dialogue:"):
            p = line.split(",", 9)
            t0 = max(0.0, sec(p[1]) - off); t1 = max(0.0, sec(p[2]) - off)
            if t1 - t0 < 0.02: continue
            p[1], p[2] = ts(t0), ts(t1); line = ",".join(p)
        out.append(line)
    open(dst, "w", encoding="utf-8").write("".join(out))

ass = bf.build_ass(os.path.join(bf.HERE, "deliver", "final.ass"))
FF = __import__("imageio_ffmpeg").get_ffmpeg_exe()
for t in [float(x) for x in sys.argv[1:]]:
    start = max(0.0, t - 0.5)
    sh = f"/tmp/sh_{t:.0f}.ass"; shift_ass(ass, sh, start)
    mp4 = f"/tmp/qc_{t:.0f}.mp4"
    render(mp4, 1.0, sh, audio=os.path.join(bf.HERE, "media", "voice.mp3"),
           palette="seerah", t_start=start, total_duration=sb.DURATION, progress=False)
    subprocess.run([FF, "-v", "error", "-ss", "0.55", "-i", mp4, "-frames:v", "1",
                    "-update", "1", "-y", f"/tmp/qc_{t:.0f}.png"], check=True)
    print("qc", t, "->", f"/tmp/qc_{t:.0f}.png")
