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
build/pack_audio.py    packs the narration into <=1500-char TTS clips
build/audio_timeline.py  measures the voice track, finds the pauses, builds the
                       master timeline (scene in/out points) -> work/timeline.json
build/render.py        frame renderer (white display unit, cut-out exhibit,
                       silhouette-anchored callouts, spec grid)
build/music.py         synthesised ambient score (drone + pulse, no melody)
build/build.py         renders stills, cuts them to the timeline, mixes voice +
                       score, encodes 1080p30 H.264 master + .srt
```

## Build

```bash
python3 build/pack_audio.py          # narration -> audio/clips.json
python3 build/build.py               # full film -> output/*.mp4
python3 build/build.py --until 171   # partial render (preview)
```

Requires `pillow numpy scipy imageio-ffmpeg` (ffmpeg is bundled by the last one).
Renders live in `renders/<vehicle-id>.png`; scenes are composited on white.

## Editorial rules

- Specifications are rounded, open-source figures — labelled "approximate" on screen.
- Loss counts are **not** invented. The outro states recorded losses are only the
  visually confirmed ones, which understates the true figure.
- Tone is analytical, not celebratory: capability plus recorded battlefield behaviour.
- Vehicle names use the designation the force uses (2S34 Khosta rather than the
  source plan's "2S34 Koalitsiya", which conflates it with the 2S35).
