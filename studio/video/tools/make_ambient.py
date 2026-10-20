#!/usr/bin/env python3
"""
Vellum Logs — 432 Hz ambient sleep bed generator
------------------------------------------------
Creates a seamless, slowly-breathing drone tuned to A4 = 432 Hz,
plus a bed of soft brown noise. No rhythm, no melody, no transients.

    python3 tools/make_ambient.py out/ambient_432.wav --seconds 90

Design notes (why it sounds "sleepy"):
  * every partial is detuned by a few cents -> slow beating, never static
  * amplitude LFOs run at 0.017–0.061 Hz (breathing speed, 16–60 s per cycle)
  * all harmonics above 2 kHz are rolled off -> no hiss, no sibilance
  * the loop point is cross-faded so it can repeat for 3 hours invisibly
"""
import argparse
import wave

import numpy as np

SR = 44100
A4 = 432.0


def note(semitones_from_a4: float) -> float:
    return A4 * (2 ** (semitones_from_a4 / 12.0))


# A minor-ish open chord, low and warm: A2, E3, A3, C4, E4
CHORD = [
    (-24, 0.30),   # A2  108 Hz
    (-17, 0.17),   # E3  162 Hz
    (-12, 0.14),   # A3  216 Hz
    (-9, 0.07),    # C4  270 Hz
    (-5, 0.05),    # E4  324 Hz
    (0, 0.025),    # A4  432 Hz
]


def build(seconds: float, seed: int = 7) -> np.ndarray:
    rng = np.random.default_rng(seed)
    n = int(SR * seconds)
    t = np.arange(n) / SR
    mix = np.zeros(n, dtype=np.float64)

    for i, (semi, amp) in enumerate(CHORD):
        base = note(semi)
        # three slightly detuned voices per partial -> chorus / slow beating
        for k, detune in enumerate((-0.11, 0.0, 0.13)):
            f = base * (2 ** (detune / 1200))
            lfo_rate = 0.017 + 0.011 * ((i + k) % 4)
            lfo = 0.62 + 0.38 * np.sin(2 * np.pi * lfo_rate * t + i * 1.7 + k)
            phase = rng.uniform(0, 2 * np.pi)
            mix += (amp / 3.0) * lfo * np.sin(2 * np.pi * f * t + phase)

    # soft low harmonics only (keeps it dark and non-fatiguing)
    for semi in (-24, -12):
        f = note(semi)
        mix += 0.05 * np.sin(2 * np.pi * f * 2 * t) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.023 * t))

    # brown noise bed (integrated white noise), low-passed twice
    white = rng.normal(0, 1, n)
    brown = np.cumsum(white)
    brown -= np.linspace(brown[0], brown[-1], n)          # remove drift
    brown /= (np.max(np.abs(brown)) + 1e-9)
    # simple one-pole low-pass to tame it further
    a = 0.0025
    lp = np.empty_like(brown)
    acc = 0.0
    for idx in range(0, n, 1):
        acc += a * (brown[idx] - acc)
        lp[idx] = acc
    lp /= (np.max(np.abs(lp)) + 1e-9)
    mix += 0.16 * lp

    # global slow swell (very gentle) — 40 s cycle
    mix *= 0.92 + 0.08 * np.sin(2 * np.pi * 0.025 * t)

    # normalise to about -20 dBFS peak; loudness is set later by ffmpeg
    mix /= np.max(np.abs(mix)) + 1e-9
    mix *= 0.32
    return mix


def crossfade_loop(x: np.ndarray, sr: int, fade: float = 3.0) -> np.ndarray:
    """Make the clip loop seamlessly by cross-fading its tail into its head."""
    f = int(sr * fade)
    head = x[:f].copy()
    tail = x[-f:].copy()
    ramp = np.linspace(0, 1, f)
    x = x[:-f].copy()
    x[-f:] = x[-f:] * (1 - ramp) + head * 0 + 0        # keep body
    # blend: start of body fades in from tail
    x[:f] = x[:f] * ramp + tail * (1 - ramp)
    return x


def write_wav(path: str, mono: np.ndarray, sr: int = SR):
    pcm = np.clip(mono, -1, 1)
    pcm = (pcm * 32767).astype(np.int16)
    stereo = np.repeat(pcm[:, None], 2, axis=1)
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(stereo.tobytes())


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("output")
    ap.add_argument("--seconds", type=float, default=90)
    ap.add_argument("--fade", type=float, default=3.0)
    args = ap.parse_args()

    body = build(args.seconds + args.fade)
    loop = crossfade_loop(body, SR, args.fade)
    write_wav(args.output, loop)
    print(f"✓ {args.output}  {len(loop)/SR:.1f}s  432 Hz bed")
