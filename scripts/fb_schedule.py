#!/usr/bin/env python3
"""Schedule photo posts on a Facebook Page through the Meta Graph API.

Reads a CSV plan (see content/week_plan.csv), uploads each image as an
unpublished photo, then creates a scheduled feed post for it.

Setup (once):
  export FB_PAGE_ID=<numeric page id>
  export FB_PAGE_TOKEN=<Page access token with pages_manage_posts>

Usage:
  python3 scripts/fb_schedule.py content/week_plan.csv              # dry run (checks only)
  python3 scripts/fb_schedule.py content/week_plan.csv --execute    # really schedules

Stdlib only; no pip install needed.
"""
import argparse
import csv
import json
import mimetypes
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from urllib import error, parse, request

GRAPH_VERSION = os.environ.get("FB_GRAPH_VERSION", "v21.0")
BASE_URL = f"https://graph.facebook.com/{GRAPH_VERSION}"
MIN_LEAD = timedelta(minutes=10)   # Meta rejects scheduled times that are too close
MAX_LEAD = timedelta(days=30)      # and times that are too far ahead (check Meta's current limit)


def load_plan(csv_path):
    base_dir = os.path.dirname(os.path.abspath(csv_path))
    rows = []
    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        for line_no, rec in enumerate(csv.DictReader(f), start=2):
            when = datetime.fromisoformat(rec["publish_at"].strip())
            if when.tzinfo is None:
                raise ValueError(
                    f"line {line_no}: publish_at needs a UTC offset, e.g. 2026-11-15T20:00+03:00"
                )
            image = rec["image"].strip()
            if not os.path.isabs(image):
                image = os.path.join(base_dir, image)
            rows.append({
                "line": line_no,
                "when": when,
                "image": image,
                "caption": rec["caption"].strip(),
            })
    return rows


def check_plan(rows):
    now = datetime.now(timezone.utc)
    problems = []
    for r in rows:
        if not os.path.isfile(r["image"]):
            problems.append(f"line {r['line']}: image not found: {r['image']}")
        lead = r["when"].astimezone(timezone.utc) - now
        if lead < MIN_LEAD:
            problems.append(f"line {r['line']}: publish time is less than 10 minutes away or in the past")
        if lead > MAX_LEAD:
            problems.append(f"line {r['line']}: publish time is more than 30 days away")
        if "[" in r["caption"] or "]" in r["caption"]:
            problems.append(f"line {r['line']}: caption still has a [placeholder] to replace")
    return problems


def build_multipart(fields, file_path):
    boundary = uuid.uuid4().hex
    parts = []
    for name, value in fields.items():
        parts.append(
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n{value}\r\n".encode()
        )
    with open(file_path, "rb") as f:
        data = f.read()
    ctype = mimetypes.guess_type(file_path)[0] or "image/jpeg"
    filename = os.path.basename(file_path)
    parts.append(
        (f"--{boundary}\r\nContent-Disposition: form-data; name=\"source\"; filename=\"{filename}\"\r\n"
         f"Content-Type: {ctype}\r\n\r\n").encode() + data + b"\r\n"
    )
    parts.append(f"--{boundary}--\r\n".encode())
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


def graph_post(path, token, fields=None, file_path=None):
    if file_path:
        body, content_type = build_multipart(fields or {}, file_path)
    else:
        body = parse.urlencode(fields or {}).encode()
        content_type = "application/x-www-form-urlencoded"
    req = request.Request(
        f"{BASE_URL}/{path}",
        data=body,
        method="POST",
        headers={"Content-Type": content_type, "Authorization": f"Bearer {token}"},
    )
    try:
        with request.urlopen(req, timeout=180) as resp:
            return json.loads(resp.read())
    except error.HTTPError as e:
        detail = e.read().decode(errors="replace")
        raise RuntimeError(f"Graph API HTTP {e.code}: {detail}") from None


def schedule_row(page_id, token, row):
    # 1) Upload the image as an unpublished photo.
    photo = graph_post(f"{page_id}/photos", token, {"published": "false"}, row["image"])
    # 2) Create a scheduled feed post that attaches that photo.
    post = graph_post(f"{page_id}/feed", token, {
        "message": row["caption"],
        "attached_media[0]": json.dumps({"media_fbid": photo["id"]}),
        "published": "false",
        "scheduled_publish_time": str(int(row["when"].timestamp())),
    })
    return post["id"]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv_path", help="plan CSV with columns publish_at,image,caption")
    ap.add_argument("--execute", action="store_true", help="actually schedule the posts")
    args = ap.parse_args()

    rows = load_plan(args.csv_path)
    for r in rows:
        print(f"line {r['line']}: {r['when'].isoformat()}  {os.path.basename(r['image'])}  "
              f"{r['caption'][:60]!r}")

    problems = check_plan(rows)
    if problems:
        print("\nProblems found:")
        for p in problems:
            print(f" - {p}")
        return 1

    if not args.execute:
        print(f"\nDry run OK: {len(rows)} posts ready. Re-run with --execute to schedule them.")
        return 0

    page_id = os.environ.get("FB_PAGE_ID")
    token = os.environ.get("FB_PAGE_TOKEN")
    if not page_id or not token:
        print("Set FB_PAGE_ID and FB_PAGE_TOKEN environment variables first.", file=sys.stderr)
        return 1

    failed = 0
    for r in rows:
        try:
            post_id = schedule_row(page_id, token, r)
            print(f"scheduled line {r['line']} -> post id {post_id}")
        except Exception as exc:  # keep going so one bad row doesn't block the rest
            failed += 1
            print(f"FAILED line {r['line']}: {exc}", file=sys.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
