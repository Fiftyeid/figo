# -*- coding: utf-8 -*-
"""Lint the storyboard: every shot >= 1.8 s, and every animated element appears at least 0.9 s before the cut."""
from storyboard import build_shots

MIN_SHOT = 1.8
MIN_VIS = 0.9


def element_times(s):
    out = []
    for ov in s.get("overlays", ()):
        out.append((ov["kind"], ov.get("text") or ov.get("name") or str(ov.get("value")), ov["t"]))
        if "t_sub" in ov:
            out.append(("sub", ov.get("sub", ""), ov["t_sub"]))
    for key in ("items", "cards", "markers"):
        for it in s.get(key, ()):
            if isinstance(it, dict) and "t" in it:
                out.append((key[:-1], it.get("label") or it.get("title") or it.get("text") or it.get("head"), it["t"]))
            if isinstance(it, dict) and "t_stamp" in it:
                out.append(("stamp", it.get("stamp"), it["t_stamp"]))
    for k, v in s.items():
        if k.startswith("t_") and isinstance(v, (int, float)):
            out.append((k, k, v))
        elif k == "t_labels":
            for tl, lab in zip(v, s.get("labels", ())):
                out.append(("label", lab, tl))
        elif k in ("left", "right") and isinstance(v, dict) and "t" in v:
            out.append((k, v.get("title"), v["t"]))
        elif k == "wall" and isinstance(v, dict) and "t" in v:
            out.append(("wall", "THE WALL", v["t"]))
    return out


def main():
    shots, tl = build_shots()
    issues = 0
    for s in shots:
        d = s["end"] - s["start"]
        if d < MIN_SHOT:
            print(f"SHORT {s['start']:6.2f} ({d:.2f}s) {s['section']:10s} {s['type']}")
            issues += 1
        for kind, name, t in element_times(s):
            if t < s["start"] - 0.5:
                print(f"EARLY {s['start']:6.2f}..{s['end']:6.2f} {s['section']:10s} {s['type']:8s} {kind} {name!r} at {t:.2f}")
                issues += 1
            elif s["end"] - t < MIN_VIS:
                print(f"LATE  {s['start']:6.2f}..{s['end']:6.2f} {s['section']:10s} {s['type']:8s} {kind} {name!r} at {t:.2f} (left {s['end']-t:.2f}s)")
                issues += 1
    print(f"{len(shots)} shots, {issues} issue(s)")
    return issues


if __name__ == "__main__":
    raise SystemExit(1 if main() else 0)
