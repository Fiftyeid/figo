# -*- coding: utf-8 -*-
"""Stylised map renderer for Egypt's governorates (Natural Earth, public domain)."""
import json, math, os, functools
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from shapely.geometry import shape

from common import ASSETS, W, H, GOLD, TEAL, WHITE, text_image, glow

LAT0 = 26.8
COSL = math.cos(math.radians(LAT0))

SEA0 = (5, 18, 42)
SEA1 = (10, 36, 72)
NEIGH = (27, 31, 44)
NEIGH_EDGE = (52, 58, 78)
LAND = (36, 48, 88)
LAND_EDGE = (78, 98, 158)
EGY_EDGE = (140, 160, 225)
NILE = (64, 190, 245)
LAKE = (30, 96, 156)

CITIES = {
    "القاهرة": (31.2357, 30.0444), "الجيزة": (31.2089, 30.0131), "الإسكندرية": (29.9187, 31.2001),
    "بورسعيد": (32.3019, 31.2653), "الإسماعيلية": (32.2715, 30.5965), "السويس": (32.5498, 29.9668),
    "دمياط": (31.8133, 31.4165), "المنصورة": (31.3807, 31.0409), "دقهلة": (31.66, 31.24),
    "الزقازيق": (31.5020, 30.5877), "طنطا": (31.0004, 30.7865), "دمنهور": (30.4699, 31.0341),
    "بنها": (31.1833, 30.4667), "قليوب": (31.2069, 30.1797), "منوف": (30.9333, 30.4667),
    "شبين الكوم": (31.0118, 30.5503), "كفر الشيخ": (30.9397, 31.1107), "بني سويف": (31.0994, 29.0661),
    "الفيوم": (30.8418, 29.3084), "المنيا": (30.7503, 28.1099), "أسيوط": (31.1837, 27.1783),
    "سوهاج": (31.6948, 26.5591), "جرجا": (31.8917, 26.3383), "قنا": (32.7267, 26.1551),
    "قفط": (32.8167, 26.0000), "الأقصر": (32.6396, 25.6872), "أسوان": (32.8998, 24.0889),
    "الغردقة": (33.8116, 27.2579), "القصير": (34.2767, 26.1043), "الخارجة": (30.5464, 25.4390),
    "مرسى مطروح": (27.2373, 31.3543), "سيوة": (25.5195, 29.2032), "العريش": (33.8034, 31.1321),
    "الطور": (33.6171, 28.2412), "سرابيط الخادم": (33.4569, 29.0369), "حلوان": (31.3342, 29.8414),
    "6 أكتوبر": (30.9277, 29.9285), "الفسطاط": (31.2330, 30.0060), "بحيرة قارون": (30.60, 29.47),
}


def proj(lon, lat):
    return (lon - 31.0) * COSL, -(lat - LAT0)


class MapData:
    def __init__(self):
        d = json.load(open(os.path.join(ASSETS, "map", "egypt_map.json"), encoding="utf-8"))
        self.govs = {g["code"]: dict(g, geom=shape(g["geometry"])) for g in d["governorates"]}
        self.neighbors = [dict(n, geom=shape(n["geometry"])) for n in d["neighbors"]]
        self.rivers = [dict(r, geom=shape(r["geometry"])) for r in d["rivers"]]
        self.lakes = [dict(l, geom=shape(l["geometry"])) for l in d["lakes"]]

    def bounds(self, codes):
        xs, ys = [], []
        for c in codes:
            b = self.govs[c]["geom"].bounds
            xs += [b[0], b[2]]
            ys += [b[1], b[3]]
        return min(xs), min(ys), max(xs), max(ys)

    def label_point(self, code):
        g = self.govs[code]["geom"]
        p = g.representative_point()
        # prefer centroid when it lies inside (looks more centred)
        c = g.centroid
        if g.contains(c):
            p = c
        return p.x, p.y


@functools.lru_cache(maxsize=1)
def mapdata():
    return MapData()


def frame_for(codes, aspect=W / H, margin=1.6, min_span=2.2, max_span=15.5):
    """Return (center_lon, center_lat, span_x_deg_projected) framing the given governorates."""
    md = mapdata()
    x0, y0, x1, y1 = md.bounds(codes)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    wx = (x1 - x0) * COSL * margin
    wy = (y1 - y0) * margin
    span = max(wx, wy * aspect, min_span)
    span = min(span, max_span)
    return cx, cy, span


class View:
    """Projection for a rendered map image of size (w,h) centred on (lon,lat) with span (proj units)."""

    def __init__(self, clon, clat, span, size):
        self.clon, self.clat, self.span = clon, clat, span
        self.w, self.h = size
        self.scale = self.w / span
        self.cx, self.cy = proj(clon, clat)

    def __call__(self, lon, lat):
        x, y = proj(lon, lat)
        return (x - self.cx) * self.scale + self.w / 2, (y - self.cy) * self.scale + self.h / 2

    def poly_px(self, geom, ss=1):
        out = []
        geoms = getattr(geom, "geoms", [geom])
        for g in geoms:
            if g.geom_type == "Polygon":
                ext = [self(*p) for p in g.exterior.coords]
                holes = [[self(*p) for p in r.coords] for r in g.interiors]
                out.append(([(x * ss, y * ss) for x, y in ext], [[(x * ss, y * ss) for x, y in h] for h in holes]))
        return out

    def line_px(self, geom, ss=1):
        out = []
        geoms = getattr(geom, "geoms", [geom])
        for g in geoms:
            if g.geom_type == "LineString":
                out.append([(self(*p)[0] * ss, self(*p)[1] * ss) for p in g.coords])
            elif g.geom_type == "Polygon":
                out.append([(self(*p)[0] * ss, self(*p)[1] * ss) for p in g.exterior.coords])
        return out


def _sea(size):
    w, h = size
    y = np.linspace(0, 1, h)[:, None, None]
    x = np.linspace(0, 1, w)[None, :, None]
    t = np.clip(0.55 * y + 0.45 * (1 - np.abs(x - 0.5) * 2), 0, 1)
    a = np.array(SEA0, np.float32) * (1 - t) + np.array(SEA1, np.float32) * t
    a = a + np.random.default_rng(3).normal(0, 1.4, (h, w, 3))
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "RGB")


def _fill_polys(draw, polys, fill, outline=None, width=1):
    for ext, holes in polys:
        if len(ext) < 3:
            continue
        draw.polygon(ext, fill=fill)
        for hh in holes:
            if len(hh) >= 3:
                draw.polygon(hh, fill=None)
    if outline:
        for ext, holes in polys:
            if len(ext) >= 2:
                draw.line(ext + [ext[0]], fill=outline, width=width, joint="curve")


def render_view(clon, clat, span, size=(W, H), highlight=(), highlight2=(), hl_color=GOLD,
                hl2_color=TEAL, ss=2, dim_others=False):
    """Render base map + highlighted variant. Returns dict(base, hl, view, mask)."""
    md = mapdata()
    w, h = size
    view = View(clon, clat, span, size)
    big = (w * ss, h * ss)
    img = _sea(big)
    d = ImageDraw.Draw(img)
    lw = max(1, int(1.2 * ss))
    for n in md.neighbors:
        _fill_polys(d, view.poly_px(n["geom"], ss), NEIGH, NEIGH_EDGE, lw)
    # Egypt outer glow
    egy_mask = Image.new("L", big, 0)
    dm = ImageDraw.Draw(egy_mask)
    for g in md.govs.values():
        for ext, holes in view.poly_px(g["geom"], ss):
            if len(ext) >= 3:
                dm.polygon(ext, fill=255)
    gl = egy_mask.filter(ImageFilter.GaussianBlur(14 * ss))
    glow_layer = Image.new("RGB", big, (70, 100, 190))
    img = Image.composite(glow_layer, img, gl.point(lambda v: int(v * 0.35)))
    d = ImageDraw.Draw(img)
    for code, g in md.govs.items():
        col = LAND
        if dim_others and code not in highlight and code not in highlight2:
            col = (24, 32, 60)
        _fill_polys(d, view.poly_px(g["geom"], ss), col, LAND_EDGE, max(1, int(1.6 * ss)))
    # lakes + rivers
    for l in md.lakes:
        _fill_polys(d, view.poly_px(l["geom"], ss), LAKE, None)
    rw = max(2, int(span_to_width(span) * ss))
    for r in md.rivers:
        col = NILE if r["name"] != "Suez Canal" else (90, 170, 230)
        wdt = rw if r["name"] == "Nile" else max(2, int(rw * 0.8))
        for line in view.line_px(r["geom"], ss):
            if len(line) >= 2:
                d.line(line, fill=col, width=wdt, joint="curve")
    # Egypt border
    for g in md.govs.values():
        pass
    edge = egy_mask.filter(ImageFilter.FIND_EDGES).filter(ImageFilter.MaxFilter(3))
    img.paste(EGY_EDGE, (0, 0), edge.point(lambda v: 180 if v > 40 else 0))
    base = img.resize(size, Image.LANCZOS)

    # highlight variant
    hl = base.copy()
    mask = None
    for codes, col in ((highlight, hl_color), (highlight2, hl2_color)):
        if not codes:
            continue
        m = Image.new("L", big, 0)
        dmm = ImageDraw.Draw(m)
        for c in codes:
            for ext, holes in view.poly_px(md.govs[c]["geom"], ss):
                if len(ext) >= 3:
                    dmm.polygon(ext, fill=255)
        m_small = m.resize(size, Image.LANCZOS)
        gl = m_small.filter(ImageFilter.GaussianBlur(16))
        hl = Image.composite(Image.new("RGB", size, col), hl, gl.point(lambda v: int(v * 0.55)))
        fill = Image.new("RGB", size, col)
        hl = Image.composite(fill, hl, m_small.point(lambda v: int(v * 0.88)))
        # crisp bright edge
        e = m.filter(ImageFilter.FIND_EDGES).filter(ImageFilter.MaxFilter(3)).resize(size, Image.LANCZOS)
        hl.paste((255, 245, 210), (0, 0), e.point(lambda v: min(255, v * 2)))
        if mask is None:
            mask = m_small
    # rivers drawn again on top of highlight so the Nile stays visible
    if highlight or highlight2:
        top = Image.new("RGBA", big, (0, 0, 0, 0))
        dt = ImageDraw.Draw(top)
        for r in md.rivers:
            if r["name"] == "Suez Canal":
                continue
            wdt = rw if r["name"] == "Nile" else max(2, int(rw * 0.8))
            for line in view.line_px(r["geom"], ss):
                if len(line) >= 2:
                    dt.line(line, fill=(40, 120, 200, 235), width=wdt, joint="curve")
        for l in md.lakes:
            for ext, holes in view.poly_px(l["geom"], ss):
                if len(ext) >= 3:
                    dt.polygon(ext, fill=(30, 100, 165, 240))
        top = top.resize(size, Image.LANCZOS)
        hl = hl.convert("RGBA")
        hl.alpha_composite(top)
        hl = hl.convert("RGB")
    return dict(base=base, hl=hl, view=view, mask=mask)


def span_to_width(span):
    # Nile line width (px at 1x) depending on zoom: wider when zoomed in
    return float(np.clip(2.0 + (6.0 - span) * 0.55, 2.0, 5.0))
