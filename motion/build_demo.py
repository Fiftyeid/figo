"""Style preview: a 15.5s, 1080x1920 (9:16) motion-graphics demo, silent.

It shows the four building blocks used in the real build:
  1. statement card          - big kinetic typography
  2. caption stream          - the word-synced subtitle system
  3. feature chips           - glass panel + pills
  4. outro card              - call to action

    python build_demo.py    ->  out/style_preview.mp4
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mgfx.assgen import Ass, CYAN, GOLD, VIOLET, WHITE  # noqa: E402
from mgfx.render import render  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DUR = 15.5
EDGES = (3.25, 6.95, 11.35)


def build_ass() -> Ass:
    a = Ass()

    # ---------------- 1. statement -----------------------------------------
    a.line(0.25, 3.20, "موشن جرافيك عربي", y=640, style="Kicker", rise=28, blur=18)
    a.line(0.45, 3.20, "من الصوت", y=800, style="Title")
    a.line(0.75, 3.20, "إلى الشاشة", y=975, style="Accent")
    a.rule(1.05, 3.20, y=1105, width=360)
    a.line(1.25, 3.20, "تايبوجرافي متزامن مع كل كلمة", y=1210, style="Body",
           rise=34, blur=20)

    # ---------------- 2. caption stream (the real product) ------------------
    a.line(3.40, 4.75, "بأخد الصوت بتاعك", y=1290, style="Body", extra="\\fs76")
    a.line(4.75, 6.05, "وأحوّله فيديو", y=1290, style="Body", extra="\\fs76")
    a.line(6.05, 6.90, "متزامن كلمة بكلمة", y=1290, style="Body",
           extra=f"\\fs76\\1c{CYAN}")
    a.rule(3.45, 6.90, y=1395, width=520, color=CYAN, thick=5, grow=0.45)
    a.line(3.55, 6.90, "CAPTIONS  ·  30 FPS", y=1465, style="Small", rise=18, blur=10)

    # ---------------- 3. feature chips -------------------------------------
    a.line(7.10, 11.30, "تلات حاجات بتصنع الفرق", y=700, style="Title", extra="\\fs96")
    a.card(7.30, 11.30, cy=1035, wpx=780, hpx=480, delay=0.15)
    a.pill(7.55, 11.30, "إيقاع", cx=540, cy=900, color=VIOLET)
    a.pill(7.80, 11.30, "حركة", cx=540, cy=1040, color=CYAN)
    a.pill(8.05, 11.30, "هوية", cx=540, cy=1180, color=GOLD)

    # ---------------- 4. outro ---------------------------------------------
    a.card(11.45, DUR - 0.02, cy=1030, wpx=860, hpx=470, delay=0.1, edge="A78BFA")
    a.line(11.55, DUR - 0.05, "يلا نبدأ", y=900, style="Accent", scale=80, rise=60)
    a.line(11.95, DUR - 0.05, "ارفع الملف الصوتي… والباقي عليّا", y=1050,
           style="Body", extra="\\fs56")
    a.line(12.35, DUR - 0.05, "FIGO  ·  MOTION", y=1170, style="Small",
           rise=20, blur=12)
    return a


def main():
    ass = build_ass().write(os.path.join(HERE, "out", "demo.ass"))

    def flags(t, total):
        f = 0.0
        for edge in EDGES:
            d = abs(t - edge)
            if d < 0.28:
                f += (1 - d / 0.28) ** 2 * 0.95
        return {"flash": f}

    out = os.path.join(HERE, "out", "style_preview.mp4")
    render(out, DUR, ass, audio=None, flags=flags)
    print("wrote", out, os.path.getsize(out) // 1024, "KB")


if __name__ == "__main__":
    main()
