"""YouTube thumbnail, same design system as the film."""
import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import render as R  # noqa: E402

W, H = 1280, 720


def build():
    canvas = Image.new("RGBA", (W, H), R.WHITE + (255,))
    draw = ImageDraw.Draw(canvas)

    for (x, y, dx, dy) in [(30, 30, 1, 1), (W - 30, 30, -1, 1), (30, H - 30, 1, -1), (W - 30, H - 30, -1, -1)]:
        draw.line([(x, y), (x + dx * 40, y)], fill=R.RED, width=3)
        draw.line([(x, y), (x, y + dy * 40)], fill=R.RED, width=3)

    hero = R.cutout(R.render_path("renders", "t90m"), 980)
    hh = 470
    hw = int(hero.width * hh / hero.height)
    hero = hero.resize((hw, hh), Image.LANCZOS)
    canvas.alpha_composite(hero, (W - hw - 20, 190))

    f1 = R.font(R.F_BOLD, 96)
    R.tracked(draw, (52, 96), "EVERY", f1, R.INK, tracking=2)
    R.tracked(draw, (52, 196), "RUSSIAN", f1, R.RED, tracking=2)
    R.tracked(draw, (52, 296), "TANK", f1, R.RED, tracking=2)

    draw.rectangle([0, 430, 706, 522], fill=R.RED)
    f2 = R.font(R.F_BOLD, 34)
    R.tracked(draw, (52, 458), "52 VEHICLES  ·  8 CATEGORIES", f2, R.WHITE, tracking=2)

    f3 = R.font(R.F_BOLD, 26)
    R.tracked(draw, (52, 548), "TECHNICAL INVENTORY", f3, R.INK, tracking=6)
    f4 = R.font(R.F_BOLD, 18)
    R.tracked(draw, (52, 596), "IN ACTIVE SERVICE  ·  1947 — 2023", f4, R.GREY, tracking=3)

    f5 = R.font(R.F_BOLD, 22)
    R.tracked(draw, (W - 60, 44), "RUSSIAN ARMOR", f5, R.RED, tracking=3, anchor="ra")

    os.makedirs("output", exist_ok=True)
    canvas.convert("RGB").save("output/thumbnail.jpg", quality=92)
    print("wrote output/thumbnail.jpg")


if __name__ == "__main__":
    build()
