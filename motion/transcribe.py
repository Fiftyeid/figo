"""Speech-to-text with word-level timings (faster-whisper, CPU int8).

The Whisper "small" CTranslate2 int8 weights live in ../asr/model (assembled
from the npm packages @skillninja/shortmovie-telop-model-p{0..3}).

    python transcribe.py path/to/voice.mp3 --out deliver/transcript.json
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.abspath(os.path.join(HERE, "..", "..", "asr", "model"))


def ffmpeg_bin() -> str:
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"


def to_wav(src: str, dst: str, sr: int = 16000) -> str:
    subprocess.run([ffmpeg_bin(), "-v", "error", "-y", "-i", src,
                    "-ac", "1", "-ar", str(sr), "-c:a", "pcm_s16le", dst], check=True)
    return dst


def transcribe(audio: str, language: str = "ar", model_dir: str = MODEL_DIR,
               beam: int = 5, tmpdir: str | None = None):
    from faster_whisper import WhisperModel

    tmpdir = tmpdir or os.path.join(HERE, "deliver", "tmp")
    os.makedirs(tmpdir, exist_ok=True)
    wav = to_wav(audio, os.path.join(tmpdir, "asr16k.wav"))

    model = WhisperModel(model_dir, device="cpu", compute_type="int8", cpu_threads=2)
    segments, info = model.transcribe(
        wav, language=language, beam_size=beam, vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=350, speech_pad_ms=120),
        word_timestamps=True, condition_on_previous_text=False,
        temperature=[0.0, 0.2, 0.4],
    )
    out = {"language": info.language, "duration": info.duration,
           "probability": info.language_probability, "segments": []}
    for seg in segments:
        words = [{"w": w.word.strip(), "start": round(w.start, 3),
                  "end": round(w.end, 3), "p": round(w.probability, 3)}
                 for w in (seg.words or [])]
        out["segments"].append({"start": round(seg.start, 3), "end": round(seg.end, 3),
                                "text": seg.text.strip(), "words": words})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("audio")
    ap.add_argument("--out", default=os.path.join(HERE, "deliver", "transcript.json"))
    ap.add_argument("--lang", default="ar")
    ap.add_argument("--text-out", default=None)
    args = ap.parse_args()

    data = transcribe(args.audio, language=args.lang)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)

    txt = "\n".join(s["text"] for s in data["segments"])
    tpath = args.text_out or args.out.replace(".json", ".txt")
    with open(tpath, "w", encoding="utf-8") as f:
        f.write(txt + "\n")
    print(txt)
    print(f"\n[{len(data['segments'])} segments, {data['duration']:.1f}s] -> {args.out}",
          file=sys.stderr)


if __name__ == "__main__":
    main()
