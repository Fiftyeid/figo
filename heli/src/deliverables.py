# -*- coding: utf-8 -*-
"""
Companion deliverables for "World's Fastest Military Helicopter Explained":
  - output/thumbnail.jpg            (1280x720 high-CTR YouTube thumbnail)
  - output/subtitles_en.srt         (synced English SRT captions)
  - output/youtube_description.md   (vidIQ-optimised title, description, chapters, tags, pinned comment)
  - script/script_en.md             (full voice-over script with timestamps)
"""
import os, re, json
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from common import (ROOT, ASSETS, BUILD, AMBER, RED, CYAN, GREEN, WHITE, INK, MUTED,
                    load_photo, view, text_image, glow, chip, rounded_rect, paste_at, paste_center, vignette)
from script_data import SECTIONS

OUT = os.path.join(ROOT, "output")
os.makedirs(OUT, exist_ok=True)

tl = json.load(open(os.path.join(BUILD, "timeline.json"), encoding="utf-8"))
SEC = {s["id"]: s for s in tl["sections"]}


def char_time(sec, c):
    cm = sec["cmap"]
    for k in range(len(cm) - 1):
        if cm[k][0] <= c <= cm[k + 1][0]:
            c0, t0 = cm[k]
            c1, t1 = cm[k + 1]
            return t0 + (t1 - t0) * (c - c0) / max(1, c1 - c0)
    return cm[-1][1]


def ts_srt(t):
    ms = int(round(max(0.0, t) * 1000))
    s, ms = divmod(ms, 1000)
    m, s = divmod(s, 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def ts_yt(t):
    s = int(max(0, round(t)))
    m, s = divmod(s, 60)
    return f"{m:02d}:{s:02d}"


def subtitles():
    cues = []
    for sec in tl["sections"]:
        text = sec["text"]
        # split into natural clauses
        parts = [m for m in re.finditer(r"[^.!?;:\n]+[.!?;:]?", text) if m.group(0).strip()]
        for m in parts:
            clause = m.group(0).strip()
            c0, c1 = m.start(), m.end()
            t0, t1 = char_time(sec, c0), char_time(sec, c1)
            words = clause.split()
            # chunk into <= 12 words per caption
            n_chunks = max(1, int(round(len(words) / 10)))
            step = max(1, int(round(len(words) / n_chunks)))
            chunks = [" ".join(words[i:i + step]) for i in range(0, len(words), step)]
            tot_c = sum(len(ch) for ch in chunks) or 1
            cur = t0
            for ch in chunks:
                dur = (t1 - t0) * (len(ch) / tot_c)
                cues.append((cur, min(t1, cur + max(0.9, dur - 0.04)), ch))
                cur += dur
    with open(os.path.join(OUT, "subtitles_en.srt"), "w", encoding="utf-8") as f:
        for i, (a, b, txt) in enumerate(cues, 1):
            f.write(f"{i}\n{ts_srt(a)} --> {ts_srt(b)}\n{txt}\n\n")
    return len(cues)


CHAPTER_TITLES = [
    ("intro", "00:00 The 40-Year-Old Helicopter Speed Record"),
    ("chinook", f"{ts_yt(SEC['chinook']['start'])} Answer #1: Boeing CH-47F Chinook (Guinness Record)"),
    ("hind", f"{ts_yt(SEC['hind']['start'])} Answer #2: Soviet Mi-24 Hind & the 1978 Record"),
    ("lynx", f"{ts_yt(SEC['lynx']['start'])} Answer #3: Westland G-Lynx & BERP Rotor Blades"),
    ("record", f"{ts_yt(SEC['record']['start'])} The 400.87 km/h Run Over Somerset (1986)"),
    ("wall", f"{ts_yt(SEC['wall']['start'])} The Physics Wall: Advancing vs. Retreating Blades"),
    ("stall", f"{ts_yt(SEC['stall']['start'])} Retreating Blade Stall & the Mach 1 Trap"),
    ("compound", f"{ts_yt(SEC['compound']['start'])} Compound Helicopters & Lockheed AH-56 Cheyenne"),
    ("x2", f"{ts_yt(SEC['x2']['start'])} Sikorsky X2, Eurocopter X3, SB-1 Defiant & Airbus Racer"),
    ("tiltrotor", f"{ts_yt(SEC['tiltrotor']['start'])} Answer #4: Bell V-280 Valor / MV-75 Cheyenne II"),
    ("verdict", f"{ts_yt(SEC['verdict']['start'])} Final Verdict: Which One Is Really the Fastest?"),
]


TAGS = [
    "world's fastest military helicopter",
    "fastest military helicopter explained",
    "fastest helicopter in the world",
    "why helicopters can't fly faster",
    "retreating blade stall explained",
    "westland lynx speed record",
    "G-LYNX 400 km/h",
    "CH-47F Chinook top speed",
    "Mi-24 Hind speed record",
    "Sikorsky SB-1 Defiant",
    "Sikorsky X2",
    "Bell V-280 Valor",
    "MV-75 Cheyenne II",
    "Airbus Racer",
    "military aviation explained",
]


def description_and_metadata():
    chapters = "\n".join(line for _, line in CHAPTER_TITLES)
    tag_str = ", ".join(TAGS)
    md = f"""# Publishing Metadata (vidIQ-Optimised)

## Primary Title (50 chars — primary keyword at character 0)
```
World’s Fastest Military Helicopter Explained
```

## Alternative High-CTR Titles (for YouTube Studio Test & Compare)
1. `World’s Fastest Military Helicopter Explained (Why 400 km/h Is a Wall)`
2. `Why No Helicopter Has Beaten This 1986 Speed Record`

## Description (copy & paste)
```
World’s Fastest Military Helicopter Explained: why a 1986 British Westland Lynx record of 400.87 km/h still stands 40 years later, why Guinness lists the Boeing CH-47F Chinook at 315 km/h, and how compound helicopters and the US Army’s new MV-75 Cheyenne II tiltrotor broke through the aerodynamic wall.

Ask who builds the fastest military helicopter in the world and you get four different answers: a twin-rotor heavy lifter from 1961 (CH-47F Chinook), a Soviet armored gunship (Mil Mi-24 Hind / A-10), a modified British Westland Lynx (G-LYNX), and a next-generation tiltrotor that doesn't fly like a helicopter at all (Bell V-280 Valor / MV-75 Cheyenne II). In this video we break down the rotor physics behind retreating blade stall and transonic blade tips—and the 60-year engineering race to beat them.

CHAPTERS
{chapters}

SOURCES & REFERENCES
- Fédération Aéronautique Internationale (FAI) — Record #11659 (John Trevor Egginton, Westland G-LYNX, 400.87 km/h, 11 August 1986)
- Guinness World Records — Fastest Military Helicopter (Boeing CH-47F Chinook)
- Royal Aeronautical Society & Leonardo UK — British Experimental Rotor Programme (BERP) & G-LYNX restoration notes
- Sikorsky / Boeing / Lockheed Martin / Bell Textron / Airbus Helicopters flight-test disclosures (X2, X3, S-97 Raider, SB>1 Defiant, V-280 Valor, Racer)
- U.S. Army Public Affairs — MV-75 Cheyenne II official designation (April 2026)

#MilitaryAviation #Helicopters #EngineeringExplained
```

## Tags ({len(TAGS)} tags — copy into YouTube Tags box)
```
{tag_str}
```

## Upload Settings
- **Category:** Science & Technology *(or Education — keep consistent with your channel default)*
- **Video Language:** English (United States)
- **Subtitles:** Upload `subtitles_en.srt`
- **AI Use Disclosure:** Yes (synthetic voice narration & AI-generated illustrations)
- **Pinned Comment:**
```
Which one gets your vote for the title — the CH-47F Chinook (in service), G-LYNX (official FAI record), the X2/Defiant (compound), or the MV-75 Cheyenne II (tiltrotor)? Drop your pick below 👇
```
"""
    open(os.path.join(OUT, "youtube_description.md"), "w", encoding="utf-8").write(md)


def script_markdown():
    lines = [
        "# Voice-Over Script — World’s Fastest Military Helicopter Explained",
        "",
        f"Final runtime: {ts_yt(tl['duration'])} — {len(SECTIONS)} sections — Voice: English documentary narrator",
        "",
    ]
    for s in SECTIONS:
        sec = SEC[s["id"]]
        lines.append(f"## {s['title']}  `({ts_yt(sec['start'])} -> {ts_yt(sec['end'])})`")
        lines.append("")
        lines.append(s["text"].replace("\n", "\n\n"))
        lines.append("")
    open(os.path.join(ROOT, "script", "script_en.md"), "w", encoding="utf-8").write("\n".join(lines))


def thumbnail():
    TW, TH = 1280, 720
    # Split high-contrast composition: G-LYNX on the left, Defiant on the right
    left = view(load_photo("lynx_record", contrast=1.15, sat=1.12, warmth=0.4), 0.45, 0.52, 1.25, out=(780, TH))
    right = view(load_photo("defiant", contrast=1.15, sat=1.10, teal=0.35), 0.52, 0.48, 1.30, out=(680, TH))

    canvas = Image.new("RGBA", (TW, TH), INK + (255,))
    canvas.paste(left.convert("RGBA"), (0, 0))

    # Diagonal mask for the right half
    mask = Image.new("L", (680, TH), 0)
    ImageDraw.Draw(mask).polygon([(140, 0), (680, 0), (680, TH), (0, TH)], fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(2))
    r_rgba = right.convert("RGBA")
    r_rgba.putalpha(mask)
    canvas.alpha_composite(r_rgba, (TW - 680, 0))

    # Dark top & bottom gradient bands for text legibility
    yy = np.arange(TH, dtype=np.float32)[:, None]
    top_a = np.clip(1.0 - yy / 250.0, 0, 1) ** 1.4 * 0.82
    bot_a = np.clip((yy - 440.0) / 280.0, 0, 1) ** 1.3 * 0.88
    a = np.maximum(top_a, bot_a)
    shade = Image.new("RGBA", (TW, TH), (6, 9, 14, 255))
    shade.putalpha(Image.fromarray((a * 255).astype(np.uint8).repeat(TW, axis=1), "L"))
    canvas.alpha_composite(shade)

    #Glowing diagonal divider line
    d = ImageDraw.Draw(canvas)
    d.line([(740, 0), (600, TH)], fill=AMBER + (255,), width=7)

    # Top headline
    t1 = glow(text_image("WORLD'S FASTEST", "title", 118, WHITE, stroke=8, stroke_fill=INK, shadow=10), 16, 0.7)
    paste_center(canvas, t1, TW // 2, 86)

    # Bottom giant hook + speed badges
    b1 = chip("1986 RECORD: 401 KM/H", AMBER, size=42, fg=INK, padx=24, pady=8)
    b2 = chip("US PROTOTYPE: 463+ KM/H", CYAN, size=42, fg=INK, padx=24, pady=8)
    paste_center(canvas, b1, 330, 545)
    paste_center(canvas, b2, 955, 545)

    t2 = glow(text_image("40 YEARS UNBEATEN?!", "title", 112, AMBER, stroke=8, stroke_fill=INK, shadow=10),
              20, 0.85, color=AMBER)
    paste_center(canvas, t2, TW // 2, 648)

    canvas.alpha_composite(vignette(size=(TW, TH), strength=0.45))
    canvas.convert("RGB").save(os.path.join(OUT, "thumbnail.jpg"), quality=93, subsampling=0)


if __name__ == "__main__":
    print("SRT cues:", subtitles())
    description_and_metadata()
    script_markdown()
    thumbnail()
    print("deliverables ready ->", OUT)
