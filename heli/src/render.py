# -*- coding: utf-8 -*-
"""Render the video frames -> build/video_noaudio.mp4 (parallel segments).
usage: python3 render.py frames t1 t2 ...   |  range t0 t1 [out]  |  all [workers] [segments] [--resume] [--until T]
"""
import os, sys, math, time, subprocess
import multiprocessing as mp
import imageio_ffmpeg
from PIL import Image, ImageDraw
from common import *
from storyboard import build_shots
from shots import SHOT_TYPES, T
from diagrams import DIAGRAMS

FF = imageio_ffmpeg.get_ffmpeg_exe()
XF = 0.32
ALL_TYPES = dict(SHOT_TYPES, **DIAGRAMS)

TAGS = dict(chinook="ANSWER 1 · CH-47F CHINOOK", hind="ANSWER 2 · MI-24 HIND", lynx="ANSWER 3 · G-LYNX",
            lynxmods="ANSWER 3 · G-LYNX", record="ANSWER 3 · G-LYNX", wall="THE WALL", stall="THE WALL",
            trap="THE WALL", compound="BREAKING THE WALL", x2="BREAKING THE WALL", tiltrotor="ANSWER 4 · MV-75",
            verdict="THE VERDICT")
NO_TAG = ("title", "answer", "end")


def make_shot(spec):
    sp = dict(spec)
    typ = sp.pop("type")
    sp.pop("section", None)
    sp.pop("trans", None)
    st, en = sp.pop("start"), sp.pop("end")
    return ALL_TYPES[typ](st, en, **sp)


class Renderer:
    def __init__(self):
        self.specs, self.tl = build_shots()
        self.shots = [None] * len(self.specs)
        self.duration = self.tl["duration"]

    def shot(self, k):
        if self.shots[k] is None:
            s = make_shot(self.specs[k])
            s.prepare()
            self.shots[k] = s
        return self.shots[k]

    def release_before(self, k):
        for j in range(0, max(0, k - 1)):
            self.shots[j] = None

    def index_at(self, t):
        lo, hi = 0, len(self.specs) - 1
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if self.specs[mid]["start"] <= t:
                lo = mid
            else:
                hi = mid - 1
        return lo

    def tag(self, im, t, k):
        sp = self.specs[k]
        sid = sp["section"]
        if sid not in TAGS or sp["type"] in NO_TAG:
            return
        # section span
        secs = [s for s in self.tl["sections"] if s["id"] == sid][0]
        a = min(ease_out_cubic((t - sp["start"] - 0.5) / 0.4), 1 - ease_in_out((t - (secs["end"] - 0.2)) / 0.3))
        if a <= 0:
            return
        lab = T(TAGS[sid], "mono", 24, WHITE, tracking=3)
        bg = Image.new("RGBA", (lab.width + 40, lab.height + 6), (0, 0, 0, 120))
        d = ImageDraw.Draw(bg)
        d.rectangle([0, 0, 5, bg.height], fill=AMBER + (255,))
        bg.alpha_composite(lab, (24, 3))
        paste_at(im, bg, W - bg.width - 40, 40, a * 0.9)

    def frame(self, t):
        k = self.index_at(t)
        cur = self.shot(k).frame(t)
        st = self.specs[k]["start"]
        trans = self.specs[k].get("trans", "xf")
        if k > 0 and t - st < XF and trans == "xf":
            prev = self.shot(k - 1).frame(t)
            a = ease_in_out((t - st) / XF)
            cur = Image.blend(prev.convert("RGB"), cur.convert("RGB"), a).convert("RGBA")
        if cur.mode != "RGBA":
            cur = cur.convert("RGBA")
        if trans == "flash" and 0 <= t - st < 0.22:
            a = 1 - (t - st) / 0.22
            cur.alpha_composite(Image.new("RGBA", cur.size, (255, 255, 255, int(210 * a))))
        self.tag(cur, t, k)
        if t < 0.4 or t > self.duration - 1.5:
            a = min(clamp(t / 0.4), clamp((self.duration - t) / 1.5))
            cur.alpha_composite(Image.new("RGBA", cur.size, (0, 0, 0, int(255 * (1 - a)))))
        self.release_before(k)
        return cur.convert("RGB")


def encode_cmd(out, crf=18, preset="veryfast"):
    return [FF, "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
            "-i", "-", "-c:v", "libx264", "-preset", preset, "-crf", str(crf), "-pix_fmt", "yuv420p",
            "-g", str(FPS * 2), "-bf", "2", out]


def render_range(args):
    f0, f1, out, wid = args
    r = Renderer()
    p = subprocess.Popen(encode_cmd(out), stdin=subprocess.PIPE)
    t_start = time.time()
    for f in range(f0, f1):
        im = r.frame(f / FPS)
        p.stdin.write(im.tobytes())
        if (f - f0) % 250 == 0:
            el = time.time() - t_start
            done = f - f0 + 1
            print(f"[w{wid}] frame {f} ({done}/{f1 - f0})  {done / max(el, 1e-6):.1f} fps", flush=True)
    p.stdin.close()
    p.wait()
    return out


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    os.makedirs(os.path.join(BUILD, "preview"), exist_ok=True)
    if cmd == "frames":
        r = Renderer()
        for ts in sys.argv[2:]:
            t = float(ts)
            im = r.frame(t)
            im.save(os.path.join(BUILD, "preview", f"f_{t:07.2f}.jpg"), quality=88)
            print("saved", t, flush=True)
        return
    if cmd == "range":
        t0, t1 = float(sys.argv[2]), float(sys.argv[3])
        out = sys.argv[4] if len(sys.argv) > 4 else os.path.join(BUILD, "test_range.mp4")
        render_range((int(t0 * FPS), int(t1 * FPS), out, 0))
        print(out)
        return
    if cmd == "all":
        args = [a for a in sys.argv[2:] if not a.startswith("--")]
        nw = int(args[0]) if len(args) > 0 else 2
        nseg = int(args[1]) if len(args) > 1 else 8
        r = Renderer()
        until = r.duration
        if "--until" in sys.argv:
            until = float(sys.argv[sys.argv.index("--until") + 1])
        total = int(math.ceil(until * FPS))
        bounds = [0]
        starts = [int(round(s["start"] * FPS)) for s in r.specs]
        for i in range(1, nseg):
            target = total * i / nseg
            b = min(starts, key=lambda x: abs(x - target))
            if bounds[-1] < b < total:
                bounds.append(b)
        bounds.append(total)
        segdir = os.path.join(BUILD, "segments")
        os.makedirs(segdir, exist_ok=True)
        jobs = [(bounds[i], bounds[i + 1], os.path.join(segdir, f"seg_{i:02d}.mp4"), i) for i in range(len(bounds) - 1)]
        if "--resume" in sys.argv:
            jobs = [j for j in jobs if not (os.path.exists(j[2]) and os.path.getsize(j[2]) > 1000)]
        t0 = time.time()
        with mp.get_context("fork").Pool(nw) as pool:
            for out in pool.imap_unordered(render_range, jobs):
                print("done", out, f"{time.time() - t0:.0f}s", flush=True)
        lst = os.path.join(segdir, "list.txt")
        with open(lst, "w") as f:
            for i in range(len(bounds) - 1):
                f.write(f"file 'seg_{i:02d}.mp4'\n")
        subprocess.run([FF, "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy",
                        os.path.join(BUILD, "video_noaudio.mp4")], check=True)
        print("video_noaudio.mp4 ready", f"{time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
