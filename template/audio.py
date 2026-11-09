"""Minimal audio helpers the template needs: decode, normalise, seamless loop."""
from __future__ import annotations

import subprocess
from pathlib import Path

import numpy as np

SR = 44100
ROOT = Path(__file__).resolve().parents[1]


def _decode(path: Path, sr: int = SR) -> np.ndarray:
    import imageio_ffmpeg
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    raw = subprocess.run([ff, "-v", "quiet", "-i", str(path), "-f", "s16le",
                          "-ac", "1", "-ar", str(sr), "-"], capture_output=True).stdout
    if not raw:
        return np.zeros(1, np.float32)
    return np.frombuffer(raw, np.int16).astype(np.float32) / 32768.0


def _trim_silence(a: np.ndarray, thresh: float = 0.006, pad: int = 900) -> np.ndarray:
    idx = np.where(np.abs(a) > thresh)[0]
    if not len(idx):
        return a
    lo, hi = max(0, idx[0] - pad), min(len(a), idx[-1] + pad)
    return a[lo:hi]


def _norm(a: np.ndarray, target_db: float = -19.0) -> np.ndarray:
    rms = float(np.sqrt(np.mean(a ** 2)) + 1e-9)
    return a * (10 ** (target_db / 20) / rms)


def _loop_fit(src: np.ndarray, n: int, fade: float = 1.1) -> np.ndarray:
    """Loop a cue to exactly n samples without a dip or a click at the seam."""
    a = np.asarray(src, np.float32).copy()
    hop = int(0.05 * SR)
    if len(a) > 4 * hop:
        rms = np.array([np.sqrt(np.mean(a[i:i + hop] ** 2)) for i in range(0, len(a) - hop, hop)])
        keep = np.where(rms > np.median(rms) * 0.32)[0]
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
    pos = 0
    while pos < n:
        seg = loop[: min(len(loop), n - pos)]
        out[pos:pos + len(seg)] += seg
        pos += len(loop)
    f = int(0.3 * SR)
    out[:f] *= np.linspace(0, 1, f).astype(np.float32)
    out[-f:] *= np.linspace(1, 0, f).astype(np.float32)
    return out
