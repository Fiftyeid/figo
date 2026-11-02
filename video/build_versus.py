#!/usr/bin/env python3
"""USAF vs PLAAF 2026 — rendered on the first film's engine, unchanged.

The soldier comparison, the Japan chapter film and this one share one renderer
family: the showroom cyc, the split-screen duel, the metric bars, the two-tone
headline, the flag chips and the corner credits. The only thing that changes
is the content table — that is the point of the engine, and it is why this
film should look like it came off the same channel as EP.02.

    python3 video/build_versus.py --poster intro
    python3 video/build_versus.py --still 40
    python3 video/build_versus.py                # full render

Narration clips live in audio/vo_vs/ (intro.mp3, 01..09, end.mp3).
"""
from __future__ import annotations

import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import build as B                                                  # noqa: E402
from engine import config as C                                     # noqa: E402
from engine import subs                                            # noqa: E402
from engine.scenes import Renderer                                 # noqa: E402
from content_versus import META_VS, SECTIONS_VS, SIDES_VS          # noqa: E402

ROOT = os.path.dirname(HERE)

INTRO = (
    "Two of the most powerful air forces on earth, built on completely different ideas. "
    "One flies fewer, older, more expensive aircraft. The other is building faster than "
    "anyone has since the Cold War. Here is every fighter that matters in 2026, compared "
    "one by one."
)
END = "Same sky. Two answers. And ten years to find out which one was right."


class VersusRenderer(Renderer):
    """The EP.02 renderer with a different title card and a different pair.

    Aircraft are much wider than rifles, so the duel box is squashed and the
    name/pill columns are pulled up the frame — same furniture, proportions
    retuned for a 3:1 subject.
    """

    def __init__(self, sections, intro_narration, assets_dir, timeline, total_duration):
        super().__init__(sections, intro_narration, assets_dir, timeline, total_duration,
                         meta=META_VS, sides=SIDES_VS)

    def scene_duel(self, f, sec, local, box=(520, 212), baseline=482, name_y=536,
                   pill_y=592, cx_off=470):
        return Renderer.scene_duel(self, f, sec, local, box=box, baseline=baseline,
                                   name_y=name_y, pill_y=pill_y, cx_off=cx_off)

    def pill_times(self, dur=None):
        """Every spec pill lands inside the first two seconds of the shot.

        The rifle film can afford to stagger them across six seconds; an
        aircraft shot that only holds for five would show an empty column on
        the right of the frame for most of its life.
        """
        dur = dur if dur is not None else (self._seg_dur or 8.0)
        return (0.55, max(1.10, dur * 0.22), max(1.70, dur * 0.34))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vo", default=os.path.join(ROOT, "audio", "vo_vs"))
    ap.add_argument("--assets", default=os.path.join(ROOT, "assets"))
    ap.add_argument("--out", default=os.path.join(ROOT, "deliverables",
                                                  "hikka_usaf_vs_plaaf_2026.mp4"))
    ap.add_argument("--still", type=float, default=None)
    ap.add_argument("--poster", default="")
    ap.add_argument("--draft", action="store_true")
    ap.add_argument("--audio-only", action="store_true")
    ap.add_argument("--no-subs", action="store_true")
    args = ap.parse_args()

    segs, total = B.build_timeline(args.vo, None, SECTIONS_VS)
    os.makedirs(os.path.join(ROOT, "build"), exist_ok=True)
    print(f"  timeline: {len(segs)} segments, {total/60:.1f} min")

    if args.still is not None:
        r = VersusRenderer(SECTIONS_VS, INTRO, args.assets, segs, total)
        t, seg = args.still, segs[-1]
        for s in segs:
            if s["start"] <= t < s["start"] + s["dur"]:
                seg = s
                break
        local = t - seg["start"]
        f = r.stage.frame()
        r._global_t, r._seg_dur = t, seg["dur"]
        if seg["kind"] == "intro":
            f = r.draw_intro(f, local, seg["dur"]) or f
        elif seg["kind"] == "endcard":
            r.draw_endcard(f, local)
        else:
            f = r.draw_section(f, seg["section"], local, 1) or f
        out = os.path.join(ROOT, "build", "vs_still.png")
        f.save(out)
        print("  ", out)
        return

    if args.poster:
        B.poster(segs, total, args.assets, args.poster,
                 os.path.join(ROOT, "deliverables", f"poster_vs_{args.poster}.png"),
                 sections=SECTIONS_VS, renderer_cls=VersusRenderer, intro_narration=INTRO)
        print("  poster written")
        return

    mix_path = os.path.join(ROOT, "build", "mix_vs.wav")
    B.mix_audio(segs, total, args.vo, mix_path)
    print("  audio mixed")

    if not args.no_subs:
        for m in subs.export(segs, os.path.join(ROOT, "deliverables"), INTRO, END,
                             stem="hikka_usaf_vs_plaaf_2026"):
            print("  subs ->", m)

    if args.audio_only:
        return

    w, h = (960, 540) if args.draft else (C.W, C.H)
    B.render(segs, total, args.assets, args.out, w, h, C.FPS,
             sections=SECTIONS_VS, renderer_cls=VersusRenderer,
             intro_narration=INTRO, mix_path=mix_path)


if __name__ == "__main__":
    main()
