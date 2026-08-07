#!/usr/bin/env python3
"""Assemble the static GitHub Pages build into site/.

Deploy (gh-pages branch):
    python3 scripts/build_pages.py
    git worktree add ../movevalue-pages gh-pages
    rsync -a --delete --exclude .git site/ ../movevalue-pages/
    cd ../movevalue-pages && git add -A && git commit -m "Deploy Pages build" && git push origin gh-pages
"""

from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"

PY_FILES = [
    "env_loader.py",
    "route_adapters.py",
    "real_estate_price_adapters.py",
    "jeonse_safeguard.py",
    "property_model.py",
    "apartment_adapters.py",
    "property_adapters.py",
    "movevalue_api.py",
    "static_dispatcher.py",
]
DATA_FILES = ["areas.actual.json", "apartments.seoul.snapshot.json"]


def main() -> None:
    shutil.rmtree(SITE, ignore_errors=True)
    (SITE / "py").mkdir(parents=True)
    (SITE / "data").mkdir()

    index = (ROOT / "app" / "index.html").read_text(encoding="utf-8")
    marker = '<script src="./app.js"></script>'
    assert marker in index, "app.js script tag not found in app/index.html"
    index = index.replace(marker, f'<script src="./static-api.js"></script>\n    {marker}')
    (SITE / "index.html").write_text(index, encoding="utf-8")

    for name in ("app.js", "styles.css", "static-api.js"):
        shutil.copy2(ROOT / "app" / name, SITE / name)
    for name in PY_FILES:
        shutil.copy2(ROOT / "api" / name, SITE / "py" / name)
    for name in DATA_FILES:
        shutil.copy2(ROOT / "data" / name, SITE / "data" / name)
    (SITE / ".nojekyll").write_text("", encoding="utf-8")
    print(f"built {SITE}")


if __name__ == "__main__":
    main()
