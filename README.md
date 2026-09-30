# figo

## PDF stamping tool

`tools/stamp_pdf.py` overlays a stamp / logo image on every page of a PDF
(or a chosen subset) without covering the page content.

```bash
python tools/stamp_pdf.py input.pdf stamp.png output.pdf \
    --position bottom-center --width-ratio 0.22 --opacity 0.9
```

| option | meaning |
| --- | --- |
| `--position` | `bottom-center` (default), `bottom-left`, `bottom-right`, `top-center`, `top-left`, `top-right`, `center` |
| `--width-ratio` | stamp width as a fraction of the page width (`0.22` = 22%) |
| `--opacity` | `0.0`–`1.0`, applied through the image's alpha mask |
| `--margin` | distance from the page edge, in points (default `24`) |
| `--bg-key` | `auto` (default), `black`, `white`, `keep` — `black`/`white` key out that background colour and rebuild a clean alpha channel, un-premultiplying the colour so edges do not look muddy |
| `--gain` | alpha boost when keying (default `2.5`) |
| `--trim` | crop empty borders of the artwork |
| `--pages` | subset, e.g. `1-5,9` |

Details that matter:

* The stamp is inserted as an image XObject with an SMask, so it is transparent
  and the underlying text stays readable.
* Rotated pages (`/Rotate` 90 / 180 / 270) are handled — the artwork is
  pre-rotated so it still reads upright, and the target rectangle is mapped
  from visible page coordinates back to unrotated page coordinates. Verified
  for all four rotations against rendered output.

### Rebuilding the stamp artwork

`tools/make_stamp.py` regenerates the "Ability / قدرة" stamp as a clean
transparent artwork (the supplied PNG has a black background and fuzzy text).
Arabic shaping uses `arabic-reshaper` + `python-bidi` because Pillow in this
environment is built without libraqm. Amiri (SIL OFL) is bundled in
`tools/fonts/`.

```bash
python tools/make_stamp.py "شركة قدرة للتنمية" "والحلول التكنولوجية للتعليم" \
    "Ability For Development" "And Technological Solutions For Education" \
    --ar3 "س.ت: ١١٤٤٩٩  ب.ض: ٥٥٧-٦٦٩" -o stamp.png
```

### Requirements

```bash
python -m venv .venv && .venv/bin/pip install pymupdf pillow numpy arabic-reshaper python-bidi
```