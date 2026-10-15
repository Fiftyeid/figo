# -*- coding: utf-8 -*-
"""
Storyboard QA: flags card elements / overlays / pins that would pop in too close to (or after)
the cut to the next shot, i.e. things the viewer would never see or would only glimpse.
    python3 check_timing.py [min_visible_seconds=1.0]
"""
import sys
from storyboard import build_shots

FAR = 9000  # times >= FAR are intentionally "never" (e.g. ledger page shown before its rewrite)


def main():
    minvis = float(sys.argv[1]) if len(sys.argv) > 1 else 1.0
    specs, tl = build_shots()
    issues = []
    for s in specs:
        st, en, tag = s["start"], s["end"], f'{s["start"]:7.2f} {s["section"]:16s} {s["type"]:8s}'
        for x in s.get("ts") or []:
            if x is not None and x < FAR and x > en - minvis:
                issues.append(f"{tag} card element at {x:.2f} but cut at {en:.2f}")
        for key in ("foot_t", "cap2_t"):
            if s.get(key) and s[key] > en - minvis:
                issues.append(f"{tag} {key} at {s[key]:.2f} but cut at {en:.2f}")
        for ov in s.get("overlays") or []:
            if ov.get("t") and ov["t"] > en - minvis:
                issues.append(f'{tag} overlay «{ov.get("text") or ov.get("title")}» at {ov["t"]:.2f} but cut at {en:.2f}')
        for p in (s.get("pins") or []) + (s.get("labels") or []):
            if p.get("t") and p["t"] > en - minvis:
                issues.append(f'{tag} pin/label «{p.get("name") or p.get("text")}» at {p["t"]:.2f} but cut at {en:.2f}')
        for r in s.get("routes") or []:
            if r.get("t") and r["t"] + r.get("dur", 1.0) > en - 0.3:
                issues.append(f'{tag} route ends at {r["t"] + r.get("dur", 1.0):.2f} but cut at {en:.2f}')
        if en - st < 1.0:
            issues.append(f"{tag} shot only {en - st:.2f}s long")
    for line in issues:
        print(line)
    print(f"{len(specs)} shots, {len(issues)} issue(s) (min visible {minvis}s)")
    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(main())
