"""매물별 문제 제보 저장소.

사용자·이웃·중개사가 보낸 제보를 매물 키별로 쌓는다. 제보는 핏홈이 확인하기 전까지
"미검증"으로 남고, 판정에서는 '주의' 신호 하나로만 반영된다.
"""

from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime
from pathlib import Path

# ponytail: 단일 JSON 파일 + 프로세스 락. 동시 사용자가 늘면 DB로 옮긴다.
STORE_PATH = Path(__file__).resolve().parents[1] / "data" / "property_feedback.json"
CATEGORIES = {
    "info": "정보가 달라요",
    "condition": "집 상태 문제",
    "landlord": "임대인·중개사 문제",
    "other": "기타",
}
ROLES = {"tenant": "세입자", "neighbor": "이웃", "broker": "중개사", "visitor": "방문자"}
_lock = threading.Lock()


def _load() -> dict:
    if not STORE_PATH.exists():
        return {}
    try:
        return json.loads(STORE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def list_feedback(key: str) -> list[dict]:
    with _lock:
        items = _load().get(key, [])
    return sorted(items, key=lambda item: item.get("createdAt", ""), reverse=True)


def add_feedback(key: str, category: str, text: str, role: str) -> dict:
    key = (key or "").strip()
    text = (text or "").strip()
    if not key or len(key) > 80:
        raise ValueError("매물 키가 올바르지 않습니다.")
    if category not in CATEGORIES:
        raise ValueError("제보 종류를 선택해주세요.")
    if not 2 <= len(text) <= 500:
        raise ValueError("제보 내용은 2자 이상 500자 이하로 적어주세요.")
    item = {
        "id": uuid.uuid4().hex[:10],
        "category": category,
        "categoryLabel": CATEGORIES[category],
        "role": role if role in ROLES else "visitor",
        "roleLabel": ROLES.get(role, "방문자"),
        "text": text,
        "status": "unverified",
        "statusLabel": "접수 · 미검증",
        "createdAt": datetime.now().isoformat(timespec="seconds"),
    }
    with _lock:
        data = _load()
        data.setdefault(key, []).append(item)
        STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
        tmp = STORE_PATH.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        tmp.replace(STORE_PATH)
    return item


if __name__ == "__main__":
    import tempfile

    STORE_PATH = Path(tempfile.mkdtemp()) / "feedback.json"
    saved = add_feedback("demo-x", "condition", "욕실 천장에 누수 자국이 있어요", "visitor")
    assert list_feedback("demo-x")[0]["id"] == saved["id"]
    for bad in (("", "info", "내용", "tenant"), ("k", "nope", "내용", "tenant"), ("k", "info", "x", "tenant")):
        try:
            add_feedback(*bad)
            raise AssertionError(bad)
        except ValueError:
            pass
    print("property_feedback self-check OK")
