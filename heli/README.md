# World’s Fastest Military Helicopter Explained — Full 1080p Documentary (13:07)

An original English-language aviation & engineering explainer built in the editing style of top-performing YouTube
military-aviation documentaries (*Top Fives*, *IMD Aviation*, *Mustard*, *Real Engineering*).

📁 **Google Drive folder:** https://drive.google.com/drive/folders/138leiJlNIlk9LD-6uELSreO4nKN1m7CJ
🎬 **Video on Google Drive (1080p MP4 — 100% Real Video B-Roll Edition):** https://drive.google.com/file/d/14JlcZ6bgcrPty4vYkGePwVxVgk-FfqhI/view

| File | Description |
|---|---|
| `output/worlds_fastest_military_helicopter.mp4` | Final 1080p25 H.264 video (13:07.30, 100% moving aircraft B-roll + HUD diagrams, AAC audio at -14.2 LUFS) |
| `output/thumbnail.jpg` | 1280×720 split-comparison high-CTR YouTube thumbnail |
| `output/subtitles_en.srt` | Synced English SRT captions (226 cues) |
| `output/youtube_description.md` | vidIQ-optimised title, alternative titles, description, chapters, 15 tags, category & pinned comment |
| `script/script_en.md` | Full voice-over script with section timestamps |

## Story & Editing Structure
Rather than a flat listicle, the video investigates why asking *"What is the world's fastest military helicopter?"*
produces **four different answers**—and explains the aerodynamic wall behind all of them:
1. **Cold Open (00:00):** August 11, 1986 over the Somerset Levels (`400.87 km/h`), the 40-year-old record nobody has
   officially beaten, the 4-answer board, and the title sting at `01:04`.
2. **Answer #1 — Boeing CH-47F Chinook (01:11):** Why Guinness lists a "flying school bus" at `315 km/h`, with an animated
   top-down diagram of single-rotor tail-rotor torque loss vs. counter-rotating tandem rotors, plus TAS vs. IAS vs. VNE.
3. **Answer #2 — Mil Mi-24 Hind / A-10 (02:36):** The Soviet "flying tank" and its `368.4 km/h` FAI record in 1978.
4. **Answer #3 — Westland G-Lynx (03:44):** Uprated Gem 60 engines, water-methanol injection, and an interactive diagram of
   the swept paddle-tip **BERP rotor blades** and the two-way 15 km Somerset Levels course (`400.87 km/h` average, blade tips at **Mach 0.97**).
5. **The Physics Wall (05:41):** Animated top-down rotor speed map (`785 km/h` hover tip speed ± `400 km/h` forward speed ->
   `1,185 km/h` advancing tip vs. `385 km/h` retreating tip + reverse-flow circle), animated airfoil streamlines showing
   transonic shock waves vs. **retreating blade stall**, and the **Trap** corridor graph.
6. **Compound Helicopters (07:33):** Splitting lift, thrust, and control across wings + pusher propeller; the 1967
   **Lockheed AH-56 Cheyenne** (`215 kn`, canceled 1972); **Sikorsky X2** (`250 kn / 463 km/h`), **Eurocopter X3**
   (`255 kn / 472 km/h`), **SB-1 Defiant** (`247 kn / 457 km/h`), and **Airbus Racer** (`444 km/h`).
7. **Answer #4 — Bell V-280 Valor / MV-75 Cheyenne II (10:06):** Animated tiltrotor conversion (90° helicopter mode -> 0°
   airplane mode), `305 kn / 565 km/h`, why the US Army picked it over Defiant in Dec 2022, canceled FARA in Feb 2024, and
   officially named it **MV-75 Cheyenne II** in April 2026.
8. **Final Verdict (11:45):** Side-by-side summary of all four winners + G-Lynx in the Helicopter Museum at Weston-super-Mare.

## Rebuild from Source
```bash
pip install pillow numpy scipy imageio-ffmpeg
./build.sh
```
