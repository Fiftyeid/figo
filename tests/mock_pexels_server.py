#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""خادم وهمي يحاكي Pexels API (المسارات الجديدة والقديمة) لاختبار السكربتات.

التشغيل:
    python3 tests/mock_pexels_server.py [PORT]        # الافتراضي 8765

المفتاح الصحيح: TESTKEY (في ترويسة Authorization أو ك query param ?key=TESTKEY)
ملفات الـ "CDN" تحت /files/ تُخدم بدون تفويض — مثل الواقع.

ملاحظة: الخادم يرتبط بـ 0.0.0.0 ليعمل ضمن بيئة المعاينة الحيّة.
"""
import json
import os
import re
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
BASE = f"http://127.0.0.1:{PORT}"
API_KEY = "TESTKEY"

# معرف يرد 404 على المسار الجديد فقط — لاختبار التراجع للمسار القديم
LEGACY_ONLY_ID = 16764717

PHOTOS_P1 = [
    {"id": 101, "width": 4000, "height": 6000, "url": f"{BASE}/photo/101",
     "photographer": "أحمد", "avg_color": "#123456", "alt": "جبال",
     "src": {"original": f"{BASE}/files/photo_101.jpg",
             "large2x": f"{BASE}/files/photo_101_l2x.jpg"}},
    {"id": 102, "width": 1920, "height": 1080, "url": f"{BASE}/photo/102",
     "photographer": "Sara", "avg_color": "#ABCDEF", "alt": "sea",
     "src": {"original": f"{BASE}/files/photo_102.jpg",
             "large2x": f"{BASE}/files/photo_102_l2x.jpg"}},
]
PHOTOS_P2 = [
    {"id": 103, "width": 800, "height": 800, "url": f"{BASE}/photo/103",
     "photographer": "Omar", "avg_color": "#FFFFFF", "alt": "city",
     "src": {"original": f"{BASE}/files/photo_103.jpg"}},
]


def make_video(video_id: int) -> dict:
    """فيديو بملفات متعددة: mp4 بأحجام مختلفة + portrait + غير mp4."""
    return {
        "id": video_id,
        "width": 3840, "height": 2160, "duration": 12,
        "url": f"{BASE}/video/{video_id}",
        "user": {"id": 7, "name": f"Creator {video_id}"},
        "video_files": [
            {"id": 1, "quality": "sd", "file_type": "video/mp4",
             "width": 640, "height": 360,
             "link": f"{BASE}/files/v{video_id}_sd.mp4"},
            {"id": 2, "quality": "hd", "file_type": "video/mp4",
             "width": 1920, "height": 1080,
             "link": f"{BASE}/files/v{video_id}_hd.mp4"},
            {"id": 3, "quality": "hd", "file_type": "video/mp4",
             "width": 3840, "height": 2160,
             "link": f"{BASE}/files/v{video_id}_4k.mp4"},
            {"id": 4, "quality": "hd", "file_type": "video/mp4",
             "width": 1080, "height": 1920,
             "link": f"{BASE}/files/v{video_id}_port.mp4"},
            {"id": 5, "quality": "uhd", "file_type": "video/avi",
             "width": 7680, "height": 4320,
             "link": f"{BASE}/files/v{video_id}_8k.avi"},
        ],
    }


VIDEO_SEARCH = {"total_results": 1, "videos": [make_video(201)]}
VIDEO_POPULAR = {"total_results": 1, "videos": [make_video(202)]}

INDEX_HTML = f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<title>Mock Pexels API</title>
<style>
  body {{ font-family: system-ui, sans-serif; max-width: 720px; margin: 2rem auto; padding: 0 1rem; line-height: 1.7; }}
  code, pre {{ background: #f4f4f5; padding: .15rem .35rem; border-radius: 6px; direction: ltr; display: inline-block; }}
  pre {{ padding: .8rem 1rem; }}
  li {{ margin: .3rem 0; }}
  .box {{ background: #ecfdf5; border: 1px solid #10b981; border-radius: 10px; padding: .8rem 1rem; }}
</style>
</head>
<body>
<h1>🧪 Mock Pexels API</h1>
<p>هذا خادم <b>وهمي</b> يحاكي Pexels API لاختبار سكربتات التنزيل في هذا المستودع —
لا يتصل بـ Pexels الحقيقي (شبكة هذه البيئة محجوبة).</p>
<div class="box">
<b>المفتاح:</b> <code>TESTKEY</code> — مرّره في ترويسة <code>Authorization</code>
أو أضف <code>?key=TESTKEY</code> للروابط أدناه (متصفحات الويب لا ترسل ترويسات مخصصة).
</div>
<h2>نقاط النهاية المتاحة</h2>
<ul>
  <li><a href="/v1/search?query=nature&amp;key=TESTKEY">GET /v1/search?query=nature</a> — بحث الصور (صفحتان)</li>
  <li><a href="/v1/videos/search?query=sea&amp;key=TESTKEY">GET /v1/videos/search?query=sea</a> — بحث الفيديو (مسار جديد)</li>
  <li><a href="/videos/search?query=sea&amp;key=TESTKEY">GET /videos/search?query=sea</a> — بحث الفيديو (المسار القديم)</li>
  <li><a href="/v1/videos/popular?key=TESTKEY">GET /v1/videos/popular</a> — الفيديوهات الشائعة</li>
  <li><a href="/v1/videos/videos/28181129?key=TESTKEY">GET /v1/videos/videos/:id</a> — فيديو بالمعرّف (المسار الجديد)</li>
  <li><a href="/v1/videos/videos/16764717?key=TESTKEY">GET /v1/videos/videos/16764717</a> — يرد 404 على المسار الجديد (اختبار التراجع)</li>
  <li><a href="/files/v28181129_4k.mp4">GET /files/…</a> — ملفات وهمية بلا تفويض (مثل CDN الحقيقي)</li>
</ul>
<h2>تجربة السكربت ضد هذا الخادم</h2>
<pre>export PEXELS_API_BASE=http://127.0.0.1:8765
export PEXELS_API_KEY=TESTKEY
python3 download_stock_videos.py</pre>
</body>
</html>"""


class Handler(BaseHTTPRequestHandler):
    def _send_json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_404(self):
        self._send_json({"error": "not found"}, 404)

    def _authorized(self, qs) -> bool:
        if self.headers.get("Authorization") == API_KEY:
            return True
        return qs.get("key", [""])[0] == API_KEY

    def do_GET(self):
        parsed = urlparse(self.path)
        qs = parse_qs(parsed.query)
        page = int(qs.get("page", ["1"])[0])
        path = parsed.path

        # صفحة الاستقبال
        if path == "/":
            body = INDEX_HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        # ملفات "CDN" — بدون تفويض (مثل الواقع)
        if path.startswith("/files/"):
            fname = os.path.basename(path)
            stem = fname.rsplit(".", 1)[0]
            tag_sizes = {"sd": 300, "hd": 600, "4k": 900, "port": 400, "l2x": 800}
            if stem.startswith("v"):
                size = tag_sizes.get(stem.rsplit("_", 1)[-1], 500)
            else:
                size = {"photo_101": 1000, "photo_102": 2000,
                        "photo_103": 3000, "video_201_sd": 100,
                        "video_201_hd": 200, "video_201_4k": 400}.get(stem, 500)
            data = b"x" * size
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Length", str(size))
            self.end_headers()
            self.wfile.write(data)
            return

        # كل مسارات الـ API تتطلب المفتاح الصحيح
        if not self._authorized(qs):
            self._send_json({"error": "invalid key"}, 401)
            return

        if path in ("/v1/search", "/search"):
            if page == 1:
                self._send_json({"total_results": 3, "photos": PHOTOS_P1})
            else:
                self._send_json({"total_results": 3, "photos": PHOTOS_P2})
        elif path in ("/v1/videos/search", "/videos/search"):
            self._send_json(VIDEO_SEARCH)
        elif path in ("/v1/videos/popular", "/videos/popular", "/videos/curated"):
            self._send_json(VIDEO_POPULAR)
        elif m := re.fullmatch(r"/(?:v1/)?videos/videos/(\d+)", path):
            video_id = int(m.group(1))
            if video_id == LEGACY_ONLY_ID and path.startswith("/v1/"):
                self._send_404()  # محاكاة مسار جديد ناقص لاختبار التراجع
            else:
                self._send_json(make_video(video_id))
        else:
            self._send_404()

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", PORT), Handler)
    print(f"Mock Pexels API listening on 0.0.0.0:{PORT} (key: {API_KEY})", flush=True)
    server.serve_forever()
