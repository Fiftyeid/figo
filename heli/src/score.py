# -*- coding: utf-8 -*-
"""
Original background score, synthesised from scratch (no samples, no third-party music).

Three styles, all built to sit *under* a narrator (sustained, sparse, no busy rhythm):
  doc      - cinematic documentary: felt piano arpeggios + string ensemble + low strings
  mystery  - curiosity / investigation: soft pulse, music-box plucks with echo, dark pad, clock tick
  oriental - calm Oriental: drone, ney-like melody in maqam Hijaz on D, qanun touches, no percussion

The arrangement follows the video: quiet cold open -> swell on the title sting -> light bridge ->
"movements" that change texture every ~100 s on section boundaries (with a breath between them)
-> warm outro that resolves and fades.

    render(style, tl, t1=None) -> float32 array (n, 2)   (tl = build/timeline.json dict)
"""
import math
import numpy as np
from scipy import signal

SR = 48000


def midi(n):
    return 440.0 * 2 ** ((n - 69) / 12.0)


# ------------------------------------------------------------------ DSP helpers
def _f(kind, fc, order):
    if kind == "band":
        return signal.butter(order, [fc[0] / (SR / 2), min(fc[1], SR / 2 - 200) / (SR / 2)], "band")
    return signal.butter(order, min(fc, SR / 2 - 200) / (SR / 2), kind)


def lp(x, fc, order=2):
    b, a = _f("low", fc, order)
    return signal.lfilter(b, a, x)


def hp(x, fc, order=2):
    b, a = _f("high", fc, order)
    return signal.lfilter(b, a, x)


def bp(x, f1, f2, order=2):
    b, a = _f("band", (f1, f2), order)
    return signal.lfilter(b, a, x)


def env_ar(n, a, r, curve=1.6):
    """Attack / sustain / release envelope over n samples (a, r in seconds)."""
    e = np.ones(n, np.float32)
    na, nr = min(n, int(a * SR)), min(n, int(r * SR))
    if na > 0:
        e[:na] = (0.5 - 0.5 * np.cos(np.linspace(0, np.pi, na))) ** (curve / 1.6)
    if nr > 0:
        e[n - nr:] *= np.linspace(1, 0, nr) ** curve
    return e


class Bus:
    """Stereo dry bus + mono reverb send, filled with note events."""

    def __init__(self, dur):
        self.n = int(dur * SR)
        self.L = np.zeros(self.n, np.float32)
        self.R = np.zeros(self.n, np.float32)
        self.send = np.zeros(self.n, np.float32)

    def add(self, x, t, gain=1.0, pan=0.0, rev=0.3, width=0.0):
        """pan -1..1; width = Haas delay (s) on the far side for wide sources."""
        i0 = int(round(t * SR))
        if i0 >= self.n or gain <= 0:
            return
        if i0 < 0:
            x = x[-i0:]
            i0 = 0
        i1 = min(self.n, i0 + len(x))
        seg = x[: i1 - i0] * gain
        gl, gr = math.cos((pan + 1) * math.pi / 4), math.sin((pan + 1) * math.pi / 4)
        self.L[i0:i1] += seg * gl * 1.41
        if width > 0:
            d = int(width * SR)
            j0 = min(self.n, i0 + d)
            j1 = min(self.n, i1 + d)
            self.R[j0:j1] += seg[: j1 - j0] * gr * 1.41
        else:
            self.R[i0:i1] += seg * gr * 1.41
        self.send[i0:i1] += seg * rev


def make_ir(seconds=3.2, t60=(3.2, 2.5, 1.1), predelay=0.025, seed=3):
    rng = np.random.default_rng(seed)
    n = int(seconds * SR)
    t = np.arange(n) / SR
    irs = []
    for ch in range(2):
        nz = rng.standard_normal(n)
        ir = (lp(nz, 700) * np.exp(-t * 6.91 / t60[0]) +
              0.8 * bp(nz, 700, 4000) * np.exp(-t * 6.91 / t60[1]) +
              0.35 * hp(nz, 4000) * np.exp(-t * 6.91 / t60[2]))
        ir[: int(predelay * SR)] = 0
        ir *= np.clip(t / 0.06, 0, 1)            # soft onset: no early "slap"
        irs.append((ir / np.sqrt((ir ** 2).sum())).astype(np.float32))
    return irs


def convolve(x, ir, block=1 << 19):
    L = len(ir)
    N = 1 << int(math.ceil(math.log2(block + L - 1)))
    H = np.fft.rfft(ir, N)
    y = np.zeros(len(x) + L - 1, np.float32)
    for i in range(0, len(x), block):
        seg = x[i:i + block]
        if not np.any(seg):
            continue
        Y = np.fft.irfft(np.fft.rfft(seg, N) * H, N)[: len(seg) + L - 1]
        y[i:i + len(Y)] += Y.astype(np.float32)
    return y


# ------------------------------------------------------------------ instruments
class Inst:
    def __init__(self, seed=11):
        self.rng = np.random.default_rng(seed)
        self.cache = {}

    # felt piano: inharmonic partials, 3 detuned strings per note, soft hammer, low-passed
    def piano(self, m, bright=0.45):
        key = ("pno", m, bright)
        if key in self.cache:
            return self.cache[key]
        f0 = midi(m)
        dur = 5.5 if m < 72 else 4.0
        n = int(dur * SR)
        t = np.arange(n) / SR
        B = 0.00015 * (f0 / 261.6) ** 0.5
        out = np.zeros(n)
        for k in range(1, 15):
            fk = k * f0 * math.sqrt(1 + B * k * k)
            if fk > 8000:
                break
            amp = (1.0 / k ** 1.25) * math.exp(-(k - 1) * (0.9 - bright) * 0.5)
            dec = 2.6 * (261.6 / f0) ** 0.45 / (1 + 0.55 * (k - 1))
            for det in (-0.7, 0.0, 0.6):
                ff = fk * 2 ** (det / 1200)
                out += (amp / 3) * np.sin(2 * np.pi * ff * t + self.rng.random() * 6.283) * \
                    (0.75 * np.exp(-t / dec) + 0.25 * np.exp(-t / (dec * 3.5)))
        h = int(0.025 * SR)
        thump = lp(self.rng.standard_normal(h), 900) * np.exp(-np.arange(h) / (0.005 * SR))
        out[:h] += 0.05 * thump
        a = int(0.006 * SR)
        out[:a] *= np.linspace(0, 1, a)
        out = lp(out, 1800 + 3000 * bright)
        r = int(0.4 * SR)
        out[-r:] *= np.linspace(1, 0, r)
        out = (out / (np.abs(out).max() + 1e-9)).astype(np.float32)
        self.cache[key] = out
        return out

    # string ensemble pad (5 detuned saws per note, slow bow, gentle vibrato)
    def strings(self, notes, dur, bright=0.45, attack=1.1, release=1.8, voices=5):
        n = int((dur + release) * SR)
        t = np.arange(n) / SR
        out = np.zeros(n)
        for m in notes:
            f = midi(m)
            vib = 1 + 0.0022 * np.sin(2 * np.pi * (4.6 + self.rng.random()) * t + self.rng.random() * 6.283)
            for v in range(voices):
                det = (v - (voices - 1) / 2) * 0.06 + self.rng.normal(0, 0.012)
                ph = np.cumsum(f * 2 ** (det / 12) * vib) / SR + self.rng.random()
                out += (2 * (ph % 1.0) - 1) / voices
        out = lp(lp(out, 900 + 2200 * bright), 5200)
        out *= env_ar(n, attack, release)
        return (out / max(1.0, len(notes)) * 0.9).astype(np.float32)

    # low bowed string / drone
    def low(self, m, dur, attack=1.5, release=2.0, cutoff=520):
        n = int((dur + release) * SR)
        t = np.arange(n) / SR
        f = midi(m)
        out = np.zeros(n)
        vib = 1 + 0.003 * np.sin(2 * np.pi * 4.3 * t)
        for det in (-0.05, 0.0, 0.05):
            ph = np.cumsum(f * 2 ** (det / 12) * vib) / SR + self.rng.random()
            out += (2 * (ph % 1.0) - 1) / 3
        out = lp(lp(out, cutoff), cutoff * 2.5)
        out *= env_ar(n, attack, release)
        return out.astype(np.float32)

    # Karplus-Strong pluck (music box / qanun / pizzicato)
    def pluck(self, m, bright=0.6, dur=2.2, decay=0.997, tone_lp=6000):
        key = ("ks", m, bright, dur, decay)
        if key in self.cache:
            return self.cache[key]
        f = midi(m)
        n = int(dur * SR)
        N = max(2, int(round(SR / f)))
        y = np.zeros(n + N + 2, np.float64)
        burst = lp(self.rng.uniform(-1, 1, N), 1200 + 6000 * bright)
        y[:N] = burst
        y[N] = decay * 0.5 * (y[0] + y[N - 1])
        b = N + 1
        while b < len(y):
            e = min(len(y), b + N)
            y[b:e] = decay * 0.5 * (y[b - N:e - N] + y[b - N - 1:e - N - 1])
            b = e
        y = lp(y[:n], tone_lp)
        y *= env_ar(n, 0.002, 0.3)
        y = (y / (np.abs(y).max() + 1e-9)).astype(np.float32)
        self.cache[key] = y
        return y

    # FM bell / celesta
    def bell(self, m, dur=3.5):
        key = ("bell", m)
        if key in self.cache:
            return self.cache[key]
        f = midi(m)
        n = int(dur * SR)
        t = np.arange(n) / SR
        I = 1.6 * np.exp(-t / 0.5)
        x = np.sin(2 * np.pi * f * t + I * np.sin(2 * np.pi * f * 3.5 * t)) * np.exp(-t / 1.3)
        x += 0.25 * np.sin(2 * np.pi * f * 2 * t) * np.exp(-t / 0.6)
        x *= env_ar(n, 0.003, 0.5)
        x = lp(x, 7000)
        x = (x / np.abs(x).max()).astype(np.float32)
        self.cache[key] = x
        return x

    # soft filtered pulse (mystery ostinato)
    def pulse(self, m, L=0.26, cutoff=420):
        key = ("pulse", m, cutoff)
        if key in self.cache:
            return self.cache[key]
        f = midi(m)
        n = int(L * SR)
        t = np.arange(n) / SR
        ph = (f * t + 0.3) % 1.0
        x = (2 * ph - 1) + 0.6 * np.sin(2 * np.pi * f * t)
        x = lp(lp(x, cutoff), cutoff * 1.8) * np.exp(-t / 0.11)
        x[: int(0.004 * SR)] *= np.linspace(0, 1, int(0.004 * SR))
        x = (x / np.abs(x).max()).astype(np.float32)
        self.cache[key] = x
        return x

    def tick(self):
        if "tick" not in self.cache:
            n = int(0.05 * SR)
            x = hp(self.rng.standard_normal(n), 7000) * np.exp(-np.arange(n) / (0.012 * SR))
            self.cache["tick"] = (x / np.abs(x).max()).astype(np.float32)
        return self.cache["tick"]

    # ney-like breathy flute: one legato phrase = list of (midi, beats), glides between notes
    def ney(self, phrase, beat):
        segs = [(m, b * beat) for m, b in phrase]
        tot = sum(d for _, d in segs) + 0.6
        n = int(tot * SR)
        t = np.arange(n) / SR
        f = np.zeros(n)
        amp = np.zeros(n)
        pos = 0
        prev = None
        for m, d in segs:
            k = int(d * SR)
            fm = midi(m)
            seg_f = np.full(k, fm)
            if prev is not None:                         # 70 ms portamento from the previous note
                g = min(k, int(0.07 * SR))
                seg_f[:g] = prev * (fm / prev) ** (0.5 - 0.5 * np.cos(np.linspace(0, np.pi, g)))
            tt = np.arange(k) / SR                       # vibrato grows in after 0.3 s
            depth = 0.0045 * np.clip((tt - 0.3) / 0.6, 0, 1)
            seg_f *= 1 + depth * np.sin(2 * np.pi * 5.0 * tt)
            f[pos:pos + k] = seg_f
            a = np.ones(k)
            dip = min(k, int(0.06 * SR))
            a[:dip] = 0.82 + 0.18 * np.linspace(0, 1, dip)   # small re-articulation
            amp[pos:pos + k] = a
            pos += k
            prev = fm
        f[pos:] = prev
        amp[pos:] = 0
        amp *= env_ar(n, 0.18, 0.0)
        rel = int(0.35 * SR)
        amp[pos - rel // 2:pos + rel // 2] *= np.linspace(1, 0, len(amp[pos - rel // 2:pos + rel // 2]))
        ph = 2 * np.pi * np.cumsum(f) / SR
        tone = np.sin(ph) + 0.30 * np.sin(2 * ph) + 0.11 * np.sin(3 * ph) + 0.04 * np.sin(4 * ph)
        nz = self.rng.standard_normal(n)
        breath = bp(nz, 500, 2600) * 0.22 + hp(nz, 3500) * 0.05
        x = (tone * (0.85 + 0.15 * lp(np.abs(nz), 8)) + breath) * amp
        x = lp(x, 4200)
        return (x / (np.abs(x).max() + 1e-9) * 0.9).astype(np.float32)


# ------------------------------------------------------------------ form (from the timeline)
def form(tl):
    secs = tl["sections"]
    dur = tl["duration"]
    intro = secs[0]
    title = intro["title_at"]
    body0 = secs[1]["start"] - 0.25
    outro0 = secs[-1]["start"] - 0.25
    # movements: change texture on a section boundary roughly every 100 s, with a 1-bar breath
    bounds = [body0]
    for s in secs[2:-1]:
        if s["start"] - bounds[-1] >= 95:
            bounds.append(s["start"] - 0.25)
    return dict(dur=dur, title=title, body0=body0, outro0=outro0, moves=bounds)


def _grid(t0, t1, step):
    k0 = int(math.ceil(t0 / step - 1e-9))
    t = k0 * step
    while t < t1 - 1e-9:
        yield t
        t += step


# ------------------------------------------------------------------ style: cinematic documentary
DOC_CHORDS = [  # (pad voicing, bass, piano arpeggio tones, melody top note)
    ([50, 53, 57, 62], 38, [62, 69, 74, 77], 81),   # Dm
    ([50, 53, 58, 62], 34, [58, 65, 70, 74], 77),   # Bb
    ([48, 53, 57, 60], 41, [60, 65, 72, 76], 81),   # F
    ([48, 52, 55, 60], 36, [60, 67, 72, 76], 79),   # C
    ([50, 53, 57, 62], 38, [62, 69, 74, 77], 81),   # Dm
    ([50, 53, 58, 62], 34, [58, 65, 70, 74], 77),   # Bb
    ([50, 55, 58, 62], 43, [62, 67, 70, 74], 79),   # Gm
    ([49, 52, 57, 61], 33, [61, 64, 69, 73], 76),   # A
]


def style_doc(bus, I, F, t1):
    bpm = 72.0
    beat = 60 / bpm
    bar = 4 * beat
    rng = np.random.default_rng(5)
    title = F["title"]
    # cold open: low D drone + sparse high piano, swelling a little towards the title
    bus.add(I.low(38, title + 1.0, attack=2.5, release=2.5), 0.0, 0.55, rev=0.25)
    bus.add(I.low(45, title + 1.0, attack=3.5, release=2.5), 0.0, 0.30, pan=0.15, rev=0.25)
    for k, t in enumerate(_grid(0.6, title - 1.2, bar / 2)):
        m = [74, 69, 77, 72, 74, 70, 76, 69][k % 8]
        bus.add(I.piano(m, 0.35), t + rng.normal(0, 0.01), 0.20, pan=-0.2, rev=0.55)
    bus.add(I.strings([62, 69], title - 4.0, bright=0.35, attack=5.0, release=1.5), 4.0, 0.22, rev=0.5, width=0.012)
    # title sting: full Dm chord + low octave
    bus.add(I.strings([50, 57, 62, 65, 69], 4.0, bright=0.6, attack=0.15, release=3.0), title, 0.55, rev=0.55, width=0.012)
    bus.add(I.low(38, 3.5, attack=0.08, release=3.0, cutoff=700), title, 0.65, rev=0.35)
    bus.add(I.piano(38, 0.5), title + 0.02, 0.45, rev=0.5)
    bus.add(I.piano(50, 0.5), title + 0.02, 0.35, rev=0.5)
    # body: 8-bar cycles from the end of the sting
    start = title + 3.2
    moves = F["moves"] + [F["outro0"]]
    end = math.floor((F["dur"] - 6.5) / bar) * bar     # final chord on the bar grid
    k = 0
    for t in _grid(start, min(t1, end), bar):
        pad, bass, arp, top = DOC_CHORDS[7 if t + bar > end - 1e-6 else k % 8]   # A -> D at the very end
        k += 1
        if t >= F["outro0"]:
            mv = "outro"
        elif t < F["body0"]:
            mv = "bridge"
        else:
            mi = max(i for i, b in enumerate(moves[:-1]) if b <= t + 1e-6)
            nxt = moves[mi + 1]
            if nxt - t < bar:                            # last bar before a new movement: breathe
                bus.add(I.strings(pad, bar, bright=0.35, attack=0.8, release=2.0), t, 0.30, rev=0.5, width=0.012)
                continue
            mv = ("A", "B", "C")[mi % 3]
        lvl = {"bridge": 0.30, "A": 0.34, "B": 0.38, "C": 0.42, "outro": 0.46}[mv]
        bus.add(I.strings(pad, bar, bright=0.45 if mv != "outro" else 0.55), t, lvl, rev=0.5, width=0.012)
        if mv in ("C", "outro"):
            bus.add(I.low(bass + 12, bar, attack=0.9, release=1.6, cutoff=600), t, 0.42, rev=0.3)
        # piano arpeggio (8ths with rests); sparser in C
        pat = [(0, 0), (2, 1), (3, 2), (5, 1), (6, 3)] if mv != "C" else [(0, 0), (4, 2)]
        for pos, ti in pat:
            v = (0.30 if pos == 0 else 0.22) + rng.normal(0, 0.02)
            bus.add(I.piano(arp[ti]), t + pos * beat / 2 + rng.normal(0, 0.008), v, pan=-0.25, rev=0.4)
        if mv in ("B", "outro") and (k % 2 == 1):
            bus.add(I.piano(top, 0.5), t + rng.normal(0, 0.006), 0.30, pan=0.1, rev=0.5)
    # ending: resolve to D major (Picardy) and let it ring
    if end < t1:
        bus.add(I.strings([50, 54, 57, 62, 66], 4.5, bright=0.5, attack=1.2, release=2.5), end, 0.45, rev=0.6, width=0.012)
        bus.add(I.piano(62, 0.45), end, 0.30, rev=0.6)
        bus.add(I.piano(66, 0.45), end + 0.3, 0.24, rev=0.6)
        bus.add(I.piano(69, 0.45), end + 0.6, 0.22, rev=0.6)


# ------------------------------------------------------------------ style: mystery / curiosity
MYS_CHORDS = [  # (pad, bass root, pluck pattern over 8 eighths)
    ([50, 57, 62, 65], 38, [74, 81, 77, 81, 74, 81, 77, 76]),   # Dm
    ([46, 53, 58, 62], 34, [74, 82, 77, 82, 74, 82, 77, 74]),   # Bb
    ([43, 50, 55, 58], 31, [74, 79, 82, 79, 74, 79, 82, 81]),   # Gm
    ([45, 52, 57, 61], 33, [73, 76, 81, 76, 73, 76, 81, 79]),   # A
]


def style_mystery(bus, I, F, t1):
    bpm = 100.0
    beat = 60 / bpm
    bar = 4 * beat
    rng = np.random.default_rng(9)
    title = F["title"]
    # cold open: dark pad + bell notes, no pulse (suspense)
    bus.add(I.strings([50, 57, 62], title + 0.5, bright=0.25, attack=3.0, release=2.0), 0.0, 0.42, rev=0.55, width=0.015)
    bus.add(I.low(38, title + 0.5, attack=3.0, release=2.0, cutoff=380), 0.0, 0.40, rev=0.3)
    for k, t in enumerate(_grid(1.0, title - 1.0, 2 * bar)):
        bus.add(I.bell([81, 77, 76, 74][k % 4]), t, 0.16, pan=0.35 if k % 2 else -0.35, rev=0.7)
    # sting
    bus.add(I.strings([50, 57, 62, 65, 69], 3.5, bright=0.5, attack=0.12, release=3.0), title, 0.5, rev=0.6, width=0.015)
    bus.add(I.low(38, 3.0, attack=0.05, release=2.5, cutoff=600), title, 0.6, rev=0.3)
    start = title + 3.2
    moves = F["moves"] + [F["outro0"]]
    k = 0
    echo = int(0.75 * beat * SR)
    for t in _grid(start, min(t1, F["dur"] - 6.0 - bar), bar):
        pad, root, pl = MYS_CHORDS[(k // 2) % 4]
        k += 1
        if t >= F["outro0"]:
            mv = "outro"
        elif t < F["body0"]:
            mv = "bridge"
        else:
            mi = max(i for i, b in enumerate(moves[:-1]) if b <= t + 1e-6)
            if moves[mi + 1] - t < bar:
                bus.add(I.strings(pad, bar, bright=0.25, attack=0.6, release=1.5), t, 0.34, rev=0.55, width=0.015)
                continue
            mv = ("A", "B", "C")[mi % 3]
        if k % 2 == 1:
            bus.add(I.strings(pad, 2 * bar, bright=0.3, attack=1.0, release=1.6), t, 0.36, rev=0.55, width=0.015)
        if mv in ("A", "C", "outro") or mv == "bridge":
            for e in range(8):                           # soft 8th-note pulse
                v = 0.30 if e % 4 == 0 else 0.20
                bus.add(I.pulse(root + (12 if e % 2 else 0)), t + e * beat / 2, v, rev=0.15)
        if mv in ("A", "B", "outro"):
            for e in range(8):                           # music-box ostinato with a dotted-8th echo
                if mv == "outro" and e % 2:
                    continue
                x = I.pluck(pl[e], bright=0.75, dur=1.4, decay=0.996)
                tt = t + e * beat / 2 + rng.normal(0, 0.005)
                p = -0.3 if e % 2 else 0.3
                bus.add(x, tt, 0.16, pan=p, rev=0.45)
                bus.add(x, tt + echo / SR, 0.07, pan=-p, rev=0.6)
        if mv in ("A", "B"):
            for e in range(8):                           # clock tick
                bus.add(I.tick(), t + e * beat / 2 + (0.02 if e % 2 else 0), 0.05 if e % 2 else 0.03, pan=0.4, rev=0.1)
        if mv == "C" and k % 4 == 1:
            bus.add(I.bell(pl[0] + 7), t, 0.14, pan=-0.3, rev=0.7)
    end = F["dur"] - 6.0
    if end < t1:
        bus.add(I.strings([50, 57, 62, 66], 4.5, bright=0.35, attack=1.0, release=2.5), end, 0.42, rev=0.6, width=0.015)
        bus.add(I.bell(74), end + 0.2, 0.18, rev=0.7)
        bus.add(I.bell(81), end + 1.0, 0.12, rev=0.7)


# ------------------------------------------------------------------ style: calm Oriental (Hijaz on D)
# D Eb F# G A Bb C D  ->  62 63 66 67 69 70 72 74
NEY_PHRASES = [
    [(69, 2), (70, 1), (69, 1), (67, 1), (66, 2), (63, 1), (62, 4)],
    [(62, 1), (66, 1), (67, 1), (69, 3), (70, 1), (69, 1), (67, 1), (66, 1), (67, 4)],
    [(74, 2), (72, 1), (70, 1), (69, 2), (67, 1), (66, 1), (69, 4)],
    [(69, 1), (70, 1), (72, 2), (70, 1), (69, 1), (67, 2), (66, 1), (63, 1), (62, 4)],
]


def style_oriental(bus, I, F, t1):
    bpm = 66.0
    beat = 60 / bpm
    bar = 4 * beat
    title = F["title"]
    total = min(t1, F["dur"])
    # drone the whole way: D2 + A2 + D3, breathing slowly
    seg = 24.0
    t = 0.0
    k = 0
    while t < total:
        L = min(seg, total - t) + 0.1
        g = 0.42 if k % 2 == 0 else 0.36
        bus.add(I.low(38, L, attack=4.0, release=4.0, cutoff=420), t, g, rev=0.3)
        bus.add(I.low(45, L, attack=5.0, release=4.0, cutoff=500), t + 1.0, g * 0.6, pan=0.2, rev=0.35)
        bus.add(I.strings([62, 69], L, bright=0.25, attack=5.0, release=4.0, voices=3), t + 2.0, 0.16, rev=0.6, width=0.014)
        t += seg - 4.0
        k += 1
    # cold open: one slow ney phrase, then qanun shimmer into the sting
    bus.add(I.ney(NEY_PHRASES[0], beat * 1.15), 2.0, 0.34, pan=0.1, rev=0.6)
    for j in range(10):
        bus.add(I.pluck(74 if j % 2 else 69, bright=0.85, dur=1.0, decay=0.995), title - 1.0 + j * 0.085, 0.07 + 0.012 * j, pan=-0.2, rev=0.5)
    bus.add(I.strings([50, 57, 62, 69], 3.5, bright=0.45, attack=0.12, release=3.0), title, 0.5, rev=0.6, width=0.014)
    bus.add(I.pluck(50, bright=0.7, dur=2.5), title, 0.45, rev=0.5)
    bus.add(I.pluck(62, bright=0.8, dur=2.5), title + 0.01, 0.35, rev=0.5)
    # body: ney phrase -> rest (the narrator breathes) -> qanun ornament, cycling
    t = title + 3.6
    k = 0
    moves = F["moves"]
    while t < total - 8:
        ph = NEY_PHRASES[k % len(NEY_PHRASES)]
        L = sum(b for _, b in ph) * beat
        in_out = t >= F["outro0"]
        bus.add(I.ney(ph, beat), t, 0.30 if not in_out else 0.36, pan=0.1, rev=0.6)
        tq = t + L + beat
        for j, m in enumerate([62, 66, 69, 74] if k % 2 else [74, 69, 67, 66, 62]):
            bus.add(I.pluck(m, bright=0.8, dur=1.6, decay=0.996), tq + j * beat / 2, 0.15, pan=-0.25, rev=0.5)
        rest = (3 if k % 3 else 5) * bar
        if any(t < b <= t + L + rest for b in moves):    # new movement: a slightly longer breath
            rest += bar
        t += L + rest
        k += 1
    end = F["dur"] - 6.0
    if end < t1:
        bus.add(I.pluck(50, bright=0.6, dur=3.0), end, 0.35, rev=0.6)
        bus.add(I.pluck(62, bright=0.7, dur=3.0), end + 0.02, 0.30, rev=0.6)
        bus.add(I.pluck(69, bright=0.8, dur=3.0), end + 0.35, 0.22, rev=0.6)


STYLES = dict(doc=style_doc, mystery=style_mystery, oriental=style_oriental)
NAMES = dict(doc="وثائقي سينمائي — بيانو ووتريات", mystery="غموض وفضول — نبض خفيف وصندوق موسيقى",
             oriental="شرقي هادي — ناي وقانون بدون إيقاع")


def render(style, tl, t1=None):
    F = form(tl)
    t1 = F["dur"] + 3.0 if t1 is None else t1
    bus = Bus(t1 + 6.0)
    STYLES[style](bus, Inst(), F, t1)
    n = int(t1 * SR)
    irs = make_ir()
    chans = []
    for dry, ir in ((bus.L, irs[0]), (bus.R, irs[1])):
        x = dry[:n] + 0.9 * convolve(bus.send, ir)[:n]
        chans.append(hp(x, 45).astype(np.float32))          # tame lows under the voice
        del x
    del bus
    # soft fade in / out (only the ends are touched), peak normalise
    a = int(1.2 * SR)
    f0 = int((F["dur"] - 3.5) * SR)
    for c in chans:
        c[:a] *= np.linspace(0, 1, a, dtype=np.float32)
        if f0 < n:
            c[f0:] *= np.clip(1 - (np.arange(n - f0, dtype=np.float32) / SR) / 4.0, 0, 1)
    peak = max(np.abs(c).max() for c in chans) + 1e-6
    out = np.stack(chans, 1)
    del chans
    out *= 0.6 / peak
    return out
