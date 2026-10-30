"""Procedural animated background renderer (pure numpy, fast).

Renders soft "mesh gradient" blobs, floating dust, an audio waveform strip,
a progress bar and scene flashes into RGB24 frames at 540x960, which ffmpeg
upscales to 1080x1920.
"""
from __future__ import annotations

import math
import numpy as np

def hex2rgb(h: str) -> np.ndarray:
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], dtype=np.float32) / 255.0


PALETTES = {
    # cool tech look (style preview)
    "aurora": dict(
        stops=["03040A", "070A16", "05070F", "020309"],
        blobs=[(-0.55, -0.62, 0.80, 0.30, "312E81"), (0.62, -0.10, 0.66, 0.20, "155E75"),
               (0.10, 0.72, 0.92, 0.24, "4C1D95"), (-0.80, 0.55, 0.60, 0.14, "0E7490")],
        rings=["67E8F9", "A78BFA", "38BDF8"], dust="BFDBFE", ui=("22D3EE", "A78BFA"),
    ),
    # warm, cinematic look for the seerah story
    "seerah": dict(
        stops=["050506", "0C0B12", "0E0B07", "040404"],
        blobs=[(-0.55, -0.60, 0.82, 0.34, "5A3F1C"), (0.66, -0.06, 0.70, 0.22, "14524A"),
               (0.06, 0.74, 0.95, 0.26, "46290F"), (-0.82, 0.52, 0.62, 0.15, "1C3A46")],
        rings=["E9C27A", "8FD3C1", "C79A4B"], dust="F1E3C8", ui=("E9C27A", "8FD3C1"),
    ),
}


class Background:
    def __init__(self, w=540, h=960, fps=30, seed=7, palette="aurora"):
        self.w, self.h, self.fps = w, h, fps
        rng = np.random.default_rng(seed)

        # ---- normalised coordinate grids -------------------------------------
        self.xs = ((np.arange(w, dtype=np.float32) - w / 2) / (h / 2)).astype(np.float32)
        self.ys = ((np.arange(h, dtype=np.float32) - h / 2) / (h / 2)).astype(np.float32)

        # ---- base vertical gradient -----------------------------------------
        pal = PALETTES.get(palette, PALETTES["aurora"])
        self.pal = pal
        stops = [(0.0, hex2rgb(pal["stops"][0])), (0.45, hex2rgb(pal["stops"][1])),
                 (0.75, hex2rgb(pal["stops"][2])), (1.0, hex2rgb(pal["stops"][3]))]
        t = np.linspace(0, 1, h, dtype=np.float32)
        base = np.zeros((h, 3), dtype=np.float32)
        for (p0, c0), (p1, c1) in zip(stops, stops[1:]):
            m = (t >= p0) & (t <= p1)
            k = ((t[m] - p0) / (p1 - p0))[:, None]
            base[m] = c0 + (c1 - c0) * k
        self.base = np.repeat(base[:, None, :], w, axis=1)

        # ---- soft blobs (separable gaussians, almost free) -------------------
        motions = [(0.16, 0.10, 0.11, 0.09, 0.0), (0.13, 0.14, 0.08, 0.12, 1.7),
                   (0.11, 0.09, 0.09, 0.07, 3.1), (0.09, 0.12, 0.10, 0.08, 4.6)]
        self.blobs = []
        for (cx, cy, r, amp, col), (dx, dy, sx, sy, ph) in zip(pal["blobs"], motions):
            self.blobs.append(dict(cx=cx, cy=cy, r=r, amp=amp, col=hex2rgb(col),
                                   dx=dx, dy=dy, sx=sx, sy=sy, ph=ph))

        # ---- dust particles --------------------------------------------------
        n = 78
        self.dust = [dict(
            x=float(rng.uniform(0, w)), y=float(rng.uniform(0, h)),
            spd=float(rng.uniform(6, 26)), amp=float(rng.uniform(0.6, 2.6)),
            size=float(rng.uniform(1.1, 3.2)), a=float(rng.uniform(0.06, 0.30)),
            ph=float(rng.uniform(0, 6.28)),
        ) for _ in range(n)]

        # ---- vignette --------------------------------------------------------
        r = np.sqrt((self.xs[None, :] ** 2) * 0.65 + (self.ys[:, None] ** 2) * 0.55)
        self.vignette = (1.0 - 0.55 * np.clip(r, 0, 1.30) ** 1.6).astype(np.float32)[:, :, None]

        # ---- orbit rings (thin dashed arcs, cheap) ---------------------------
        self.rings = [
            dict(cx=0.00, cy=-0.30, R=0.34, thick=2.0, segs=5, spin=5.0, a=0.14, col=hex2rgb(pal["rings"][0])),
            dict(cx=0.00, cy=-0.30, R=0.47, thick=1.6, segs=8, spin=-3.6, a=0.10, col=hex2rgb(pal["rings"][1])),
            dict(cx=0.00, cy=-0.30, R=0.62, thick=1.2, segs=11, spin=2.6, a=0.07, col=hex2rgb(pal["rings"][2])),
        ]

        for ring in self.rings:
            rr = np.sqrt((self.xs[None, :] - ring["cx"]) ** 2 + (self.ys[:, None] - ring["cy"]) ** 2)
            ring["band"] = (np.abs(rr - ring["R"]) < (ring["thick"] / self.h)).astype(np.float32)
            ring["ang"] = np.arctan2(self.ys[:, None] - ring["cy"], self.xs[None, :] - ring["cx"])
            ring["step"] = 6.2831853 / ring["segs"]

        self.dust_col = hex2rgb(pal["dust"]) * 0.92 + 0.08

        self.frame_i = 0

    # ------------------------------------------------------------------ utils
    def _blob_layer(self, cx, cy, r):
        gx = np.exp(-((self.xs - cx) ** 2) / (r * r)).astype(np.float32)
        gy = np.exp(-((self.ys - cy) ** 2) / (r * r)).astype(np.float32)
        return gy[:, None] * gx[None, :]

    def _dot(self, img, px, py, size, color, alpha):
        h, w = self.h, self.w
        r = max(1, int(size * 1.6))
        x0, x1 = int(px) - r, int(px) + r + 1
        y0, y1 = int(py) - r, int(py) + r + 1
        if x1 <= 0 or y1 <= 0 or x0 >= w or y0 >= h:
            return
        cx0, cx1 = max(0, x0), min(w, x1)
        cy0, cy1 = max(0, y0), min(h, y1)
        ax = np.arange(cx0, cx1, dtype=np.float32) - px
        ay = np.arange(cy0, cy1, dtype=np.float32) - py
        g = np.exp(-(ay[:, None] ** 2 + ax[None, :] ** 2) / (size * size)).astype(np.float32)
        img[cy0:cy1, cx0:cx1] += (g * alpha)[:, :, None] * color

    # ------------------------------------------------------------------ frame
    def frame(self, t, envelope=None, progress=None, flash=0.0, dust_boost=1.0, fade=0.0):
        img = self.base.copy()

        for b in self.blobs:
            cx = b["cx"] + b["dx"] * math.sin(t * b["sx"] * 6.283 + b["ph"])
            cy = b["cy"] + b["dy"] * math.cos(t * b["sy"] * 6.283 + b["ph"] * 0.7)
            r = b["r"] * (1.0 + 0.06 * math.sin(t * 0.31 + b["ph"]))
            img += (self._blob_layer(cx, cy, r) * b["amp"])[:, :, None] * b["col"]

        # dust
        for p in self.dust:
            y = (p["y"] - t * p["spd"]) % (self.h + 40) - 20
            x = p["x"] + p["amp"] * 9 * math.sin(t * 0.55 + p["ph"])
            tw = 0.65 + 0.35 * math.sin(t * 1.7 + p["ph"] * 2.1)
            self._dot(img, x, y, p["size"], self.dust_col,
                      p["a"] * tw * 0.40 * dust_boost)

        # orbit arcs (centred in the upper third of the frame)
        for ring in self.rings:
            step = ring["step"]
            phase = (ring["ang"] + t * ring["spin"] * 0.08) % step
            m = ring["band"] * (phase < step * 0.33)
            img += (m * ring["a"])[:, :, None] * ring["col"]

        img *= self.vignette

        # ---- waveform strip ---------------------------------------------------
        if envelope is not None and len(envelope):
            ybase = self.h - 84
            bars, bw, gap = 40, 5, 4
            total = bars * (bw + gap)
            x_start = (self.w - total) // 2
            idx = np.linspace(0, len(envelope) - 1, bars).astype(int)
            colA = hex2rgb(self.pal["ui"][0]); colB = hex2rgb(self.pal["ui"][1])
            for i, k in enumerate(idx):
                v = float(envelope[k])
                hgt = int(3 + v * 34)
                x0 = x_start + i * (bw + gap)
                k2 = i / max(1, bars - 1)
                col = colA * (1 - k2) + colB * k2
                y0 = ybase - hgt
                img[y0:ybase, x0:x0 + bw] += col * (0.34 + 0.40 * v)

        # ---- progress bar ------------------------------------------------------
        if progress is not None:
            y = self.h - 34
            img[y:y + 2, 60:self.w - 60] += np.array([0.30, 0.34, 0.48], np.float32) * 0.55
            pw = int((self.w - 120) * max(0.0, min(1.0, progress)))
            if pw > 0:
                g = np.linspace(0, 1, pw, dtype=np.float32)[None, :, None]
                c0 = hex2rgb(self.pal["ui"][0]); c1 = hex2rgb(self.pal["ui"][1])
                img[y:y + 2, 60:60 + pw] += (c0 * (1 - g) + c1 * g) * 1.35

        if flash:
            img += flash * 0.055
        if fade:
            img *= max(0.0, 1.0 - fade)

        np.clip(img, 0, 1, out=img)
        self.frame_i += 1
        return (img * 255.0 + 0.5).astype(np.uint8)
