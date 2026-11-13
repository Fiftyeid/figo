"""تحويل الصور إلى صفحات تلوين خطية جاهزة للطباعة + محرّك رسم محلي.

المبدأ:
  * كل صفحة تُنتج بدقة 300 DPI وبوضع لوني 1-bit (أسود/أبيض نقي، بدون رمادي).
  * الخطوط تُضخَّم/تُرقَّق حسب إعداد المستخدم، وتُنظَّف من النقاط المتناثرة.
"""
from __future__ import annotations

import math
import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

from . import config as C


# ---------------------------------------------------------------------------
# أدوات صور
# ---------------------------------------------------------------------------
def open_image(path: str | Path) -> Image.Image:
    img = Image.open(path)
    img.load()
    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGBA")
        bg = Image.new("RGBA", img.size, "white")
        img = Image.alpha_composite(bg, img)
    return img.convert("RGB")


def is_colorful(img: Image.Image, tol: int = 12) -> bool:
    small = img.resize((160, 160))
    arr = np.asarray(small, dtype=np.int16)
    chroma = arr.max(axis=2) - arr.min(axis=2)
    return float((chroma > tol).mean()) > 0.02


def ink_ratio(img: Image.Image) -> float:
    bw = img.convert("L")
    arr = np.asarray(bw)
    return float((arr < 128).mean())


# ---------------------------------------------------------------------------
# المعالجة الخطية
# ---------------------------------------------------------------------------
def _sobel(a: np.ndarray) -> np.ndarray:
    p = np.pad(a.astype(np.float32), 1, mode="edge")
    gx = (
        p[:-2, 2:] + 2 * p[1:-1, 2:] + p[2:, 2:]
        - p[:-2, :-2] - 2 * p[1:-1, :-2] - p[2:, :-2]
    )
    gy = (
        p[2:, :-2] + 2 * p[2:, 1:-1] + p[2:, 2:]
        - p[:-2, :-2] - 2 * p[:-2, 1:-1] - p[:-2, 2:]
    )
    return np.hypot(gx, gy) / 4.0


def _dilate(mask: np.ndarray, radius: int) -> np.ndarray:
    if radius <= 0:
        return mask
    img = Image.fromarray((mask * 255).astype(np.uint8), mode="L")
    img = img.filter(ImageFilter.MaxFilter(2 * radius + 1))
    return np.asarray(img) > 127


def _erode(mask: np.ndarray, radius: int) -> np.ndarray:
    if radius <= 0:
        return mask
    img = Image.fromarray((mask * 255).astype(np.uint8), mode="L")
    img = img.filter(ImageFilter.MinFilter(2 * radius + 1))
    return np.asarray(img) > 127


def _despeckle(mask: np.ndarray, min_neighbors: int = 2) -> np.ndarray:
    m = mask.astype(np.uint8)
    p = np.pad(m, 1)
    acc = np.zeros_like(m, dtype=np.uint8)
    for dy in (0, 1, 2):
        for dx in (0, 1, 2):
            if dx == 1 and dy == 1:
                continue
            acc += p[dy:dy + m.shape[0], dx:dx + m.shape[1]]
    return mask & (acc >= min_neighbors)


def to_line_art(
    img: Image.Image,
    thickness: int = 2,
    threshold: int = 150,
    mode: str = "auto",
    detail: float = 1.0,
) -> Image.Image:
    """يحوّل أي صورة إلى خطوط سوداء على أبيض نقي (mode "1")."""
    if mode == "auto":
        mode = "trace" if is_colorful(img) else "clean"

    gray = ImageOps.autocontrast(img.convert("L"), cutoff=1)
    arr = np.asarray(gray).astype(np.float32)

    if mode == "trace":
        smooth = np.asarray(gray.filter(ImageFilter.GaussianBlur(1.0))).astype(np.float32)
        edges = _sobel(smooth)
        edge_thr = max(12.0, 46.0 - (threshold - 150) * 0.18)
        ink = edges > edge_thr
        # المناطق الداكنة تُعتبر حبرًا أيضًا (للأشكال المملوءة)
        ink |= arr < (threshold * 0.42)
        # إغلاق الفجوات الصغيرة ثم تنظيف
        ink = _dilate(ink, 1)
        ink = _erode(ink, 1)
    else:
        ink = arr < threshold

    ink = _despeckle(ink, 2)
    ink = _despeckle(ink, 1)

    thin = int(round((thickness - 2) * max(0.5, detail)))
    if thin > 0:
        ink = _dilate(ink, thin)
    elif thin < 0:
        ink = _erode(ink, -thin)

    # لا نسمح بصفحة فارغة تمامًا
    if ink.mean() < 0.0004:
        ink = _dilate(ink, 2)

    out = np.where(ink, 0, 255).astype(np.uint8)
    res = Image.fromarray(out, mode="L").convert("1", dither=Image.Dither.NONE)
    return res


def fit_image(img: Image.Image, box_w_px: int, box_h_px: int) -> Image.Image:
    """يصغّر/يكبّر الصورة لتناسب الصندوق مع الحفاظ على النسبة."""
    ratio = min(box_w_px / img.width, box_h_px / img.height)
    w = max(1, int(img.width * ratio))
    h = max(1, int(img.height * ratio))
    return img.resize((w, h), Image.LANCZOS)


def compose_page(
    art: Image.Image, box_w_px: int, box_h_px: int, margin_ratio: float = 0.02
) -> Image.Image:
    """يضع الرسمة في منتصف صفحة بيضاء بمقاس صندوق المحتوى بالضبط."""
    inner_w = int(box_w_px * (1 - 2 * margin_ratio))
    inner_h = int(box_h_px * (1 - 2 * margin_ratio))
    fitted = fit_image(art, inner_w, inner_h)
    canvas = Image.new("L", (box_w_px, box_h_px), 255)
    canvas.paste(fitted.convert("L"), ((box_w_px - fitted.width) // 2, (box_h_px - fitted.height) // 2))
    return canvas.convert("1", dither=Image.Dither.NONE)


def thumbnail(img: Image.Image, max_px: int = C.THUMB_MAX) -> Image.Image:
    """معاينة صغيرة بخلفية بيضاء (PNG)."""
    thumb = img.convert("L").copy()
    thumb.thumbnail((max_px, max_px), Image.LANCZOS)
    return thumb.convert("RGB")


# ---------------------------------------------------------------------------
# محرّك الرسم المحلي (بدون إنترنت) — ماندالا / هندسي / زخرفي
# ---------------------------------------------------------------------------
def _pol(cx: float, cy: float, r: float, a: float) -> tuple[float, float]:
    return (cx + r * math.cos(a), cy + r * math.sin(a))


def _bezier(p0, p1, p2, p3, n=28):
    pts = []
    for i in range(n + 1):
        t = i / n
        u = 1 - t
        pts.append((
            u**3 * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t**3 * p3[0],
            u**3 * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t**3 * p3[1],
        ))
    return pts


def _leaf_radial(d, cx, cy, r0, r1, a, half, lw):
    """ورقة ناعمة تمتد من r0 إلى r1 في اتجاه a."""
    base = _pol(cx, cy, r0, a)
    tip = _pol(cx, cy, r1, a)
    mid = (r0 + r1) / 2
    c1 = _pol(cx, cy, mid + (r1 - r0) * 0.18, a - half)
    c2 = _pol(cx, cy, mid + (r1 - r0) * 0.18, a + half)
    left = _bezier(base, _pol(cx, cy, mid * 0.85, a - half), c1, tip)
    right = _bezier(tip, c2, _pol(cx, cy, mid * 0.85, a + half), base)
    d.polygon(left + right, outline=0, width=lw)
    d.line([base, tip], fill=0, width=max(1, lw - 1))


def _petal(d, cx, cy, r0, r1, a, half, lw):
    _leaf_radial(d, cx, cy, r0, r1, a, half, lw)


def _dot_ring(d, cx, cy, r, n, dot_r, lw, phase=0.0):
    for k in range(n):
        a = 2 * math.pi * k / n + phase
        x, y = _pol(cx, cy, r, a)
        d.ellipse([x - dot_r, y - dot_r, x + dot_r, y + dot_r], outline=0, width=lw)


def _mandala(d, W, H, rng, detail, lw):
    cx, cy = W / 2, H / 2
    R = min(W, H) * 0.45
    base = rng.choice([8, 12, 16])
    d.ellipse([cx - R * 0.055, cy - R * 0.055, cx + R * 0.055, cy + R * 0.055], outline=0, width=lw)

    # حلقة بتلات حول المركز
    _petal_ring(d, cx, cy, R * 0.07, R * 0.26, base, 0.42 * math.pi / base, lw)
    d.ellipse([cx - R * 0.27, cy - R * 0.27, cx + R * 0.27, cy + R * 0.27], outline=0, width=lw)
    _dot_ring(d, cx, cy, R * 0.33, base, R * 0.028, lw, phase=math.pi / base)
    d.ellipse([cx - R * 0.38, cy - R * 0.38, cx + R * 0.38, cy + R * 0.38], outline=0, width=lw)

    rings = 2 + int(round(2 * detail))
    for i in range(rings):
        r0 = R * (0.40 + 0.36 * i / max(1, rings))
        r1 = r0 + R * 0.28
        _petal_ring(d, cx, cy, r0, r1, base + 2 * i, 0.34 * math.pi / (base + 2 * i), lw)
        d.ellipse([cx - r1, cy - r1, cx + r1, cy + r1], outline=0, width=lw)

    # حلقة نقاط نهائية + إطار مزدوج
    _dot_ring(d, cx, cy, R * 0.93, base * 2, R * 0.016, max(1, lw - 1), phase=0.0)
    d.ellipse([cx - R, cy - R, cx + R, cy + R], outline=0, width=lw)
    pad = R * 0.055
    d.ellipse([cx - R - pad, cy - R - pad, cx + R + pad, cy + R + pad], outline=0, width=max(1, lw - 1))
    d.ellipse([cx - R * 0.875, cy - R * 0.875, cx + R * 0.875, cy + R * 0.875], outline=0, width=max(1, lw - 1))


def _petal_ring(d, cx, cy, r0, r1, n, half, lw):
    for k in range(n):
        a = 2 * math.pi * k / n + math.pi / n
        _petal(d, cx, cy, r0, r1, a, half, lw)
        # فاصل صغير بين البتلات
        g = _pol_avg(cx, cy, r0 * 0.55, a + math.pi / n)
        d.ellipse([g[0] - (r1 - r0) * 0.06, g[1] - (r1 - r0) * 0.06,
                   g[0] + (r1 - r0) * 0.06, g[1] + (r1 - r0) * 0.06], outline=0, width=max(1, lw - 1))


def _pol_avg(cx, cy, r, a):
    return _pol(cx, cy, r, a)


def _ellipse_pts(cx, cy, rx, ry, rot, n=64):
    pts = []
    c, s = math.cos(rot), math.sin(rot)
    for k in range(n):
        t = 2 * math.pi * k / n
        x, y = rx * math.cos(t), ry * math.sin(t)
        pts.append((cx + x * c - y * s, cy + x * s + y * c))
    return pts


def _leaf(d, x0, y0, x1, y1, width, lw):
    """ورقة على شكل عدسة بين نقطتين."""
    mx, my = (x0 + x1) / 2, (y0 + y1) / 2
    dx, dy = x1 - x0, y1 - y0
    L = math.hypot(dx, dy) or 1.0
    nx, ny = -dy / L, dx / L
    up, down = [], []
    for k in range(25):
        t = k / 24
        f = math.sin(math.pi * t) * width
        up.append((x0 + dx * t + nx * f, y0 + dy * t + ny * f))
        down.append((x0 + dx * t - nx * f, y0 + dy * t - ny * f))
    d.polygon(up, outline=0)
    d.polygon(list(reversed(down)), outline=0)
    d.line([(x0, y0), (x1, y1)], fill=0, width=max(1, lw - 1))
    d.line([_pol(x0, 0, 0, 0), (mx, my)], fill=0, width=1) if False else None


def _geometric(d, W, H, rng, detail, lw):
    cx, cy = W / 2, H / 2
    R = min(W, H) * 0.46
    sides = rng.choice([3, 4, 5, 6, 8])
    layers = max(4, int(4 + 6 * detail))
    for i in range(layers):
        r = R * 0.95 * (1 - i / (layers + 1))
        rot = i * rng.uniform(0.05, 0.18)
        pts = [_pol(cx, cy, r, 2 * math.pi * k / sides + rot) for k in range(sides)]
        d.polygon(pts, outline=0)
        inner = [_pol(cx, cy, r * 0.66, 2 * math.pi * k / sides + rot + math.pi / sides) for k in range(sides)]
        d.polygon(inner, outline=0)
    for k in range(sides * 2):
        a = 2 * math.pi * k / (sides * 2)
        d.line([_pol(cx, cy, R * 0.14, a), _pol(cx, cy, R * 0.96, a)], fill=0, width=max(1, lw - 1))
    for k in range(sides):
        a = 2 * math.pi * k / sides + math.pi / sides
        x, y = _pol(cx, cy, R * 0.44, a)
        d.ellipse([x - R * 0.055, y - R * 0.055, x + R * 0.055, y + R * 0.055], outline=0, width=lw)
    d.ellipse([cx - R * 0.16, cy - R * 0.16, cx + R * 0.16, cy + R * 0.16], outline=0, width=lw)


def _flower(d, fx, fy, fr, rng, lw):
    petals = rng.choice([5, 6, 8])
    for p in range(petals):
        pa = 2 * math.pi * p / petals
        px, py = fx + fr * 0.60 * math.cos(pa), fy + fr * 0.60 * math.sin(pa)
        d.polygon(_ellipse_pts(px, py, fr * 0.40, fr * 0.24, pa), outline=0, width=lw)
        # خط داخلي للبتلة
        d.polygon(_ellipse_pts(px, py, fr * 0.26, fr * 0.13, pa), outline=0, width=max(1, lw - 1))
    d.ellipse([fx - fr * 0.25, fy - fr * 0.25, fx + fr * 0.25, fy + fr * 0.25], outline=0, width=lw)
    _dot_ring(d, fx, fy, fr * 0.13, max(5, petals), fr * 0.028, max(1, lw - 1))


def _floral(d, W, H, rng, detail, lw):
    """باقة زهور في مزهرية — تملأ الصفحة بشكل متوازن."""
    cx = W / 2
    vase_top = H * 0.80
    vase_bottom = H * 0.94
    vase_w = W * 0.17
    # المزهرية: جسم منحني + فوهة
    left = _bezier((cx - vase_w, vase_top), (cx - vase_w * 1.25, vase_top + (vase_bottom - vase_top) * 0.55),
                   (cx - vase_w * 0.62, vase_bottom), (cx - vase_w * 0.55, vase_bottom))
    right = _bezier((cx + vase_w * 0.55, vase_bottom), (cx + vase_w * 0.62, vase_bottom),
                    (cx + vase_w * 1.25, vase_top + (vase_bottom - vase_top) * 0.55), (cx + vase_w, vase_top))
    d.line(left + right, fill=0, width=lw, joint="curve")
    d.line([(cx - vase_w, vase_top), (cx + vase_w, vase_top)], fill=0, width=lw, joint="curve")
    d.ellipse([cx - vase_w, vase_top - H * 0.022, cx + vase_w, vase_top + H * 0.022], outline=0, width=lw)
    d.arc([cx - vase_w * 0.92, vase_top + (vase_bottom - vase_top) * 0.28,
           cx + vase_w * 0.92, vase_bottom - H * 0.005], 200, 340, fill=0, width=max(1, lw - 1))
    # زخرفة على المزهرية
    for k in range(5):
        a = math.pi + math.pi * k / 4
        x1 = cx + vase_w * 0.62 * math.cos(a)
        y1 = (vase_top + vase_bottom) / 2 + (vase_bottom - vase_top) * 0.22 * math.sin(a)
        x2 = cx + vase_w * 0.62 * math.cos(a + 0.35)
        y2 = (vase_top + vase_bottom) / 2 + (vase_bottom - vase_top) * 0.22 * math.sin(a + 0.35)
        d.line([(x1, y1), (x2, y2)], fill=0, width=max(1, lw - 1))

    # توزيع الزهور على قبة فوق المزهرية
    count = max(5, int(5 + 2.5 * detail))
    dome_cx, dome_cy = cx, H * 0.44
    Rx, Ry = W * 0.31, H * 0.30
    spots = []
    for i in range(count):
        t = i / max(1, count - 1)
        ang = math.pi * (0.06 + 0.88 * t) + rng.uniform(-0.05, 0.05)
        spread = rng.uniform(0.80, 1.0)
        fx = dome_cx + Rx * spread * math.cos(ang)
        fy = dome_cy - Ry * spread * math.sin(ang) + rng.uniform(-H * 0.02, H * 0.02)
        fr = min(W, H) * rng.uniform(0.085, 0.115)
        spots.append((fx, fy, fr))
    # زهرة مركزية أعلى
    spots.append((dome_cx + rng.uniform(-W * 0.03, W * 0.03), dome_cy - Ry * 0.55, min(W, H) * 0.10))

    # السيقان
    for (fx, fy, fr) in spots:
        p0 = (cx + rng.uniform(-vase_w * 0.45, vase_w * 0.45), vase_top + H * 0.01)
        c1 = (p0[0] + (fx - cx) * 0.18, p0[1] - (p0[1] - fy) * 0.45)
        c2 = (fx + (cx - fx) * 0.10, fy + (p0[1] - fy) * 0.22)
        stem = _bezier(p0, c1, c2, (fx, fy + fr * 0.55))
        d.line(stem, fill=0, width=max(1, lw - 1), joint="curve")
        # أوراق على الساق
        for j in (1, 2):
            if rng.random() < 0.45:
                continue
            idx = int(len(stem) * rng.uniform(0.25, 0.6))
            lx, ly = stem[idx]
            ang2 = math.atan2(fy - p0[1], fx - p0[0]) + rng.choice([-0.9, 0.9])
            lx2, ly2 = lx + fr * 1.25 * math.cos(ang2), ly + fr * 1.25 * math.sin(ang2)
            d.polygon(_ellipse_pts((lx + lx2) / 2, (ly + ly2) / 2, fr * 0.62, fr * 0.26,
                                   math.atan2(ly2 - ly, lx2 - lx)), outline=0, width=lw)
            d.line([(lx, ly), (lx2, ly2)], fill=0, width=max(1, lw - 2))

    for (fx, fy, fr) in spots:
        _flower(d, fx, fy, fr, rng, lw)

    # أرضية خفيفة
    d.line([(W * 0.10, vase_bottom + H * 0.012), (W * 0.90, vase_bottom + H * 0.012)],
           fill=0, width=max(1, lw - 1))


PROCEDURAL_STYLES = {"mandala": _mandala, "geometric": _geometric, "floral": _floral}


def procedural_art(
    style: str = "mandala",
    seed: int | None = None,
    width: int = 2400,
    height: int = 3000,
    detail: float = 0.8,
    thickness: int = 2,
) -> Image.Image:
    """يرسم صفحة تلوين كاملة محليًا (لا يحتاج إنترنت ولا مفاتيح)."""
    if style not in PROCEDURAL_STYLES:
        style = "mandala"
    rng = random.Random(seed)
    scale = 3  # supersampling للحصول على خطوط ناعمة
    W, H = width * scale, height * scale
    img = Image.new("L", (W, H), 255)
    d = ImageDraw.Draw(img)
    lw = max(3 * scale // 2, int(round((thickness + 0.6) * scale * (0.85 + 0.2 * detail))))
    PROCEDURAL_STYLES[style](d, W, H, rng, detail, lw)
    img = img.resize((width, height), Image.LANCZOS)
    # عتبة مرتفعة نسبيًا كي لا تتقطّع الخطوط الرفيعة
    return to_line_art(img, thickness=thickness, mode="clean", threshold=205, detail=detail)
