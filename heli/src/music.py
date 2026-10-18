# -*- coding: utf-8 -*-
"""
Original score + documentary SFX + final loudness-normalised mix (-14 LUFS) -> build/final_audio.m4a.
  python3 music.py [mystery|doc]
"""
import os, sys, math, subprocess
import numpy as np
from scipy import signal
import imageio_ffmpeg

from common import BUILD
from storyboard import build_shots
from check_timing import element_times
import score

FF = imageio_ffmpeg.get_ffmpeg_exe()
SR = 48000
STYLE = "mystery"


def lowpass(x, fc, order=2):
    b, a = signal.butter(order, fc / (SR / 2), btype="low")
    return signal.lfilter(b, a, x).astype(np.float32)


def bandpass(x, f1, f2, order=2):
    b, a = signal.butter(order, [f1 / (SR / 2), f2 / (SR / 2)], btype="band")
    return signal.lfilter(b, a, x).astype(np.float32)


def whoosh(L=0.48):
    rng = np.random.default_rng(7)
    n = int(L * SR)
    t = np.linspace(0, 1, n, dtype=np.float32)
    env = np.sin(np.pi * t) ** 1.8
    w = rng.normal(0, 1, n).astype(np.float32)
    return (bandpass(w, 180, 900) * (1 - t) + bandpass(w, 500, 2600) * t) * env * 0.22


def flash_hit(L=0.35):
    rng = np.random.default_rng(13)
    n = int(L * SR)
    t = np.arange(n, dtype=np.float32) / SR
    click = bandpass(rng.normal(0, 1, n).astype(np.float32), 900, 5000) * np.exp(-t * 45)
    thud = np.sin(2 * np.pi * (140 * np.exp(-t * 14) + 48) * t) * np.exp(-t * 9)
    return (click * 0.25 + thud * 0.45).astype(np.float32)


def stamp_thud(L=0.45):
    rng = np.random.default_rng(19)
    n = int(L * SR)
    t = np.arange(n, dtype=np.float32) / SR
    sub = np.sin(2 * np.pi * (110 * np.exp(-t * 12) + 42) * t) * np.exp(-t * 7)
    snap = bandpass(rng.normal(0, 1, n).astype(np.float32), 300, 2400) * np.exp(-t * 32)
    return (sub * 0.55 + snap * 0.22).astype(np.float32)


def pop():
    n = int(0.065 * SR)
    t = np.arange(n, dtype=np.float32) / SR
    f = 680 * np.exp(-t * 20) + 220
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 45) * 0.16).astype(np.float32)


def riser(L=1.8):
    rng = np.random.default_rng(11)
    n = int(L * SR)
    t = np.linspace(0, 1, n, dtype=np.float32)
    f = 90 * (6.5 ** t)
    ph = 2 * np.pi * np.cumsum(f) / SR
    tone = np.sin(ph) * 0.4 + np.sin(2 * ph) * 0.2
    w = bandpass(rng.normal(0, 1, n).astype(np.float32), 300, 3800) * (t ** 2) * 0.35
    return ((tone + w) * (t ** 2.2) * 0.32).astype(np.float32)


def impact(L=2.4):
    rng = np.random.default_rng(23)
    n = int(L * SR)
    t = np.arange(n, dtype=np.float32) / SR
    f = 120 * np.exp(-t * 9) + 36
    sub = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 2.2)
    thump = bandpass(rng.normal(0, 1, n).astype(np.float32), 50, 240) * np.exp(-t * 15) * 0.7
    tail = lowpass(rng.normal(0, 1, n).astype(np.float32), 650) * np.exp(-t * 3.0) * 0.16
    return np.tanh((sub + thump + tail) * 1.3).astype(np.float32) * 0.55


def heli_pass(L=12.0, bpf=19.2, pan0=-0.6, pan1=0.6):
    """Synthesised helicopter rotor pass-by (blade-vortex slap + low rotor thump + faint turbine)."""
    rng = np.random.default_rng(31)
    n = int(L * SR)
    t = np.arange(n, dtype=np.float32) / SR
    u = t / L
    # Doppler pitch shift as it passes
    dop = 1.0 + 0.08 * np.tanh((0.5 - u) * 5.0)
    ph = np.cumsum(bpf * dop) / SR
    pulse = np.maximum(0.0, np.sin(2 * np.pi * ph)) ** 5
    slap = bandpass(rng.normal(0, 1, n).astype(np.float32), 90, 650) * pulse * 0.55
    thump = np.sin(2 * np.pi * ph) * 0.28 + np.sin(4 * np.pi * ph) * 0.16
    turb = np.sin(2 * np.pi * np.cumsum(980 * dop) / SR) * 0.025
    env = np.sin(np.pi * u) ** 1.4
    mono = lowpass((slap + thump + turb) * env, 1200) * 0.22
    pan = 0.5 + 0.5 * np.linspace(pan0, pan1, n, dtype=np.float32)
    return np.stack([mono * (1 - pan), mono * pan], axis=1).astype(np.float32)


def write_wav(path, x, ch=2):
    pcm = (np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes()
    p = subprocess.Popen([FF, "-y", "-v", "error", "-f", "s16le", "-ar", str(SR), "-ac", str(ch),
                          "-i", "-", path], stdin=subprocess.PIPE)
    p.communicate(pcm)


def make_sfx(specs, tl, n):
    secs = {s["id"]: s for s in tl["sections"]}
    title_at = secs["intro"]["title_at"]
    sfx = np.zeros((n, 2), np.float32)
    W_ = whoosh()
    F_ = flash_hit()
    S_ = stamp_thud()
    P_ = pop()

    def put_stereo(x2, t, g=1.0):
        i0 = int(t * SR)
        if 0 <= i0 < n:
            k = min(len(x2), n - i0)
            sfx[i0:i0 + k] += x2[:k] * g

    def put_mono(x1, t, g=1.0, pan=0.5):
        i0 = int(t * SR)
        if 0 <= i0 < n:
            k = min(len(x1), n - i0)
            sfx[i0:i0 + k, 0] += x1[:k] * g * (1 - pan)
            sfx[i0:i0 + k, 1] += x1[:k] * g * pan

    # subtle rotor pass-bys in the cold open, record run, and Chinook intro
    put_stereo(heli_pass(14.5, 19.4, -0.5, 0.5), 0.8, 0.55)
    put_stereo(heli_pass(10.0, 15.0, 0.4, -0.4), secs["chinook"]["start"] + 2.0, 0.40)
    put_stereo(heli_pass(11.0, 19.6, -0.6, 0.6), secs["record"]["start"] + 4.0, 0.50)

    # section transitions & flash cuts
    first = {}
    for s in specs:
        first.setdefault(s["section"], s["start"])
    for sid, st in first.items():
        if sid == "intro":
            continue
        put_mono(W_, st - 0.24, 0.50, 0.5)
    for s in specs:
        if s.get("trans") == "flash" or s["type"] == "answer":
            put_mono(F_, s["start"], 0.55, 0.5)

    # element pops & stamp thuds
    for s in specs:
        for kind, _, tt in element_times(s):
            if kind == "stamp":
                put_mono(S_, tt, 0.50, 0.5)
            elif kind in ("chip", "callout", "item", "card", "marker", "label"):
                put_mono(P_, tt, 0.22, 0.5)

    R = riser()
    I = impact()
    put_mono(R, title_at - len(R) / SR + 0.05, 0.45)
    put_mono(I, title_at + 0.02, 0.85)
    return sfx


MIX = (
    "[0:a]aresample=48000,pan=stereo|c0=c0|c1=c0,highpass=f=70,"
    "acompressor=threshold=-20dB:ratio=3:attack=8:release=120:makeup=2,asplit=2[v][vsc];"
    "[1:a]volume=0.52[m];"
    "[m][vsc]sidechaincompress=threshold=0.03:ratio=8:attack=40:release=450:makeup=1[md];"
    "[2:a]volume=0.88[s];"
    "[v][md][s]amix=inputs=3:duration=first:normalize=0,"
    "loudnorm=I=-14:TP=-1.5:LRA=11[out]"
)


def mix(narr, music, sfx, out, t1=None, codec=("-c:a", "aac", "-b:a", "160k")):
    cut = ["-t", f"{t1:.3f}"] if t1 else []
    subprocess.run([FF, "-y", "-v", "error", *cut, "-i", narr, *cut, "-i", music, *cut, "-i", sfx,
                    "-filter_complex", MIX, "-map", "[out]", "-ar", "48000", *codec, out], check=True)


def main(style=STYLE):
    specs, tl = build_shots()
    dur = tl["duration"]
    n = int((dur + 3) * SR)
    print(f"music ({style})...", flush=True)
    mus = score.render(style, tl)[:n]
    write_wav(os.path.join(BUILD, "music.wav"), mus.reshape(-1), ch=2)
    del mus
    print("sfx...", flush=True)
    write_wav(os.path.join(BUILD, "sfx.wav"), make_sfx(specs, tl, n).reshape(-1), ch=2)
    print("mix...", flush=True)
    out = os.path.join(BUILD, "final_audio.m4a")
    mix(os.path.join(BUILD, "narration.wav"), os.path.join(BUILD, "music.wav"), os.path.join(BUILD, "sfx.wav"), out)
    print("audio ready:", out, flush=True)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else STYLE)
