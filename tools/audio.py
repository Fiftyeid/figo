"""Audio: voiceover placement, gentle music bed, and final mix."""
from __future__ import annotations

import re
import subprocess
import wave
from pathlib import Path

import imageio_ffmpeg
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
VO = ROOT / "build" / "vo"
SR = 44100
FF = imageio_ffmpeg.get_ffmpeg_exe()


def _duration(path: Path) -> float:
    out = subprocess.run([FF, "-hide_banner", "-i", str(path)],
                         capture_output=True, text=True).stderr
    m = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", out)
    if not m:
        return 0.0
    h, mi, s = m.groups()
    return int(h) * 3600 + int(mi) * 60 + float(s)


def probe_durations() -> dict[str, float]:
    return {p.stem: _duration(p) for p in sorted(VO.glob("*.mp3"))}


def _decode(path: Path) -> np.ndarray:
    """Decode any audio file to mono float32 @ SR."""
    raw = subprocess.run([FF, "-v", "quiet", "-i", str(path), "-f", "s16le",
                          "-ac", "1", "-ar", str(SR), "-"], capture_output=True).stdout
    a = np.frombuffer(raw, np.int16).astype(np.float32) / 32768.0
    return a


def _trim_silence(a: np.ndarray, thresh: float = 0.006, pad: int = 900) -> np.ndarray:
    idx = np.where(np.abs(a) > thresh)[0]
    if len(idx) == 0:
        return a
    lo, hi = max(0, idx[0] - pad), min(len(a), idx[-1] + pad)
    return a[lo:hi]


def _norm(a: np.ndarray, target_db: float = -19.0) -> np.ndarray:
    rms = float(np.sqrt(np.mean(a ** 2)) + 1e-9)
    gain = 10 ** (target_db / 20) / rms
    return a * gain


def music_bed(total: float, key: float = 55.0) -> np.ndarray:
    """Slow, quiet ambient pad: stacked fifths with long swells, no percussion."""
    n = int(total * SR)
    t = np.arange(n) / SR
    pad = np.zeros(n, np.float32)
    # a D minor colour: root, fifth, minor tenth, plus an airy overtone
    voices = [(1.0, 0.30), (1.5, 0.16), (2.0, 0.10), (3.0, 0.05), (4.02, 0.022)]
    for mul, amp in voices:
        for det in (-0.0016, 0.0016):
            f = key * mul * (1 + det)
            sw = 0.5 + 0.5 * np.sin(2 * np.pi * (0.021 + 0.007 * mul) * t + mul * 2.1)
            pad += (amp * (0.35 + 0.65 * sw) * np.sin(2 * np.pi * f * t + mul)).astype(np.float32)
    # slow harmonic drift every ~40 s
    drift = 0.55 + 0.45 * np.sin(2 * np.pi * t / 83.0)
    pad *= drift.astype(np.float32)
    # gentle high-shelf air
    noise = np.random.default_rng(3).normal(0, 1, n).astype(np.float32)
    b = np.zeros(6, np.float32)
    for i in range(1, 6):
        b[i] = b[i - 1] * 0.62 + noise[i % n] * 0.38
    air = np.convolve(noise, np.ones(240) / 240, mode="same").astype(np.float32)
    pad += air * 0.05
    # fade in/out
    fi, fo = int(6 * SR), int(8 * SR)
    env = np.ones(n, np.float32)
    env[:fi] = np.linspace(0, 1, fi) ** 1.5
    env[-fo:] = np.linspace(1, 0, fo) ** 1.5
    return pad * env


# ------------------------------------------------------------------ score
def _pluck(freq: float, dur: float, amp: float = 0.3, bright: float = 1.0) -> np.ndarray:
    """Additive plucked string: harmonic stack with per-partial decay."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    sig = np.zeros(n, np.float32)
    for k in range(1, 13):
        f = freq * k * (1.0 + 0.0009 * k)          # slight inharmonicity
        if f > 15000:
            break
        decay = 3.2 + k * 2.6 / max(bright, 0.2)   # highs die first
        sig += (np.sin(2 * np.pi * f * t) * np.exp(-t * decay) / (k ** 1.25)).astype(np.float32)
    atk = max(1, int(0.006 * SR))
    sig[:atk] *= np.linspace(0, 1, atk)
    return (sig * amp).astype(np.float32)


def _note(freq: float, dur: float, amp: float = 0.2, harmonics=(1.0, 0.42, 0.20),
          attack: float = 0.008, release: float = 0.22, detune: float = 0.0025) -> np.ndarray:
    """Sustained synth note with a short attack and a musical release."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    sig = np.zeros(n, np.float32)
    for det in (1 - detune, 1 + detune):
        for h, a in enumerate(harmonics, start=1):
            f = freq * h * det
            if f > 16000:
                break
            sig += (np.sin(2 * np.pi * f * t) * a).astype(np.float32)
    sig /= max(1, len(harmonics))
    env = np.ones(n, np.float32)
    na = max(2, int(attack * SR))
    nr = max(2, int(release * SR))
    env[:na] = np.linspace(0, 1, na) ** 1.5
    if nr < n:
        env[-nr:] = np.linspace(1, 0, nr) ** 1.8
    return (sig * env * amp).astype(np.float32)


def _pad(freqs, dur: float, amp: float = 0.10, attack: float = 0.5,
         release: float = 1.2) -> np.ndarray:
    """Slow choral pad: detuned sine pairs with a soft swell."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    sig = np.zeros(n, np.float32)
    for f in freqs:
        for det in (-0.0022, 0.0022):
            vib = 1 + 0.0016 * np.sin(2 * np.pi * 0.9 * t + f)
            sig += (np.sin(2 * np.pi * f * det_ratio(det) * vib * t) / len(freqs)).astype(np.float32)
    a = np.clip(t / max(attack, 1e-3), 0, 1) ** 1.4
    r = np.clip((dur - t) / max(release, 1e-3), 0, 1) ** 1.3
    return (sig * a * r * amp).astype(np.float32)


def det_ratio(det: float) -> float:
    return 1.0 + det


def _hit(dur: float = 1.8, amp: float = 0.5, f0: float = 54.0, pitch_drop: float = 1.0):
    """Cinematic low impact: pitch-dropping sub plus a short noise transient."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = f0 * (1 + pitch_drop * np.exp(-t * 9))
    phase = 2 * np.pi * np.cumsum(f) / SR
    sub = np.sin(phase) * np.exp(-t * 4.2)
    body = np.sin(phase * 2) * np.exp(-t * 9.0) * 0.35
    trans = np.random.default_rng(5).normal(0, 1, n).astype(np.float32)
    trans = np.convolve(trans, np.ones(40) / 40, mode="same").astype(np.float32)
    trans *= np.exp(-t * 42) * 0.5
    out = (sub + body + trans).astype(np.float32)
    na = max(2, int(0.0035 * SR))          # 3.5 ms attack: no transient click
    out[:na] *= np.linspace(0, 1, na) ** 1.2
    nr = max(2, int(0.05 * SR))
    out[-nr:] *= np.linspace(1, 0, nr) ** 1.5
    return (out * amp).astype(np.float32)


def _riser(dur: float, amp: float = 0.22, lo_hi=(400.0, 4200.0)) -> np.ndarray:
    """Smooth noise swell that opens up as it climbs.

    Two fixed-width moving averages (tight and wide) are cross-faded with a
    continuous ramp, so the tone brightens over time with no block boundaries
    and therefore no clicks.
    """
    n = int(dur * SR)
    noise = np.random.default_rng(31).normal(0, 1, n).astype(np.float32)
    tight = np.convolve(noise, np.ones(12, np.float32) / 12, mode="same").astype(np.float32)
    wide = np.convolve(noise, np.ones(320, np.float32) / 320, mode="same").astype(np.float32)
    t = np.arange(n) / SR
    u = np.clip(t / max(dur, 1e-6), 0, 1)
    mix = (u ** 1.5).astype(np.float32)
    body = noise * 0.55 + tight * 0.9 * (1 - mix) + (tight - wide) * 1.6 * mix
    shape = np.clip(t / (dur * 0.82), 0, 1) ** 2.0 * np.clip((dur - t) / 0.14, 0, 1)
    out = body * shape
    out -= float(np.mean(out))
    return (out * amp).astype(np.float32)


def add(buf: np.ndarray, sig: np.ndarray, at: float, gain: float = 1.0) -> None:
    i0 = int(at * SR)
    if i0 >= len(buf):
        return
    n = min(len(sig), len(buf) - i0)
    if n > 0:
        buf[i0:i0 + n] += sig[:n] * gain


def intro_score(dur: float = 12.0) -> np.ndarray:
    """Musical hook cut to the four-beat title card.

    D minor, 100 BPM. A sustained eighth-note arp carries momentum through all
    four beats, pads hold the harmony, sub hits land exactly on the picture cuts
    at 3.0 / 6.0 / 10.0 s, and the cue is swallowed as the frame blows to white.
    """
    n = int(dur * SR)
    buf = np.zeros(n, np.float32)

    D2 = 73.42
    hz = lambda semi: D2 * (2 ** (semi / 12.0))        # noqa: E731
    eighth = 60.0 / 100.0 / 2.0                        # 0.30 s

    # ---- harmony bed
    add(buf, _pad([hz(0), hz(7)], 3.05, 0.045, 0.9, 1.1), 0.0)
    add(buf, _pad([hz(0), hz(3), hz(7)], 3.15, 0.055, 0.30, 1.2), 3.0)
    add(buf, _pad([hz(0), hz(3), hz(7), hz(12)], 4.15, 0.062, 0.35, 1.5), 5.98)
    add(buf, _pad([hz(0), hz(3), hz(7), hz(12), hz(19)], 2.7, 0.068, 0.18, 1.0), 9.98)

    # ---- driving arp: 8ths, overlapping so the level never drops out
    figures = [
        (0.0, 0.55, (12, 15, 19, 15, 12, 17, 15, 19, 22, 19)),      # beat 1, establishing
        (3.0, 0.80, (12, 19, 15, 22, 12, 19, 17, 22, 19, 24)),      # beat 2, subject lands
        (6.0, 0.95, (12, 19, 22, 15, 24, 19, 22, 17, 24, 26)),      # beat 3, stack grows
    ]
    for t0, g, seq in figures:
        for i, semi in enumerate(seq):
            if t0 + i * eighth + eighth > 11.95:
                break
            add(buf, _note(hz(semi), eighth * 1.7, 0.105 * g,
                           (1.0, 0.34, 0.16, 0.07)), t0 + i * eighth)
            add(buf, _pluck(hz(semi + 12), 0.7, 0.045 * g), t0 + i * eighth)

    # ---- beat 4: resolve, held chord with a longer release
    for i, semi in enumerate((12, 15, 19, 24)):
        add(buf, _note(hz(semi), 1.5, 0.085, (1.0, 0.40, 0.22, 0.10), 0.01, 0.5), 10.0 + i * 0.12)

    # ---- bass on the half-bar
    for bt in np.arange(0.0, 11.9, 0.6):
        semi = 0 if (round(bt / 0.6) % 4) else 12
        add(buf, _note(hz(semi - 12), 0.52, 0.085, (1.0, 0.28), 0.014, 0.16), float(bt))

    # ---- picture-cut impacts and the opening air
    add(buf, _hit(1.9, 0.24, 60.0), 0.02)
    add(buf, _hit(1.9, 0.34, 52.0), 3.00)
    add(buf, _hit(1.9, 0.28, 56.0), 6.00)
    add(buf, _hit(2.4, 0.40, 47.0), 10.00)
    add(buf, _riser(2.6, 0.07, (300, 2600)), 0.05)
    add(buf, _riser(1.5, 0.10, (900, 7000)), 10.35)

    # ---- blow-out: gate to silence, then one soft tail rings out
    t = np.arange(n) / SR
    gate = np.where(t < 11.08, np.minimum(1.0, np.clip((11.08 - t) / 0.08, 0, 1)), 0.0)
    buf *= gate.astype(np.float32)
    add(buf, _pad([hz(0), hz(7), hz(12)], 3.6, 0.040, 0.02, 3.2), 11.06)

    # ---- de-click: 15 ms median-style smoothing kills single-sample spikes
    #      without touching the musical envelope
    if len(buf) > 64:
        k = 5
        med = np.median(np.lib.stride_tricks.sliding_window_view(buf, k), axis=1)
        med = np.pad(med, (k // 2, k // 2), mode="edge")[: len(buf)].astype(np.float32)
        spike = np.abs(buf - med) > 0.08
        buf = np.where(spike, med, buf)
        # gentle 1-pole low-pass at ~16 kHz to tame residual sizzle
        a = 0.55
        y = np.empty_like(buf)
        acc = buf[0]
        for i in range(len(buf)):
            acc = acc + a * (buf[i] - acc)
            y[i] = acc
        buf = y

    # ---- loudness: consistent body, soft limit, musical headroom
    buf /= (float(np.max(np.abs(buf))) + 1e-9)
    buf = np.tanh(buf * 1.5).astype(np.float32) / np.tanh(1.5)
    return (buf * 0.72).astype(np.float32)


def mix_audio(scenes, out: Path, total: float) -> None:
    n = int((total + 2.0) * SR)
    voice = np.zeros(n, np.float32)
    for sc in scenes:
        if sc.kind == "intro":                     # musical hook for the title card
            fx = intro_score(sc.dur)
            i0 = int(sc.abs_start * SR)
            voice[i0:i0 + len(fx)] += fx[: max(0, n - i0)]
        for path, off in sc.audio:
            if not Path(path).exists():
                continue
            a = _trim_silence(_decode(Path(path)))
            a = _norm(a, -18.5)
            start = int((sc.abs_start + off) * SR)
            end = min(n, start + len(a))
            if start >= n:
                continue
            voice[start:end] += a[: end - start]

    # speech envelope drives music ducking
    hop = int(0.02 * SR)
    frames = len(voice) // hop
    env = np.abs(voice[: frames * hop]).reshape(frames, hop).max(axis=1)
    env = np.convolve(env, np.ones(40) / 40, mode="same")
    duck = 1.0 - 0.72 * np.clip(env / 0.25, 0, 1)
    duck_full = np.repeat(duck, hop)
    if len(duck_full) < n:
        duck_full = np.pad(duck_full, (0, n - len(duck_full)), mode="edge")

    bed = music_bed(total + 2.0) * duck_full.astype(np.float32)
    # the ambient bed stays out of the title card; it enters after the cut
    intro_len = next((sc.dur for sc in scenes if sc.kind == "intro"), 0.0)
    gate = np.clip((np.arange(len(bed)) / SR - intro_len) / 2.5, 0, 1) ** 1.3
    bed = bed * gate.astype(np.float32)
    bed = bed / (np.max(np.abs(bed)) + 1e-9) * 0.10        # quiet bed, ~-20 dBFS peak

    mix = voice + bed
    # soft limiter
    peak = np.max(np.abs(mix)) + 1e-9
    if peak > 0.95:
        mix = np.tanh(mix / peak * 1.05) * 0.95
    mix = mix * 0.92

    # subtle stereo width: voice centred, bed slightly decorrelated
    left = mix
    right = mix * 0.995 + np.roll(bed, 90) * 0.05
    stereo = np.stack([left, right], axis=1)
    pcm = (np.clip(stereo, -1, 1) * 32767).astype(np.int16)

    with wave.open(str(out), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


def _loop_fit(src: np.ndarray, n: int, fade: float = 1.1) -> np.ndarray:
    """Loop `src` to exactly `n` samples with no dip and no click at the seam.

    The supplied cues end in a fade to silence, so tiling them raw drops the
    music to nothing and then jumps back in — that gap reads as a bad edit.
    Trim the dying tail, then equal-power crossfade the head over the tail.
    """
    a = np.asarray(src, np.float32).copy()
    hop = int(0.05 * SR)
    if len(a) > 4 * hop:
        rms = np.array([np.sqrt(np.mean(a[i:i + hop] ** 2)) for i in range(0, len(a) - hop, hop)])
        thr = np.median(rms) * 0.32
        keep = np.where(rms > thr)[0]
        if len(keep):
            a = a[: min(len(a), (keep[-1] + 2) * hop)]
    if len(a) < int(0.6 * SR) or n <= len(a):
        return np.pad(a, (0, max(0, n - len(a))))[:n]

    k = int(min(fade * SR, len(a) * 0.28))
    body, tail, head = a[:-k], a[-k:], a[:k]
    t = np.linspace(0, 1, k).astype(np.float32)
    seam = tail * np.cos(t * np.pi / 2) + head * np.sin(t * np.pi / 2)
    loop = np.concatenate([body, seam]).astype(np.float32)

    out = np.zeros(n, np.float32)
    pos, L = 0, len(loop)
    while pos < n:
        seg = loop[: min(L, n - pos)]
        out[pos:pos + len(seg)] += seg
        pos += L
    f = int(0.3 * SR)
    out[:f] *= np.linspace(0, 1, f).astype(np.float32)
    out[-f:] *= np.linspace(1, 0, f).astype(np.float32)
    return out


def roll_mix(vo: np.ndarray, total: float, per: float, lead: float, out: Path,
             bed_path: Path | None = None, bed_gain: float = 1.05) -> None:
    """Voice over a music bed. No transition sound effects: the cut is on the music."""
    n = int(total * SR)
    voice = np.zeros(n, np.float32)
    i0 = int(lead * SR)
    seg = vo[: max(0, n - i0)]
    voice[i0:i0 + len(seg)] += seg

    if bed_path is not None and Path(bed_path).exists():
        bed = _loop_fit(_norm(_decode(Path(bed_path)), -17.5), n)
    else:
        bed = music_bed(total)

    hop = int(0.02 * SR)
    frames = len(voice) // hop
    env = np.abs(voice[: frames * hop]).reshape(frames, hop).max(axis=1)
    env = np.convolve(env, np.ones(40) / 40, mode="same")
    duck = 1.0 - 0.50 * np.clip(env / 0.26, 0, 1)
    duck_full = np.repeat(duck, hop)
    if len(duck_full) < n:
        duck_full = np.pad(duck_full, (0, n - len(duck_full)), mode="edge")

    bed = bed * duck_full.astype(np.float32) * bed_gain
    mix = voice + bed
    peak = float(np.max(np.abs(mix))) + 1e-9
    if peak > 0.95:
        mix = np.tanh(mix / peak * 1.05) * 0.95

    left = mix
    right = mix * 0.995 + np.roll(bed, 120) * 0.06
    stereo = np.stack([left, right], axis=1)
    pcm = (np.clip(stereo, -1, 1) * 32767).astype(np.int16)
    with wave.open(str(out), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
