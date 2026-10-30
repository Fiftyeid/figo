"""ASS (Advanced SubStation Alpha) builder for kinetic Arabic typography.

libass does the hard parts: real Arabic shaping (harfbuzz + fribidi), so we get
correct letter joining, ligatures and RTL ordering, while \move / \t transform
tags give us the motion design.
"""
from __future__ import annotations

import os

# --- palette (BGR hex as ASS wants) -----------------------------------------
def c(rgb: str) -> str:
    rgb = rgb.lstrip("#")
    r, g, b = rgb[0:2], rgb[2:4], rgb[4:6]
    return f"&H{b}{g}{r}&".upper().replace("&H", "&H00")


WHITE = c("FFFFFF")
MUTED = c("C7D2E5")
CYAN = c("22D3EE")
VIOLET = c("A78BFA")
GOLD = c("F5C451")
INK = c("0A0E22")


def ts(sec: float) -> str:
    if sec < 0:
        sec = 0
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = sec % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def esc(text: str) -> str:
    t = text.replace("\\", "\\\\").replace("{", "(").replace("}", ")")
    return t.replace("\r\n", "\\N").replace("\n", "\\N")


def styles(accent="22D3EE", accent2="A78BFA", muted="C7D2E5", ink="0A0E22",
           ivory="F3EDE3", gold="E9C27A"):
    """ASS style block for a given accent palette."""
    return """
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Title,Cairo ExtraBold,138,{ivory_c},&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,5,90,90,90,1
Style: Accent,Tajawal ExtraBold,158,{accent_c},&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,5,90,90,90,1
Style: Body,Cairo Medium,64,{muted_c},&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,5,90,90,90,1
Style: Kicker,Cairo Medium,46,{accent_c},&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,5,90,90,90,1
Style: Bullet,Cairo Medium,62,{ivory_c},&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,5,90,90,90,1
Style: Small,Cairo Medium,40,{muted_c},&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,5,90,90,90,1
Style: Draw,Cairo Medium,20,{ivory_c},&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1
Style: Cap,Cairo Bold,84,{ivory_c},&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,5,80,80,80,1
Style: Quote,Amiri Bold,112,{gold_c},&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,5,90,90,90,1
Style: Dua,Cairo Bold,74,{gold_c},&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,5,90,90,90,1
Style: Ghost,Cairo ExtraBold,600,{gold_c},&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,5,0,0,0,1
Style: Chap,Cairo Medium,38,{gold_c},&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,5,90,90,90,1
""".format(ivory_c=c(ivory), accent_c=c(accent), accent2_c=c(accent2), muted_c=c(muted),
           gold_c=c(gold))


STYLES = styles()


STYLE_FONTS = {"Title": "Cairo ExtraBold", "Accent": "Tajawal ExtraBold", "Body": "Cairo Medium",
               "Kicker": "Cairo Medium", "Bullet": "Cairo Medium", "Small": "Cairo Medium",
               "Draw": "Cairo Medium", "Cap": "Cairo Bold", "Quote": "Amiri Bold",
               "Dua": "Cairo Bold", "Chap": "Cairo Medium"}


class Ass:
    def __init__(self, w=1080, h=1920, palette=None):
        self.w, self.h = w, h
        self.events: list[str] = []
        self.styles = styles(**(palette or {}))

    # ---------------------------------------------------------------- low level
    def ev(self, layer: int, t0: float, t1: float, style: str, text: str, tags: str = ""):
        if t1 - t0 <= 0.02:
            return
        block = "{" + tags + "}" if tags else ""
        body = esc(text)
        if "\ufdfa" in body:  # ﷺ -> Amiri (Cairo subset lacks U+FDFA), then back
            base = STYLE_FONTS.get(style, "Cairo Bold")
            body = body.replace("\ufdfa", "{\\fnAmiri Bold}\ufdfa{\\fn" + base + "}")
        self.events.append(
            f"Dialogue: {layer},{ts(t0)},{ts(t1)},{style},,0,0,0,,{block}{body}")

    # ---------------------------------------------------------------- animation
    @staticmethod
    def anim_in(x, y, dur=0.46, rise=46, blur=26, scale=86, alpha_out=True, extra=""):
        ms = int(dur * 1000)
        return (f"\\an5\\move({x},{y + rise},{x},{y},0,{ms})\\blur{blur}\\fscx{scale}\\fscy{scale}"
                f"\\alpha&HFF&\\t(0,{ms},\\blur0\\fscx100\\fscy100\\alpha&H00&){extra}")

    @staticmethod
    def anim_out(t1, t0, dur=0.32, scale_to=106, blur_to=18):
        ms = int(dur * 1000)
        start = max(0, int((t1 - t0) * 1000) - ms)
        return (f"\\t({start},{start + ms},\\alpha&HFF&\\fscx{scale_to}\\fscy{scale_to}"
                f"\\blur{blur_to})")

    def line(self, t0, t1, text, y, style="Title", x=None, rise=46, blur=26, scale=86,
             dur=0.46, out=True, extra=""):
        x = self.w // 2 if x is None else x
        tags = self.anim_in(x, y, dur, rise, blur, scale, extra=extra)
        if out:
            tags += self.anim_out(t1, t0)
        self.ev(1, t0, t1, style, text, tags)

    # ---------------------------------------------------------------- ornaments
    def rule(self, t0, t1, y, width=300, color=CYAN, thick=7, grow=0.5):
        """Thin accent bar that wipes in from the right (RTL friendly)."""
        if not str(color).startswith("&H"):
            color = c(str(color))
        x = self.w // 2 + width // 2
        ms = int(grow * 1000)
        tags = (f"\\an9\\pos({x},{y})\\p1\\1c{color}\\bord0\\shad0\\fscx0"
                f"\\alpha&HFF&\\t(0,{max(60, ms // 3)},\\alpha&H00&)"
                f"\\t({max(60, ms // 3)},{ms},\\fscx100)")
        body = f"m 0 0 l {width} 0 l {width} {thick} l 0 {thick}"
        self.ev(2, t0, t1, "Draw", body, tags)

    def pill(self, t0, t1, text, cx, cy, pad=52, height=112, color=VIOLET, size=60,
             delay=0.0):
        """Rounded translucent pill with a centred label."""
        wpx = max(190, int(len(text) * size * 0.40) + pad * 2)
        hpx = height
        r = hpx // 2
        d = (f"m {r} 0 l {wpx - r} 0 b {wpx} 0 {wpx} 0 {wpx} {r} "
             f"l {wpx} {hpx - r} b {wpx} {hpx} {wpx} {hpx} {wpx - r} {hpx} "
             f"l {r} {hpx} b 0 {hpx} 0 {hpx} 0 {hpx - r} l 0 {r} "
             f"b 0 0 0 0 {r} 0")
        ms = 420
        dly = int(delay * 1000)
        tags = (f"\\an7\\pos({cx - wpx // 2},{cy - hpx // 2})\\p1\\1c{color}"
                f"\\3c{color}\\bord2\\shad0\\fscx88\\fscy88"
                f"\\1a&HFF&\\3a&HFF&"
                f"\\t({dly},{dly + ms},\\fscx100\\fscy100\\1a&HBF&\\3a&H50&)")
        self.ev(1, t0, t1, "Draw", d, tags)
        ltags = (f"\\an5\\pos({cx},{cy + 4})\\fs{size}\\1c{WHITE}"
                 f"\\alpha&HFF&\\t({dly + 80},{dly + ms},\\alpha&H00&)")
        self.ev(3, t0, t1, "Draw", text, ltags)

    def star(self, t0, t1, cx=540, cy=760, R=250, color=CYAN, thick=2, alpha="&HC8&",
             spin=90.0, grow=1.2):
        """Khatim (8-point star) outline: two interlocked squares, slowly rotating."""
        s_half = R * 0.7071
        square = (f"m {-s_half} {-s_half} l {s_half} {-s_half} l {s_half} {s_half} "
                  f"l {-s_half} {s_half}")
        diamond = f"m 0 {-R} l {R} 0 l 0 {R} l {-R} 0"
        if not str(color).startswith("&H"):
            color = c(str(color))
        ms = int((t1 - t0) * 1000)
        for body in (square, diamond):
            tags = (f"\\pos({cx},{cy})\\p1\\1c{color}\\3c{color}"
                    f"\\1a&HFF&\\3a{alpha}\\bord{thick}\\shad0\\fscx90\\fscy90"
                    f"\\t(0,{max(400, int(grow * 1000))},\\fscx100\\fscy100)"
                    f"\\t(0,{ms},\\frz{spin})")
            self.ev(0, t0, t1, "Draw", body, tags)

    def ghost(self, t0, t1, text, y=780, size=520, color=CYAN, alpha="&HDA&"):
        """Huge, almost invisible numeral/label used as a background graphic."""
        if not str(color).startswith("&H"):
            color = c(str(color))
        ms = 600
        tags = (f"\\an5\\pos({self.w // 2},{y})\\fs{size}\\1c{color}\\3c{color}"
                f"\\1a{alpha}\\3a&HFF&\\bord0\\shad0\\fscx92\\fscy92"
                f"\\t(0,{ms},\\fscx100\\fscy100)")
        self.ev(0, t0, t1, "Ghost", text, tags)

    def card(self, t0, t1, cy, wpx=880, hpx=560, delay=0.0, dur=0.55,
             fill="0A1024", edge="22D3EE"):
        """Translucent rounded "glass" panel used behind a text block."""
        r = 46
        x0 = (self.w - wpx) // 2
        y0 = cy - hpx // 2
        d = (f"m {r} 0 l {wpx - r} 0 b {wpx} 0 {wpx} 0 {wpx} {r} "
             f"l {wpx} {hpx - r} b {wpx} {hpx} {wpx} {hpx} {wpx - r} {hpx} "
             f"l {r} {hpx} b 0 {hpx} 0 {hpx} 0 {hpx - r} l 0 {r} "
             f"b 0 0 0 0 {r} 0")
        ms = int(dur * 1000)
        dly = int(delay * 1000)
        tags = (f"\\an7\\pos({x0},{y0})\\p1\\1c{c(fill)}\\3c{c(edge)}"
                f"\\bord2\\shad0\\fscx96\\fscy94"
                f"\\1a&HFF&\\3a&HFF&"
                f"\\t({dly},{dly + ms},\\fscx100\\fscy100\\1a&H7A&\\3a&HC8&)")
        self.ev(0, t0, t1, "Draw", d, tags)

    # ---------------------------------------------------------------- output
    def write(self, path):
        head = f"""[Script Info]
ScriptType: v4.00+
Title: figo motion
PlayResX: {self.w}
PlayResY: {self.h}
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709

[V4+ Styles]{self.styles}
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(head + "\n".join(self.events) + "\n")
        return path
