"""The look: virtual showroom stage, comparison chrome, section layouts."""
from __future__ import annotations

import math
import os
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from . import art as A
from . import config as C
from . import pixels as P
from .content import META, SIDES

_wash_cache: dict = {}
_grain_cache: dict = {}


def _grain():
    """A tiling film-grain plate, generated once."""
    if "g" not in _grain_cache:
        rng = np.random.default_rng(9)
        n = rng.normal(0, 1, (C.H, C.W + 64)).astype(np.float32)
        n = (np.clip(n, -2.2, 2.2) / 2.2 * 0.5 + 0.5) * 90 + 80
        _grain_cache["g"] = Image.fromarray(n.astype(np.uint8), "L")
    return _grain_cache["g"]


def _grain_offset(local: float) -> int:
    return int(local * 37) % 64
_camo = A.camouflage
_cartridge = A.cartridge

# ---------------------------------------------------------------- rhythm
HEAD_PILL_Y = 152      # chapter kicker
HEAD_TITLE_Y = 196     # chapter title
STAGE_TOP = 330
NAME_Y = 648
PILL_Y = 722
PILL_H = 50
PILL_GAP = 10


# ================================================================ helpers
def tw(text: str, weight: str, size: int, tracking: float = 0.0) -> int:
    """Exact rendered width (text_img adds 8 px of padding we don't want)."""
    return P.text_img(text, weight, size, C.INK, tracking).width - 8


def wrap(text: str, weight: str, size: int, max_w: float, max_lines: int = 4) -> list[str]:
    words = text.split()
    lines, cur = [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if tw(trial, weight, size) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines[:max_lines]


def paste_rgba(frame: Image.Image, sprite: Image.Image, xy, alpha: float = 1.0, mask=None):
    if alpha <= 0.01:
        return
    if alpha >= 0.995:
        frame.paste(sprite.convert("RGB"), (int(xy[0]), int(xy[1])), sprite.split()[3])
        return
    m = mask if mask is not None else sprite.split()[3]
    m = m.point(lambda v: int(v * alpha))
    frame.paste(sprite.convert("RGB"), (int(xy[0]), int(xy[1])), m)


@lru_cache(maxsize=256)
def fit(path: str, box_w: int, box_h: int) -> Image.Image:
    src = P.cutout(path)
    r = min(box_w / src.width, box_h / src.height)
    h = max(8, int(round(src.height * r / 2)) * 2)
    return P.scaled(path, h)


@lru_cache(maxsize=256)
def fit_shadow(path: str, box_w: int, box_h: int) -> tuple:
    s = fit(path, box_w, box_h)
    return P.shadow(path, s.height, spread=22, opacity=0.28)


def camera(f, zoom, cx=None, cy=None):
    """Slow dolly: crop then scale up. Cheap (one resize) and reads as a move."""
    if zoom <= 1.0005:
        return f
    cx = C.W / 2 if cx is None else cx
    cy = C.H / 2 if cy is None else cy
    w = int(round(C.W / zoom)) // 2 * 2
    h = int(round(C.H / zoom)) // 2 * 2
    x = int(C.clamp(cx - w / 2, 0, C.W - w))
    y = int(C.clamp(cy - h / 2, 0, C.H - h))
    return f.crop((x, y, x + w, y + h)).resize((C.W, C.H), Image.BILINEAR)


def paste_object(frame, path, cx, baseline, box_w=560, box_h=340, alpha=1.0,
                 lift=0.0, shadow=True, shadow_scale=1.0, reflect=True, flip=False,
                 scale_boost=1.0):
    """A cutout standing on the floor line, with contact shadow + reflection."""
    if alpha <= 0.01:
        return
    if flip:
        box_w = int(box_w * scale_boost)
        box_h = int(box_h * scale_boost)
        spr = fit(path, box_w, box_h).transpose(Image.FLIP_LEFT_RIGHT)
    else:
        box_w = int(box_w * scale_boost)
        box_h = int(box_h * scale_boost)
        spr = fit(path, box_w, box_h)
    x = int(cx - spr.width / 2)
    y = int(baseline - spr.height - lift)
    if shadow:
        rgb, m = fit_shadow(path, box_w, box_h)
        sw = int(spr.width * 0.94 * shadow_scale)
        sh = max(8, int(m.height * 0.20))
        rgb2 = rgb.resize((max(8, sw), sh), Image.BILINEAR)
        m2 = m.resize((max(8, sw), sh), Image.BILINEAR)
        fade = max(0.0, 1.0 - lift / 200.0)
        v = alpha * fade
        m2 = m2.point(lambda p: int(p * v))
        frame.paste(rgb2, (int(cx - m2.width / 2), int(baseline - m2.height * 0.42)), m2)
    if reflect:
        rr, ra = P.reflection(path, spr.height, 0.12)
        rh = rr.height
        if rh > 2 and spr.width > 2:
            ra2 = ra.resize((spr.width, rh), Image.BILINEAR).point(
                lambda v: int(v * alpha * max(0.0, 1.0 - lift / 180.0)))
            frame.paste(rr, (x, int(baseline + 2)), ra2)
    paste_rgba(frame, spr, (x, y), alpha)


# ================================================================ stage
class Stage:
    """Pre-rendered showroom: gradient cyclorama, floor grid, falloff."""

    def __init__(self):
        self.bg = self._build_bg()
        self.vignette = self._build_vignette()
        self.glow = self._build_glow()

    def _build_bg(self) -> Image.Image:
        w, h = C.W, C.H
        horizon = int(C.H * 0.57)
        ys = np.arange(h, dtype=np.float32)[:, None]
        top = np.array(C.BG_TOP, dtype=np.float32)
        mid = np.array(C.BG_HORIZON, dtype=np.float32)
        bot = np.array(C.BG_BOTTOM, dtype=np.float32)
        u1 = np.clip(ys / horizon, 0, 1) ** 1.1
        u2 = np.clip((ys - horizon) / max(1, h - horizon), 0, 1) ** 0.9
        grad = np.where(ys < horizon, top + (mid - top) * u1, mid + (bot - mid) * u2)
        img = np.repeat(grad[:, None, :], w, axis=1)

        xx = np.arange(w, dtype=np.float32)[None, :]
        d = ((xx - w / 2) / (w * 0.55)) ** 2 + ((ys - horizon * 0.70) / (h * 0.62)) ** 2
        img = np.clip(img + (np.clip(1 - d, 0, 1) ** 1.7 * 14)[..., None], 0, 255)
        base = Image.fromarray(img.astype(np.uint8), "RGB")

        grid = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        gd = ImageDraw.Draw(grid)
        vx, vy = w / 2, horizon
        for i in range(-24, 25):
            xb = vx + i * 168
            gd.line([(vx + (xb - vx) * 0.02, vy), (vx + (xb - vx) * 2.6, h + 240)],
                    fill=C.GRID_INK + (95,), width=2)
            gd.line([(vx + (xb - vx) * 0.02 + 2, vy + 2), (vx + (xb - vx) * 2.6 + 2, h + 240)],
                    fill=C.GRID_SHADE + (20,), width=2)
        depth, k = 0.0, 1.0
        while True:
            depth += 0.045 * k
            k *= 1.055
            y = horizon + (h - horizon) * (depth ** 1.85)
            if y > h + 4:
                break
            a = int(22 + 78 * depth)
            gd.line([(0, y), (w, y)], fill=C.GRID_INK + (a,), width=2)
            gd.line([(0, y + 2), (w, y + 2)], fill=C.GRID_SHADE + (int(a * 0.30),), width=2)
        fade = Image.new("L", (w, h), 0)
        fd = ImageDraw.Draw(fade)
        for y in range(horizon - 60, horizon + 150):
            fd.line([(0, y), (w, y)],
                    fill=int(255 * C.clamp((y - (horizon - 60)) / 190.0)))
        fd.rectangle([0, horizon + 150, w, h], fill=255)
        grid.putalpha(Image.composite(grid.split()[3], Image.new("L", (w, h), 0), fade))
        base = Image.alpha_composite(base.convert("RGBA"), grid).convert("RGB")
        return base

    def _build_vignette(self) -> Image.Image:
        w, h = C.W, C.H
        xx = np.arange(w, dtype=np.float32)[None, :] / w - 0.5
        yy = np.arange(h, dtype=np.float32)[:, None] / h - 0.5
        d = np.sqrt((xx * 1.02) ** 2 + (yy * 0.92) ** 2) / 0.72
        v = np.clip(1.0 - 0.30 * np.clip(d, 0, 1.2) ** 2.6, 0, 1)
        return Image.fromarray((v * 255).astype(np.uint8), "L")

    def _build_glow(self) -> Image.Image:
        w, h = C.W, C.H
        im = Image.new("L", (w // 4, h // 4), 0)
        ImageDraw.Draw(im).ellipse(
            [w // 4 * 0.18, h // 4 * 0.78, w // 4 * 0.82, h // 4 * 1.42], fill=120)
        return im.resize((w, h), Image.BICUBIC).filter(ImageFilter.GaussianBlur(50))

    def frame(self) -> Image.Image:
        f = self.bg.copy()
        f.paste((255, 255, 255), (0, 0), self.glow.point(lambda v: int(v * 0.5)))
        return f


# ================================================================ renderer
class Renderer:
    def __init__(self, sections, intro_narration, assets_dir, timeline, total_duration,
                 meta=None, sides=None):
        self.sections = sections
        self.meta = meta or META
        self.sides = sides or SIDES
        self.intro_narration = intro_narration
        self.intro_lines = wrap(self.meta["deck"], "reg", 23, 560, 4)
        self.assets = assets_dir
        self.tl = timeline
        self.total = total_duration
        self.stage = Stage()
        self._global_t = 0.0
        self._seg_dur = None
        self._broll_cache = {}

    def asset(self, key):
        if not key:
            return None
        p = os.path.join(self.assets, key + ".png")
        return p if os.path.exists(p) else None

    # ------------------------------------------------------------ chrome
    def top_bar(self, f, t, alpha=1.0):
        if alpha <= 0.01:
            return
        y = 54
        P.draw_flag_chip(f, C.SAFE, y, 42, self.sides["left"]["country"], self.sides["left"]["code"],
                         self.sides["left"]["accent"], alpha=alpha, dark=True)
        P.draw_flag_chip(f, C.W - C.SAFE, y, 42, self.sides["right"]["country"], self.sides["right"]["code"],
                         self.sides["right"]["accent"],
                         alpha=alpha, dark=True, align="right")
        P.draw_text(f, (C.W / 2, y - 2), self.meta["title"], "bold", 27, C.INK, tracking=10,
                    anchor="mt", alpha=alpha)
        P.draw_text(f, (C.W / 2, y + 36), self.meta["episode"], "reg", 14, C.INK_FAINT,
                    tracking=5, anchor="mt", alpha=alpha)
        py = 116
        d = ImageDraw.Draw(f, "RGBA")
        d.line([(C.SAFE, py), (C.W - C.SAFE, py)], fill=(150, 158, 168, 55), width=2)
        prog = C.clamp(t / max(0.1, self.total))
        d.line([(C.SAFE, py), (C.SAFE + (C.W - C.SAFE * 2) * prog, py)],
               fill=C.CHARCOAL + (225,), width=3)

    def bottom_bar(self, f, alpha=1.0, left_note=None, right_note=None, rule=True):
        if alpha <= 0.01:
            return
        y = 1006
        if rule:
            ImageDraw.Draw(f, "RGBA").line([(C.SAFE, y - 40), (C.W - C.SAFE, y - 40)],
                                           fill=(150, 158, 168, 65), width=2)
        P.draw_text(f, (C.SAFE, y), left_note or self.meta["disclaimer"], "reg", 16, C.INK_FAINT,
                    tracking=3, alpha=alpha)
        P.draw_text(f, (C.W - C.SAFE, y), right_note or self.meta["channel"], "bold", 16, C.INK_DIM,
                    tracking=3, anchor="rt", alpha=alpha)

    def side_wash(self, f, alpha=0.06):
        if alpha <= 0.001:
            return
        overlay = _wash_cache.get(alpha)
        if overlay is None:
            w, h = C.W, C.H
            xs = np.arange(w, dtype=np.float32) / w
            us = np.array(self.sides["left"]["accent"], dtype=np.float32)
            cn = np.array(self.sides["right"]["accent"], dtype=np.float32)
            lu = np.clip(1 - xs / 0.58, 0, 1) ** 1.7
            ru = np.clip((xs - 0.42) / 0.58, 0, 1) ** 1.7
            layer = us * lu[:, None] + cn * ru[:, None]
            layer = np.repeat(layer[None, :, :], h, axis=0)
            ys = np.arange(h, dtype=np.float32) / h
            mask = np.broadcast_to(
                (np.clip(1 - abs(ys - 0.44) * 1.15, 0, 1) ** 1.4)[:, None], (h, w))
            rgba = np.dstack([layer, (mask * alpha * 255)]).astype(np.uint8)
            overlay = Image.fromarray(rgba, "RGBA")
            _wash_cache[alpha] = overlay
        f.paste(overlay.convert("RGB"), (0, 0), overlay.split()[3])

    def divider(self, f, alpha=1.0, flash=0.0):
        if alpha <= 0.01:
            return
        d = ImageDraw.Draw(f, "RGBA")
        x = C.DIVIDER_X
        d.line([(x, 316), (x, 958)], fill=(120, 128, 138, int(60 * alpha)), width=2)
        if flash > 0.01:
            d.line([(x, 316), (x, 958)], fill=(255, 255, 255, int(170 * flash)), width=7)

    def chapter_head(self, f, sec, local):
        """Chapter header, centred over the seam so both halves stay balanced."""
        e = C.ramp(local, 0.05, 0.6, C.ease_out_expo)
        if e <= 0.01:
            return
        dy = (1 - e) * 22
        kicker = f"{sec['id']}   {sec['chapter']}"
        kw = tw(kicker, "bold", 15, 3.2) + 40
        P.draw_pill(f, C.DIVIDER_X - kw / 2, 138 + dy, kicker, size=15, fg=C.PAPER,
                    bg=C.CHARCOAL, tracking=3.2, pad_x=20, pad_y=9, alpha=e)
        size = P.fit_size(sec["title"], "bold", 900, 52, 1.6)
        P.draw_text(f, (C.DIVIDER_X, 182 + dy), sec["title"], "bold", size, C.INK,
                    tracking=3, anchor="mt", alpha=e)
        d = ImageDraw.Draw(f, "RGBA")
        ly = 182 + dy + size + 12
        d.line([(C.DIVIDER_X - 42 * e, ly), (C.DIVIDER_X + 42 * e, ly)],
               fill=C.CHARCOAL + (int(255 * e),), width=4)
        sf = sec["standfirst"]
        ssize = P.fit_size(sf, "reg", 980, 21, 0.4)
        P.draw_text(f, (C.DIVIDER_X, ly + 12), sf, "reg", ssize, C.INK_DIM, tracking=0.4,
                    anchor="mt", alpha=C.ramp(local, 0.28, 0.5) * e)

    def side_name(self, f, side, name, local, start=0.5, size=38, y=NAME_Y, sub=None):
        e = C.ramp(local, start, 0.55, C.ease_out_expo)
        if e <= 0.01:
            return
        accent = self.sides[side]["accent"]
        left = side == "left"
        x = C.SAFE + 6 if left else C.W - C.SAFE - 6
        dy = (1 - e) * 18
        sz = P.fit_size(name, "bold", 700, size, 3)
        w = tw(name, "bold", sz, 3)
        P.draw_text(f, (x, y + dy), name, "bold", sz, C.INK, tracking=3,
                    anchor="lt" if left else "rt", alpha=e)
        d = ImageDraw.Draw(f, "RGBA")
        bx = x if left else x - w
        d.line([(bx, y + dy - 12), (bx + w * e, y + dy - 12)],
               fill=accent + (int(230 * e),), width=5)

    def pill_times(self, dur=None):
        """When each spec pill lands, in seconds from the chapter start."""
        dur = dur if dur is not None else (self._seg_dur or 12.0)
        if dur >= 9.0:
            return (1.5, 4.0, 6.5)
        # short chapter: keep the three beats inside it
        return (0.8, max(1.8, dur * 0.40), max(2.6, min(dur - 1.2, dur * 0.68)))

    def spec_pills(self, f, side, specs, local, times=None, size=19, y0=PILL_Y):
        times = times or self.pill_times()
        accent = self.sides[side]["accent"]
        for i, (label, lv, rv) in enumerate(specs or ()):
            value = lv if side == "left" else rv
            t0 = times[min(i, len(times) - 1)]
            e = C.ramp(local, t0, 0.45, C.ease_out_back)
            if e <= 0.01:
                continue
            lw = tw(label, "bold", 14, 3.0)
            vw = tw(value, "bold", size, 0.4)
            pad = 20
            h = PILL_H
            w = int(lw + vw + pad * 2 + 18) + 8
            dx = (1 - e) * 80 * (1 if side == "left" else -1)
            x = C.SAFE + 6 if side == "left" else C.W - C.SAFE - 6 - w
            x += dx
            y = y0 + i * (h + PILL_GAP)
            rgb, m = P.rounded(w, h, 16, C.CHARCOAL)
            f.paste(rgb, (int(x), int(y)), m.point(lambda q: int(q * min(1.0, e))))
            d = ImageDraw.Draw(f, "RGBA")
            d.rectangle([x + 2, y + 12, x + 4, y + h - 12], fill=accent + (int(230 * e),))
            P.draw_text(f, (x + pad, y + h / 2), label, "bold", 14, (146, 154, 164),
                        tracking=3.0, anchor="lm", alpha=e)
            P.draw_text(f, (x + pad + lw + 18, y + h / 2), value, "bold", size, C.PAPER,
                        tracking=0.4, anchor="lm", alpha=e)

    # ------------------------------------------------------------ intro
    def draw_intro(self, f, local, dur):
        """Hook: numbers first, then the two soldiers take turns stepping forward."""
        self.side_wash(f, 0.085)

        # headline (top bar keeps the brand, so the hero line is the question)
        e1 = C.ramp(local, 0.05, 0.7, C.ease_out_expo)
        P.draw_text(f, (C.W / 2, 130 - (1 - e1) * 30), self.meta["hero_a"], "bold", 88, C.INK,
                    tracking=7, anchor="mt", alpha=e1)
        e1b = C.ramp(local, 0.2, 0.7, C.ease_out_expo)
        P.draw_text(f, (C.W / 2, 212 - (1 - e1b) * 26), self.meta["hero_b"], "bold", 88,
                    C.INK_DIM, tracking=7, anchor="mt", alpha=e1b)

        # the two soldiers; each one pops forward on its own narration line
        for side, key, cx, cue in self.meta.get("hero_sprites",
                 (("left", "soldier_us", 350, 0.35),
                  ("right", "soldier_cn", 1570, 3.10))):
            path = self.asset(key)
            if not path:
                continue
            e = C.ramp(local, 0.35, 1.15, C.ease_out_expo)
            off = (1 - e) * 260 * (1 if side == "left" else -1)
            pop = C.pulse(local, cue, 1.9)
            dim = C.pulse(local, cue + 1.9, 1.9) * 0.0  # reserved
            paste_object(f, path, cx + off, 948 - 10 * pop, 480, 560,
                         alpha=e * (1 - dim), shadow_scale=1.05 + 0.06 * pop,
                         scale_boost=1.0 + 0.045 * pop)
            # a thin accent bracket under the active figure
            if pop > 0.02:
                d = ImageDraw.Draw(f, "RGBA")
                a = int(200 * pop)
                bw = 120
                bx, by = cx - bw / 2, 972
                d.line([(bx, by), (bx + bw, by)],
                       fill=self.sides[side]["accent"] + (a,), width=4)

        # centre copy block
        e2 = C.ramp(local, 0.5, 0.8, C.ease_out_expo)
        parts = [("USA", self.sides["left"]["accent"]), ("  ×  ", C.INK_FAINT),
                 ("CHINA", self.sides["right"]["accent"])]
        widths = [tw(p, "bold", 44, 8) for p, _ in parts]
        x = C.W / 2 - sum(widths) / 2
        for (p, col), w in zip(parts, widths):
            P.draw_text(f, (x, 372 - (1 - e2) * 18), p, "bold", 44, col, tracking=8, alpha=e2)
            x += w
        d = ImageDraw.Draw(f, "RGBA")
        e3 = C.ramp(local, 0.7, 0.8, C.ease_in_out)
        d.line([(C.W / 2 - 240 * e3, 440), (C.W / 2 + 240 * e3, 440)],
               fill=(140, 148, 158, 120), width=2)
        e4 = C.ramp(local, 0.9, 0.7)
        for i, ln in enumerate(self.intro_lines):
            P.draw_text(f, (C.W / 2, 460 + i * 32), ln, "reg", 22, C.INK_DIM, tracking=0.4,
                        anchor="mt", alpha=e4)
        # key numbers under the copy, so the hook lands with data
        e5 = C.ramp(local, 1.6, 0.6)
        P.draw_text(f, (C.W / 2, 604), self.meta["hero_stat"], "bold", 20, C.INK_FAINT,
                    tracking=8, anchor="mt", alpha=e5)
        # dolly the stage + soldiers, then lay the UI on top so it stays sharp
        f = camera(f, 1.0 + 0.05 * C.ease_in_out(C.clamp(local / max(0.1, dur))),
                   cy=C.H * 0.52)
        self.top_bar(f, local, C.ramp(local, 0.05, 0.6))
        self.bottom_bar(f, C.ramp(local, 0.7, 0.7),
                        left_note="19 TYPES   ·   ONE QUESTION   ·   OPEN SOURCES", rule=False)
        return f

    # ------------------------------------------------------------ end card
    def draw_endcard(self, f, local):
        self.side_wash(f, 0.05)
        e = C.ramp(local, 0.1, 0.9)
        P.draw_text(f, (C.W / 2, 392), "GEAR COMPARED", "bold", 118, C.INK, tracking=13,
                    anchor="mt", alpha=e)
        P.draw_text(f, (C.W / 2, 552), "USA  ×  CHINA   ·   SOLDIER", "bold", 40, C.INK_DIM,
                    tracking=9, anchor="mt", alpha=C.ramp(local, 0.6, 0.8))
        P.draw_text(f, (C.W / 2, 648), "18 ITEMS   ·   ONE QUESTION", "reg", 24, C.INK_FAINT,
                    tracking=7, anchor="mt", alpha=C.ramp(local, 1.0, 0.8))
        d = ImageDraw.Draw(f, "RGBA")
        w = 300 * C.ramp(local, 1.2, 0.9, C.ease_in_out)
        d.line([(C.W / 2 - w, 740), (C.W / 2 + w, 740)], fill=(140, 148, 158, 110), width=2)

    # ------------------------------------------------------------ dispatch
    def draw_section(self, f, sec, local, idx):
        """Camera dollies the showroom; the UI is composited on top, post-zoom,
        so flags/rules/counters stay pixel-crisp and never drift at the edges."""
        kind = sec["kind"]
        self._sec_dur = self._seg_dur or 12.0
        self.side_wash(f, 0.055)

        br = sec.get("broll")
        is_broll = bool(br and local < br.get("secs", 3.4)
                        and self.broll_source(br["clip"]))
        if is_broll:
            # footage is already 1080p: grade it, no dolly, so it stays sharp
            self.draw_broll(f, sec, br, local)
        else:
            getattr(self, "scene_" + kind, self.scene_duel)(f, sec, local)
            z = 1.0 + 0.035 * C.ease_in_out(C.clamp(local / max(0.1, self._sec_dur)))
            f = camera(f, z, cy=C.H * 0.52)

        # ---- UI layer (fixed, sharp) ----
        flash = C.pulse(local, 0.0, 0.8)
        if kind != "outro" and not is_broll:
            self.divider(f, C.ramp(local, 0.0, 0.5), flash=flash * 0.8)
        if kind != "outro" and not is_broll:
            self.chapter_head(f, sec, local)
        self.top_bar(f, self._global_t, 1.0)
        if not is_broll:
            self.bottom_bar(f, C.ramp(local, 0.4, 0.5))
            P.draw_text(f, (C.DIVIDER_X, 1006), f"{sec['id']} / {len(self.sections):02d}",
                        "mono_bold", 15, C.INK_FAINT, tracking=5, anchor="mt",
                        alpha=C.ramp(local, 0.5, 0.5))
        return f

    # -------------------------------------------------- scene: b-roll
    # Two sources, same look:
    #   1. real footage  -> build/broll/<clip>/00000.png  (video/broll.py)
    #   2. still board   -> assets/broll/<clip>.jpg       (2.5D parallax move)
    def broll_source(self, clip):
        if clip in self._broll_cache:
            return self._broll_cache[clip]
        still = None
        for ext in (".jpg", ".jpeg", ".png"):
            p = os.path.join(self.assets, "broll", clip + ext)
            if os.path.exists(p):
                still = p
                break
        frames = os.path.join(os.path.dirname(self.assets), "build", "broll", clip)
        if os.path.isdir(frames) and os.listdir(frames):
            src = ("frames", frames)          # real footage always wins
        elif still:
            src = ("still", still)
        else:
            src = None
        self._broll_cache[clip] = src
        return src

    def broll_frame(self, clip, local):
        src = self.broll_source(clip)
        if not src:
            return None
        kind, path = src
        try:
            if kind == "still":
                return Image.open(path).convert("RGB")
            idx = max(0, int(local * 30))
            p = os.path.join(path, f"{idx:05d}.png")
            if not os.path.exists(p):
                files = sorted(os.listdir(path))
                if not files:
                    return None
                p = os.path.join(path, files[min(idx, len(files) - 1)])
            return Image.open(p).convert("RGB")
        except Exception:
            return None

    def ken_burns(self, img, t):
        """2.5D move on a still: sharp plate pushes in, blurred bed drifts back."""
        w, h = C.W, C.H
        src = img.convert("RGB")

        def cover(zoom, dx, dy, blur=0):
            sw, sh = int(src.width * zoom), int(src.height * zoom)
            if sw < w or sh < h:                      # never crop past the plate
                k = max(w / sw, h / sh)
                sw, sh = int(sw * k), int(sh * k)
            big = src.resize((sw, sh), Image.BICUBIC)
            x = (sw - w) / 2 + dx * sw
            y = (sh - h) / 2 + dy * sh
            x = C.clamp(x, 0, sw - w)
            y = C.clamp(y, 0, sh - h)
            out = big.crop((int(x), int(y), int(x) + w, int(y) + h))
            return out.filter(ImageFilter.GaussianBlur(blur)) if blur else out

        e = C.ease_in_out(C.clamp(t))
        plate = cover(1.02 + 0.10 * e, 0.010 * e, -0.008 * e)
        bed = cover(1.55 + 0.25 * e, -0.02 * e, 0.015 * e, blur=30)
        bed = Image.blend(bed, Image.new("RGB", (w, h), (9, 12, 17)), 0.45)
        # soft-edged mask so the plate melts into the bed instead of looking pasted
        mx, my = int(w * 0.05), int(h * 0.07)
        mask = Image.new("L", (w, h), 0)
        inner = Image.new("L", (w - 2 * mx, h - 2 * my), 255)
        mask.paste(inner, (mx, my))
        mask = mask.filter(ImageFilter.GaussianBlur(40))
        out = bed.copy()
        out.paste(plate, (0, 0), mask)
        return out

    def grade(self, img, local, secs):
        """Cinema grade + grain + vignette so a still reads as motion footage."""
        w, h = C.W, C.H
        arr = np.asarray(img.convert("RGB")).astype(np.float32) / 255.0

        # cool shadows, warm highlights, slight S-curve
        arr = arr * 1.06 - 0.02
        arr[..., 2] += 0.035 * (1.0 - arr.mean(axis=2))      # cool in the shadows
        arr[..., 0] += 0.030 * arr.mean(axis=2)              # warm in the highs
        arr = np.clip(arr, 0, 1) ** 1.04
        arr = np.clip(arr, 0, 1)

        # vignette (cheap radial falloff)
        yy, xx = np.mgrid[0:h, 0:w]
        r = np.sqrt(((xx - w / 2) / (w * 0.62)) ** 2 + ((yy - h / 2) / (h * 0.62)) ** 2)
        arr *= np.clip(1.0 - 0.55 * np.clip(r - 0.45, 0, 2) ** 1.4, 0.15, 1.0)[..., None]

        # grain: one tiling plate, shifted per frame so it shimmers
        g = np.asarray(_grain()).astype(np.float32) / 255.0 - 0.5
        off = _grain_offset(local) % max(1, g.shape[1] - w)
        arr += g[:, off:off + w, None] * 0.09
        return Image.fromarray((np.clip(arr, 0, 1) * 255).astype(np.uint8), "RGB")

    def draw_broll(self, f, sec, br, local):
        """Full-screen insert: field plate, caption capsule, provenance line."""
        clip = br["clip"]
        img = self.broll_frame(clip, local)
        if img is None:
            return
        secs = br.get("secs", 3.4)
        t = C.clamp(local / max(0.1, secs))
        if self.broll_source(clip)[0] == "still":
            frame = self.grade(self.ken_burns(img, t), local, secs)
        else:
            frame = img.resize((C.W, C.H), Image.BILINEAR)
            frame = self.grade(frame, local, secs)
        f.paste(frame, (0, 0))

        # in/out fades
        # fade IN from black, then fade OUT just before the cut back to the studio
        fade = C.ramp(local, 0.0, 0.4) * (1.0 - C.ramp(local, secs - 0.45, 0.45))
        if fade < 0.999:
            f.paste((9, 11, 15), (0, 0), Image.new("L", (C.W, C.H), int(255 * (1 - fade))))

        # top scrim: the brand row must read over sky/highlights
        gt = Image.new("L", (1, C.H), 0)
        gtd = ImageDraw.Draw(gt)
        for y in range(C.H):
            gtd.point((0, y), fill=int(190 * C.clamp((175 - y) / 175) ** 1.2))
        f.paste((7, 9, 13), (0, 0), gt.resize((C.W, C.H), Image.BILINEAR))

        # bottom gradient for legibility
        g = Image.new("L", (1, C.H), 0)
        gd = ImageDraw.Draw(g)
        for y in range(C.H):
            gd.point((0, y), fill=int(205 * C.clamp((y - C.H * 0.52) / (C.H * 0.48)) ** 1.5))
        f.paste((7, 9, 13), (0, 0), g.resize((C.W, C.H), Image.BILINEAR))

        ea = C.ramp(local, 0.1, 0.45)
        P.draw_pill(f, C.SAFE, 150, br.get("kicker", "FIELD · RECONSTRUCTION"),
                    size=14, fg=C.PAPER, bg=(16, 19, 24), tracking=3.4, pad_x=20,
                    pad_y=10, alpha=ea)
        tag = f"{sec['id']}   {sec['chapter']}"
        tw_ = tw(tag, "bold", 14, 3.4) + 40
        P.draw_pill(f, C.W - C.SAFE - tw_, 150, tag, size=14, fg=(216, 221, 228),
                    bg=(16, 19, 24), tracking=3.4, pad_x=20, pad_y=10, alpha=ea)
        P.draw_text(f, (C.SAFE, 824), br.get("label", sec["title"]), "bold", 60, C.PAPER,
                    tracking=4, alpha=ea)
        P.draw_text(f, (C.SAFE, 906), br.get("credit", "ILLUSTRATIVE RECONSTRUCTION"),
                    "reg", 14, (190, 196, 204), tracking=3, alpha=ea)
        # keep the running progress rail above the footage
        d = ImageDraw.Draw(f, "RGBA")
        py = 116
        prog = C.clamp(self._global_t / max(0.1, self.total))
        d.line([(C.SAFE, py), (C.W - C.SAFE, py)], fill=(255, 255, 255, 42), width=2)
        d.line([(C.SAFE, py), (C.SAFE + (C.W - C.SAFE * 2) * prog, py)],
               fill=(255, 255, 255, 190), width=3)

    # -------------------------------------------------- scene: duel
    def scene_duel(self, f, sec, local, box=(640, 300), baseline=612, name_y=NAME_Y,
                   pill_y=PILL_Y, cx_off=452):
        flips = set(sec.get("flip", ()))
        for side in ("left", "right"):
            path = self.asset(sec["assets"].get(side))
            cx = C.DIVIDER_X - cx_off if side == "left" else C.DIVIDER_X + cx_off
            e = C.ramp(local, 0.14, 0.95, C.ease_out_expo)
            off = (1 - e) * 160 * (1 if side == "left" else -1)
            if path:
                paste_object(f, path, cx + off, baseline, box[0], box[1], alpha=e,
                             lift=(1 - e) * 34, flip=side in flips)
            self.side_name(f, side, sec["names"][side], local, start=0.5, y=name_y)
            self.spec_pills(f, side, sec.get("specs") or (), local, y0=pill_y)

    # -------------------------------------------------- scene: bars
    def scene_bars(self, f, sec, local):
        b = sec["bars"]
        seam = C.DIVIDER_X
        span, h, bar_y = 600, 82, 470
        for side in ("left", "right"):
            accent = self.sides[side]["accent"]
            e = C.ramp(local, 0.3, 1.0, C.ease_out_expo)
            val = b["left"] if side == "left" else b["right"]
            w = span * C.clamp(val / b["max"]) * e
            if side == "left":
                x = seam - 96 - w
                P.draw_text(f, (x - 26, bar_y + h / 2), b["left_label"], "bold", 54, accent,
                            tracking=1, anchor="rm", alpha=C.ramp(local, 0.85, 0.5))
            else:
                x = seam + 96
                P.draw_text(f, (x + w + 26, bar_y + h / 2), b["right_label"], "bold", 54,
                            accent, tracking=1, anchor="lm", alpha=C.ramp(local, 0.85, 0.5))
            rgb, m = P.rounded(int(max(4, w)), h, 12, accent)
            f.paste(rgb, (int(x), bar_y), m)
            # track
            d = ImageDraw.Draw(f, "RGBA")
            tx0 = seam - 96 - span
            d.line([(tx0, bar_y + h / 2), (seam - 96, bar_y + h / 2)],
                   fill=(120, 128, 138, 45), width=3)
            d.line([(seam + 96, bar_y + h / 2), (seam + 96 + span, bar_y + h / 2)],
                   fill=(120, 128, 138, 45), width=3)
            # name + service
            ne = C.ramp(local, 0.45, 0.6)
            nx = C.SAFE + 6 if side == "left" else C.W - C.SAFE - 6
            P.draw_text(f, (nx, 386), sec["names"][side], "bold", 36, C.INK, tracking=3,
                        anchor="lt" if side == "left" else "rt", alpha=ne)
            P.draw_text(f, (nx, 432), self.sides[side]["force"], "reg", 16, C.INK_FAINT,
                        tracking=4, anchor="lt" if side == "left" else "rt", alpha=ne)
            if sec.get("specs"):
                self.spec_pills(f, side, sec.get("specs") or (), local, y0=PILL_Y)
        # unit caption above the seam
        if b.get("unit"):
            P.draw_text(f, (seam, bar_y - 74), b["unit"], "bold", 17, C.INK_FAINT,
                        tracking=7, anchor="mt", alpha=C.ramp(local, 0.7, 0.6))
        # scale ticks
        ua = C.ramp(local, 0.8, 0.6)
        d = ImageDraw.Draw(f, "RGBA")
        a = int(80 * ua)
        for i in range(5):
            for sx in (seam - 96 - span * i / 4, seam + 96 + span * i / 4):
                d.line([(sx, bar_y + h + 18), (sx, bar_y + h + 30)],
                       fill=(110, 118, 128, a), width=2)
        d.line([(seam - 96 - span, bar_y + h + 24), (seam + 96 + span, bar_y + h + 24)],
               fill=(110, 118, 128, a), width=1)

    # -------------------------------------------------- scene: swatch
    def scene_swatch(self, f, sec, local):
        w, h, y = 620, 268, 360
        for side in ("left", "right"):
            e = C.ramp(local, 0.18, 0.9, C.ease_out_expo)
            off = (1 - e) * 130 * (1 if side == "left" else -1)
            cx = C.DIVIDER_X - 440 if side == "left" else C.DIVIDER_X + 440
            x = cx - w / 2 + off
            pat = _camo(side, w, h)
            sh = Image.new("L", (w + 160, h + 160), 0)
            ImageDraw.Draw(sh).rounded_rectangle([80, 80, w + 80, h + 80], radius=22, fill=85)
            sh = sh.filter(ImageFilter.GaussianBlur(30)).point(lambda v: int(v * e * 0.9))
            f.paste((28, 31, 36), (int(x - 80), int(y - 60)), sh)
            sprite = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            sprite.paste(pat, (0, 0))
            paste_rgba(f, sprite, (x, y), e)
            ne = C.ramp(local, 0.6, 0.6)
            P.draw_text(f, (x + 26, y + 22), sec["names"][side], "bold", 38, C.PAPER,
                        tracking=4, alpha=ne)
            P.draw_flag_chip(f, x + 26, y + h - 74, 36, self.sides[side]["country"],
                             self.sides[side]["code"], self.sides[side]["accent"], alpha=ne, dark=True)
            self.spec_pills(f, side, sec.get("specs") or (), local, y0=PILL_Y)
        for side in ("left", "right"):
            nx = C.SAFE + 6 if side == "left" else C.W - C.SAFE - 6
            P.draw_text(f, (nx, 648), "PATTERN", "bold", 13, C.INK_FAINT, tracking=6,
                        anchor="lt" if side == "left" else "rt",
                        alpha=C.ramp(local, 0.7, 0.5))
            P.draw_text(f, (nx, 668), sec["names"][side], "bold", 28, C.INK,
                        tracking=3, anchor="lt" if side == "left" else "rt",
                        alpha=C.ramp(local, 0.75, 0.5))

    # -------------------------------------------------- scene: ammo
    def scene_ammo(self, f, sec, local):
        for side in ("left", "right"):
            e = C.ramp(local, 0.22, 1.0, C.ease_out_expo)
            cx = C.DIVIDER_X - 430 if side == "left" else C.DIVIDER_X + 430
            accent = self.sides[side]["accent"]
            cal = sec["bullets"][side]
            spr = _cartridge(cal, int(112 * (cal / 6.8) ** 0.9))
            off = (1 - e) * 150 * (1 if side == "left" else -1)
            x = cx - spr.width / 2 + off
            y = 560 - spr.height
            sh = Image.new("L", (spr.width + 140, 70), 0)
            ImageDraw.Draw(sh).ellipse([70, 18, spr.width + 70, 62], fill=80)
            sh = sh.filter(ImageFilter.GaussianBlur(14)).point(lambda v: int(v * e))
            f.paste((28, 31, 36), (int(x - 70), 566), sh)
            paste_rgba(f, spr, (x, y), e)
            d = ImageDraw.Draw(f, "RGBA")
            a = int(140 * e)
            d.line([(x - 6, 576), (x + spr.width + 6, 576)], fill=(120, 128, 138, a), width=2)
            for xx in (x, x + spr.width):
                d.line([(xx, 570), (xx, 584)], fill=(120, 128, 138, a), width=2)
            self.side_name(f, side, sec["names"][side], local, start=0.55, y=NAME_Y, size=34)
            self.spec_pills(f, side, sec.get("specs") or (), local, y0=PILL_Y)

    # -------------------------------------------------- scene: list
    def scene_list(self, f, sec, local):
        for side in ("left", "right"):
            accent = self.sides[side]["accent"]
            left = side == "left"
            ne = C.ramp(local, 0.35, 0.6)
            nx = C.SAFE + 6 if left else C.W - C.SAFE - 6
            P.draw_text(f, (nx, 356), sec["names"][side], "bold", 42, C.INK, tracking=4,
                        anchor="lt" if left else "rt", alpha=ne)
            P.draw_text(f, (nx, 408), self.sides[side]["force"], "reg", 16, C.INK_FAINT,
                        tracking=4, anchor="lt" if left else "rt", alpha=ne)
            for i, it in enumerate(sec["list"][side]):
                e = C.ramp(local, 0.6 + i * 0.16, 0.5, C.ease_out_expo)
                if e <= 0.01:
                    continue
                y = 470 + i * 56
                d = ImageDraw.Draw(f, "RGBA")
                bx = (nx + (1 - e) * 50) if left else (nx - 14 - (1 - e) * 50)
                d.rectangle([bx, y + 6, bx + 13, y + 19], fill=accent + (int(245 * e),))
                size = P.fit_size(it, "reg", 600, 23)
                tx = bx + 26 if left else bx - 12
                P.draw_text(f, (tx, y), it, "reg", size, C.INK, tracking=0.2,
                            anchor="lt" if left else "rt", alpha=e)
            self.spec_pills(f, side, sec.get("specs") or (), local, y0=PILL_Y)

    # -------------------------------------------------- scene: stat
    def scene_stat(self, f, sec, local):
        for side in ("left", "right"):
            st = sec["stats"][side]
            accent = self.sides[side]["accent"]
            cx = C.DIVIDER_X - 430 if side == "left" else C.DIVIDER_X + 430
            e = C.ramp(local, 0.18, 0.9, C.ease_out_expo)
            hb, hm = P.hex_badge(330, (236, 239, 243), "")
            f.paste(hb, (int(cx - 165), int(STAGE_TOP + 10 + (1 - e) * 30)),
                    hm.point(lambda v: int(v * e * 0.9)))
            ve = C.ramp(local, 0.3, 0.8, C.ease_out_back)
            vsize = P.fit_size(st["value"], "bold", 290, 150, 2)
            P.draw_text(f, (cx, STAGE_TOP + 148), st["value"], "bold",
                        int(vsize * (0.92 + 0.08 * ve)), accent, tracking=2,
                        anchor="mm", alpha=min(1.0, ve * 1.2))
            P.draw_text(f, (cx, STAGE_TOP + 226), st["unit"], "bold", 40, C.INK_DIM,
                        tracking=10, anchor="mt", alpha=C.ramp(local, 0.5, 0.6))
            P.draw_text(f, (cx, STAGE_TOP + 286), st["note"], "reg", 20, C.INK_FAINT,
                        tracking=1, anchor="mt", alpha=C.ramp(local, 0.7, 0.6))
            self.side_name(f, side, sec["names"][side], local, start=0.65, y=660, size=32)
            self.spec_pills(f, side, sec.get("specs") or (), local, y0=722)

    # -------------------------------------------------- scene: outro
    def scene_outro(self, f, sec, local):
        self.side_wash(f, 0.09)
        e = C.ramp(local, 0.1, 0.8, C.ease_out_expo)
        P.draw_text(f, (C.DIVIDER_X, 138), sec["chapter"], "bold", 18, C.INK_FAINT,
                    tracking=10, anchor="mt", alpha=e)
        P.draw_text(f, (C.DIVIDER_X, 168), sec["title"], "bold", 84, C.INK, tracking=9,
                    anchor="mt", alpha=e)
        P.draw_text(f, (C.DIVIDER_X, 274), sec["standfirst"], "reg", 27, C.INK_DIM,
                    tracking=0.6, anchor="mt", alpha=C.ramp(local, 0.45, 0.7))

        # verdict table: small label on the seam, each side answers on its own half
        for i, (label, lv, rv) in enumerate(sec.get("specs") or ()):
            ea = C.ramp(local, 0.7 + i * 0.16, 0.55, C.ease_out_expo)
            if ea <= 0.01:
                continue
            y = 330 + i * 76
            if i:
                ImageDraw.Draw(f, "RGBA").line(
                    [(C.DIVIDER_X - 420, y - 14), (C.DIVIDER_X + 420, y - 14)],
                    fill=(140, 148, 158, int(50 * ea)), width=1)
            P.draw_text(f, (C.DIVIDER_X, y), label, "bold", 13, C.INK_FAINT, tracking=5,
                        anchor="mt", alpha=ea * 0.9)
            P.draw_text(f, (C.DIVIDER_X - 30, y + 24), lv, "bold", 23,
                        self.sides["left"]["accent"], tracking=0.4, anchor="rt", alpha=ea)
            P.draw_text(f, (C.DIVIDER_X + 30, y + 24), rv, "bold", 23,
                        self.sides["right"]["accent"], tracking=0.4, anchor="lt", alpha=ea)

        for side in ("left", "right"):
            path = self.asset((sec.get("assets") or {}).get(side)) if sec.get("assets") else None
            cx = 340 if side == "left" else 1580
            ea = C.ramp(local, 0.5, 1.0, C.ease_out_expo)
            off = (1 - ea) * 220 * (1 if side == "left" else -1)
            if path:
                paste_object(f, path, cx + off, 902, 430, 430, alpha=ea)
            ne = C.ramp(local, 0.95, 0.6)
            nx = C.SAFE + 6 if side == "left" else C.W - C.SAFE - 6
            P.draw_text(f, (nx, 924), sec["names"][side], "bold", 24, C.INK, tracking=4,
                        anchor="lt" if side == "left" else "rt", alpha=ne)
