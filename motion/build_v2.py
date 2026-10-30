"""v2 renderer: real motion design — scenes, kinetic type, icons, battles, cards.

    python build_v2.py                 # full render -> deliver/final_v2.mp4
    python build_v2.py --probe 12.5    # single frame PNG for QC
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mgfx.ease import clamp, lerp, out_back, out_cubic, pulse, ramp, in_out  # noqa: E402
from mgfx.masks import Sprites  # noqa: E402
from mgfx.stage import Stage, C, W, H  # noqa: E402
from mgfx.render import audio_envelope, ffmpeg_bin  # noqa: E402
import story2 as S  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
IVORY = C("F5EFE6")
GOLD = C("E9C27A")
GOLD2 = C("C79A4B")
MINT = C("8FD3C1")
RED = C("D98B7F")

SP = Sprites()


# --------------------------------------------------------------------------- base
class Beat:
    def __init__(self, t0, t1, mood="calm"):
        self.t0, self.t1, self.mood = t0, t1, mood
        self.items = []          # drawable words/glyphs
        self.rects = []          # (t0off, x0,y0,x1,y1, color, alpha, radius, wipe)
        self.echoes = []         # ghost type behind the block
        self.rings = []          # (x, y, r, th, color, alpha, delay, a0, a1)
        self.icon = None

    # -- entrance/exit envelope ------------------------------------------
    def word_state(self, t, it):
        lt = t - self.t0 - it.get("delay", 0.0)
        pin = ramp(lt, 0.0, it.get("dur", 0.46))
        e = out_back(pin)
        pout = ramp(t, self.t1 - 0.26, 0.26)
        alpha = min(1.0, pin * 2.4) * (1.0 - pout) * it.get("a", 1.0)
        scale = it["scale"] * lerp(0.82, 1.0, e)
        if it.get("pulse"):
            scale *= 1.0 + 0.06 * pulse(t, self.t0 + it["pulse"][0], self.t0 + it["pulse"][1])
        scale *= 1.0 + 0.05 * pout
        dy = lerp(it.get("rise", 74.0), 0.0, e)
        blur = (1.0 - pin) * it.get("blur", 20.0) + pout * 9.0
        return alpha, scale, dy, blur

    def draw(self, canvas, t):
        for e in self.echoes:
            lt = t - self.t0 - e["delay"]
            p = out_cubic(ramp(lt, 0.0, e.get("dur", 1.1)))
            pout = ramp(t, self.t1 - 0.3, 0.3)
            if p <= 0.01:
                continue
            Stage.paste(canvas, e["mask"], e["x"], e["y"], scale=e["scale"],
                        alpha=e["alpha"] * p * (1 - pout), color=e["color"],
                        blur=e.get("blur", 16.0))
        for (x, y, r, th, col, a, d, a0, a1) in self.rings:
            lt = t - self.t0 - d
            p = out_cubic(ramp(lt, 0.0, 0.9))
            pout = ramp(t, self.t1 - 0.3, 0.3)
            if p <= 0.01:
                continue
            Stage.ring(canvas, x, y, r * lerp(1.12, 1.0, p), th, col,
                       a * p * (1 - pout), a0, a1)
        for (d, x0, y0, x1, y1, col, a, rad, wipe) in self.rects:
            lt = t - self.t0 - d
            if lt < 0 or t > self.t1:
                continue
            grow = out_cubic(ramp(lt, 0.0, wipe))
            pout = ramp(t, self.t1 - 0.24, 0.24)
            aa = a * grow * (1 - pout)
            if aa <= 0.003:
                continue
            yy0, yy1 = y0, y1
            yc = (y0 + y1) / 2
            hh = max(1.0, (y1 - y0) * grow)
            Stage.rect(canvas, x0, yc - hh / 2, x1, yc + hh / 2, col, aa, rad)
        for it in self.items:
            alpha, scale, dy, blur = self.word_state(t, it)
            Stage.paste(canvas, it["mask"], it["x"], it["y"] + dy, scale=scale,
                        alpha=alpha, color=it["color"], blur=blur, glow=it.get("glow", 0.0))
        if self.icon is not None:
            it = self.icon
            lt = t - self.t0 - it.get("delay", 0.0)
            p = ramp(lt, 0.0, it.get("dur", 0.7))
            pout = ramp(t, self.t1 - 0.28, 0.28)
            if p > 0:
                sc = it["scale"] * lerp(0.6, 1.0, out_back(p))
                Stage.paste(canvas, it["mask"], it["x"], it["y"], scale=sc,
                            rot=lerp(it.get("rot0", -14.0), 0.0, out_cubic(p)),
                            alpha=out_cubic(p) * it.get("alpha", 0.9) * (1 - pout),
                            color=it["color"], blur=(1 - p) * 10)


def add_word(beat, sprites, word, x, y, size, color, delay, font="Cairo ExtraBold",
             scale=1.0, glow=0.0, rise=74.0, dur=0.46, pulse_win=None, blur=18.0):
    mask = sprites.text(word, size, font)
    beat.items.append(dict(mask=mask, x=x, y=y, scale=scale, color=color,
                           delay=delay, glow=glow, rise=rise, dur=dur,
                           pulse=pulse_win, blur=blur))


def add_block(beat, sprites, text, cx, cy, size, color, t_off=0.0, font="Cairo ExtraBold",
              glow=0.0, rise=54.0, dur=0.6, blur=24.0, scale=1.0):
    """One whole line as a single shaped sprite — keeps Arabic ligatures intact."""
    mask = sprites.text(text, size, font)
    beat.items.append(dict(mask=mask, x=cx, y=cy, scale=scale, color=color, delay=t_off,
                           glow=glow, rise=rise, dur=dur, blur=min(blur, 0.34 * size)))
    return mask


def add_line(beat, sprites, words, cx, cy, size, color, t_off=0.0, font="Cairo ExtraBold",
             max_width=920, scale=1.0, glow=0.0, stagger=0.075, rise=74.0,
             pulse_last=False, blur=18.0):
    """Word-by-word kinetic line (RTL). Returns the block's half-width / half-height."""
    lay = sprites.layout(words, size, font=font, max_width=max_width)
    for i, it in enumerate(lay):
        add_word(beat, sprites, it["word"], cx + it["cx"], cy + it["cy"], size, color,
                 delay=t_off + i * stagger, font=font, scale=scale, glow=glow, rise=rise,
                 pulse_win=(0.9, 1.5) if (pulse_last and i == len(lay) - 1) else None,
                 blur=blur)
    hw = max([abs(it["cx"]) + it["w"] / 2 for it in lay] + [1.0])
    hh = max([abs(it["cy"]) + it["h"] / 2 for it in lay] + [1.0])
    return hw, hh


def add_spine(beat, y0, y1, x=540, alpha=0.14):
    """Vertical hairline + lozenge marker: fills the upper frame with a design cue."""
    if y1 - y0 < 60:
        return
    beat.rects.append((0.15, x - 1, y0, x + 1, y1, GOLD2, alpha, 1, 0.65))
    beat.rects.append((0.05, x - 7, y0 - 7, x + 7, y0 + 7, GOLD2, 0.55, 3, 0.35))


def add_echo(beat, sprites, word, cx, cy, size, color=GOLD2, alpha=0.035,
             target_w=1120, delay=0.25, blur=30.0):
    """Ghost type: oversized, near-invisible word behind the block for depth."""
    mask = sprites.text(word, size, "Cairo ExtraBold")
    sc = max(1.0, min(4.0, target_w / max(1, mask.shape[1])))
    beat.echoes.append(dict(mask=mask, x=cx, y=cy, scale=sc, color=color,
                            alpha=alpha, delay=delay, dur=1.1, blur=blur))


# --------------------------------------------------------------------------- beats
class TitleBeat(Beat):
    def __init__(self, b):
        super().__init__(b["t0"], b["t1"], b.get("mood", "calm"))
        self.icon = dict(mask=SP.icon("mosque", 300), x=540, y=430, scale=0.72,
                         color=GOLD2, alpha=0.30, delay=0.0, rot0=-10.0)
        self.rings.append((540, 430, 250, 2, GOLD2, 0.30, 0.1, 0, 360))
        self.rings.append((540, 430, 300, 1, GOLD2, 0.16, 0.35, 0, 360))
        add_line(self, SP, b["kicker"].split(), 540, 700, 62, GOLD, t_off=0.0, stagger=0.05)
        add_line(self, SP, b["main"].split(), 540, 880, 190, IVORY, t_off=0.12,
                 stagger=0.14, glow=0.22)
        self.rects.append((0.45, 540 - 170, 1030, 540 + 170, 1044, GOLD2, 0.85, 3, 0.5))
        add_block(self, SP, b["sub"], 540, 1150, 74, MINT, t_off=0.6, rise=40, dur=0.5,
                  blur=14.0)


class HeroBeat(Beat):
    """One dominant phrase — big type, ghost echo, accent bar, optional kicker/sub."""
    def __init__(self, b):
        super().__init__(b["t0"], b["t1"], b.get("mood", "calm"))
        base_y = b.get("y", 950)
        main = b["main"]
        if b.get("echo"):
            add_echo(self, SP, b["echo"], 540, base_y - 20, 200,
                     color=b.get("echo_color", GOLD2), alpha=b.get("echo_alpha", 0.05))
        if b.get("kicker"):
            add_line(self, SP, b["kicker"].split(), 540, base_y - 268, 58, GOLD,
                     t_off=0.0, stagger=0.05)
            self.rects.append((0.16, 540 - 44, base_y - 196, 540 + 44, base_y - 190,
                               GOLD2, 0.75, 2, 0.5))
        hw, hh = add_line(self, SP, main.split(), 540, base_y, b.get("size", 205), IVORY,
                          t_off=0.10, stagger=0.13, glow=0.18, pulse_last=True,
                          max_width=b.get("maxw", 950))
        # vertical accent bar hugging the block
        if not b.get("icon"):
            add_spine(self, 330, base_y - hh - 70, alpha=0.13)
        if b.get("sub"):
            self.rects.append((0.5, 540 - 130, base_y + 196, 540 + 130, base_y + 204,
                               GOLD2, 0.7, 2, 0.45))
            add_block(self, SP, b["sub"], 540, base_y + 300, b.get("subsize", 76),
                      b.get("subcolor", MINT), t_off=0.62, rise=40, dur=0.5, blur=14.0)
        if b.get("icon"):
            iy = base_y - 520
            self.icon = dict(mask=SP.icon(b["icon"], 300), x=540, y=iy,
                             scale=0.80, color=GOLD2, alpha=0.44, delay=0.0, rot0=-12.0)
            self.rings.append((540, iy, 190, 2.0, GOLD2, 0.28, 0.2, 0, 360))
            self.rings.append((540, iy, 245, 1.0, GOLD2, 0.14, 0.45, 0, 360))


class QuoteBeat(Beat):
    """A spoken quotation: framed card, whole lines (ligature-safe), gilded rules."""
    def __init__(self, b):
        super().__init__(b["t0"], b["t1"], b.get("mood", "warm"))
        size = b.get("size", 126)
        font = b.get("font", "Amiri Bold")
        lines = b["text"].split("\\N")
        masks = [SP.text(ln, size, font) for ln in lines]
        gap = size * 0.42
        heights = [m.shape[0] for m in masks]
        total = sum(heights) + gap * (len(lines) - 1)
        cy = b.get("cy", 950)
        pad = b.get("pad", 104)
        top, bot = cy - total / 2 - pad, cy + total / 2 + pad
        fill = b.get("panel", C("1B1209"))
        self.rects.append((0.0, 84, top, W - 84, bot, fill, 0.52, 70, 0.42))
        self.rects.append((0.0, 84, top, W - 84, top + 2, GOLD2, 0.60, 1, 0.42))
        self.rects.append((0.30, 84, bot - 2, W - 84, bot, GOLD2, 0.60, 1, 0.42))
        # label above the card, with a gold lozenge on its right (RTL)
        lab = b["label"]
        lm = SP.text(lab, 46, "Cairo Bold")
        add_block(self, SP, lab, 540, top - 72, 46, GOLD, t_off=0.10, rise=34, dur=0.5,
                  blur=16.0)
        lx = 540 + lm.shape[1] / 2 + 34
        self.rects.append((0.16, lx, top - 78, lx + 11, top - 67, GOLD2, 0.9, 3, 0.4))
        if b.get("icon"):
            iy = top - 250
            self.icon = dict(mask=SP.icon(b["icon"], 200), x=540, y=iy, scale=0.62,
                             color=GOLD2, alpha=0.32, delay=0.0, rot0=-9.0)
            self.rings.append((540, iy, 128, 1.6, GOLD2, 0.22, 0.28, 0, 360))
        else:
            add_spine(self, top - 300, top - 150, alpha=0.12)
        # quote lines
        color = b.get("color_", C("F8E9C8"))
        y = cy - total / 2
        for i, m in enumerate(masks):
            self.items.append(dict(mask=m, x=540, y=y + heights[i] / 2, scale=1.0,
                                   color=color, delay=0.24 + i * 0.16, glow=0.12,
                                   rise=44.0, dur=0.6, blur=26.0))
            y += heights[i] + gap


class CaptionBeat(Beat):
    """Narration: kinetic keyword line + supporting line, lit by a ghost word."""
    def __init__(self, b):
        super().__init__(b["t0"], b["t1"], b.get("mood", "calm"))
        y = b.get("y", 1180)
        main = b.get("main", "")
        if not b.get("icon"):
            key = b.get("echo") or (max(main.split(), key=len) if main.split() else main)
            add_echo(self, SP, key, 540, y - 6, 180, alpha=b.get("echo_alpha", 0.028),
                     color=b.get("echo_color", GOLD2), delay=0.1, target_w=860)
        iy = b.get("icon_y", 660)
        if b.get("icon"):
            self.icon = dict(mask=SP.icon(b["icon"], 210), x=540, y=iy, scale=0.66,
                             color=GOLD2, alpha=b.get("iconalpha", 0.40), delay=0.0,
                             rot0=-10.0)
            self.rings.append((540, iy, 138, 1.8, GOLD2, 0.26, 0.25, 0, 360))
            self.rings.append((540, iy, 190, 1.0, GOLD2, 0.13, 0.5, 0, 360))
        else:
            add_spine(self, iy - 130, y - 200, alpha=0.12)
        self.rects.append((0.24, 540 - 32, y - 128, 540 + 32, y - 125, GOLD2, 0.35, 2, 0.5))
        add_line(self, SP, main.split(), 540, y, b.get("size", 96), IVORY,
                 t_off=0.02, stagger=0.055, rise=44, max_width=940)
        if b.get("sub"):
            add_block(self, SP, b["sub"], 540, y + 152, b.get("subsize", 70),
                      b.get("subcolor", GOLD), t_off=0.18, rise=40, dur=0.5, blur=14.0)


class IconBeat(Beat):
    """Big glyph inside rings + text underneath — the 'scene' beats."""
    def __init__(self, b):
        super().__init__(b["t0"], b["t1"], b.get("mood", "calm"))
        iy = b.get("icon_y", 720)
        self.icon = dict(mask=SP.icon(b["icon"], 320), x=540, y=iy, scale=0.9,
                         color=b.get("iconcolor", GOLD2), alpha=b.get("iconalpha", 0.9),
                         delay=0.0, dur=0.75, rot0=b.get("rot0", -12.0))
        self.rings.append((540, iy, 232, 2.5, GOLD2, 0.40, 0.18, 0, 360))
        self.rings.append((540, iy, 288, 1.2, GOLD2, 0.20, 0.42, 0, 360))
        y = b.get("y", 1150)
        add_line(self, SP, b["main"].split(), 540, y, b.get("size", 132), IVORY,
                 t_off=0.22, stagger=0.09, glow=0.1, max_width=900)
        if b.get("sub"):
            add_block(self, SP, b["sub"], 540, y + 168, b.get("subsize", 72),
                      b.get("subcolor", MINT), t_off=0.55, rise=40, dur=0.5, blur=14.0)


class CounterBeat(Beat):
    def __init__(self, b):
        super().__init__(b["t0"], b["t1"], b.get("mood", "battle"))
        self.n_from, self.n_to = b.get("from", 1), b.get("to", 7)
        add_line(self, SP, b["label"].split(), 540, 690, 62, GOLD, t_off=0.0, stagger=0.05)
        self.txt_y = 980
        self.counter_style = b

    def draw(self, canvas, t):
        p = ramp(t - self.t0, 0.05, 0.4)
        pout = ramp(t, self.t1 - 0.25, 0.25)
        frac = in_out(ramp(t, self.t0 + 0.2, 1.6))
        Stage.ring(canvas, 540, self.txt_y, 300, 9, GOLD2, 0.45 * p * (1 - pout),
                   -90, -90 + 360 * frac)
        Stage.ring(canvas, 540, self.txt_y, 330, 1.2, GOLD2, 0.18 * p * (1 - pout),
                   0, 360)
        n = self.n_from + int(round((self.n_to - self.n_from) * frac))
        mask = SP.text(str(n), 400, "Tajawal ExtraBold")
        Stage.paste(canvas, mask, 540, self.txt_y, scale=lerp(1.15, 1.0, out_back(p)),
                    alpha=p * (1 - pout), color=GOLD, glow=0.2)
        super().draw(canvas, t)


class EndBeat(Beat):
    def __init__(self, b):
        super().__init__(b["t0"], b["t1"], b.get("mood", "end"))
        self.icon = dict(mask=SP.icon("favorite", 270), x=540, y=650, scale=0.64,
                         color=GOLD2, alpha=0.26, delay=0.0, rot0=-8.0)
        self.rings.append((540, 650, 170, 1.6, GOLD2, 0.18, 0.3, 0, 360))
        self.rings.append((540, 650, 225, 1.0, GOLD2, 0.10, 0.55, 0, 360))
        add_block(self, SP, b["label"], 540, 850, 50, GOLD, t_off=0.10, rise=34, dur=0.55)
        parts = b["main"].split("\\N")
        add_block(self, SP, parts[0], 540, 995, 112, IVORY, t_off=0.30, glow=0.14)
        if len(parts) > 1:
            add_block(self, SP, parts[1], 540, 1135, 112, IVORY, t_off=0.55, glow=0.14)
        self.rects.append((0.8, 540 - 150, 1225, 540 + 150, 1232, GOLD2, 0.8, 2, 0.4))
        add_block(self, SP, "FIGO MOTION", 540, 1615, 44, MINT, t_off=0.7, rise=24, dur=0.5)


KINDS = dict(title=TitleBeat, hero=HeroBeat, quote=QuoteBeat, caption=CaptionBeat,
             icon=IconBeat, counter=CounterBeat, end=EndBeat)


# --------------------------------------------------------------------------- render
def build_beats():
    return [KINDS[b["kind"]](b) for b in S.BEATS]


def render(out_path: str, audio: str | None, fps: int = 30, crf: int = 19,
           progress: bool = True, probe: float | None = None):
    beats = build_beats()
    dur = S.DURATION
    n = int(dur * fps)
    stage = Stage(palette="seerah")
    env = audio_envelope(audio, n, fps) if audio else None

    if probe is not None:
        canvas = frame_at(stage, beats, probe, env, n, fps)
        Image.fromarray(canvas).save("/tmp/probe.png")
        print("probe -> /tmp/probe.png")
        return

    vf = ("noise=alls=6:allf=t+u,eq=contrast=1.05:saturation=1.05:gamma=1.01,"
          "vignette=angle=PI/7,format=yuv420p")
    cmd = [ffmpeg_bin(), "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{W}x{H}", "-r", str(fps), "-i", "pipe:0"]
    if audio:
        cmd += ["-i", audio]
    else:
        cmd += ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-shortest"]
    cmd += ["-vf", vf, "-c:v", "libx264", "-preset", "veryfast", "-crf", str(crf),
            "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.2",
            "-x264-params", "keyint=60:min-keyint=30",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart",
            out_path]
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        for i in range(n):
            t = i / fps
            canvas = frame_at(stage, beats, t, env, n, fps, i)
            proc.stdin.write(canvas.tobytes())
            if progress and i % 60 == 0:
                sys.stderr.write(f"\r  frame {i}/{n} ({100 * i / n:4.1f}%)")
                sys.stderr.flush()
    finally:
        if proc.stdin:
            proc.stdin.close()
        err = proc.stderr.read().decode("utf-8", "replace")
        code = proc.wait()
    if progress:
        sys.stderr.write("\r" + " " * 44 + "\r")
    if code != 0:
        raise RuntimeError(f"ffmpeg failed:\n{err[-2000:]}")


def overlay(canvas, t):
    """Global design layer: chapter marker on top, progress line at the bottom."""
    p = ramp(t, 1.0, 0.9)
    if p <= 0.01:
        return
    lab = S.CHAPTERS[0][1]
    for t0, name in S.CHAPTERS:
        if t >= t0 - 0.15:
            lab = name
    m = SP.text(lab, 40, "Cairo Medium")
    Stage.paste(canvas, m, 540, 156, alpha=0.50 * p, color=GOLD2)
    Stage.rect(canvas, 540 - 34, 186, 540 + 34, 188, GOLD2, 0.22 * p, 1)
    y = 1840
    x0, x1 = 100, W - 100
    Stage.rect(canvas, x0, y, x1, y + 3, IVORY, 0.09 * p, 2)
    f = x0 + (x1 - x0) * min(1.0, t / S.DURATION)
    Stage.rect(canvas, x0, y, max(x0 + 4, f), y + 3, GOLD2, 0.55 * p, 2)


def frame_at(stage, beats, t, env, n, fps, i=None):
    i = int(t * fps) if i is None else i
    active = [b for b in beats if b.t0 <= t < b.t1]
    mood = active[-1].mood if active else "calm"
    # punch-in zoom right after a beat starts
    zoom = 1.0
    for b in active:
        lt = t - b.t0
        if lt < 0.5:
            zoom = 1.0 + 0.06 * (1 - out_cubic(lt / 0.5))
    flash = 0.0
    for b in beats:
        d = abs(t - b.t0)
        if d < 0.14:
            flash = max(flash, (1 - d / 0.14) * 0.45)
    fade = 0.0
    if t < 0.6:
        fade = 1 - t / 0.6
    if S.DURATION - t < 1.0:
        fade = max(fade, 1 - (S.DURATION - t))
    win = env[max(0, i - 72):i + 5] if env is not None else None
    canvas = stage.background(t, env=win, progress=None,
                              mood=mood, flash=flash, fade=fade * 0.9, zoom=zoom)
    for b in active:
        b.draw(canvas, t)
    overlay(canvas, t)
    return Stage.finish(canvas)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--audio", default=os.path.join(HERE, "media", "voice.mp3"))
    ap.add_argument("--out", default=os.path.join(HERE, "deliver", "final_v2.mp4"))
    ap.add_argument("--crf", type=int, default=19)
    ap.add_argument("--probe", type=float, default=None)
    args = ap.parse_args()
    audio = args.audio if os.path.exists(args.audio) else None
    render(args.out, audio, crf=args.crf, probe=args.probe)
    if args.probe is None:
        print("wrote", args.out, round(os.path.getsize(args.out) / 1048576, 1), "MB")


if __name__ == "__main__":
    main()
