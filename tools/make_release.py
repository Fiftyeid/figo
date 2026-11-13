#!/usr/bin/env python3
"""يبني حزم التوزيع (ZIP) من مجلد المشروع.

    python tools/make_release.py                     # حزمة عالمية (بدون wheels)
    python tools/make_release.py --wheels /tmp/wheels --suffix win64-offline
"""
from __future__ import annotations

import argparse
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "releases"
VERSION = "1.0"

INCLUDE = [
    "midad.py", "requirements.txt", "README.md", "QUICK-START.txt", "LICENSE.md",
    "run.bat", "run.sh", "run.command",
]
INCLUDE_DIRS = ["app"]
EXCLUDE_PARTS = {"__pycache__", ".git", ".venv", "data", "dist", "releases", "node_modules", ".mypy_cache"}


def add_file(zf: zipfile.ZipFile, path: Path, arc_root: str) -> None:
    zf.write(path, arcname=f"{arc_root}/{path.relative_to(ROOT).as_posix()}")


def build(wheels: Path | None, suffix: str) -> Path:
    name = f"midad-kdp-studio-v{VERSION}" + (f"-{suffix}" if suffix else "")
    out = DIST / f"{name}.zip"
    DIST.mkdir(exist_ok=True)
    root = name
    count = 0
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for rel in INCLUDE:
            p = ROOT / rel
            if p.exists():
                add_file(zf, p, root)
                count += 1
        for d in INCLUDE_DIRS:
            for p in sorted((ROOT / d).rglob("*")):
                if not p.is_file() or EXCLUDE_PARTS & set(p.parts):
                    continue
                if p.suffix in (".pyc", ".pyo", ".log"):
                    continue
                add_file(zf, p, root)
                count += 1
        (ROOT / "data").mkdir(exist_ok=True)
        zf.writestr(f"{root}/data/.gitkeep", "")
        if wheels and wheels.exists():
            for whl in sorted(wheels.glob("*.whl")):
                zf.write(whl, arcname=f"{root}/wheels/{whl.name}")
                count += 1
        zf.writestr(f"{root}/VERSION.txt", f"{name}\nbuilt from branch arena/c9b008d2-figo\n")
    size = out.stat().st_size / 1048576
    print(f"✓ {out}  ({count} ملفًا، {size:.1f} MB)")
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--wheels", type=Path, default=None)
    ap.add_argument("--suffix", default="")
    args = ap.parse_args()
    build(args.wheels, args.suffix)


if __name__ == "__main__":
    main()
