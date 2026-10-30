"""Render orchestration: numpy background -> ffmpeg (upscale + ASS + grade) -> mp4."""
from __future__ import annotations

import os
import subprocess
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mgfx.background import Background  # noqa: E402

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FFMPEG = None


def ffmpeg_bin() -> str:
    global FFMPEG
    if FFMPEG:
        return FFMPEG
    try:
        import imageio_ffmpeg
        FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        FFMPEG = "ffmpeg"
    return FFMPEG


def audio_envelope(path: str, n_frames: int, fps: int = 30, sr: int = 8000,
                   smooth: int = 3):
    """Per-frame loudness envelope of the soundtrack, normalised 0..1."""
    if not path:
        return None
    cmd = [ffmpeg_bin(), "-v", "error", "-i", path, "-ac", "1", "-ar", str(sr),
           "-f", "s16le", "-"]
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    pcm = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    hop = max(1, sr // fps)
    n = min(n_frames, len(pcm) // hop)
    env = np.array([np.sqrt(np.mean(pcm[i * hop:(i + 1) * hop] ** 2) + 1e-9)
                    for i in range(n)], dtype=np.float32)
    # light smoothing
    if smooth > 1:
        k = np.ones(smooth, dtype=np.float32) / smooth
        env = np.convolve(env, k, mode="same")
    p95 = float(np.percentile(env, 96)) or 1.0
    env = np.clip(env / p95, 0, 1) ** 0.72
    if len(env) < n_frames:
        env = np.pad(env, (0, n_frames - len(env)), mode="constant")
    return env


def render(out: str, duration: float, ass_path: str, audio: str | None = None,
           fps: int = 30, w: int = 540, h: int = 960, crf: int = 19,
           preset: str = "veryfast", flags=None, progress=True, seed: int = 7,
           log: str | None = None, palette: str = "aurora", t_start: float = 0.0,
           total_duration: float | None = None):
    """Render the full video. `flags(t)->dict` may inject per-frame effects
    (flash=..., dust_boost=...)."""
    n = max(1, int(round(duration * fps)))
    total_n = int(round((total_duration or (t_start + n / fps)) * fps))
    env = audio_envelope(audio, total_n, fps) if audio else None
    if env is not None and t_start:
        env = env[int(t_start * fps):]
    bg = Background(w=w, h=h, fps=fps, seed=seed, palette=palette)
    fontsdir = os.path.join(HERE, "fonts")

    vf = (f"scale=1080:1920:flags=bicubic+accurate_rnd+full_chroma_int,"
          f"ass={ass_path}:fontsdir={fontsdir},"
          f"eq=contrast=1.05:saturation=1.06:gamma=1.01,"
          f"noise=alls=4:allf=t+u,vignette=angle=PI/7,format=yuv420p")

    cmd = [ffmpeg_bin(), "-y", "-v", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}", "-r", str(fps), "-i", "pipe:0"]
    if audio:
        cmd += ["-i", audio]
    else:
        cmd += ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-shortest"]
    cmd += ["-vf", vf, "-c:v", "libx264", "-preset", preset, "-crf", str(crf),
            "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.2",
            "-x264-params", "keyint=60:min-keyint=30",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
            "-movflags", "+faststart", out]

    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        total = total_duration or (t_start + n / fps)
        for i in range(n):
            t = t_start + i / fps
            extra = flags(t, total) if flags else {}
            win = None
            if env is not None:
                j0 = max(0, i - 72)
                win = env[j0:i + 5]
            frame = bg.frame(t, envelope=win, progress=min(1.0, t / max(0.1, total)), **extra)
            proc.stdin.write(frame.tobytes())
            if progress and i % 60 == 0:
                sys.stderr.write(f"\r  frame {i}/{n} ({100*i/n:4.1f}%)")
                sys.stderr.flush()
    finally:
        if proc.stdin:
            proc.stdin.close()
        err = proc.stderr.read().decode("utf-8", "replace")
        code = proc.wait()
    if progress:
        sys.stderr.write("\r" + " " * 42 + "\r")
    if code != 0:
        raise RuntimeError(f"ffmpeg failed ({code}):\n{err[-3000:]}")
    if log:
        with open(log, "w") as f:
            f.write(err)
    return out
