"""Build the final vertical motion-graphics video from a voice track.

    python build.py --audio media/voice.mp3 --transcript deliver/transcript.json
    python build.py --transcript deliver/transcript.json      # no audio (preview)

Captions are generated from word-level timings: short chunks that appear on the
beat of the voice, with a soft scrim, an accent underline and a live waveform.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mgfx.assgen import Ass, CYAN, WHITE  # noqa: E402
from mgfx.render import render  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))

MAX_WORDS = 4          # words per caption chunk
MAX_DUR = 2.4          # seconds per chunk
MIN_DUR = 0.55
GAP_SPLIT = 0.42       # pause (s) that forces a new chunk
CAP_Y = 1320           # vertical centre of the caption block (1080x1920)


def load_words(path: str):
    data = json.load(open(path, encoding="utf-8"))
    words = []
    for seg in data.get("segments", []):
        for w in seg.get("words", []):
            if w["w"]:
                words.append(w)
    return data, words


def chunk_words(words):
    """Group words into readable caption chunks."""
    chunks, cur = [], []
    for w in words:
        if cur:
            gap = w["start"] - cur[-1]["end"]
            dur = w["end"] - cur[0]["start"]
            if (len(cur) >= MAX_WORDS or gap > GAP_SPLIT or dur > MAX_DUR
                    or cur[-1]["w"].endswith((".", "؟", "!", "،", ":", "..."))):
                chunks.append(cur)
                cur = []
        cur.append(w)
    if cur:
        chunks.append(cur)
    out = []
    for ch in chunks:
        t0, t1 = ch[0]["start"], ch[-1]["end"]
        if t1 - t0 < MIN_DUR:
            t1 = t0 + MIN_DUR
        out.append({"t0": t0, "t1": t1, "text": " ".join(w["w"] for w in ch)})
    return out


def build_ass(chunks, duration: float) -> Ass:
    a = Ass()
    for i, ch in enumerate(chunks):
        t0 = max(0.0, ch["t0"] - 0.08)
        t1 = min(duration - 0.02, ch["t1"] + 0.16)
        if i + 1 < len(chunks):
            t1 = min(t1, chunks[i + 1]["t0"] + 0.02)
        n = len(ch["text"])
        size = 78 if n <= 22 else (68 if n <= 30 else 58)
        a.line(t0, t1, ch["text"], y=CAP_Y, style="Body",
               rise=26, blur=16, scale=94, dur=0.30, extra=f"\\fs{size}")
    return a


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--audio", default=None)
    ap.add_argument("--transcript", default=os.path.join(HERE, "deliver", "transcript.json"))
    ap.add_argument("--out", default=os.path.join(HERE, "deliver", "final.mp4"))
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--crf", type=int, default=19)
    args = ap.parse_args()

    data, words = load_words(args.transcript)
    if not words:
        raise SystemExit("no words in transcript")

    if args.audio:
        import subprocess
        try:
            import imageio_ffmpeg
            ff = imageio_ffmpeg.get_ffmpeg_exe()
        except Exception:
            ff = "ffmpeg"
        raw = subprocess.run([ff, "-v", "error", "-i", args.audio, "-ac", "1",
                              "-ar", "8000", "-f", "s16le", "-"],
                             capture_output=True, check=True).stdout
        dur = len(raw) / 2 / 8000
    else:
        dur = max(ch["t1"] for ch in chunk_words(words)) + 0.6

    chunks = chunk_words(words)
    dur = max(dur, chunks[-1]["t1"] + 0.5)
    ass = build_ass(chunks, dur).write(os.path.join(HERE, "deliver", "build.ass"))

    def flags(t, total):
        f = 0.0
        for ch in chunks:
            d = abs(t - ch["t0"])
            if d < 0.12:
                f += (1 - d / 0.12) * 0.28
        return {"flash": f}

    render(args.out, dur, ass, audio=args.audio, flags=flags, fps=args.fps, crf=args.crf)
    print(f"wrote {args.out}  ({dur:.1f}s, {len(chunks)} caption chunks)")


if __name__ == "__main__":
    main()
