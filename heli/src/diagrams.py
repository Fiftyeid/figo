# -*- coding: utf-8 -*-
"""Animated explainer diagrams (HUD / blueprint style)."""
import math, functools
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from common import *
from shots import Shot, SS, T, dashed, curved_arrow, grid_bg_cached, _chip, _stamp, _glowed, _panel

SOUND = 1225.0  # km/h, sea level


def title_bar(im, text, t, t0, sub=None, x=110, y=80):
    a = ease_out_cubic((t - t0) / 0.4)
    if a <= 0:
        return
    paste_at(im, T(text, "cx", 64, WHITE, tracking=3, shadow=3), x + (1 - a) * -30, y, a)
    d = ImageDraw.Draw(im)
    d.rectangle([x - 30, y + 14, x - 22, y + 74], fill=AMBER + (int(255 * a),))
    if sub:
        paste_at(im, T(sub, "cs", 36, MUTED, tracking=2), x + 2, y + 78, a)


# ------------------------------------------------------------------ colour map for local airspeed
_STOPS = [(-450, (200, 80, 255)), (-1, (120, 70, 170)), (0, (40, 50, 80)), (300, (40, 120, 255)),
          (600, (50, 210, 210)), (800, (110, 230, 90)), (1000, (255, 205, 40)), (1120, (255, 110, 40)),
          (1225, (255, 40, 40))]


def cmap(u):
    if u <= _STOPS[0][0]:
        return _STOPS[0][1]
    for (u0, c0), (u1, c1) in zip(_STOPS, _STOPS[1:]):
        if u <= u1:
            f = (u - u0) / max(1e-6, u1 - u0)
            return tuple(int(c0[i] + (c1[i] - c0[i]) * f) for i in range(3))
    return _STOPS[-1][1]


@functools.lru_cache(maxsize=1)
def legend_img():
    w, h = 560, 24
    im = Image.new("RGBA", (w + 40, h + 70), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for x in range(w):
        u = -300 + (1300 + 300) * x / w
        d.line([(20 + x, 30), (20 + x, 30 + h)], fill=cmap(u) + (255,))
    for u, lab in ((-300, "BACKWARD"), (0, "0"), (600, "600"), (1225, "MACH 1")):
        x = 20 + (u + 300) / 1600 * w
        d.line([(x, 26), (x, 58)], fill=WHITE + (200,), width=2)
        tl = text_image(lab, "mono", 20, WHITE)
        im.alpha_composite(tl, (int(clamp(x - tl.width / 2, 0, im.width - tl.width)), 58))
    im.alpha_composite(text_image("LOCAL AIRSPEED ON THE BLADE (KM/H)", "mono", 20, MUTED), (14, 0))
    return im


# ================================================================== rotor disc (top view)
class RotorShot(Shot):
    """Top view of a rotor in forward flight. Nose = up, rotor counter-clockwise -> advancing side on the right.
    v_ramp = (t0, t1, v0, v1) forward speed in km/h. mode 'coax' adds a counter-rotating lower rotor."""

    def __init__(self, start, end, v_ramp=None, vt=785.0, mode="single", t_hover=None, t_adv=None, t_ret=None,
                 t_rev=None, t_mach=None, slow=None, title=None, sub=None, rev_label="REVERSE FLOW", **kw):
        super().__init__(start, end, **kw)
        self.v_ramp = v_ramp or (start, start + 1, 0, 0)
        self.vt0, self.mode = vt, mode
        self.t_hover, self.t_adv, self.t_ret, self.t_rev, self.t_mach = t_hover, t_adv, t_ret, t_rev, t_mach
        self.slow, self.title, self.sub, self.rev_label = slow, title, sub, rev_label
        self.cx, self.cy, self.R = 960, 585, 340

    def prepare(self):
        bg = grid_bg_cached().copy()
        ss = SS(W, H, 2)
        cx, cy, R = self.cx, self.cy, self.R
        # fuselage (top view)
        body = [(cx + 62 * math.sin(a), cy - 40 + 190 * math.cos(a) * (1.0 if math.cos(a) > 0 else 0.8))
                for a in np.linspace(0, 2 * math.pi, 60)]
        ss.poly([(cx - 20, cy + 100), (cx + 20, cy + 100), (cx + 10, cy + 440), (cx - 10, cy + 440)],
                fill=(40, 50, 64, 255), outline=(120, 140, 160, 255), width=2)
        ss.poly([(cx - 70, cy + 400), (cx + 70, cy + 400), (cx + 70, cy + 420), (cx - 70, cy + 420)],
                fill=(40, 50, 64, 255), outline=(120, 140, 160, 255), width=2)
        ss.poly(body, fill=(48, 60, 76, 255), outline=(140, 160, 180, 255), width=2)
        ss.circle(cx, cy, R, outline=(255, 255, 255, 70), width=2, fill=(255, 255, 255, 10))
        for k in range(24):
            a = 2 * math.pi * k / 24
            r0 = R + 6
            r1 = R + (20 if k % 6 == 0 else 12)
            ss.line([(cx + r0 * math.cos(a), cy + r0 * math.sin(a)), (cx + r1 * math.cos(a), cy + r1 * math.sin(a))],
                    (255, 255, 255, 110), 2)
        bg.alpha_composite(ss.done())
        nose = text_image("NOSE / DIRECTION OF FLIGHT", "mono", 22, MUTED, tracking=2)
        bg.alpha_composite(nose, (cx - nose.width // 2, cy - R - 70))
        self.bg = bg

    def speed(self, t):
        t0, t1, v0, v1 = self.v_ramp
        return lerp(v0, v1, ease_in_out((t - t0) / max(0.01, t1 - t0)))

    def tip(self, t):
        if not self.slow:
            return self.vt0
        t0, t1, vt1 = self.slow
        return lerp(self.vt0, vt1, ease_in_out((t - t0) / max(0.01, t1 - t0)))

    def draw_rotor(self, ss, t, V, vt, sign, phase, dim=1.0, width=24):
        cx, cy, R = self.cx, self.cy, self.R
        om = 2 * math.pi * 0.42
        for b in range(4):
            psi = om * (t - self.start) + phase + b * math.pi / 2
            sp, cp = math.sin(psi), math.cos(psi)
            n = 16
            for k in range(n):
                r0 = 0.10 + 0.9 * k / n
                r1 = 0.10 + 0.9 * (k + 1) / n
                u = vt * (r0 + r1) / 2 + V * sp
                col = cmap(u)
                col = tuple(int(c * dim) for c in col)
                p0 = (cx + sign * R * r0 * sp, cy + R * r0 * cp)
                p1 = (cx + sign * R * r1 * sp, cy + R * r1 * cp)
                ss.line([p0, p1], col + (255,), width)
            # blade outline tip
            ss.circle(cx + sign * R * sp, cy + R * cp, width / 2 - 1, fill=cmap(vt + V * sp) + (255,))
        ss.circle(cx, cy, 20, fill=(200, 210, 220, 255), outline=(60, 70, 80, 255), width=3)

    def base(self, t):
        im = self.bg.copy()
        V = self.speed(t)
        vt = self.tip(t)
        cx, cy, R = self.cx, self.cy, self.R
        # relative wind streaks (air comes from the nose)
        if V > 5:
            ss0 = SS(W, H, 1)
            aw = int(clamp(V / 400) * 70)
            for k in range(22):
                x = 180 + k * 75
                off = ((t * V * 1.6) + k * 97) % 160
                y = -160 + off
                while y < H:
                    ss0.line([(x, y), (x, y + 60)], (180, 220, 255, aw), 2)
                    y += 160
            im.alpha_composite(ss0.done())
        ss = SS(W, H, 2)
        # reverse flow circles
        if self.t_rev is not None and t >= self.t_rev and V > 0:
            a = ease_out_cubic((t - self.t_rev) / 0.6)
            mu = V / vt
            rr = mu * R / 2 * a
            for sign in ((1,) if self.mode == "single" else (1, -1)):
                rcx = cx - sign * rr
                ss.circle(rcx, cy, rr, fill=(200, 80, 255, 70), outline=(220, 120, 255, 230), width=3)
        if self.mode == "coax":
            self.draw_rotor(ss, t, V, vt, -1, math.pi / 4, dim=0.62, width=20)
        self.draw_rotor(ss, t, V, vt, 1, 0.0)
        im.alpha_composite(ss.done())

        if self.title:
            title_bar(im, self.title, t, self.start + 0.1, self.sub)
        # hover label
        if self.t_hover is not None:
            a = ease_out_cubic((t - self.t_hover) / 0.4) * (1 - ease_in_out((t - (self.v_ramp[0] + 0.5)) / 0.4)
                                                            if self.v_ramp[0] > self.t_hover else 1)
            if a > 0:
                c = _chip("HOVER · BLADE TIPS ≈ 785 KM/H", CYAN, 40, INK)
                paste_center(im, c, cx, cy + R + 70, a)
        # forward speed readout
        if self.v_ramp[3] > 0 and t >= self.v_ramp[0] - 0.3:
            a = ease_out_cubic((t - self.v_ramp[0] + 0.3) / 0.4)
            paste_at(im, T("FORWARD SPEED", "mono", 26, MUTED, tracking=3), 1460, 120, a)
            paste_at(im, T(f"{V:,.0f} KM/H", "title", 64, WHITE), 1460, 150, a)
        # side panels
        if self.mode == "single":
            self.side_panel(im, t, self.t_adv, 1, "ADVANCING BLADE", vt + V, "+ FLIGHT SPEED", GREEN)
            self.side_panel(im, t, self.t_ret, -1, "RETREATING BLADE", vt - V, "− FLIGHT SPEED", CYAN)
        else:
            if self.t_adv is not None:
                for sgn in (1, -1):
                    a = ease_out_cubic((t - self.t_adv - (0.0 if sgn > 0 else 0.3)) / 0.4)
                    c = _chip("ADVANCING", GREEN, 44, INK)
                    x = cx + sgn * (R + 250)
                    paste_center(im, c, x, cy - 40, a)
                    lab = T("UPPER ROTOR" if sgn > 0 else "LOWER ROTOR", "mono", 26, MUTED, tracking=2)
                    paste_center(im, lab, x, cy + 20, a)
            if self.slow and t >= self.slow[0] - 0.2:
                a = ease_out_cubic((t - self.slow[0] + 0.2) / 0.4)
                paste_at(im, T("ROTOR TIP SPEED", "mono", 26, MUTED, tracking=3), 110, 215, a)
                mach = (vt + V) / SOUND
                col = GREEN if mach < 0.92 else RED
                paste_at(im, T(f"{vt:,.0f} KM/H  ·  ADVANCING TIP MACH {mach:.2f}", "cx", 46, col), 110, 248, a)
        if self.t_rev is not None and t >= self.t_rev + 0.3 and V > 0:
            a = ease_out_cubic((t - self.t_rev - 0.3) / 0.4)
            mu = V / vt
            lab = _chip(self.rev_label, (220, 120, 255), 36, INK)
            paste_center(im, lab, cx - mu * R / 2, cy - mu * R / 2 - 40, a)
        lg = legend_img()
        paste_at(im, lg, W - lg.width - 60, H - lg.height - 40, ease_out_cubic((t - self.start - 0.3) / 0.5))
        return im

    def side_panel(self, im, t, ta, side, head, u, sub, col):
        if ta is None:
            return
        a = ease_out_cubic((t - ta) / 0.4)
        if a <= 0:
            return
        w, h = 420, 230
        x = self.cx + side * (self.R + 90) - (0 if side > 0 else w)
        y = self.cy - 150
        panel = _panel(w, h)
        paste_at(im, panel, x + (1 - a) * 60 * side, y, a)
        paste_at(im, T(head, "cx", 44, col, tracking=2), x + 26, y + 22, a)
        paste_at(im, T("TIP SPEED", "mono", 24, MUTED, tracking=2), x + 28, y + 82, a)
        mach = u / SOUND
        c2 = RED if mach > 0.9 else WHITE
        paste_at(im, T(f"{u:,.0f} KM/H", "title", 60, c2), x + 26, y + 108, a)
        paste_at(im, T(f"MACH {mach:.2f}   {sub}", "mono", 24, MUTED), x + 28, y + 186, a)
        # arrow showing blade direction
        ss = SS(W, H, 2)
        ax = self.cx + side * (self.R * 0.75)
        y0, y1 = (self.cy + 120, self.cy - 120) if side > 0 else (self.cy - 120, self.cy + 120)
        ss.arrow((ax, y0), (ax, y1), col + (int(220 * a),), 8, 30)
        im.alpha_composite(ss.done())
        if self.t_mach is not None and side > 0 and t >= self.t_mach:
            b = ease_out_cubic((t - self.t_mach) / 0.3)
            st = _chip("EDGE OF THE SOUND BARRIER", RED, 34, WHITE)
            paste_center(im, st, x + w / 2, y + h + 50, a * b)


# ================================================================== airfoil: shock / stall
class AirfoilShot(Shot):
    def __init__(self, start, end, mode="stall", aoa=(4, 22), t_tilt=None, t_stall=None, t_labels=(), labels=(),
                 title=None, sub=None, **kw):
        super().__init__(start, end, **kw)
        self.mode, self.aoa, self.t_tilt, self.t_stall = mode, aoa, t_tilt, t_stall
        self.t_labels, self.labels, self.title, self.sub = list(t_labels), list(labels), title, sub
        self.c = 720.0
        self.xp, self.yp = 820.0, 600.0

    def alpha(self, t):
        if self.mode == "shock" or not self.t_tilt:
            return self.aoa[0]
        t0, t1 = self.t_tilt
        return lerp(self.aoa[0], self.aoa[1], ease_in_out((t - t0) / max(0.01, t1 - t0)))

    def stalled(self, t):
        return self.mode == "stall" and self.t_stall is not None and t >= self.t_stall

    def surface(self, al):
        c = self.c
        xs = np.linspace(0, 1, 90) ** 1.6
        yt = 5 * 0.15 * (0.2969 * np.sqrt(xs) - 0.1260 * xs - 0.3516 * xs ** 2 + 0.2843 * xs ** 3 - 0.1036 * xs ** 4)
        a = math.radians(al)
        out = []
        for sgn in (1, -1):
            u = (xs - 0.25) * c
            v = sgn * yt * c
            uu = u * math.cos(a) + v * math.sin(a)
            vv = -u * math.sin(a) + v * math.cos(a)
            out.append((uu, vv))
        return out

    def base(self, t):
        im = grid_bg_cached().copy()
        al = self.alpha(t)
        (uu_up, vv_up), (uu_lo, vv_lo) = self.surface(al)
        xp, yp, c = self.xp, self.yp, self.c
        x_le = min(uu_up.min(), uu_lo.min())
        x_te = max(uu_up.max(), uu_lo.max())
        o_up = np.argsort(uu_up)
        o_lo = np.argsort(uu_lo)

        def surf(x, upper=True):
            if upper:
                return np.interp(x, uu_up[o_up], vv_up[o_up])
            return np.interp(x, uu_lo[o_lo], vv_lo[o_lo])

        y_le = surf(x_le + 1, True)
        y_te = surf(x_te - 1, True)
        stalled = self.stalled(t)
        ss = SS(W, H, 2)
        xs = np.linspace(-820, 900, 120)
        spd = 900 if self.mode == "shock" else 260
        lines = [24, 60, 110, 170, 240, 320, 410] if True else []
        for sgn in (1, -1):
            for y0 in lines:
                w = math.exp(-y0 / 260)
                ys = []
                for x in xs:
                    if x < x_le:
                        base_ = y_le * math.exp(-((x_le - x) / 260) ** 2)
                    elif x > x_te:
                        base_ = y_te * math.exp(-((x - x_te) / 520) ** 2)
                    else:
                        base_ = float(surf(x, sgn > 0))
                    y = base_ * w + sgn * y0
                    if stalled and sgn > 0 and y0 < 330 and x > x_le:
                        sep = (y_le + y0 * 0.85 + 14) + (x - x_le) * math.tan(math.radians(al * 0.15)) * 0.2
                        k = math.exp(-max(0, x - x_te) / 900)
                        sep = sep * k + (y0) * (1 - k)
                        y = max(y, sep)
                    ys.append(y)
                pts = [(xp + x, yp - y) for x, y in zip(xs, ys)]
                ss.line(pts, (150, 200, 255, 70), 2)
                # moving particles
                ph = (t * spd / 1720 + y0 * 0.013 + (0.5 if sgn < 0 else 0)) % 1.0
                for k in range(6):
                    f = (ph + k / 6) % 1.0
                    i = int(f * (len(xs) - 3))
                    p0, p1 = pts[i], pts[i + 2]
                    ss.line([p0, p1], (220, 240, 255, 230), 4)
        # stall vortices
        if stalled:
            a = ease_out_cubic((t - self.t_stall) / 0.5)
            rng = np.random.default_rng(4)
            for k in range(9):
                ph = ((t - self.t_stall) * 0.45 + k / 9) % 1.0
                x = x_le + 120 + ph * (x_te - x_le + 380)
                yb = float(surf(min(x, x_te - 2), True)) if x < x_te else y_te
                r = 18 + 40 * ph + rng.uniform(0, 10)
                y = yb + r + 10 + 30 * ph
                rot = (t * 360 * 1.3 + k * 40) % 360
                ss.arc((xp + x - r, yp - y - r, xp + x + r, yp - y + r), rot, rot + 260, (255, 120, 90, int(220 * a)), 4)
                r2 = r * 0.5
                ss.arc((xp + x - r2, yp - y - r2, xp + x + r2, yp - y + r2), rot + 90, rot + 330, (255, 150, 110, int(180 * a)), 3)
        # shock wave
        if self.mode == "shock":
            xs_ = x_le + 0.62 * (x_te - x_le)
            ysurf = float(surf(xs_, True))
            fl = 0.75 + 0.25 * math.sin(t * 40)
            pts = [(xp + xs_ + 10 * math.sin(k * 0.5) * 0.3 - k * 1.2, yp - ysurf - k * 9) for k in range(28)]
            ss.line(pts, (255, 255, 255, int(255 * fl)), 6)
            ss.line([(xp + xs_ - 40, yp - ysurf - 4), (xp + xs_, yp - ysurf - 60)], (255, 255, 255, int(200 * fl)), 4)
            # thickened wake behind the shock
            wpts = [(xp + x, yp - float(surf(x, True)) - 10 - 8 * math.sin(x * 0.08 + t * 25) - (x - xs_) * 0.08)
                    for x in np.linspace(xs_, x_te, 30)]
            ss.line(wpts, (255, 140, 80, 200), 5)
        # airfoil body
        poly = [(xp + u, yp - v) for u, v in zip(uu_up, vv_up)] + \
               [(xp + u, yp - v) for u, v in list(zip(uu_lo, vv_lo))[::-1]]
        ss.poly(poly, fill=(205, 214, 226, 255), outline=(255, 255, 255, 255), width=3)
        # lift arrow
        if self.mode == "stall":
            cl = (al / 15.0) if not stalled else max(0.35, 1.0 - 0.65 * ease_out_cubic((t - self.t_stall) / 0.6))
            L = 60 + 220 * clamp(cl, 0, 1.2)
            ss.arrow((xp + 40, yp - 40), (xp + 40, yp - 40 - L), GREEN + (230,), 10, 34)
        im.alpha_composite(ss.done())
        if self.title:
            title_bar(im, self.title, t, self.start + 0.1, self.sub)
        if self.mode == "stall":
            ca = ease_out_cubic((t - self.start - 0.3) / 0.4)
            paste_at(im, T("ANGLE OF ATTACK", "mono", 26, MUTED, tracking=3), 110, 900, ca)
            col = RED if stalled else WHITE
            paste_at(im, T(f"{al:4.1f}°", "title", 80, col), 110, 930, ca)
            paste_at(im, T("LIFT", "cx", 44, GREEN), xp + 70, yp - 200, ca)
            if stalled:
                a = ease_out_cubic((t - self.t_stall) / 0.25)
                st = _stamp("STALL", RED, 120)
                paste_center(im, st, 1500, 300, a, 1 + 0.5 * (1 - a))
        for k, (tl, lab) in enumerate(zip(self.t_labels, self.labels)):
            a = ease_out_cubic((t - tl) / 0.3)
            if a <= 0:
                continue
            hot = lab.startswith("MORE")
            c_ = _chip(lab, RED if hot else AMBER, 44, WHITE if hot else INK)
            paste_at(im, c_, 1420, 700 + k * 90, a)
        return im


# ================================================================== the trap (operating corridor)
class TrapShot(Shot):
    """x = forward speed, y = rotor tip speed. Red: advancing tip ~Mach limit. Blue: retreating-blade stall."""

    def __init__(self, start, end, t_red=None, t_blue=None, t_a=None, t_b=None, t_c=None, t_typ=None,
                 t_lynx=None, t_wall=None, **kw):
        super().__init__(start, end, **kw)
        self.ts = dict(red=t_red, blue=t_blue, a=t_a, b=t_b, c=t_c, typ=t_typ, lynx=t_lynx, wall=t_wall)

    def X(self, v):
        return 300 + v * 1380 / 500

    def Y(self, u):
        return 930 - (u - 400) * 700 / 900

    def prepare(self):
        bg = grid_bg_cached().copy()
        ss = SS(W, H, 2)
        X, Y = self.X, self.Y
        ss.line([(X(0), Y(400)), (X(500), Y(400))], WHITE + (220,), 3)
        ss.line([(X(0), Y(400)), (X(0), Y(1300))], WHITE + (220,), 3)
        for v in range(0, 501, 100):
            ss.line([(X(v), Y(400)), (X(v), Y(400) + 14)], WHITE + (200,), 2)
        for u in range(400, 1301, 200):
            ss.line([(X(0) - 14, Y(u)), (X(0), Y(u))], WHITE + (200,), 2)
        bg.alpha_composite(ss.done())
        for v in range(0, 501, 100):
            tl = text_image(str(v), "mono", 26, MUTED)
            bg.alpha_composite(tl, (int(X(v) - tl.width / 2), int(Y(400) + 18)))
        for u in range(400, 1301, 200):
            tl = text_image(str(u), "mono", 26, MUTED)
            bg.alpha_composite(tl, (int(X(0) - 24 - tl.width), int(Y(u) - tl.height / 2)))
        xl = text_image("FORWARD SPEED (KM/H)", "cs", 34, WHITE, tracking=2)
        bg.alpha_composite(xl, (int(X(250) - xl.width / 2), int(Y(400) + 56)))
        yl = text_image("ROTOR TIP SPEED (KM/H)", "cs", 34, WHITE, tracking=2).rotate(90, expand=True)
        bg.alpha_composite(yl, (120, int(Y(850) - yl.height / 2)))
        self.bg = bg

    def red_u(self, v):
        return 1188 - v

    def blue_u(self, v):
        return 2 * v

    def base(self, t):
        im = self.bg.copy()
        X, Y, ts = self.X, self.Y, self.ts
        ss = SS(W, H, 2)
        title_bar(im, "THE TRAP", t, self.start + 0.1, "WHY SPINNING FASTER OR SLOWER DOESN'T HELP")
        if ts["red"] and t >= ts["red"]:
            p = ease_out_cubic((t - ts["red"]) / 0.8)
            vend = 500 * p
            ss.poly([(X(0), Y(1300)), (X(0), Y(1188)), (X(vend), Y(self.red_u(vend))), (X(vend), Y(1300))],
                    fill=RED + (40,))
            ss.line([(X(0), Y(1188)), (X(vend), Y(self.red_u(vend)))], RED + (255,), 6)
        if ts["blue"] and t >= ts["blue"]:
            p = ease_out_cubic((t - ts["blue"]) / 0.8)
            vend = 200 + 300 * p
            ss.poly([(X(200), Y(400)), (X(vend), Y(self.blue_u(vend))), (X(vend), Y(400))], fill=CYAN + (40,))
            ss.line([(X(200), Y(400)), (X(vend), Y(self.blue_u(vend)))], CYAN + (255,), 6)
        if ts["c"] and t >= ts["c"]:
            p = ease_out_cubic((t - ts["c"]) / 0.6)
            pts = [(X(0), Y(1188))]
            vs = np.linspace(0, 396, 30)
            pts += [(X(v), Y(self.red_u(v))) for v in vs]
            pts += [(X(v), Y(max(400, self.blue_u(v)))) for v in vs[::-1]]
            ss.poly(pts, fill=GREEN + (int(70 * p),))
        if ts["typ"] and t >= ts["typ"]:
            p = ease_out_cubic((t - ts["typ"]) / 0.5)
            dashed(ss, (X(300), Y(400)), (X(300), Y(400) - (Y(400) - Y(1300)) * p), WHITE + (200,), 3)
        if ts["wall"] and t >= ts["wall"]:
            p = ease_out_cubic((t - ts["wall"]) / 0.3)
            ss.rect((X(396) - 6, Y(1300), X(396) + 26, Y(400)), fill=RED + (int(150 * p),))
        # state dot
        dot = self.dot(t)
        if dot:
            v, u, col = dot
            ss.line([(X(0), Y(u)), (X(v), Y(u))], col + (160,), 3)
            ss.circle(X(v), Y(u), 16, fill=col + (255,), outline=WHITE + (255,), width=3)
        im.alpha_composite(ss.done())
        if ts["red"] and t >= ts["red"] + 0.4:
            a = ease_out_cubic((t - ts["red"] - 0.4) / 0.4)
            paste_at(im, T("ADVANCING TIP HITS THE SOUND BARRIER", "cb", 38, RED, shadow=3), X(150), Y(1250), a)
        if ts["blue"] and t >= ts["blue"] + 0.4:
            a = ease_out_cubic((t - ts["blue"] - 0.4) / 0.4)
            paste_at(im, T("RETREATING BLADE STALLS", "cb", 38, CYAN, shadow=3), X(330), Y(560), a)
        if ts["a"]:
            self.state_label(im, t, ts["a"], "SPIN FASTER", RED)
        if ts["b"]:
            self.state_label(im, t, ts["b"], "SPIN SLOWER", CYAN)
        if ts["typ"] and t >= ts["typ"]:
            a = ease_out_cubic((t - ts["typ"] - 0.3) / 0.4)
            lab = T("MOST HELICOPTERS ≈ 300", "cb", 34, WHITE, shadow=3)
            paste_at(im, lab, X(300) - lab.width - 14, Y(540), a)
        if ts["lynx"] and t >= ts["lynx"]:
            a = ease_out_cubic((t - ts["lynx"]) / 0.4)
            c = _chip("G-LYNX ≈ 400 (BERP BLADES)", AMBER, 36, INK)
            paste_at(im, c, X(396) + 40, Y(792) - 30, a)
        if ts["wall"] and t >= ts["wall"]:
            a = ease_out_cubic((t - ts["wall"]) / 0.25)
            st = _stamp("THE WALL", RED, 96)
            paste_center(im, st, X(450), Y(1100), a, 1 + 0.5 * (1 - a))
        return im

    def state_label(self, im, t, t0, text, col):
        a = ease_out_cubic((t - t0) / 0.3) * (1 - ease_in_out((t - t0 - 3.2) / 0.4))
        if a > 0:
            c = _chip(text, col, 40, WHITE if col == RED else INK)
            paste_at(im, c, 1380, 300, a)

    def dot(self, t):
        ts = self.ts
        if ts["c"] and t >= ts["c"]:
            p = ease_in_out((t - ts["c"] - 0.4) / 2.2)
            return (lerp(0, 396, p), 792, GREEN)
        if ts["b"] and t >= ts["b"]:
            p = ease_in_out((t - ts["b"] - 0.3) / 1.6)
            vmax = 600 / 2
            return (lerp(0, vmax, p), 600, CYAN)
        if ts["a"] and t >= ts["a"]:
            p = ease_in_out((t - ts["a"] - 0.3) / 1.6)
            vmax = 1188 - 980
            return (lerp(0, vmax, p), 980, RED)
        return None


# ================================================================== speed scale
class SpeedoShot(Shot):
    """Horizontal speed scale 0..vmax km/h with markers sliding to their value; optional wall band."""

    def __init__(self, start, end, markers, wall=None, vmax=600, title="TOP SPEED", sub=None, **kw):
        super().__init__(start, end, **kw)
        self.markers, self.wall, self.vmax, self.title, self.sub = markers, wall, vmax, title, sub
        self.x0, self.x1, self.y = 170, 1750, 640

    def X(self, v):
        return self.x0 + (self.x1 - self.x0) * v / self.vmax

    def prepare(self):
        bg = grid_bg_cached().copy()
        ss = SS(W, H, 2)
        ss.line([(self.x0, self.y), (self.x1, self.y)], WHITE + (230,), 4)
        for v in range(0, self.vmax + 1, 25):
            big = v % 100 == 0
            ss.line([(self.X(v), self.y), (self.X(v), self.y + (26 if big else 12))], WHITE + (200 if big else 120,), 3 if big else 2)
        bg.alpha_composite(ss.done())
        for v in range(0, self.vmax + 1, 100):
            tl = text_image(str(v), "mono", 30, MUTED)
            bg.alpha_composite(tl, (int(self.X(v) - tl.width / 2), self.y + 34))
        u = text_image("KM/H", "mono", 30, AMBER)
        bg.alpha_composite(u, (self.x1 + 20, self.y - 16))
        self.bg = bg

    def base(self, t):
        im = self.bg.copy()
        title_bar(im, self.title, t, self.start + 0.1, self.sub)
        if self.wall and t >= self.wall["t"]:
            a = ease_out_cubic((t - self.wall["t"]) / 0.4)
            v0, v1 = self.wall.get("v", (385, 415))
            pul = 0.75 + 0.25 * math.sin((t - self.wall["t"]) * 4)
            ss = SS(W, H, 1)
            ss.rect((self.X(v0), 250, self.X(v1), 900), fill=RED + (int(110 * a * pul),))
            for k in range(-20, 40):
                y = 250 + k * 24
                ss.line([(self.X(v0), y), (self.X(v1), y + (self.X(v1) - self.X(v0)))], RED + (int(90 * a),), 2)
            im.alpha_composite(ss.done().crop((0, 0, W, H)))
            # mask hatch outside the band (redraw edges)
            lab = _glowed(self.wall.get("label", "THE WALL"), "title", 84, RED)
            paste_center(im, lab, self.X((v0 + v1) / 2), 215, a)
        lane = {}
        for k, m in enumerate(self.markers):
            t0 = m["t"]
            if t < t0:
                continue
            p = ease_out_cubic((t - t0) / m.get("dur", 1.0))
            v = m["v"] * p
            col = tuple(m.get("color", AMBER))
            level = m.get("level", k % 3)
            up = m.get("up", True)
            ss = SS(W, H, 2)
            yb = self.y - 8 + (k % 4) * 0  # same line
            ss.line([(self.x0, yb), (self.X(v), yb)], col + (200,), 10)
            ss.circle(self.X(v), self.y, 14, fill=col + (255,), outline=WHITE + (255,), width=3)
            ly = (self.y - 120 - level * 110) if up else (self.y + 110 + level * 110)
            if p > 0.6:
                a = ease_out_cubic((p - 0.6) / 0.4)
                ss.line([(self.X(v), self.y), (self.X(v), ly)], col + (int(200 * a),), 2)
            im.alpha_composite(ss.done())
            if p > 0.6:
                a = ease_out_cubic((t - t0 - 0.6 * m.get("dur", 1.0)) / 0.3)
                name = T(m["label"], "cx", 40, WHITE)
                val = T(m.get("vtext", f"{m['v']:g}"), "title", 46, col)
                bw = max(name.width, val.width) + 30
                bh = name.height + val.height - 6
                x = self.X(m["v"]) - (bw if m.get("left", False) else 0) + (-10 if m.get("left") else 10)
                y = ly - bh / 2
                paste_at(im, rounded_rect((bw, bh), 8, (8, 12, 18, 215), outline=col + (255,), width=2), x, y, a)
                paste_at(im, name, x + 14, y - 2, a)
                paste_at(im, val, x + 14, y + name.height - 14, a)
                if m.get("note"):
                    paste_at(im, T(m["note"], "mono", 22, MUTED), x + 14, y + bh + 4, a)
        return im


# ================================================================== records chart (speed vs year)
class RecordsShot(Shot):
    KIND = dict(official=(AMBER, "OFFICIAL RECORD"), unofficial=(CYAN, "UNOFFICIAL"), tilt=((220, 120, 255), "TILTROTOR"),
                proto=(GREEN, "PROTOTYPE"))

    def __init__(self, start, end, items, t_line=None, vlim=(300, 600), years=(1960, 2030), title="THE SPEED RACE",
                 sub=None, wall=None, **kw):
        super().__init__(start, end, **kw)
        self.items, self.t_line, self.vlim, self.years, self.title, self.sub, self.wall = items, t_line, vlim, years, title, sub, wall

    def X(self, yr):
        return 230 + (yr - self.years[0]) / (self.years[1] - self.years[0]) * 1460

    def Y(self, v):
        return 900 - (v - self.vlim[0]) / (self.vlim[1] - self.vlim[0]) * 640

    def prepare(self):
        bg = grid_bg_cached().copy()
        ss = SS(W, H, 2)
        ss.line([(self.X(self.years[0]), self.Y(self.vlim[0])), (self.X(self.years[1]), self.Y(self.vlim[0]))], WHITE + (220,), 3)
        for yr in range(self.years[0], self.years[1] + 1, 10):
            ss.line([(self.X(yr), self.Y(self.vlim[0])), (self.X(yr), self.Y(self.vlim[0]) + 14)], WHITE + (200,), 2)
            dashed(ss, (self.X(yr), self.Y(self.vlim[0])), (self.X(yr), self.Y(self.vlim[1])), (255, 255, 255, 30), 1)
        for v in range(self.vlim[0], self.vlim[1] + 1, 50):
            dashed(ss, (self.X(self.years[0]), self.Y(v)), (self.X(self.years[1]), self.Y(v)), (255, 255, 255, 30), 1)
        bg.alpha_composite(ss.done())
        for yr in range(self.years[0], self.years[1] + 1, 10):
            tl = text_image(str(yr), "mono", 28, MUTED)
            bg.alpha_composite(tl, (int(self.X(yr) - tl.width / 2), int(self.Y(self.vlim[0]) + 20)))
        for v in range(self.vlim[0], self.vlim[1] + 1, 100):
            tl = text_image(str(v), "mono", 26, MUTED)
            bg.alpha_composite(tl, (int(self.X(self.years[0]) - 20 - tl.width), int(self.Y(v) - tl.height / 2)))
        u = text_image("KM/H", "mono", 26, AMBER)
        bg.alpha_composite(u, (int(self.X(self.years[0]) - 20 - u.width), int(self.Y(self.vlim[1]) - 50)))
        self.bg = bg

    def base(self, t):
        im = self.bg.copy()
        title_bar(im, self.title, t, self.start + 0.1, self.sub)
        ss = SS(W, H, 2)
        if self.wall and t >= self.wall["t"]:
            a = ease_out_cubic((t - self.wall["t"]) / 0.4)
            ss.rect((self.X(self.years[0]), self.Y(410), self.X(self.years[1]), self.Y(385)), fill=RED + (int(70 * a),))
        if self.t_line and t >= self.t_line:
            p = ease_out_cubic((t - self.t_line) / 1.0)
            x0 = self.X(1986)
            ss.line([(x0, self.Y(400.87)), (x0 + (self.X(self.years[1]) - x0) * p, self.Y(400.87))], AMBER + (220,), 4)
        im.alpha_composite(ss.done())
        if self.wall and t >= self.wall["t"]:
            a = ease_out_cubic((t - self.wall["t"]) / 0.4)
            paste_at(im, T("THE WALL", "cx", 34, RED), self.X(self.years[0]) + 10, self.Y(385) + 4, a)
        if self.t_line and t >= self.t_line + 0.6:
            a = ease_out_cubic((t - self.t_line - 0.6) / 0.4)
            paste_at(im, T("OFFICIAL RECORD SINCE 1986: 400.87", "cb", 32, AMBER), self.X(1992), self.Y(400.87) + 6, a)
        for it in self.items:
            t0 = it["t"]
            if t < t0:
                continue
            a = ease_out_cubic((t - t0) / 0.4)
            col = self.KIND[it.get("kind", "official")][0]
            x, y = self.X(it["year"]), self.Y(it["v"])
            ss = SS(W, H, 2)
            y_ = self.Y(self.vlim[0]) + (y - self.Y(self.vlim[0])) * ease_out_cubic((t - t0) / 0.5)
            ss.line([(x, self.Y(self.vlim[0])), (x, y_)], col + (int(150 * a),), 3)
            if it.get("kind") == "unofficial":
                ss.circle(x, y_, 15, fill=(8, 12, 18, 255), outline=col + (255,), width=4)
            elif it.get("kind") == "tilt":
                ss.poly([(x, y_ - 18), (x + 18, y_), (x, y_ + 18), (x - 18, y_)], fill=col + (255,))
            else:
                ss.circle(x, y_, 15, fill=col + (255,), outline=WHITE + (255,), width=3)
            im.alpha_composite(ss.done())
            if t >= t0 + 0.35:
                b = ease_out_cubic((t - t0 - 0.35) / 0.35)
                name = T(it["label"], "cx", 38, WHITE, shadow=3)
                val = T(it.get("vtext", f"{it['v']:g}") + ("  " + it["note"] if it.get("note") else ""), "cb", 32, col, shadow=3)
                left = it.get("left", False)
                dy = it.get("dy", -70)
                xx = x - name.width - 20 if left else x + 20
                paste_at(im, name, xx, y + dy, b)
                paste_at(im, val, xx + (name.width - val.width if left else 0), y + dy + 42, b)
        # legend
        lx = 1180
        kinds = []
        for it in self.items:
            k = it.get("kind", "official")
            if k not in kinds and t >= it["t"]:
                kinds.append(k)
        for i, k in enumerate(kinds):
            col, lab = self.KIND[k]
            paste_at(im, _chip(lab, col, 28, INK), lx + i * 250, 110, 1.0)
        return im


# ================================================================== compound: the rotor's three jobs
def heli_side(ss, cx, cy, s=1.0, col=CYAN, fill=(70, 200, 255, 28), wings=0.0, prop=0.0, t=0.0):
    """Blueprint side view, nose to the right."""
    P = lambda pts: [(cx + x * s, cy + y * s) for x, y in pts]
    body = [(260, 10), (300, -20), (290, -60), (230, -100), (120, -118), (-40, -118), (-140, -100), (-200, -60),
            (-210, -10), (-170, 40), (-60, 62), (150, 62), (230, 45)]
    boom = [(-190, -70), (-560, -48), (-560, -22), (-190, 0)]
    fin = [(-520, -40), (-600, -170), (-560, -170), (-490, -36)]
    ss.poly(P(boom), fill=fill, outline=col + (255,), width=3)
    ss.poly(P(fin), fill=fill, outline=col + (255,), width=3)
    ss.poly(P(body), fill=fill, outline=col + (255,), width=3)
    ss.poly(P([(170, -96), (250, -60), (275, -20), (190, -20), (150, -96)]), fill=(70, 200, 255, 60),
            outline=col + (200,), width=2)
    ss.line(P([(-150, 112), (190, 112)]), col + (255,), 4)
    ss.line(P([(-90, 62), (-110, 112)]), col + (255,), 3)
    ss.line(P([(110, 62), (130, 112)]), col + (255,), 3)
    ss.rect((cx - 14 * s, cy - 150 * s, cx + 14 * s, cy - 118 * s), fill=col + (200,))
    ss.line(P([(-470, -158), (470, -158)]), col + (255,), 5)
    ss.ellipse((cx - 470 * s, cy - 172 * s, cx + 470 * s, cy - 144 * s), outline=col + (90,), width=2)
    if prop <= 0:
        ss.circle(cx - 545 * s, cy - 60 * s, 54 * s, outline=col + (160,), width=2)
    if wings > 0:
        a = int(255 * wings)
        ss.poly(P([(-80, 0), (110, -6), (150, 4), (120, 14), (-80, 16)]), fill=(255, 176, 32, int(120 * wings)),
                outline=AMBER + (a,), width=3)
    if prop > 0:
        a = int(255 * prop)
        ph = math.sin(t * 30)
        ss.rect((cx - 620 * s, cy - 44 * s, cx - 600 * s, cy - 24 * s), fill=AMBER + (a,))
        ss.ellipse((cx - 628 * s, cy - (34 + 120 * prop) * s, cx - 592 * s, cy + (-34 + 120 * prop) * s),
                   outline=AMBER + (a,), width=3, fill=(255, 176, 32, int(50 * prop)))


class JobsShot(Shot):
    def __init__(self, start, end, t_lift=None, t_thrust=None, t_steer=None, t_wing=None, t_prop=None,
                 t_relax=None, **kw):
        super().__init__(start, end, **kw)
        self.ts = dict(lift=t_lift, thrust=t_thrust, steer=t_steer, wing=t_wing, prop=t_prop, relax=t_relax)

    def base(self, t):
        im = grid_bg_cached().copy()
        ts = self.ts
        cx, cy = 1010, 640
        wings = ease_out_cubic((t - ts["wing"]) / 0.6) if ts["wing"] else 0.0
        prop = ease_out_cubic((t - ts["prop"]) / 0.6) if ts["prop"] else 0.0
        ss = SS(W, H, 2)
        heli_side(ss, cx, cy, 1.0, wings=wings, prop=prop, t=t)
        hub = (cx, cy - 175)
        if ts["lift"] and t >= ts["lift"]:
            a = ease_out_cubic((t - ts["lift"]) / 0.4)
            L = (240 - 110 * wings) * a
            ss.arrow(hub, (hub[0], hub[1] - L), CYAN + (255,), 12, 38)
        if ts["thrust"] and t >= ts["thrust"]:
            a = ease_out_cubic((t - ts["thrust"]) / 0.4)
            L = 260 * a * (1 - 0.85 * prop)
            if L > 30:
                ss.arrow((hub[0] + 30, hub[1] - 20), (hub[0] + 30 + L, hub[1] - 20), AMBER + (255,), 12, 38)
        if ts["steer"] and t >= ts["steer"]:
            a = ease_out_cubic((t - ts["steer"]) / 0.4)
            curved_arrow(ss, hub[0], hub[1] - 10, 120, 200, 200 + 120 * a, GREEN + (255,), 8, 30)
        if wings > 0:
            ss.arrow((cx + 30, cy - 10), (cx + 30, cy - 10 - 150 * wings), CYAN + (255,), 10, 34)
        if prop > 0:
            ss.arrow((cx - 620, cy - 34), (cx - 620 + 240 * prop, cy - 34), AMBER + (255,), 12, 38)
        im.alpha_composite(ss.done())
        if wings > 0.5 or prop > 0.5:
            title_bar(im, "COMPOUND HELICOPTER", t, (ts["wing"] or ts["prop"]), "WINGS LIFT · PROPELLER PUSHES · ROTOR RELAXES")
        else:
            title_bar(im, "A ROTOR HAS THREE JOBS", t, self.start + 0.1, "LIFT · THRUST · CONTROL")
        for key, lab, col, pos in (("lift", "LIFT", CYAN, (hub[0] + 30, hub[1] - 250)),
                                   ("thrust", "THRUST", AMBER, (hub[0] + 300, hub[1] - 80)),
                                   ("steer", "CONTROL", GREEN, (hub[0] - 330, hub[1] - 130))):
            if ts[key] and t >= ts[key]:
                a = ease_out_cubic((t - ts[key] - 0.2) / 0.3)
                if key == "thrust":
                    a *= 1 - prop * 0.85
                paste_at(im, T(lab, "cx", 52, col, shadow=3), pos[0], pos[1], a)
        if wings > 0:
            paste_at(im, T("WINGS: EXTRA LIFT", "cx", 44, AMBER, shadow=3), cx + 90, cy + 20, wings)
        if prop > 0:
            paste_at(im, T("PROPELLER: PUSH", "cx", 44, AMBER, shadow=3), cx - 660, cy + 85, prop)
        if ts["relax"] and t >= ts["relax"]:
            a = ease_out_cubic((t - ts["relax"]) / 0.4)
            c = _chip("THE ROTOR CAN RELAX", GREEN, 44, INK)
            paste_center(im, c, W / 2, 1000, a)
        return im


# ================================================================== tandem vs tail rotor (top view)
class TandemShot(Shot):
    def __init__(self, start, end, t_left=None, t_tail=None, t_right=None, t_cancel=None, t_power=None, **kw):
        super().__init__(start, end, **kw)
        self.ts = dict(left=t_left, tail=t_tail, right=t_right, cancel=t_cancel, power=t_power)

    def disc(self, ss, cx, cy, r, t, direction=1, col=CYAN, a=1.0):
        ss.circle(cx, cy, r, fill=col + (int(26 * a),), outline=col + (int(200 * a),), width=3)
        ang = direction * (t - self.start) * 160
        for b in range(3):
            th = math.radians(ang + b * 120)
            ss.line([(cx, cy), (cx + r * math.cos(th), cy + r * math.sin(th))], WHITE + (int(220 * a),), 8)
        curved_arrow(ss, cx, cy, r + 26, -150 if direction > 0 else -30, -60 if direction > 0 else -120,
                     col + (int(255 * a),), 6, 24)

    def base(self, t):
        im = grid_bg_cached().copy()
        ts = self.ts
        ss = SS(W, H, 2)
        d = ImageDraw.Draw(im)
        title_bar(im, "WHY THE CHINOOK HAS NO TAIL ROTOR", t, self.start + 0.1)
        if ts["left"] and t >= ts["left"]:
            a = ease_out_cubic((t - ts["left"]) / 0.4)
            cx, cy = 560, 520
            ss.poly([(cx - 40, cy - 140), (cx + 40, cy - 140), (cx + 46, cy + 80), (cx + 12, cy + 380), (cx - 12, cy + 380),
                     (cx - 46, cy + 80)], fill=(48, 60, 76, int(255 * a)), outline=(140, 160, 180, int(255 * a)), width=2)
            self.disc(ss, cx, cy, 230, t, -1, CYAN, a)
            # torque reaction on the body
            curved_arrow(ss, cx, cy + 10, 90, 30, 150, RED + (int(255 * a),), 7, 26)
            if ts["tail"] and t >= ts["tail"]:
                b = ease_out_cubic((t - ts["tail"]) / 0.4)
                ss.rect((cx + 8, cy + 330, cx + 22, cy + 420), fill=AMBER + (int(255 * b),))
                ss.arrow((cx + 30, cy + 375), (cx + 30 + 130 * b, cy + 375), AMBER + (int(255 * b),), 8, 28)
        if ts["right"] and t >= ts["right"]:
            a = ease_out_cubic((t - ts["right"]) / 0.4)
            cx = 1390
            ss.poly([(cx - 44, 300), (cx + 44, 300), (cx + 44, 780), (cx - 44, 780)], fill=(48, 60, 76, int(255 * a)),
                    outline=(140, 160, 180, int(255 * a)), width=2)
            self.disc(ss, cx, 390, 175, t, -1, CYAN, a)
            self.disc(ss, cx, 710, 175, t, 1, GREEN, a)
            if ts["cancel"] and t >= ts["cancel"]:
                b = ease_out_cubic((t - ts["cancel"]) / 0.4)
                curved_arrow(ss, cx - 300, 530, 70, -60, 60, RED + (int(255 * b),), 7, 24)
                curved_arrow(ss, cx + 300, 530, 70, 240, 120, RED + (int(255 * b),), 7, 24)
        im.alpha_composite(ss.done())
        if ts["left"] and t >= ts["left"]:
            a = ease_out_cubic((t - ts["left"]) / 0.4)
            paste_center(im, T("SINGLE MAIN ROTOR", "cx", 46, WHITE, tracking=2), 560, 230, a)
            paste_at(im, T("TORQUE", "cb", 36, RED, shadow=3), 560 + 100, 520 + 60, a)
        if ts["tail"] and t >= ts["tail"]:
            b = ease_out_cubic((t - ts["tail"]) / 0.4)
            paste_at(im, T("TAIL ROTOR", "cx", 40, AMBER, shadow=3), 560 + 160, 520 + 290, b)
            paste_at(im, T("power spent just to stop the spin", "bodym", 28, MUTED), 560 + 160, 520 + 340, b)
        if ts["right"] and t >= ts["right"]:
            a = ease_out_cubic((t - ts["right"]) / 0.4)
            paste_center(im, T("CHINOOK: TANDEM ROTORS", "cx", 46, WHITE, tracking=2), 1390, 140 + 30, a)
        if ts["cancel"] and t >= ts["cancel"]:
            b = ease_out_cubic((t - ts["cancel"]) / 0.4)
            c = _chip("OPPOSITE SPIN = TORQUE CANCELS", RED, 36, WHITE)
            paste_center(im, c, 1390, 960, b)
        if ts["power"] and t >= ts["power"]:
            b = ease_out_cubic((t - ts["power"]) / 0.4)
            c = _chip("ALL THE POWER GOES INTO LIFT + SPEED", GREEN, 40, INK)
            paste_center(im, c, 1390, 1030, b)
        return im


# ================================================================== BERP blade tip
class BerpShot(Shot):
    def __init__(self, start, end, t_conv=None, t_berp=None, t_paddle=None, t_swept=None, t_mod=None, **kw):
        super().__init__(start, end, **kw)
        self.ts = dict(conv=t_conv, berp=t_berp, paddle=t_paddle, swept=t_swept, mod=t_mod)

    def base(self, t):
        im = grid_bg_cached().copy()
        ts = self.ts
        title_bar(im, "BERP ROTOR BLADE", t, self.start + 0.1, "BRITISH EXPERIMENTAL ROTOR PROGRAMME")
        ss = SS(W, H, 2)
        x0, x1 = 160, 1700
        if ts["conv"] and t >= ts["conv"]:
            a = ease_out_cubic((t - ts["conv"]) / 0.5)
            y = 360
            xe = x0 + (x1 - 80 - x0) * a
            ss.rect((x0, y - 44, xe, y + 44), fill=(160, 175, 195, 255), outline=WHITE + (255,), width=3, radius=8)
        if ts["berp"] and t >= ts["berp"]:
            a = ease_out_cubic((t - ts["berp"]) / 0.6)
            y = 700
            pts = [(x0, y - 44), (1360, y - 44), (1380, y - 64), (1560, y - 64), (1700, y + 44), (x0, y + 44)]
            # reveal from the root
            xe = x0 + (1720 - x0) * a
            clipped = [(min(px, xe), py) for px, py in pts]
            ss.poly(clipped, fill=(255, 196, 80, 255), outline=WHITE + (255,), width=3)
        im.alpha_composite(ss.done())
        if ts["conv"] and t >= ts["conv"]:
            a = ease_out_cubic((t - ts["conv"] - 0.3) / 0.4)
            paste_at(im, T("CONVENTIONAL TIP", "cx", 44, WHITE, shadow=3), x0, 250, a)
        if ts["berp"] and t >= ts["berp"]:
            a = ease_out_cubic((t - ts["berp"] - 0.3) / 0.4)
            paste_at(im, T("BERP TIP", "cx", 44, AMBER, shadow=3), x0, 590, a)
        from shots import ov_callout
        if ts["paddle"]:
            ov_callout(im, dict(t=ts["paddle"], p=(1480, 660), l=(1480, 500), text="PADDLE-SHAPED TIP"), t, self.end)
            ov_callout(im, dict(t=ts["paddle"] + 0.3, p=(1370, 648), l=(960, 500), text="NOTCH", color=CYAN), t, self.end)
        if ts["swept"]:
            ov_callout(im, dict(t=ts["swept"], p=(1650, 705), l=(1560, 870), text="SWEPT BACK, LIKE A JET WING"), t, self.end)
        if ts["mod"] and t >= ts["mod"]:
            a = ease_out_cubic((t - ts["mod"]) / 0.3)
            paste_center(im, _chip("WESTLAND + UK MINISTRY OF DEFENCE", AMBER, 40, INK), W / 2, 1000, a)
        return im


# ================================================================== record course (stylised map)
class CourseShot(Shot):
    def __init__(self, start, end, t_line=None, t_run1=None, t_run2=None, t_wind=None, t_avg=None, **kw):
        super().__init__(start, end, **kw)
        self.ts = dict(line=t_line, run1=t_run1, run2=t_run2, wind=t_wind, avg=t_avg)
        self.A, self.B = (330, 640), (1590, 470)

    def prepare(self):
        rng = np.random.default_rng(11)
        im = Image.new("RGBA", (W, H), (14, 22, 18, 255))
        d = ImageDraw.Draw(im)
        for _ in range(420):
            x, y = rng.uniform(-100, W), rng.uniform(-100, H)
            w, h = rng.uniform(60, 220), rng.uniform(40, 160)
            g = int(rng.uniform(26, 52))
            col = (int(g * 0.7), g, int(g * 0.6), 255)
            ang = rng.uniform(-0.25, 0.25)
            pts = [(x, y), (x + w, y + w * ang), (x + w - h * ang, y + h + w * ang), (x - h * ang, y + h)]
            d.polygon(pts, fill=col, outline=(10, 16, 12, 255))
        for k in range(7):
            y = rng.uniform(80, H - 80)
            pts = [(x, y + 40 * math.sin(x / 300 + k)) for x in range(-20, W + 40, 40)]
            d.line(pts, fill=(70, 120, 160, 160), width=3)
        im = im.filter(ImageFilter.GaussianBlur(1.0))
        im.alpha_composite(vignette(strength=0.7))
        lab = text_image("SOMERSET LEVELS, ENGLAND", "mono", 30, WHITE, tracking=4)
        im.alpha_composite(lab, (W - lab.width - 80, H - 90))
        ss = SS(W, H, 2)
        ss.arrow((W - 120, 230), (W - 120, 140), WHITE + (220,), 5, 24)
        im.alpha_composite(ss.done())
        im.alpha_composite(text_image("N", "cx", 40, WHITE), (W - 134, 236))
        self.bg = im

    def P(self, f):
        return (lerp(self.A[0], self.B[0], f), lerp(self.A[1], self.B[1], f))

    def base(self, t):
        im = self.bg.copy()
        ts = self.ts
        title_bar(im, "THE RECORD COURSE · 11 AUGUST 1986", t, self.start + 0.1, "15 KM · FLOWN IN BOTH DIRECTIONS")
        ss = SS(W, H, 2)
        if ts["line"] and t >= ts["line"]:
            p = ease_out_cubic((t - ts["line"]) / 1.0)
            ss.line([self.A, self.P(p)], WHITE + (240,), 6)
            for f in (0.0, 1.0):
                if p >= f:
                    x, y = self.P(f)
                    ss.circle(x, y, 16, fill=AMBER + (255,), outline=WHITE + (255,), width=3)
            # dimension line
            if p >= 1:
                ax, ay = self.A
                bx, by = self.B
                nx, ny = -(by - ay), (bx - ax)
                L = math.hypot(nx, ny)
                nx, ny = nx / L * 70, ny / L * 70
                dashed(ss, (ax + nx, ay + ny), (bx + nx, by + ny), (255, 255, 255, 140), 2)
        for key, f0, f1, col, off in (("run1", 0, 1, AMBER, -26), ("run2", 1, 0, CYAN, 26)):
            if ts[key] and t >= ts[key]:
                p = ease_in_out((t - ts[key]) / 1.6)
                f = lerp(f0, f1, p)
                ax, ay = self.P(f0)
                bx, by = self.P(f)
                nx, ny = -(self.B[1] - self.A[1]), (self.B[0] - self.A[0])
                L = math.hypot(nx, ny)
                nx, ny = nx / L * off, ny / L * off
                if abs(f - f0) > 0.02:
                    ss.arrow((ax + nx, ay + ny), (bx + nx, by + ny), col + (255,), 8, 30)
        if ts["wind"] and t >= ts["wind"]:
            a = ease_out_cubic((t - ts["wind"]) / 0.4)
            for k in range(5):
                x = 500 + k * 230
                ph = ((t - ts["wind"]) * 160 + k * 40) % 120
                ss.arrow((x + ph, 820), (x + ph + 110, 820 - 20), (220, 230, 240, int(170 * a)), 5, 20)
        im.alpha_composite(ss.done())
        if ts["line"] and t >= ts["line"] + 0.6:
            a = ease_out_cubic((t - ts["line"] - 0.6) / 0.4)
            paste_at(im, T("EAST HUNTSPILL", "cx", 40, WHITE, shadow=3), self.A[0] - 80, self.A[1] + 30, a)
            paste_at(im, T("HARTLAKE BRIDGE", "cx", 40, WHITE, shadow=3), self.B[0] - 200, self.B[1] - 90, a)
            mx, my = self.P(0.5)
            paste_center(im, _chip("15 KM", WHITE, 40, INK), mx + 20, my + 85, a)
        if ts["run1"] and t >= ts["run1"] + 0.4:
            a = ease_out_cubic((t - ts["run1"] - 0.4) / 0.3)
            paste_at(im, _chip("RUN 1", AMBER, 34, INK), 150, 300, a)
        if ts["run2"] and t >= ts["run2"] + 0.4:
            a = ease_out_cubic((t - ts["run2"] - 0.4) / 0.3)
            paste_at(im, _chip("RUN 2", CYAN, 34, INK), 150, 370, a)
        if ts["wind"] and t >= ts["wind"] + 0.3:
            a = ease_out_cubic((t - ts["wind"] - 0.3) / 0.3)
            paste_at(im, T("WIND HELPS ONE RUN AND HURTS THE OTHER: THE AVERAGE CANCELS IT", "cb", 36, WHITE, shadow=3), 330, 880, a)
        if ts["avg"] and t >= ts["avg"]:
            from shots import ov_big
            ov_big(im, dict(t=ts["avg"], value=400.87, dec=2, size=165, x=960, y=255, sub="AVERAGE OF BOTH RUNS · 249 MPH"),
                   t, self.end)
        return im


# ================================================================== tiltrotor conversion (side view)
class TiltShot(Shot):
    def __init__(self, start, end, t_tilt=(None, None), **kw):
        super().__init__(start, end, **kw)
        self.t_tilt = t_tilt

    def base(self, t):
        im = grid_bg_cached().copy()
        t0, t1 = self.t_tilt
        p = ease_in_out((t - t0) / max(0.01, t1 - t0)) if t0 else 0.0
        ang = 90 * (1 - p)   # nacelle angle: 90 = up (helicopter), 0 = forward (airplane)
        cx, cy = 900, 640
        ss = SS(W, H, 2)
        col = CYAN
        body = [(-520, -40), (-420, -80), (300, -80), (420, -50), (470, 0), (420, 40), (-380, 40), (-520, 0)]
        ss.poly([(cx + x, cy + y) for x, y in body], fill=(70, 200, 255, 28), outline=col + (255,), width=3)
        ss.poly([(cx - 560, cy - 30), (cx - 640, cy - 170), (cx - 590, cy - 170), (cx - 500, cy - 40)],
                fill=(70, 200, 255, 28), outline=col + (255,), width=3)
        # wing section (seen edge-on) above the fuselage
        wx, wy = cx + 40, cy - 110
        ss.ellipse((wx - 120, wy - 18, wx + 120, wy + 18), fill=(255, 176, 32, 90), outline=AMBER + (255,), width=3)
        # nacelle + rotor
        th = math.radians(ang)
        ux, uy = math.cos(th), -math.sin(th)
        n0 = (wx + 60, wy)
        n1 = (n0[0] + ux * 150, n0[1] + uy * 150)
        ss.line([n0, n1], (220, 230, 240, 255), 26)
        px, py = -uy, ux
        Rr = 330
        ss.line([(n1[0] + px * Rr, n1[1] + py * Rr), (n1[0] - px * Rr, n1[1] - py * Rr)], WHITE + (255,), 6)
        ss.ellipse((n1[0] - 12, n1[1] - 12, n1[0] + 12, n1[1] + 12), fill=WHITE + (255,))
        # force arrows
        if p < 0.5:
            a = 1 - p * 2
            ss.arrow((n1[0], n1[1] - 20), (n1[0], n1[1] - 20 - 200 * a), CYAN + (int(255 * a),), 12, 36)
        else:
            a = (p - 0.5) * 2
            ss.arrow((n1[0] + 30, n1[1]), (n1[0] + 30 + 230 * a, n1[1]), AMBER + (int(255 * a),), 12, 36)
            ss.arrow((wx, wy - 30), (wx, wy - 30 - 170 * a), CYAN + (int(255 * a),), 10, 34)
        im.alpha_composite(ss.done())
        lab = "HELICOPTER MODE" if p < 0.5 else "AIRPLANE MODE"
        c = CYAN if p < 0.5 else AMBER
        title_bar(im, "TILTROTOR", t, self.start + 0.1, "TAKES OFF LIKE A HELICOPTER · FLIES LIKE A PLANE")
        paste_center(im, _chip(lab, c, 48, INK), W / 2, 980, 1.0)
        paste_at(im, T(f"NACELLE {ang:3.0f}°", "mono", 34, MUTED), 1500, 200, 1.0)
        if p >= 0.5:
            a = ease_out_cubic((p - 0.5) * 3)
            paste_at(im, T("WINGS CARRY THE WEIGHT", "cx", 42, CYAN, shadow=3), wx - 160, wy - 270, a)
        return im


DIAGRAMS = dict(rotor=RotorShot, airfoil=AirfoilShot, trap=TrapShot, speedo=SpeedoShot, records=RecordsShot,
                jobs=JobsShot, tandem=TandemShot, berp=BerpShot, course=CourseShot, tilt=TiltShot)
