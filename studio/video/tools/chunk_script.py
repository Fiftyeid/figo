#!/usr/bin/env python3
"""
Vellum Logs — turn the written script into TTS-sized chunks.

The speech engine accepts ~1,500 characters per call, so the narration is cut
into ~1,300-character pieces at *sentence* boundaries only. Each chunk keeps a
chapter tag so the video manifest can line pictures up with the words.

    python3 tools/chunk_script.py scripts/EP01_part2.md scripts/EP01_part3.md \
        --start "It is so large that it had to be built where it stands." \
        --first-clip 18 --out narration/plan_rest.json

Rules:
  * a chunk never starts or ends mid-sentence
  * stage directions inside [brackets] are dropped (they are sound cues, not speech)
  * markdown headings become chapter tags, never speech
  * a chunk never crosses a chapter boundary
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

MAX_CHARS = 1380
HEADING = re.compile(r"^###\s*([A-Z0-9IVXLC]+)\s*[·.\-]\s*(.+?)\s*(?:\[.*\])?\s*$")


def clean(line: str) -> str | None:
    s = line.strip()
    if not s:
        return None
    if s.startswith("#"):                      # heading / part marker
        return None
    if s.startswith("**"):                     # metadata line
        return None
    if s.startswith("---") or s.startswith("***"):
        return None
    if s.startswith("[") and s.endswith("]"):  # stage direction
        return None
    if s.startswith("*(") and s.endswith(")*"):  # whispered aside
        return None
    s = s.replace("—", ", ").replace("–", ", ")
    s = re.sub(r"\s+", " ", s)
    return s


def split_sentences(text: str) -> list[str]:
    # keep the terminator with the sentence
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z\"'“‘])", text)
    return [p.strip() for p in parts if p.strip()]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--start", default=None,
                    help="only narrate from the first sentence containing this text")
    ap.add_argument("--first-clip", type=int, default=1)
    ap.add_argument("--prefix", default="c")
    ap.add_argument("--stop", default=None, help="stop at the first line starting with this")
    ap.add_argument("--max-chars", type=int, default=MAX_CHARS)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    chapter = "00"
    chapter_title = "Opening"
    started = args.start is None
    chunks: list[dict] = []
    buf = ""

    def flush() -> None:
        nonlocal buf
        if buf.strip():
            chunks.append({"chapter": chapter, "chapter_title": chapter_title,
                           "chars": len(buf), "words": len(buf.split()),
                           "text": buf.strip()})
        buf = ""

    for path in args.files:
        for line in Path(path).read_text(encoding="utf-8").splitlines():
            if args.stop and line.strip().startswith(args.stop):
                break
            m = HEADING.match(line.strip())
            if m:
                flush()
                chapter, chapter_title = m.group(1), m.group(2).strip().title()
                continue
            body = clean(line)
            if not body:
                continue
            if not started:
                if args.start in body:
                    body = body[body.index(args.start):]
                    started = True
                else:
                    continue
            for sentence in split_sentences(body):
                if len(buf) + len(sentence) + 1 > args.max_chars and buf:
                    flush()
                buf = (buf + " " + sentence).strip()

    flush()

    for i, c in enumerate(chunks):
        c["clip"] = f"{args.prefix}{args.first_clip + i}"
        c["chars"] = len(c["text"])
        c["words"] = len(c["text"].split())

    total_w = sum(c["words"] for c in chunks)
    Path(args.out).write_text(json.dumps(chunks, indent=1, ensure_ascii=False),
                              encoding="utf-8")
    print(f"✓ {len(chunks)} chunks  ·  {total_w} words  ·  "
          f"≈{total_w / 141.5:.1f} min at the measured pace  → {args.out}")
    for c in chunks:
        print(f"  {c['clip']:>4}  ch {c['chapter']:<3} {c['chars']:>5} chars  "
              f"{c['words']:>4} w  {c['text'][:64]}…")


if __name__ == "__main__":
    main()
