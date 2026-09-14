#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
تنزيل فيديوهات Pexels محددة بالمعرّف (ID) إلى مجلد stock_scenes.

التشغيل:
    Windows CMD:   set PEXELS_API_KEY=YOUR_KEY
    PowerShell:    $env:PEXELS_API_KEY="YOUR_KEY"
    Linux/macOS:   export PEXELS_API_KEY=YOUR_KEY

    python download_stock_videos.py

ملاحظات:
- لا يشترط تثبيت requests — يستخدمها إن كانت موجودة، وإلا يعمل بمكتبة
  urllib القياسية (بدون أي تبعيات).
- الملفات تُنزَّل أولًا باسم مؤقت ‎.part ثم تُعاد تسميتها، فلا يبقى ملف
  تالف لو انقطع الاتصال (وإلا كان سيُتخطى في التشغيل التالي!).
- عند 404 على المسار الجديد يجرّب المسار القديم تلقائيًا (Pexels تعمل
  على ترحيل /videos/ إلى /v1/videos/).
"""

import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

try:
    import requests  # اختيارية
except ImportError:
    requests = None

# -----------------------------------------------------------------------
# ضع Pexels API Key في Environment Variable:
#
# Windows CMD:
# set PEXELS_API_KEY=YOUR_KEY
#
# PowerShell:
# $env:PEXELS_API_KEY="YOUR_KEY"
#
# Linux/macOS:
# export PEXELS_API_KEY=YOUR_KEY
# -----------------------------------------------------------------------

API_KEY = os.getenv("PEXELS_API_KEY")

if not API_KEY:
    print("ERROR: PEXELS_API_KEY was not found.")
    print("Set your Pexels API key first, then run the script again.")
    sys.exit(1)

# يمكن تجاوزه للاختبار المحلي عبر متغير البيئة PEXELS_API_BASE
API_BASE = os.getenv("PEXELS_API_BASE", "https://api.pexels.com").rstrip("/")

# المسار الجديد أولًا ثم القديم احتياطًا
VIDEO_SHOW_PATHS = ["/v1/videos/videos", "/videos/videos"]

OUTPUT_DIR = Path("stock_scenes")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

VIDEOS = [
    # Mediterranean / opening
    (28181129, "01_cyprus_mediterranean"),
    (32800871, "02_clear_mediterranean"),
    (33078022, "03_mediterranean_boats"),
    (16764717, "04_mediterranean_lone_boat"),

    # Underwater
    (32790667, "05_underwater_sunlight"),
    (5237551,  "06_underwater_rocks"),
    (33456619, "07_diver_large_rock"),
    (31062484, "08_diver_rock_formations"),
    (35832900, "09_deep_blue_diver"),
    (34385460, "10_scuba_rock_formation"),
    (37996231, "11_underwater_exploration"),
    (33994571, "12_underwater_cave_rays"),

    # Ancient history / ruins
    (35654838, "13_mediterranean_coast_ruins"),
    (30768986, "14_ancient_ruins"),
    (30414475, "15_ancient_ruins_landscape"),

    # Maps / geography
    (3125427, "16_digital_world_map"),
    (8817503, "17_rotating_earth"),

    # Science
    (3209070, "18_scientist_computer"),
    (5752735, "19_scientist_microscope"),
    (8325990, "20_scientist_specimen"),
    (4121321, "21_laboratory_top_view"),

    # Geology
    (10109224, "22_rock_formations_sea"),
]

HEADERS = {
    "Authorization": API_KEY,
    "User-Agent": "StockVideosDownloader/1.0",
}

TIMEOUT = 30          # مهلة طلبات الـ API (ثوانٍ)
DOWNLOAD_TIMEOUT = 300  # مهلة تنزيل الملفات (ثوانٍ)
ATTEMPTS = 3          # عدد المحاولات للأخطاء المؤقتة


# ------------------------------------------------------------------------
# طبقة HTTP (requests إن وجدت، وإلا urllib)
# ------------------------------------------------------------------------

class HttpError(RuntimeError):
    def __init__(self, status: int, message: str):
        super().__init__(f"HTTP {status}: {message}")
        self.status = status


def _open(url: str, timeout: int):
    if requests is not None:
        return requests.get(url, headers=HEADERS, timeout=timeout, stream=True)
    req = urllib.request.Request(url, headers=HEADERS)
    return urllib.request.urlopen(req, timeout=timeout)


def _status(resp) -> int:
    return resp.status_code if requests is not None else resp.status


def _chunks(resp, size: int = 1024 * 1024):
    if requests is not None:
        yield from resp.iter_content(chunk_size=size)
    else:
        while True:
            block = resp.read(size)
            if not block:
                break
            yield block


def _close(resp) -> None:
    try:
        resp.close()
    except Exception:
        pass


def get_with_retry(url: str, timeout: int = TIMEOUT):
    """GET مع إعادة محاولات للأخطاء المؤقتة (شبكة/5xx/429).

    4xx غير قابلة للإصلاح (مثل 401/404) تفشل فورًا.
    """
    last: Exception | None = None
    for attempt in range(1, ATTEMPTS + 1):
        try:
            resp = _open(url, timeout)
            status = _status(resp)
            if status == 200:
                return resp
            body = ""
            try:
                body = resp.text[:300] if requests is not None \
                    else resp.read(300).decode("utf-8", "replace")
            except Exception:
                pass
            _close(resp)
            err = HttpError(status, body)
            if 400 <= status < 500 and status != 429:
                raise err
            last = err
        except urllib.error.HTTPError as exc:
            # مسار urllib: الأخطاء ترمي استثناءً بدل إرجاع استجابة
            err = HttpError(exc.code, str(exc.reason))
            if 400 <= exc.code < 500 and exc.code != 429:
                raise err
            last = err
        except HttpError:
            raise
        except Exception as exc:  # أخطاء شبكة
            last = exc
        if attempt < ATTEMPTS:
            wait = 2.0 * (2 ** (attempt - 1))
            print(f"  retry in {wait:.0f}s ({attempt}/{ATTEMPTS})…", flush=True)
            time.sleep(wait)
    raise last if last else RuntimeError(f"request failed: {url}")


def get_json(url: str) -> dict:
    resp = get_with_retry(url)
    try:
        if requests is not None:
            return resp.json()
        return json.loads(resp.read().decode("utf-8"))
    finally:
        _close(resp)


# ------------------------------------------------------------------------
# منطق Pexels
# ------------------------------------------------------------------------

def get_video_info(video_id: int) -> dict:
    """جلب بيانات فيديو بالمعرّف — مسار جديد ثم القديم عند 404."""
    last: Exception | None = None
    for path in VIDEO_SHOW_PATHS:
        url = f"{API_BASE}{path}/{video_id}"
        try:
            return get_json(url)
        except HttpError as exc:
            if exc.status == 404:
                last = exc
                print(f"  (404 on {path} — trying legacy path)")
                continue
            raise
    raise last if last else RuntimeError(f"video {video_id} not found")


def choose_best_file(video: dict) -> dict:
    """
    Prefer:
    1. MP4
    2. Landscape
    3. Highest resolution up to 4K
    """
    files = video.get("video_files", [])
    candidates = []

    for f in files:
        link = f.get("link")
        if not link:
            continue

        file_type = f.get("file_type", "")
        width = f.get("width") or 0
        height = f.get("height") or 0

        if file_type != "video/mp4":
            continue

        candidates.append({
            "link": link,
            "width": width,
            "height": height,
            "pixels": width * height,
            "landscape": width >= height,
        })

    if not candidates:
        raise RuntimeError(f"No MP4 files found for video {video['id']}")

    # Landscape first, then resolution
    candidates.sort(key=lambda x: (x["landscape"], x["pixels"]), reverse=True)
    return candidates[0]


def download_file(url: str, destination: Path) -> int:
    """تنزيل إلى ‎.part مؤقتًا ثم إعادة تسمية — لا ملفات تالفة عند الانقطاع."""
    tmp = destination.with_name(destination.name + ".part")
    last: Exception | None = None

    for attempt in range(1, ATTEMPTS + 1):
        try:
            resp = get_with_retry(url, timeout=DOWNLOAD_TIMEOUT)
            try:
                total = int(resp.headers.get("Content-Length")
                            or resp.headers.get("content-length") or 0)
            except (ValueError, TypeError):
                total = 0

            downloaded = 0
            try:
                with open(tmp, "wb") as file:
                    for chunk in _chunks(resp):
                        if not chunk:
                            continue
                        file.write(chunk)
                        downloaded += len(chunk)
                        if total:
                            percent = (downloaded / total) * 100
                            print(f"\r{percent:5.1f}%", end="", flush=True)
            finally:
                _close(resp)

            if total and downloaded != total:
                raise RuntimeError(f"incomplete download {downloaded}/{total}")

            print(flush=True)
            tmp.replace(destination)  # ذرّي: إما كامل أو لا شيء
            return downloaded

        except Exception as exc:
            last = exc
            if tmp.exists():
                try:
                    tmp.unlink()
                except OSError:
                    pass
            if attempt < ATTEMPTS:
                wait = 2.0 * (2 ** (attempt - 1))
                print(f"  download failed ({exc}) — retry in {wait:.0f}s "
                      f"({attempt}/{ATTEMPTS})", flush=True)
                time.sleep(wait)
    raise last if last else RuntimeError(f"download failed: {url}")


# ------------------------------------------------------------------------
# البرنامج الرئيسي
# ------------------------------------------------------------------------

def main() -> int:
    total_videos = len(VIDEOS)

    print(f"Downloading {total_videos} stock videos...")
    print(f"Folder: {OUTPUT_DIR.resolve()}")
    print("-" * 60)

    failed = []
    credits = []

    for index, (video_id, name) in enumerate(VIDEOS, start=1):
        destination = OUTPUT_DIR / f"{name}.mp4"  # الاسم مرقّم مسبقًا في القائمة

        if destination.exists():
            print(f"[{index}/{total_videos}] SKIP: {destination.name}")
            continue

        print(f"\n[{index}/{total_videos}] Getting video ID {video_id}")

        try:
            info = get_video_info(video_id)
            selected = choose_best_file(info)

            print("Resolution:", f"{selected['width']}x{selected['height']}")
            creator = info.get("user", {}).get("name", "Unknown")
            print("Creator:", creator)
            print("Downloading:", destination.name)

            download_file(selected["link"], destination)
            credits.append(
                f"{destination.name} — {creator} — {info.get('url', '')}"
            )

        except Exception as exc:
            print(f"FAILED: {video_id}")
            print(exc)
            failed.append((video_id, name))

    # ملف شكر/إسناد (متطلب من ترخيص Pexels: الإشارة إلى المصدر)
    if credits:
        with open(OUTPUT_DIR / "CREDITS.txt", "w", encoding="utf-8") as fh:
            fh.write("Videos provided by Pexels (https://www.pexels.com)\n\n")
            fh.write("\n".join(credits) + "\n")

    print("\n" + "=" * 60)

    if failed:
        print(f"Finished with {len(failed)} failures:")
        for video_id, name in failed:
            print(video_id, name)
    else:
        print("All stock videos downloaded successfully.")

    print("\nDownloaded files:")
    for file in sorted(OUTPUT_DIR.glob("*.mp4")):
        print(file.name)

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
