#!/usr/bin/env python3
"""The countdown cut, in the HIKKA showroom house style.

The cream stage was a copy of another channel's look. This is ours: the light
showroom cyc, the editorial furniture from the first film — flag chip, kicker,
episode line, hairline rule with a progress fill, corner credits — and the same
two-tone headline in the intro.

What is new here is only the beat: instead of a chapter header and a row of
item pills, each shot is a single airframe with a rank numeral, its name, its
role and its fleet count. The chrome does not move; the room does.

    python3 video/build_showroom.py                 # full 1080p30
    python3 video/build_showroom.py --still 30
    python3 video/build_showroom.py --draft         # 960x540
"""
from __future__ import annotations

import argparse
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import build as B                                                  # noqa: E402
from content_countdown import END_VO, ENTRIES, INTRO_VO            # noqa: E402
from engine import config as C                                     # noqa: E402
from engine import pixels as P                                     # noqa: E402
from engine.fleet import (FLEET_BASE, FLEET_BOX, JP_RED, META_JP,   # noqa: E402
                          FleetRenderer, _camera, _hook_halo, _paleness)
from engine.scenes import Stage, fit, paste_rgba, tw               # noqa: E402

ROOT = os.path.dirname(HERE)
ASSETS = os.path.join(ROOT, "assets")

LEAD = 0.34           # a beat of silence before each line
TAIL = 0.52           # and a beat after it
INTRO_TAIL = 0.80

BOX = (1200, 420)      # slightly smaller than the chapter film: the name needs air
BASELINE = 742


def timeline(vo_dir: str, upto: int | None = None):
    """Narration drives the cut, exactly as in the chapter film."""
    intro = B.vo_duration(os.path.join(vo_dir, "intro.mp3"))
    segs = [{"kind": "intro", "start": 0.0,
             "dur": LEAD + max(intro, 5.0) + INTRO_TAIL, "vo": intro, "vo_at": LEAD}]
    t = segs[0]["dur"]
    for i, (asset, name, role, count, _vo) in enumerate(ENTRIES if not upto else ENTRIES[:upto]):
        vo = B.vo_duration(os.path.join(vo_dir, f"{i + 1:02d}.mp3"))
        dur = LEAD + max(vo, 2.4) + TAIL
        segs.append({"kind": "beat", "start": t, "dur": dur, "vo": vo,
                     "vo_at": LEAD, "idx": i, "entry": (asset, name, role, count)})
        t += dur
    end_vo = B.vo_duration(os.path.join(vo_dir, "end.mp3"))
    segs.append({"kind": "end", "start": t, "dur": max(5.2, end_vo + 1.9),
                 "vo": end_vo, "vo_at": 0.40})
    return segs, segs[-1]["start"] + segs[-1]["dur"]


class ShowroomRenderer(FleetRenderer):
    """FleetRenderer, but every shot is a ranked single airframe."""

    def __init__(self, entries, assets_dir):
        # deliberately not calling FleetRenderer.__init__: it wants a section
        # table, and this film has no chapters — only entries.
        self.entries = entries
        self.n = len(entries)
        self.assets = assets_dir
        self.stage = Stage()
        self.total = 1.0
        self._hook_cfg = None
        self.intro_lines = []

    # ------------------------------------------------------------- one entry
    def beat(self, entry, idx, local, dur, t_global) -> Image.Image:
        key, name, role, count = entry
        f = self.stage.frame()

        path = self.asset(key)
        if path:
            spr = fit(path, BOX[0], BOX[1])
            x = int(C.DIVIDER_X - spr.width / 2)
            y = int(BASELINE - spr.height)

            halo, pad = _hook_halo(path, BOX[0], BOX[1])
            f.paste((150, 154, 160), (x - pad, y - pad),
                    halo.point(lambda v: int(v * (0.16 + 0.34 * _paleness(path)))))
            rgb, m = P.shadow(path, spr.height, spread=56, opacity=0.18)
            m2 = m.resize((max(8, int(spr.width * 1.14)), max(10, int(m.height * 0.12))),
                          Image.BILINEAR).point(lambda v: int(v * 0.55))
            f.paste(rgb.getpixel((0, 0)),
                    (int(C.DIVIDER_X - m2.width / 2), int(BASELINE - m2.height * 0.30)), m2)
            paste_rgba(f, spr, (x, y))

        # alternating dolly, as in the chapter film
        p = C.clamp(local / max(0.1, dur))
        e = C.ease_in_out(p)
        f = _camera(f, 1.0 + 0.045 * (e if idx % 2 == 0 else (1.0 - e)), cy=C.H * 0.52)

        self._rank(f, idx, p)
        self._name(f, name, role, count, p)

        # house furniture, laid over the move so it stays crisp
        self.top_bar(f, t_global, 1.0)
        self.bottom_bar(f, 1.0,
                        left_note="19 TYPES   ·   ONE FLEET   ·   OPEN SOURCES")
        return f

    # ---------------------------------------------------------------- chrome
    def _rank(self, f, idx, p):
        e = C.ramp(p, 0.0, 0.18, C.ease_out_expo)
        size = 186
        ny = 296 - (1 - e) * 22
        P.draw_text(f, (C.SAFE + 6, ny), f"{idx + 1:02d}", "black", size, C.INK,
                    tracking=-6, anchor="lt", alpha=e)
        P.draw_text(f, (C.SAFE + 12, ny + size + 4), f"{self.n:02d}", "bold", 30,
                    C.INK_FAINT, tracking=4, anchor="lt", alpha=e)
        d = ImageDraw.Draw(f, "RGBA")
        w = int(120 * e)
        d.line([(C.SAFE + 12, ny - 26), (C.SAFE + 12 + w, ny - 26)],
               fill=JP_RED + (int(235 * e),), width=4)

    def _name(self, f, name, role, count, p):
        e = C.ramp(p, 0.06, 0.22, C.ease_out_expo)
        size = P.fit_size(name, "bold", 1240, 58, 3)
        ly = 846
        P.draw_text(f, (C.DIVIDER_X, ly - (1 - e) * 12), name, "bold", size, C.INK,
                    tracking=3, anchor="mt", alpha=e)

        msize, gap = 19, 12
        w1 = tw(role, "bold", msize, 5.0) + 44
        w2 = tw(count, "bold", msize, 5.0) + 44
        x = C.DIVIDER_X - (w1 + gap + w2) / 2
        y = ly + size + 8
        P.draw_pill(f, x, y, role, size=msize, fg=C.PAPER, bg=C.CHARCOAL,
                    tracking=5.0, pad_x=22, pad_y=10, alpha=e)
        P.draw_pill(f, x + w1 + gap, y, count, size=msize, fg=C.INK, bg=(232, 235, 239),
                    tracking=5.0, pad_x=22, pad_y=10, alpha=e)

def mix(segs, total, vo_dir, out_path):
    """Narration, a quiet bed and the same ticks on every cut."""
    from engine import audio as A
    n = int(total * A.SR) + A.SR
    bed = A.make_bed(total, bpm=74, root=52.0)
    buf = np.zeros(n, dtype=np.float32)
    buf[: len(bed)] += bed * 0.13

    voice = np.zeros(n, dtype=np.float32)
    for s in segs:
        if s["vo"] <= 0.5:
            continue
        key = ("intro" if s["kind"] == "intro"
               else "end" if s["kind"] == "end" else f"{s['idx'] + 1:02d}")
        wav = os.path.join(ROOT, "build", "vo_cache",
                           os.path.basename(vo_dir) + "__" + key + ".mp3.wav")
        if not os.path.exists(wav):
            continue
        clip = A.read_wav(wav)
        rms = float(np.sqrt(np.mean(clip ** 2))) or 1.0
        clip = clip * min(2.2, 0.11 / rms)
        a = int((s["start"] + s["vo_at"]) * A.SR)
        b = min(n, a + len(clip))
        voice[a:b] += clip[: b - a]

    env = np.abs(voice)
    k = np.ones(int(0.20 * A.SR)) / int(0.20 * A.SR)
    duck = np.clip(np.convolve(env, k, mode="same") / 0.06, 0, 1) * 0.72
    music = (buf * (1.0 - duck)).astype(np.float32)

    fx = np.zeros(n, dtype=np.float32)
    at = 0.0
    for s in segs[1:]:
        at = s["start"]
        clip = A.sfx("tick")
        a = int(at * A.SR)
        b = min(n, a + len(clip))
        if b > a:
            fx[a:b] += clip[: b - a] * 0.40

    out = music + voice * 0.95 + fx
    out = np.tanh(out * 1.05) * 0.92
    A.write_wav(out_path, out)
    return out_path


def render(segs, total, out, w=C.W, h=C.H, fps=C.FPS, mix_path=None):
    import subprocess
    import time
    r = ShowroomRenderer([e[:4] for e in ENTRIES], ASSETS)
    r.total = total
    frames = int(total * fps)
    cmd = [B.FFMPEG, "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}",
           "-r", str(fps), "-i", "-", "-i", mix_path,
           "-c:v", "libx264", "-preset", "fast", "-crf", "20",
           "-pix_fmt", "yuv420p", "-movflags", "+faststart",
           "-c:a", "aac", "-b:a", "192k", "-shortest", out]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    t0, idx = time.time(), 0
    for k in range(frames):
        t = k / fps
        while idx + 1 < len(segs) and t >= segs[idx]["start"] + segs[idx]["dur"]:
            idx += 1
        s = segs[idx]
        local = t - s["start"]
        if s["kind"] == "intro":
            f = r.draw_intro(r.stage.frame(), local, s["dur"])
        elif s["kind"] == "end":
            f = r.stage.frame()
            r.draw_endcard(f, local)          # draws in place, returns nothing
            r.top_bar(f, t, 1.0)
        else:
            f = r.beat(s["entry"], s["idx"], local, s["dur"], t)
        proc.stdin.write(np.asarray(f, dtype=np.uint8).tobytes())
        if k % 30 == 0:
            el = time.time() - t0
            print(f"\r  frame {k}/{frames}  {el:5.1f}s  "
                  f"({(k + 1) / max(el, 0.001):4.1f} fps)", end="", flush=True)
    proc.stdin.close()
    proc.wait()
    print(f"\n  wrote {out} in {time.time() - t0:.0f}s")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vo", default=os.path.join(ROOT, "audio", "vo_cd"))
    ap.add_argument("--out", default=os.path.join(ROOT, "deliverables",
                                                  "hikka_japan_showroom.mp4"))
    ap.add_argument("--draft", action="store_true")
    ap.add_argument("--still", type=float, default=None)
    args = ap.parse_args()

    segs, total = timeline(args.vo, None)
    os.makedirs(os.path.join(ROOT, "build"), exist_ok=True)
    print(f"  {len(segs)} shots, {total:.1f}s")

    if args.still is not None:
        r = ShowroomRenderer([e[:4] for e in ENTRIES], ASSETS)
        r.total = total
        t, s = args.still, segs[-1]
        for x in segs:
            if x["start"] <= t < x["start"] + x["dur"]:
                s = x
                break
        local = t - s["start"]
        if s["kind"] == "intro":
            f = r.draw_intro(r.stage.frame(), local, s["dur"])
        elif s["kind"] == "end":
            f = r.stage.frame()
            r.draw_endcard(f, local)
        else:
            f = r.beat(s["entry"], s["idx"], local, s["dur"], t)
        out = os.path.join(ROOT, "build", "showroom_still.png")
        f.save(out)
        print("  ", out)
        return

    mix_path = os.path.join(ROOT, "build", "mix_showroom.wav")
    mix(segs, total, args.vo, mix_path)
    print("  audio mixed")

    w, h = (960, 540) if args.draft else (C.W, C.H)
    render(segs, total, args.out, w, h, C.FPS, mix_path)


if __name__ == "__main__":
    main()
