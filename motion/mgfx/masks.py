"""Text & icon sprites.

Arabic text is shaped by libass (HarfBuzz + FriBidi) and returned as a cropped
alpha mask, which the compositor can then move/scale/blur/tint per frame — the
best of both worlds: correct Arabic typography + real motion design.
"""
from __future__ import annotations

import hashlib
import os
import subprocess

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS = os.path.join(HERE, "fonts")
ICON_TTF = os.path.join(FONTS, "MaterialSymbols-Rounded.ttf")

_HEAD = """[Script Info]
ScriptType: v4.00+
PlayResX: {w}
PlayResY: {h}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: T,{font},{size},&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,5,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,0:00:00.10,T,,0,0,0,,{{\\an5\\pos({cx},{cy})}}{body}
"""


def ffmpeg_bin() -> str:
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"


def sanitize(text: str) -> str:
    """Map punctuation the bundled fonts lack onto glyphs they do have."""
    text = text.replace("\u2026", "\u060C")      # … -> ،
    text = text.replace("\u00b7", "-").replace("\u2022", "-")
    text = text.replace("\u00ab", "").replace("\u00bb", "")   # drop « »
    text = text.replace("\u2013", "-").replace("\u2014", "-")
    while "  " in text:
        text = text.replace("  ", " ")
    return text.strip()


def _crop(a: np.ndarray, pad: int = 3, thr: float = 0.20):
    ys, xs = np.where(a > thr)
    if len(ys) == 0:
        return a, 0, 0
    y0, y1 = max(0, ys.min() - pad), min(a.shape[0], ys.max() + 1 + pad)
    x0, x1 = max(0, xs.min() - pad), min(a.shape[1], xs.max() + 1 + pad)
    return a[y0:y1, x0:x1], x0, y0


class Sprites:
    """Renders and caches alpha masks for Arabic text runs and icon glyphs."""

    def __init__(self, cachedir: str | None = None):
        self.cachedir = cachedir or os.path.join(HERE, "media", "cache")
        os.makedirs(self.cachedir, exist_ok=True)
        self.mem: dict[str, np.ndarray] = {}
        self._icons: dict[tuple, np.ndarray] = {}

    # ---------------------------------------------------------------- text
    def text(self, body: str, size: int, font: str = "Cairo ExtraBold") -> np.ndarray:
        body = sanitize(body)
        key = hashlib.sha1(f"{body}|{size}|{font}".encode()).hexdigest()[:16]
        if key in self.mem:
            return self.mem[key]
        png = os.path.join(self.cachedir, f"t_{key}.png")
        if not os.path.exists(png):
            body = body.replace("ﷺ", "{\\fnAmiri Bold}ﷺ{\\fn" + font + "}")
            n = max(len(body), 6)
            w = min(4200, int(0.62 * size * n) + 500)
            lines = body.count("\\N") + 1
            h = int(size * 2.7 * lines)
            cx, cy = w // 2, h // 2
            ass = os.path.join(self.cachedir, f"t_{key}.ass")
            with open(ass, "w", encoding="utf-8") as f:
                f.write(_HEAD.format(w=w, h=h, font=font, size=size, cx=cx, cy=cy, body=body))
            subprocess.run([ffmpeg_bin(), "-v", "error", "-y", "-f", "lavfi",
                            "-i", f"color=c=black:s={w}x{h}:d=0.12",
                            "-vf", f"ass={ass}:fontsdir={FONTS},format=gray",
                            "-frames:v", "1", "-update", "1", png], check=True)
        arr = np.asarray(Image.open(png).convert("L"), dtype=np.float32) / 255.0
        # ffmpeg gray output is limited-range: black=16/255, white=235/255
        arr = np.clip((arr - 0.0627) / 0.8588, 0.0, 1.0)
        arr, _x, _y = _crop(arr)
        self.mem[key] = arr
        return arr

    # ---------------------------------------------------------------- icons
    def icon(self, name: str, size: int = 160) -> np.ndarray:
        from .icons import codepoint
        key = (name, size)
        if key in self._icons:
            return self._icons[key]
        cp = codepoint(name)
        if cp is None:
            arr = np.zeros((8, 8), np.float32)
            self._icons[key] = arr
            return arr
        font = ImageFont.truetype(ICON_TTF, size)
        canvas = Image.new("L", (size * 2, size * 2), 0)
        d = ImageDraw.Draw(canvas)
        d.text((size // 2, size // 2), chr(cp), font=font, fill=255)
        arr = np.asarray(canvas, dtype=np.float32) / 255.0
        arr, _x, _y = _crop(arr, thr=0.12)
        self._icons[key] = arr
        return arr

    # ---------------------------------------------------------------- layout
    def layout(self, words, size, font="Cairo ExtraBold", max_width=920,
               gap=0.24, line_gap=1.16):
        """RTL word layout. Returns list of dicts with sprite + centre position,
        relative to the block's centre (0,0)."""
        sprites = [self.text(w, size, font) for w in words]
        rows, cur, cur_w = [], [], 0.0
        space = size * gap
        for sp, wd in zip(sprites, words):
            ww = sp.shape[1]
            add = ww + (space if cur else 0)
            if cur and cur_w + add > max_width:
                rows.append((cur, cur_w))
                cur, cur_w = [], 0.0
                add = ww
            cur.append((sp, wd, ww))
            cur_w += add
        if cur:
            rows.append((cur, cur_w))

        out = []
        total_h = sum(max(sp.shape[0] for sp, _w, _ww in r) for r, _cw in rows) + \
            line_gap * size * (len(rows) - 1)
        y = -total_h / 2
        for row, row_w in rows:
            x = row_w / 2                      # start from the right edge (RTL)
            row_h = max(sp.shape[0] for sp, _w, _ww in row)
            for sp, wd, ww in row:
                cx = x - ww / 2
                cy = y + row_h / 2
                out.append(dict(mask=sp, word=wd, cx=cx, cy=cy, w=ww, h=sp.shape[0]))
                x -= ww + space
            y += row_h + line_gap * size
        return out
