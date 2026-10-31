"""Procedural score + final mix.

The bed is synthesised from scratch (numpy) so the project ships with no
third-party music: a slow minor drone, a soft pulse every two bars and a
filtered noise "air" layer that opens up under the b-roll moments.
"""
from __future__ import annotations

import math
import wave
from functools import lru_cache

import numpy as np

SR = 44100


# ---------------------------------------------------------------- helpers
def _env(n, attack, release):
    a = np.linspace(0, 1, max(1, int(attack * SR)))
    r = np.linspace(1, 0, max(1, int(release * SR)))
    hold = np.ones(max(0, n - len(a) - len(r)))
    return np.concatenate([a, hold, r])[:n]


def _saw(freq, n, harmonics=6):
    t = np.arange(n) / SR
    out = np.zeros(n)
    for k in range(1, harmonics + 1):
        out += np.sin(2 * math.pi * freq * k * t) / k
    return out


def _pad(freq, n, detune=0.0):
    return _saw(freq * (1 + detune), n, harmonics=4) * 0.5


def _lowpass(x, cutoff=900.0):
    """One-pole low-pass; enough to make the synth sit behind a voice."""
    a = math.exp(-2 * math.pi * cutoff / SR)
    y = np.empty_like(x)
    acc = 0.0
    for i in range(0, len(x), 1):
        acc = (1 - a) * x[i] + a * acc
        y[i] = acc
    return y


def _noise_air(n, seed=3):
    rng = np.random.default_rng(seed)
    x = rng.normal(0, 1, n)
    # cheap smoothing = band-limited hiss
    k = np.ones(24) / 24
    return np.convolve(x, k, mode="same")


# ---------------------------------------------------------------- score
def make_bed(duration, bpm=72, root=55.0, seed=5):
    n = int(duration * SR)
    mix = np.zeros(n, dtype=np.float32)
    bar = 60.0 / bpm * 4.0

    # A minor-ish drone: root, fifth, octave, minor third (colour)
    chord = [root, root * 1.5, root * 2.0, root * 2.378]
    t0 = 0.0
    idx = 0
    while t0 < duration:
        seg = min(bar * 2, duration - t0)
        if seg <= 0.05:
            break
        m = int(seg * SR)
        root_f = chord[idx % len(chord)]
        layer = np.zeros(m, dtype=np.float32)
        layer += _pad(root_f, m, 0.0) * 0.55
        layer += _pad(root_f * 2, m, 0.0035) * 0.22
        layer += _pad(root_f * 1.5, m, -0.0035) * 0.18
        layer = _lowpass(layer, 620)
        layer *= _env(m, 1.6, 1.8)
        start = int(t0 * SR)
        end = min(n, start + m)
        mix[start:end] += layer[: end - start]
        t0 += seg
        idx += 1

    # sub pulse on the beat, very quiet
    beat = 60.0 / bpm
    t = 0.0
    kick_env = np.exp(-np.linspace(0, 9, int(beat * SR)))
    kick = np.sin(2 * math.pi * 46 * np.arange(len(kick_env)) / SR) * kick_env
    while t < duration:
        s = int(t * SR)
        e = min(n, s + len(kick))
        mix[s:e] += (kick[: e - s] * 0.16).astype(np.float32)
        t += beat * 2

    # air layer, slowly breathing
    air = _noise_air(n, seed).astype(np.float32) * 0.05
    lfo = (0.5 + 0.5 * np.sin(2 * math.pi * np.arange(n) / (SR * 21))) ** 2
    mix += air * lfo.astype(np.float32)

    # gentle top-and-tail
    fade = int(3.0 * SR)
    mix[:fade] *= np.linspace(0, 1, fade)
    mix[-fade:] *= np.linspace(1, 0, fade)
    peak = float(np.max(np.abs(mix))) or 1.0
    return mix / peak * 0.9


# ---------------------------------------------------------------- sfx
@lru_cache(maxsize=8)
def _sfx_cached(kind: str) -> "np.ndarray":
    return _make_sfx(kind)


def _make_sfx(kind):
    """Tiny UI/tactical sounds synthesised from noise + damped sines."""
    rng = np.random.default_rng(abs(hash(kind)) % 2 ** 32)
    if kind == "impact":
        n = int(1.5 * SR)
        t = np.arange(n) / SR
        boom = np.sin(2 * math.pi * 62 * t) * np.exp(-t * 5.5) * 0.9
        boom += np.sin(2 * math.pi * 34 * t) * np.exp(-t * 3.0) * 0.6
        air = rng.normal(0, 1, n) * np.exp(-t * 9.0) * 0.18
        click = np.zeros(n)
        click[: int(0.02 * SR)] = rng.normal(0, 1, int(0.02 * SR)) * np.linspace(1, 0, int(0.02 * SR))
        out = boom + air + click * 0.5
        return (out / (np.max(np.abs(out)) or 1) * 0.75).astype(np.float32)
    if kind == "whoosh":
        n = int(0.55 * SR)
        t = np.arange(n) / SR
        noise = rng.normal(0, 1, n)
        # sweeping band-pass by cross-fading two smoothed copies
        a = np.convolve(noise, np.ones(9) / 9, mode="same")
        b = np.convolve(noise, np.ones(140) / 140, mode="same")
        x = a * np.linspace(1, 0, n) + b * np.linspace(0, 1, n)
        env = np.sin(np.pi * np.clip(t / 0.55, 0, 1)) ** 1.6
        out = x * env
        return (out / (np.max(np.abs(out)) or 1) * 0.30).astype(np.float32)
    # "tick": a small metal click, like a switch or a UI card landing
    n = int(0.16 * SR)
    t = np.arange(n) / SR
    body = (np.sin(2 * math.pi * 1450 * t) * 0.5 + np.sin(2 * math.pi * 2600 * t) * 0.28)
    body *= np.exp(-t * 70)
    tr = rng.normal(0, 1, n) * np.exp(-t * 180) * 0.5
    out = body + tr
    return (out / (np.max(np.abs(out)) or 1) * 0.22).astype(np.float32)


def sfx(kind: str):
    return _sfx_cached(kind)


# ---------------------------------------------------------------- files
def read_wav(path):
    with wave.open(path, "rb") as w:
        n = w.getnframes()
        ch = w.getnchannels()
        sr = w.getframerate()
        raw = w.readframes(n)
    data = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    if ch > 1:
        data = data.reshape(-1, ch).mean(axis=1)
    if sr != SR:
        # linear resample (good enough for speech)
        tgt = int(len(data) * SR / sr)
        data = np.interp(np.linspace(0, len(data) - 1, tgt), np.arange(len(data)), data)
    return data.astype(np.float32)


def write_wav(path, mono, peak=0.89):
    m = np.asarray(mono, dtype=np.float32)
    p = float(np.max(np.abs(m))) or 1.0
    m = m / p * peak
    pcm = (np.clip(m, -1, 1) * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


def music_swell(duration, bpm=72, root=55.0):
    """A short riser used under the intro and the end card."""
    n = int(duration * SR)
    t = np.arange(n) / SR
    riser = np.sin(2 * math.pi * (70 + 40 * (t / max(t[-1], 0.01))) * t) * 0.20
    riser *= np.linspace(0.2, 1.0, n) ** 1.5
    bed = make_bed(duration, bpm=bpm, root=root)
    out = riser + bed * 0.8
    return out / (float(np.max(np.abs(out))) or 1.0)
