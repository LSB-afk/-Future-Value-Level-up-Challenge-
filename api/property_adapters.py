"""Property dashboard API adapters."""

from __future__ import annotations

from apartment_adapters import apartment_credential_status, load_apartment_dataset
from property_model import build_property_detail, build_property_preview, property_agent_answer
from real_estate_price_adapters import price_credential_status


def single_value(raw: dict[str, list[str]], name: str, default: str = "") -> str:
    return raw.get(name, [default])[0].strip()


def load_apartments() -> tuple[list[dict], dict, str, str]:
    dataset, source_mode, source_error = load_apartment_dataset()
    return list(dataset.get("apartments", [])), dataset.get("meta", {}), source_mode, source_error


def find_apartment(raw: dict[str, list[str]]) -> dict:
    property_id = single_value(raw, "id") or single_value(raw, "propertyId")
    query = (single_value(raw, "q") or single_value(raw, "name") or property_id).lower()
    apartments, _, _, _ = load_apartments()
    if not query:
        raise ValueError("id 또는 q 파라미터가 필요합니다.")

    for item in apartments:
        if str(item.get("id", "")).lower() == query:
            return item

    matches = [
        item
        for item in apartments
        if query in item.get("name", "").lower()
        or query in item.get("address", "").lower()
        or query in item.get("dong", "").lower()
    ]
    if matches:
        return sorted(matches, key=lambda item: item.get("households", 0), reverse=True)[0]

    raise ValueError(f"단지 정보를 찾을 수 없습니다: {query}")


def comparison_candidates(limit: int = 80) -> list[dict]:
    apartments, _, _, _ = load_apartments()
    rows = []
    for item in apartments[:limit]:
        rows.append(
            {
                "id": item.get("id"),
                "name": item.get("name"),
                "address": item.get("address"),
                "preview": build_property_preview(item),
            }
        )
    return rows


def property_detail_response(raw: dict[str, list[str]]) -> dict:
    apartment = find_apartment(raw)
    apartments, meta, source_mode, source_error = load_apartments()
    detail = build_property_detail(apartment)
    return {
        "ok": True,
        "detail": detail,
        "meta": {
            "sourceMode": source_mode,
            "sourceError": source_error,
            "complete": bool(meta.get("complete")),
            "totalRecords": int(meta.get("totalRecords") or len(apartments)),
            "availableRecords": int(meta.get("recordsWithCoordinates") or len(apartments)),
            "note": "단지 상세 대시보드는 실데이터 필드와 추정/연계 예정 필드를 dataStatus로 구분합니다.",
        },
        "integrations": {**apartment_credential_status(), **price_credential_status()},
    }


def property_agent_response(raw: dict[str, list[str]]) -> dict:
    apartment = find_apartment(raw)
    detail = build_property_detail(apartment)
    question = single_value(raw, "question", "이 단지 전세 들어가도 괜찮아?")
    answer = property_agent_answer(question, detail, comparison_candidates())
    return {"ok": True, "question": question, "propertyId": detail["id"], "agent": answer}
