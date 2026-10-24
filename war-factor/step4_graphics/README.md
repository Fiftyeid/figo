# Step 4: graphics (preview, 2026-10-24)

Status: PREVIEW for review. The Step 4 palette and layout were not found in the repo, commit history, or session notes, so `palette.json` holds placeholder values. Confirm or replace them before final render.

## Files
- `palette.json`: colors, type sizes, layout margins (placeholder, labelled as such).
- `graphics_data.json`: one entry per card. Every number is a `source_id` into `../step1_research/sources.csv`. The `expected` value is checked against the CSV.
- `build_graphics.py`: renders the layers and stops if any `expected` value differs from the CSV. Run with `/home/user/.ffmpeg-venv/bin/python build_graphics.py` (Pillow and ffmpeg).
- `layers/NN_<card>.png`: transparent 1920x1080 RGBA layer per card, for CapCut.
- `layers/03_race_manned_2023.png`: final state of the race card.
- `preview/NN_<card>_composite.png`: each layer over the placeholder background.
- `preview/race_composite.mp4`: the animated race card (bars grow at 2 s and 4 s, hold to 14 s), 1920x1080, 30 fps, over the placeholder background.
- `../step6_publish/thumbnail_1280x720.png`: thumbnail. Text only: no footage, logos, seals, or unit insignia.

Not kept in the repo: an animated ProRes 4444 alpha of the race card (about 200 MB). Set `WF_ALPHA_MOV=1` to write it locally.

## Layout (placeholder)
- 1920x1080, 30 fps. Safe margins 96 px left and right, 90 px top and bottom.
- Headline at y=110, 64 px bold. Chip row at y=900 (46 px tall, 28 px text). Caveat text sits above the chips.
- Colors: Air Force blue, Army olive, Navy + Marine Corps combined amber, second view violet, unmanned gray. Caveats in red.

## Numbers on screen (all from sources.csv)
| Card | Shown | Source id |
|---|---|---|
| 01 hook | 4,959 manned, 2023, includes 25 gliders | 2 |
| 02 hook types | about 2,100 H-60; 862 F-16 | 53, 17 |
| 03 race | 4,959 AF; about 3,900 Army; manned, 2023 | 2, 24 |
| 04 AF total | 5,286 total = 4,959 manned + 327 unmanned and targets | 1, 2, 16 |
| 05 AF types | 2,093; 862; 408; 185; 376; 1,102; 442; 222; 261 (on-screen only) | 4, 17, 20, 47, 21, 10, 19, 43, 46 |
| 06 Army types | about 2,100; 700; 500; 400 (CBO text); 200 | 53–57 |
| 07 Army views | about 3,900 manned; about 4,600 including drones (derived); 5,286 AF total | 24, 26, 1 |
| 08 Navy + USMC | about 4,000 combined, FY2022, not split, not ranked | 28 |
| 09 context | just over 52,200 aircraft, 161 nations (FlightGlobal public summary) | 36, 37 |
| 10 recap | the five figures above | 2, 24, 28, 1, 26 |

No USMC-only figure (1,262, 2022) is drawn. The Navy and Marine Corps card is never shown beside separate Marine figures.

## Open items
- Confirm the palette and layout (placeholder).
- Captions (`captions.srt`) and the final edit need the narration audio, which is blocked until a voice is chosen.
- The H-47 figure is shown as "about 400 (CBO text)". See sources.csv row 56 and unverified.txt section G1.
