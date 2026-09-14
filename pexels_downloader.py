#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pexels Downloader — سكربت بايثون لتنزيل الصور والفيديوهات من Pexels عبر الـ API الرسمي المجاني.

قبل الاستخدام:
  1) احصل على مفتاح API مجاني من: https://www.pexels.com/api/
  2) مرّر المفتاح بالخيار --api-key أو عبر متغير البيئة PEXELS_API_KEY

أمثلة:
  export PEXELS_API_KEY="مفتاحك هنا"
  python pexels_downloader.py --query nature --limit 50
  python pexels_downloader.py --query "mountains" --type videos --limit 20
  python pexels_downloader.py --curated --limit 100
  python pexels_downloader.py --query sunset --type all          # كل النتائج
  python pexels_downloader.py --query sunset --type all --dry-run  # عرض بدون تنزيل

لا يحتاج أي مكتبات خارجية — يعمل بمكتبة Python القياسية فقط (Python 3.8+).
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import re
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

API_BASE = os.environ.get("PEXELS_API_BASE", "https://api.pexels.com")
PER_PAGE_MAX = 80
PHOTO_PATHS = {"search": ["/v1/search"], "curated": ["/v1/curated"]}
VIDEO_PATHS = {"search": ["/v1/videos/search", "/videos/search"],
               "curated": ["/v1/videos/popular", "/videos/popular"]}
USER_AGENT = "PexelsDownloader/1.0 (Python; +https://www.pexels.com/api/)"

PHOTO_VARIANTS = [
    "original", "large2x", "large", "medium", "small",
    "portrait", "landscape", "tiny",
]

_print_lock = threading.Lock()
_index_lock = threading.Lock()


def log(msg: str) -> None:
    with _print_lock:
        print(msg, flush=True)


class ApiError(RuntimeError):
    """خطأ غير متوقع في الـ API بعد انتهاء المحاولات."""


class RateLimiter:
    """محدد معدّل بسيط لاحترام حدود الـ API (طلبات القوائم فقط)."""

    def __init__(self, min_interval: float) -> None:
        self.min_interval = min_interval
        self._lock = threading.Lock()
        self._next_time = 0.0

    def wait(self) -> None:
        with self._lock:
            now = time.monotonic()
            delay = self._next_time - now
            if delay > 0:
                time.sleep(delay)
                now = time.monotonic()
            self._next_time = max(now, self._next_time) + self.min_interval


def human_size(num_bytes: int | None) -> str:
    if not num_bytes:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(num_bytes)
    for unit in units:
        if size < 1024 or unit == units[-1]:
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} B"
        size /= 1024
    return f"{size:.1f} TB"


def safe_filename(name: str) -> str:
    return re.sub(r"[^\w\-.]+", "_", name).strip("._")[:80] or "file"


# ----------------------------------------------------------------------------
# طبقة الـ API
# ----------------------------------------------------------------------------

def api_get(url: str, api_key: str, limiter: RateLimiter,
            attempts: int = 5, timeout: int = 30,
            not_found_ok: bool = False) -> dict | None:
    """طلب GET مع إعادة محاولات ذكية (429/5xx) وتراجع أُسّي. يعيد None عند 404 إذا not_found_ok."""
    headers = {
        "Authorization": api_key,
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
    }
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        limiter.wait()
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = ""
            try:
                body = exc.read().decode("utf-8", "replace")[:300]
            except Exception:
                pass
            if exc.code in (401, 403):
                raise ApiError(
                    f"مفتاح API غير صالح أو غير مصرّح به (HTTP {exc.code}).\n"
                    f"  احصل على مفتاح مجاني من https://www.pexels.com/api/ وتأكد من صحته."
                ) from exc
            if exc.code == 404:
                if not_found_ok:
                    return None
                raise ApiError(f"المسار غير موجود (HTTP 404): {url}") from exc
            retry_after = exc.headers.get("Retry-After") if exc.headers else None
            wait_s = float(retry_after) if (retry_after or "").isdigit() else 2.0 * (2 ** (attempt - 1))
            last_error = ApiError(f"HTTP {exc.code}: {body}")
            if attempt < attempts:
                log(f"⚠ تحذير: HTTP {exc.code} — إعادة المحاولة بعد {wait_s:.0f} ثانية ({attempt}/{attempts})")
                time.sleep(wait_s)
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as exc:
            last_error = exc
            wait_s = 2.0 * (2 ** (attempt - 1))
            if attempt < attempts:
                log(f"⚠ تحذير: خطأ شبكة ({exc}) — إعادة المحاولة بعد {wait_s:.0f} ثانية ({attempt}/{attempts})")
                time.sleep(wait_s)
    raise ApiError(f"فشل الطلب بعد {attempts} محاولات: {last_error}")


def build_params(args: argparse.Namespace, kind: str, page: int) -> dict:
    params: dict = {"page": page, "per_page": args.per_page}
    if not args.curated and args.query:
        params["query"] = args.query
    if args.orientation:
        params["orientation"] = args.orientation
    if kind == "photos":
        if args.size:
            params["size"] = args.size
        if args.color:
            params["color"] = args.color
    else:
        if args.size:
            params["size"] = args.size
        if args.min_duration is not None:
            params["min_duration"] = args.min_duration
        if args.max_duration is not None:
            params["max_duration"] = args.max_duration
    return params


def iter_pages(args: argparse.Namespace, api_key: str, kind: str, limiter: RateLimiter):
    """يولّد عناصر النتائج صفحةً صفحة حتى نهايتها."""
    mode = "curated" if args.curated else "search"
    candidates = (PHOTO_PATHS if kind == "photos" else VIDEO_PATHS)[mode]
    items_key = "photos" if kind == "photos" else "videos"
    path: str | None = None
    page = 1
    total_seen = 0
    total_reported = None
    while True:
        params = urllib.parse.urlencode(build_params(args, kind, page))
        if path is None:
            # جرّب المسارات بالترتيب (الجديد ثم القديم) عند أول صفحة فقط
            data = None
            for candidate in candidates:
                data = api_get(f"{API_BASE}{candidate}?{params}", api_key,
                               limiter, not_found_ok=True)
                if data is not None:
                    path = candidate
                    break
            if data is None:
                raise ApiError(f"لا توجد نقطة نهاية صالحة ({kind}/{mode}).")
        else:
            data = api_get(f"{API_BASE}{path}?{params}", api_key, limiter)
        if total_reported is None:
            total_reported = data.get("total_results") or 0
            if total_reported == 0:
                log(f"ℹ لا توجد نتائج ({kind}).")
                return
        items = data.get(items_key) or []
        if not items:
            return
        for item in items:
            total_seen += 1
            yield item
        if len(items) < args.per_page:
            return
        page += 1


# ----------------------------------------------------------------------------
# اختيار روابط التنزيل
# ----------------------------------------------------------------------------

def choose_photo_url(photo: dict, variant: str) -> str | None:
    src = photo.get("src") or {}
    return src.get(variant) or src.get("original")


def choose_video_url(video: dict, prefer_quality: str) -> tuple[str | None, dict | None]:
    candidates = [
        f for f in (video.get("video_files") or [])
        if f.get("file_type") == "video/mp4" and f.get("link")
    ]
    if prefer_quality in ("hd", "sd"):
        matching = [f for f in candidates if f.get("quality") == prefer_quality]
        if matching:
            candidates = matching
    if not candidates:
        return None, None
    candidates.sort(key=lambda f: (f.get("height") or 0), reverse=True)
    best = candidates[0]
    return best.get("link"), best


def photo_filename(photo: dict, variant: str) -> str:
    if variant == "original":
        dims = f"{photo.get('width') or 0}x{photo.get('height') or 0}"
        dims = "" if dims == "0x0" else f"_{dims}"
        return f"pexels_photo_{photo.get('id')}{dims}.jpg"
    return f"pexels_photo_{photo.get('id')}_{variant}.jpg"


def video_filename(video: dict, meta: dict) -> str:
    w = meta.get("width") or video.get("width") or 0
    h = meta.get("height") or video.get("height") or 0
    return f"pexels_video_{video.get('id')}_{w}x{h}.mp4"


# ----------------------------------------------------------------------------
# التنزيل
# ----------------------------------------------------------------------------

def download_file(url: str, dest: str, attempts: int = 4,
                  timeout: int = 180) -> int:
    """تنزيل ملف إلى المسار المحدد (تنزيل مؤقت ثم إعادة تسمية). يعيد الحجم بالبايت."""
    tmp = dest + ".part"
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
            with urllib.request.urlopen(req, timeout=timeout) as resp, open(tmp, "wb") as out:
                while True:
                    chunk = resp.read(1 << 16)  # 64 KB
                    if not chunk:
                        break
                    out.write(chunk)
            size = os.path.getsize(tmp)
            os.replace(tmp, dest)
            return size
        except urllib.error.HTTPError as exc:
            last_error = exc
            if os.path.exists(tmp):
                try:
                    os.remove(tmp)
                except OSError:
                    pass
            if 400 <= exc.code < 500 and exc.code != 429:
                break  # أخطاء العميل لا تُصلح بإعادة المحاولة
            if attempt < attempts:
                wait_s = 2.0 * (2 ** (attempt - 1))
                time.sleep(wait_s)
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as exc:
            last_error = exc
            if os.path.exists(tmp):
                try:
                    os.remove(tmp)
                except OSError:
                    pass
            if attempt < attempts:
                wait_s = 2.0 * (2 ** (attempt - 1))
                time.sleep(wait_s)
    raise RuntimeError(f"فشل تنزيل {url}: {last_error}")


# ----------------------------------------------------------------------------
# البرنامج الرئيسي
# ----------------------------------------------------------------------------

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="pexels_downloader",
        description="تنزيل الصور والفيديوهات من Pexels عبر الـ API الرسمي المجاني.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "أمثلة:\n"
            '  python pexels_downloader.py --query nature --limit 50\n'
            '  python pexels_downloader.py --query mountains --type videos\n'
            '  python pexels_downloader.py --curated --limit 100\n'
            '  python pexels_downloader.py --query sunset --type all --dry-run\n'
        ),
    )
    parser.add_argument("--api-key", default=os.environ.get("PEXELS_API_KEY"),
                        help="مفتاح Pexels API (أو متغير البيئة PEXELS_API_KEY)")
    parser.add_argument("-q", "--query", default=None,
                        help="كلمة البحث (اتركها فارغة مع --curated للمجموعة المميزة)")
    parser.add_argument("--curated", action="store_true",
                        help="تنزيل من المجموعة المميزة (curated) بدل البحث")
    parser.add_argument("-t", "--type", choices=["photos", "videos", "all"],
                        default="photos", help="نوع الملفات (افتراضي: photos)")
    parser.add_argument("--limit", type=int, default=0,
                        help="أقصى عدد لكل نوع (0 = كل النتائج)")
    parser.add_argument("--per-page", type=int, default=PER_PAGE_MAX,
                        help=f"عدد النتائج لكل صفحة API (الحد الأقصى {PER_PAGE_MAX})")
    parser.add_argument("--orientation", choices=["landscape", "portrait", "square"],
                        default=None, help="اتجاه الميديا")
    parser.add_argument("--size", choices=["large", "medium", "small"], default=None,
                        help="فلتر الحجم حسب Pexels")
    parser.add_argument("--color", default=None,
                        help="فلتر اللون للصور (مثل red أو كود hex مثل 065F46)")
    parser.add_argument("--photo-quality", choices=PHOTO_VARIANTS, default="original",
                        help="جودة الصور (افتراضي: original — الحجم الكامل)")
    parser.add_argument("--video-quality", choices=["any", "hd", "sd"], default="any",
                        help="جودة الفيديو المفضلة (افتراضي: any — الأعلى دقة)")
    parser.add_argument("--min-duration", type=int, default=None,
                        help="أقل مدة للفيديو بالثواني")
    parser.add_argument("--max-duration", type=int, default=None,
                        help="أقصى مدة للفيديو بالثواني")
    parser.add_argument("-o", "--out", default="pexels_downloads",
                        help="مجلد الإخراج (افتراضي: pexels_downloads)")
    parser.add_argument("--workers", type=int, default=4,
                        help="عدد التنزيلات المتوازية (افتراضي: 4)")
    parser.add_argument("--overwrite", action="store_true",
                        help="إعادة تنزيل الملفات الموجودة مسبقًا")
    parser.add_argument("--no-index", action="store_true",
                        help="عدم إنشاء ملف index.jsonl (البيانات الوصفية)")
    parser.add_argument("--dry-run", action="store_true",
                        help="عرض ما سيُنزّل دون تنزيل أي شيء")
    return parser.parse_args(argv)


def collect_tasks(args: argparse.Namespace, api_key: str, kind: str,
                  limiter: RateLimiter) -> list[dict]:
    """يبني قائمة مهام التنزيل ({url, dest, meta}) لنوع واحد."""
    tasks: list[dict] = []
    type_dir = os.path.join(args.out, "photos" if kind == "photos" else "videos")
    if not args.dry_run:
        os.makedirs(type_dir, exist_ok=True)

    count = 0
    for item in iter_pages(args, api_key, kind, limiter):
        if kind == "photos":
            url = choose_photo_url(item, args.photo_quality)
            if not url:
                continue
            name = photo_filename(item, args.photo_quality)
            meta = {
                "id": item.get("id"), "type": "photo",
                "photographer": item.get("photographer"),
                "page_url": item.get("url"),
                "width": item.get("width"), "height": item.get("height"),
                "avg_color": item.get("avg_color"), "alt": item.get("alt"),
            }
        else:
            url, best = choose_video_url(item, args.video_quality)
            if not url:
                continue
            name = video_filename(item, best or {})
            meta = {
                "id": item.get("id"), "type": "video",
                "photographer": (item.get("user") or {}).get("name"),
                "page_url": item.get("url"),
                "width": (best or {}).get("width") or item.get("width"),
                "height": (best or {}).get("height") or item.get("height"),
                "duration": item.get("duration"),
                "quality": (best or {}).get("quality"),
            }
        tasks.append({
            "url": url,
            "dest": os.path.join(type_dir, safe_filename(name)),
            "meta": {**meta, "download_url": url},
        })
        count += 1
        if args.limit and count >= args.limit:
            break
    return tasks


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    api_key = (args.api_key or "").strip()
    if not api_key:
        print("خطأ: مفتاح API مفقود.\n"
              "  1) سجّل مجانًا في https://www.pexels.com/api/ للحصول على المفتاح\n"
              '  2) مرّره بالخيار --api-key أو ضعه في متغير البيئة PEXELS_API_KEY',
              file=sys.stderr)
        return 2

    args.per_page = max(1, min(args.per_page, PER_PAGE_MAX))
    if args.limit < 0:
        args.limit = 0
    args.workers = max(1, args.workers)
    if not args.curated and not args.query:
        args.curated = True
        log("ℹ لم تُحدد كلمة بحث — سيتم استخدام المجموعة المميزة (curated).")

    kinds = ["photos", "videos"] if args.type == "all" else [args.type]
    limiter = RateLimiter(min_interval=0.65)

    all_tasks: list[dict] = []
    for kind in kinds:
        log(f"⏳ جلب قائمة {kind} …")
        try:
            tasks = collect_tasks(args, api_key, kind, limiter)
        except ApiError as exc:
            print(f"خطأ: {exc}", file=sys.stderr)
            return 1
        log(f"✓ عُثر على {len(tasks)} ملف ({kind}).")
        all_tasks.extend(tasks)

    if not all_tasks:
        log("لا توجد ملفات للتنزيل.")
        return 0

    total_bytes = 0
    downloaded = skipped = failed = 0
    failures: list[str] = []
    index_file = None

    if not args.dry_run:
        os.makedirs(args.out, exist_ok=True)
        if not args.no_index:
            index_file = open(os.path.join(args.out, "index.jsonl"), "a", encoding="utf-8")

    log(f"⬇ بدء تنزيل {len(all_tasks)} ملف إلى «{args.out}» "
        f"({args.workers} تنزيلات متوازية){' — وضع المعاينة فقط' if args.dry_run else ''}")

    def do_task(task: dict) -> tuple[dict, str, int]:
        dest = task["dest"]
        if not args.overwrite and os.path.exists(dest) and os.path.getsize(dest) > 0:
            return task, "skipped", 0
        if args.dry_run:
            return task, "dryrun", 0
        size = download_file(task["url"], dest)
        return task, "ok", size

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = [pool.submit(do_task, task) for task in all_tasks]
            done_count = 0
            for future in concurrent.futures.as_completed(futures):
                done_count += 1
                try:
                    task, status, size = future.result()
                except Exception as exc:  # noqa: BLE001
                    failed += 1
                    failures.append(str(exc))
                    log(f"✗ [{done_count}/{len(all_tasks)}] فشل: {exc}")
                    continue
                task_id = task["meta"].get("id")
                if status == "skipped":
                    skipped += 1
                    log(f"↷ [{done_count}/{len(all_tasks)}] موجود مسبقًا: {os.path.basename(task['dest'])}")
                elif status == "dryrun":
                    log(f"• [{done_count}/{len(all_tasks)}] سيُنزّل: {os.path.basename(task['dest'])}")
                else:
                    downloaded += 1
                    total_bytes += size
                    log(f"✓ [{done_count}/{len(all_tasks)}] {os.path.basename(task['dest'])} ({human_size(size)})")
                if index_file is not None and status != "dryrun":
                    with _index_lock:
                        index_file.write(json.dumps(task["meta"], ensure_ascii=False) + "\n")
    except KeyboardInterrupt:
        log("\n⏹ أُلغي التنزيل بواسطة المستخدم.")
        return 130
    finally:
        if index_file is not None:
            index_file.close()

    log("─" * 50)
    log(f"اكتمل: نُزّل {downloaded} ملف ({human_size(total_bytes)}) — "
        f"تخطي {skipped} — فشل {failed}")
    if failures:
        log("الملفات الفاشلة:")
        for failure in failures[:20]:
            log(f"  - {failure}")
        if len(failures) > 20:
            log(f"  … و {len(failures) - 20} أخرى")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
