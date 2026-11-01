#!/usr/bin/env python3
"""The reference cut: one airframe per scene on the cream stage.

Built to match a frame of the source video rather than its transcript, which is
what the earlier countdown edit got wrong. What the reference actually does,
per scene:

    * one aircraft, side-on, filling ~90 % of the frame width
    * warm cream cyc, perspective tile floor, hard shadow on the right
    * a single small red badge in the top-left corner — that is *all* the type
    * no name card, no pills, no progress bar, no chapter headers
    * the shot simply holds while the narrator talks

So this module keeps the picture almost empty and lets the voice carry it. The
badge shows the rank, which is the one thing carried over from the countdown
structure.

    python3 video/build_cream.py                # full film
    python3 video/build_cream.py --still 30     # one frame, for checking
    python3 video/build_cream.py --draft        # 960x540, fast
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time

import numpy as np
from PIL import Image, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import build as B                                        # noqa: E402
from build_countdown import sfx                           # noqa: E402
from content_countdown import END_VO, INTRO_VO            # noqa: E402
from content_countdown import ENTRIES                    # noqa: E402
from engine import audio as A                          # noqa: E402
from engine import config as C                            # noqa: E402
from engine.cream import CreamStage, airframe, year_badge  # noqa: E402
from engine.scenes import camera                          # noqa: E402

ROOT = os.path.dirname(HERE)
ASSETS = os.path.join(ROOT, "assets")      # keys are "fleet/<name>"

LEAD = 0.45           # silence before the line starts
TAIL = 1.15           # hold after it ends — the reference lets each shot sit
INTRO_TAIL = 1.30

BASELINE = 790        # ground line the wheels touch
MAX_H = 700           # nothing may touch the top third of the frame
FULL_W = 1815         # airframe width at full frame
INTRO_W = 1290        # establishing shot: same aircraft, much smaller


def timeline(vo_dir: str, upto: int | None = None):
    """Same narration cues as the countdown, but each shot is allowed to sit."""
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
    segs.append({"kind": "end", "start": t, "dur": max(5.4, end_vo + 2.2),
                 "vo": end_vo, "vo_at": 0.45})
    return segs, segs[-1]["start"] + segs[-1]["dur"]


def grain(f: Image.Image, amount: float = 5.0, seed: int = 0) -> Image.Image:
    """Fine film grain — the reference frame is not clean digital."""
    rng = np.random.default_rng(seed)
    n = rng.normal(0, 1, (f.height, f.width)).astype(np.float32)
    n = np.asarray(Image.fromarray(((n * 0.5 + 0.5) * 255).astype(np.uint8), "L")
                   .filter(ImageFilter.GaussianBlur(0.6))).astype(np.float32)
    n = (n - 127.5) / 127.5 * amount
    a = np.asarray(f).astype(np.float32) + n[..., None]
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "RGB")


class CreamRenderer:
    def __init__(self, entries):
        self.entries = entries
        self.n = len(entries)
        self.stage = CreamStage()
        self._bg = self.stage.frame()

    def beat(self, entry, idx, local, dur) -> Image.Image:
        key = entry[0]
        f = self._bg.copy()
        airframe(f, os.path.join(ASSETS, f"{key}.png"), 950, BASELINE, FULL_W,
                 max_height=MAX_H)

        # a breath of movement, nothing that reads as a zoom
        p = C.clamp(local / max(0.1, dur))
        z = 1.0 + (0.022 * C.ease_in_out(p) if idx % 2 == 0
                   else 0.022 * (1.0 - C.ease_in_out(p)))
        f = camera(f, z, cy=C.H * 0.55)
        year_badge(f, f"{idx + 1:02d}")
        return grain(f, 2.6, seed=idx)

    def intro(self, local, dur) -> Image.Image:
        f = self._bg.copy()
        airframe(f, os.path.join(ASSETS, f"{ENTRIES[0][0]}.png"),
                 880, BASELINE - 10, INTRO_W, max_height=MAX_H - 60)
        f = camera(f, 1.0 + 0.030 * C.ease_in_out(C.clamp(local / max(0.1, dur))),
                   cy=C.H * 0.55)
        return grain(f, 2.6, seed=99)

    def end(self, local, dur) -> Image.Image:
        """The stage empties out: same room, nothing on it, no type."""
        f = self._bg.copy()
        f = camera(f, 1.0 + 0.028 * C.ease_in_out(C.clamp(local / max(0.1, dur))),
                   cy=C.H * 0.55)
        return grain(f, 2.6, seed=199)


def mix(segs, total, vo_dir, out_path):
    """Narration over a quiet bed, with the same ticks on every cut."""
    n = int(total * A.SR) + A.SR
    bed = A.make_bed(total, bpm=72, root=50.0)
    buf = np.zeros(n, dtype=np.float32)
    buf[: len(bed)] += bed * 0.11

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
    for at, kind, gain in sfx(segs):
        clip = A.sfx(kind)
        a = int(at * A.SR)
        b = min(n, a + len(clip))
        if b > a:
            fx[a:b] += clip[: b - a] * gain * 0.55

    out = music + voice * 0.95 + fx
    out = np.tanh(out * 1.05) * 0.92
    A.write_wav(out_path, out)
    return out_path


def render(segs, total, out, w=C.W, h=C.H, fps=C.FPS, mix_path=None):
    r = CreamRenderer([e[:4] for e in ENTRIES])
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
            f = r.intro(local, s["dur"])
        elif s["kind"] == "end":
            f = r.end(local, s["dur"])
        else:
            f = r.beat(s["entry"], s["idx"], local, s["dur"])
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
                                                  "hikka_japan_cream.mp4"))
    ap.add_argument("--draft", action="store_true")
    ap.add_argument("--still", type=float, default=None)
    args = ap.parse_args()

    segs, total = timeline(args.vo, None)
    os.makedirs(os.path.join(ROOT, "build"), exist_ok=True)
    print(f"  {len(segs)} scenes, {total:.1f}s")

    if args.still is not None:
        r = CreamRenderer([e[:4] for e in ENTRIES])
        t, s = args.still, None
        for x in segs:
            if x["start"] <= t < x["start"] + x["dur"]:
                s = x
                break
        s = s or segs[-1]
        local = t - s["start"]
        f = (r.intro(local, s["dur"]) if s["kind"] == "intro"
             else r.end(local, s["dur"]) if s["kind"] == "end"
             else r.beat(s["entry"], s["idx"], local, s["dur"]))
        out = os.path.join(ROOT, "build", "cream_still.png")
        f.save(out)
        print("  ", out)
        return

    mix_path = os.path.join(ROOT, "build", "mix_cream.wav")
    mix(segs, total, args.vo, mix_path)
    print("  audio mixed")

    w, h = (960, 540) if args.draft else (C.W, C.H)
    render(segs, total, args.out, w, h, C.FPS, mix_path)


if __name__ == "__main__":
    main()
