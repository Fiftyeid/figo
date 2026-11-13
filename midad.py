#!/usr/bin/env python3
"""مِداد (Midad) — مشغّل التطبيق المحلي.

يشغّل الخادم على جهازك ثم يفتح الواجهة في نافذة تطبيق (Chrome/Edge app mode)
أو في المتصفح الافتراضي. لا يحتاج إنترنت إلا عند استخدام مفاتيح الذكاء الاصطناعي.

الاستخدام:
    python midad.py                 # يفتح المتصفح تلقائيًا
    python midad.py --port 9000     # منفذ آخر
    python midad.py --no-browser    # بدون فتح المتصفح
"""
from __future__ import annotations

import argparse
import os
import shutil
import socket
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

BANNER = r"""
   __  __ ___ ____   _   ____
  |  \/  |_ _|  _ \ / \ |  _ \
  | |\/| || || | | / _ \| | | |
  | |  | || || |_| / ___ \ |_| |
  |_|  |_|___|____/_/   \_\____/
  استوديو كتب التلوين — متوافق مع Amazon KDP
"""


def free_port(start: int) -> int:
    for port in range(start, start + 40):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    return start


def wait_ready(port: int, timeout: float = 40.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.4):
                return True
        except OSError:
            time.sleep(0.25)
    return False


def chrome_candidates() -> list[str]:
    if sys.platform.startswith("win"):
        bases = [
            os.environ.get("PROGRAMFILES", r"C:\Program Files"),
            os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)"),
            os.environ.get("LOCALAPPDATA", ""),
        ]
        names = [
            r"Google\Chrome\Application\chrome.exe",
            r"Microsoft\Edge\Application\msedge.exe",
            r"BraveSoftware\Brave-Browser\Application\brave.exe",
        ]
        return [str(Path(b) / n) for b in bases if b for n in names]
    if sys.platform == "darwin":
        return [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        ]
    return [
        shutil.which("google-chrome") or "",
        shutil.which("chromium") or "",
        shutil.which("chromium-browser") or "",
        shutil.which("microsoft-edge") or "",
    ]


def open_window(url: str) -> None:
    if os.environ.get("MIDAD_NO_APP_WINDOW") == "1":
        webbrowser.open(url)
        return
    for exe in chrome_candidates():
        if exe and Path(exe).exists():
            try:
                profile = ROOT / "data" / ".app-window"
                profile.mkdir(parents=True, exist_ok=True)
                subprocess.Popen(
                    [
                        exe,
                        f"--app={url}",
                        f"--user-data-dir={profile}",
                        "--window-size=1440,960",
                        "--no-first-run",
                        "--no-default-browser-check",
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                print(" → تم فتح نافذة التطبيق.")
                return
            except Exception:
                continue
    webbrowser.open(url)
    print(" → تم فتح الواجهة في المتصفح.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Midad — local KDP coloring book studio")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args()

    os.chdir(ROOT)
    port = free_port(args.port)
    url = f"http://127.0.0.1:{port}"

    print(BANNER)
    print(f"  المجلد: {ROOT}")
    print(f"  العنوان: {url}")
    print("  لإيقاف التطبيق اضغط Ctrl + C\n")

    if not args.no_browser:
        threading.Thread(target=lambda: (wait_ready(port), time.sleep(0.6), open_window(url)), daemon=True).start()

    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=args.host,
        port=port,
        reload=args.reload,
        log_level="warning",
    )


if __name__ == "__main__":
    main()
