# -*- coding: utf-8 -*-
"""Silence analysis of TTS clips -> section boundaries + per-section timing."""
import json, subprocess, sys, os
import numpy as np
import imageio_ffmpeg

FF = imageio_ffmpeg.get_ffmpeg_exe()
SR = 24000

def load_wav(path, sr=SR):
    cmd = [FF, "-v", "error", "-i", path, "-f", "s16le", "-ac", "1", "-ar", str(sr), "-"]
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0

def silences(x, sr=SR, win=0.01, thr_db=-38.0, min_len=0.18):
    hop = int(sr * win)
    n = len(x) // hop
    frames = x[: n * hop].reshape(n, hop)
    rms = np.sqrt((frames ** 2).mean(axis=1) + 1e-12)
    db = 20 * np.log10(rms + 1e-9)
    quiet = db < thr_db
    out = []
    i = 0
    while i < n:
        if quiet[i]:
            j = i
            while j < n and quiet[j]:
                j += 1
            if (j - i) * win >= min_len:
                out.append((i * win, j * win))
            i = j
        else:
            i += 1
    return out, db

if __name__ == "__main__":
    for f in sorted(os.listdir(sys.argv[1])):
        if not f.endswith(".wav"):
            continue
        x = load_wav(os.path.join(sys.argv[1], f))
        s, db = silences(x)
        dur = len(x) / SR
        longs = [(round(a, 2), round(b - a, 2)) for a, b in s if b - a >= 0.45]
        print(f, round(dur, 2), "n_sil", len(s), "lead", round(s[0][1], 2) if s and s[0][0] == 0 else 0,
              "\n   long:", longs)
