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
    R.background_grid(draw, step=64)

    for (x, y, dx, dy) in [(30, 30, 1, 1), (W - 30, 30, -1, 1), (30, H - 30, 1, -1), (W - 30, H - 30, -1, -1)]:
        draw.line([(x, y), (x + dx * 40, y)], fill=R.RED, width=3)
        draw.line([(x, y), (x, y + dy * 40)], fill=R.RED, width=3)

    # exhibit on the right, kept clear of the type column
    hero = R.cutout(R.render_path("renders", "t90m"), 980)
    hh = 430
    hw = int(hero.width * hh / hero.height)
    hero = hero.resize((hw, hh), Image.LANCZOS)
    hx, hy = W - hw - 18, 232
    R.studio_ground(draw, hx + hw // 2, hy + hh - 8, int(hw * 0.5))
    canvas.alpha_composite(hero, (hx, hy))

    f1 = R.font(R.F_SB, 92)
    R.tracked(draw, (52, 84), "EVERY", f1, R.INK, tracking=2)
    R.tracked(draw, (52, 176), "RUSSIAN", f1, R.RED, tracking=2)
    R.tracked(draw, (52, 268), "TANK", f1, R.RED, tracking=2)

    f2 = R.font(R.F_SB, 30)
    band_txt = "52 VEHICLES  ·  8 CATEGORIES"
    bw = R.text_width(draw, band_txt, f2, 2)
    draw.rectangle([0, 396, 52 + bw + 40, 462], fill=R.RED)
    R.tracked(draw, (52, 414), band_txt, f2, R.WHITE, tracking=2)

    f3 = R.font(R.F_SR, 25)
    R.tracked(draw, (52, 494), "TECHNICAL INVENTORY", f3, R.INK, tracking=3)
    f4 = R.font(R.F_SR, 17)
    R.tracked(draw, (52, 546), "IN ACTIVE SERVICE  ·  1947 — 2023", f4, R.GREY, tracking=2)

    f5 = R.font(R.F_BOLD, 20)
    R.tracked(draw, (W - 60, 46), "RUSSIAN ARMOR", f5, R.RED, tracking=3, anchor="ra")

    os.makedirs("output", exist_ok=True)
    canvas.convert("RGB").save("output/thumbnail.jpg", quality=92)
    print("wrote output/thumbnail.jpg")


if __name__ == "__main__":
    build()
