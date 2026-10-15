# -*- coding: utf-8 -*-
"""
Render the video.
  python3 render.py frames 12.5 80 300      -> preview JPGs in build/preview/
  python3 render.py range 60 75             -> build/test_range.mp4 (silent)
  python3 render.py all [workers]           -> build/segments/*.mp4 + build/video_noaudio.mp4
"""
import os, sys, json, math, subprocess, time
import multiprocessing as mp
import numpy as np
from PIL import Image, ImageDraw
import imageio_ffmpeg

from common import *
from shots import SHOT_TYPES, appear, to_ar_digits
from storyboard import build_shots, NUM
from script_data import SECTIONS

FF = imageio_ffmpeg.get_ffmpeg_exe()
XF = 0.32          # crossfade between shots (s)
TITLES = {s["id"]: s["title"] for s in SECTIONS}
ORDER = ["cairo", "giza", "alex", "portsaid", "ismailia", "suez", "damietta", "dakahlia", "sharqia_gharbia",
         "beheira", "qalyubia", "monufia", "kafrelsheikh", "benisuef", "faiyum", "minya", "asyut", "sohag", "qena",
         "luxor", "aswan", "redsea", "newvalley", "matrouh", "sinai"]
COUNT = {}
_c = 0
for sid in ORDER:
    _c += 2 if sid in ("sharqia_gharbia", "sinai") else 1
    COUNT[sid] = _c


def make_shot(spec):
    sp = dict(spec)
    typ = sp.pop("type")
    sp.pop("section", None)
    start, end = sp.pop("start"), sp.pop("end")
    if "frame_" in sp and sp["frame_"] is not None:
        sp["frame_"] = tuple(sp["frame_"])
    return SHOT_TYPES[typ](start, end, **sp)


class Globals:
    """Badge (top-right) + segmented progress bar (bottom) for governorate sections."""

    def __init__(self, timeline):
        self.secs = timeline["sections"]
        self.cache = {}

    def badge(self, sid):
        if sid not in self.cache:
            num = chip(f"{NUM[sid]} / ٢٧", GOLD, "black", 34, padx=18, pady=2)
            name = text_image(TITLES[sid], "black", 40, WHITE, pad=4)
            w = num.width + name.width + 60
            h = max(num.height, name.height) + 22
            box = rounded_rect((w, h), h // 2, (8, 12, 26, 210))
            box.alpha_composite(num, (w - 12 - num.width, (h - num.height) // 2))
            box.alpha_composite(name, (w - 12 - num.width - 18 - name.width, (h - name.height) // 2 - 2))
            self.cache[sid] = box
        return self.cache[sid]

    def draw(self, im, t):
        sec = None
        for s in self.secs:
            if s["start"] - 0.3 <= t < s["end"] + 0.5:
                sec = s
                break
        if sec is None or sec["id"] in ("intro", "outro"):
            return
        sid = sec["id"]
        a_in, _ = appear(t, sec["start"] + 0.6, 0.4)
        a_out = 1 - ease_in_out((t - (sec["end"] + 0.1)) / 0.3)
        a = min(a_in, a_out)
        if a <= 0.01:
            return
        b = self.badge(sid)
        off = (1 - ease_out_cubic((t - sec["start"] - 0.6) / 0.5)) * 80
        paste_at(im, b, W - 40 - b.width + off, 34, alpha=a)
        # progress bar
        n, done = 27, COUNT[sid]
        prev = done - (2 if sid in ("sharqia_gharbia", "sinai") else 1)
        bw = 1500
        x0 = (W - bw) / 2
        seg = bw / n
        y = H - 22
        d = ImageDraw.Draw(im)
        for k in range(n):
            # RTL: first governorate on the right
            xr = x0 + bw - k * seg
            xl = xr - seg + 4
            if k < prev:
                col = GOLD + (int(170 * a),)
            elif k < done:
                p = ease_out_cubic((t - sec["start"] - 0.8) / 0.8)
                col = GOLD + (int(255 * a * max(0.25, p)),)
            else:
                col = (255, 255, 255, int(45 * a))
            d.rounded_rectangle([xl, y, xr, y + 7], radius=3, fill=col)


class Renderer:
    def __init__(self):
        self.specs, self.tl = build_shots()
        self.shots = [None] * len(self.specs)
        self.glob = Globals(self.tl)
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

    def frame(self, t):
        k = self.index_at(t)
        cur = self.shot(k).frame(t)
        st = self.specs[k]["start"]
        if k > 0 and t - st < XF:
            prev = self.shot(k - 1).frame(t)
            a = ease_in_out((t - st) / XF)
            cur = Image.blend(prev.convert("RGB"), cur.convert("RGB"), a).convert("RGBA")
        if cur.mode != "RGBA":
            cur = cur.convert("RGBA")
        self.glob.draw(cur, t)
        # global fade in/out
        if t < 0.5 or t > self.duration - 1.2:
            a = min(clamp(t / 0.5), clamp((self.duration - t) / 1.2))
            black = Image.new("RGBA", cur.size, (0, 0, 0, int(255 * (1 - a))))
            cur.alpha_composite(black)
        self.release_before(k)
        return cur.convert("RGB")


def encode_cmd(out, crf=17, preset="veryfast"):
    return [FF, "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
            "-i", "-", "-c:v", "libx264", "-preset", preset, "-crf", str(crf), "-pix_fmt", "yuv420p",
            "-g", str(FPS * 2), "-bf", "2", out]


def render_range(args):
    f0, f1, out, wid = args
    r = Renderer()
    p = subprocess.Popen(encode_cmd(out), stdin=subprocess.PIPE)
    t_start = time.time()
    for f in range(f0, f1):
        t = f / FPS
        im = r.frame(t)
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
            print("saved", t)
        return
    if cmd == "range":
        t0, t1 = float(sys.argv[2]), float(sys.argv[3])
        out = os.path.join(BUILD, "test_range.mp4")
        render_range((int(t0 * FPS), int(t1 * FPS), out, 0))
        print(out)
        return
    if cmd == "all":
        nw = int(sys.argv[2]) if len(sys.argv) > 2 else 2
        nseg = int(sys.argv[3]) if len(sys.argv) > 3 else 8
        r = Renderer()
        total = int(math.ceil(r.duration * FPS))
        # split on shot boundaries into nseg chunks of ~equal length
        bounds = [0]
        starts = [int(round(s["start"] * FPS)) for s in r.specs]
        for i in range(1, nseg):
            target = total * i / nseg
            b = min(starts, key=lambda x: abs(x - target))
            if b > bounds[-1]:
                bounds.append(b)
        bounds.append(total)
        segdir = os.path.join(BUILD, "segments")
        os.makedirs(segdir, exist_ok=True)
        jobs = [(bounds[i], bounds[i + 1], os.path.join(segdir, f"seg_{i:02d}.mp4"), i) for i in range(len(bounds) - 1)]
        jobs = [j for j in jobs if not (os.path.exists(j[2]) and os.path.getsize(j[2]) > 1000 and "--resume" in sys.argv)]
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
