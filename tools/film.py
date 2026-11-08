"""Frame-accurate renderer for the U.S. Naval Aviation fleet catalogue film.

Everything is drawn per frame with Pillow into a pipe to ffmpeg; voiceover
timing drives every scene length so picture and narration stay locked.
"""
from __future__ import annotations

import json
import math
import re
from functools import lru_cache
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parent))
import design as D
from design import (H, INK, INK_25, INK_45, INK_70, M, PAPER, PAPER_HI, RED, RED_DEEP, RULE,
                    RULE_SOFT, W, box, chrome, font, grid_plate, hairline,
                    glow, intro_plate, status_chip, sweep_text, text,
                    text_sprite, tick_corners, tw, wrap)
from cutout import cutout, ground_shadow

ROOT = Path(__file__).resolve().parent.parent
FLEET = ROOT / "assets" / "fleet"
VO = ROOT / "build" / "vo"
FPS = 24
TARGET = 15 * 60 + 44          # 15:44
XFADE = 0.42                   # seconds of dissolve between scenes


# ------------------------------------------------------------------ helpers
def clamp(v, a=0.0, b=1.0):
    return a if v < a else b if v > b else v


def ease_out(p):
    return 1 - (1 - p) ** 3


def ease_in_out(p):
    return p * p * (3 - 2 * p)


def ramp(t, start, dur, fn=ease_out):
    return fn(clamp((t - start) / dur if dur else 1.0))


def timecode(sec: float) -> str:
    sec = max(0, int(sec))
    return f"{sec // 60:02d}:{sec % 60:02d}"


# ------------------------------------------------------------------ sprites
@dataclass
class Sprite:
    image: Image.Image
    shadow: Image.Image | None = None
    ground_y: float = 0.0


_SPRITE_CACHE: dict[tuple[str, int], Sprite] = {}


def aircraft_sprite(aid: str, target_w: int) -> Sprite | None:
    key = (aid, target_w)
    if key in _SPRITE_CACHE:
        return _SPRITE_CACHE[key]
    path = FLEET / f"{aid}.png"
    if not path.exists():
        return None
    full = None
    for (k_id, k_w), spr in _SPRITE_CACHE.items():
        if k_id == aid:
            full = spr
            break
    if full is None:
        img = cutout(str(path))
        sh = ground_shadow(img, blur=30, opacity=30)
        full = Sprite(img, sh)
    ratio = target_w / full.image.width
    img = full.image.resize((max(8, target_w), max(8, int(full.image.height * ratio))),
                            Image.LANCZOS)
    sh = full.shadow.resize((max(8, target_w), max(8, int(full.shadow.height * ratio))),
                            Image.LANCZOS) if full.shadow else None
    spr = Sprite(img, sh, ground_y=full.ground_y)
    _SPRITE_CACHE[key] = spr
    return spr


@lru_cache(maxsize=128)
def _silhouette(aid: str) -> tuple[int, int] | None:
    """Trimmed silhouette size of a source render, in source pixels."""
    path = FLEET / f"{aid}.png"
    if not path.exists():
        return None
    a = np.asarray(cutout(str(path)).getchannel("A"))
    ys, xs = np.nonzero(a > 26)
    return (int(xs.max() - xs.min() + 1), int(ys.max() - ys.min() + 1)) if len(xs) else None


def aircraft_fit(aid: str, max_w: float, max_h: float) -> Sprite | None:
    """Scale an airframe to sit inside a box, measured on its own silhouette."""
    dims = _silhouette(aid)
    if dims is None:
        return None
    sw, sh = dims
    return aircraft_sprite(aid, max(24, int(round(sw * min(max_w / sw, max_h / sh)))))


_ROT_CACHE: dict[str, Image.Image] = {}


def rotated_label(s: str, fkey="mono", size=13, color=INK_45, track=4.0) -> Image.Image:
    key = f"{s}|{fkey}|{size}|{track}"
    if key not in _ROT_CACHE:
        spr = text_sprite(s, fkey, size, tuple(color), track)
        _ROT_CACHE[key] = spr.rotate(90, expand=True)
    return _ROT_CACHE[key]



def _count(inv: str) -> str:
    """Leading quantity of an inventory string, for the register readout."""
    m = re.search(r"[\d,]+", inv)
    return inv[:m.end()] if m else inv.split(" ")[0].capitalize()


def _speed(ac: dict) -> tuple[str, str, str]:
    """Register readout: the speed figure where there is one, else the key metric."""
    pick = next(((l, v) for l, v in ac["specs"] if "SPEED" in l), None)
    if pick is None and len(ac["specs"]) >= 3:
        pick = ac["specs"][2]
    if pick is None:
        return ("KEY FIGURE", "—", "")
    label, value = pick
    head, _, tail = value.partition(" ")
    return (label, head, tail.strip())


# ------------------------------------------------------------------ scenes
@dataclass
class Scene:
    kind: str
    dur: float = 6.0
    data: dict = field(default_factory=dict)
    audio: list[tuple[Path, float]] = field(default_factory=list)   # (file, offset in scene)
    abs_start: float = 0.0
    section: str = ""
    counter: str = ""
    progress: float = 0.0

    def draw(self, img: Image.Image, t: float, abs_t: float) -> None:
        getattr(self, f"draw_{self.kind}")(img, t, abs_t)

    # ---------------------------------------------------------- intro
    # Four three-second beats on pure white that accumulate into one stack,
    # then a blow-out to white before the cut — the montage grammar taken from
    # the frame-by-frame analysis of the source film.
    def draw_intro(self, img, t, abs_t):
        img.paste(intro_plate(), (0, 0))
        CX = W / 2

        def scaled(s_, fk, size, col, track, scale, a, cy):
            spr = text_sprite(s_, fk, size, col, track)
            if abs(scale - 1.0) > 0.002:
                nw, nh = int(spr.width * scale), int(spr.height * scale)
                spr = spr.resize((nw, nh), Image.LANCZOS)
            D.put(img, spr, (CX - spr.width / 2, cy - spr.height / 2), a)

        # measured stack: EVERY / AIRCRAFT / service line / catalogue line
        y_every, y_craft, y_serv, y_cat = 316, 432, 562, 672

        # ---- beat 1 [0–3] : EVERY alone, a light band running across it
        if t < 3.0:
            a = clamp(t / 0.26)
            scaled("EVERY", "disp-semi", 76, INK, 16.0, 1.0, a, y_every)
            spr = text_sprite("EVERY", "disp-semi", 76, INK, 16.0)
            if a > 0.55:
                sweep_text(img, (CX, y_every), spr, t, 0.34, 2.2, 0.92, anchor="cm")
            text(img, "A U.S. NAVAL AVIATION CATALOGUE", (CX, y_every + 62), "mono-med", 13,
                 INK_45, 7.0, clamp((t - 0.75) / 0.7) * 0.8, anchor="cm")

        # ---- beat 2 [3–6] : the subject lands in red with a small push-in
        elif t < 6.0:
            a = clamp((t - 3.0) / 0.30)
            scaled("EVERY", "disp-semi", 76, INK, 16.0, 1.0, a * 0.9, y_every)
            sc_ = 1.0 + 0.055 * (1 - ease_out(clamp((t - 3.0) / 0.45)))
            scaled("AIRCRAFT", "black", 186, RED, 2.0, sc_, a, y_craft)

        # ---- beat 3 [6–10] : thin service line + hairline wipe
        elif t < 10.0:
            p = clamp((t - 6.0) / 0.8)
            scaled("EVERY", "disp-semi", 76, INK, 16.0, 1.0, 0.9, y_every)
            scaled("AIRCRAFT", "black", 186, RED, 2.0, 1.0, 1.0, y_craft)
            scaled("IN U.S. NAVY & MARINE CORPS SERVICE", "disp-light", 54, INK_70, 7.0,
                   1.0, p, y_serv)
            hairline(img, (CX - 210, y_serv + 48), int(420 * ease_out(clamp((t - 6.4) / 0.7))),
                     RED, 3)

        # ---- beat 4 [10–12] : small line, then the field blows out to white
        else:
            scaled("EVERY", "disp-semi", 76, INK, 16.0, 1.0, 0.9, y_every)
            scaled("AIRCRAFT", "black", 186, RED, 2.0, 1.0, 1.0, y_craft)
            scaled("IN U.S. NAVY & MARINE CORPS SERVICE", "disp-light", 54, INK_70, 7.0,
                   1.0, 1.0, y_serv)
            hairline(img, (CX - 210, y_serv + 48), 420, RED, 3)
            p = clamp((t - 10.05) / 0.5)
            text(img, "FLEET CATALOGUE · 2026", (CX, y_cat), "mono-med", 17, INK_45, 9.0, p,
                 anchor="cm")
            text(img, "STATEWIDE USA", (CX, H - 150), "mono", 11, INK_25, 6.0, p, anchor="cm")
            if t > 11.1:
                wa = clamp((t - 11.1) / 0.6) ** 1.35
                white = Image.new("RGBA", (W, H), (255, 255, 255, 255))
                white.putalpha(white.getchannel("A").point(lambda v: int(v * wa)))
                img.alpha_composite(white)

    # ---------------------------------------------------------- division
    def draw_division(self, img, t, abs_t):
        cat = self.data["cat"]
        n = len(cat["aircraft"])
        d = ImageDraw.Draw(img)

        # faint outlined section index, top right shoulder
        p = ramp(t, 0.0, 1.4, ease_out)
        num_spr = text_sprite(f"{cat['index']:02d}", "black", 210, PAPER, 1,
                              False, 2, (228, 226, 219))
        num = num_spr.copy()
        num.putalpha(num.getchannel("A").point(lambda v: int(v * 0.9 * p)))
        img.alpha_composite(num, (W - num.width - 118 - int((1 - p) * 30), 104))

        # red section block
        p = ramp(t, 0.15, 0.5, ease_out)
        bw = int(84 * p)
        if bw > 2:
            d.rectangle([M, 236, M + bw - 1, 236 + 84], fill=RED)
            if p > 0.6:
                text(img, cat["numeral"], (M + bw / 2, 236 + 40), "disp-bold", 46, PAPER_HI,
                     1.0, (p - 0.6) / 0.4, anchor="cm")
        p = ramp(t, 0.4, 0.8)
        text(img, "SECTION", (M + 110, 244), "mono", 14, INK_45, 5.0, p)
        text(img, f"{cat['index']:02d} OF 13", (M + 110, 270), "mono-med", 14, RED, 4.4, p)

        p = ramp(t, 0.5, 0.9)
        text(img, cat["kicker"], (M, 372 + (1 - p) * 14), "mono-med", 15, INK_70, 6.0, p)

        tw_avail = 1120
        size = min(112, D.fit_size(d, cat["title"], "black", tw_avail, 112, 56, -1.2))
        lines = wrap(d, cat["title"], "black", size, tw_avail, -1.2)
        if len(lines) > 1:
            size = int(size * 0.74)
            lines = wrap(d, cat["title"], "black", size, tw_avail, -1.2)
        y = 412
        for i, ln in enumerate(lines):
            p = ramp(t, 0.6 + i * 0.1, 0.85)
            text(img, ln, (M - 3, y + (1 - p) * 28), "black", size, INK, -1.2, p)
            y += int(size * 0.96)

        hairline(img, (M, y + 26), int(1120 * ramp(t, 0.9, 0.9)), INK_25)
        p = ramp(t, 1.0, 0.9)
        plines = wrap(d, cat["lead"], "sans-light", 30, 700)
        yy = y + 56
        for ln in plines:
            text(img, ln, (M, yy + (1 - p) * 14), "sans-light", 30, INK_70, 0.2, p)
            yy += 40

        # lineup of the section's airframes on a shared baseline
        base_y = H - 236
        n_show = min(6, n)
        prow = ramp(t, 1.25, 1.0)
        if prow > 0.02:
            hairline(img, (M, base_y + 4), int(1560 * prow), RULE, 1, 0.9)
        slot_w = (1560 - 40) / max(1, n_show)
        for i, ac in enumerate(cat["aircraft"][:n_show]):
            p = ramp(t, 1.3 + i * 0.1, 0.85)
            if p <= 0.02:
                continue
            max_w = min(slot_w - 26, 360)
            spr = aircraft_sprite(ac["id"], int(max_w))
            if not spr:
                continue
            s = spr.image
            if s.width > max_w:
                s = s.resize((int(max_w), int(s.height * max_w / s.width)), Image.LANCZOS)
            im = s.copy()
            im.putalpha(im.getchannel("A").point(lambda v: int(v * 0.92 * p)))
            cx = M + i * slot_w + slot_w / 2
            img.alpha_composite(im, (int(cx - s.width / 2), int(base_y - s.height + (1 - p) * 14)))
            text(img, ac["short"], (cx, base_y + 20), "mono", 12, INK_45, 2.6, p * 0.9,
                 anchor="ct")

        # right metadata column
        p = ramp(t, 1.4, 0.9)
        cx = W - M
        text(img, f"{n:02d}", (cx, 402), "disp-bold", 92, RED, 0, p, anchor="rt")
        text(img, "AIRFRAME TYPES", (cx, 512), "mono", 13, INK_45, 4.2, p, anchor="rt")
        hairline(img, (cx - 300, 548), 300, RULE, 1, p)
        iy = 570
        for ac in cat["aircraft"]:
            pp = ramp(t, 1.5 + cat["aircraft"].index(ac) * 0.07, 0.7)
            text(img, ac["name"], (cx, iy), "mono-med", 13, INK_70, 2.2, pp, anchor="rt")
            iy += 32
        D.chrome(img, self.progress, timecode(abs_t), f"SECTION {cat['numeral']} — {cat['title']}",
                 self.counter)

    # ---------------------------------------------------------- aircraft
    # Motion grammar from the frame analysis:
    #   image fade-in 0.3 s · title slides in from the left 0.5 s ·
    #   category slides in from the right 0.5 s ·
    #   spec cards rise from below in sequence, 0.8 s total·
    def draw_aircraft(self, img, t, abs_t):
        """Catalogue plate laid out like the reference montage frame.

        Left column: black title slab with a red spine and a red category
        ribbon under it — the reference carries no spec table, so nothing else.
        Top right: a three-column register (operator / inventory / speed).
        """
        cat, ac = self.data["cat"], self.data["aircraft"]
        LW = 610                      # title column width
        CX_IMG = 1100                 # airframe centre

        def slide(delay, dur=0.5, dist=60):
            p = ease_out(clamp((t - delay) / dur))
            return dist * (1 - p), p

        # ---- title slab: slides in from the left, 0.5 s
        dx, p = slide(0.04, 0.5, 66)
        d = ImageDraw.Draw(img)
        size = D.fit_size(d, ac["name"], "black", LW, 54, 30, -0.6)
        nlines = wrap(d, ac["name"], "black", size, LW, -0.6)
        if len(nlines) > 2:
            size = int(size * 0.82)
            nlines = wrap(d, ac["name"], "black", size, LW, -0.6)
        y = 58
        for ln in nlines:
            _, h = D.title_slab(img, (104 + dx, y), ln, "black", size, -0.6, p)
            y += h + 10

        # ---- category ribbon: sits under the slab, +0.16 s
        dx2, p2 = slide(0.20, 0.5, 44)
        D.category_ribbon(img, (104 + dx2, y + 6),
                          f"{cat['title']} · {ac['year']}", "cond-bold", 21, 2.6, p2)

        # ---- top-right register: three readouts on a fixed ladder
        slabel, sval, sunit = _speed(ac)
        reg = [("FLOWN BY", D.OP_NAMES.get(ac["operator"], ac["operator"]).upper(), ""),
               ("IN SERVICE", _count(ac["inventory"]), ""),
               (slabel, sval, sunit)]
        for i, (lab, val, unit) in enumerate(reg):
            D.register_item(img, 1284 + i * 274, 30, lab, val, unit,
                            ramp(t, 0.30 + i * 0.09, 0.45))

        # ---- the airframe: fades up on the studio floor, then a 1.8 % push-in
        p = ramp(t, 0.0, 0.34)
        kb = 1.0 + 0.022 * clamp(t / max(self.dur, 1))
        spr = aircraft_fit(ac["id"], 1400 * kb, 640 * kb)
        if spr and spr.image.width > 4:
            s_ = spr.image
            x = CX_IMG - s_.width / 2
            base_y = 938
            if spr.shadow:
                sh = spr.shadow.copy()
                sh.putalpha(sh.getchannel("A").point(lambda v: int(v * 0.9 * p)))
                img.alpha_composite(sh, (int(x + s_.width * 0.02), int(base_y - sh.height * 0.55)))
            body = s_.copy()
            body.putalpha(body.getchannel("A").point(lambda v: int(v * p)))
            img.alpha_composite(body, (int(x), int(base_y - s_.height)))
        else:
            text(img, "RENDER PENDING", (CX_IMG, 620), "mono-med", 18, D.INK_25, 5, 1.0,
                 anchor="cm")

    # ---------------------------------------------------------- outro
    def draw_outro(self, img, t, abs_t):
        d = ImageDraw.Draw(img)
        hero = aircraft_sprite("f35", 820)
        if hero:
            a = 0.13 * ramp(t, 0.2, 2.0)
            h = hero.image.copy()
            h.putalpha(h.getchannel("A").point(lambda v: int(v * a)))
            img.alpha_composite(h, (960, 250))

        p = ramp(t, 0.2, 0.9)
        text(img, "END OF CATALOGUE", (M, 250 + (1 - p) * 12), "mono-med", 16, RED, 6.0, p)

        y = 300
        for i, ln in enumerate(["THAT IS THE", "WHOLE FLEET"]):
            pp = ramp(t, 0.35 + i * 0.12, 0.9)
            text(img, ln, (M - 3, y + (1 - pp) * 26), "black", 96, INK, -1.0, pp)
            y += 100

        p = ramp(t, 0.8, 0.9)
        hairline(img, (M, y + 30), int(640 * p), RED, 3)

        rows = [("AIRCRAFT TYPES", str(self.data["total"])),
                ("CATEGORIES", "13"),
                ("RETIREMENTS TRACKED TO", "2032")]
        ry = y + 70
        for i, (lab, val) in enumerate(rows):
            pp = ramp(t, 1.0 + i * 0.14, 0.7)
            text(img, lab, (M, ry + 12), "mono", 14, INK_45, 3.4, pp)
            text(img, val, (M + 420, ry), "disp-bold", 44, INK, 0.6, pp, anchor="rt")
            hairline(img, (M, ry + 62), 420, RULE_SOFT, 1, pp)
            ry += 78

        p = ramp(t, 1.7, 1.0)
        text(img, "SOURCES: U.S. NAVY · U.S. MARINE CORPS · FY2026 BUDGET DOCUMENTS",
             (M, H - 214), "mono", 12, INK_45, 2.6, p)
        text(img, "CATALOGUE PRODUCED BY STATEWIDE USA", (M, H - 188), "mono", 12, INK_25, 2.6, p)

        # sign-off block, bottom right, clear of the hero
        p = ramp(t, 1.9, 1.2)
        if p > 0.02:
            bw = int(560 * p)
            hairline(img, (W - M - bw, 812), bw, RED, 2)
        text(img, "WANT TO SUPPORT THE CHANNEL?", (W - M, 832), "disp-med", 30, INK, 2.0, p,
             anchor="rt")
        text(img, "CLICK JOIN TO KEEP THESE CATALOGUES COMING · THANK YOU",
             (W - M, 878), "mono", 11, INK_45, 2.0, p, anchor="rt")
        D.chrome(img, 1.0, timecode(abs_t), "END OF CATALOGUE", "")


# ------------------------------------------------------------------ build
def vo_path(name: str) -> Path:
    return VO / f"{name}.mp3"


def build_scenes(fleet: dict, durations: dict[str, float]) -> list[Scene]:
    scenes: list[Scene] = []
    total = fleet["meta"]["total_aircraft"]

    intro = Scene("intro", data={}, section="")
    intro.dur = 12.0
    scenes.append(intro)

    fig = 0
    for ci, cat in enumerate(fleet["categories"]):
        div = Scene("division", data={"cat": cat})
        key = f"vo_lead_{cat['index']}"
        div.audio = [(vo_path(key), 0.5)]
        div.dur = max(5.6, durations.get(key, 0) + 2.5) if durations.get(key) else 7.4
        scenes.append(div)

        for ac in cat["aircraft"]:
            fig += 1
            sc = Scene("aircraft", data={"cat": cat, "aircraft": ac, "fig": fig})
            key = f"vo_{ac['id']}"
            sc.audio = [(vo_path(key), 0.85)]
            if durations.get(key):
                sc.dur = max(6.6, durations[key] + 1.55)
            else:                       # plate-only beat while narration is pending
                sc.dur = 8.4
            sc.counter = f"{fig:02d} / {total}"
            scenes.append(sc)

    outro = Scene("outro", data={"total": total})
    outro.audio = [(vo_path("vo_outro"), 0.9)]
    outro.dur = max(8.0, durations.get("vo_outro", 0) + 5.0)
    scenes.append(outro)

    # absolute times, sections and progress
    t = 0.0
    for s in scenes:
        s.abs_start = t
        if s.kind == "aircraft":
            s.section = f"SECTION {s.data['cat']['numeral']} — {s.data['cat']['title']}"
        elif s.kind == "division":
            s.section = f"SECTION {s.data['cat']['numeral']} — {s.data['cat']['title']}"
        elif s.kind == "intro":
            s.section = "INTRODUCTION"
        else:
            s.section = "END"
        t += s.dur
    for s in scenes:
        s.progress = (s.abs_start + s.dur / 2) / max(t, 1e-6)
    scenes[0].progress = 0.0
    scenes[-1].progress = 1.0
    return scenes


def fit_to_target(scenes: list[Scene], target: float) -> None:
    """Stretch or trim the breath between beats so the film lands on runtime."""
    total = sum(s.dur for s in scenes)
    diff = target - total
    if abs(diff) < 0.2:
        return
    if diff > 0:
        stretchable = [s for s in scenes if s.kind in ("aircraft", "division", "outro")]
        weight = sum(s.dur for s in stretchable)
        for s in stretchable:
            s.dur += diff * (s.dur / weight)
    else:
        for s in scenes:
            if s.kind != "outro":
                s.dur += diff * (s.dur / total) * 0.98
    t = 0.0
    for s in scenes:
        s.abs_start = t
        t += s.dur
    for s in scenes:
        s.progress = (s.abs_start + s.dur / 2) / max(t, 1e-6)
    scenes[0].progress = 0.0
    scenes[-1].progress = 1.0


# ------------------------------------------------------------------ render
def render(scenes: list[Scene], out: Path, preview: bool = False) -> None:
    import imageio_ffmpeg
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    total_dur = sum(s.dur for s in scenes)
    n_frames = int(round(total_dur * FPS))
    base = D.reference_plate()
    cmd = [ff, "-y", "-hide_banner", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-an",
           "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
           "-movflags", "+faststart", str(out)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    prev_last: Image.Image | None = None
    xf = int(XFADE * FPS)
    f_i = 0
    for si, sc in enumerate(scenes):
        n = int(round(sc.dur * FPS))
        for k in range(n):
            t = k / FPS
            frame = base.copy()
            sc.draw(frame, t, sc.abs_start + t)
            if sc.kind != "intro":
                D.plate_grain(frame, 1.7, 31)
            if prev_last is not None and k < xf:
                a = ease_in_out((k + 1) / xf)
                frame = Image.blend(prev_last, frame, a)
            if si == 0 and k < 10:
                frame = Image.blend(Image.new("RGBA", (W, H), (245, 239, 228, 255)), frame,
                                    ease_in_out((k + 1) / 10))
            if si == len(scenes) - 1 and not preview and k > n - 26:
                frame = Image.blend(frame, Image.new("RGBA", (W, H), (245, 239, 228, 255)),
                                    ease_in_out((k - (n - 26)) / 25))
            proc.stdin.write(frame.convert("RGB").tobytes())
            prev_last = frame
            f_i += 1
            if f_i % 240 == 0:
                print(f"  frame {f_i}/{n_frames}  ({f_i / n_frames * 100:5.1f}%)", flush=True)
    proc.stdin.close()
    proc.wait()
    if proc.returncode != 0:
        raise SystemExit("ffmpeg failed")
    print(f"  video written: {out} ({f_i} frames, {total_dur:.1f}s)")


def mux(video: Path, audio: Path, out: Path) -> None:
    import imageio_ffmpeg
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    subprocess.run([ff, "-y", "-hide_banner", "-loglevel", "error",
                    "-i", str(video), "-i", str(audio),
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                    "-shortest", "-movflags", "+faststart", str(out)], check=True)


def load_fleet() -> dict:
    return json.loads((ROOT / "data" / "fleet.json").read_text())


fleet_meta: dict = {"categories": []}


if __name__ == "__main__":
    import argparse
    from audio import probe_durations, mix_audio

    ap = argparse.ArgumentParser()
    ap.add_argument("--stills", default="", help="comma list of scene indices to dump")
    ap.add_argument("--out", default="build/film.mp4")
    ap.add_argument("--preview", type=int, default=0, help="render only the first N scenes")
    ap.add_argument("--no-fit", action="store_true")
    args = ap.parse_args()

    fleet = load_fleet()
    fleet_meta["categories"] = fleet["categories"]
    durs = probe_durations()
    scenes = build_scenes(fleet, durs)
    if not args.no_fit:
        fit_to_target(scenes, TARGET)
    if args.preview:
        scenes = scenes[: args.preview]

    if args.stills:
        base = D.reference_plate()
        for idx in [int(x) for x in args.stills.split(",")]:
            sc = scenes[idx]
            for frac in (0.35, 0.85):
                frame = base.copy()
                sc.draw(frame, sc.dur * frac, sc.abs_start + sc.dur * frac)
                frame.convert("RGB").save(ROOT / "build" / f"still_{idx}_{int(frac*100)}.png")
                print("still", idx, frac, sc.kind, f"{sc.dur:.1f}s")
        sys.exit(0)

    total = sum(s.dur for s in scenes)
    print(f"total runtime {total:.1f}s → {timecode(total)}")
    render(scenes, ROOT / args.out)
    wav = ROOT / "build" / "mix.wav"
    mix_audio(scenes, wav, total=total)
    print("audio mix written", wav)
    mux(ROOT / args.out, wav, ROOT / args.out.replace(".mp4", "_av.mp4"))
    print("muxed")
