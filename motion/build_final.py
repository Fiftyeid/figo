"""Render «قصّة جليبيب» — vertical 1080x1920 motion graphics over the voiceover.

    python build_final.py                 # full render -> deliver/final.mp4
    python build_final.py --still 60      # single PNG at t=60s for QC
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import storyboard as sb  # noqa: E402
from mgfx.assgen import Ass, c  # noqa: E402
from mgfx.render import render  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
PALETTE = dict(accent="E9C27A", accent2="8FD3C1", muted="CFC3AF", ivory="F5EFE6", gold="E9C27A")
CAP_Y = 1180


def salawat(text: str, font: str = "Cairo Bold") -> str:
    """ﷺ is handled by assgen (Amiri fallback); kept for readability at call sites."""
    return text


def split_parts(text: str):
    """'a… b' -> ['a', 'b'] ; long halves are split once more at a word edge."""
    return [p.strip() for p in text.split("…") if p.strip()]


def caption_block(a: Ass, t0: float, t1: float, text: str):
    parts = split_parts(text)
    weights = [len(p) + 4 for p in parts]
    total = sum(weights)
    cur = t0
    for p, w in zip(parts, weights):
        seg = (t1 - t0) * w / total
        size = 92 if len(p) <= 24 else (84 if len(p) <= 34 else (76 if len(p) <= 46 else 68))
        a.line(cur + 0.02, cur + seg, salawat(p), y=CAP_Y, style="Cap",
               rise=24, blur=14, scale=95, dur=0.26, extra=f"\\fs{size}")
        cur += seg


def title_card(a: Ass):
    t = sb.TITLE
    t0, t1 = t["t0"], t["t1"]
    a.line(t0, t1, t["kicker"], y=700, style="Kicker", rise=26, blur=14)
    a.line(t0 + 0.18, t1, t["main"], y=860, style="Title")
    a.rule(t0 + 0.45, t1, y=1000, width=340, color="E9C27A", thick=6)
    a.line(t0 + 0.60, t1, t["sub"], y=1090, style="Body", rise=28, blur=16,
           extra="\\fs54")


def card(a: Ass, card: dict):
    t0, t1 = card["t0"], card["t1"]
    kind = card["kind"]
    if kind == "dua":
        a.card(t0, t1 - 0.05, cy=960, wpx=880, hpx=560, delay=0.05, fill="120E08", edge="C79A4B")
        a.line(t0 + 0.06, t1, card["label"], y=790, style="Chap", rise=18, blur=10)
        a.line(t0 + 0.18, t1, salawat(card["text"], "Dua"), y=975, style="Dua",
               rise=30, blur=18)
        a.rule(t0 + 0.30, t1, y=1185, width=300, color="C79A4B", thick=5)
    elif kind == "quote":
        a.card(t0, t1 - 0.05, cy=940, wpx=880, hpx=470, delay=0.05, fill="140F07", edge="E9C27A")
        a.line(t0 + 0.06, t1, card["label"], y=800, style="Chap", rise=18, blur=10)
        a.line(t0 + 0.16, t1, card["text"], y=960, style="Quote", rise=34, blur=22)
        a.rule(t0 + 0.28, t1, y=1090, width=280, color="E9C27A", thick=5)
    elif kind == "end":
        a.line(t0 + 0.05, t1, card["label"], y=850, style="Kicker", rise=20, blur=12)
        a.line(t0 + 0.20, t1, card["text"], y=1010, style="Body", rise=28, blur=16,
               extra="\\fs66")
        a.rule(t0 + 0.40, t1, y=1160, width=300, color="E9C27A", thick=5)
        a.line(t0 + 0.55, t1, "FIGO  ·  MOTION", y=1240, style="Small", rise=16, blur=8)


def chapters(a: Ass):
    numerals = ["١", "٢", "٣", "٤"]
    for i, (t, label) in enumerate(sb.CHAPTERS):
        nxt = sb.CHAPTERS[i + 1][0] if i + 1 < len(sb.CHAPTERS) else sb.DURATION - 1.5
        t0 = max(3.45, t) if i == 0 else max(0.0, t)
        end = min(nxt, 176.6) if i == len(sb.CHAPTERS) - 1 else nxt
        a.line(t0, end, label, y=235, style="Chap", rise=14, blur=8, dur=0.5, scale=98)
        a.star(t0, end, cx=540, cy=770, R=268, color="C79A4B", thick=2,
               alpha="&HDD&", spin=70.0)
    a.line(4.2, 176.4, "قصّة جليبيب", y=150, style="Chap", rise=8, blur=6, dur=0.8,
           scale=100, extra="\\fs30\\alpha&H60&")


def build_ass(path: str):
    a = Ass(palette=PALETTE)
    title_card(a)
    chapters(a)
    for t0, t1, text in sb.BLOCKS:
        caption_block(a, t0, t1, text)
    for carddef in sb.CARDS:
        card(a, carddef)
    return a.write(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--audio", default=os.path.join(HERE, "media", "voice.mp3"))
    ap.add_argument("--out", default=os.path.join(HERE, "deliver", "final.mp4"))
    ap.add_argument("--crf", type=int, default=19)
    ap.add_argument("--still", type=float, default=None)
    args = ap.parse_args()

    ass = build_ass(os.path.join(HERE, "deliver", "final.ass"))

    if args.still is not None:
        from PIL import Image
        from mgfx.background import Background
        bg = Background(palette="seerah")
        from mgfx.render import audio_envelope
        n = int(sb.DURATION * 30)
        env = audio_envelope(args.audio, n, 30)
        i = int(args.still * 30)
        fr = bg.frame(args.still, envelope=env, progress=i / n)
        Image.fromarray(fr).save("/tmp/still_bg.png")
        print("bg still -> /tmp/still_bg.png (burn .ass separately for text)")
        return

    def flags(t, total):
        fade = 0.0
        if t < 0.7:
            fade = 1.0 - t / 0.7
        if total - t < 1.0:
            fade = max(fade, min(1.0, (1.0 - (total - t))))
        f = 0.0
        for cd in sb.CARDS:
            d = abs(t - cd["t0"])
            if d < 0.3:
                f += (1 - d / 0.3) ** 2 * 0.55
        for t0, _t1, _txt in sb.BLOCKS:
            d = abs(t - t0)
            if d < 0.10:
                f += (1 - d / 0.10) * 0.12
        return {"flash": f, "fade": fade * 0.9}

    render(args.out, sb.DURATION, ass, audio=args.audio, flags=flags,
           palette="seerah", crf=args.crf)
    print("wrote", args.out, round(os.path.getsize(args.out) / 1048576, 1), "MB")


if __name__ == "__main__":
    main()
