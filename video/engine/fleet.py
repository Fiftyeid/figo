"""FLEET: the same showroom, retooled for a one-country inventory.

The USA-vs-CHINA film is a duel, so its chrome is split down the middle.
This variant keeps the identical stage, type ramp, pills and motion, but
drops the seam: one country, one aircraft at a time, a rotating roster of
types under the hero, and the count on the spec rail.

`FleetRenderer` subclasses the duel renderer, so every shared behaviour
(stage, dolly-and-stick camera, grain, pills) comes from the engine and
only the chrome + the section layout are new.
"""
from __future__ import annotations

import os
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from . import config as C
from . import pixels as P
from .scenes import Renderer, fit, paste_rgba, tw, wrap

META_JP = {
    "title": "AIR FLEET 2026",
    "subtitle": "JAPAN — SELF-DEFENSE FORCES",
    "channel": "HIKKA / STYLE STUDY",
    "episode": "FLEET INVENTORY  /  EP. 03",
    "disclaimer": "OPEN-SOURCE DATA · ILLUSTRATIVE RENDERS",
    "hero_a": "EVERY AIRCRAFT",
    "hero_b": "JAPAN FLIES IN 2026",
    "hero_stat": "19 TYPES   ·   8 CHAPTERS   ·   ONE ISLAND NATION",
    "deck": "Fighters, gunships, patrol planes, tankers, trainers and drones — "
            "the whole fleet, one type at a time.",
    "country": "jp",
    "code": "JPN",
    "name": "JAPAN",
}

JP_RED = (188, 0, 45)
JP_RED_DEEP = (140, 0, 34)
JP_SLATE = (52, 62, 74)

# layout for the single-subject scene
_CUE_CACHE: dict = {}

FLEET_BASE = 806          # where the aircraft "rests" on the showroom floor
FLEET_BOX = (1230, 436)   # max sprite box (w, h)
HEAD_PILL_Y = 144
HEAD_NAME_Y = 184
NAME_MIN = 40


def _fit_h(path: str, box_w: int, box_h: int) -> Image.Image:
    return fit(path, box_w, box_h)


class FleetRenderer(Renderer):
    def __init__(self, sections, intro_narration, assets_dir, timeline, total_duration):
        super().__init__(sections, intro_narration, assets_dir, timeline, total_duration)
        self.intro_lines = wrap(META_JP["deck"], "reg", 23, 760, 3)

    # ------------------------------------------------------------ helpers
    def cue_times(self, sec):
        """When each type is actually named in the narration.

        The visual roster has to change *on the word*, so the boundaries are
        taken from the script itself: find where each aircraft is first
        mentioned, turn that character offset into a share of the measured
        voiceover, and use it as the cut point.  Falls back to an even split
        when a type is never named.
        """
        key = (sec.get("id"), round(self._seg_dur or 0, 2))
        cached = _CUE_CACHE.get(key)
        if cached is not None:
            return cached

        items = sec["items"]
        dur = self._seg_dur or 12.0
        vo_start, vo_len = 0.35, max(0.5, dur - 0.35 - 0.45)
        text = (sec.get("narration") or "").lower()

        marks = []
        for it in items:
            cue = (it.get("cue") or it["name"]).lower()
            best = -1
            for cand in [cue] + [w.lower() for w in it["name"].replace("-", " ").split()]:
                if len(cand) < 3:
                    continue
                pos = text.find(cand)
                if pos >= 0 and (best < 0 or pos < best):
                    best = pos
            marks.append(best / max(1, len(text)) if best >= 0 else None)

        known = [m for m in marks if m is not None]
        if len(known) < len(items):
            # fill unknowns between their neighbours so the order is stable
            for i, m in enumerate(marks):
                if m is not None:
                    continue
                before = next((marks[j] for j in range(i - 1, -1, -1) if marks[j] is not None), 0.0)
                after = next((marks[j] for j in range(i + 1, len(marks)) if marks[j] is not None), 1.0)
                marks[i] = (before + after) / 2
        marks[0] = 0.0 if marks[0] is None else min(marks[0], 0.35)
        for i in range(1, len(marks)):
            marks[i] = max(marks[i], marks[i - 1] + 0.06)

        times = [vo_start + m * vo_len for m in marks]
        times[0] = 0.0          # the first type holds from the chapter cut
        times.append(dur)
        _CUE_CACHE[key] = times
        return times

    def item_at(self, sec, local):
        times = self.cue_times(sec)
        idx = len(times) - 2
        for i in range(len(times) - 1):
            if local < times[i + 1]:
                idx = i
                break
        t0, t1 = times[idx], times[idx + 1]
        return idx, local - t0, max(0.4, t1 - t0)

    # ------------------------------------------------------------ chrome
    def divider(self, f, alpha=1.0, flash=0.0):     # no seam in a solo film
        return

    def top_bar(self, f, t, alpha=1.0):
        if alpha <= 0.01:
            return
        y = 54
        P.draw_flag_chip(f, C.SAFE, y, 42, "jp", "JPN", JP_SLATE, alpha=alpha, dark=True)
        # right side: the year, in a pill, mirrors the flag chip's weight
        P.draw_pill(f, C.W - C.SAFE, y + 1, "2026", size=21, fg=C.PAPER, bg=JP_RED,
                    tracking=3, pad_x=20, pad_y=10, alpha=alpha, align="right")
        P.draw_text(f, (C.W / 2, y - 2), META_JP["title"], "bold", 27, C.INK, tracking=10,
                    anchor="mt", alpha=alpha)
        P.draw_text(f, (C.W / 2, y + 36), META_JP["episode"], "reg", 14, C.INK_FAINT,
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
        P.draw_text(f, (C.SAFE, y), left_note or META_JP["disclaimer"], "reg", 16,
                    C.INK_FAINT, tracking=3, alpha=alpha)
        P.draw_text(f, (C.W - C.SAFE, y), right_note or META_JP["channel"], "bold", 16,
                    C.INK_DIM, tracking=3, anchor="rt", alpha=alpha)

    def side_wash(self, f, alpha=0.06):
        """One soft red/graphite wash instead of the US/CN two-tone."""
        if alpha <= 0.001:
            return
        overlay = _jp_wash(alpha)
        f.paste(overlay.convert("RGB"), (0, 0), overlay.split()[3])

    # ------------------------------------------------------------ header
    def chapter_head(self, f, sec, local):
        if sec.get("kind") != "fleet":
            return super().chapter_head(f, sec, local)
        idx, u, _ = self.item_at(sec, local)
        it = sec["items"][idx]

        e = C.ramp(local, 0.05, 0.6, C.ease_out_expo)
        dy = (1 - e) * 20
        kicker = f"{sec['id']}   {sec['chapter']}"
        kw = tw(kicker, "bold", 15, 3.2) + 40
        P.draw_pill(f, C.W / 2 - kw / 2, HEAD_PILL_Y + dy, kicker, size=15, fg=C.PAPER,
                    bg=C.CHARCOAL, tracking=3.2, pad_x=20, pad_y=9, alpha=e)

        # the type name re-announces itself on every roster change
        ne = C.ramp(u, 0.0, 0.5, C.ease_out_expo)
        size = P.fit_size(it["name"], "bold", 1060, 64, 4)
        ny = HEAD_NAME_Y - (1 - ne) * 14
        P.draw_text(f, (C.W / 2, ny), it["name"], "bold", size, C.INK, tracking=4,
                    anchor="mt", alpha=ne)
        ly = ny + size + 16
        w = 46 * ne
        d = ImageDraw.Draw(f, "RGBA")
        d.line([(C.W / 2 - w, ly), (C.W / 2 + w, ly)], fill=JP_RED + (int(235 * ne),), width=4)
        sf = sec.get("standfirst")
        if sf:
            ssize = P.fit_size(sf, "reg", 1020, 21, 0.4)
            P.draw_text(f, (C.W / 2, ly + 12), sf, "reg", ssize, C.INK_DIM, tracking=0.4,
                        anchor="mt", alpha=C.ramp(local, 0.3, 0.6) * e)

    # ------------------------------------------------------------ scene
    def scene_fleet(self, f, sec, local):
        idx, u, step = self.item_at(sec, local)
        it = sec["items"][idx]
        items = sec["items"]

        # stage glow under the aircraft
        f.paste((255, 255, 255), (0, 0), _fleet_glow())

        e = C.ramp(u, 0.0, 0.55, C.ease_out_expo)
        e_fade = C.ramp(u, max(0.0, step - 0.32), 0.32, C.ease_in_out)
        alpha = e * (1.0 - 0.55 * e_fade * (0 if idx == len(items) - 1 else 1))

        path = self.asset(it["asset"])
        if path:
            paste_object_lift = 30 * (1 - e)
            self._hero(f, path, C.DIVIDER_X + (1 - e) * 60, FLEET_BASE, alpha,
                       lift=paste_object_lift + 18, scale=0.97 + 0.03 * e)

        # spec rail: count / role / origin, the HIKKA pill language
        pe = C.ramp(local, 0.45, 0.7, C.ease_out_expo)
        self._spec_rail(f, it, pe)

        # roster of every type in this chapter
        self._roster(f, sec, idx, C.ramp(local, 0.25, 0.7, C.ease_out_expo))

        # chapter progress under the roster
        d = ImageDraw.Draw(f, "RGBA")
        prog = C.clamp(local / max(0.1, self._seg_dur or 12.0))
        gp = C.ramp(local, 0.5, 0.6)
        y = 934
        d.line([(C.W / 2 - 240, y), (C.W / 2 + 240, y)], fill=(150, 158, 168, 70), width=2)
        d.line([(C.W / 2 - 240, y), (C.W / 2 - 240 + 480 * prog, y)],
               fill=JP_RED + (int(200 * gp),), width=2)

    def _hero(self, f, path, cx, baseline, alpha, lift=0.0, scale=1.0):
        if alpha <= 0.01:
            return
        bw, bh = int(FLEET_BOX[0] * scale), int(FLEET_BOX[1] * scale)
        spr = fit(path, bw, bh)
        x = int(cx - spr.width / 2)
        y = int(baseline - spr.height - lift)

        # a very faint floor pool: the product shots carry their own soft
        # shadow, so this only has to stop the airframe looking pasted on.
        rgb, m = P.shadow(path, spr.height, spread=56, opacity=0.18)
        sw = int(spr.width * 1.14)
        sh = max(10, int(m.height * 0.12))
        rgb2 = rgb.resize((max(8, sw), sh), Image.BILINEAR)
        m2 = m.resize((max(8, sw), sh), Image.BILINEAR)
        m2 = m2.point(lambda v: int(v * alpha * 0.55))
        f.paste(rgb2, (int(cx - m2.width / 2), int(baseline - m2.height * 0.30)), m2)

        paste_rgba(f, spr, (x, y), alpha)

        # tiny ID ticks flanking the airframe: the "museum label" touch
        d = ImageDraw.Draw(f, "RGBA")
        a = int(120 * alpha)
        d.line([(C.SAFE, baseline), (C.SAFE + 30, baseline)], fill=(120, 128, 138, a), width=2)
        d.line([(C.W - C.SAFE - 30, baseline), (C.W - C.SAFE, baseline)],
               fill=(120, 128, 138, a), width=2)

    def _spec_rail(self, f, it, alpha):
        if alpha <= 0.01:
            return
        pills = [(it["kpi"], C.CHARCOAL, C.PAPER),
                 (it["role"], (232, 235, 239), C.INK),
                 (it["tag"], (232, 235, 239), C.INK_DIM)]
        sizes = 17
        pads = (22, 16)
        gap = 12
        widths = [tw(t, "bold", sizes, 2.6) + pads[0] * 2 for t, _, _ in pills]
        total = sum(widths) + gap * (len(pills) - 1)
        x = C.W / 2 - total / 2
        y = 800 - (1 - alpha) * 16
        for (txt, bg, fg), w in zip(pills, widths):
            P.draw_pill(f, x, y, txt, size=sizes, fg=fg, bg=bg, tracking=2.6,
                        pad_x=pads[0], pad_y=pads[1], alpha=alpha)
            x += w + gap

    def _roster(self, f, sec, idx, alpha):
        if alpha <= 0.01:
            return
        items = sec["items"]
        labels = [f"{i + 1:02d}   {it['short']}" for i, it in enumerate(items)]
        sizes, pad_x, pad_y, gap = 13, 16, 10, 10
        widths = [tw(l, "bold", sizes, 2.2) + pad_x * 2 for l in labels]
        total = sum(widths) + gap * (len(labels) - 1)
        x = C.W / 2 - total / 2
        for i, (lab, w) in enumerate(zip(labels, widths)):
            active = i == idx
            fg = C.PAPER if active else C.INK_FAINT
            bg = C.CHARCOAL if active else (235, 238, 242)
            P.draw_pill(f, x, 866, lab, size=sizes, fg=fg, bg=bg, tracking=2.2,
                        pad_x=pad_x, pad_y=pad_y, alpha=alpha * (1.0 if active else 0.75))
            x += w + gap

    # ------------------------------------------------------------ intro
    def draw_intro(self, f, local, dur):
        self.side_wash(f, 0.09)
        e1 = C.ramp(local, 0.05, 0.7, C.ease_out_expo)
        P.draw_text(f, (C.W / 2, 150 - (1 - e1) * 30), META_JP["hero_a"], "bold", 92,
                    C.INK, tracking=6, anchor="mt", alpha=e1)
        e1b = C.ramp(local, 0.22, 0.7, C.ease_out_expo)
        P.draw_text(f, (C.W / 2, 250 - (1 - e1b) * 26), META_JP["hero_b"], "bold", 92,
                    C.INK_DIM, tracking=6, anchor="mt", alpha=e1b)

        # three airframes drifting in, wide to tight, as a fleet teaser
        group = (("fleet/e767", 430, 0.42, 862, 560, 200),
                 ("fleet/f35", 960, 0.62, 902, 700, 260),
                 ("fleet/ch47j", 1500, 0.82, 856, 520, 210))
        for key, cx, delay, base, bw, bh in group:
            path = self.asset(key)
            if not path:
                continue
            e = C.ramp(local, delay, 0.9, C.ease_out_expo)
            if e <= 0.01:
                continue
            spr = fit(path, int(bw * (0.94 + 0.06 * e)), bh)
            bob = 6.0 * np.sin(local * 1.6 + delay * 9)
            y = int(base - spr.height - bob)
            x = int(cx + (1 - e) * 130 - spr.width / 2)
            paste_rgba(f, spr, (x, y), e)
            d = ImageDraw.Draw(f, "RGBA")
            lw = int(70 * e)
            d.line([(cx - lw, base + 26), (cx + lw, base + 26)],
                   fill=JP_RED + (int(140 * e),), width=3)

        e2 = C.ramp(local, 0.5, 0.8, C.ease_out_expo)
        P.draw_text(f, (C.W / 2, 386 - (1 - e2) * 16), "JAPAN  ·  AIR  ·  SEA  ·  GROUND",
                    "bold", 30, C.INK, tracking=10, anchor="mt", alpha=e2)
        e3 = C.ramp(local, 0.65, 0.8, C.ease_in_out)
        d = ImageDraw.Draw(f, "RGBA")
        d.line([(C.W / 2 - 260 * e3, 444), (C.W / 2 + 260 * e3, 444)],
               fill=(140, 148, 158, 120), width=2)
        e4 = C.ramp(local, 0.85, 0.7)
        for i, ln in enumerate(self.intro_lines):
            P.draw_text(f, (C.W / 2, 466 + i * 32), ln, "reg", 22, C.INK_DIM, tracking=0.4,
                        anchor="mt", alpha=e4)
        e5 = C.ramp(local, 1.5, 0.6)
        P.draw_text(f, (C.W / 2, 596), META_JP["hero_stat"], "bold", 20, C.INK_FAINT,
                    tracking=8, anchor="mt", alpha=e5)

        f = _camera(f, 1.0 + 0.05 * C.ease_in_out(C.clamp(local / max(0.1, dur))))
        self.top_bar(f, local, C.ramp(local, 0.05, 0.6))
        self.bottom_bar(f, C.ramp(local, 0.7, 0.7),
                        left_note="19 TYPES   ·   ONE FLEET   ·   OPEN SOURCES", rule=False)
        return f

    def draw_endcard(self, f, local):
        self.side_wash(f, 0.05)
        e = C.ramp(local, 0.1, 0.9)
        P.draw_text(f, (C.W / 2, 380), "AIR FLEET 2026", "bold", 118, C.INK, tracking=10,
                    anchor="mt", alpha=e)
        P.draw_text(f, (C.W / 2, 540), "JAPAN   ·   SELF-DEFENSE FORCES", "bold", 40,
                    C.INK_DIM, tracking=9, anchor="mt", alpha=C.ramp(local, 0.6, 0.8))
        P.draw_text(f, (C.W / 2, 636), "19 TYPES   ·   8 CHAPTERS   ·   ONE ISLAND NATION",
                    "reg", 24, C.INK_FAINT, tracking=7, anchor="mt",
                    alpha=C.ramp(local, 1.0, 0.8))
        d = ImageDraw.Draw(f, "RGBA")
        w = 300 * C.ramp(local, 1.2, 0.9, C.ease_in_out)
        d.line([(C.W / 2 - w, 728), (C.W / 2 + w, 728)], fill=(140, 148, 158, 110), width=2)


# ---------------------------------------------------------------- caches
@lru_cache(maxsize=4)
def _fleet_glow():
    """A soft pool of light behind the hero, so the wall never looks flat."""
    w, h = C.W, C.H
    im = Image.new("L", (w // 4, h // 4), 0)
    d = ImageDraw.Draw(im)
    d.ellipse([w // 4 * 0.12, h // 4 * 0.30, w // 4 * 0.88, h // 4 * 0.86], fill=150)
    im = im.resize((w, h), Image.BICUBIC).filter(ImageFilter.GaussianBlur(70))
    return im


@lru_cache(maxsize=4)
def _jp_wash(alpha):
    w, h = C.W, C.H
    xs = np.arange(w, dtype=np.float32) / w
    ys = np.arange(h, dtype=np.float32) / h
    red = np.array(JP_RED, dtype=np.float32)
    slate = np.array((222, 227, 233), dtype=np.float32)
    u = (np.clip((xs - 0.55) / 0.45, 0, 1) ** 1.8)[None, :, None]      # (1, w, 1)
    layer = slate[None, None, :] * (1 - u) + red[None, None, :] * u     # (1, w, 3)
    layer = np.repeat(layer, h, axis=0)                                 # (h, w, 3)
    mask = np.clip(1 - np.abs(ys - 0.46) * 1.05, 0, 1) ** 1.5
    mask = np.broadcast_to(mask[:, None], (h, w))
    rgba = np.dstack([layer, mask * alpha * 255.0]).astype(np.uint8)
    return Image.fromarray(rgba, "RGBA")


def _camera(f, zoom, cy=None):
    from .scenes import camera
    return camera(f, zoom, cy=cy)
