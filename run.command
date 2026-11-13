#!/usr/bin/env bash
# انقر مرتين على هذا الملف في macOS لتشغيل مِداد
cd "$(dirname "$0")"
if [ ! -d ".venv" ]; then python3 -m venv .venv; fi
source .venv/bin/activate
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements.txt
python midad.py
