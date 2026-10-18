# -*- coding: utf-8 -*-
"""Real Video B-Roll Engine for 'World's Fastest Military Helicopter Explained'.

Provides 100% real 25fps live-action and 3D engineering `.mp4` video B-roll clips
from `heli/assets/broll_clips/` with:
- Zero static photos, zero animated cutouts (`comp:*`), and zero GIFs
- Strictly forward 25fps playback (no reverse ping-pong loops, no artificial wobble)
- Continuous clip-local timestamps across smooth 0.36s cross-dissolves
- Centered cinema framing and fast LUT-based dark HUD color grading.
"""
import functools
import math
import os
import subprocess
from collections import OrderedDict
import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from common import ASSETS, W, H, GRID, clamp

FFMPEG_BIN = imageio_ffmpeg.get_ffmpeg_exe()
BROLL_DIR = os.path.join(ASSETS, "broll_clips")
CLIP_W, CLIP_H = 768, 432
CLIP_FPS = 25.0

_CLIP_CACHE = OrderedDict()
_MAX_CLIP_CACHE = 5


@functools.lru_cache(maxsize=64)
def _grade_lut(contrast=1.08, warmth=0.0, teal=0.25, darken=0.0):
    """Precompute a 768-entry (R, G, B) uint8 lookup table for C-speed Image.point() grading."""
    x = np.linspace(0.0, 1.0, 256, dtype=np.float32)
    c = (x - 0.5) * contrast + 0.5
    sh = np.clip(1.0 - c * 1.6, 0.0, 1.0)
    r = c * (1.0 + warmth * 0.06) - teal * 0.05 * sh
    g = c * (1.0 + teal * 0.01 * sh)
    b = c * (1.0 - warmth * 0.06) + teal * 0.06 * sh
    scale = 1.0 - darken
    r_lut = np.clip(r * scale * 255.0 + 0.5, 0, 255).astype(np.uint8).tolist()
    g_lut = np.clip(g * scale * 255.0 + 0.5, 0, 255).astype(np.uint8).tolist()
    b_lut = np.clip(b * scale * 255.0 + 0.5, 0, 255).astype(np.uint8).tolist()
    return r_lut + g_lut + b_lut


def fast_grade(im, contrast=1.08, warmth=0.0, teal=0.25, darken=0.0):
    lut = _grade_lut(round(contrast, 2), round(warmth, 2), round(teal, 2), round(darken, 2))
    return im.convert("RGB").point(lut)


def _load_real_clip(clip_name):
    """Decode all frames of a 960x540@25fps B-roll .mp4 into an LRU cache via ffmpeg rawvideo."""
    if clip_name.endswith(".mp4"):
        clip_name = clip_name[:-4]
    if clip_name in _CLIP_CACHE:
        _CLIP_CACHE.move_to_end(clip_name)
        return _CLIP_CACHE[clip_name]

    path = os.path.join(BROLL_DIR, f"{clip_name}.mp4")
    if not os.path.exists(path):
        path = os.path.join(BROLL_DIR, "sikorsky_river_dash.mp4")

    cmd = [
        FFMPEG_BIN, "-v", "error", "-i", path,
        "-vf", f"scale={CLIP_W}:{CLIP_H}:flags=bilinear",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-"
    ]
    raw = subprocess.run(cmd, capture_output=True).stdout
    frame_bytes = CLIP_W * CLIP_H * 3
    n_frames = len(raw) // frame_bytes
    if n_frames <= 0:
        arr = np.zeros((25, CLIP_H, CLIP_W, 3), dtype=np.uint8)
    else:
        arr = np.frombuffer(raw[: n_frames * frame_bytes], dtype=np.uint8).reshape((n_frames, CLIP_H, CLIP_W, 3)).copy()

    _CLIP_CACHE[clip_name] = arr
    while len(_CLIP_CACHE) > _MAX_CLIP_CACHE:
        _CLIP_CACHE.popitem(last=False)
    return arr


# ---------------------------------------------------------------------------
# Named Multi-Clip Documentary Reels (100% real .mp4 clips from broll_clips/)
# Also supports explicit "clip_a+clip_b+clip_c" chains per shot in storyboard.py
# ---------------------------------------------------------------------------
BROLL_REELS = {
    # CH-47F Chinook
    "chinook": (
        "chinook_flight_turn",
        "chinook_sunset_approach",
        "chinook_sling_cargo",
        "chinook_fast_rope",
    ),
    "chinook_load": (
        "chinook_sling_cargo",
        "chinook_ground_rotors",
        "chinook_cabin_ramp",
        "chinook_sunset_wide",
    ),
    "chinook_hover": (
        "chinook_sunset_approach",
        "chinook_sunset_flare",
        "chinook_flight_turn",
        "chinook_sunset_land",
    ),
    # AH-64E Apache
    "apache": (
        "apache_headon_taxi",
        "apache_pilot_ihadss",
        "apache_wing_cam",
        "apache_forest_cruise",
    ),
    # Mil Mi-24 / A-10 Hind
    "hind": (
        "hind_highway_low",
        "hind_headon_hover",
        "hind_rocket_salvo",
        "hind_steppe_dash",
    ),
    "hind_attack": (
        "hind_rocket_salvo",
        "hind_overhead_roar",
        "hind_headon_close",
        "mi17_airshow_pass",
    ),
    # Westland G-LYNX / BERP / Record Run
    "lynx_record": (
        "westland_aw109_liftoff",
        "heligo_ocean_dash",
        "benn_cockpit_country",
        "aerounion_fast_cruise",
    ),
    "lynx_speed": (
        "heligo_ocean_dash",
        "westland_aw109_liftoff",
        "benn_cockpit_thames",
        "euro_bk117_bank",
    ),
    "lynx_3d": (
        "rotor_swashplate_hub",
        "rotor_twin_turboshafts",
        "rotor_gearbox_planetary",
        "rotor_intakes_spool",
    ),
    "lynx_naval": (
        "uh60_seahawk_ocean",
        "heligo_ocean_dash",
        "westland_aw109_liftoff",
        "euro_bk117_bank",
    ),
    # Lockheed AH-56 Cheyenne / Compound Gunships
    "cheyenne": (
        "apache_flyby_clouds",
        "uh60_rocket_fire",
        "apache_weapons_pylons",
        "apache_takeoff_hover",
    ),
    # Sikorsky X2 / S-97 Raider / SB-1 Defiant
    "x2": (
        "sikorsky_hangar_rollout",
        "sikorsky_side_profile",
        "sikorsky_cockpit_mfd",
        "sikorsky_forest_bank",
    ),
    "raider": (
        "sikorsky_river_dash",
        "sikorsky_dap_gunship",
        "sikorsky_nose_track",
        "sikorsky_hud_pov",
    ),
    "defiant": (
        "sikorsky_desert_form",
        "sikorsky_troop_assault",
        "sikorsky_sling_hookup",
        "uh60_fastrope_desert",
    ),
    # Eurocopter X3 & Airbus Racer
    "x3": (
        "airbus_alpine_day",
        "airbus_h125_flyby",
        "airbus_ec135_hover",
        "airbus_alpine_night",
    ),
    "racer": (
        "rotor_intakes_spool",
        "airbus_ec135_climb",
        "cabri_composite_flare",
        "airbus_as350_pass",
    ),
    # Bell V-280 Valor / MV-75 Cheyenne II & V-22 Osprey
    "v280_plane": (
        "bell_proprotor_cruise",
        "osprey_deck_takeoff",
        "bell_tiltrotor_hover",
        "osprey_deck_landing",
    ),
    "v280_hover": (
        "bell_tiltrotor_hover",
        "osprey_deck_landing",
        "bell_proprotor_cruise",
        "osprey_carrier_fleet",
    ),
    "valor_cruise": (
        "bell_proprotor_cruise",
        "osprey_deck_takeoff",
        "bell_tiltrotor_hover",
        "osprey_cabin_escort",
    ),
    "osprey": (
        "osprey_deck_landing",
        "osprey_deck_takeoff",
        "osprey_carrier_fleet",
        "osprey_cabin_escort",
    ),
}


def _resolve_reel(spec_or_key):
    """Resolve a reel key, '+'-joined clip chain, or single clip name into a tuple of clip names."""
    if isinstance(spec_or_key, (list, tuple)):
        out = []
        for item in spec_or_key:
            out.extend(_resolve_reel(item))
        return tuple(out) if out else BROLL_REELS["raider"]

    if not spec_or_key:
        return BROLL_REELS["raider"]

    s = str(spec_or_key).strip()
    if s.startswith("comp:"):
        s = s.split(":")[1]

    if "+" in s:
        parts = tuple(p.strip().split(":")[0] for p in s.split("+") if p.strip())
        if parts:
            return parts

    s_clean = s.split(":")[0]
    if s_clean in BROLL_REELS:
        return BROLL_REELS[s_clean]
    if os.path.exists(os.path.join(BROLL_DIR, f"{s_clean}.mp4")):
        return (s_clean,)
    return BROLL_REELS["raider"]


def _sample_clip_native(clip_name, t_clip):
    """Sample a 960x540 PIL Image from `clip_name` at clip-local time `t_clip` (strictly forward)."""
    frames = _load_real_clip(clip_name)
    n = frames.shape[0]
    if n <= 1:
        return Image.fromarray(frames[0])

    max_idx = n - 1
    pos = max(0.0, float(t_clip)) * CLIP_FPS
    if pos >= max_idx:
        pos = pos % max_idx
    f0 = int(math.floor(pos))
    f1 = min(max_idx, f0 + 1)
    frac = pos - f0
    if frac < 0.04 or f0 == f1:
        return Image.fromarray(frames[f0])
    im0 = Image.fromarray(frames[f0])
    im1 = Image.fromarray(frames[f1])
    return Image.blend(im0, im1, frac)


@functools.lru_cache(maxsize=8)
def _blurred_bg_cached(reel_tuple, tick_12fps, out, contrast, warmth, teal, darken, blur):
    t = tick_12fps / 12.5
    cut_period = 4.4
    pos = max(0.0, t) / cut_period
    m = int(math.floor(pos))
    t_clip = (pos - m) * cut_period
    im = _sample_clip_native(reel_tuple[m % len(reel_tuple)], t_clip)
    im = fast_grade(im, contrast=contrast, warmth=warmth, teal=teal, darken=darken)
    im = im.filter(ImageFilter.GaussianBlur(max(2.0, blur * 1.1)))
    if im.size != out:
        im = im.resize(out, Image.Resampling.BILINEAR)
    return im


def broll_view(spec_or_key, t, cx=0.5, cy=0.5, zoom=1.0, out=(W, H),
               contrast=1.08, sat=1.06, warmth=0.0, teal=0.25, darken=0.0, blur=0, cut_period=4.4):
    """Render a 25fps real-video B-roll frame for any reel key, '+' clip chain, or single clip name."""
    reel = _resolve_reel(spec_or_key)

    if blur >= 3:
        return _blurred_bg_cached(
            reel, int(max(0.0, float(t)) * 12.5), out,
            round(contrast, 2), round(warmth, 2), round(teal, 2), round(darken, 2), int(blur)
        ).copy()

    t_pos = max(0.0, float(t))
    if len(reel) == 1:
        im = _sample_clip_native(reel[0], t_pos)
    else:
        fade_sec = 0.36
        fade_frac = fade_sec / cut_period
        pos = t_pos / cut_period
        m = int(math.floor(pos))
        frac = pos - m
        clip_curr = reel[m % len(reel)]
        # Continuous clip-local time: clip m starts at 0.0s when its fade-in begins
        t_curr = (pos * cut_period) if m == 0 else ((frac + fade_frac) * cut_period)
        im = _sample_clip_native(clip_curr, t_curr)
        if frac > (1.0 - fade_frac):
            clip_next = reel[(m + 1) % len(reel)]
            alpha = (frac - (1.0 - fade_frac)) / fade_frac
            t_next = (frac - (1.0 - fade_frac)) * cut_period
            nxt_im = _sample_clip_native(clip_next, t_next)
            im = Image.blend(im, nxt_im, clamp(alpha, 0.0, 1.0))

    # Gentle, centered cinema crop at native 960x540 before scaling to `out`
    iw, ih = im.size
    tw, th = out
    target_aspect = tw / max(1, th)
    src_aspect = iw / max(1, ih)
    if src_aspect > target_aspect:
        base_h = float(ih)
        base_w = base_h * target_aspect
    else:
        base_w = float(iw)
        base_h = base_w / target_aspect

    z_eff = 1.0 + clamp((float(zoom) - 1.0) * 0.18, 0.01, 0.10)
    sw, sh = base_w / z_eff, base_h / z_eff
    cx_eff = 0.5 + clamp((float(cx) - 0.5) * 0.20, -0.05, 0.05)
    cy_eff = 0.5 + clamp((float(cy) - 0.5) * 0.20, -0.05, 0.05)
    x0 = int(clamp(cx_eff * iw - sw * 0.5, 0.0, max(0.0, iw - sw)))
    y0 = int(clamp(cy_eff * ih - sh * 0.5, 0.0, max(0.0, ih - sh)))
    im = im.crop((x0, y0, int(x0 + sw), int(y0 + sh)))

    im = fast_grade(im, contrast=contrast, warmth=warmth, teal=teal, darken=darken)
    if blur > 0:
        im = im.filter(ImageFilter.BoxBlur(max(1.0, blur * 0.5)))
    if im.size != out:
        im = im.resize(out, Image.Resampling.BILINEAR)
    return im


@functools.lru_cache(maxsize=2)
def grid_overlay_cached(size=(W, H), step=60):
    """Translucent HUD blueprint grid overlay to composite over darkened moving B-roll."""
    w, h = size
    im = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for x in range(0, w, step):
        d.line([(x, 0), (x, h)], fill=GRID + (34 if x % (step * 4) else 64,), width=1)
    for y in range(0, h, step):
        d.line([(0, y), (w, y)], fill=GRID + (34 if y % (step * 4) else 64,), width=1)
    return im


def hud_broll_bg(reel_key, t, darken=0.78, blur=8):
    """Render a darkened, cool-teal HUD-graded moving B-roll background with blueprint grid overlay."""
    im = broll_view(reel_key, t, contrast=1.10, sat=0.85, teal=0.55, darken=darken, blur=blur).convert("RGBA")
    im.alpha_composite(grid_overlay_cached())
    return im
