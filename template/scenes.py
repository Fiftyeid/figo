"""Scene renderers. Each one draws a complete frame for a given time.

Scenes are pure functions of (cfg, data, t) so the timeline can place them
anywhere and the renderer can draw any frame in isolation — which is what makes
chunked rendering and re-renders possible.
"""
from __future__ import annotations

import math

from PIL import Image, ImageDraw, ImageFilter

import design as D
from design import W, H, text, put, hairline, box, text_sprite, wrap, font, ink_offset


def clamp(v, a=0.0, b=1.0):
    return max(a, min(b, v))


def ease_out(p):
    return 1 - (1 - p) ** 3


def ease_in_out(p):
    return p * p * (3 - 2 * p)


def ramp(t, start, dur, fn=ease_out):
    return fn(clamp((t - start) / max(dur, 1e-6)))


# --------------------------------------------------------------- aircraft
def draw_aircraft(img, cfg, ac, cat, fig, t, timecode, progress):
    """The catalogue page for one airframe."""
    pad = 86

    # name slab, top left, and the red category tag under it
    name = ac["name"].upper()
    nx, ny = pad, 42
    _, h_name = D.chip(img, (nx, ny), name, "display", 54, D.PAPER_HI, D.INK,
                       pad_x=24, pad_y=15)

    tag = f"{cat['title'].upper()} · {ac['year']}"
    D.chip(img, (nx, ny + h_name + 12), tag, "mono-med", 15, (255, 255, 255), D.RED,
           track=2.0, pad_x=16, pad_y=9)

    # the stats, top right: label over value, columns measured so they never collide
    stats = (ac.get("stats") or [])[:3]
    gap = 54
    cols = []
    for st in stats:
        lab = str(st["label"]).upper()
        val = str(st["value"]).upper()
        w = max(D.measure(lab, "mono", 12, 4.0)[0],
                D.measure(val, "cond-semi", 34, 1.0)[0])
        cols.append((lab, val, w))
    total_w = sum(c[2] for c in cols) + gap * max(0, len(cols) - 1)
    x = W - pad - total_w
    for lab, val, w in cols:
        text(img, lab, (x, 44), "mono", 12, D.INK_45, 4.0)
        text(img, val, (x, 72), "cond-semi", 34, D.INK, 1.0)
        x += w + gap

    # optional head-to-head: the rival's value for the same three rows, under a hairline
    versus = ac.get("versus") or []
    if versus:
        vy = 148
        hairline(img, (x - total_w, vy - 16), total_w, D.RULE, 1)
        text(img, str(ac.get("versus_label", "VERSUS")).upper(), (x - total_w, vy - 4),
             "mono", 11, D.RED, 5.0)
        for i, (lab, val, w) in enumerate(cols):
            if i >= len(versus):
                break
            rival = versus[i]
            cx = x - total_w + sum(c[2] + gap for c in cols[:i])
            text(img, str(rival).upper(), (cx, vy + 20), "cond-semi", 26, D.INK_45, 0.5)

    # the airframe
    sprite = ac.get("_sprite")
    if sprite is not None:
        cy = int(H * 0.545)
        x = W // 2 - sprite.width // 2
        y = cy - sprite.height // 2
        shadow = ac.get("_shadow")
        if shadow is not None:
            img.alpha_composite(shadow, (x, cy + sprite.height // 2 - int(shadow.height * 0.46)))
        # a slow 1.5% push so the page breathes
        push = 1.0 + 0.015 * clamp(t / max(1e-6, ac.get("_dur", 20.0)))
        if abs(push - 1.0) > 1e-4:
            nw, nh = int(sprite.width * push), int(sprite.height * push)
            sp = sprite.resize((nw, nh), Image.BILINEAR)
            img.alpha_composite(sp, (x - (nw - sprite.width) // 2,
                                     y - (nh - sprite.height) // 2))
        else:
            img.alpha_composite(sprite, (x, y))

    D.bottom_chrome(img, timecode, f"Section {cat['numeral']} — {cat['title']} "
                                   f"· {fig:02d} / {cfg['meta']['total_items']}", progress)


# ---------------------------------------------------------------- section
def draw_section(img, cfg, cat, prev_items, t, timecode, progress):
    """The divider that opens a category: numeral, title, filmstrip, index."""
    pad = 86

    # red numeral tile — the numeral is centred on its ink so it sits dead centre
    box(img, (pad, 168), 78, 78, fill=D.RED)
    D.text_centered(img, cat["numeral"].upper(), (pad + 39, 207), "display", 40)
    text(img, "SECTION", (pad + 100, 186), "mono", 13, D.INK_45, 5.0)
    text(img, f"{cat['index']:02d} OF {len(cfg['categories']):02d}", (pad + 100, 208),
         "mono", 13, D.INK_45, 5.0)

    # giant ghost numeral, top right, with the red count stacked underneath it
    ghost = f"{cat['index']:02d}"
    text(img, ghost, (W - pad, 250), "display", 190, (235, 231, 222), anchor="rs")

    text(img, cat.get("kicker", "").upper(), (pad, 296), "mono-med", 15, D.INK_45, 6.5)
    title = cat["title"].upper()
    size = 96
    while D.measure(title, "display", size)[0] > W - pad * 2 - 340 and size > 48:
        size -= 4
    text(img, title, (pad, 326), "display", size, D.INK)

    # count, right, on the ghost's baseline
    count = f"{len(cat['items']):02d}"
    text(img, count, (W - pad, 392), "display", 74, D.RED, anchor="rs")
    text(img, "AIRFRAME TYPES" if cfg["meta"]["subject"] == "aircraft" else "ITEMS",
         (W - pad, 404), "mono", 12, D.INK_45, 5.0, anchor="rt")

    # index list of this section's items, right column
    y = 446
    for ac in cat["items"]:
        text(img, ac["name"].upper(), (W - pad, y), "mono-med", 14, D.INK_70, 2.5,
             anchor="rt")
        y += 26

    # the lead line
    lead = cat.get("lead", "")
    if lead:
        hairline(img, (pad, 470), W - pad * 2 - 340, D.RULE, 1)
        y = 500
        for line in wrap(lead, "body", 30, W * 0.52):
            text(img, line, (pad, y), "body", 30, D.INK_70)
            y += 42

    # filmstrip of everything in the section: thumbs on one line, captions under
    strip_y = H - 330
    thumb_h = 165
    n = max(1, len(prev_items))
    cell = min(300, int((W - pad * 2) / n))
    gap = 10
    total_w = cell * n + gap * (n - 1)
    x = W // 2 - total_w // 2
    for ac in prev_items:
        sp = ac.get("_thumb")
        if sp is not None:
            img.alpha_composite(sp, (x + (cell - sp.width) // 2,
                                     strip_y + (thumb_h - sp.height) // 2))
        text(img, ac.get("short", ac["name"]).upper(),
             (x + cell // 2, strip_y + thumb_h + 18), "mono", 11, D.INK_45, 3.0,
             anchor="cm")
        x += cell + gap

    D.top_chrome(img, cfg["meta"]["brand"], cfg["meta"]["catalogue"])
    D.bottom_chrome(img, timecode, f"Section {cat['numeral']} — {cat['title']}",
                    progress, label_x=560)


# ------------------------------------------------------------------ intro
def draw_intro(img, cfg, t, dur):
    """Title card: the subject lands in red, then a hairline closes under it."""
    m = cfg["meta"]
    CX = W / 2
    img.paste(D.reference_plate(), (0, 0))

    # the whole title block is laid out from one baseline, so any word length stacks
    BASE = 520
    BIG = 172
    SMALL = 46
    uS = ink_offset("display", SMALL)
    text(img, m["title_1"].upper(), (CX, BASE - ink_offset("display", 172) - 56),
         "display", SMALL, D.INK, 16.0, ramp(t, 0.3, 0.7), anchor="cs")
    sc = 1.0 + 0.05 * (1 - ease_out(clamp((t - 0.9) / 0.55)))
    big = m["title_2"].upper()
    while BIG > 60 and D.measure(big, "display", BIG, 2.0)[0] > W - 190:
        BIG -= 6                              # long titles shrink to fit the frame
    spr = text_sprite(big, "display", BIG, D.RED, 2.0)
    nw, nh = int(spr.width * sc), int(spr.height * sc)
    spr = spr.resize((nw, nh), Image.LANCZOS)
    put(img, spr, (CX - nw / 2, BASE - ink_offset("display", BIG) * sc),
        ramp(t, 0.9, 0.4))

    # the strap line hangs from the same baseline
    strap = m["subtitle"].upper()
    text(img, strap, (CX, BASE + 96), "cond-light", 44, D.INK_70, 5.0,
         ramp(t, 1.8, 0.9), anchor="cs")
    sw, _ = D.measure(strap, "cond-light", 44, 5.0)
    w = int((sw + 90) * ramp(t, 2.2, 0.8))
    hairline(img, (CX - w // 2, BASE + 114), w, D.RED, 2)
    text(img, m["footer"].upper(), (CX, BASE + 168), "mono-med", 17, D.INK_45, 9.0,
         ramp(t, 2.6, 0.9), anchor="cm")
    text(img, m["channel"].upper(), (CX, H - 96), "mono", 11, D.INK_25, 6.0,
         ramp(t, 3.0, 0.9), anchor="cm")


# ------------------------------------------------------------------ outro
def draw_outro(img, cfg, t, dur):
    m = cfg["meta"]
    pad = 86
    text(img, "END OF CATALOGUE", (pad, 168), "mono-med", 15, D.INK_45, 6.5,
         ramp(t, 0.1, 0.6))
    lines = m["outro_title"].upper().split("\n")
    size = 92
    while size > 48 and max(D.measure(ln, "display", size, 1.0)[0] for ln in lines) > W * 0.53:
        size -= 4                              # keep the closing line inside the column
    y = 214
    for ln in lines:
        text(img, ln, (pad, y), "display", size, D.INK, 1.0, ramp(t, 0.25, 0.7))
        y += int(size * 1.14)
    hairline(img, (pad, y + 24), 640, D.RED, 3)
    y += 76
    for i, (label, val) in enumerate(m["outro_stats"]):
        a = ramp(t, 0.55 + i * 0.18, 0.5)
        text(img, label.upper(), (pad, y + 14), "mono", 12, D.INK_45, 5.0, a)
        text(img, str(val), (W * 0.30, y), "cond-semi", 42, D.INK, 0.0, a)
        y += 64

    text(img, m["sources"], (pad, H - 190), "mono", 11, D.INK_35, 3.0,
         ramp(t, 0.8, 0.6))
    text(img, m["credit"], (pad, H - 168), "mono", 11, D.INK_35, 3.0,
         ramp(t, 0.9, 0.6))

    # faint hero silhouette on the right
    sp = m.get("_outro_sprite")
    if sp is None and m.get("outro_art"):          # lazily cut it the first time
        from pathlib import Path
        from cutout import plate
        sp = plate(str(Path(__file__).resolve().parent.parent / m["outro_art"]))
        k = min(900 / sp.width, 620 / sp.height)
        sp = sp.resize((max(1, int(sp.width * k)), max(1, int(sp.height * k))),
                       Image.LANCZOS)
        m["_outro_sprite"] = sp
    if sp is not None:
        ghost = sp.copy()
        a = ghost.getchannel("A").point(lambda v: int(v * 0.26))
        ghost.putalpha(a)
        img.alpha_composite(ghost, (W - pad - ghost.width,
                                    H // 2 - ghost.height // 2 - 30))

    text(img, "WANT TO SUPPORT THE CHANNEL?", (W - pad, H - 210), "cond-semi", 30, D.INK,
         anchor="rt", alpha=ramp(t, 1.0, 0.8))
    text(img, "CLICK JOIN TO KEEP THESE CATALOGUES COMING · THANK YOU",
         (W - pad, H - 172), "mono", 10, D.INK_45, 4.0, anchor="rt",
         alpha=ramp(t, 1.2, 0.8))
    hairline(img, (W - pad - 380, H - 232), 380, D.RED, 2, ramp(t, 0.9, 0.6))
    D.top_chrome(img, m["brand"], m["catalogue"])
