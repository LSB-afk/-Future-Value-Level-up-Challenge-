"""Small .env loader for local MoveValue development.

The project avoids a runtime dependency on python-dotenv, so optional API keys
can be loaded from the repository-level .env file with this helper.
"""

from __future__ import annotations

import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"


def _clean_value(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def load_dotenv(path: Path = ENV_PATH) -> None:
    if not path.is_file():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        name = name.strip()
        if not name or name in os.environ:
            continue
        os.environ[name] = _clean_value(value)
