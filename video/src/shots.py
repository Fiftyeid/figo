# -*- coding: utf-8 -*-
"""Shot types: map, image (Ken Burns), cards (chain / meaning / fact / list / myth / quote / ledger), title."""
import math, os, functools
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from common import *
from mapgen import render_view, frame_for, mapdata, CITIES, View

IMG_DIR = os.path.join(ASSETS, "images")


# ======================================================================= helpers
def appear(t, t0, dur=0.35):
    """(alpha, scale) for a pop-in that starts at t0."""
    if t0 is None:
        return 1.0, 1.0
    x = (t - t0)
    if x <= 0:
        return 0.0, 0.85
    a = ease_out_cubic(x / 0.25)
    s = 0.86 + 0.14 * ease_out_back(min(1.0, x / dur))
    return a, s


def fade_out(t, t1, dur=0.3):
    if t1 is None:
        return 1.0
    return 1.0 - ease_in_out((t - t1) / dur)


def icon_check(size=64, color=(52, 195, 143)):
    s = 4
    im = Image.new("RGBA", (size * s, size * s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse([0, 0, size * s - 1, size * s - 1], fill=color + (255,))
    w = int(size * s * 0.11)
    pts = [(size * s * 0.27, size * s * 0.52), (size * s * 0.44, size * s * 0.69), (size * s * 0.75, size * s * 0.34)]
    d.line(pts, fill=(255, 255, 255, 255), width=w, joint="curve")
    for p in (pts[0], pts[-1]):
        d.ellipse([p[0] - w / 2, p[1] - w / 2, p[0] + w / 2, p[1] + w / 2], fill=(255, 255, 255, 255))
    return im.resize((size, size), Image.LANCZOS)


def icon_cross(size=64, color=(235, 87, 87)):
    s = 4
    im = Image.new("RGBA", (size * s, size * s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse([0, 0, size * s - 1, size * s - 1], fill=color + (255,))
    w = int(size * s * 0.11)
    a, b = size * s * 0.32, size * s * 0.68
    d.line([(a, a), (b, b)], fill=(255, 255, 255, 255), width=w)
    d.line([(a, b), (b, a)], fill=(255, 255, 255, 255), width=w)
    return im.resize((size, size), Image.LANCZOS)


def pin_icon(size=34, color=CORAL):
    s = 4
    im = Image.new("RGBA", (size * s, size * s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse([s * 2, s * 2, size * s - s * 2, size * s - s * 2], fill=(255, 255, 255, 255))
    d.ellipse([s * 6, s * 6, size * s - s * 6, size * s - s * 6], fill=color + (255,))
    return im.resize((size, size), Image.LANCZOS)


def lower_third(title, sub=None, accent=GOLD):
    t1 = text_image(title, "black", 58, WHITE)
    t2 = text_image(sub, "semi", 36, MUTED) if sub else None
    w = max(t1.width, t2.width if t2 else 0) + 90
    h = t1.height + (t2.height - 6 if t2 else 0) + 34
    box = rounded_rect((w, h), 22, (10, 14, 30, 225))
    d = ImageDraw.Draw(box)
    d.rounded_rectangle([w - 14, 14, w - 4, h - 14], radius=5, fill=accent + (255,))
    box.alpha_composite(t1, (w - 40 - t1.width, 10))
    if t2:
        box.alpha_composite(t2, (w - 40 - t2.width, 10 + t1.height - 12))
    return box


@functools.lru_cache(maxsize=64)
def blurred_bg(key, darken=0.55, blur=18):
    """Background source (pre-scaled for drift) from an image key or 'map:CODE,CODE'."""
    Z = 1.08
    if key.startswith("map:"):
        codes = [c for c in key[4:].split(",") if c]
        if codes:
            cx, cy, sp = frame_for(codes)
        else:
            cx, cy, sp = 30.8, 26.9, 19.5
        r = render_view(cx, cy, sp, size=(int(W * Z), int(H * Z)), highlight=codes, ss=1)
        im = Image.blend(r["base"], r["hl"], 0.32).filter(ImageFilter.GaussianBlur(blur // 2))
        im = grade_image(im, darken=max(darken, 0.62), sat=0.85)
    elif key == "gradient":
        im = gradient_bg((int(W * Z), int(H * Z)))
        st = starfield((int(W * Z), int(H * Z)), n=260)
        im = im.convert("RGBA")
        im.alpha_composite(st)
        im = im.convert("RGB")
    else:
        im = ken_burns_source(os.path.join(IMG_DIR, key + ".jpg"), zoom_max=Z, darken=darken, blur=blur)
    return im


def drift(src, t, dur, zoom_in=True, pan=(0.0, 0.0)):
    """Ken-Burns view of a source pre-scaled by Z (zoom from 1/Z to 1 or reverse)."""
    Z = src.width / W
    p = ease_in_out(t / max(dur, 0.01)) if dur > 0 else 0
    z0, z1 = (1 / Z, 1.0) if zoom_in else (1.0, 1 / Z)
    zoom = lerp(z0, z1, p)
    vis_w, vis_h = W / zoom, H / zoom
    max_dx = (src.width - vis_w) / 2
    max_dy = (src.height - vis_h) / 2
    cx = src.width / 2 + pan[0] * max_dx * (2 * p - 1)
    cy = src.height / 2 + pan[1] * max_dy * (2 * p - 1)
    return view_transform(src, cx, cy, zoom)


# ======================================================================= overlays
def build_overlay(item):
    k = item["kind"]
    if k == "chip":
        return chip(item["text"], item.get("color", GOLD), item.get("font", "black"), item.get("size", 52),
                    fg=item.get("fg", INK))
    if k == "text":
        return text_image(item["text"], item.get("font", "black"), item.get("size", 60), item.get("color", WHITE),
                          stroke=item.get("stroke", 4), stroke_fill=item.get("stroke_fill", INK),
                          shadow=item.get("shadow", 6))
    if k == "lower":
        return lower_third(item["title"], item.get("sub"), item.get("accent", GOLD))
    if k == "para":
        return paragraph_image(item["text"], item.get("font", "bold"), item.get("size", 50), item.get("color", WHITE),
                               max_w=item.get("max_w", 1500), stroke=item.get("stroke", 3), shadow=4)
    raise ValueError(k)


class OverlayMixin:
    def prep_overlays(self):
        self._ov = [(it, build_overlay(it)) for it in getattr(self, "overlays", []) or []]

    def draw_overlays(self, base, t):
        for it, im in self._ov:
            t0 = it.get("t", self.start)
            if t < t0:
                continue
            a, s = appear(t, t0)
            a *= fade_out(t, it.get("t_out"))
            if a <= 0.01:
                continue
            x, y = it.get("x", W / 2), it.get("y", H - 140)
            if it["kind"] == "lower":
                # slide in from the right (RTL)
                off = (1 - ease_out_cubic((t - t0) / 0.45)) * 120
                paste_at(base, im, W - 70 - im.width + off, H - 70 - im.height, alpha=a)
            else:
                paste_center(base, im, x, y, alpha=a, scale=s)


# ======================================================================= shots
class Shot(OverlayMixin):
    kind = "base"

    def __init__(self, start, end, **kw):
        self.start, self.end = start, end
        self.__dict__.update(kw)
        self.prepared = False

    @property
    def dur(self):
        return self.end - self.start

    def prepare(self):
        self.prep_overlays()
        self.prepared = True

    def frame(self, t):
        raise NotImplementedError


class ImageShot(Shot):
    """Ken Burns over an illustration + timed overlays."""
    kind = "image"

    def prepare(self):
        self.src = ken_burns_source(os.path.join(IMG_DIR, self.image + ".jpg"),
                                    zoom_max=getattr(self, "zmax", 1.16), darken=getattr(self, "darken", 0.0))
        self.vig = vignette(strength=0.6)
        super().prepare()

    def frame(self, t):
        lt = t - self.start
        im = drift(self.src, lt, self.dur + 0.6, zoom_in=getattr(self, "zoom_in", True),
                   pan=getattr(self, "pan", (0.0, 0.0))).convert("RGBA")
        im.alpha_composite(self.vig)
        self.draw_overlays(im, t)
        return im


class MapShot(Shot):
    """Stylised map with highlight, title, pins, labels and routes."""
    kind = "map"
    Z = 1.07

    def prepare(self):
        codes = list(getattr(self, "codes", []) or [])
        codes2 = list(getattr(self, "codes2", []) or [])
        fr = getattr(self, "frame_", None)
        if fr is None:
            fc = codes + codes2 if (codes or codes2) else []
            fr = frame_for(fc, margin=getattr(self, "margin", 1.7),
                           min_span=getattr(self, "min_span", 2.4)) if fc else (30.8, 26.9, 19.5)
        self.cx_, self.cy_, self.span_ = fr
        size = (int(W * self.Z), int(H * self.Z))
        r = render_view(self.cx_, self.cy_, self.span_ / 1.0, size=size, highlight=codes, highlight2=codes2,
                        dim_others=getattr(self, "dim", False))
        self.base, self.hl, self.view = r["base"], r["hl"], r["view"]
        self.vig = vignette(strength=0.5)
        # title
        self.title_im = None
        if getattr(self, "title", None):
            t = text_image(self.title, "display", getattr(self, "title_size", 150), GOLD, stroke=6, stroke_fill=INK,
                           shadow=10)
            self.title_im = glow(t, radius=22, strength=0.8, color=(255, 170, 30))
        self.sub_im = None
        if getattr(self, "subtitle", None):
            self.sub_im = text_image(self.subtitle, "bold", 44, WHITE, stroke=4, stroke_fill=INK, shadow=4)
        self.pin_im = pin_icon(36)
        self.pins_ = []
        for p in getattr(self, "pins", []) or []:
            lon, lat = p.get("ll") or CITIES[p["name"]]
            lab = text_image(p.get("label", p["name"]), "black", p.get("size", 40), WHITE, stroke=5, stroke_fill=INK,
                             shadow=4)
            self.pins_.append((p, lon, lat, lab))
        self.labels_ = []
        for l in getattr(self, "labels", []) or []:
            lab = text_image(l["text"], l.get("font", "bold"), l.get("size", 40), l.get("color", (190, 220, 255)),
                             stroke=4, stroke_fill=INK, shadow=3)
            self.labels_.append((l, lab))
        self.gov_labels_ = []
        if getattr(self, "gov_labels", False):
            md = mapdata()
            for code, g in md.govs.items():
                if code in getattr(self, "skip_labels", ()):
                    continue
                lon, lat = md.label_point(code)
                lab = text_image(g["name_ar"], "bold", getattr(self, "gov_label_size", 26), WHITE, stroke=3,
                                 stroke_fill=INK)
                self.gov_labels_.append((code, lon, lat, lab))
        super().prepare()

    def out_xy(self, lon, lat, cx, cy, zoom):
        sx, sy = self.view(lon, lat)
        x0 = cx - (W / zoom) / 2
        y0 = cy - (H / zoom) / 2
        return (sx - x0) * zoom, (sy - y0) * zoom

    def frame(self, t):
        lt = t - self.start
        p = ease_in_out(lt / max(self.dur + 0.5, 0.1))
        zoom_in = getattr(self, "zoom_in", True)
        z0, z1 = (1 / self.Z, 1.0) if zoom_in else (1.0, 1 / self.Z)
        zoom = lerp(z0, z1, p)
        cx, cy = self.base.width / 2, self.base.height / 2
        # highlight fade-in (+ gentle pulse)
        hl_t = getattr(self, "hl_t", self.start + 0.15)
        a = ease_out_cubic((t - hl_t) / 0.6) if (getattr(self, "codes", None) or getattr(self, "codes2", None)) else 0
        if a > 0:
            a = a * (0.9 + 0.1 * math.sin(lt * 3.2))
            src = Image.blend(self.base, self.hl, a)
        else:
            src = self.base
        if getattr(self, "sweep", False):
            src = self._sweep(src, lt)
        im = view_transform(src, cx, cy, zoom).convert("RGBA")
        im.alpha_composite(self.vig)
        # routes
        for rt in getattr(self, "routes", []) or []:
            self._route(im, rt, t, cx, cy, zoom)
        # governorate labels
        if self.gov_labels_:
            t_lab = getattr(self, "gov_labels_t", self.start + 0.3)
            order = sorted(self.gov_labels_, key=lambda g: -g[2])  # north -> south
            for k, (code, lon, lat, lab) in enumerate(order):
                tt = t_lab + k * getattr(self, "gov_label_step", 0.06)
                al, sc = appear(t, tt)
                if al <= 0:
                    continue
                x, y = self.out_xy(lon, lat, cx, cy, zoom)
                paste_center(im, lab, x, y, alpha=al, scale=sc)
        # labels
        for l, lab in self.labels_:
            tt = l.get("t", self.start + 0.6)
            al, sc = appear(t, tt)
            if al <= 0:
                continue
            x, y = self.out_xy(l["ll"][0], l["ll"][1], cx, cy, zoom)
            paste_center(im, lab, x, y, alpha=al, scale=sc)
        # pins
        for pdef, lon, lat, lab in self.pins_:
            tt = pdef.get("t", self.start + 0.5)
            al, sc = appear(t, tt)
            if al <= 0:
                continue
            x, y = self.out_xy(lon, lat, cx, cy, zoom)
            # pulse ring
            ring_p = ((t - tt) % 1.6) / 1.6
            rr = 14 + ring_p * 34
            ov = Image.new("RGBA", (int(rr * 2 + 8), int(rr * 2 + 8)), (0, 0, 0, 0))
            ImageDraw.Draw(ov).ellipse([4, 4, 4 + rr * 2, 4 + rr * 2], outline=CORAL + (int(200 * (1 - ring_p) * al),),
                                       width=4)
            paste_center(im, ov, x, y)
            paste_center(im, self.pin_im, x, y, alpha=al, scale=sc)
            side = pdef.get("side", "up")
            dy = -lab.height / 2 - 22 if side == "up" else lab.height / 2 + 22
            dx = 0
            if side == "left":
                dx, dy = -lab.width / 2 - 26, 0
            elif side == "right":
                dx, dy = lab.width / 2 + 26, 0
            paste_center(im, lab, x + dx, y + dy, alpha=al, scale=sc)
        # title + subtitle
        if self.title_im is not None:
            tt = getattr(self, "title_t", self.start + 0.25)
            al, sc = appear(t, tt, 0.45)
            if al > 0:
                ty = getattr(self, "title_y", H - 215)
                tx = getattr(self, "title_x", W / 2)
                paste_center(im, self.title_im, tx, ty, alpha=al, scale=sc)
                if self.sub_im is not None:
                    al2, sc2 = appear(t, tt + 0.35)
                    paste_center(im, self.sub_im, tx, ty + self.title_im.height / 2 - 6, alpha=al2, scale=sc2)
        self.draw_overlays(im, t)
        return im

    def _sweep(self, src, lt):
        """Colourful reveal of all governorates, north -> south."""
        if not hasattr(self, "_colored"):
            md = mapdata()
            size = src.size
            col = self.base.copy()
            ss = 1
            d = ImageDraw.Draw(col)
            rng = np.random.default_rng(7)
            pal = [(255, 201, 60), (46, 196, 182), (255, 127, 80), (120, 160, 255), (186, 160, 255),
                   (52, 195, 143), (255, 160, 200)]
            for k, (code, g) in enumerate(sorted(md.govs.items())):
                c = pal[k % len(pal)]
                c = tuple(int(v * 0.85) for v in c)
                for ext, holes in self.view.poly_px(g["geom"], ss):
                    if len(ext) >= 3:
                        d.polygon(ext, fill=c, outline=(250, 250, 255))
            self._colored = Image.blend(self.base, col, 0.92)
            y = np.linspace(0, 1, size[1])[:, None]
            self._ygrid = np.repeat(y, size[0], axis=1)
        t0 = getattr(self, "sweep_t0", 0.2)
        dur = getattr(self, "sweep_dur", 2.2)
        p = clamp((lt - t0) / dur)
        if p <= 0:
            return src
        edge = p * 1.25 - 0.1
        m = np.clip((edge - self._ygrid) / 0.12, 0, 1)
        mask = Image.fromarray((m * 255).astype(np.uint8), "L")
        return Image.composite(self._colored, src, mask)

    def _route(self, im, rt, t, cx, cy, zoom):
        t0 = rt.get("t", self.start + 0.5)
        if t < t0:
            return
        prog = ease_in_out((t - t0) / rt.get("dur", 1.4))
        if "river" in rt and "pts" not in rt:
            md = mapdata()
            geo = [r["geom"] for r in md.rivers if r["name"] == rt["river"]][0]
            lines = list(getattr(geo, "geoms", [geo]))
            coords = []
            for ln in sorted(lines, key=lambda g: g.coords[0][1]):
                cs = list(ln.coords)
                if coords and cs and (cs[0][1] < coords[-1][1]):
                    cs = cs[::-1]
                coords += cs
            coords.sort(key=lambda c: c[1])   # south -> north
            rt["pts"] = coords[::max(1, len(coords) // 60)] + [coords[-1]]
        pts = [self.out_xy(lon, lat, cx, cy, zoom) for lon, lat in rt["pts"]]
        # cumulative length
        L = [0.0]
        for a, b in zip(pts, pts[1:]):
            L.append(L[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
        tot = L[-1] * prog
        cut = [pts[0]]
        for k in range(1, len(pts)):
            if L[k] <= tot:
                cut.append(pts[k])
            else:
                a, b = pts[k - 1], pts[k]
                f = (tot - L[k - 1]) / max(1e-6, L[k] - L[k - 1])
                cut.append((a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f))
                break
        s = 2
        ov = Image.new("RGBA", (W * s // 2, H * s // 2), (0, 0, 0, 0))  # half-res*2 = full-res canvas
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)
        col = rt.get("color", CORAL) + (255,)
        wdt = rt.get("width", 7)
        if rt.get("dashed"):
            # draw dashes along the polyline
            seg_len, gap = 22, 14
            acc = 0.0
            for a, b in zip(cut, cut[1:]):
                l = math.hypot(b[0] - a[0], b[1] - a[1])
                if l < 1e-6:
                    continue
                ux, uy = (b[0] - a[0]) / l, (b[1] - a[1]) / l
                pos = 0.0
                while pos < l:
                    phase = (acc + pos) % (seg_len + gap)
                    if phase < seg_len:
                        e = min(l, pos + (seg_len - phase))
                        d.line([(a[0] + ux * pos, a[1] + uy * pos), (a[0] + ux * e, a[1] + uy * e)], fill=col,
                               width=wdt)
                        pos = e
                    else:
                        pos += (seg_len + gap - phase)
                acc += l
        else:
            if len(cut) >= 2:
                d.line(cut, fill=col, width=wdt, joint="curve")
        if rt.get("arrow") and len(cut) >= 2 and prog > 0.05:
            (x1, y1), (x2, y2) = cut[-2], cut[-1]
            ang = math.atan2(y2 - y1, x2 - x1)
            hs = 26
            p1 = (x2 + math.cos(ang) * 6, y2 + math.sin(ang) * 6)
            p2 = (x2 - math.cos(ang - 0.5) * hs, y2 - math.sin(ang - 0.5) * hs)
            p3 = (x2 - math.cos(ang + 0.5) * hs, y2 - math.sin(ang + 0.5) * hs)
            d.polygon([p1, p2, p3], fill=col)
        ov = ov.filter(ImageFilter.SMOOTH)
        im.alpha_composite(ov)
        if rt.get("label") and prog > 0.6:
            if not hasattr(self, "_rlab"):
                self._rlab = {}
            key = rt["label"]
            if key not in self._rlab:
                self._rlab[key] = text_image(key, "black", 40, WHITE, stroke=5, stroke_fill=INK, shadow=4)
            lab = self._rlab[key]
            mx, my = pts[len(pts) // 2]
            al = ease_out_cubic((prog - 0.6) / 0.3)
            paste_center(im, lab, mx + rt.get("label_dx", 0), my + rt.get("label_dy", -50), alpha=al)


# ----------------------------------------------------------------------- cards
class CardShot(Shot):
    kind = "card"

    def prepare(self):
        self.bgsrc = blurred_bg(getattr(self, "bg", "gradient"))
        self.vig = vignette(strength=0.65)
        self.build()
        super().prepare()

    def background(self, t):
        im = drift(self.bgsrc, t - self.start, self.dur + 0.8, zoom_in=True).convert("RGBA")
        im.alpha_composite(self.vig)
        return im

    def build(self):
        pass

    def frame(self, t):
        im = self.background(t)
        self.draw(im, t)
        self.draw_overlays(im, t)
        return im

    def times(self, n, key="ts", first=None, step=0.9):
        ts = list(getattr(self, key, []) or [])
        base = first if first is not None else self.start + 0.35
        while len(ts) < n:
            ts.append((ts[-1] + step) if ts else base)
        ts = [x if x is not None else base + i * step for i, x in enumerate(ts)]
        # never leave the card empty: first element shows quickly, then keep order
        if ts:
            ts[0] = min(ts[0], self.start + 0.9)
            for i in range(1, len(ts)):
                ts[i] = max(ts[i], ts[i - 1] + 0.3)
        return ts


class ChainCard(CardShot):
    """Etymology chain:  word(era) <- word(era) <- ...  read right-to-left."""

    def build(self):
        self.items_ = []
        for it in self.items:
            word, era = it[0], it[1]
            note = it[2] if len(it) > 2 else None
            col = ERA.get(era, GOLD)
            wt = text_image(word, "display", getattr(self, "word_size", 128), WHITE, pad=6)
            bw, bh = wt.width + 70, wt.height + 40
            box = rounded_rect((bw, bh), 30, (13, 18, 38, 235), outline=col + (255,), width=5)
            box.alpha_composite(wt, ((bw - wt.width) // 2, (bh - wt.height) // 2))
            box = glow(box, radius=16, strength=0.6, color=col)
            lab = chip(era, col, "black", 40, fg=INK, padx=24, pady=4)
            nt = text_image(note, "black", 52, col, stroke=4, stroke_fill=INK) if note else None
            self.items_.append((box, lab, nt))
        self.arrow = arrow_left(96, 14, 30, WHITE)
        gapw = self.arrow.width + 34
        total = sum(b.width for b, _, _ in self.items_) + gapw * (len(self.items_) - 1)
        self.sc = min(1.0, (W - 160) / total)
        self.total = total
        self.head = None
        if getattr(self, "heading", None):
            self.head = text_image(self.heading, "black", 60, GOLD, stroke=4, stroke_fill=INK, shadow=6)
        self.foot = None
        if getattr(self, "footer", None):
            self.foot = paragraph_image(self.footer, "bold", 44, WHITE, max_w=1500, stroke=3)

    def draw(self, im, t):
        n = len(self.items_)
        ts = self.times(n)
        sc = self.sc
        gapw = (self.arrow.width + 34) * sc
        x = W / 2 + self.total * sc / 2      # start at right edge (RTL)
        cy = H / 2 + 10
        if self.head is not None:
            al, s = appear(t, self.start + 0.1)
            paste_center(im, self.head, W / 2, 165, alpha=al, scale=s)
        for k, (box, lab, nt) in enumerate(self.items_):
            bw = box.width * sc
            cx = x - bw / 2
            al, s = appear(t, ts[k], 0.45)
            if al > 0:
                paste_center(im, box, cx, cy, alpha=al, scale=s * sc)
                paste_center(im, lab, cx, cy - box.height * sc / 2 - 8, alpha=al, scale=s * min(1, sc * 1.1))
                if nt is not None:
                    paste_center(im, nt, cx, cy + box.height * sc / 2 + 28, alpha=al, scale=s * min(1, sc * 1.1))
            x -= bw
            if k < n - 1:
                al2, s2 = appear(t, ts[k + 1])
                if al2 > 0:
                    paste_center(im, self.arrow, x - gapw / 2, cy, alpha=al2, scale=sc)
                x -= gapw
        if self.foot is not None:
            al, s = appear(t, getattr(self, "foot_t", ts[-1] + 0.8))
            paste_center(im, self.foot, W / 2, H - 170, alpha=al, scale=s)


class MeaningCard(CardShot):
    """BIG WORD  =  meaning   (+ optional badge / note)."""

    def build(self):
        self.w_im = glow(text_image(self.word, "display", getattr(self, "word_size", 190), GOLD, stroke=6,
                                    stroke_fill=INK, shadow=10), 24, 0.7, (255, 170, 30))
        self.eq = text_image("=", "black", 110, WHITE, stroke=4, stroke_fill=INK)
        self.m_im = paragraph_image(self.meaning, "black", getattr(self, "meaning_size", 84), WHITE,
                                    max_w=1600, stroke=5, shadow=6)
        self.n_im = paragraph_image(self.note, "bold", 46, (200, 210, 235), max_w=1500, stroke=3) \
            if getattr(self, "note", None) else None
        self.b_im = chip(self.badge, getattr(self, "badge_color", TEAL), "black", 40) \
            if getattr(self, "badge", None) else None

    def draw(self, im, t):
        ts = self.times(3, step=0.8)
        has_b = self.b_im is not None
        cy0 = 330 if not has_b else 360
        if has_b:
            al, s = appear(t, self.start + 0.1)
            paste_center(im, self.b_im, W / 2, 150, alpha=al, scale=s)
        al, s = appear(t, ts[0], 0.5)
        paste_center(im, self.w_im, W / 2, cy0, alpha=al, scale=s)
        al, s = appear(t, ts[1])
        paste_center(im, self.eq, W / 2, cy0 + self.w_im.height / 2 + 30, alpha=al, scale=s)
        al, s = appear(t, ts[1] + 0.1, 0.45)
        my = cy0 + self.w_im.height / 2 + 70 + self.m_im.height / 2 + 40
        paste_center(im, self.m_im, W / 2, my, alpha=al, scale=s)
        if self.n_im is not None:
            al, s = appear(t, ts[2])
            paste_center(im, self.n_im, W / 2, min(H - 110, my + self.m_im.height / 2 + 90), alpha=al, scale=s)


class FactCard(CardShot):
    """Huge number / short fact + caption (optional count-up)."""

    def build(self):
        self.c_im = paragraph_image(self.caption, "black", getattr(self, "caption_size", 64), WHITE, max_w=1600,
                                    stroke=4, shadow=6) if getattr(self, "caption", None) else None
        self.top_im = chip(self.top, getattr(self, "top_color", TEAL), "black", 42) if getattr(self, "top", None) else None
        self._big_cache = {}

    def big(self, s):
        if s not in self._big_cache:
            self._big_cache[s] = glow(text_image(s, "display", getattr(self, "big_size", 260), GOLD, stroke=7,
                                                 stroke_fill=INK, shadow=12), 26, 0.75, (255, 170, 30))
        return self._big_cache[s]

    def draw(self, im, t):
        ts = self.times(2, step=0.9)
        if self.top_im is not None:
            al, s = appear(t, self.start + 0.1)
            paste_center(im, self.top_im, W / 2, 170, alpha=al, scale=s)
        txt = self.text
        if getattr(self, "count_to", None) is not None:
            p = ease_out_cubic((t - ts[0]) / 1.2)
            v = int(round(self.count_to * p))
            txt = self.fmt.format(to_ar_digits(v))
        al, s = appear(t, ts[0], 0.5)
        if al > 0:
            paste_center(im, self.big(txt), W / 2, 450, alpha=al, scale=s)
        if self.c_im is not None:
            al, s = appear(t, ts[1])
            paste_center(im, self.c_im, W / 2, 760, alpha=al, scale=s)


class ListCard(CardShot):
    """Heading + items that appear one by one (numbered)."""

    def build(self):
        self.h_im = text_image(self.heading, "black", 70, GOLD, stroke=5, stroke_fill=INK, shadow=6)
        self.rows = []
        cols = getattr(self, "colors", None) or [GOLD, TEAL, CORAL, (186, 160, 255), (52, 195, 143)]
        for k, it in enumerate(self.items):
            col = cols[k % len(cols)]
            num = chip(to_ar_digits(k + 1), col, "black", 46, padx=22, pady=2)
            txt = text_image(it, "black", getattr(self, "item_size", 62), WHITE, stroke=4, stroke_fill=INK, shadow=4)
            w = num.width + 26 + txt.width + 70
            h = max(num.height, txt.height) + 30
            row = rounded_rect((w, h), 26, (12, 16, 34, 215), outline=col + (200,), width=3)
            row.alpha_composite(num, (w - 30 - num.width, (h - num.height) // 2))
            row.alpha_composite(txt, (w - 30 - num.width - 26 - txt.width, (h - txt.height) // 2))
            self.rows.append(row)

    def draw(self, im, t):
        n = len(self.rows)
        ts = self.times(n, step=1.2)
        al, s = appear(t, self.start + 0.1)
        paste_center(im, self.h_im, W / 2, 190, alpha=al, scale=s)
        gap = 28
        tot = sum(r.height for r in self.rows) + gap * (n - 1)
        y = 300 + max(0, (H - 380 - tot) / 2)
        for k, r in enumerate(self.rows):
            al, s = appear(t, ts[k])
            off = (1 - ease_out_cubic((t - ts[k]) / 0.45)) * 90 if t >= ts[k] else 90
            if al > 0:
                paste_at(im, r, (W - r.width) / 2 + off, y, alpha=al)
            y += r.height + gap


class MythCard(CardShot):
    """Myth (✗) vs real origin (✓)."""

    def build(self):
        def panel(head, body, col, icon):
            hd = chip(head, col, "black", 42)
            bd = paragraph_image(body, "display", getattr(self, "body_size", 116), WHITE, max_w=700, stroke=5, shadow=6)
            w, h = 780, 560
            p = rounded_rect((w, h), 36, (12, 16, 34, 225), outline=col + (230,), width=5)
            p.alpha_composite(hd, ((w - hd.width) // 2, 40))
            p.alpha_composite(bd, ((w - bd.width) // 2, 40 + hd.height + (h - 40 - hd.height - bd.height) // 2 - 30))
            ic = icon(96)
            p.alpha_composite(ic, ((w - ic.width) // 2, h - ic.height - 30))
            return p
        self.left = panel(getattr(self, "fact_head", "الأصل الأقرب"), self.fact, (52, 195, 143), icon_check)
        self.right = panel(getattr(self, "myth_head", "الحكاية الشعبية"), self.myth, (235, 87, 87), icon_cross)

    def draw(self, im, t):
        ts = self.times(2, step=1.5)
        al, s = appear(t, ts[0], 0.45)
        paste_center(im, self.right, W / 2 + 430, H / 2 + 20, alpha=al, scale=s)
        al, s = appear(t, ts[1], 0.45)
        paste_center(im, self.left, W / 2 - 430, H / 2 + 20, alpha=al, scale=s)
        # strike the myth when the fact appears
        if t > ts[1] + 0.2:
            p = ease_out_cubic((t - ts[1] - 0.2) / 0.5)
            d = ImageDraw.Draw(im)
            x0, x1 = W / 2 + 430 + 300, W / 2 + 430 - 300
            y = H / 2 + 20
            d.line([(x0, y + 20), (lerp(x0, x1, p), y + 20 - 60 * p)], fill=(235, 87, 87, 255), width=12)


class QuoteCard(CardShot):
    def build(self):
        self.q_im = paragraph_image(self.quote, getattr(self, "qfont", "display"), getattr(self, "qsize", 110), WHITE,
                                    max_w=1600, stroke=5, shadow=8)
        self.a_im = text_image(self.attrib, "black", 50, GOLD, stroke=4, stroke_fill=INK) if getattr(self, "attrib", None) else None
        self.top_im = chip(self.top, getattr(self, "top_color", TEAL), "black", 42) if getattr(self, "top", None) else None

    def draw(self, im, t):
        ts = self.times(2, step=1.0)
        if self.top_im is not None:
            al, s = appear(t, self.start + 0.1)
            paste_center(im, self.top_im, W / 2, 170, alpha=al, scale=s)
        al, s = appear(t, ts[0], 0.5)
        paste_center(im, self.q_im, W / 2, H / 2 - 10, alpha=al, scale=s)
        if self.a_im is not None:
            al, s = appear(t, ts[1])
            paste_center(im, self.a_im, W / 2, H / 2 + self.q_im.height / 2 + 80, alpha=al, scale=s)


class LedgerCard(CardShot):
    """Old ledger page: old word gets struck through and rewritten."""

    def build(self):
        pw, ph = 1180, 720
        rng = np.random.default_rng(5)
        a = np.zeros((ph, pw, 3), np.float32)
        a[...] = np.array([233, 214, 170], np.float32)
        a += rng.normal(0, 6, (ph, pw, 1))
        yy = np.linspace(-1, 1, ph)[:, None]
        xx = np.linspace(-1, 1, pw)[None, :]
        a *= (1 - 0.18 * (xx ** 2 + yy ** 2))[..., None]
        paper = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "RGB").convert("RGBA")
        d = ImageDraw.Draw(paper)
        for y in range(150, ph - 40, 64):
            d.line([(60, y), (pw - 60, y)], fill=(150, 120, 80, 90), width=2)
        d.line([(pw - 140, 30), (pw - 140, ph - 30)], fill=(170, 60, 50, 110), width=3)
        hdr = text_image(self.header, "amiri", 54, (90, 60, 30), pad=6)
        paper.alpha_composite(hdr, (pw - 170 - hdr.width, 50))
        # faint fake lines of handwriting
        for k, y in enumerate(range(214, ph - 80, 64)):
            if k == 2:
                continue
            ln = "".join(rng.choice(list("ابتثجحخدذرزسشصضطظعغفقكلمنهوي ")) for _ in range(rng.integers(18, 32)))
            tl = text_image(ln, "amiri", 34, (110, 80, 50), pad=2)
            tl = with_alpha(tl, 0.35)
            paper.alpha_composite(tl, (max(80, pw - 180 - tl.width), y - tl.height + 6))
        self.paper = paper.rotate(-2.0, resample=Image.BICUBIC, expand=True)
        shadow = Image.new("RGBA", (self.paper.width + 80, self.paper.height + 80), (0, 0, 0, 0))
        shadow.alpha_composite(Image.new("RGBA", self.paper.size, (0, 0, 0, 170)), (40, 52))
        self.shadow = shadow.filter(ImageFilter.GaussianBlur(22))
        self.old_im = text_image(self.old, "amiri", 120, (60, 40, 20), pad=8)
        self.new_im = text_image(self.new, "amiri", 120, (190, 30, 30), pad=8)
        self.cap_im = text_image(self.caption, "black", 52, WHITE, stroke=4, stroke_fill=INK, shadow=6) if getattr(self, "caption", None) else None

    def draw(self, im, t):
        ts = self.times(3, step=1.3)
        al, s = appear(t, self.start + 0.05, 0.5)
        cx, cy = W / 2, H / 2 + 10
        paste_center(im, self.shadow, cx + 10, cy + 20, alpha=al * 0.9, scale=s)
        paste_center(im, self.paper, cx, cy, alpha=al, scale=s)
        if al < 0.99:
            return
        ox, oy = cx + 40, cy + 40
        al, s = appear(t, ts[0])
        paste_center(im, self.old_im, ox, oy, alpha=al, scale=s)
        if t > ts[1]:
            p = ease_out_cubic((t - ts[1]) / 0.45)
            d = ImageDraw.Draw(im)
            x0 = ox + self.old_im.width / 2 + 10
            x1 = ox - self.old_im.width / 2 - 10
            d.line([(x0, oy + 8), (lerp(x0, x1, p), oy + 8 - 14 * p)], fill=(200, 20, 20, 255), width=11)
        al, s = appear(t, ts[2], 0.45)
        paste_center(im, self.new_im, ox - 10, oy - 150, alpha=al, scale=s)
        if self.cap_im is not None:
            al, s = appear(t, ts[2] + 0.6)
            paste_center(im, self.cap_im, W / 2, H - 90, alpha=al, scale=s)


class TitleCard(CardShot):
    """Big title sting."""

    def build(self):
        self.t_im = glow(paragraph_image(self.text, "display", getattr(self, "size", 150), GOLD, max_w=1600,
                                         stroke=7, shadow=12), 30, 0.9, (255, 160, 20))
        self.s_im = text_image(self.sub, "black", 56, WHITE, stroke=4, stroke_fill=INK, shadow=6) if getattr(self, "sub", None) else None
        self.stars = starfield(n=500, seed=11)

    def background(self, t):
        im = super().background(t)
        lt = t - self.start
        im.alpha_composite(self.stars)
        return im

    def draw(self, im, t):
        lt = t - self.start
        al, s = appear(t, self.start + 0.1, 0.6)
        s = s * (1.0 + 0.03 * ease_in_out(lt / max(self.dur, 0.1)))
        paste_center(im, self.t_im, W / 2, H / 2 - 30, alpha=al, scale=s)
        if self.s_im is not None:
            al2, s2 = appear(t, self.start + 0.7)
            paste_center(im, self.s_im, W / 2, H / 2 + self.t_im.height / 2 + 30, alpha=al2, scale=s2)
        # light sweep
        if 0.3 < lt < 1.6:
            p = (lt - 0.3) / 1.3
            x = lerp(-300, W + 300, p)
            sweep = Image.new("RGBA", (260, H), (0, 0, 0, 0))
            arr = np.zeros((H, 260, 4), np.uint8)
            prof = np.exp(-((np.arange(260) - 130) / 60.0) ** 2)
            arr[..., :3] = 255
            arr[..., 3] = (prof * 60)[None, :].astype(np.uint8)
            sweep = Image.fromarray(arr, "RGBA").rotate(12, expand=False)
            paste_center(im, sweep, x, H / 2)


AR_DIG = str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")


def to_ar_digits(v):
    return str(v).translate(AR_DIG)


SHOT_TYPES = dict(map=MapShot, image=ImageShot, chain=ChainCard, meaning=MeaningCard, fact=FactCard,
                  list=ListCard, myth=MythCard, quote=QuoteCard, ledger=LedgerCard, title=TitleCard)
