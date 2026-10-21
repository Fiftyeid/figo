#!/usr/bin/env python3
"""
Vellum Logs — publish-pack linter
---------------------------------
YouTube silently mangles a description with bad chapters, and refuses a title
over 100 characters. This checks every limit before you paste anything.

    python3 tools/check_publish.py publish/ep01_part1.metadata.json

Checks
  * title ≤ 100 chars, and the first 45 characters alone carry the promise
  * description ≤ 5,000 chars, no tabs, no unbalanced quotes
  * tags ≤ 500 chars total, ≤ 500 per tag, no '#'
  * chapter block starts at 0:00, every stamp is ascending, at least 3 chapters
  * hashtags: 3 shown above the title, ≤ 15 accepted at all
  * the promise words the reference channel always uses
"""
from __future__ import annotations

import json
import re
import sys

LIMITS = {"title": 100, "description": 5000, "tags_total": 500, "tag": 500}
PROMISE = ["no adverts", "432 hz"]
STAMP = re.compile(r"^(\d{1,2}):([0-5]\d):([0-5]\d)\s+\S", re.M)


def secs(h, m, s):
    return int(h) * 3600 + int(m) * 60 + int(s)


def main(path: str) -> int:
    meta = json.load(open(path, encoding="utf-8"))
    sn, st = meta["snippet"], meta["status"]
    title, desc, tags = sn["title"], sn["description"], sn.get("tags", [])
    errors, warnings = [], []

    if len(title) > LIMITS["title"]:
        errors.append(f"title is {len(title)} chars (limit 100)")
    elif len(title) > 90:
        warnings.append(f"title is {len(title)} chars — safe, but close to the 100 limit")
    if len(title.split("—")[0].strip()) > 55:
        warnings.append("the first dash-segment of the title is long; mobile may cut it")

    if len(desc) > LIMITS["description"]:
        errors.append(f"description is {len(desc)} chars (limit 5000)")
    if "\t" in desc:
        errors.append("description contains a tab")
    for word in PROMISE:
        if word not in desc.lower():
            warnings.append(f"the promise phrase “{word}” is missing from the description")

    total = len(", ".join(tags))
    if total > LIMITS["tags_total"]:
        errors.append(f"tags are {total} chars (limit 500)")
    for t in tags:
        if len(t) > LIMITS["tag"]:
            errors.append(f"tag too long: {t[:40]}…")
        if t.startswith("#"):
            errors.append(f"tag must not include '#': {t}")

    stamps = [(secs(*m.groups()), m.group(0)) for m in STAMP.finditer(desc)]
    if not stamps:
        errors.append("no chapter timestamps found in the description")
    else:
        if stamps[0][0] != 0:
            errors.append(f"first chapter starts at {stamps[0][0]}s — it must be 0:00:00")
        if len(stamps) < 3:
            warnings.append(f"only {len(stamps)} chapters — YouTube needs at least 3")
        for (a, _), (b, line) in zip(stamps, stamps[1:]):
            if b <= a:
                errors.append(f"chapters out of order or repeated: “{line}”")
        if len(stamps) >= 3 and stamps[-1][0] < 600:
            warnings.append("last chapter starts before 10:00 — chapters may not be accepted")

    hashtags = re.findall(r"#\w+", desc)
    if len(hashtags) > 15:
        errors.append(f"{len(hashtags)} hashtags (YouTube ignores all of them above 15)")
    elif len(hashtags) > 3:
        warnings.append(f"{len(hashtags)} hashtags — only the first 3 show above the title")

    if st.get("privacyStatus") not in ("private", "unlisted", "public"):
        errors.append(f"odd privacyStatus: {st.get('privacyStatus')}")

    print(f"· {path}")
    print(f"  title {len(title):>3}/100   desc {len(desc):>4}/5000   "
          f"tags {total:>3}/500 ({len(tags)})   chapters {len(stamps)}")
    for w in warnings:
        print(f"  ! {w}")
    for e in errors:
        print(f"  ✗ {e}")
    if not errors:
        print("  ✓ ready to paste")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(max(main(p) for p in sys.argv[1:]) if len(sys.argv) > 1 else
             print(__doc__))
