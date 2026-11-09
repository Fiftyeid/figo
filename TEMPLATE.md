# Catalogue Template — the edit system behind the 17-minute film

This folder is the **template**: the design, the motion, the timing logic and the
audio mix of the film *Every Aircraft in U.S. Navy & Marine Corps Service 2026*, turned
into a reusable engine. A new video on any subject is a **new recipe file plus new
artwork** — no layout work, no re-timing by hand.

```
recipes/from_fleet.py   regenerates the 44-airframe recipe from data/fleet.json
template/
  design.py     palette, type, paper grain, chrome bars, text helpers
  scenes.py     the four page types: intro · section card · item page · outro
  build.py      recipe loader → timeline → frame renderer → audio mix → mp4
  cutout.py     turns white-background artwork into a sprite that sits on the paper
  audio.py      narration decode / trim / normalise + music loop fit
recipes/
  template.json         the episode recipe (the only file you edit per video)
  fleet_2026.json       the full 13-section / 44-item film, generated
  example_battle_tanks.json  a second topic, same template
artwork/        one PNG per item, shot on white, any size
assets/fleet/   the 44 airframe plates of the original film
assets/fonts/   Archivo Black, Barlow, Barlow Condensed, IBM Plex Mono
```

---

## 1. The look is fixed — that is the point

| Element | Value |
|---|---|
| Paper | `#F7F4EC` ivory, live 35 mm grain, never pure white |
| Ink | `#121417` |
| Accent | `#C41A20` (all titles, chips, rails, the section tile) |
| Display | Archivo Black, ALL CAPS, tight |
| Data / labels | IBM Plex Mono, wide-tracked, small |
| Figures | Barlow Condensed SemiBold |
| Body | Barlow Light |
| Frame | 1920×1080, 24 fps, H.264 High, `yuv420p`, faststart |

Every episode built from this folder is automatically on-brand: same paper, same
red, same chrome, same pacing. Only the content changes.

## 2. The four page types

1. **Intro** — `EVERY` in ink over the subject in red (172 px), strap line, red rule,
   catalogue line, channel mark. Elements fade in on a fixed 3-second choreography.
2. **Section card** — red numeral tile, giant ghost numeral, section title, a one-line
   lead paragraph, red item count, right-hand index of names, filmstrip of every item's
   thumbnail with captions.
3. **Item page** — black name slab + red `SECTION · YEAR` chip top-left, up to three
   stat columns top-right (measured so they never collide), the item large and centred
   with a 1.5 % slow push over its lifetime, bottom chrome with running timecode and
   section progress rail.
4. **Outro** — closing statement, three summary figures, a ghosted hero image of the
   last item, sources + credit, end-card rail.

## 3. Make a new episode

**Step 1 — artwork.** One PNG per item, shot or rendered on a plain white/light
backdrop, subject roughly centred, any resolution (≥1200 px wide looks best). Save as
`artwork/<id>.png`. Because `cutout.py` keys on luminance, the backdrop must be
*light and plain*; a busy background will show. The item's own soft shadow comes along
for free and blends into the paper.

**Step 2 — recipe.** Copy `recipes/template.json` and edit only these:

```jsonc
{
  "meta": {
    "brand":      "U.S. NAVAL AVIATION",      // small line, top left
    "catalogue":  "FLEET CATALOGUE · 2026",   // small line, top right
    "channel":    "STATEWIDE USA",            // intro footer
    "subject":    "aircraft",                 // "aircraft" or "items" (label wording)
    "title_1":    "EVERY",                    // small ink line on the intro
    "title_2":    "AIRCRAFT",                 // the giant red word
    "subtitle":   "IN U.S. NAVY & MARINE CORPS SERVICE",
    "footer":     "FLEET CATALOGUE · 2026",
    "outro_title":"THAT IS THE\nWHOLE FLEET",  // "\n" splits lines
    "outro_stats":[["AIRCRAFT TYPES",44],["CATEGORIES",13],["RETIREMENTS TRACKED TO",2032]],
    "sources":    "SOURCES: …",
    "credit":     "CATALOGUE PRODUCED BY …",
    "intro_dur":  12.0,
    "outro_dur":  20.0,
    "vo_dir":     "build/vo",
    "music":      { "file": "assets/music/bed.mp3", "gain": 0.55 },
    "output":     "EPISODE_02"
  },
  "categories": [
    {
      "title":  "Combat Jets",
      "kicker": "Strike Fighters",            // small line above the title
      "lead":   "One or two sentences of narration.",
      "items": [
        { "id": "fa18c", "name": "F/A-18C HORNET", "short": "F/A-18C", "year": 1983,
          "art": "artwork/fa18c.png",
          "stats": [ { "label": "Flown by", "value": "Marine Corps" },
                     { "label": "In service", "value": "≈125" },
                     { "label": "Max speed", "value": "Mach 1.8" } ] }
      ]
    }
  ]
}
```

Rules the loader enforces: every item needs a unique `id` and a `name`; artwork must
exist; `stats` is optional but **three** fills the page best; `outro_stats` falls back
to item/category counts if omitted.

**Step 3 — narration.** Drop mp3 files in `build/vo/` (any name the recipe
points at, these are the defaults):

| file | covers |
|---|---|
| `vo_intro.mp3` | the intro |
| `vo_sec_01.mp3` (alias `vo_lead_01.mp3`) | each section card |
| `vo_<item id>.mp3` | each item page |
| `vo_outro.mp3` | the outro |

The build tells you what it is still missing: `narration missing for N scene(s)`.
Scenes without a clip keep their minimum length, so a half-narrated episode still
renders and still cuts to the beat.

Every scene's length is derived from its clip (`+1.8 s` on items, `+2.2 s` on sections,
minimum 7 s / 6 s), so the film breathes at the pace of the voice — the 17-minute
original was built exactly this way. **Missing clips are fine**: scenes fall back to
their minimum length and the build produces a silent video, which is what you want
while you are still designing the pages.

**Step 4 — render.**

```bash
python3 template/build.py recipes/template.json --check      # validate only
python3 template/build.py recipes/template.json --stills 0,1,2,12   # QA frames
python3 template/build.py recipes/template.json              # full film
```

Output lands in `deliverables/EPISODE_xx.mp4`. `--crf` (default 19) and `--preset`
(default `medium`) pass through to ffmpeg; `--out` overrides the filename.

## 4. The original film, rebuilt

`recipes/from_fleet.py` converts `data/fleet.json` (13 sections, 44 airframes, their
stats and narration scripts) into `recipes/fleet_2026.json`. The full 2026 film is
therefore produced by this template — there is no episode-specific edit script:

```bash
python3 recipes/from_fleet.py
python3 template/build.py recipes/fleet_2026.json --check
python3 template/build.py recipes/fleet_2026.json
```

## 5. Re-branding

- **Colours / type / grain** — the top of `template/design.py` (`PAPER`, `INK`, `RED`,
  `FONTS`, `reference_plate`).
- **Page furniture** — `top_chrome()` / `bottom_chrome()` in `design.py`.
- **Motion** — `ramp()`, `ease_out()` and the `push` factor in `scenes.py`.

Nothing else needs touching for a normal episode.

## 6. What it costs

A 9-item, 2-section demo renders in ~3.5 minutes at 1080p. A 44-item, 13-section film
is ~17 minutes of footage — render it scene by scene if your machine is modest:

```bash
# preview any page without rendering a second of video
python3 template/build.py recipes/template.json --stills 5

# render a slice of the timeline (resumable, then concat the chunks)
python3 template/build.py recipes/template.json --scene 0,1,2 --out build/chunk_a.mp4
```

Chunk boundaries are baselines of real scenes, so chunks concat cleanly:

```bash
printf "file 'chunk_a.mp4'\nfile 'chunk_b.mp4'\n" > build/chunks.txt
ffmpeg -f concat -safe 0 -i build/chunks.txt -c copy deliverables/EPISODE_01.mp4
```

Chunks keep their absolute scene start times, so the on-screen timecode and the
section progress rail stay continuous across the join without any post-fix.

## 7. Dependencies

```
pip install pillow numpy imageio-ffmpeg
```

No system ffmpeg needed — `imageio-ffmpeg` ships its own binary.
