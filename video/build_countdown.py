#!/usr/bin/env python3
"""Render 19 AIRCRAFT JAPAN FLIES — the countdown edit of EP.03.

    python3 video/build_countdown.py                  # full 1080p30
    python3 video/build_countdown.py --draft           # 960x540 proof
    python3 video/build_countdown.py --still 3         # one frame
    python3 video/build_countdown.py --audio-only

Every entry is held open for exactly as long as its narration clip, so the
rank number changes on the voice, never ahead of it.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import build as B  # noqa: E402
from engine import audio as A  # noqa: E402
from engine import config as C  # noqa: E402
from engine import pixels as P  # noqa: E402
from engine import subs  # noqa: E402
from engine.fleet import FleetRenderer, _hook_halo, _paleness  # noqa: E402
from engine.scenes import Stage, camera, fit, paste_rgba, tw  # noqa: E402
from content_countdown import END_VO, ENTRIES, INTRO_VO  # noqa: E402

ROOT = os.path.dirname(HERE)

BASE = 806
BOX = (1472, 528)
JP_RED = (188, 0, 45)

LEAD = 0.30        # beat between the cut and the voice
TAIL = 0.42        # beat after the voice before the next cut
INTRO_LEAD = 0.35
ENDCARD = 4.6


# ---------------------------------------------------------------- timeline
def timeline(vo_dir: str, upto: int | None = None):
    intro = B.vo_duration(os.path.join(vo_dir, "intro.mp3"))
    segs = [{"kind": "intro", "start": 0.0,
             "dur": INTRO_LEAD + max(intro, 5.0) + 0.8, "vo": intro,
             "vo_at": INTRO_LEAD}]
    t = segs[0]["dur"]
    entries = ENTRIES if not upto else ENTRIES[:upto]
    for i, (asset, name, role, count, _vo) in enumerate(entries):
        vo = B.vo_duration(os.path.join(vo_dir, f"{i + 1:02d}.mp3"))
        dur = LEAD + max(vo, 2.4) + TAIL
        segs.append({"kind": "beat", "start": t, "dur": dur, "vo": vo,
                     "vo_at": LEAD, "idx": i,
                     "entry": (asset, name, role, count)})
        t += dur
    end_vo = B.vo_duration(os.path.join(vo_dir, "end.mp3"))
    segs.append({"kind": "end", "start": t, "dur": max(ENDCARD, end_vo + 1.2),
                 "vo": end_vo, "vo_at": 0.35})
    t = segs[-1]["start"] + segs[-1]["dur"]
    return segs, t


def sfx(segs):
    """A tick on every cut, a heavier one on the opening and the close."""
    ev = [(0.0, "impact", 1.0)]
    for s in segs[1:]:
        ev.append((s["start"] + 0.01, "tick", 0.55))
        ev.append((s["start"] + s["vo_at"] - 0.05, "tick", 0.30))
    ev.append((segs[-1]["start"] + 0.02, "whoosh", 0.8))
    return ev


# ---------------------------------------------------------------- renderer
class CountdownRenderer:
    def __init__(self, entries, assets_dir):
        self.entries = entries
        self.n = len(entries)
        self.assets = assets_dir
        self.stage = Stage()
        self._local = 0.0

    def asset(self, key):
        p = os.path.join(self.assets, key + ".png")
        return p if os.path.exists(p) else None

    def beat(self, entry, idx, local, dur) -> Image.Image:
        key, name, role, count = entry
        p = C.clamp(local / max(0.1, dur))
        f = self.stage.frame()

        path = self.asset(key)
        if path:
            self._airframe(f, path, C.DIVIDER_X, BASE)

        z = 1.0 + 0.045 * (C.ease_in_out(p) if idx % 2 == 0 else 1.0 - C.ease_in_out(p))
        f = camera(f, z, cy=C.H * 0.52)
        self._chrome(f, idx, name, role, count, p)
        return f

    def _airframe(self, f, path, cx, baseline):
        spr = fit(path, BOX[0], BOX[1])
        x, y = int(cx - spr.width / 2), int(baseline - spr.height)
        halo, pad = _hook_halo(path, BOX[0], BOX[1])
        strength = 0.16 + 0.34 * _paleness(path)
        f.paste((150, 154, 160), (x - pad, y - pad),
                halo.point(lambda v: int(v * strength)))
        rgb, m = P.shadow(path, spr.height, spread=56, opacity=0.18)
        sw = int(spr.width * 1.14)
        sh = max(10, int(m.height * 0.12))
        m2 = m.resize((max(8, sw), sh), Image.BILINEAR).point(lambda v: int(v * 0.55))
        f.paste(rgb.getpixel((0, 0)), (int(cx - m2.width / 2),
                                      int(baseline - m2.height * 0.30)), m2)
        paste_rgba(f, spr, (x, y))

    def _chrome(self, f, idx, name, role, count, p):
        e = C.ramp(p, 0.0, 0.18, C.ease_out_expo)
        size = 208
        ny = 296 - (1 - e) * 24
        P.draw_text(f, (C.SAFE + 6, ny), f"{idx + 1:02d}", "black", size, C.INK,
                    tracking=-6, anchor="lt", alpha=e)
        P.draw_text(f, (C.SAFE + 12, ny + size + 2), f"{self.n:02d}", "bold", 34,
                    C.INK_FAINT, tracking=4, anchor="lt", alpha=e)
        d = ImageDraw.Draw(f, "RGBA")
        d.line([(C.SAFE, ny - 26), (C.SAFE + 150, ny - 26)],
               fill=JP_RED + (int(230 * e),), width=5)

        le = C.ramp(p, 0.05, 0.22, C.ease_out_expo)
        nsize = P.fit_size(name, "bold", 1040, 56, 4)
        ly = 842 - (1 - le) * 14
        P.draw_text(f, (C.DIVIDER_X, ly), name, "bold", nsize, C.INK, tracking=3,
                    anchor="mt", alpha=le)

        # role + count, as one dark pill and one light pill: the HIKKA pairing
        msize = 20
        gap = 12
        w1 = tw(role, "bold", msize, 5.0) + 44
        w2 = tw(count, "bold", msize, 5.0) + 44
        x = C.DIVIDER_X - (w1 + gap + w2) / 2
        y = ly + nsize + 16
        P.draw_pill(f, x, y, role, size=msize, fg=C.PAPER, bg=C.CHARCOAL,
                    tracking=5.0, pad_x=22, pad_y=11, alpha=le)
        P.draw_pill(f, x + w1 + gap, y, count, size=msize, fg=C.INK, bg=(232, 235, 239),
                    tracking=5.0, pad_x=22, pad_y=11, alpha=le)

        # progress ticks, one per entry
        tw_, gp = 34, 10
        span = self.n * tw_ + (self.n - 1) * gp
        x0 = C.DIVIDER_X - span / 2
        ty = 992
        for k in range(self.n):
            on = k <= idx
            col = C.CHARCOAL if k == idx else (JP_RED if on else (206, 211, 217))
            d.rectangle([x0 + k * (tw_ + gp), ty, x0 + k * (tw_ + gp) + tw_, ty + 6],
                        fill=col + (255 if on else 150,))

    def intro(self, local, dur) -> Image.Image:
        f = self.stage.frame()
        path = self.asset(ENTRIES[0][0])
        if path:
            self._airframe(f, path, C.DIVIDER_X, BASE + 40)
        f = camera(f, 1.0 + 0.04 * C.ease_in_out(C.clamp(local / max(0.1, dur))),
                   cy=C.H * 0.52)

        # headline sits above the aircraft, never on it
        e1 = C.ramp(local, 0.05, 0.55, C.ease_out_expo)
        P.draw_text(f, (C.DIVIDER_X, 96 - (1 - e1) * 26), "19 AIRCRAFT", "black", 132,
                    C.INK, tracking=-4, anchor="mt", alpha=e1)
        e2 = C.ramp(local, 0.26, 0.55, C.ease_out_expo)
        P.draw_text(f, (C.DIVIDER_X, 252 - (1 - e2) * 18), "JAPAN FLIES IN 2026", "bold",
                    46, C.INK_DIM, tracking=8, anchor="mt", alpha=e2)
        e3 = C.ramp(local, 0.46, 0.5)
        d = ImageDraw.Draw(f, "RGBA")
        w = 200 * e3
        d.line([(C.DIVIDER_X - w, 330), (C.DIVIDER_X + w, 330)],
               fill=JP_RED + (int(235 * e3),), width=5)
        return f

    def end(self, local, dur) -> Image.Image:
        f = self.stage.frame()
        e = C.ramp(local, 0.05, 0.6, C.ease_out_expo)
        P.draw_text(f, (C.DIVIDER_X, 400), "19 TYPES", "black", 150, C.INK,
                    tracking=-4, anchor="mt", alpha=e)
        P.draw_text(f, (C.DIVIDER_X, 570), "ONE FLEET   ·   ONE ISLAND NATION", "bold",
                    40, C.INK_DIM, tracking=8, anchor="mt", alpha=C.ramp(local, 0.4, 0.6))
        d = ImageDraw.Draw(f, "RGBA")
        w = 280 * C.ramp(local, 0.6, 0.6, C.ease_in_out)
        d.line([(C.DIVIDER_X - w, 680), (C.DIVIDER_X + w, 680)],
               fill=(140, 148, 158, 120), width=2)
        return f


# ---------------------------------------------------------------- audio
def mix(segs, total, vo_dir, out_path):
    n = int(total * A.SR) + A.SR
    bed = A.make_bed(total, bpm=76, root=54.0)
    mixbuf = np.zeros(n, dtype=np.float32)
    mixbuf[: len(bed)] += bed * 0.15

    voice = np.zeros(n, dtype=np.float32)
    for s in segs:
        if s["vo"] <= 0.5:
            continue
        key = "intro" if s["kind"] == "intro" else (
            "end" if s["kind"] == "end" else f"{s['idx'] + 1:02d}")
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
    music = (mixbuf * (1.0 - duck)).astype(np.float32)

    fx = np.zeros(n, dtype=np.float32)
    for at, kind, gain in sfx(segs):
        clip = A.sfx(kind)
        a = int(at * A.SR)
        b = min(n, a + len(clip))
        if b > a:
            fx[a:b] += clip[: b - a] * gain

    out = music + voice * 0.95 + fx
    out = np.tanh(out * 1.05) * 0.92
    A.write_wav(out_path, out)
    return out_path


# ---------------------------------------------------------------- main
def render(segs, total, out, w=C.W, h=C.H, fps=C.FPS, mix_path=None, upto=None):
    r = CountdownRenderer([e[:4] for e in (ENTRIES if not upto else ENTRIES[:upto])],
                          os.path.join(ROOT, "assets"))
    frames = int(total * fps)
    cmd = [B.FFMPEG, "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}", "-r", str(fps), "-i", "-",
           "-i", mix_path or os.path.join(ROOT, "build", "mix_cd.wav"),
           "-c:v", "libx264", "-preset", "fast", "-crf", "20", "-pix_fmt", "yuv420p",
           "-movflags", "+faststart", "-c:a", "aac", "-b:a", "192k", "-shortest", out]
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
        if f.size != (w, h):
            f = f.resize((w, h), Image.LANCZOS)
        proc.stdin.write(np.asarray(f, dtype=np.uint8).tobytes())
        if k % 30 == 0:
            el = time.time() - t0
            print(f"\r  frame {k}/{frames}  {el:5.1f}s  ({(k+1)/max(el,0.001):4.1f} fps)",
                  end="", flush=True)
    proc.stdin.close()
    proc.wait()
    print(f"\n  wrote {out} in {time.time()-t0:.0f}s")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vo", default=os.path.join(ROOT, "audio", "vo_cd"))
    ap.add_argument("--out", default=os.path.join(ROOT, "deliverables", "hikka_japan_19_aircraft.mp4"))
    ap.add_argument("--draft", action="store_true")
    ap.add_argument("--audio-only", action="store_true")
    ap.add_argument("--still", type=float, default=None)
    ap.add_argument("--upto", type=int, default=0,
                    help="render only the first N entries (for VO proofs)")
    args = ap.parse_args()

    segs, total = timeline(args.vo, args.upto or None)
    os.makedirs(os.path.join(ROOT, "build"), exist_ok=True)
    print(f"  {len(segs)} segments, {total/60:.2f} min")

    if args.still is not None:
        r = CountdownRenderer([e[:4] for e in ENTRIES], os.path.join(ROOT, "assets"))
        t = args.still
        s = next(x for x in segs if x["start"] <= t < x["start"] + x["dur"])
        local = t - s["start"]
        f = (r.intro(local, s["dur"]) if s["kind"] == "intro"
             else r.end(local, s["dur"]) if s["kind"] == "end"
             else r.beat(s["entry"], s["idx"], local, s["dur"]))
        out = os.path.join(ROOT, "build", "cd_still.png")
        f.save(out)
        print("  ", out)
        return

    mix_path = os.path.join(ROOT, "build", "mix_cd.wav")
    mix(segs, total, args.vo, mix_path)
    print("  audio mixed")

    cues = []
    for s in segs:
        if s["kind"] == "intro":
            text = INTRO_VO
        elif s["kind"] == "end":
            text = END_VO
        else:
            i = s["idx"]
            text = ENTRIES[i][4] if i < len(ENTRIES) else ""
        cues.append({"kind": "intro" if s["kind"] == "intro" else "section",
                     "start": s["start"], "dur": s["dur"], "vo": s["vo"],
                     "vo_at": s["vo_at"], "section": {"narration": text}})
    subs.export(cues, os.path.join(ROOT, "deliverables"), INTRO_VO, "",
                stem="hikka_japan_19_aircraft")
    print("  subs ->", "hikka_japan_19_aircraft.en.srt")

    if not args.audio_only:
        w, h = (960, 540) if args.draft else (C.W, C.H)
        render(segs, total, args.out, w=w, h=h, mix_path=mix_path, upto=args.upto or None)


if __name__ == "__main__":
    main()
