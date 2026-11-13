#!/usr/bin/env bash
# تشغيل مِداد على Linux / macOS
set -e
cd "$(dirname "$0")"

PY=python3
command -v $PY >/dev/null 2>&1 || PY=python
$PY -c 'import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)' || {
  echo "  [X] Python 3.10+ is required."; exit 1; }

if [ ! -d ".venv" ]; then
  echo "  [1/3] إنشاء بيئة افتراضية…"
  $PY -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate

if [ -d "wheels" ]; then
  echo "  [2/3] تثبيت المتطلبات من مجلد wheels (بدون إنترنت)…"
  python -m pip install --quiet --disable-pip-version-check --no-index --find-links wheels -r requirements.txt \
    || python -m pip install --quiet --disable-pip-version-check -r requirements.txt
else
  echo "  [2/3] تثبيت المتطلبات (يحتاج إنترنت مرة واحدة)…"
  python -m pip install --quiet --disable-pip-version-check -r requirements.txt
fi

echo "  [3/3] تشغيل مِداد…"
exec python midad.py "$@"
