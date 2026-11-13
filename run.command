#!/usr/bin/env bash
# انقر مرتين على هذا الملف في macOS لتشغيل مِداد
cd "$(dirname "$0")"
chmod +x run.sh 2>/dev/null || true
./run.sh
