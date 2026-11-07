# Russian Armor — Technical Inventory

A 13:42 single-voice documentary short listing **every tank and armored vehicle in
Russian service today**: 52 machines, 8 categories.

Design language: a clean white **"technical display unit"** — pure white field,
hairline structure, flat type in red / white / ink, no shadows, no gradients.
All imagery is still; only the scene cuts move.

## Structure

```
data/vehicles.json     52 vehicles: name, category, year, crew, weight, armament,
                       two on-screen feature tags, render prompt, narration line
pipeline/pack_audio.py    packs the narration into <=1500-char TTS clips
pipeline/audio_timeline.py  measures the voice track, finds the pauses, builds the
                       master timeline (scene in/out points) -> work/timeline.json
pipeline/render.py        frame renderer (white display unit, cut-out exhibit,
                       silhouette-anchored callouts, spec grid)
pipeline/music.py         synthesised ambient score (drone + pulse, no melody)
pipeline/shorts.py        vertical teaser (per-line TTS = exact sync)
pipeline/build.py         renders stills, cuts them to the timeline, mixes voice +
                       score, encodes 1080p30 H.264 master + .srt
```

## Build

```bash
python3 pipeline/pack_audio.py          # narration -> audio/clips.json
python3 pipeline/build.py               # full film -> output/*.mp4
python3 pipeline/build.py --until 171   # partial render (preview)
```

Requires `pillow numpy scipy imageio-ffmpeg` (ffmpeg is bundled by the last one).
Renders live in `renders/<vehicle-id>.png` (or `.jpg`); scenes are composited on white
and the vehicles are keyed out of their studio background at render time.

## Deliverables

```
output/russian-armor-inventory.mp4        13:42 · 1920x1080 · 30 fps · H.264 + AAC stereo
output/russian-armor-inventory.srt        full subtitles, one cue per vehicle
output/russian-armor-inventory-packaging.md  title, description, chapters, tags
output/thumbnail.jpg                      1280x720
output/shorts-8-vehicles.mp4              vertical teaser 1080x1920 · 1:09 · one card per line
```

## Editorial rules

- Specifications are rounded, open-source figures — labelled "approximate" on screen.
- Loss counts are **not** invented. The outro states recorded losses are only the
  visually confirmed ones, which understates the true figure.
- Tone is analytical, not celebratory: capability plus recorded battlefield behaviour.
- Vehicle names use the designation the force uses (2S34 Khosta rather than the
  source plan's "2S34 Koalitsiya", which conflates it with the 2S35).

## Image QA

Every render is reviewed against reference silhouettes before the film is built. Pass 1
(52 vehicles) flagged ten vehicles with wrong or incomplete features — barrels truncated,
wrong hull family, generic airbrushed bodies. Those were regenerated with feature-level
prompts (turret shape, launcher type, hull lineage, wheel count) and re-reviewed.
Known-acceptable approximations: the Astais body reads more generic than the real
Remdiesel car, and the T-90's Shtora dazzler housings are understated.
