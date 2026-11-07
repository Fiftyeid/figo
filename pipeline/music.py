"""Ambient score: a dark, mechanical drone bed. No melody, no percussion."""
import sys
import wave

import numpy as np
from scipy import signal

SR = 44100


def build(dur, seed=7):
    rng = np.random.default_rng(seed)
    n = int(dur * SR)
    t = np.arange(n) / SR
    out = np.zeros(n)

    for f, amp in [(55.0, 0.50), (55.35, 0.42), (82.41, 0.26), (82.9, 0.20), (110.0, 0.14)]:
        lfo = 0.62 + 0.38 * np.sin(2 * np.pi * (0.021 + 0.011 * f / 110) * t + rng.uniform(0, 6.28))
        out += amp * lfo * np.sin(2 * np.pi * f * t + rng.uniform(0, 6.28))

    noise = rng.normal(0, 1, n)
    b, a = signal.butter(2, [180 / (SR / 2), 900 / (SR / 2)], btype="band")
    noise = signal.lfilter(b, a, noise)
    swell = 0.5 + 0.5 * np.sin(2 * np.pi * 0.017 * t + 1.1)
    out += 0.30 * swell * noise / (np.abs(noise).max() + 1e-9)

    period = 4.0
    for k in range(int(dur / period) + 1):
        env_len = int(0.9 * SR)
        i0 = int((k * period + 0.25) * SR)
        if i0 + env_len > n:
            break
        env = np.exp(-np.linspace(0, 7, env_len))
        out[i0:i0 + env_len] += np.sin(2 * np.pi * 48 * np.linspace(0, 0.9, env_len)) * env * 0.22

    fade = int(4 * SR)
    out[:fade] *= np.linspace(0, 1, fade) ** 1.6
    out[-fade:] *= np.linspace(1, 0, fade) ** 1.6
    out *= 1 + 0.12 * np.sin(2 * np.pi * 0.007 * t)
    out = out / (np.abs(out).max() + 1e-9) * 0.82

    stereo = np.stack([out, np.roll(out, int(0.011 * SR)) * 0.96], axis=1)
    return (np.clip(stereo, -1, 1) * 32767).astype(np.int16)


if __name__ == "__main__":
    dur = float(sys.argv[1]) if len(sys.argv) > 1 else 840
    data = build(dur)
    with wave.open("work/music.wav", "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data.tobytes())
    print("music.wav", round(dur, 1), "s")
