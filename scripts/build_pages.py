#!/usr/bin/env python3
"""Assemble the static GitHub Pages build into site/.

Deploy (gh-pages branch):
    python3 scripts/build_pages.py            # or --out <dir> to build somewhere else
    git worktree add ../movevalue-pages gh-pages
    rsync -a --delete --exclude .git site/ ../movevalue-pages/
    cd ../movevalue-pages && git add -A && git commit -m "Deploy Pages build" && git push origin gh-pages

The build is assembled and checked in a temporary directory first; the existing
output is replaced only after every check passes.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app"
API = ROOT / "api"
SITE = ROOT / "site"

ENTRY_MODULE = "static_dispatcher"
DATA_FILES = ["areas.actual.json", "apartments.seoul.snapshot.json"]
# index.html의 로컬 .js/.css 참조(./app.js?v=... 처럼 쿼리가 붙어 있어도 됨). 내용 해시로 ?v=를 다시 붙인다.
LOCAL_REF = re.compile(r'(src|href)="\./([^"?#]+\.(?:js|css))(?:\?[^"]*)?"')
APP_SCRIPT = re.compile(r'<script src="\./app\.js(?:\?[^"]*)?"></script>')


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:10]


def python_modules() -> list[str]:
    """static_dispatcher가 모듈 최상위에서 import하는 api/ 모듈 전체(전이 포함).

    함수 안의 지연 import(agent_llm 등 정적 빌드에서 안 쓰는 경로)는 따라가지 않는다.
    """
    seen: list[str] = []
    stack = [ENTRY_MODULE]
    while stack:
        name = stack.pop()
        if name in seen:
            continue
        seen.append(name)
        tree = ast.parse((API / f"{name}.py").read_text(encoding="utf-8"))
        for node in tree.body:
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
                names = [node.module]
            else:
                continue
            stack += [n for n in names if (API / f"{n}.py").exists()]
    return sorted(f"{name}.py" for name in seen)


def build_index(asset_hashes: dict[str, str]) -> str:
    index = (APP / "index.html").read_text(encoding="utf-8")
    app_tags = APP_SCRIPT.findall(index)
    assert len(app_tags) == 1, f"app.js script tag not found exactly once in app/index.html: {app_tags}"
    missing = [path for _, path in LOCAL_REF.findall(index) if path not in asset_hashes]
    assert not missing, f"app/index.html references files that are not in app/: {missing}"

    # 해시를 붙이지 않으면 새 index.html이 캐시된 옛 app.js와 짝을 이뤄
    # 새 탭 마크업만 있고 렌더러가 없는 상태로 깨진다.
    index = LOCAL_REF.sub(lambda m: f'{m.group(1)}="./{m.group(2)}?v={asset_hashes[m.group(2)]}"', index)
    app_tag = APP_SCRIPT.search(index).group(0)
    shim_tag = f'<script src="./static-api.js?v={asset_hashes["static-api.js"]}"></script>'
    return index.replace(app_tag, f"{shim_tag}\n    {app_tag}", 1)


def build_shim(py_files: list[str]) -> str:
    """static-api.js는 Pyodide 파일시스템에 쓸 파일 목록을 하드코딩한다. 빌드가 실제로 넣은 목록으로 맞춘다."""
    shim = (APP / "static-api.js").read_text(encoding="utf-8")
    for name, values in (("PY_FILES", py_files), ("DATA_FILES", DATA_FILES)):
        pattern = re.compile(rf"const {name} = \[[^\]]*\];")
        assert len(pattern.findall(shim)) == 1, f"{name} array not found exactly once in app/static-api.js"
        shim = pattern.sub(f"const {name} = {json.dumps(values, ensure_ascii=False)};", shim)
    return shim


def check_imports(out: Path) -> None:
    """빌드된 py/와 data/만으로 static_dispatcher import가 되는지 확인한다(Pyodide와 같은 배치)."""
    code = f"import sys; sys.path.insert(0, {str(out / 'py')!r}); import {ENTRY_MODULE}"
    result = subprocess.run([sys.executable, "-I", "-B", "-c", code], cwd=out, capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, f"built site cannot import {ENTRY_MODULE}:\n{result.stderr[-2000:]}"


def assemble(out: Path) -> list[str]:
    py_files = python_modules()
    shutil.copytree(APP, out, ignore=shutil.ignore_patterns("index.html", "static-api.js"))
    shim = build_shim(py_files)
    (out / "static-api.js").write_text(shim, encoding="utf-8")

    asset_hashes = {
        str(path.relative_to(out)).replace("\\", "/"): digest(path.read_bytes())
        for path in out.rglob("*") if path.is_file() and path.suffix in {".js", ".css"}
    }
    (out / "index.html").write_text(build_index(asset_hashes), encoding="utf-8")

    (out / "py").mkdir()
    (out / "data").mkdir()
    for name in py_files:
        shutil.copy2(API / name, out / "py" / name)
    for name in DATA_FILES:
        shutil.copy2(ROOT / "data" / name, out / "data" / name)
    (out / ".nojekyll").write_text("", encoding="utf-8")
    check_imports(out)
    return py_files


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=SITE, help="output directory (default: site/)")
    target = parser.parse_args().out.resolve()

    target.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{target.name}-build-", dir=target.parent))
    try:
        py_files = assemble(staging / "out")
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    # 모든 검사를 통과한 뒤에만 기존 출력을 바꾼다.
    backup = staging / "previous"
    if target.exists():
        target.rename(backup)
    (staging / "out").rename(target)
    shutil.rmtree(staging, ignore_errors=True)
    print(f"built {target} ({len(py_files)} python modules: {', '.join(py_files)})")


if __name__ == "__main__":
    main()
