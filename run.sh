#!/usr/bin/env bash
# تشغيل مِداد على Linux / macOS
set -e
cd "$(dirname "$0")"
if [ ! -d ".venv" ]; then
  echo "→ إنشاء بيئة افتراضية…"
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements.txt
python midad.py "$@"
