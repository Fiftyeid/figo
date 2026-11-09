"""Catalogue template — build an episode from a JSON content file.

    python3 template/build.py recipe.json               # full film
    python3 template/build.py recipe.json --stills 0,2   # dump reference stills
    python3 template/build.py recipe.json --check        # validate the recipe only

The recipe describes *what* the episode is; template/design.py and
template/scenes.py decide *how* it looks. A new episode means a new recipe and
new artwork — no layout work.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

import design as D
import scenes as S
from design import W, H, FPS


class RecipeError(RuntimeError):
    """Read the message, fix the recipe, run again."""


# ------------------------------------------------------------------ helpers
def log(m: str) -> None:
    print(f"  {m}", flush=True)


def timecode(sec: float) -> str:
    sec = max(0, int(sec))
    return f"{sec // 60:02d}:{sec % 60:02d}"


def ffmpeg() -> str:
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


# ------------------------------------------------------------------- recipe
def load_recipe(path: Path) -> dict:
    if not path.exists():
        raise RecipeError(f"recipe not found: {path}")
    try:
        cfg = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise RecipeError(f"recipe is not valid JSON ({exc})") from exc

    missing = [k for k in ("meta", "categories") if k not in cfg]
    if missing:
        raise RecipeError(f"recipe is missing: {', '.join(missing)}")
    if not cfg["categories"]:
        raise RecipeError("recipe has no categories")

    for key in ("brand", "catalogue", "title_1", "title_2", "subtitle", "footer",
                "channel", "outro_title", "sources", "credit", "subject"):
        if key not in cfg["meta"]:
            raise RecipeError(f"meta is missing '{key}'")

    seen_ids: set[str] = set()
    total = 0
    for ci, cat in enumerate(cfg["categories"], 1):
        for key in ("title", "items"):
            if key not in cat:
                raise RecipeError(f"category {ci} is missing '{key}'")
        cat.setdefault("index", ci)
        cat["numeral"] = roman(ci)
        cat.setdefault("kicker", "")
        cat.setdefault("lead", "")
        if not cat["items"]:
            raise RecipeError(f"category '{cat['title']}' has no items")
        for ac in cat["items"]:
            for key in ("id", "name"):
                if key not in ac:
                    raise RecipeError(f"an item in '{cat['title']}' is missing '{key}'")
            if ac["id"] in seen_ids:
                raise RecipeError(f"duplicate id '{ac['id']}'")
            seen_ids.add(ac["id"])
            ac.setdefault("stats", [])
            ac.setdefault("year", "")
            ac.setdefault("art", f"artwork/{ac['id']}.png")
            if not (ROOT / ac["art"]).exists():
                raise RecipeError(f"artwork missing for '{ac['id']}': {ac['art']}")
            total += 1
    cfg["meta"]["total_items"] = total
    # the outro's hero image defaults to the last item in the catalogue
    if not cfg["meta"].get("outro_art") and cfg["categories"]:
        cfg["meta"]["outro_art"] = cfg["categories"][-1]["items"][-1]["art"]
    # the outro's default stats come from the recipe itself
    if not cfg["meta"].get("outro_stats"):
        cfg["meta"]["outro_stats"] = [
            ["Subjects", f"{total:02d}"],
            ["Categories", f"{len(cfg['categories']):02d}"],
        ]
    cfg["meta"].setdefault("outro_stats", [])
    return cfg


def roman(n: int) -> str:
    vals = [(10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")]
    out = ""
    for v, s in vals:
        while n >= v:
            out += s
            n -= v
    return out


# --------------------------------------------------------------------- art
def knock_out(path: Path) -> Image.Image:
    """Key the white backdrop out of an item plate and return a tight RGBA sprite."""
    from cutout import plate
    return plate(str(path))


def prepare(cfg: dict) -> None:
    for cat in cfg["categories"]:
        for ac in cat["items"]:
            sp = knock_out(ROOT / ac["art"])
            k = min(1230 / sp.width, 575 / sp.height)
            sp = sp.resize((max(1, int(sp.width * k)), max(1, int(sp.height * k))),
                           Image.LANCZOS)
            ac["_sprite"] = sp
            ac["_shadow"] = None          # plates on white already carry their shadow
            tw = 250 if len(cat["items"]) <= 4 else 190
            tk = min(tw / sp.width, 130 / sp.height)
            ac["_thumb"] = sp.resize((max(1, int(sp.width * tk)),
                                      max(1, int(sp.height * tk))), Image.LANCZOS)


# ----------------------------------------------------------------- timeline
def build_timeline(cfg: dict) -> list[dict]:
    """Place every scene. Durations come from the narration when it exists."""
    vo_dir = ROOT / cfg["meta"].get("vo_dir", "build/vo")
    intro = cfg["meta"].get("intro_dur", 12.0)
    outro = cfg["meta"].get("outro_dur", 20.0)

    def vo_len(name: str) -> float:
        p = vo_dir / f"{name}.mp3"
        if not p.exists():
            return 0.0
        import imageio_ffmpeg
        out = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-hide_banner", "-i", str(p)],
                             capture_output=True, text=True).stderr
        for line in out.splitlines():
            if "Duration:" in line:
                hms = line.split("Duration:")[1].split(",")[0].strip()
                h, m, s = hms.split(":")
                return int(h) * 3600 + int(m) * 60 + float(s)
        return 0.0

    scenes: list[dict] = [{"kind": "intro", "dur": intro, "vo": "vo_intro"}]
    for cat in cfg["categories"]:
        lead = max(6.0, vo_len(f"vo_sec_{cat['index']:02d}") + 2.2)
        scenes.append({"kind": "section", "cat": cat, "dur": lead,
                       "vo": f"vo_sec_{cat['index']:02d}"})
        for ac in cat["items"]:
            d = max(7.0, vo_len(f"vo_{ac['id']}") + 1.8)
            ac["_dur"] = d
            scenes.append({"kind": "item", "cat": cat, "ac": ac, "dur": d,
                           "vo": f"vo_{ac['id']}"})
    scenes.append({"kind": "outro", "dur": outro, "vo": "vo_outro"})

    t = 0.0
    for sc in scenes:
        sc["start"] = t
        t += sc["dur"]
    total = t
    for sc in scenes:
        sc["progress"] = (sc["start"] + sc["dur"] / 2) / max(total, 1e-6)
    scenes[0]["progress"] = 0.0
    scenes[-1]["progress"] = 1.0
    cfg["_total"] = total
    return scenes


def draw_frame(cfg: dict, scenes: list[dict], sc: dict, t: float) -> Image.Image:
    img = D.reference_plate().copy()
    abs_t = sc["start"] + t
    tc = timecode(abs_t)
    if sc["kind"] == "intro":
        S.draw_intro(img, cfg, t, sc["dur"])
    elif sc["kind"] == "section":
        S.draw_section(img, cfg, sc["cat"], sc["cat"]["items"], t, tc, sc["progress"])
    elif sc["kind"] == "item":
        fig = sum(len(c["items"]) for c in cfg["categories"][:sc["cat"]["index"] - 1]) \
              + sc["cat"]["items"].index(sc["ac"]) + 1
        S.draw_aircraft(img, cfg, sc["ac"], sc["cat"], fig, t, tc, sc["progress"])
    else:
        S.draw_outro(img, cfg, t, sc["dur"])
    if sc["kind"] != "intro":
        D.plate_grain(img, 1.7, 31)
    return img


# ------------------------------------------------------------------- render
def render(cfg: dict, scenes: list[dict], out: Path, preset: str = "medium",
           crf: int = 19) -> None:
    total = sum(s["dur"] for s in scenes)
    n_frames = int(round(total * FPS))
    proc = subprocess.Popen(
        [ffmpeg(), "-y", "-hide_banner", "-loglevel", "error", "-f", "rawvideo",
         "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-an",
         "-c:v", "libx264", "-preset", preset, "-crf", str(crf),
         "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out)],
        stdin=subprocess.PIPE)
    assert proc.stdin
    i = 0
    for sc in scenes:
        n = int(round(sc["dur"] * FPS))
        for k in range(n):
            img = draw_frame(cfg, scenes, sc, k / FPS)
            proc.stdin.write(img.convert("RGB").tobytes())
            i += 1
            if i % 480 == 0:
                print(f"    frame {i}/{n_frames} ({i / n_frames * 100:5.1f}%)", flush=True)
    proc.stdin.close()
    if proc.wait() != 0:
        raise RecipeError("ffmpeg failed while encoding the picture")
    log(f"picture: {i} frames, {total:.1f}s → {out.name}")


def mix_audio(cfg: dict, scenes: list[dict], out_wav: Path) -> bool:
    """Lay the narration clips on the timeline over the music bed, if present."""
    vo_dir = ROOT / cfg["meta"].get("vo_dir", "build/vo")
    clips = [(s, vo_dir / f"{s['vo']}.mp3") for s in scenes]
    clips = [(s, p) for s, p in clips if p.exists()]
    if not clips:
        log("no narration clips found — rendering a silent picture")
        return False

    SR = 44100
    total = sum(s["dur"] for s in scenes) + 2.0
    n = int(total * SR)
    voice = np.zeros(n, np.float32)

    from audio import _decode, _norm, _trim_silence
    for sc, path in clips:
        a = _norm(_trim_silence(_decode(path)), -18.5)
        start = int((sc["start"] + sc.get("vo_offset", 0.7)) * SR)
        end = min(n, start + len(a))
        if start < n:
            voice[start:end] += a[: end - start]

    bed = np.zeros(n, np.float32)
    bed_cfg = cfg["meta"].get("music")
    if bed_cfg:
        bed_path = ROOT / bed_cfg["file"]
        if bed_path.exists():
            from audio import _loop_fit
            bed = _loop_fit(_norm(_decode(bed_path), -18.0), n) * bed_cfg.get("gain", 0.6)

    # duck the bed under the voice
    hop = int(0.02 * SR)
    frames = len(voice) // hop
    env = np.abs(voice[: frames * hop]).reshape(frames, hop).max(axis=1)
    env = np.convolve(env, np.ones(40) / 40, mode="same")
    duck = 1.0 - 0.55 * np.clip(env / 0.26, 0, 1)
    duck = np.repeat(duck, hop)
    duck = np.pad(duck, (0, max(0, n - len(duck))), mode="edge")[:n]
    bed *= duck.astype(np.float32)

    mix = voice + bed
    peak = float(np.max(np.abs(mix))) + 1e-9
    if peak > 0.95:
        mix = np.tanh(mix / peak * 1.05) * 0.95
    stereo = np.stack([mix, mix * 0.995 + np.roll(bed, 120) * 0.06], axis=1)
    pcm = (np.clip(stereo, -1, 1) * 32767).astype(np.int16)
    with wave.open(str(out_wav), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    log(f"audio: {len(clips)} clips mixed" + (" + music bed" if bed_cfg else ""))
    return True


# --------------------------------------------------------------------- main
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="build a catalogue episode from a recipe")
    ap.add_argument("recipe")
    ap.add_argument("--out", default="")
    ap.add_argument("--stills", default="", help="comma list of scene indices")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--crf", type=int, default=19)
    ap.add_argument("--scene", default="", help="render only these scene indices (comma list)")
    ap.add_argument("--preset", default="medium")
    args = ap.parse_args(argv)

    try:
        cfg = load_recipe(ROOT / args.recipe)
        log(f"{cfg['meta']['title_1']} {cfg['meta']['title_2']} — "
            f"{len(cfg['categories'])} sections, {cfg['meta']['total_items']} items")
        prepare(cfg)
        scenes = build_timeline(cfg)
        total = cfg["_total"]
        log(f"timeline: {len(scenes)} scenes, {timecode(total)} ({total:.1f}s)")
        if args.check:
            log("recipe valid")
            return 0

        if args.scene:
            pick = [int(x) for x in args.scene.split(",")]
            sub = [scenes[i] for i in pick if 0 <= i < len(scenes)]
            out = ROOT / (args.out or f"build/scenes_{args.scene.replace(',', '_')}.mp4")
            out.parent.mkdir(parents=True, exist_ok=True)
            # starts are left absolute so the on-screen timecode keeps running
            render(cfg, sub, out, preset=args.preset, crf=args.crf)
            log(f"chunk → {out.relative_to(ROOT)}")
            return 0

        out = ROOT / (args.out or f"deliverables/{cfg['meta'].get('output', 'EPISODE')}.mp4")

        if args.stills:
            out.parent.mkdir(parents=True, exist_ok=True)
            for idx in [int(x) for x in args.stills.split(",")]:
                sc = scenes[idx]
                for frac in (0.25, 0.85):
                    img = draw_frame(cfg, scenes, sc, sc["dur"] * frac)
                    p = out.parent / f"still_{idx}_{int(frac * 100)}.png"
                    img.convert("RGB").save(p)
                    log(f"still {idx} ({sc['kind']}) → {p.name}")
            return 0

        out.parent.mkdir(parents=True, exist_ok=True)
        pic = ROOT / "build" / "episode_pic.mp4"
        pic.parent.mkdir(parents=True, exist_ok=True)
        log("rendering picture")
        render(cfg, scenes, pic, preset=args.preset, crf=args.crf)

        wav = ROOT / "build" / "episode.wav"
        has_audio = mix_audio(cfg, scenes, wav)
        if has_audio:
            subprocess.run([ffmpeg(), "-y", "-hide_banner", "-loglevel", "error",
                            "-i", str(pic), "-i", str(wav), "-c:v", "copy",
                            "-c:a", "aac", "-b:a", "192k", "-ac", "2", "-shortest",
                            "-movflags", "+faststart", str(out)], check=True)
        else:
            out.write_bytes(pic.read_bytes())
        log(f"done → {out.relative_to(ROOT)} ({out.stat().st_size / 1e6:.0f} MB)")
        return 0
    except RecipeError as exc:
        print(f"\nbuild stopped: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
