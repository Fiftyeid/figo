# -*- coding: utf-8 -*-
"""Moving Aircraft B-Roll Engine for 'World's Fastest Military Helicopter Explained'.

Provides continuous 25fps moving aircraft footage with ZERO static photos:
1. Real live-action military rotorcraft video clips (`heli/assets/broll_clips/real_*.mp4`),
   decoded via ffmpeg with smooth ping-pong looping and camera tracking drift.
2. Multi-plane 25fps air-to-air chase-plane composites (`comp:*`) for experimental
   high-speed prototypes and specific camera angles (G-LYNX, AH-56 Cheyenne,
   Sikorsky X2, Eurocopter X3, SB-1 Defiant, Airbus Racer, Bell V-280 Valor / MV-75,
   CH-47F Chinook, Mi-24 / A-10 Hind, S-97 Raider) combining:
   - Parallax-scrolling 3840x1080 aerial terrain/cloud plates
   - Pre-despilled RGBA aircraft cutouts with aerodynamic pitch/bob dynamics
   - 25fps shutter-blurred spinning main/coaxial/tandem rotors & pusher/tractor props
   - Turbine exhaust heat plume, high-speed cloud wisps, and anti-collision strobes.
3. Multi-angle B-Roll Reels (`BROLL_REELS`) that automatically cut between distinct
   camera angles and live-action clips every ~3.8 seconds so no shot ever lingers
   on a single static angle.
"""
import functools
import math
import os
import re
import subprocess
from collections import OrderedDict
import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from common import ASSETS, W, H, BG0, BG1, GRID, clamp, lerp


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


@functools.lru_cache(maxsize=1)
def _wisp_sprite():
    im = Image.new("RGBA", (560, 76), (0, 0, 0, 0))
    ImageDraw.Draw(im, "RGBA").ellipse((0, 0, 560, 76), fill=(235, 242, 250, 16))
    return im

FFMPEG_BIN = imageio_ffmpeg.get_ffmpeg_exe()
BROLL_DIR = os.path.join(ASSETS, "broll_clips")
CUTOUT_DIR = os.path.join(ASSETS, "cutouts")
PLATE_DIR = os.path.join(ASSETS, "plates")

_CLIP_CACHE = OrderedDict()
_MAX_CLIP_CACHE = 10
_CUTOUT_CACHE = {}
_PLATE_CACHE = {}


def _load_real_clip(clip_name):
    """Load all frames of a compact real B-roll mp4 into an LRU cache via ffmpeg rawvideo."""
    if not clip_name.endswith(".mp4"):
        clip_name = clip_name + ".mp4"
    if clip_name in _CLIP_CACHE:
        _CLIP_CACHE.move_to_end(clip_name)
        return _CLIP_CACHE[clip_name]
    path = os.path.join(BROLL_DIR, clip_name)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Missing B-roll clip: {path}")
    probe = subprocess.run([FFMPEG_BIN, "-i", path], capture_output=True, text=True)
    m = re.search(r"Stream #0:\d+.*Video:.* (\d{2,4})x(\d{2,4})", probe.stderr)
    cw, ch = (int(m.group(1)), int(m.group(2))) if m else (640, 360)
    cmd = [
        FFMPEG_BIN, "-v", "error", "-i", path,
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-"
    ]
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    frame_bytes = cw * ch * 3
    n_frames = len(raw) // frame_bytes
    if n_frames <= 0:
        raise RuntimeError(f"Empty B-roll clip: {path}")
    arr = np.frombuffer(raw[: n_frames * frame_bytes], dtype=np.uint8).reshape((n_frames, ch, cw, 3))
    frames = [arr[i] for i in range(n_frames)]
    _CLIP_CACHE[clip_name] = frames
    if len(_CLIP_CACHE) > _MAX_CLIP_CACHE:
        _CLIP_CACHE.popitem(last=False)
    return frames


def _load_cutout(name):
    """Load pre-despilled 1408x768 RGBA cutout."""
    if name not in _CUTOUT_CACHE:
        p = os.path.join(CUTOUT_DIR, f"{name}.webp")
        if not os.path.exists(p):
            p = os.path.join(CUTOUT_DIR, f"{name}.png")
        _CUTOUT_CACHE[name] = Image.open(p).convert("RGBA")
    return _CUTOUT_CACHE[name]


def _load_plate(name):
    """Load 3840x1080 seamless panoramic background plate."""
    if name not in _PLATE_CACHE:
        p = os.path.join(PLATE_DIR, f"{name}.jpg")
        _PLATE_CACHE[name] = Image.open(p).convert("RGB")
    return _PLATE_CACHE[name]


# ---------------------------------------------------------------------------
# Aircraft composite definitions (1408x768 cutout coordinates & rotor specs)
# ---------------------------------------------------------------------------
COMP_SPECS = {
    "glynx": {
        "cutout": "glynx_body",
        "plate": "somerset_sunset",
        "dir": -1,
        "scroll_speed": 230.0,
        "scale": 0.96,
        "base_pos": (960, 545),
        "pitch_deg": -1.5,
        "main_rotors": [
            {"hub": (645, 160), "mast_bottom": (648, 222), "radius": 470, "tilt": 0.095,
             "blades": 4, "omega": 20.5, "dir": 1, "berp": True, "color": (210, 220, 232)},
        ],
        "props": [
            {"hub": (1280, 240), "rx": 28, "ry": 95, "blades": 4, "omega": 38.0, "dir": 1,
             "color": (215, 225, 235), "tip_color": (245, 198, 52)},
        ],
        "exhaust": (795, 250, 1),
        "strobe": (1295, 168),
    },
    "cheyenne": {
        "cutout": "cheyenne_body",
        "plate": "desert_mountains",
        "dir": -1,
        "scroll_speed": 205.0,
        "scale": 0.94,
        "base_pos": (960, 542),
        "pitch_deg": -1.2,
        "main_rotors": [
            {"hub": (680, 198), "mast_bottom": (680, 262), "radius": 460, "tilt": 0.09,
             "blades": 4, "omega": 18.0, "dir": 1, "berp": False, "color": (205, 212, 198)},
        ],
        "props": [
            {"hub": (1222, 495), "rx": 32, "ry": 86, "blades": 4, "omega": 36.0, "dir": 1,
             "color": (210, 215, 220), "tip_color": (240, 200, 60)},
            {"hub": (1298, 355), "rx": 38, "ry": 122, "blades": 3, "omega": 44.0, "dir": -1,
             "color": (225, 230, 238), "tip_color": (245, 92, 92)},
        ],
        "exhaust": (855, 290, 1),
        "strobe": (1262, 270),
    },
    "x2": {
        "cutout": "x2_body",
        "plate": "clouds_high",
        "dir": -1,
        "scroll_speed": 245.0,
        "scale": 0.95,
        "base_pos": (960, 550),
        "pitch_deg": -1.5,
        "main_rotors": [
            {"hub": (645, 185), "mast_bottom": (645, 248), "radius": 435, "tilt": 0.088,
             "blades": 4, "omega": 21.5, "dir": 1, "berp": False, "color": (220, 228, 240)},
            {"hub": (645, 92), "mast_bottom": (645, 185), "radius": 435, "tilt": 0.088,
             "blades": 4, "omega": 21.5, "dir": -1, "berp": False, "color": (230, 236, 248)},
        ],
        "props": [
            {"hub": (1225, 392), "rx": 36, "ry": 128, "blades": 6, "omega": 48.0, "dir": 1,
             "color": (225, 235, 245), "tip_color": (56, 198, 244)},
        ],
        "exhaust": (740, 275, 1),
        "strobe": (1192, 260),
    },
    "x3": {
        "cutout": "x3_body",
        "plate": "clouds_cumulus",
        "dir": -1,
        "scroll_speed": 250.0,
        "scale": 0.95,
        "base_pos": (960, 542),
        "pitch_deg": -1.6,
        "main_rotors": [
            {"hub": (652, 92), "mast_bottom": (652, 165), "radius": 455, "tilt": 0.095,
             "blades": 5, "omega": 20.5, "dir": 1, "berp": False, "color": (215, 225, 238)},
        ],
        "props": [
            {"hub": (410, 415), "rx": 46, "ry": 115, "blades": 5, "omega": 46.0, "dir": 1,
             "color": (225, 232, 242), "tip_color": (56, 198, 244)},
            {"hub": (910, 468), "rx": 42, "ry": 105, "blades": 5, "omega": 46.0, "dir": -1,
             "color": (225, 232, 242), "tip_color": (56, 198, 244)},
        ],
        "exhaust": (795, 240, 1),
        "strobe": (1278, 270),
    },
    "defiant": {
        "cutout": "defiant_body",
        "plate": "desert_valley",
        "dir": -1,
        "scroll_speed": 235.0,
        "scale": 0.95,
        "base_pos": (960, 545),
        "pitch_deg": -1.3,
        "main_rotors": [
            {"hub": (630, 178), "mast_bottom": (630, 250), "radius": 465, "tilt": 0.09,
             "blades": 4, "omega": 21.0, "dir": 1, "berp": False, "color": (195, 205, 192)},
            {"hub": (630, 88), "mast_bottom": (630, 178), "radius": 465, "tilt": 0.09,
             "blades": 4, "omega": 21.0, "dir": -1, "berp": False, "color": (205, 215, 202)},
        ],
        "props": [
            {"hub": (1318, 422), "rx": 36, "ry": 135, "blades": 8, "omega": 46.0, "dir": 1,
             "color": (210, 218, 224), "tip_color": (245, 198, 52)},
        ],
        "exhaust": (925, 295, 1),
        "strobe": (1265, 240),
    },
    "racer": {
        "cutout": "racer_body",
        "plate": "clouds_horizon",
        "dir": 1,
        "scroll_speed": 240.0,
        "scale": 0.94,
        "base_pos": (960, 542),
        "pitch_deg": 1.3,
        "main_rotors": [
            {"hub": (618, 130), "mast_bottom": (618, 195), "radius": 455, "tilt": 0.095,
             "blades": 5, "omega": 20.5, "dir": 1, "berp": False, "color": (215, 225, 238)},
        ],
        "props": [
            {"hub": (122, 370), "rx": 35, "ry": 98, "blades": 6, "omega": 45.0, "dir": 1,
             "color": (220, 230, 242), "tip_color": (56, 198, 244)},
            {"hub": (1048, 536), "rx": 35, "ry": 98, "blades": 6, "omega": 45.0, "dir": -1,
             "color": (220, 230, 242), "tip_color": (56, 198, 244)},
        ],
        "exhaust": (475, 250, -1),
        "strobe": (125, 250),
    },
    "v280": {
        "cutout": "v280_body",
        "plate": "desert_mountains",
        "dir": -1,
        "scroll_speed": 270.0,
        "scale": 0.95,
        "base_pos": (960, 542),
        "pitch_deg": -1.2,
        "main_rotors": [],
        "props": [
            {"hub": (92, 292), "rx": 88, "ry": 265, "blades": 3, "omega": 35.0, "dir": 1,
             "color": (215, 222, 228), "tip_color": (245, 198, 52)},
            {"hub": (1092, 272), "rx": 88, "ry": 265, "blades": 3, "omega": 35.0, "dir": -1,
             "color": (215, 222, 228), "tip_color": (245, 198, 52)},
        ],
        "exhaust": (580, 315, 1),
        "strobe": (1188, 260),
    },
    "chinook": {
        "cutout": "chinook_body",
        "plate": "desert_valley",
        "dir": -1,
        "scroll_speed": 190.0,
        "scale": 0.94,
        "base_pos": (960, 548),
        "pitch_deg": -1.8,
        "main_rotors": [
            {"hub": (315, 208), "mast_bottom": (315, 255), "radius": 420, "tilt": 0.095,
             "blades": 3, "omega": 18.5, "dir": 1, "berp": False, "color": (205, 212, 198)},
            {"hub": (1122, 118), "mast_bottom": (1122, 175), "radius": 420, "tilt": 0.095,
             "blades": 3, "omega": 18.5, "dir": -1, "berp": False, "color": (205, 212, 198)},
        ],
        "props": [],
        "exhaust": (1195, 315, 1),
        "strobe": (1135, 195),
    },
    "hind": {
        "cutout": "hind_body",
        "plate": "steppe_hills",
        "dir": -1,
        "scroll_speed": 215.0,
        "scale": 0.95,
        "base_pos": (960, 545),
        "pitch_deg": -1.6,
        "main_rotors": [
            {"hub": (632, 126), "mast_bottom": (632, 198), "radius": 465, "tilt": 0.095,
             "blades": 5, "omega": 19.0, "dir": 1, "berp": False, "color": (208, 215, 202)},
        ],
        "props": [
            {"hub": (1268, 250), "rx": 34, "ry": 112, "blades": 3, "omega": 39.0, "dir": 1,
             "color": (215, 220, 225), "tip_color": (245, 92, 92)},
        ],
        "exhaust": (715, 275, 1),
        "strobe": (1245, 175),
    },
    "s97": {
        "cutout": "s97_body",
        "plate": "somerset_fields",
        "dir": -1,
        "scroll_speed": 240.0,
        "scale": 0.95,
        "base_pos": (960, 545),
        "pitch_deg": -1.4,
        "main_rotors": [
            {"hub": (675, 208), "mast_bottom": (675, 272), "radius": 445, "tilt": 0.088,
             "blades": 4, "omega": 21.5, "dir": 1, "berp": False, "color": (205, 212, 220)},
            {"hub": (675, 115), "mast_bottom": (675, 208), "radius": 445, "tilt": 0.088,
             "blades": 4, "omega": 21.5, "dir": -1, "berp": False, "color": (215, 222, 230)},
        ],
        "props": [
            {"hub": (1318, 422), "rx": 34, "ry": 118, "blades": 6, "omega": 46.0, "dir": 1,
             "color": (220, 228, 236), "tip_color": (245, 198, 52)},
        ],
        "exhaust": (870, 320, 1),
        "strobe": (1262, 290),
    },
}

# Framing presets (camera crop window inside the 1920x1080 composite canvas)
CAM_VIEWS = {
    "wide":    (0.00, 0.00, 1.00, 1.00),
    "chase":   (0.04, 0.05, 0.90, 0.90),
    "nose":    (0.02, 0.10, 0.74, 0.74),
    "rotor":   (0.10, 0.02, 0.76, 0.76),
    "tail":    (0.22, 0.08, 0.74, 0.74),
    "lowpass": (0.03, 0.04, 0.86, 0.86),
    "climb":   (0.06, 0.02, 0.84, 0.84),
}

# Curated multi-angle B-Roll Reels for every aircraft / storyline key.
# Every 3.8s, shots automatically advance to the next camera angle / live-action clip!
BROLL_REELS = {
    "lynx_record": [
        "comp:glynx:wide:somerset_sunset",
        "comp:glynx:rotor:somerset_sunset",
        "real_cockpit_pov:wide",
        "comp:glynx:chase:somerset_fields",
        "comp:glynx:nose:clouds_horizon",
        "real_nh90_bank:wide",
        "comp:glynx:tail:somerset_sunset",
        "real_nh90_tarmac:wide",
    ],
    "museum": [
        "comp:glynx:chase:somerset_sunset",
        "real_cockpit_pov:wide",
        "comp:glynx:wide:clouds_horizon",
        "real_tiger_duo:wide",
        "comp:glynx:rotor:somerset_fields",
    ],
    "chinook": [
        "real_chinook_lowpass:wide",
        "real_chinook_takeoff:wide",
        "comp:chinook:wide:desert_valley",
        "real_chinook_wheelie:wide",
        "real_chinook_sling:wide",
        "real_chinook_tarmac:wide",
        "real_chinook_flares:wide",
        "real_troops_exit:wide",
        "real_chinook_headon:wide",
    ],
    "hind": [
        "real_hind_lowpass:wide",
        "real_hind_rockets:wide",
        "comp:hind:wide:steppe_hills",
        "real_hind_clouds:wide",
        "real_hind_formation:wide",
        "real_hind_highway:wide",
        "comp:hind:chase:clouds_high",
        "comp:hind:rotor:steppe_hills",
    ],
    "cheyenne": [
        "comp:cheyenne:wide:desert_mountains",
        "comp:cheyenne:tail:desert_valley",
        "real_apache_low:wide",
        "comp:cheyenne:nose:desert_mountains",
        "real_apache_tads:wide",
        "comp:cheyenne:chase:clouds_horizon",
    ],
    "x2": [
        "comp:x2:wide:clouds_high",
        "real_coaxial_hover:wide",
        "comp:x2:rotor:clouds_high",
        "comp:x3:wide:clouds_cumulus",
        "real_coaxial_bank:wide",
        "comp:s97:wide:somerset_fields",
        "comp:x3:nose:clouds_cumulus",
    ],
    "defiant": [
        "comp:defiant:wide:desert_valley",
        "real_coaxial_hover:wide",
        "comp:defiant:tail:desert_valley",
        "comp:s97:wide:somerset_fields",
        "comp:defiant:rotor:desert_mountains",
        "real_blackhawk_smoke:wide",
        " real_coaxial_bank:wide".strip(),
    ],
    "racer": [
        "comp:racer:wide:clouds_horizon",
        "real_airbus_snow:wide",
        "comp:racer:nose:clouds_cumulus",
        "comp:x3:wide:clouds_cumulus",
        "real_tiger_duo:wide",
        "comp:racer:chase:clouds_horizon",
    ],
    "v280_plane": [
        "comp:v280:wide:desert_mountains",
        "real_tiltrotor_fly:wide",
        "comp:v280:chase:clouds_horizon",
        "real_tiltrotor_nacelle:wide",
        "comp:v280:nose:desert_valley",
        "real_blackhawk_ocean:wide",
    ],
    "v280_heli": [
        "real_tiltrotor_fly:wide",
        "comp:v280:chase:clouds_horizon",
        "real_tiltrotor_nacelle:wide",
        "comp:v280:wide:desert_mountains",
        "real_blackhawk_flyby:wide",
        "real_heli_dust:wide",
    ],
}


def _draw_horizontal_rotor(draw, hub, mast_bottom, radius, tilt, blades, omega, direction, t, berp=False, color=(215, 225, 235)):
    """Draw a 25fps motion-blurred horizontal rotor disc + mast on an RGBA ImageDraw."""
    hx, hy = int(hub[0]), int(hub[1])
    mx, my = int(mast_bottom[0]), int(mast_bottom[1])
    draw.line([(hx, hy), (mx, my)], fill=(68, 76, 86, 255), width=14)
    draw.line([(hx - 3, hy), (mx - 3, my)], fill=(120, 132, 145, 230), width=4)

    rx = int(radius)
    ry = max(14, int(radius * tilt))

    draw.ellipse((hx - rx, hy - ry, hx + rx, hy + ry), outline=(color[0], color[1], color[2], 55), width=3)
    if berp:
        draw.ellipse((hx - rx - 4, hy - ry - 1, hx + rx + 4, hy + ry + 1), outline=(245, 198, 52, 85), width=4)

    draw.ellipse((hx - int(rx * 0.92), hy - int(ry * 0.92), hx + int(rx * 0.92), hy + int(ry * 0.92)),
                 fill=(color[0], color[1], color[2], 18))

    base_angle = t * omega * direction
    n_sub = 7
    shutter_span = 0.46 * direction
    for b in range(blades):
        theta0 = base_angle + (2.0 * math.pi * b) / blades
        fan_pts = [(hx, hy)]
        for s in range(n_sub + 1):
            th = theta0 + shutter_span * (s / n_sub - 0.5)
            px = hx + rx * math.cos(th)
            py = hy + ry * math.sin(th)
            fan_pts.append((px, py))
        draw.polygon(fan_pts, fill=(color[0], color[1], color[2], 42))

        th_mid = theta0
        px = hx + rx * math.cos(th_mid)
        py = hy + ry * math.sin(th_mid)
        draw.line([(hx, hy), (px, py)], fill=(38, 44, 52, 185), width=6)
        draw.line([(hx, hy), (px, py)], fill=(245, 250, 255, 150), width=2)

        tx0 = hx + (rx * 0.88) * math.cos(th_mid)
        ty0 = hy + (ry * 0.88) * math.sin(th_mid)
        tip_col = (245, 198, 52, 220) if berp else (235, 240, 248, 180)
        draw.line([(tx0, ty0), (px, py)], fill=tip_col, width=7 if berp else 5)

    draw.ellipse((hx - 28, hy - 11, hx + 28, hy + 11), fill=(48, 54, 64, 255), outline=(135, 148, 162, 255), width=2)
    draw.ellipse((hx - 14, hy - 6, hx + 14, hy + 6), fill=(88, 98, 112, 255))


def _draw_prop_disc(draw, hub, rx, ry, blades, omega, direction, t, color=(220, 230, 242), tip_color=(245, 198, 52)):
    """Draw a 25fps motion-blurred vertical/tilted propeller or tail rotor disc."""
    hx, hy = int(hub[0]), int(hub[1])
    draw.ellipse((hx - rx, hy - ry, hx + rx, hy + ry),
                 fill=(color[0], color[1], color[2], 24),
                 outline=(tip_color[0], tip_color[1], tip_color[2], 90), width=3)

    base_angle = t * omega * direction
    n_sub = 6
    shutter_span = 0.52 * direction
    for b in range(blades):
        theta0 = base_angle + (2.0 * math.pi * b) / blades
        fan_pts = [(hx, hy)]
        for s in range(n_sub + 1):
            th = theta0 + shutter_span * (s / n_sub - 0.5)
            px = hx + rx * math.cos(th)
            py = hy + ry * math.sin(th)
            fan_pts.append((px, py))
        draw.polygon(fan_pts, fill=(color[0], color[1], color[2], 52))

        px = hx + rx * math.cos(theta0)
        py = hy + ry * math.sin(theta0)
        draw.line([(hx, hy), (px, py)], fill=(45, 52, 60, 175), width=4)
        draw.line([(hx, hy), (px, py)], fill=(248, 252, 255, 155), width=2)
        tx0 = hx + (rx * 0.85) * math.cos(theta0)
        ty0 = hy + (ry * 0.85) * math.sin(theta0)
        draw.line([(tx0, ty0), (px, py)], fill=(tip_color[0], tip_color[1], tip_color[2], 215), width=5)

    srx = max(7, int(rx * 0.20))
    sry = max(9, int(ry * 0.13))
    draw.ellipse((hx - srx, hy - sry, hx + srx, hy + sry),
                 fill=(55, 62, 72, 255), outline=(160, 172, 185, 255), width=2)


@functools.lru_cache(maxsize=32)
def _prepared_body(comp_id):
    """Return the pre-tilted cutout for `comp_id` so we don't call .rotate() on 1408x768 every frame."""
    spec = COMP_SPECS[comp_id]
    cutout = _load_cutout(spec["cutout"])
    return cutout.rotate(spec["pitch_deg"], resample=Image.Resampling.BICUBIC, expand=False)


def _render_comp_frame(comp_id, cam="wide", plate_override=None, t=0.0, size=(W, H)):
    """Render a single 25fps frame of a multi-plane aircraft chase-plane composite."""
    spec = COMP_SPECS[comp_id]
    plate_name = plate_override or spec["plate"]
    plate = _load_plate(plate_name)
    pw, ph = plate.size

    scroll_dir = spec["dir"]
    x_off = int((t * spec["scroll_speed"] * (-scroll_dir)) % pw)
    if x_off + W <= pw:
        bg = plate.crop((x_off, 0, x_off + W, H)).copy()
    else:
        w1 = pw - x_off
        bg = Image.new("RGB", (W, H))
        bg.paste(plate.crop((x_off, 0, pw, H)), (0, 0))
        bg.paste(plate.crop((0, 0, W - w1, H)), (w1, 0))

    body_im = _prepared_body(comp_id)
    ac_layer = body_im.copy()
    draw_over = ImageDraw.Draw(ac_layer, "RGBA")

    if spec.get("exhaust"):
        ex, ey, edir = spec["exhaust"]
        for k in range(1, 6):
            wob = math.sin(t * 28.0 + k * 1.3) * (3.5 * k)
            px = ex + edir * k * 28
            py = ey + wob
            rad_x = 18 + k * 14
            rad_y = 9 + k * 5
            draw_over.ellipse((px - rad_x, py - rad_y, px + rad_x, py + rad_y),
                              fill=(255, 195, 130, max(6, 30 - k * 5)))

    for mr in spec["main_rotors"]:
        _draw_horizontal_rotor(
            draw_over,
            hub=mr["hub"],
            mast_bottom=mr["mast_bottom"],
            radius=mr["radius"],
            tilt=mr["tilt"],
            blades=mr["blades"],
            omega=mr["omega"],
            direction=mr["dir"],
            t=t,
            berp=mr.get("berp", False),
            color=mr.get("color", (215, 225, 235)),
        )

    for pr in spec["props"]:
        _draw_prop_disc(
            draw_over,
            hub=pr["hub"],
            rx=pr["rx"],
            ry=pr["ry"],
            blades=pr["blades"],
            omega=pr["omega"],
            direction=pr["dir"],
            t=t,
            color=pr.get("color", (220, 230, 242)),
            tip_color=pr.get("tip_color", (245, 198, 52)),
        )

    if spec.get("strobe"):
        sx, sy = spec["strobe"]
        phase = (t * 1.15) % 1.0
        if phase < 0.09 or (0.18 < phase < 0.25):
            draw_over.ellipse((sx - 26, sy - 26, sx + 26, sy + 26), fill=(255, 70, 55, 95))
            draw_over.ellipse((sx - 12, sy - 12, sx + 12, sy + 12), fill=(255, 180, 160, 210))
            draw_over.ellipse((sx - 5, sy - 5, sx + 5, sy + 5), fill=(255, 255, 255, 255))

    tw_out, th_out = size
    target_aspect = tw_out / max(1, th_out)
    aspect_scale = 1.0 if target_aspect >= 1.45 else clamp(0.58 + 0.28 * target_aspect, 0.66, 0.92)
    scale = spec["scale"] * aspect_scale
    if abs(scale - 1.0) > 0.03:
        tw = int(ac_layer.size[0] * scale)
        th = int(ac_layer.size[1] * scale)
        ac_final = ac_layer.resize((tw, th), Image.Resampling.BILINEAR)
    else:
        tw, th = ac_layer.size
        ac_final = ac_layer

    bx, by = spec["base_pos"]
    dx = int(16.0 * math.sin(t * 1.65) + 6.0 * math.cos(t * 3.1))
    dy = int(11.0 * math.sin(t * 2.15 + 0.7))
    paste_x = bx - tw // 2 + dx
    paste_y = by - th // 2 + dy

    canvas = bg
    canvas.paste(ac_final, (paste_x, paste_y), ac_final)

    wisp = _wisp_sprite()
    for w_idx in range(3):
        wx = int(((t * spec["scroll_speed"] * 2.4 * (-scroll_dir)) + w_idx * 780) % (W + 700)) - 350
        wy = 160 + w_idx * 310 + int(18 * math.sin(t + w_idx))
        canvas.paste(wisp, (wx - 280, wy - 38), wisp)

    out_rgb = canvas

    src_aspect = W / H
    if src_aspect > target_aspect:
        base_h = H
        base_w = H * target_aspect
    else:
        base_w = W
        base_h = W / target_aspect

    cx0, cy0, cw_frac, ch_frac = CAM_VIEWS.get(cam, CAM_VIEWS["wide"])
    win_w = base_w * cw_frac
    win_h = base_h * ch_frac
    drift_x = 0.012 * math.sin(t * 1.35) * W
    drift_y = 0.010 * math.cos(t * 1.75) * H
    center_x = (cx0 + cw_frac * 0.5) * W + drift_x
    center_y = (cy0 + ch_frac * 0.5) * H + drift_y
    x0 = clamp(center_x - win_w * 0.5, 0.0, max(0.0, W - win_w))
    y0 = clamp(center_y - win_h * 0.5, 0.0, max(0.0, H - win_h))
    if cw_frac < 0.999 or ch_frac < 0.999 or size != (W, H):
        out_rgb = out_rgb.crop((int(x0), int(y0), int(x0 + win_w), int(y0 + win_h))).resize(size, Image.Resampling.BILINEAR)
    return out_rgb


def _render_real_clip_frame(clip_name, cam="wide", t=0.0, size=(W, H), speed=1.0):
    """Render a 25fps frame from a real live-action B-roll mp4 with smooth ping-pong looping."""
    frames = _load_real_clip(clip_name)
    n = len(frames)
    if n == 1:
        arr = frames[0]
    else:
        cycle = 2 * (n - 1)
        pos = (t * 25.0 * speed) % cycle
        idx0 = int(math.floor(pos))
        frac = pos - idx0
        idx1 = (idx0 + 1) % cycle
        f0 = idx0 if idx0 < n else cycle - idx0
        f1 = idx1 if idx1 < n else cycle - idx1
        if frac < 1e-3 or f0 == f1:
            arr = frames[f0]
        else:
            arr = ((1.0 - frac) * frames[f0].astype(np.float32) + frac * frames[f1].astype(np.float32)).astype(np.uint8)

    im = Image.fromarray(arr)
    iw, ih = im.size

    tw, th = size
    target_aspect = tw / max(1, th)
    src_aspect = iw / max(1, ih)
    if src_aspect > target_aspect:
        base_h = ih
        base_w = ih * target_aspect
    else:
        base_w = iw
        base_h = iw / target_aspect

    cx0, cy0, cw_frac, ch_frac = CAM_VIEWS.get(cam, CAM_VIEWS["wide"])
    if cam == "wide":
        cw_frac, ch_frac = 0.93, 0.93
    win_w = base_w * cw_frac
    win_h = base_h * ch_frac
    drift_x = 0.022 * math.sin(t * 1.15) * (iw - win_w)
    drift_y = 0.018 * math.cos(t * 1.45) * (ih - win_h)
    x0 = clamp((iw - win_w) * 0.5 + drift_x, 0.0, max(0.0, iw - win_w))
    y0 = clamp((ih - win_h) * 0.5 + drift_y, 0.0, max(0.0, ih - win_h))
    cropped = im.crop((int(x0), int(y0), int(x0 + win_w), int(y0 + win_h))).resize(size, Image.Resampling.BILINEAR)
    return cropped


def _render_single_spec(spec_str, t, size=(W, H)):
    """Render a single clip spec ('comp:...' or 'real_...')."""
    if spec_str.startswith("comp:"):
        parts = spec_str.split(":")
        comp_id = parts[1]
        cam = parts[2] if len(parts) > 2 and parts[2] else "wide"
        plate_override = parts[3] if len(parts) > 3 and parts[3] else None
        return _render_comp_frame(comp_id, cam=cam, plate_override=plate_override, t=t, size=size)
    parts = spec_str.split(":")
    clip_name = parts[0]
    cam = parts[1] if len(parts) > 1 and parts[1] else "wide"
    return _render_real_clip_frame(clip_name, cam=cam, t=t, size=size)


@functools.lru_cache(maxsize=6)
def _blurred_bg_cached(reel_tuple, tick_12fps, out, contrast, warmth, teal, darken, blur):
    t = tick_12fps / 12.5
    render_size = (max(160, out[0] // 2), max(90, out[1] // 2))
    if len(reel_tuple) == 1:
        im = _render_single_spec(reel_tuple[0], t, size=render_size)
    else:
        idx = int(math.floor(t / 3.8)) % len(reel_tuple)
        im = _render_single_spec(reel_tuple[idx], t, size=render_size)
    im = fast_grade(im, contrast=contrast, warmth=warmth, teal=teal, darken=darken)
    im = im.filter(ImageFilter.BoxBlur(max(1.0, blur * 0.5)))
    if render_size != out:
        im = im.resize(out, Image.Resampling.BILINEAR)
    return im


def broll_view(spec_or_key, t, cx=0.5, cy=0.5, zoom=1.0, out=(W, H),
               contrast=1.08, sat=1.06, warmth=0.0, teal=0.25, darken=0.0, blur=0, cut_period=3.8):
    """Render a 25fps moving B-roll frame for any reel key, clip spec, or list of clip specs."""
    if isinstance(spec_or_key, (list, tuple)):
        reel = tuple(spec_or_key)
    elif spec_or_key in BROLL_REELS:
        reel = tuple(BROLL_REELS[spec_or_key])
    else:
        reel = (spec_or_key,)

    if blur >= 3:
        return _blurred_bg_cached(
            reel, int(t * 12.5), out,
            round(contrast, 2), round(warmth, 2), round(teal, 2), round(darken, 2), int(blur)
        ).copy()

    render_size = out
    if len(reel) == 1:
        im = _render_single_spec(reel[0], t, size=render_size)
    else:
        pos = t / cut_period
        idx = int(math.floor(pos)) % len(reel)
        frac = pos - math.floor(pos)
        im = _render_single_spec(reel[idx], t, size=render_size)
        fade_frac = 0.14 / cut_period
        if frac > 1.0 - fade_frac:
            alpha = (frac - (1.0 - fade_frac)) / fade_frac
            nxt_im = _render_single_spec(reel[(idx + 1) % len(reel)], t, size=render_size)
            im = Image.blend(im, nxt_im, clamp(alpha, 0.0, 1.0))

    z_eff = 1.0 + clamp((zoom - 1.0) * 0.22, 0.0, 0.16)
    if z_eff > 1.005:
        ow, oh = render_size
        sw, sh = ow / z_eff, oh / z_eff
        cx_eff = 0.5 + (cx - 0.5) * 0.25
        cy_eff = 0.5 + (cy - 0.5) * 0.25
        x0 = int(clamp(cx_eff * ow - sw / 2, 0, ow - sw))
        y0 = int(clamp(cy_eff * oh - sh / 2, 0, oh - sh))
        im = im.crop((x0, y0, int(x0 + sw), int(y0 + sh))).resize(render_size, Image.Resampling.BILINEAR)

    im = fast_grade(im, contrast=contrast, warmth=warmth, teal=teal, darken=darken)
    if blur > 0:
        im = im.filter(ImageFilter.BoxBlur(max(1.0, blur * 0.5)))
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


def hud_broll_bg(reel_key, t, darken=0.72, blur=3):
    """Render a darkened, cool-teal HUD-graded moving B-roll background with blueprint grid overlay."""
    im = broll_view(reel_key, t, contrast=1.10, sat=0.85, teal=0.55, darken=darken, blur=blur).convert("RGBA")
    im.alpha_composite(grid_overlay_cached())
    return im
