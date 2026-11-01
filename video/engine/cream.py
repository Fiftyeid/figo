"""The reference stage: warm cream cyc, perspective floor, hard sun shadow.

Measured off a frame of the source video (the Nimrod MRA4 scene, 845x425 crop):

    wall top      (227, 219, 205)     wall at horizon (232, 227, 212)
    floor horizon (241, 236, 221)     floor bottom    (238, 231, 216)
    badge red     (164,  38,  26)     airframe ~92 % of frame width
    wheels at ~0.70 H                 hard shadow thrown right, attached
    on-screen type: one small badge, nothing else

The floor matters as much as the aircraft: it is a wide-angle shot, so the tile
lines run to a vanishing point rather than sitting flat. Everything here is
built to that spec, so a frame from this module and a frame from the source
read as the same studio.
"""
from __future__ import annotations

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from . import config as C
from . import pixels as P

# --- measured palette ------------------------------------------------------
WALL_TOP = (224, 215, 198)
WALL_LOW = (231, 225, 209)
FLOOR_TOP = (243, 238, 224)
FLOOR_LOW = (234, 226, 209)
GRID_INK = (168, 156, 134)
BADGE_RED = (164, 38, 26)

HORIZON = 0.595          # of frame height
VANISH_X = 0.46          # vanishing point drifts left of centre, like the ref


class CreamStage:
    """Pre-rendered cream cyclorama: gradient wall, perspective tile floor."""

    def __init__(self, horizon: float = HORIZON, vx: float = VANISH_X):
        self.horizon = horizon
        self.vx = vx
        self.bg = self._build()

    # ---------------------------------------------------------------- wall
    def _build(self) -> Image.Image:
        w, h = C.W, C.H
        hy = int(h * self.horizon)
        ys = np.arange(h, dtype=np.float32)[:, None]

        wall = np.array(WALL_TOP, np.float32)
        wall_lo = np.array(WALL_LOW, np.float32)
        f_top = np.array(FLOOR_TOP, np.float32)
        f_low = np.array(FLOOR_LOW, np.float32)

        wallcol = wall + (wall_lo - wall) * (np.clip(ys / hy, 0, 1) ** 0.80)
        dn = np.clip((ys - hy) / max(1, h - hy), 0, 1)
        floorcol = f_top + (f_low - f_top) * (dn ** 0.70)

        # soft seam: the cyc curve, not a line
        t = np.clip((ys - (hy - 80)) / 170.0, 0, 1)
        t = t * t * (3 - 2 * t)
        img = wallcol * (1 - t) + floorcol * t
        img = np.repeat(img[:, None, :], w, axis=1)

        # light falling from the left, so the wall is never a flat field
        xs = np.arange(w, dtype=np.float32)[None, :] / w
        pool = np.clip(1 - ((xs - 0.42) / 0.62) ** 2, 0, 1) ** 1.6
        img = np.clip(img + (pool * 5.5)[..., None], 0, 255)

        base = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), "RGB")
        return self._vignette(Image.alpha_composite(
            base.convert("RGBA"), self._floor_grid(hy)).convert("RGB"))

    # ------------------------------------------------------------- floor grid
    def _floor_grid(self, hy: int) -> Image.Image:
        """One-point perspective: radial lines to a VP, depth lines compressed."""
        w, h = C.W, C.H
        grid = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        gd = ImageDraw.Draw(grid)
        vx = w * self.vx

        # lines running away from the camera
        step = 132
        for i in range(-26, 27):
            xb = vx + i * step
            gd.line([(vx + (xb - vx) * 0.015, hy), (vx + (xb - vx) * 3.1, h + 320)],
                    fill=GRID_INK + (34,), width=3)

        # lines across, packed toward the horizon
        d = 0.012
        k = 1.0
        while True:
            y = hy + (h - hy) * (d ** 1.42)
            if y > h + 6:
                break
            a = int(38 * min(1.0, d * 5.0))
            gd.line([(0, y), (w, y)], fill=GRID_INK + (a,), width=3)
            k *= 1.115
            d += 0.012 * k

        # nothing at all right at the seam
        fade = Image.new("L", (w, h), 0)
        fd = ImageDraw.Draw(fade)
        for yy in range(hy - 60, hy + 210):
            fd.line([(0, yy), (w, yy)],
                    fill=int(255 * C.clamp((yy - (hy - 60)) / 270.0) ** 1.4))
        fd.rectangle([0, hy + 210, w, h], fill=255)
        grid.putalpha(Image.composite(grid.split()[3], Image.new("L", (w, h), 0), fade))
        return grid

    # -------------------------------------------------------------- vignette
    def _vignette(self, im: Image.Image) -> Image.Image:
        w, h = im.size
        xx = np.arange(w, dtype=np.float32)[None, :] / w - 0.5
        yy = np.arange(h, dtype=np.float32)[:, None] / h - 0.5
        d = np.sqrt((xx * 0.90) ** 2 + (yy * 0.82) ** 2) / 0.70
        v = np.clip(1.0 - 0.13 * np.clip(d, 0, 1.4) ** 2.2, 0, 1)
        a = np.asarray(im).astype(np.float32) * v[..., None]
        return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "RGB")

    def frame(self) -> Image.Image:
        return self.bg.copy()


# ---------------------------------------------------------------- placement
def airframe(frame: Image.Image, path: str, cx: int, baseline: int,
             width: int, shadow_k: float = 0.62,
             max_height: int | None = None) -> tuple:
    """One airframe standing on the floor, with the reference's hard sun shadow.

    ``baseline`` is the ground line the wheels touch. The sprite's opaque bottom
    comes from its alpha channel, so changing asset cannot silently float it.
    """
    spr = P.cutout(path)
    spr = spr.crop(spr.split()[3].getbbox())        # strip the 6 px matte border
    # fit the box, not just the width: a tall asset (a helicopter on skids)
    # must not lose its rotor to the top edge
    scale = width / spr.width
    if max_height and spr.height * scale > max_height:
        scale = max_height / spr.height
    spr = spr.resize((max(1, int(spr.width * scale)), max(1, int(spr.height * scale))),
                     Image.LANCZOS)

    x = int(cx - spr.width / 2)
    y = int(baseline - spr.height)
    alpha = spr.split()[3]

    # a wide, low, hard shadow that starts under the wheels and dies out right
    band = alpha.crop((0, alpha.height - max(8, int(alpha.height * 0.11)),
                       alpha.width, alpha.height))
    sh_h = max(10, int(spr.height * 0.075))
    sh = band.resize((spr.width, sh_h), Image.LANCZOS)
    pad_r = int(spr.width * 0.55)
    canvas = Image.new("L", (spr.width + pad_r, sh_h), 0)
    for yy in range(sh_h):
        shift = int((1 - yy / max(1, sh_h - 1)) * pad_r * 0.55)
        canvas.paste(sh.crop((0, yy, spr.width, yy + 1)), (shift, yy))
    fade = Image.new("L", canvas.size, 0)
    fd = ImageDraw.Draw(fade)
    for xx in range(canvas.width):
        fd.line([(xx, 0), (xx, canvas.height)],
                fill=int(255 * max(0.0, 1.0 - (xx / canvas.width) ** 1.35)))
    canvas = Image.composite(canvas, Image.new("L", canvas.size, 0), fade)
    canvas = canvas.filter(ImageFilter.GaussianBlur(2.4)).point(lambda v: int(v * shadow_k))
    frame.paste(Image.new("RGBA", canvas.size, (118, 106, 88, 255)),
                (x, baseline - sh_h + 4), canvas)

    frame.paste(spr.convert("RGB"), (x, y), alpha)
    return x, y, x + spr.width, y + spr.height


# ---------------------------------------------------------------- chrome
def year_badge(frame: Image.Image, text: str, x: int = 30, y: int = 22,
               size: int = 30, pad_x: int = 11, pad_y: int = 4) -> tuple:
    """The one piece of on-screen type in the reference: a small red badge."""
    probe = P.text_img(text, "bold", size, (255, 255, 255), 1.6)
    tw = probe.width - 8
    th = int(size * 0.80)
    d = ImageDraw.Draw(frame, "RGBA")
    d.rectangle([x, y, x + tw + pad_x * 2, y + th + pad_y * 2], fill=BADGE_RED + (255,))
    P.draw_text(frame, (x + pad_x, y + pad_y - int(size * 0.14)), text, "bold", size,
                (255, 255, 255), tracking=1.6, anchor="lt")
    return x, y, x + tw + pad_x * 2, y + th + pad_y * 2
