"""Subtitle export: turns the same content + timeline into .srt files.

Timing is derived from the narration audio: each chapter's sentences are
spread across the measured voiceover window, weighted by character count.
That keeps captions in lock-step even though the voiceover is a single clip.
"""
from __future__ import annotations

import re

MAX_CHARS = 92  # keep captions to two comfortable lines


def _sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?؟])\s+", " ".join(text.split()))
    out = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        while len(p) > MAX_CHARS * 2:
            cut = p.rfind(" ", 0, MAX_CHARS * 2)
            cut = cut if cut > 0 else MAX_CHARS * 2
            out.append(p[:cut].strip())
            p = p[cut:].strip()
        if len(p) > MAX_CHARS:
            # prefer a clause boundary near the limit (comma / semicolon)
            cut = max(
                (i for i in (p.rfind(", ", 0, MAX_CHARS + 1), p.rfind("; ", 0, MAX_CHARS + 1),
                             p.rfind("، ", 0, MAX_CHARS + 1)) if i > MAX_CHARS * 0.4),
                default=-1,
            )
            if cut > 0:
                out.append(p[: cut + 1].strip())
                p = p[cut + 1:].strip()
                if len(p) <= MAX_CHARS:
                    out.append(p)
                    continue
            words, line, chunks = p.split(), "", []
            for w in words:
                if len(line) + len(w) + 1 <= MAX_CHARS:
                    line = (line + " " + w).strip()
                else:
                    chunks.append(line)
                    line = w
            if line:
                chunks.append(line)
            out.extend(chunks)
        else:
            out.append(p)
    return out


def _tc(t: float) -> str:
    t = max(0.0, t)
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = int(t % 60)
    ms = int(round((t - int(t)) * 1000))
    if ms == 1000:
        s, ms = s + 1, 0
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def cues_for(segs, intro_text, intro_text_ar):
    """[(start, end, text)] for the whole film."""
    cues = []
    for seg in segs:
        if seg["kind"] in ("endcard", "hook"):
            continue          # the cold open carries no narration by design
        if seg["kind"] == "intro":
            body, body_ar = intro_text, intro_text_ar
        else:
            sec = seg["section"]
            body = sec["narration"]
            body_ar = sec.get("narration_ar", "")
        span = seg["vo"] if seg["vo"] > 0.5 else seg["dur"] - seg["vo_at"] - 1.2
        start = seg["start"] + seg["vo_at"]
        for text in (body, body_ar):
            if not text:
                continue
            sents = _sentences(text)
            total = sum(len(s) for s in sents) or 1
            t = start
            for s in sents:
                d = span * len(s) / total
                cues.append((t, min(t + d, start + span), s))
                t += d
    return cues


def write_srt(path: str, cues) -> str:
    with open(path, "w", encoding="utf-8") as f:
        for i, (a, b, text) in enumerate(cues, 1):
            f.write(f"{i}\n{_tc(a)} --> {_tc(b)}\n{text}\n\n")
    return path


def export(segs, out_dir: str, intro_text: str, intro_text_ar: str = "",
           stem: str = "hikka_gear_usa_vs_china") -> list[str]:
    """Write <name>.en.srt and <name>.ar.srt into out_dir."""
    import os

    os.makedirs(out_dir, exist_ok=True)
    cues = cues_for(segs, intro_text, intro_text_ar)
    en = [c for c in cues if not _is_arabic(c[2])]
    ar = [c for c in cues if _is_arabic(c[2])]
    made = []
    for name, subset in (("en", en), ("ar", ar)):
        if subset:
            made.append(write_srt(os.path.join(out_dir, f"{stem}.{name}.srt"),
                                  subset))
    return made


def _is_arabic(s: str) -> bool:
    return any("\u0600" <= ch <= "\u06ff" for ch in s)
