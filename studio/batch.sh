#!/usr/bin/env bash
# Regenerate every thumbnail from ../configs
set -e
cd "$(dirname "$0")/.."
for f in configs/*.json; do echo "→ $f"; python3 tools/make_thumbnail.py "$f"; done
