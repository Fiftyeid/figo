# -*- coding: utf-8 -*-
"""Shot types (photo + HUD overlays + cards). Diagram shots live in diagrams.py."""
import math, functools
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from common import *
from broll import broll_view, hud_broll_bg

T = functools.lru_cache(maxsize=4096)(text_image)


@functools.lru_cache(maxsize=1)
def grid_bg_cached():
    return grid_bg()


# =========================================================== supersampled canvas
class SS:
    """Draw with antialiasing: draw at s x resolution, then reduce."""

    def __init__(self, w=W, h=H, s=2):
        self.s = s
        self.im = Image.new("RGBA", (int(w * s), int(h * s)), (0, 0, 0, 0))
        self.d = ImageDraw.Draw(self.im)

    def _p(self, pts):
        return [(x * self.s, y * self.s) for x, y in pts]

    def line(self, pts, fill, width=2):
        self.d.line(self._p(pts), fill=fill, width=max(1, int(width * self.s)), joint="curve")

    def poly(self, pts, fill=None, outline=None, width=1):
        self.d.polygon(self._p(pts), fill=fill)
        if outline:
            pp = list(pts) + [pts[0]]
            self.line(pp, outline, width)

    def ellipse(self, box, fill=None, outline=None, width=1):
        x0, y0, x1, y1 = box
        self.d.ellipse([x0 * self.s, y0 * self.s, x1 * self.s, y1 * self.s], fill=fill, outline=outline,
                       width=max(1, int(width * self.s)) if outline else 0)

    def circle(self, cx, cy, r, **kw):
        self.ellipse((cx - r, cy - r, cx + r, cy + r), **kw)

    def arc(self, box, a0, a1, fill, width=2):
        x0, y0, x1, y1 = box
        self.d.arc([x0 * self.s, y0 * self.s, x1 * self.s, y1 * self.s], a0, a1, fill=fill,
                   width=max(1, int(width * self.s)))

    def rect(self, box, fill=None, outline=None, width=1, radius=0):
        x0, y0, x1, y1 = box
        self.d.rounded_rectangle([x0 * self.s, y0 * self.s, x1 * self.s, y1 * self.s], radius=radius * self.s,
                                 fill=fill, outline=outline, width=max(1, int(width * self.s)) if outline else 0)

    def arrow(self, p0, p1, fill, width=6, head=26):
        x0, y0 = p0
        x1, y1 = p1
        L = math.hypot(x1 - x0, y1 - y0)
        if L < 2:
            return
        ux, uy = (x1 - x0) / L, (y1 - y0) / L
        hb = (x1 - ux * head, y1 - uy * head)
        self.line([p0, hb], fill, width)
        px, py = -uy, ux
        self.poly([(x1, y1), (hb[0] + px * head * 0.55, hb[1] + py * head * 0.55),
                   (hb[0] - px * head * 0.55, hb[1] - py * head * 0.55)], fill=fill)

    def done(self):
        return self.im.reduce(self.s) if self.s > 1 else self.im


def dashed(ss, p0, p1, fill, width=2, dash=14, gap=10):
    x0, y0 = p0
    x1, y1 = p1
    L = math.hypot(x1 - x0, y1 - y0)
    if L < 1:
        return
    ux, uy = (x1 - x0) / L, (y1 - y0) / L
    s = 0.0
    while s < L:
        e = min(L, s + dash)
        ss.line([(x0 + ux * s, y0 + uy * s), (x0 + ux * e, y0 + uy * e)], fill, width)
        s += dash + gap


def curved_arrow(ss, cx, cy, r, a0, a1, fill, width=6, head=24):
    """Arc arrow from angle a0 to a1 (degrees, screen coords, clockwise positive)."""
    n = 28
    pts = [(cx + r * math.cos(math.radians(a0 + (a1 - a0) * k / n)),
            cy + r * math.sin(math.radians(a0 + (a1 - a0) * k / n))) for k in range(n + 1)]
    ss.line(pts[:-2], fill, width)
    ss.arrow(pts[-4], pts[-1], fill, width, head)


# =========================================================== overlays
def _alpha_window(t, t0, t1, fin=0.3, fout=0.3):
    a_in = ease_out_cubic((t - t0) / fin)
    a_out = 1 - ease_in_out((t - (t1 - fout)) / fout) if t1 is not None else 1.0
    return clamp(min(a_in, a_out))


def ov_lower(im, ov, t, t1):
    t0 = ov["t"]
    a = _alpha_window(t, t0, ov.get("t_out", t1))
    if a <= 0:
        return
    name = T(ov["name"], "cx", ov.get("size", 70), WHITE, shadow=3)
    sub = T(ov.get("sub", ""), "cs", 34, AMBER, tracking=2, shadow=2) if ov.get("sub") else None
    x, y = ov.get("x", 110), ov.get("y", 830)
    p = ease_out_cubic((t - t0) / 0.45)
    bh = name.height + (sub.height if sub else 0) - 10
    d = ImageDraw.Draw(im)
    d.rectangle([x, y + bh * (1 - p) * 0.5, x + 8, y + bh * (1 - (1 - p) * 0.5)], fill=AMBER + (int(255 * a),))
    # dark backing gradient for legibility
    off = (1 - p) * -60
    paste_at(im, name, x + 26 + off, y - 8, a)
    if sub:
        paste_at(im, sub, x + 28 + off * 1.4, y + name.height - 22, a * ease_out_cubic((t - t0 - 0.15) / 0.4))


def ov_text(im, ov, t, t1):
    t0 = ov["t"]
    a = _alpha_window(t, t0, ov.get("t_out", t1), fin=ov.get("fin", 0.35))
    if a <= 0:
        return
    img = T(ov["text"], ov.get("font", "cx"), ov.get("size", 80), tuple(ov.get("color", WHITE)), shadow=ov.get("shadow", 4),
            tracking=ov.get("tracking", 0), stroke=ov.get("stroke", 0))
    if ov.get("glow"):
        img = _glowed(ov["text"], ov.get("font", "cx"), ov.get("size", 80), tuple(ov.get("color", WHITE)))
    p = ease_out_cubic((t - t0) / 0.5)
    dy = (1 - p) * ov.get("rise", 30)
    anchor = ov.get("anchor", "center")
    x, y = ov["x"], ov["y"]
    if anchor == "center":
        paste_at(im, img, x - img.width / 2, y - img.height / 2 + dy, a)
    elif anchor == "right":
        paste_at(im, img, x - img.width, y - img.height / 2 + dy, a)
    else:
        paste_at(im, img, x, y - img.height / 2 + dy, a)


@functools.lru_cache(maxsize=256)
def _glowed(text, kind, size, color):
    return glow(text_image(text, kind, size, color), radius=max(8, size // 8), strength=0.9, color=color)


def ov_type(im, ov, t, t1):
    """Typewriter mono text (dates, locations)."""
    t0 = ov["t"]
    a = _alpha_window(t, t0, ov.get("t_out", t1), fin=0.1)
    if a <= 0:
        return
    s = ov["text"]
    n = int(clamp((t - t0) / max(0.2, len(s) * 0.035)) * len(s))
    cur = s[:n] + ("_" if (int(t * 3) % 2 == 0 and n < len(s) + 1) else " ")
    img = T(cur, "mono", ov.get("size", 40), tuple(ov.get("color", WHITE)), shadow=3)
    x, y = ov.get("x", 110), ov.get("y", 120)
    if ov.get("box", True):
        full = T(s + "_", "mono", ov.get("size", 40), WHITE)
        bg = rounded_rect((full.width + 24, full.height + 4), 4, (0, 0, 0, 150))
        paste_at(im, bg, x - 12, y - 2, a)
    paste_at(im, img, x, y, a)


def ov_chip(im, ov, t, t1):
    t0 = ov["t"]
    a = _alpha_window(t, t0, ov.get("t_out", t1), fin=0.2)
    if a <= 0:
        return
    c = _chip(ov["text"], tuple(ov.get("color", AMBER)), ov.get("size", 44), tuple(ov.get("fg", INK)))
    s = 0.6 + 0.4 * ease_out_back((t - t0) / 0.35)
    paste_center(im, c, ov["x"], ov["y"], a, scale=s)


@functools.lru_cache(maxsize=256)
def _chip(text, color, size, fg):
    return chip(text, color, size=size, fg=fg)


def ov_big(im, ov, t, t1):
    """Count-up speed readout: value + unit, optional sub line."""
    t0 = ov["t"]
    a = _alpha_window(t, t0, ov.get("t_out", t1), fin=0.2)
    if a <= 0:
        return
    v = ov["value"]
    dec = ov.get("dec", 0)
    p = ease_out_cubic((t - t0) / ov.get("dur", 1.0))
    cur = v * p if ov.get("count", True) else v
    s = f"{cur:,.{dec}f}"
    size = ov.get("size", 190)
    col = tuple(ov.get("color", WHITE))
    num = T(s, "title", size, col, shadow=6)
    unit = T(ov.get("unit", "KM/H"), "cx", int(size * 0.36), AMBER, shadow=4)
    x, y = ov.get("x", 960), ov.get("y", 540)
    anchor = ov.get("anchor", "center")
    tw = num.width + unit.width - 10
    x0 = x - tw / 2 if anchor == "center" else (x if anchor == "left" else x - tw)
    sc = 1.0 + 0.10 * (1 - ease_out_cubic((t - t0 - ov.get("dur", 1.0)) / 0.25)) * (t > t0 + ov.get("dur", 1.0))
    paste_at(im, num, x0, y - num.height / 2, a)
    paste_at(im, unit, x0 + num.width - 10, y + num.height * 0.5 - unit.height - size * 0.12, a)
    if ov.get("sub"):
        ts = ov.get("t_sub", t0 + 0.6)
        sub = T(ov["sub"], "cs", int(size * 0.26), WHITE, shadow=3, tracking=2)
        paste_at(im, sub, x0 + 6, y + num.height * 0.42, a * ease_out_cubic((t - ts) / 0.35))


@functools.lru_cache(maxsize=64)
def _stamp(text, color, size):
    t = text_image(text, "cx", size, color, tracking=4, pad=4)
    pad = 26
    w, h = t.width + 2 * pad, t.height + 2 * pad - 10
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle([3, 3, w - 4, h - 4], outline=color + (255,), width=6)
    d.rectangle([13, 13, w - 14, h - 14], outline=color + (200,), width=2)
    im.alpha_composite(t, (pad, pad - 6))
    # distressed texture
    rng = np.random.default_rng(len(text))
    a = np.asarray(im.getchannel("A")).astype(np.float32)
    noise = rng.random(a.shape) > 0.12
    a *= noise
    im.putalpha(Image.fromarray(a.astype(np.uint8)))
    big = Image.new("RGBA", (int(w * 1.2), int(h * 1.8)), (0, 0, 0, 0))
    big.alpha_composite(im, ((big.width - w) // 2, (big.height - h) // 2))
    return big.rotate(6, resample=Image.BICUBIC, expand=True)


def ov_stamp(im, ov, t, t1):
    t0 = ov["t"]
    a = _alpha_window(t, t0, ov.get("t_out", t1), fin=0.12)
    if a <= 0:
        return
    st = _stamp(ov["text"], tuple(ov.get("color", RED)), ov.get("size", 90))
    s = 1.0 + 0.6 * (1 - ease_out_cubic((t - t0) / 0.22))
    paste_center(im, st, ov.get("x", 960), ov.get("y", 540), a * 0.95, scale=s)


def ov_callout(im, ov, t, t1):
    """Dot on the subject + leader line + label."""
    t0 = ov["t"]
    a = _alpha_window(t, t0, ov.get("t_out", t1), fin=0.15)
    if a <= 0:
        return
    px, py = ov["p"]
    lx, ly = ov["l"]
    p = ease_out_cubic((t - t0) / 0.4)
    col = tuple(ov.get("color", AMBER))
    ss = SS(W, H, 1)
    ex, ey = px + (lx - px) * p, py + (ly - py) * p
    ss.line([(px, py), (ex, ey)], col + (int(230 * a),), 3)
    r = 9 + 5 * math.sin(t * 6)
    ss.circle(px, py, 8, fill=col + (int(255 * a),))
    ss.circle(px, py, r + 8, outline=col + (int(150 * a),), width=2)
    im.alpha_composite(ss.done())
    if p > 0.6:
        lab = T(ov["text"], "cb", ov.get("size", 44), WHITE, shadow=3)
        bg = rounded_rect((lab.width + 26, lab.height + 2), 6, (8, 12, 18, 200), outline=col + (255,), width=2)
        right = lx >= px
        x = lx if right else lx - bg.width
        aa = a * ease_out_cubic((t - t0 - 0.25) / 0.3)
        paste_at(im, bg, x, ly - bg.height / 2, aa)
        paste_at(im, lab, x + 13, ly - bg.height / 2, aa)


def ov_spec(im, ov, t, t1):
    """Right-side spec panel; rows = [(label, value)], ts = appear times."""
    t0 = ov["t"]
    a = _alpha_window(t, t0, ov.get("t_out", t1))
    if a <= 0:
        return
    rows = ov["rows"]
    ts = ov.get("ts") or [t0 + 0.3 + 0.35 * k for k in range(len(rows))]
    x, y, w = ov.get("x", 1310), ov.get("y", 230), ov.get("w", 520)
    rh = 96
    h = 90 + rh * len(rows)
    p = ease_out_cubic((t - t0) / 0.4)
    panel = _panel(w, h)
    paste_at(im, panel, x + (1 - p) * 80, y, a)
    head = T(ov.get("title", "SPECS"), "mono", 32, AMBER, tracking=3)
    paste_at(im, head, x + 26 + (1 - p) * 80, y + 16, a)
    for k, (lab, val) in enumerate(rows):
        aa = a * ease_out_cubic((t - ts[k]) / 0.35)
        if aa <= 0:
            continue
        yy = y + 76 + k * rh
        dx = (1 - ease_out_cubic((t - ts[k]) / 0.35)) * 40
        paste_at(im, T(lab, "mono", 26, MUTED, tracking=2), x + 28 + dx, yy, aa)
        paste_at(im, T(val, "cx", 52, WHITE), x + 26 + dx, yy + 24, aa)


@functools.lru_cache(maxsize=32)
def _panel(w, h):
    p = rounded_rect((w, h), 10, (8, 12, 18, 205), outline=(255, 255, 255, 40), width=2)
    ImageDraw.Draw(p).rectangle([0, 0, w, 5], fill=AMBER + (255,))
    return p


OVERLAYS = dict(lower=ov_lower, text=ov_text, type=ov_type, chip=ov_chip, big=ov_big, stamp=ov_stamp,
                callout=ov_callout, spec=ov_spec)


# =========================================================== base shot
class Shot:
    grain = 0.0

    def __init__(self, start, end, overlays=(), **kw):
        self.start, self.end = start, end
        self.overlays = list(overlays)
        self.kw = kw

    def prepare(self):
        pass

    def base(self, t):
        return grid_bg_cached().copy()

    def frame(self, t):
        im = self.base(t)
        if im.mode != "RGBA":
            im = im.convert("RGBA")
        for ov in self.overlays:
            OVERLAYS[ov["kind"]](im, ov, t, ov.get("t_out", self.end - 0.05))
        return im

    def p(self, t):
        return clamp((t - self.start) / max(0.01, self.end - self.start))


# =========================================================== photo shot
@functools.lru_cache(maxsize=2)
def speed_layer(seed=3):
    rng = np.random.default_rng(seed)
    im = Image.new("RGBA", (W * 2, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for _ in range(140):
        y = rng.uniform(0, H)
        x = rng.uniform(0, W * 2)
        L = rng.uniform(180, 900)
        a = int(rng.uniform(25, 95))
        wd = int(rng.choice([1, 1, 2, 2, 3]))
        d.line([(x, y), (x + L, y)], fill=(255, 255, 255, a), width=wd)
        if x + L > W * 2:
            d.line([(x - W * 2, y), (x + L - W * 2, y)], fill=(255, 255, 255, a), width=wd)
    return im.filter(ImageFilter.GaussianBlur(1.2))


class PhotoShot(Shot):
    """Moving 25fps B-roll shot: z=(zoom0, zoom1), c0/c1 = centre (fractions), handheld shake, speed lines."""

    def __init__(self, start, end, image, z=(1.0, 1.1), c0=(0.5, 0.5), c1=None, shake=0.0, speed=0.0,
                 speed_dir=-1, darken=0.0, warmth=0.0, teal=0.25, blur=0, grain=0.04, ease=False, **kw):
        super().__init__(start, end, **kw)
        self.image, self.z, self.c0, self.c1 = image, z, c0, c1 or c0
        self.shake, self.speed, self.speed_dir = shake, speed, speed_dir
        self.look = dict(darken=darken, warmth=warmth, teal=teal, blur=blur)
        self.grain = grain
        self.ease = ease

    def prepare(self):
        pass

    def base(self, t):
        p = self.p(t)
        e = ease_in_out(p) if self.ease else p
        zoom = lerp(self.z[0], self.z[1], e)
        cx = lerp(self.c0[0], self.c1[0], e)
        cy = lerp(self.c0[1], self.c1[1], e)
        if self.shake:
            cx += self.shake * 0.0035 * (math.sin(t * 6.3) * 0.6 + math.sin(t * 11.7 + 1.3) * 0.4)
            cy += self.shake * 0.0035 * (math.sin(t * 7.9 + 0.7) * 0.6 + math.sin(t * 13.1 + 2.1) * 0.4)
        im = broll_view(self.image, t, cx, cy, zoom, contrast=1.08, sat=1.06,
                        warmth=self.look["warmth"], teal=self.look["teal"],
                        darken=self.look["darken"], blur=self.look["blur"])
        if self.grain:
            im = add_grain(im, t, self.grain)
        im = im.convert("RGBA")
        if self.speed:
            sl = speed_layer()
            off = int((t * 2600) % W)
            if self.speed_dir > 0:
                off = W - off
            layer = sl.crop((off, 0, off + W, H))
            im.alpha_composite(with_alpha(layer, self.speed))
        im.alpha_composite(vignette())
        return im


# =========================================================== title card
class TitleShot(Shot):
    def __init__(self, start, end, image, lines=("WORLD'S FASTEST", "MILITARY HELICOPTER"), sub="EXPLAINED", **kw):
        super().__init__(start, end, **kw)
        self.image, self.lines, self.sub = image, lines, sub

    def prepare(self):
        self.l1 = glow(text_image(self.lines[0], "title", 150, WHITE), 18, 0.6)
        self.l2 = glow(text_image(self.lines[1], "title", 150, AMBER), 22, 0.9, color=AMBER)
        self.subi = chip(self.sub, WHITE, size=58, tracking=10, padx=34)
        self.corners = hud_corners((W, H), WHITE, 120, inset=70)

    def base(self, t):
        p = self.p(t)
        im = broll_view(self.image, t, 0.5, 0.5, 1.02 + 0.08 * p,
                        contrast=1.1, sat=0.9, warmth=0.0, teal=0.4, darken=0.45, blur=4).convert("RGBA")
        im.alpha_composite(vignette())
        t0 = self.start + 0.1
        a1 = ease_out_cubic((t - t0) / 0.25)
        s1 = 1 + 0.25 * (1 - ease_out_cubic((t - t0) / 0.3))
        paste_center(im, self.l1, W / 2, 420, a1, s1)
        a2 = ease_out_cubic((t - t0 - 0.3) / 0.25)
        s2 = 1 + 0.25 * (1 - ease_out_cubic((t - t0 - 0.3) / 0.3))
        paste_center(im, self.l2, W / 2, 575, a2, s2)
        a3 = ease_out_cubic((t - t0 - 0.8) / 0.3)
        paste_center(im, self.subi, W / 2, 720, a3, 0.8 + 0.2 * ease_out_back((t - t0 - 0.8) / 0.35))
        d = ImageDraw.Draw(im)
        pw = ease_out_cubic((t - t0 - 0.5) / 0.6)
        d.line([(W / 2 - 520 * pw, 655), (W / 2 + 520 * pw, 655)], fill=WHITE + (150,), width=2)
        im.alpha_composite(with_alpha(self.corners, ease_out_cubic((t - t0) / 0.5)))
        # flash
        fl = 1 - clamp((t - t0) / 0.18)
        if 0 < fl:
            im.alpha_composite(Image.new("RGBA", (W, H), (255, 255, 255, int(200 * fl))))
        return im


# =========================================================== answer card
class AnswerShot(Shot):
    """ANSWER #n chapter card with 4-step progress."""

    def __init__(self, start, end, image, n=1, label="", **kw):
        super().__init__(start, end, **kw)
        self.image, self.n, self.label = image, n, label

    def prepare(self):
        self.num = glow(text_image(str(self.n), "title", 420, AMBER), 30, 0.8, color=AMBER)
        self.ans = text_image("ANSWER", "cx", 96, WHITE, tracking=18)
        self.lab = text_image(self.label, "cs", 54, WHITE, tracking=6)
        self.of = text_image("OF 4", "mono", 40, MUTED, tracking=6)

    def base(self, t):
        p = self.p(t)
        im = broll_view(self.image, t, 0.5, 0.5, 1.06 - 0.05 * p,
                        contrast=1.1, sat=0.75, warmth=0.0, teal=0.5, darken=0.52, blur=3).convert("RGBA")
        im.alpha_composite(vignette())
        # scanlines
        t0 = self.start + 0.15
        a = ease_out_cubic((t - t0) / 0.3)
        paste_center(im, self.ans, W / 2 - 230, 420, a)
        paste_center(im, self.of, W / 2 - 230, 500, a)
        s = 1 + 0.5 * (1 - ease_out_cubic((t - t0 - 0.2) / 0.3))
        paste_center(im, self.num, W / 2 + 170, 440, ease_out_cubic((t - t0 - 0.2) / 0.2), s)
        paste_center(im, self.lab, W / 2, 720, ease_out_cubic((t - t0 - 0.6) / 0.4))
        # progress pips
        d = ImageDraw.Draw(im)
        for k in range(4):
            x = W / 2 - 165 + k * 110
            col = AMBER if k + 1 == self.n else (WHITE if k + 1 < self.n else (90, 100, 115))
            aa = int(255 * ease_out_cubic((t - t0 - 0.8 - 0.08 * k) / 0.3))
            d.rectangle([x, 820, x + 90, 830], fill=col + (aa,))
        fl = 1 - clamp((t - t0 - 0.2) / 0.15)
        if 0 < fl < 1:
            im.alpha_composite(Image.new("RGBA", (W, H), (255, 255, 255, int(120 * fl))))
        return im


# =========================================================== four answers board
class FourShot(Shot):
    """4 cards with live moving B-roll inside each card. cards = [dict(image, c=(cx,cy), z, title, sub, value, t)]."""

    def __init__(self, start, end, cards, header=None, bg="hind", **kw):
        super().__init__(start, end, **kw)
        self.cards, self.header, self.bgk = cards, header, bg

    def prepare(self):
        self.cw, self.ch = 400, 520
        g = Image.new("L", (1, self.ch))
        for y in range(self.ch):
            g.putpixel((0, y), int(230 * clamp((y - self.ch * 0.45) / (self.ch * 0.55)) ** 1.2))
        self.card_shade = Image.new("RGBA", (self.cw, self.ch), (5, 8, 12, 255))
        self.card_shade.putalpha(g.resize((self.cw, self.ch)))
        self.card_mask = Image.new("L", (self.cw, self.ch), 0)
        ImageDraw.Draw(self.card_mask).rounded_rectangle([0, 0, self.cw - 1, self.ch - 1], 14, fill=255)
        self.head = text_image(self.header, "cx", 66, WHITE, tracking=4, shadow=4) if self.header else None

    def base(self, t):
        im = broll_view(self.bgk, t, 0.5, 0.5, 1.03 + 0.04 * self.p(t),
                        contrast=1.1, sat=0.65, warmth=0.0, teal=0.5, darken=0.62, blur=6).convert("RGBA")
        if self.head:
            paste_center(im, self.head, W / 2, 120, ease_out_cubic((t - self.start - 0.1) / 0.4))
        gap = 40
        x0 = (W - (4 * self.cw + 3 * gap)) / 2
        y0 = 230 if self.head else 270
        d = ImageDraw.Draw(im)
        for k, c in enumerate(self.cards):
            x = x0 + k * (self.cw + gap)
            tr = c.get("t", self.start)
            # empty slot
            d.rounded_rectangle([x, y0, x + self.cw, y0 + self.ch], 14, outline=(255, 255, 255, 70), width=2,
                                fill=(10, 14, 20, 120))
            q = T(str(k + 1), "title", 120, (255, 255, 255, 60))
            paste_center(im, q, x + self.cw / 2, y0 + self.ch / 2)
            a = ease_out_cubic((t - tr) / 0.4)
            if a <= 0:
                continue
            dy = (1 - a) * 60
            v = broll_view(c["image"], t + k * 1.15, c.get("c", (0.5, 0.5))[0], c.get("c", (0.5, 0.5))[1],
                           c.get("z", 1.3), out=(self.cw, self.ch)).convert("RGBA")
            v.alpha_composite(self.card_shade)
            v.putalpha(self.card_mask)
            paste_at(im, v, x, y0 + dy, a)
            col = tuple(c.get("color", AMBER))
            badge = _chip(str(k + 1), col, 44, INK)
            paste_at(im, badge, x + 16, y0 + 16 + dy, a)
            ty = y0 + self.ch - 150 + dy
            if c.get("value"):
                ta = ease_out_cubic((t - c.get("t_value", tr + 0.3)) / 0.35)
                paste_at(im, T(c["value"], "title", 64, col, shadow=3), x + 22, ty - 40, a * ta)
                ty += 40
            paste_at(im, T(c["title"], "cx", 46, WHITE, shadow=3), x + 22, ty + 10, a)
            if c.get("sub"):
                paste_at(im, T(c["sub"], "cs", 30, MUTED, tracking=1), x + 24, ty + 64, a)
            if c.get("stamp"):
                sa = ease_out_cubic((t - c.get("t_stamp", tr + 0.6)) / 0.15)
                if sa > 0:
                    st = _stamp(c["stamp"], tuple(c.get("stamp_color", WHITE)), 40)
                    paste_center(im, st, x + self.cw / 2, y0 + 120, sa, 1 + 0.5 * (1 - sa))
        return im


# =========================================================== big fact card
class FactShot(Shot):
    """Big text or rolling number over darkened/blurred moving B-roll."""

    def __init__(self, start, end, image=None, text=None, roll=None, size=300, color=WHITE, caption=None,
                 t_caption=None, top=None, y=500, **kw):
        super().__init__(start, end, **kw)
        self.image, self.text, self.roll, self.size = image, text, roll, size
        self.color, self.caption, self.t_caption, self.top, self.y = tuple(color), caption, t_caption, top, y

    def prepare(self):
        pass

    def base(self, t):
        if self.image is not None:
            im = broll_view(self.image, t, 0.5, 0.5, 1.02 + 0.06 * self.p(t),
                            contrast=1.1, sat=0.75, warmth=0.0, teal=0.5, darken=0.58, blur=5).convert("RGBA")
            im.alpha_composite(vignette())
        else:
            im = hud_broll_bg("lynx_record", t)
        t0 = self.start + 0.1
        if self.top:
            paste_center(im, T(self.top, "cs", 50, AMBER, tracking=8), W / 2, self.y - self.size * 0.62,
                         ease_out_cubic((t - t0) / 0.4))
        if self.roll:
            a0, a1, r0, r1 = self.roll
            v = int(round(lerp(a0, a1, ease_in_out((t - r0) / max(0.1, r1 - r0)))))
            s = self.text.format(v) if self.text else str(v)
            img = T(s, "title", self.size, self.color, shadow=8)
            paste_center(im, img, W / 2, self.y, ease_out_cubic((t - t0) / 0.3))
        elif self.text:
            img = _glowed(self.text, "title", self.size, self.color)
            s = 1 + 0.18 * (1 - ease_out_cubic((t - t0) / 0.35))
            paste_center(im, img, W / 2, self.y, ease_out_cubic((t - t0) / 0.25), s)
        if self.caption:
            tc = self.t_caption or t0 + 0.6
            cap = T(self.caption, "cx", 64, WHITE, shadow=4, tracking=2)
            a = ease_out_cubic((t - tc) / 0.4)
            paste_center(im, cap, W / 2, self.y + self.size * 0.62 + (1 - a) * 20, a)
        return im


# =========================================================== stats grid
class StatsShot(Shot):
    """Up to 4 big numbers with labels, each counting up at its own time over moving B-roll."""

    def __init__(self, start, end, image, items, header=None, **kw):
        super().__init__(start, end, **kw)
        self.image, self.items, self.header = image, items, header

    def prepare(self):
        pass

    def base(self, t):
        im = broll_view(self.image, t, 0.5, 0.5, 1.03 + 0.05 * self.p(t),
                        contrast=1.1, sat=0.75, warmth=0.0, teal=0.5, darken=0.60, blur=5).convert("RGBA")
        im.alpha_composite(vignette())
        if self.header:
            paste_center(im, T(self.header, "cx", 62, WHITE, tracking=4, shadow=4), W / 2, 170,
                         ease_out_cubic((t - self.start - 0.1) / 0.4))
        n = len(self.items)
        cw = 420
        x0 = W / 2 - cw * n / 2
        d = ImageDraw.Draw(im)
        for k, it in enumerate(self.items):
            t0 = it["t"]
            a = ease_out_cubic((t - t0) / 0.35)
            if a <= 0:
                continue
            cx = x0 + cw * (k + 0.5)
            p = ease_out_cubic((t - t0) / 0.9)
            v = it["value"]
            s = it.get("fmt", "{:,.0f}").format(v * p if it.get("count", True) else v)
            num = T(s, "title", 150, tuple(it.get("color", AMBER)), shadow=6)
            paste_center(im, num, cx, 520 + (1 - a) * 30, a)
            paste_center(im, T(it["label"], "cx", 48, WHITE, tracking=3, shadow=3), cx, 645, a)
            if it.get("sub"):
                paste_center(im, T(it["sub"], "cs", 32, MUTED, tracking=2), cx, 700, a)
            if k > 0:
                d.line([(cx - cw / 2, 430), (cx - cw / 2, 720)], fill=(255, 255, 255, int(60 * a)), width=2)
        return im


# =========================================================== measurement cards
class CardsShot(Shot):
    """Row of explainer cards over moving B-roll: items = [dict(head, title, body, t, color)]."""

    def __init__(self, start, end, image, items, header=None, footer=None, t_footer=None, **kw):
        super().__init__(start, end, **kw)
        self.image, self.items, self.header, self.footer, self.t_footer = image, items, header, footer, t_footer

    def prepare(self):
        pass

    def base(self, t):
        im = broll_view(self.image, t, 0.5, 0.5, 1.03 + 0.05 * self.p(t),
                        contrast=1.1, sat=0.75, warmth=0.0, teal=0.5, darken=0.62, blur=6).convert("RGBA")
        if self.header:
            paste_center(im, T(self.header, "cx", 64, WHITE, tracking=4, shadow=4), W / 2, 170,
                         ease_out_cubic((t - self.start - 0.1) / 0.4))
        n = len(self.items)
        cw, ch, gap = 500, 400, 50
        x0 = (W - (n * cw + (n - 1) * gap)) / 2
        for k, it in enumerate(self.items):
            a = ease_out_cubic((t - it["t"]) / 0.4)
            if a <= 0:
                continue
            x = x0 + k * (cw + gap)
            y = 300 + (1 - a) * 50
            col = tuple(it.get("color", AMBER))
            card = _card(cw, ch, col)
            paste_at(im, card, x, y, a)
            paste_at(im, T(it["head"], "title", 92, col), x + 30, y + 26, a)
            paste_at(im, T(it["title"], "cx", 46, WHITE, tracking=1), x + 32, y + 150, a)
            body = _para(it["body"], 36, cw - 70)
            paste_at(im, body, x + 32, y + 225, a)
        if self.footer:
            a = ease_out_cubic((t - self.t_footer) / 0.3)
            c = _chip(self.footer, AMBER, 46, INK)
            paste_center(im, c, W / 2, 820, a, 0.7 + 0.3 * ease_out_back((t - self.t_footer) / 0.35))
        return im


@functools.lru_cache(maxsize=32)
def _card(w, h, col):
    c = rounded_rect((w, h), 14, (8, 12, 18, 215), outline=(255, 255, 255, 45), width=2)
    ImageDraw.Draw(c).rectangle([0, 0, 8, h], fill=col + (255,))
    return c


@functools.lru_cache(maxsize=64)
def _para(s, size, w):
    return paragraph_image(s, "bodym", size, (205, 212, 222), max_w=w)


# =========================================================== checklist over moving B-roll
class ListShot(Shot):
    """Moving B-roll on the left, checklist on the right. items = [dict(text, sub, t)]."""

    def __init__(self, start, end, image, items, header="", c=(0.45, 0.5), z=(1.25, 1.35), **kw):
        super().__init__(start, end, **kw)
        self.image, self.items, self.header, self.c, self.z = image, items, header, c, z

    def prepare(self):
        g = np.zeros((1, W), np.float32)
        xs = np.arange(W)
        g[0] = np.clip((xs - 700) / 500, 0, 1) * 235
        self.shade = Image.new("RGBA", (W, H), (6, 9, 14, 255))
        self.shade.putalpha(Image.fromarray(g.astype(np.uint8), "L").resize((W, H)))
        self.head = text_image(self.header, "cx", 60, AMBER, tracking=4, shadow=3)

    def base(self, t):
        p = self.p(t)
        im = broll_view(self.image, t, self.c[0], self.c[1], lerp(self.z[0], self.z[1], p),
                        contrast=1.08, sat=1.02, warmth=0.0, teal=0.3)
        im = add_grain(im, t, 0.04).convert("RGBA")
        im.alpha_composite(self.shade)
        im.alpha_composite(vignette())
        x = 1020
        paste_at(im, self.head, x, 150, ease_out_cubic((t - self.start - 0.1) / 0.4))
        d = ImageDraw.Draw(im)
        for k, it in enumerate(self.items):
            a = ease_out_cubic((t - it["t"]) / 0.35)
            if a <= 0:
                continue
            y = 270 + k * 140
            dx = (1 - a) * 50
            d.rounded_rectangle([x + dx, y + 8, x + 52 + dx, y + 60], 8, outline=AMBER + (int(255 * a),), width=4)
            pc = ease_out_cubic((t - it["t"] - 0.15) / 0.25)
            if pc > 0:
                d.line([(x + 12 + dx, y + 34), (x + 24 + dx, y + 34 + 12 * pc)], fill=AMBER + (int(255 * a),), width=6)
                if pc > 0.5:
                    d.line([(x + 24 + dx, y + 46), (x + 24 + dx + 18 * (pc - 0.5) * 2, y + 46 - 30 * (pc - 0.5) * 2)],
                           fill=AMBER + (int(255 * a),), width=6)
            paste_at(im, T(it["text"], "cx", 54, WHITE, shadow=3), x + 80 + dx, y - 6, a)
            if it.get("sub"):
                paste_at(im, T(it["sub"], "cs", 34, MUTED, tracking=1), x + 82 + dx, y + 56, a)
        return im


# =========================================================== split screen (then vs now)
class SplitShot(Shot):
    def __init__(self, start, end, left, right, **kw):
        super().__init__(start, end, **kw)
        self.left, self.right = left, right

    def prepare(self):
        self.sides = (self.left, self.right)

    def base(self, t):
        p = self.p(t)
        im = Image.new("RGBA", (W, H), BG0 + (255,))
        for k, side in enumerate(self.sides):
            ta = side.get("t", self.start)
            a = ease_out_cubic((t - ta) / 0.45)
            if a <= 0:
                continue
            c = side.get("c", (0.5, 0.5))
            v = broll_view(side["image"], t + k * 0.9, c[0], c[1], side.get("z", 1.2) + 0.06 * p,
                           out=(W // 2 - 6, H)).convert("RGBA")
            v.alpha_composite(vignette().resize(v.size))
            x = 0 if k == 0 else W // 2 + 6
            dx = (1 - a) * (-120 if k == 0 else 120)
            paste_at(im, v, x + dx, 0, a)
            lab = T(side["title"], "cx", 66, WHITE, shadow=4)
            paste_at(im, lab, x + 60 + dx, 820, a)
            if side.get("sub"):
                paste_at(im, T(side["sub"], "cs", 40, tuple(side.get("color", AMBER)), tracking=3, shadow=3),
                         x + 62 + dx, 900, a)
        d = ImageDraw.Draw(im)
        d.rectangle([W // 2 - 3, 0, W // 2 + 3, H], fill=AMBER + (255,))
        return im


# =========================================================== end card
class EndShot(Shot):
    def __init__(self, start, end, cards, question="WHICH ONE DESERVES THE TITLE?", t_sub=None, **kw):
        super().__init__(start, end, **kw)
        self.cards, self.question, self.t_sub = cards, question, t_sub

    def prepare(self):
        self.thumb_mask = Image.new("L", (400, 240), 0)
        ImageDraw.Draw(self.thumb_mask).rounded_rectangle([0, 0, 399, 239], 12, fill=255)
        self.q = glow(text_image(self.question, "title", 96, WHITE), 14, 0.5)

    def base(self, t):
        im = hud_broll_bg("v280_plane", t)
        t0 = self.start + 0.1
        paste_center(im, self.q, W / 2, 230, ease_out_cubic((t - t0) / 0.4))
        x0 = (W - (4 * 400 + 3 * 36)) / 2
        for k, c in enumerate(self.cards):
            a = ease_out_cubic((t - t0 - 0.3 - 0.15 * k) / 0.4)
            if a <= 0:
                continue
            x = x0 + k * 436
            th = broll_view(c["image"], t + k * 1.1, c.get("c", (0.5, 0.5))[0], c.get("c", (0.5, 0.5))[1],
                            c.get("z", 1.25), out=(400, 240)).convert("RGBA")
            th.putalpha(self.thumb_mask)
            paste_at(im, th, x, 380 + (1 - a) * 40, a)
            paste_center(im, T(c["title"], "cx", 44, WHITE), x + 200, 670, a)
            paste_center(im, T(c["sub"], "cs", 34, tuple(c.get("color", AMBER)), tracking=2), x + 200, 718, a)
        if self.t_sub:
            a = ease_out_cubic((t - self.t_sub) / 0.3)
            pulse = 1 + 0.04 * math.sin((t - self.t_sub) * 5)
            btn = _chip("SUBSCRIBE", RED, 60, WHITE)
            paste_center(im, btn, W / 2, 880, a, (0.7 + 0.3 * ease_out_back((t - self.t_sub) / 0.4)) * pulse)
        return im


SHOT_TYPES = dict(photo=PhotoShot, title=TitleShot, answer=AnswerShot, four=FourShot, fact=FactShot,
                  stats=StatsShot, cards=CardsShot, list=ListShot, split=SplitShot, end=EndShot)
