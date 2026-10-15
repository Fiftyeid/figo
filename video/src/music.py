# -*- coding: utf-8 -*-
"""
Background score + sound effects, then the final audio mix.
  - score: original, synthesised from scratch in score.py (style = STYLE below, see score.STYLES)
  - SFX: whooshes on section changes, soft pops on card elements, riser + impact for the title
Output: build/music.wav, build/sfx.wav, build/final_audio.m4a

    python3 music.py [style]       full mix (default STYLE)
    python3 music.py audition      first ~37 s mixed with every style -> build/audition/<style>.wav
"""
import os, json, math, subprocess
import numpy as np
from scipy import signal
import imageio_ffmpeg

from common import BUILD
from storyboard import build_shots
from shots import SHOT_TYPES

import score

FF = imageio_ffmpeg.get_ffmpeg_exe()
SR = 48000
STYLE = "doc"
rng = np.random.default_rng(2026)


def lowpass(x, fc, order=2):
    b, a = signal.butter(order, fc / (SR / 2), "low")
    return signal.lfilter(b, a, x)


def bandpass(x, f1, f2, order=2):
    b, a = signal.butter(order, [f1 / (SR / 2), f2 / (SR / 2)], "band")
    return signal.lfilter(b, a, x)


# ------------------------------------------------------------------ SFX
def whoosh(L=0.55):
    n = int(L * SR)
    t = np.arange(n) / SR
    noise = rng.uniform(-1, 1, n)
    out = np.zeros(n)
    # sweep a band-pass by blocks
    blocks = 24
    bs = n // blocks
    for i in range(blocks):
        f = 300 * (12 ** (i / blocks))
        seg = noise[i * bs:(i + 1) * bs]
        out[i * bs:(i + 1) * bs] = bandpass(seg, f * 0.7, min(f * 1.4, SR / 2 - 100))
    env = np.sin(np.pi * np.clip(t / L, 0, 1)) ** 2
    out = lowpass(out * env, 7000)
    return (out / (np.abs(out).max() + 1e-6)).astype(np.float32)


def pop():
    n = int(0.09 * SR)
    t = np.arange(n) / SR
    f = 520 + 600 * (t / 0.09)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.025)
    return x.astype(np.float32)


def riser(L=1.6):
    n = int(L * SR)
    t = np.arange(n) / SR
    noise = lowpass(rng.uniform(-1, 1, n), 4000)
    f = 200 + 900 * (t / L) ** 2
    tone = np.sin(2 * np.pi * np.cumsum(f) / SR)
    env = (t / L) ** 2.2
    x = (0.6 * noise + 0.4 * tone) * env
    return (x / np.abs(x).max()).astype(np.float32)


def impact(L=2.2):
    n = int(L * SR)
    t = np.arange(n) / SR
    f = 70 * np.exp(-t / 0.25) + 38
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.7)
    x += 0.35 * lowpass(rng.uniform(-1, 1, n), 2500) * np.exp(-t / 0.12)
    return (x / np.abs(x).max()).astype(np.float32)


def write_wav(path, x, ch=1):
    x = np.clip(x, -1, 1)
    pcm = (x * 32767).astype(np.int16)
    p = subprocess.Popen([FF, "-y", "-v", "error", "-f", "s16le", "-ar", str(SR), "-ac", str(ch), "-i", "-", path],
                         stdin=subprocess.PIPE)
    p.communicate(pcm.tobytes())


def card_times(spec):
    sp = dict(spec)
    typ = sp.pop("type")
    sp.pop("section", None)
    st, en = sp.pop("start"), sp.pop("end")
    sh = SHOT_TYPES[typ](st, en, **sp)
    if typ == "chain":
        ts = sh.times(len(spec["items"]))
    elif typ == "list":
        ts = sh.times(len(spec["items"]), step=1.2)
    elif typ == "myth":
        ts = sh.times(2, step=1.5)
    elif typ == "ledger":
        ts = sh.times(3, step=1.3)
    else:
        ts = []
    # only elements that actually pop in while this card is on screen
    # (items carried over from an earlier card, or timed after the cut, stay silent)
    return [x for x in ts if st <= x < en - 0.1]


def make_sfx(specs, tl, n):
    secs = {s["id"]: s for s in tl["sections"]}
    title_at = secs["intro"]["title_at"]
    sfx = np.zeros((n, 2), np.float32)
    W_ = whoosh()
    P_ = pop()
    first = {}
    for s in specs:
        first.setdefault(s["section"], s["start"])
    for sid, st in first.items():
        if sid == "intro":
            continue
        i0 = int((st - 0.28) * SR)
        L = len(W_)
        if i0 < 0 or i0 + L >= n:
            continue
        pan = np.linspace(0.2, 0.8, L)
        sfx[i0:i0 + L, 0] += W_ * (1 - pan) * 0.55
        sfx[i0:i0 + L, 1] += W_ * pan * 0.55
    for s in specs:
        if s["type"] in ("chain", "list", "myth", "ledger"):
            for tt_ in card_times(s):
                i0 = int(tt_ * SR)
                if 0 <= i0 < n - len(P_):
                    sfx[i0:i0 + len(P_), :] += P_[:, None] * 0.16

    def put(x, t, g):
        i0 = int(t * SR)
        if 0 <= i0 < n:
            k = min(len(x), n - i0)
            sfx[i0:i0 + k, :] += x[:k, None] * g
    R = riser()
    put(R, title_at - len(R) / SR + 0.05, 0.35)
    I = impact()
    put(I, title_at + 0.05, 0.8)
    last_title = [s for s in specs if s["type"] == "title"][-1]["start"]   # small impact on the final card
    put(I, last_title + 0.05, 0.45)
    return sfx


MIX = (
    "[0:a]aresample=48000,pan=stereo|c0=c0|c1=c0,highpass=f=70,"
    "acompressor=threshold=-20dB:ratio=3:attack=8:release=120:makeup=2,asplit=2[v][vsc];"
    "[1:a]volume=0.55[m];"
    "[m][vsc]sidechaincompress=threshold=0.03:ratio=8:attack=40:release=450:makeup=1[md];"
    "[2:a]volume=0.9[s];"
    "[v][md][s]amix=inputs=3:duration=first:normalize=0,"
    "loudnorm=I=-14:TP=-1.5:LRA=11[out]"
)


def mix(narr, music, sfx, out, t1=None, codec=("-c:a", "aac", "-b:a", "128k")):
    cut = ["-t", f"{t1:.3f}"] if t1 else []
    subprocess.run([FF, "-y", "-v", "error", *cut, "-i", narr, *cut, "-i", music, *cut, "-i", sfx,
                    "-filter_complex", MIX, "-map", "[out]", "-ar", "48000", *codec, out], check=True)


def main(style=STYLE):
    specs, tl = build_shots()
    dur = tl["duration"]
    n = int((dur + 3) * SR)
    print(f"music ({style})...", flush=True)
    music = score.render(style, tl)[:n]
    write_wav(os.path.join(BUILD, "music.wav"), music.reshape(-1), ch=2)
    del music
    print("sfx...", flush=True)
    write_wav(os.path.join(BUILD, "sfx.wav"), make_sfx(specs, tl, n).reshape(-1), ch=2)
    print("mix...", flush=True)
    out = os.path.join(BUILD, "final_audio.m4a")
    mix(os.path.join(BUILD, "narration.wav"), os.path.join(BUILD, "music.wav"), os.path.join(BUILD, "sfx.wav"), out)
    print("audio ready:", out)


def audition(t1=37.0):
    specs, tl = build_shots()
    d = os.path.join(BUILD, "audition")
    os.makedirs(d, exist_ok=True)
    n = int(t1 * SR)
    sfx_p = os.path.join(d, "sfx.wav")
    write_wav(sfx_p, make_sfx(specs, tl, n).reshape(-1), ch=2)
    for st in score.STYLES:
        m = score.render(st, tl, t1=t1)
        mp = os.path.join(d, f"music_{st}.wav")
        write_wav(mp, m.reshape(-1), ch=2)
        mix(os.path.join(BUILD, "narration.wav"), mp, sfx_p, os.path.join(d, f"{st}.wav"), t1=t1,
            codec=("-c:a", "pcm_s16le"))
        print("audition:", st, flush=True)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "audition":
        audition()
    else:
        main(sys.argv[1] if len(sys.argv) > 1 else STYLE)
