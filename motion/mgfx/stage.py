"""Compositing stage: procedural background + transformed alpha sprites."""
from __future__ import annotations

import numpy as np
from PIL import Image, ImageFilter

from .background import Background, hex2rgb

W, H = 1080, 1920
BW, BH = 540, 960

MOODS = {
    "calm":   dict(tint=(1.00, 1.00, 1.00), gain=1.00, streak=0.0, sat=1.00),
    "warm":   dict(tint=(1.10, 1.02, 0.92), gain=1.06, streak=0.0, sat=1.05),
    "pray":   dict(tint=(1.04, 1.06, 0.98), gain=1.10, streak=0.0, sat=0.95),
    "battle": dict(tint=(1.12, 0.92, 0.86), gain=1.14, streak=1.0, sat=1.10),
    "dark":   dict(tint=(0.86, 0.88, 0.98), gain=0.92, streak=0.0, sat=0.90),
    "end":    dict(tint=(1.02, 1.00, 0.96), gain=0.96, streak=0.0, sat=0.98),
}


class Stage:
    def __init__(self, palette: str = "seerah", seed: int = 7):
        self.bg = Background(w=BW, h=BH, palette=palette, seed=seed)
        rng = np.random.default_rng(seed + 3)
        # pre-computed streak texture for battle beats
        tex = np.zeros((BH, BW), np.float32)
        for _ in range(70):
            y = int(rng.uniform(0, BH))
            x = int(rng.uniform(0, BW))
            ln = int(rng.uniform(40, 220))
            a = float(rng.uniform(0.05, 0.20))
            thick = int(rng.integers(1, 3))
            tex[y:y + thick, x:x + ln] = np.maximum(tex[y:y + thick, x:x + ln], a)
        tex = np.asarray(Image.fromarray((tex * 255).astype(np.uint8)).filter(
            ImageFilter.GaussianBlur(2.2)), np.float32) / 255.0
        self.streaks = tex

    # -------------------------------------------------------------- background
    def background(self, t, env=None, progress=None, mood="calm", flash=0.0,
                   fade=0.0, zoom=1.0) -> np.ndarray:
        m = MOODS.get(mood, MOODS["calm"])
        small = self.bg.frame(t, envelope=env, progress=progress, flash=flash, fade=fade)
        img = Image.fromarray(small)
        if zoom != 1.0:
            zw, zh = int(BW * zoom), int(BH * zoom)
            img = img.resize((zw, zh), Image.BILINEAR)
            left = (zw - BW) // 2
            top = (zh - BH) // 2
            img = img.crop((left, top, left + BW, top + BH))
        img = img.resize((W, H), Image.BICUBIC)
        canvas = np.asarray(img, dtype=np.float32) / 255.0
        canvas *= np.array(m["tint"], np.float32) * m["gain"]

        if m["streak"] > 0.05:
            st = np.roll(self.streaks, int(t * 210) % BW, axis=1)
            st = np.asarray(Image.fromarray((st * 255).astype(np.uint8)).resize(
                (W, H), Image.BILINEAR), np.float32) / 255.0
            canvas += st[:, :, None] * np.array([0.60, 0.26, 0.14], np.float32) * m["streak"] * 0.8
        return canvas

    # ------------------------------------------------------------------ sprite
    @staticmethod
    def paste(canvas: np.ndarray, mask: np.ndarray, cx: float, cy: float,
              scale: float = 1.0, rot: float = 0.0, alpha: float = 1.0,
              color=(1.0, 1.0, 1.0), blur: float = 0.0, glow: float = 0.0):
        if alpha <= 0.003 or scale <= 0.02 or mask is None or mask.size == 0:
            return
        if isinstance(color, str):
            color = hex2rgb(color)
        h, w = mask.shape
        u8 = (np.clip(mask, 0, 1) * 255).astype(np.uint8)
        img = Image.fromarray(u8, "L")
        if scale != 1.0:
            nw, nh = max(1, int(round(w * scale))), max(1, int(round(h * scale)))
            img = img.resize((nw, nh), Image.BILINEAR)
        if abs(rot) > 0.2:
            img = img.rotate(rot, expand=True, resample=Image.BICUBIC)
        if blur > 0.4:
            img = img.filter(ImageFilter.GaussianBlur(blur))
        a = np.asarray(img, dtype=np.float32) / 255.0
        if alpha < 0.999:
            a *= alpha

        hh, ww = a.shape
        x0 = int(round(cx - ww / 2))
        y0 = int(round(cy - hh / 2))
        x1, y1 = x0 + ww, y0 + hh
        cx0, cy0 = max(0, x0), max(0, y0)
        cx1, cy1 = min(W, x1), min(H, y1)
        if cx1 <= cx0 or cy1 <= cy0:
            return
        a = a[cy0 - y0:cy1 - y0, cx0 - x0:cx1 - x0]
        col = np.array(color, np.float32)

        if glow > 0.01:
            rad = max(6, int(14 * scale))
            pad = rad * 2
            ap = np.pad(a, pad)
            g = Image.fromarray((ap * 255).astype(np.uint8), "L").filter(
                ImageFilter.GaussianBlur(rad))
            ga = np.asarray(g, dtype=np.float32) / 255.0 * glow
            gy0, gx0 = cy0 - pad, cx0 - pad
            gy1, gx1 = gy0 + ga.shape[0], gx0 + ga.shape[1]
            sy0, sx0 = max(0, -gy0), max(0, -gx0)
            gy0, gx0 = max(0, gy0), max(0, gx0)
            gy1, gx1 = min(H, gy1), min(W, gx1)
            if gy1 > gy0 and gx1 > gx0:
                ga = ga[sy0:sy0 + (gy1 - gy0), sx0:sx0 + (gx1 - gx0)]
                canvas[gy0:gy1, gx0:gx1] += ga[:, :, None] * np.clip(col * 0.9, 0, 1)

        canvas[cy0:cy1, cx0:cx1] = (canvas[cy0:cy1, cx0:cx1] * (1 - a[:, :, None])
                                    + col * a[:, :, None])

    @staticmethod
    def rect(canvas, x0, y0, x1, y1, color, alpha=1.0, radius=0):
        x0, y0, x1, y1 = int(round(x0)), int(round(y0)), int(round(x1)), int(round(y1))
        x1 = max(x1, x0 + 1); y1 = max(y1, y0 + 1)
        x0c, y0c = max(0, x0), max(0, y0)
        x1c, y1c = min(W, x1), min(H, y1)
        if x1c <= x0c or y1c <= y0c:
            return
        col = hex2rgb(color) if isinstance(color, str) else np.array(color, np.float32)
        hh, ww = y1 - y0, x1 - x0
        if radius <= 0:
            canvas[y0c:y1c, x0c:x1c] = canvas[y0c:y1c, x0c:x1c] * (1 - alpha) + col * alpha
            return
        r = float(min(radius, ww / 2.0, hh / 2.0))
        yy, xx = np.mgrid[0:hh, 0:ww].astype(np.float32)
        dx = np.maximum(np.maximum(r - xx, xx - (ww - 1 - r)), 0.0)
        dy = np.maximum(np.maximum(r - yy, yy - (hh - 1 - r)), 0.0)
        inside = (dx * dx + dy * dy) <= (r * r)
        # anti-alias the edge a little
        sd = np.sqrt(dx * dx + dy * dy) - r
        m = np.clip(0.5 - sd, 0.0, 1.0).astype(np.float32)
        m[~((xx >= 0) & (yy >= 0))] = 0.0
        m = m[y0c - y0:y1c - y0, x0c - x0:x1c - x0][:, :, None] * alpha
        reg = canvas[y0c:y1c, x0c:x1c]
        canvas[y0c:y1c, x0c:x1c] = reg * (1 - m) + col * m

    @staticmethod
    def ring(canvas, cx, cy, radius, thickness, color, alpha=1.0, a0=-90.0, a1=270.0):
        """Arc / ring stroke (angles in degrees, 0 = up, clockwise)."""
        r = float(radius)
        x0 = max(0, int(cx - r - thickness - 2)); x1 = min(W, int(cx + r + thickness + 3))
        y0 = max(0, int(cy - r - thickness - 2)); y1 = min(H, int(cy + r + thickness + 3))
        if x1 <= x0 or y1 <= y0:
            return
        yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
        dx, dy = xx - cx, yy - cy
        d = np.sqrt(dx * dx + dy * dy)
        ang = (np.degrees(np.arctan2(dx, -dy))) % 360.0
        if a1 - a0 >= 359.5:
            mask = np.ones_like(d)
        else:
            lo, hi = a0 % 360.0, a1 % 360.0
            mask = ((ang - lo) % 360.0 <= ((a1 - a0) % 360.0)).astype(np.float32)
        edge = np.clip(thickness / 2.0 + 0.5 - np.abs(d - r), 0.0, 1.0)
        m = (mask * edge * alpha)[:, :, None]
        col = hex2rgb(color) if isinstance(color, str) else np.array(color, np.float32)
        reg = canvas[y0:y1, x0:x1]
        canvas[y0:y1, x0:x1] = reg * (1 - m) + col * m

    @staticmethod
    def finish(canvas: np.ndarray) -> np.ndarray:
        np.clip(canvas, 0, 1, out=canvas)
        return (canvas * 255.0 + 0.5).astype(np.uint8)


def C(hexstr: str):
    return tuple(hex2rgb(hexstr))
