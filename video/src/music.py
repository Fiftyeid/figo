# -*- coding: utf-8 -*-
"""
Procedural, original background score + sound effects, then final audio mix.
  - pad: Andalusian cadence Dm - C - Bb - A (D harmonic-minor colour)
  - plucked "oud-like" arpeggios (Karplus-Strong)
  - soft darbuka-style "maqsum" rhythm (dum / tek)
  - SFX: whooshes on section changes, soft pops on card elements, riser + impact for the title
Output: build/music.wav, build/sfx.wav, build/final_audio.m4a
"""
import os, json, math, subprocess
import numpy as np
from scipy import signal
import imageio_ffmpeg

from common import BUILD
from storyboard import build_shots
from shots import SHOT_TYPES

FF = imageio_ffmpeg.get_ffmpeg_exe()
SR = 48000
BPM = 88.0
BEAT = 60.0 / BPM
BAR = 4 * BEAT
rng = np.random.default_rng(2026)


def midi(n):
    return 440.0 * 2 ** ((n - 69) / 12.0)


# chord tones (MIDI) – D3=50
CHORDS = [
    ("Dm", [50, 53, 57, 62]),
    ("C", [48, 52, 55, 60]),
    ("Bb", [46, 50, 53, 58]),
    ("A", [45, 49, 52, 57]),
]
SCALE = [62, 64, 65, 67, 69, 70, 73, 74, 76, 77]   # D harmonic minor (upper)


def lowpass(x, fc, order=2):
    b, a = signal.butter(order, fc / (SR / 2), "low")
    return signal.lfilter(b, a, x)


def bandpass(x, f1, f2, order=2):
    b, a = signal.butter(order, [f1 / (SR / 2), f2 / (SR / 2)], "band")
    return signal.lfilter(b, a, x)


def saw(freq, n, phase0=0.0):
    t = np.arange(n) / SR
    ph = (freq * t + phase0) % 1.0
    return 2 * ph - 1


def pad_track(dur):
    n = int(dur * SR)
    out = np.zeros(n, np.float32)
    seg = 2 * BAR
    k = 0
    t0 = 0.0
    while t0 < dur:
        name, notes = CHORDS[k % 4]
        L = int((seg + 1.6) * SR)
        x = np.zeros(L, np.float32)
        for m in notes:
            f = midi(m)
            for det in (-0.08, 0.0, 0.07):
                x += saw(f * 2 ** (det / 12), L, rng.random()).astype(np.float32) * 0.18
        x = lowpass(x, 900).astype(np.float32)
        env = np.ones(L, np.float32)
        a, r = int(0.9 * SR), int(1.6 * SR)
        env[:a] = np.linspace(0, 1, a) ** 1.5
        env[-r:] = np.linspace(1, 0, r) ** 1.5
        x *= env
        i0 = int(t0 * SR)
        i1 = min(n, i0 + L)
        out[i0:i1] += x[: i1 - i0]
        t0 += seg
        k += 1
    return out


def ks_pluck(freq, dur=1.6, bright=0.5):
    n = int(dur * SR)
    N = max(2, int(SR / freq))
    y = np.zeros(n + N + 2, np.float32)
    burst = rng.uniform(-1, 1, N).astype(np.float32)
    burst = lowpass(burst, 1500 + 3500 * bright).astype(np.float32)
    y[:N] = burst
    decay = 0.996
    y[N] = decay * 0.5 * (y[0] + y[N - 1])
    b = N + 1
    while b < len(y):
        e = min(len(y), b + N)
        y[b:e] = decay * 0.5 * (y[b - N:e - N] + y[b - N - 1:e - N - 1])
        b = e
    y = y[:n]
    y *= np.exp(-np.arange(n) / (SR * 0.9))
    return y / (np.abs(y).max() + 1e-6)


_pl = {}


def pluck(m):
    if m not in _pl:
        _pl[m] = ks_pluck(midi(m), bright=0.45)
    return _pl[m]


def add(out, x, t, gain):
    i0 = int(t * SR)
    if i0 >= len(out) or i0 < 0:
        return
    i1 = min(len(out), i0 + len(x))
    out[i0:i1] += x[: i1 - i0] * gain


def pluck_track(dur, start=0.0):
    n = int(dur * SR)
    out = np.zeros(n, np.float32)
    seg = 2 * BAR
    t = start
    step = BEAT / 2
    k = 0
    while t < dur:
        bar_i = int((t) / seg)
        name, notes = CHORDS[bar_i % 4]
        pos = int(round((t % seg) / step))
        tones = [m + 12 for m in notes]
        # arpeggio pattern with rests; occasional scale ornament
        pat = [0, None, 1, 2, None, 1, 3, None, 2, None, 1, 2, None, 3, 2, None]
        p = pat[pos % 16]
        if p is not None and rng.random() > 0.12:
            m = tones[p % len(tones)]
            if rng.random() < 0.12:
                m = int(rng.choice(SCALE))
            vel = 0.55 + 0.25 * rng.random()
            add(out, pluck(m), t + rng.normal(0, 0.006), vel)
        t += step
        k += 1
    return lowpass(out, 5000).astype(np.float32)


def bass_track(dur):
    n = int(dur * SR)
    out = np.zeros(n, np.float32)
    seg = 2 * BAR
    t = 0.0
    while t < dur:
        name, notes = CHORDS[int(t / seg) % 4]
        f = midi(notes[0] - 12)
        L = int(2 * BEAT * SR)
        tt = np.arange(L) / SR
        x = (np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(4 * np.pi * f * tt)) * np.exp(-tt / 0.9)
        x[: int(0.01 * SR)] *= np.linspace(0, 1, int(0.01 * SR))
        add(out, x.astype(np.float32), t, 0.9)
        t += 2 * BEAT
    return out


def dum():
    L = int(0.45 * SR)
    t = np.arange(L) / SR
    f = 95 * np.exp(-t / 0.08) + 55
    ph = 2 * np.pi * np.cumsum(f) / SR
    x = np.sin(ph) * np.exp(-t / 0.16)
    x += 0.15 * lowpass(rng.uniform(-1, 1, L), 900) * np.exp(-t / 0.03)
    return (x / np.abs(x).max()).astype(np.float32)


def tek():
    L = int(0.12 * SR)
    t = np.arange(L) / SR
    x = bandpass(rng.uniform(-1, 1, L), 2200, 6500) * np.exp(-t / 0.025)
    x += 0.4 * np.sin(2 * np.pi * 1800 * t) * np.exp(-t / 0.01)
    return (x / np.abs(x).max()).astype(np.float32)


def perc_track(dur, on_ranges):
    n = int(dur * SR)
    out = np.zeros(n, np.float32)
    D, T = dum(), tek()
    pat = ["D", "T", None, "T", "D", None, "T", None]   # maqsum (8ths)
    step = BEAT / 2
    t = 0.0
    k = 0
    while t < dur:
        on = any(a <= t < b for a, b in on_ranges)
        if on:
            p = pat[k % 8]
            if p == "D":
                add(out, D, t, 0.9)
            elif p == "T":
                add(out, T, t + rng.normal(0, 0.004), 0.35 + 0.15 * rng.random())
            if k % 32 == 31 and rng.random() < 0.6:   # small fill
                add(out, T, t + step / 2, 0.25)
        t += step
        k += 1
    return out


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


def main():
    specs, tl = build_shots()
    dur = tl["duration"]
    secs = {s["id"]: s for s in tl["sections"]}
    title_at = secs["intro"]["title_at"]

    print("music...")
    pad = pad_track(dur + 3)
    pl = pluck_track(dur + 3)
    bs = bass_track(dur + 3)
    # percussion: off during intro hook, on afterwards with breathing gaps every ~2 min
    on = []
    t = title_at
    while t < dur - 6:
        on.append((t, min(t + 100, dur - 6)))
        t += 116
    pc = perc_track(dur + 3, on)
    n = int((dur + 3) * SR)
    music = (0.30 * pad[:n] + 0.22 * pl[:n] + 0.30 * bs[:n] + 0.20 * pc[:n]).astype(np.float32)
    del pad, pl, bs, pc
    # arrangement envelope: softer under the hook, swell at title and outro
    tt = (np.arange(n) / SR).astype(np.float32)
    env = np.ones(n, np.float32) * 0.85
    env[tt < title_at] = 0.7
    sw = (tt >= title_at - 0.2) & (tt < title_at + 3.4)
    env[sw] = 1.35
    from scipy.ndimage import uniform_filter1d
    env = uniform_filter1d(env, size=int(SR * 0.4), mode="nearest").astype(np.float32)
    fade = np.clip((dur + 0.5 - tt) / 4.0, 0, 1)
    fin = np.clip(tt / 1.5, 0, 1)
    music = music * env * fade * fin
    music = music / (np.abs(music).max() + 1e-6) * 0.6
    # stereo: tiny delay on right for width
    d = int(0.012 * SR)
    musR = np.concatenate([np.zeros(d, np.float32), music[:-d]])
    write_wav(os.path.join(BUILD, "music.wav"), np.stack([music, musR], 1).reshape(-1), ch=2)

    print("sfx...")
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
    R = riser()
    i0 = int((title_at - len(R) / SR + 0.05) * SR)
    sfx[i0:i0 + len(R), :] += R[:, None] * 0.35
    I = impact()
    i0 = int((title_at + 0.05) * SR)
    sfx[i0:i0 + len(I), :] += I[:, None] * 0.8
    # small impact on the final title card
    last_title = [s for s in specs if s["type"] == "title"][-1]["start"]
    i0 = int((last_title + 0.05) * SR)
    sfx[i0:i0 + len(I), :] += I[:, None] * 0.45
    write_wav(os.path.join(BUILD, "sfx.wav"), sfx.reshape(-1), ch=2)

    print("mix...")
    out = os.path.join(BUILD, "final_audio.m4a")
    flt = (
        "[0:a]aresample=48000,pan=stereo|c0=c0|c1=c0,highpass=f=70,"
        "acompressor=threshold=-20dB:ratio=3:attack=8:release=120:makeup=2,asplit=2[v][vsc];"
        "[1:a]volume=0.55[m];"
        "[m][vsc]sidechaincompress=threshold=0.03:ratio=8:attack=40:release=450:makeup=1[md];"
        "[2:a]volume=0.9[s];"
        "[v][md][s]amix=inputs=3:duration=first:normalize=0,"
        "loudnorm=I=-14:TP=-1.5:LRA=11[out]"
    )
    subprocess.run([FF, "-y", "-v", "error", "-i", os.path.join(BUILD, "narration.wav"),
                    "-i", os.path.join(BUILD, "music.wav"), "-i", os.path.join(BUILD, "sfx.wav"),
                    "-filter_complex", flt, "-map", "[out]", "-ar", "48000", "-c:a", "aac", "-b:a", "128k", out],
                   check=True)
    print("audio ready:", out)


if __name__ == "__main__":
    main()
