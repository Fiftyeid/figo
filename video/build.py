#!/usr/bin/env python3
"""Render the film.

    python3 video/build.py                       # full 1080p30 render
    python3 video/build.py --draft               # fast 960x540 proof
    python3 video/build.py --only 01,09,18       # render a few chapters

Narration clips (audio/vo/<id>.mp3) drive the timing: every chapter is
held open for exactly as long as its voiceover takes, so the visuals never
run ahead of the voice.  No narration file?  The `nominal` duration in
content.py is used instead.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from engine import audio  # noqa: E402
from engine import config as C  # noqa: E402
from engine import subs  # noqa: E402
from engine.content import INTRO_NARRATION, INTRO_NARRATION_AR, SECTIONS  # noqa: E402
from engine.scenes import Renderer  # noqa: E402

ROOT = os.path.dirname(HERE)


def _ffmpeg_bin():
    for p in (
        os.path.join(ROOT, "tools", "node_modules", "@ffmpeg-installer", "linux-x64", "ffmpeg"),
        "/usr/bin/ffmpeg",
        "/usr/local/bin/ffmpeg",
        _imageio_ffmpeg(),
    ):
        if os.path.exists(p):
            return p
    return "ffmpeg"


def _imageio_ffmpeg():
    """Last resort: the binary bundled with the imageio-ffmpeg wheel."""
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return ""


FFMPEG = os.environ.get("FFMPEG_BIN") or _ffmpeg_bin()

# pacing: the hook starts almost instantly, chapters cut on the voice
INTRO_LEAD = 0.2    # narration starts here (was 1.3 -- dead air kills retention)
INTRO_TAIL = 0.9
LEAD_IN = 0.35      # beat between the cut and the voice (was 1.05)
TAIL_OUT = 0.45     # beat after the voice before the next cut (was 1.45)

HOOK_HOLD = 0.55    # the last cold-open card rests for this long before the cut


def hook_timing(dur: float, count: int) -> dict:
    """Geometry of the cold open: one card per slot, then a short hold."""
    count = max(1, int(count))
    slot = max(0.06, (dur - HOOK_HOLD) / count)
    return {"dur": dur, "count": count, "slot": slot, "hold": HOOK_HOLD}


# ---------------------------------------------------------------- timing
def vo_duration(path: str) -> float:
    """Decode the clip to mono 44.1k wav (cached) and measure it."""
    if not os.path.exists(path):
        return 0.0
    cache = os.path.join(ROOT, "build", "vo_cache", os.path.basename(path) + ".wav")
    os.makedirs(os.path.dirname(cache), exist_ok=True)
    if not os.path.exists(cache):
        subprocess.run(
            [FFMPEG, "-y", "-loglevel", "error", "-i", path, "-ac", "1", "-ar", str(audio.SR), cache],
            check=True,
        )
    return len(audio.read_wav(cache)) / audio.SR


def build_timeline(vo_dir: str, only=None, sections=None, hook=None):
    """`hook` = {"dur": seconds, "count": n} prepends a silent cold open."""
    sections = SECTIONS if sections is None else sections
    segs = []
    t = 0.0
    sections = [s for s in sections if not only or s["id"] in only]

    if hook:
        cfg = hook_timing(float(hook.get("dur", 5.1)),
                          hook.get("count") or sum(len(s.get("items") or []) for s in sections))
        segs.append({"kind": "hook", "start": 0.0, "dur": cfg["dur"], "vo": 0.0,
                     "vo_at": 0.0, "hook": cfg})
        t = cfg["dur"]

    intro_vo = os.path.join(vo_dir, "intro.mp3")
    intro_len = vo_duration(intro_vo)
    dur = INTRO_LEAD + max(intro_len, 8.0) + INTRO_TAIL
    segs.append({"kind": "intro", "start": t, "dur": dur, "vo": intro_len,
                 "vo_at": INTRO_LEAD})
    t += dur

    for sec in sections:
        vo = vo_duration(os.path.join(vo_dir, sec["id"] + ".mp3"))
        body = vo if vo > 0.5 else float(sec.get("nominal", 12.0))
        dur = LEAD_IN + body + TAIL_OUT
        segs.append({"kind": "section", "start": t, "dur": dur, "section": sec,
                     "vo": vo, "vo_at": LEAD_IN})
        t += dur

    segs.append({"kind": "endcard", "start": t, "dur": 5.2, "vo": 0.0, "vo_at": 0})
    t += 5.2
    return segs, t


# ---------------------------------------------------------------- audio
def sfx_events(segs):
    """(time, kind, gain) for clicks, whooshes and the opening impact."""
    ev = [(0.0, "impact", 1.0)]
    for seg in segs:
        if seg["kind"] == "hook":
            cfg = seg.get("hook") or {}
            slot = float(cfg.get("slot") or 0.0)
            for i in range(1, int(cfg.get("count") or 0)):   # card 0 is already flat
                if slot > 0:
                    ev.append((seg["start"] + i * slot + 0.06, "tick", 0.5))
        if seg["kind"] != "section":
            continue
        t0 = seg["start"]
        ev.append((t0 + 0.02, "whoosh", 0.85))
        ev.append((t0 + LEAD_IN - 0.06, "tick", 0.9))
        for i, dt in enumerate((1.5, 4.0, 6.5)):
            if dt < seg["dur"] - 0.4:
                ev.append((t0 + max(dt, seg["vo_at"]), "tick", 0.6 - 0.08 * i))
    for seg in segs:
        if seg["kind"] == "endcard":
            ev.append((seg["start"] + 0.05, "whoosh", 0.7))
    return ev


def prepare_broll(sections):
    """Extract 30 fps png frames for any section that references a clip."""
    import shutil

    made = []
    for sec in sections:
        br = sec.get("broll")
        if not br:
            continue
        clip = br["clip"]
        src = os.path.join(ROOT, "broll", clip + ".mp4")
        dst = os.path.join(ROOT, "build", "broll", clip)
        if not os.path.exists(src):
            print(f"  broll: no clip for '{clip}' -> studio scene will be used")
            continue
        os.makedirs(dst, exist_ok=True)
        if os.path.exists(os.path.join(dst, "00000.png")):
            made.append(clip)
            continue
        # scale + crop to 1920x1080, 30 fps, ~4 s max
        vf = ("scale=1920:1080:force_original_aspect_ratio=increase,"
              "crop=1920:1080,setsar=1")
        subprocess.run(
            [FFMPEG, "-y", "-loglevel", "error", "-i", src, "-t", "4.5",
             "-vf", vf, "-r", "30", os.path.join(dst, "%05d.png")], check=True)
        made.append(clip)
    return made


def mix_audio(segs, total, vo_dir, out_path):
    n = int(total * audio.SR) + audio.SR
    bed = audio.make_bed(total, bpm=70, root=52.0)
    mix = np.zeros(n, dtype=np.float32)
    mix[: len(bed)] += bed * 0.16          # quiet score

    voice = np.zeros(n, dtype=np.float32)
    for seg in segs:
        if seg["vo"] <= 0.5:
            continue
        key = "intro" if seg["kind"] == "intro" else seg["section"]["id"]
        wav = os.path.join(ROOT, "build", "vo_cache", key + ".mp3.wav")
        if not os.path.exists(wav):
            continue
        clip = audio.read_wav(wav)
        # gentle levelling so every chapter sits at the same loudness
        rms = float(np.sqrt(np.mean(clip ** 2))) or 1.0
        clip = clip * min(2.2, 0.11 / rms)
        s = int((seg["start"] + seg["vo_at"]) * audio.SR)
        e = min(n, s + len(clip))
        voice[s:e] += clip[: e - s]

    # side-chain style ducking of the score under the narration
    env = np.abs(voice)
    k = np.ones(int(0.20 * audio.SR)) / int(0.20 * audio.SR)
    env = np.convolve(env, k, mode="same")
    duck = np.clip(env / 0.06, 0, 1) * 0.72
    music = (mix * (1.0 - duck)).astype(np.float32)
    # transition / UI sound design
    mix_sfx = np.zeros(n, dtype=np.float32)
    for at, kind, gain in sfx_events(segs):
        clip = audio.sfx(kind)
        a = int(at * audio.SR)
        b = min(n, a + len(clip))
        if b > a:
            mix_sfx[a:b] += clip[: b - a] * gain
    out = music + voice * 0.95 + mix_sfx
    # 8 ms limiter
    out = np.tanh(out * 1.05) * 0.92
    audio.write_wav(out_path, out)
    return out_path


# ---------------------------------------------------------------- render
def render(segs, total, assets, out_path, w=C.W, h=C.H, fps=C.FPS, only=None,
           sections=None, renderer_cls=None, intro_narration=None, mix_path=None):
    all_sections = SECTIONS if sections is None else sections
    sections = [s for s in all_sections if not only or s["id"] in only]
    r = (renderer_cls or Renderer)(sections, intro_narration or INTRO_NARRATION,
                                   assets, segs, total)
    frames = int(total * fps)
    cmd = [
        FFMPEG, "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}", "-r", str(fps), "-i", "-",
        "-i", mix_path or os.path.join(ROOT, "build", "mix.wav"),
        "-c:v", "libx264", "-preset", "fast", "-crf", "20", "-pix_fmt", "yuv420p",
        "-movflags", "+faststart", "-c:a", "aac", "-b:a", "192k", "-shortest", out_path,
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    t0 = time.time()
    idx = 0
    for f in range(frames):
        t = f / fps
        while idx + 1 < len(segs) and t >= segs[idx]["start"] + segs[idx]["dur"]:
            idx += 1
        seg = segs[idx]
        local = t - seg["start"]
        r._global_t = t
        r._seg_dur = seg["dur"]
        frame = r.stage.frame()
        if seg["kind"] == "hook":
            r._hook_cfg = seg.get("hook")
            frame = r.draw_hook(frame, local, seg["dur"]) or frame
        elif seg["kind"] == "intro":
            frame = r.draw_intro(frame, local, seg["dur"]) or frame
        elif seg["kind"] == "endcard":
            r.draw_endcard(frame, local)
        else:
            s_idx = sections.index(seg["section"]) + 1
            frame = r.draw_section(frame, seg["section"], local, s_idx) or frame
        if frame.size != (w, h):
            frame = frame.resize((w, h), Image.LANCZOS)
        proc.stdin.write(np.asarray(frame, dtype=np.uint8).tobytes())
        if f % fps == 0:
            el = time.time() - t0
            print(f"\r  frame {f}/{frames}  {el:5.1f}s  ({(f+1)/max(el,0.001):4.1f} fps)",
                  end="", flush=True)
    proc.stdin.close()
    proc.wait()
    print(f"\n  wrote {out_path}  in {time.time()-t0:.0f}s")


def poster(segs, total, assets, which, out_path, sections=None,
           renderer_cls=None, intro_narration=None):
    """One still frame, for thumbnails / previews."""
    all_sections = SECTIONS if sections is None else sections
    r = (renderer_cls or Renderer)(all_sections, intro_narration or INTRO_NARRATION,
                                   assets, segs, total)
    f = r.stage.frame()
    if which.startswith("hook"):
        seg = next((s for s in segs if s["kind"] == "hook"), None)
        if seg:
            at = float(which.split(":")[1]) if ":" in which else 1.4
            r._hook_cfg = seg.get("hook")
            r._global_t = at
            f = r.draw_hook(f, at, seg["dur"]) or f
    elif which == "intro":
        r._global_t = 8.0
        f = r.draw_intro(f, 8.0, 20) or f
    elif which == "end":
        r.draw_endcard(f, 3.0)
    else:
        sec = next(s for s in all_sections if s["id"] == which)
        seg = next(s for s in segs
                   if s.get("section") and s["section"]["id"] == sec["id"])
        r._global_t = seg["start"] + 5
        r._seg_dur = seg["dur"]
        f = r.draw_section(f, sec, 6.0, all_sections.index(sec) + 1) or f
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    f.save(out_path)
    print("  poster ->", out_path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vo", default=os.path.join(ROOT, "audio", "vo"))
    ap.add_argument("--assets", default=os.path.join(ROOT, "assets"))
    ap.add_argument("--out", default=os.path.join(ROOT, "deliverables", "hikka_gear_usa_vs_china.mp4"))
    ap.add_argument("--only", default="")
    ap.add_argument("--audio-only", action="store_true")
    ap.add_argument("--poster", default="", help="render one still: intro | 18 | end")
    ap.add_argument("--no-subs", action="store_true", help="skip .srt export")
    args = ap.parse_args()

    only = set(x.strip() for x in args.only.split(",") if x.strip())
    segs, total = build_timeline(args.vo, only or None)
    os.makedirs(os.path.join(ROOT, "build"), exist_ok=True)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    print(f"  timeline: {len(segs)} segments, {total/60:.1f} min")
    prepare_broll(SECTIONS)
    mix_audio(segs, total, args.vo, os.path.join(ROOT, "build", "mix.wav"))
    print("  audio mixed")
    if not args.no_subs:
        for made in subs.export(segs, os.path.join(ROOT, "deliverables"),
                                INTRO_NARRATION, INTRO_NARRATION_AR):
            print("  subs ->", made)
    if args.poster:
        poster(segs, total, args.assets, args.poster, os.path.join(ROOT, "deliverables", "poster.png"))
    if not args.audio_only:
        render(segs, total, args.assets, args.out, only=only or None)


if __name__ == "__main__":
    main()
