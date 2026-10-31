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

import math
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

# cold open: every airframe in the film, flipping past on its vertical axis
HOOK_BOX = (1472, 528)
HOOK_TURN = 0.43          # share of a slot spent turning the card over
HOOK_DIST = 4.2           # virtual camera distance, in half-cards


def _fit_h(path: str, box_w: int, box_h: int) -> Image.Image:
    return fit(path, box_w, box_h)


class FleetRenderer(Renderer):
    def __init__(self, sections, intro_narration, assets_dir, timeline, total_duration):
        super().__init__(sections, intro_narration, assets_dir, timeline, total_duration)
        self.intro_lines = wrap(META_JP["deck"], "reg", 23, 760, 3)
        self._hook_cfg = None

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

        # ambient occlusion on the wall: white airframes (Global Hawk, T-4)
        # would otherwise dissolve into a white showroom.
        halo = Image.new("L", (spr.width + 120, spr.height + 120), 0)
        hm = spr.split()[3].point(lambda v: 255 if v > 120 else 0)
        halo.paste(hm, (60, 60))
        halo = halo.filter(ImageFilter.GaussianBlur(34))
        strength = 0.16 + 0.34 * _paleness(path)
        halo = halo.point(lambda v: int(v * strength * alpha))
        f.paste((150, 154, 160), (x - 60, y - 60), halo)

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

    # ------------------------------------------------------------ cold open
    def hook_items(self):
        """Every type in the film, in running order."""
        return [it for sec in self.sections for it in (sec.get("items") or [])]

    def draw_hook(self, f, local, dur):
        """Cold open: the whole inventory flipping past, one airframe at a time.

        No chrome, no type, no narration.  Each card turns about its vertical
        axis; at edge-on the next type takes the stage, so the film opens on
        pure motion and cuts straight into the intro.
        """
        items = self.hook_items()
        if not items:
            return f
        cfg = self._hook_cfg or {}
        n = len(items)
        hold = float(cfg.get("hold", 0.55))
        slot = float(cfg.get("slot") or max(0.06, (dur - hold) / n))

        t = max(0.0, min(local, dur - 1e-3))
        i = min(n - 1, int(t / slot))
        u = t - i * slot

        half = min(0.15, slot * HOOK_TURN)
        theta, alpha = 0.0, 1.0

        if i > 0 and u < half:                       # this card swings in
            p = u / half
            theta = -math.pi / 2 * (1.0 - C.ease_out_expo(p))
            alpha = 0.55 + 0.45 * p
        elif i < n - 1 and u > slot - half:          # this card swings away
            p = (u - (slot - half)) / half
            theta = math.pi / 2 * C.ease_in_out(p)
            alpha = 1.0 - 0.42 * p

        # a short drop as the card lands, so the cut has weight
        v = C.clamp((u - half) / 0.09) if i > 0 else 1.0
        lift = 22.0 * (1.0 - C.ease_out_expo(v))

        path = self.asset(items[i]["asset"])
        if not path:
            return f
        spr = fit(path, HOOK_BOX[0], HOOK_BOX[1])
        self._hook_card(f, path, spr, theta, C.DIVIDER_X, FLEET_BASE, alpha, lift)
        return f

    def _hook_card(self, f, path, spr, theta, cx, baseline, alpha, lift):
        """One airframe mid-turn: trapezoid projection, wall glow, floor pool."""
        if alpha <= 0.01:
            return
        card, w = _flip(spr, theta)
        if card is None:
            return
        face = abs(math.cos(theta))
        x = int(round(cx - w / 2))
        y = int(baseline - card.height - lift)

        # ambient occlusion on the wall: white airframes would otherwise
        # dissolve into the showroom, so they get a stronger wash
        halo, pad = _hook_halo(path, HOOK_BOX[0], HOOK_BOX[1])
        strength = (0.14 + 0.30 * _paleness(path)) * alpha * (0.30 + 0.70 * face)
        m = halo.point(lambda v: int(v * strength))
        f.paste((150, 154, 160), (x - pad, y - pad), m)

        # contact shadow, squashed with the card
        rgb, sm = P.shadow(path, spr.height, spread=56, opacity=0.18)
        sw = max(8, int(w * 1.14))
        sh = max(10, int(sm.height * 0.12))
        m2 = sm.resize((sw, sh), Image.BILINEAR)
        m2 = m2.point(lambda v: int(v * alpha * (0.25 + 0.75 * face) * 0.55))
        f.paste(rgb.getpixel((0, 0)), (int(cx - sw / 2), int(baseline - sh * 0.30)), m2)

        paste_rgba(f, card, (x, y), alpha)

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
@lru_cache(maxsize=48)
def _hook_halo(path: str, box_w: int, box_h: int):
    """Soft wall wash behind a cold-open card, blurred once and kept."""
    spr = fit(path, box_w, box_h)
    pad = 90
    im = Image.new("L", (spr.width + pad * 2, spr.height + pad * 2), 0)
    im.paste(spr.split()[3].point(lambda v: 255 if v > 120 else 0), (pad, pad))
    k = 4
    small = im.resize((max(2, im.width // k), max(2, im.height // k)), Image.BILINEAR)
    small = small.filter(ImageFilter.GaussianBlur(9))
    return small.resize(im.size, Image.BICUBIC), pad


def _homography(dst, src):
    """8 coefficients for PIL's PERSPECTIVE: output (x, y) -> source (u, v)."""
    A, b = [], []
    for (x, y), (u, v) in zip(dst, src):
        A.append([x, y, 1.0, 0.0, 0.0, 0.0, -u * x, -u * y])
        b.append(u)
        A.append([0.0, 0.0, 0.0, x, y, 1.0, -v * x, -v * y])
        b.append(v)
    return np.linalg.solve(np.asarray(A, dtype=np.float64), np.asarray(b, dtype=np.float64))


def _flip(spr, theta, dist=HOOK_DIST):
    """Project a card turned `theta` radians about its vertical axis.

    A true perspective map, so the edge that swings towards camera grows and
    the far edge compresses — that trapezoid is what reads as a card, not a
    flat squash.
    """
    c, s = math.cos(theta), math.sin(theta)
    if abs(s) < 1.5e-3:
        return spr, spr.width
    W, H = spr.size
    hw, hh = W / 2.0, H / 2.0
    corner = ((-1.0, -1.0, 0.0, 0.0), (1.0, -1.0, W, 0.0),
              (1.0, 1.0, W, H), (-1.0, 1.0, 0.0, H))
    pts, src = [], []
    for xc, yc, u, v in corner:
        k = dist / (dist + xc * s)
        pts.append((hw + xc * c * k * hw, hh + yc * k * hh))
        src.append((u, v))

    x0 = min(p[0] for p in pts)
    y0 = min(p[1] for p in pts)
    w = int(round(max(p[0] for p in pts) - x0))
    h = int(round(max(p[1] for p in pts) - y0))
    if w < 2 or h < 2:
        return None, 0
    dst = [(p[0] - x0, p[1] - y0) for p in pts]
    coef = _homography(dst, src)
    return spr.transform((w, h), Image.PERSPECTIVE, tuple(coef), Image.BILINEAR), w


@lru_cache(maxsize=64)
def _paleness(path: str) -> float:
    """0 for a dark airframe, 1 for a white one.

    White aircraft need a stronger ambient shadow to separate from the white
    showroom wall; dark ones only need a whisper of it.
    """
    a = np.asarray(Image.open(path).convert("RGBA")).astype(np.float32) / 255.0
    m = a[..., 3] > 0.6
    if not m.any():
        return 0.0
    lum = 0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2]
    return float(np.clip((float(lum[m].mean()) - 0.55) / 0.35, 0, 1))


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
