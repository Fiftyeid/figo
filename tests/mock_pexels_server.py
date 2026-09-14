#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""خادم وهمي يحاكي Pexels API لاختبار السكربت من البداية للنهاية."""
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
BASE = f"http://127.0.0.1:{PORT}"

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
VIDEO = {
    "id": 201, "width": 3840, "height": 2160, "duration": 12,
    "url": f"{BASE}/video/201", "user": {"name": "Lina"},
    "video_files": [
        {"id": 1, "quality": "sd", "file_type": "video/mp4", "width": 640, "height": 360,
         "link": f"{BASE}/files/video_201_sd.mp4"},
        {"id": 2, "quality": "hd", "file_type": "video/mp4", "width": 1920, "height": 1080,
         "link": f"{BASE}/files/video_201_hd.mp4"},
        {"id": 3, "quality": "hd", "file_type": "video/mp4", "width": 3840, "height": 2160,
         "link": f"{BASE}/files/video_201_4k.mp4"},
    ],
}


class Handler(BaseHTTPRequestHandler):
    def _send_json(self, obj, code=200):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        qs = parse_qs(parsed.query)
        page = int(qs.get("page", ["1"])[0])
        if parsed.path.startswith("/files/"):
            fname = os.path.basename(parsed.path)
            if "video" in fname:
                size = {"video_201_sd": 100, "video_201_hd": 200, "video_201_4k": 400}.get(
                    fname.rsplit(".", 1)[0], 100)
            else:
                size = {"photo_101": 1000, "photo_101_l2x": 800,
                        "photo_102": 2000, "photo_103": 3000}.get(fname.rsplit(".", 1)[0], 500)
            data = b"x" * size
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Length", str(size))
            self.end_headers()
            self.wfile.write(data)
            return
        if self.headers.get("Authorization") != "TESTKEY":
            self._send_json({"error": "invalid key"}, 401)
            return
        if parsed.path == "/v1/search":
            if page == 1:
                self._send_json({"total_results": 3, "photos": PHOTOS_P1})
            else:
                self._send_json({"total_results": 3, "photos": PHOTOS_P2})
        elif parsed.path == "/videos/search":
            self._send_json({"total_results": 1, "videos": [VIDEO]})
        else:
            self._send_json({"error": "not found"}, 404)

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    HTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
