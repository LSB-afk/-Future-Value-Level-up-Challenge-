"""매물별 문제 제보 저장소.

사용자·이웃·중개사가 보낸 제보를 매물 키별로 쌓는다. 제보는 핏홈이 확인하기 전까지
"미검증"으로 남고, 판정에서는 '주의' 신호 하나로만 반영된다.

입력이 잘못되면 ValueError(HTTP 400), 저장 실패는 OSError를 그대로 올린다(HTTP 500).
"""

from __future__ import annotations

import json
import os
import re
import tempfile
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
KEY_PATTERN = re.compile(r"^(apt|listing):[A-Za-z0-9_-]{1,64}$")
TEXT_MIN, TEXT_MAX = 2, 500
# 파일 하나가 끝없이 커지지 않게 한다. 넘치면 가장 오래된 제보부터 버린다.
MAX_PER_KEY = 200
MAX_TOTAL = 5000
_lock = threading.Lock()


def _load() -> dict:
    if not STORE_PATH.exists():
        return {}
    try:
        data = json.loads(STORE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _save(data: dict) -> None:
    """임시 파일에 다 쓴 뒤 os.replace로 바꿔 끼운다. 도중에 실패해도 기존 파일은 그대로다."""
    STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=STORE_PATH.parent, prefix=STORE_PATH.name, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=1)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, STORE_PATH)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _trim(data: dict, key: str) -> None:
    """매물당 MAX_PER_KEY, 전체 MAX_TOTAL을 넘으면 가장 오래된 제보부터 지운다."""
    data[key] = data[key][-MAX_PER_KEY:]
    overflow = sum(len(items) for items in data.values()) - MAX_TOTAL
    if overflow <= 0:
        return
    newest = (key, len(data[key]) - 1)  # 방금 넣은 제보는 같은 초에 들어온 것끼리 겨뤄도 지우지 않는다
    oldest = sorted(
        (item.get("createdAt", ""), k, i)
        for k, items in data.items() for i, item in enumerate(items) if (k, i) != newest
    )[:overflow]
    drop: dict[str, set[int]] = {}
    for _, k, i in oldest:
        drop.setdefault(k, set()).add(i)
    for k, indexes in drop.items():
        data[k] = [item for i, item in enumerate(data[k]) if i not in indexes]
        if not data[k]:
            del data[k]


def list_feedback(key: str) -> list[dict]:
    with _lock:
        items = _load().get(key, [])
    if not isinstance(items, list):
        return []
    return sorted(items, key=lambda item: item.get("createdAt", ""), reverse=True)


def add_feedback(key: str, category: str, text: str, role: str) -> dict:
    key = (key or "").strip()
    text = (text or "").strip()
    role = (role or "").strip() or "visitor"
    if not KEY_PATTERN.match(key):
        raise ValueError("매물 키가 올바르지 않습니다.")
    if category not in CATEGORIES:
        raise ValueError("제보 종류를 선택해주세요.")
    if role not in ROLES:
        raise ValueError("제보자 구분이 올바르지 않습니다.")
    if not TEXT_MIN <= len(text) <= TEXT_MAX:
        raise ValueError(f"제보 내용은 {TEXT_MIN}자 이상 {TEXT_MAX}자 이하로 적어주세요.")
    item = {
        "id": uuid.uuid4().hex[:10],
        "category": category,
        "categoryLabel": CATEGORIES[category],
        "role": role,
        "roleLabel": ROLES[role],
        "text": text,
        "status": "unverified",
        "statusLabel": "접수 · 미검증",
        "createdAt": datetime.now().isoformat(timespec="seconds"),
    }
    with _lock:
        data = _load()
        items = data.get(key)
        data[key] = (items if isinstance(items, list) else []) + [item]
        _trim(data, key)
        _save(data)
    return item


if __name__ == "__main__":
    STORE_PATH = Path(tempfile.mkdtemp()) / "feedback.json"
    saved = add_feedback("apt:A13593908", "condition", "욕실 천장에 누수 자국이 있어요", "visitor")
    assert list_feedback("apt:A13593908")[0]["id"] == saved["id"]
    assert add_feedback("listing:A13593908-L1", "info", "층수가 달라요", "")["role"] == "visitor"
    bad_inputs = (
        ("", "info", "내용입니다", "tenant"),
        ("demo-x", "info", "내용입니다", "tenant"),  # 접두어 없음
        ("apt:../../etc", "info", "내용입니다", "tenant"),
        ("apt:" + "a" * 65, "info", "내용입니다", "tenant"),
        ("apt:A1", "nope", "내용입니다", "tenant"),
        ("apt:A1", "info", "x", "tenant"),
        ("apt:A1", "info", "가" * 501, "tenant"),
        ("apt:A1", "info", "내용입니다", "admin"),
    )
    for bad in bad_inputs:
        try:
            add_feedback(*bad)
            raise AssertionError(bad)
        except ValueError:
            pass

    MAX_PER_KEY, MAX_TOTAL = 3, 100
    for n in range(4):
        add_feedback("apt:CAP", "other", f"제보 {n}번", "tenant")
    assert {i["text"] for i in list_feedback("apt:CAP")} == {"제보 1번", "제보 2번", "제보 3번"}  # 가장 오래된 0번이 빠졌다
    MAX_TOTAL = 4  # 지금 5건 → 한 건 더 넣으면 오래된 것부터 2건이 빠져 4건
    add_feedback("apt:NEW", "other", "새 제보입니다", "tenant")
    stored = json.loads(STORE_PATH.read_text(encoding="utf-8"))
    assert sum(len(v) for v in stored.values()) == MAX_TOTAL, stored
    assert all(stored.values()), stored  # 비게 된 매물 키는 지운다

    # 쓰기 도중 실패해도 기존 파일은 깨지지 않고, 임시 파일도 남지 않는다.
    before = STORE_PATH.read_text(encoding="utf-8")
    real_dump = json.dump
    json.dump = lambda *a, **k: (_ for _ in ()).throw(OSError("disk full"))
    try:
        add_feedback("apt:CAP", "other", "실패할 제보", "tenant")
        raise AssertionError("OSError expected")
    except OSError:
        pass
    finally:
        json.dump = real_dump
    assert STORE_PATH.read_text(encoding="utf-8") == before
    assert not list(STORE_PATH.parent.glob("*.tmp"))
    print("property_feedback self-check OK")
