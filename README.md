# Every Aircraft in U.S. Navy & Marine Corps Service — 2026

A 13-section, 44-airframe catalogue film in the "military technical catalogue"
format: warm-white paper plates, condensed display type, letterspaced mono labels
and one red accent, narrated in English by a male documentary voice.

**Target runtime:** 15:44 · **Format:** 1920×1080, 24 fps, H.264 + AAC stereo

---

## What is in this repo

| Path | Purpose |
|---|---|
| `data/fleet.json` | Single source of truth: 13 categories, 44 aircraft, specs, inventory, retirement status, narration script |
| `tools/design.py` | Design system: palette, type scale, text-sprite cache, hairline rules, chrome, grid plate |
| `tools/cutout.py` | Studio-white knockout + contact shadow so AI renders sit on the paper plate |
| `tools/film.py` | Scene graph + per-frame renderer piped straight to ffmpeg |
| `tools/audio.py` | Voiceover placement, ambient music bed, ducking, stereo mix |
| `assets/fleet/*.png` | Aircraft renders (pure white studio sweep, matched lighting) |
| `build/vo/*.mp3` | Narration clips, one per aircraft + per section + intro/outro |
| `deliverables/` | Finished, muxed reels |

## Build

```bash
python3 tools/film.py                          # full film → build/film_av.mp4
python3 tools/film.py --preview 6 --no-fit     # first 6 scenes only (quick look)
python3 tools/film.py --stills 0,1,2           # dump stills for design review
```

Dependencies: `pillow`, `numpy`, `imageio-ffmpeg` (ships its own ffmpeg build).

## Design grammar

* **Paper** `#FDFDFA` with a 60 px drafted grid at ~3 % contrast and fine grain.
* **Ink** `#15181C`, secondary `#52575E`, hairline rules `#DFDED8`.
* **Accent** `#C62022` — section blocks, figure numbers, progress rail, alerts.
* **Type** Archivo Black (titles), Barlow Condensed (values), IBM Plex Mono
  (labels at +3 to +6 % letterspacing), Barlow Light (leads).
* **Scenes:** intro → per-section division → one plate per airframe → outro.
  Every plate carries chrome: catalogue header, timecode, section, `NN / 44`,
  and a red progress rail that advances through the film.

## Content accuracy

Inventory figures, service-entry years and retirement timelines follow the
source analysis (`breakdown_usnavy.json`) and current public reporting. Specs
use conservative, widely published values. Where a figure is approximate it is
prefixed with `≈`, and every sunset date is stated as a plan, not a fact.
