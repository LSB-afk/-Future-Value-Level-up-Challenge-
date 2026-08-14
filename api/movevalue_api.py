#!/usr/bin/env python3
"""MoveValue API server.

No external runtime dependency is required. The server exposes JSON API routes
and serves the static web prototype from the same origin.
"""

from __future__ import annotations

import argparse
import json
import math
import mimetypes
import re
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from apartment_adapters import apartment_credential_status, apartments_response, load_apartment_dataset
from property_adapters import property_agent_response, property_detail_response
from property_model import build_property_preview, estimate_market, nearest_living_area
from real_estate_price_adapters import price_credential_status
from route_adapters import build_commute_route, credential_status, resolve_location, search_locations_with_kakao


ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "app"
DATA_PATH = ROOT / "data" / "areas.actual.json"
TMAP_TRANSIT_SOURCE_META = {
    "name": "TMAP 대중교통 경로 API 어댑터",
    "url": "https://transit.tmapmobility.com/guide/procedure",
    "apiKeyEnv": "TMAP_APP_KEY",
    "fallback": "API 키 미설정 또는 호출 실패 시 거리 기반 폴백 경로를 사용합니다.",
}


DESTINATIONS = {
    "gangnam": {"label": "강남 업무지구", "address": "서울 강남구 역삼동", "lat": 37.4979, "lng": 127.0276},
    "yeouido": {"label": "여의도", "address": "서울 영등포구 여의도동", "lat": 37.5219, "lng": 126.9245},
    "seoulStation": {"label": "서울역/도심", "address": "서울 중구 봉래동2가", "lat": 37.5563, "lng": 126.9723},
    "digital": {"label": "구로디지털단지", "address": "서울 구로구 구로동", "lat": 37.4853, "lng": 126.9015},
    "pangyo": {"label": "판교", "address": "경기도 성남시 분당구 삼평동", "lat": 37.3947, "lng": 127.1112},
}
AREA_ADDRESSES = {
    "konkuk": "서울 광진구 화양동",
    "sillim": "서울 관악구 신림동",
    "cheongnyangni": "서울 동대문구 청량리동",
    "wangsimni": "서울 성동구 행당동",
    "guro": "서울 구로구 구로동",
    "gongdeok": "서울 마포구 공덕동",
    "magok": "서울 강서구 마곡동",
    "sangam": "서울 마포구 상암동",
    "gimpoairport": "서울 강서구 공항동",
}

VALID_PERSONAS = {"single", "family", "newlywed", "senior"}
PERSONA_DEFAULT_WEIGHTS = {
    "single": {"commute": 30, "cost": 35, "service": 15, "safety": 20},
    "newlywed": {"commute": 25, "cost": 30, "service": 25, "safety": 20},
    "family": {"commute": 15, "cost": 20, "service": 35, "safety": 30},
    "senior": {"commute": 10, "cost": 20, "service": 35, "safety": 35},
}
DEFAULT_WEIGHTS = PERSONA_DEFAULT_WEIGHTS["single"]
SOC_CATEGORY_DEFINITIONS = {
    "medical": {
        "label": "의료",
        "aliases": ["medical", "hospital", "clinic", "pharmacy", "emergency"],
        "targetCount": 3,
    },
    "transport": {
        "label": "교통",
        "aliases": ["transport", "subway", "station", "busStop", "bus_stop", "transferCenter", "transfer_center"],
        "targetCount": 4,
    },
    "convenience": {
        "label": "생활편의",
        "aliases": ["convenience", "convenienceStore", "convenience_store", "mart", "bank", "laundry"],
        "targetCount": 6,
    },
    "education": {
        "label": "교육",
        "aliases": ["education", "school", "daycare", "kindergarten", "elementarySchool", "elementary_school", "academy"],
        "targetCount": 4,
    },
    "leisure": {
        "label": "여가·복지",
        "aliases": ["leisure", "park", "trail", "sports", "gym"],
        "targetCount": 3,
    },
    "welfare": {
        "label": "복지시설",
        "aliases": ["welfare", "communityCenter", "community_center", "welfareCenter", "welfare_center", "seniorWelfare", "senior_welfare"],
        "targetCount": 3,
    },
}
SOC_PERSONA_WEIGHTS = {
    "single": {"medical": 15, "transport": 30, "convenience": 35, "education": 5, "leisure": 10, "welfare": 5},
    "family": {"medical": 15, "transport": 15, "convenience": 20, "education": 35, "leisure": 10, "welfare": 5},
    "newlywed": {"medical": 15, "transport": 20, "convenience": 20, "education": 25, "leisure": 15, "welfare": 5},
    "senior": {"medical": 35, "transport": 10, "convenience": 10, "education": 0, "leisure": 15, "welfare": 30},
}


@dataclass
class Query:
    budget: float
    destination: str
    destination_query: str
    destination_location: dict
    persona: str
    weights: dict[str, float]
    limit: int


def clamp(value: float, minimum: float = 0, maximum: float = 100) -> float:
    return max(minimum, min(maximum, value))


def number(value: object, fallback: float = 0) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return fallback
    if math.isnan(numeric) or math.isinf(numeric):
        return fallback
    return numeric


def soc_count_from_aliases(sources: list[dict], aliases: list[str]) -> tuple[float, bool]:
    count = 0.0
    has_value = False
    for source in sources:
        if not isinstance(source, dict):
            continue
        count = 0.0
        has_value = False
        for alias in aliases:
            if alias in source:
                count += number(source.get(alias))
                has_value = True
        if has_value:
            return count, has_value
    return count, has_value


def score_from_facility_count(count: float, target_count: float) -> float:
    return clamp(45 + min(max(count, 0) / max(target_count, 1), 1) * 55)


def soc_category_scores(area: dict) -> dict[str, int]:
    base_score = clamp(number(area.get("serviceScore", area.get("socScore", 70)), 70))
    soc = area.get("socSummary", {}) if isinstance(area.get("socSummary"), dict) else {}
    evidence = area.get("evidence", {}) if isinstance(area.get("evidence"), dict) else {}
    counts = soc.get("counts", {}) if isinstance(soc.get("counts"), dict) else {}
    category_counts = (
        soc.get("categoryCounts")
        or soc.get("countsByCategory")
        or evidence.get("socCategoryCounts")
        or {}
    )
    category_scores = soc.get("categoryScores") or area.get("socCategoryScores") or evidence.get("socCategoryScores") or {}
    scores: dict[str, int] = {}

    for key, definition in SOC_CATEGORY_DEFINITIONS.items():
        if key in category_scores:
            scores[key] = round(clamp(number(category_scores.get(key), base_score)))
            continue
        if key == "transport":
            scores[key] = round(clamp(number(area.get("transitScore"), base_score)))
            continue
        count, has_value = soc_count_from_aliases(
            [category_counts, counts, evidence.get("socCounts", {})],
            definition["aliases"],
        )
        scores[key] = round(score_from_facility_count(count, definition["targetCount"]) if has_value else base_score)
    return scores


def persona_soc_score(area: dict, persona: str) -> dict:
    scores = soc_category_scores(area)
    weights = SOC_PERSONA_WEIGHTS.get(persona, SOC_PERSONA_WEIGHTS["single"])
    total_weight = sum(weights.values()) or 100
    weighted = sum(number(scores.get(key), 70) * weight for key, weight in weights.items())
    return {
        "score": round(clamp(weighted / total_weight)),
        "categoryScores": scores,
        "weights": weights,
    }


def soc_summary_text(area: dict, persona: str, limit: int = 3) -> str:
    scoring = persona_soc_score(area, persona)
    category_keys = sorted(
        (key for key, weight in scoring["weights"].items() if weight > 0),
        key=lambda key: scoring["weights"][key],
        reverse=True,
    )[:limit]
    return " · ".join(
        f"{SOC_CATEGORY_DEFINITIONS[key]['label']} {scoring['categoryScores'].get(key, 0)}점"
        for key in category_keys
    )


def haversine_km(a_lat: float, a_lng: float, b_lat: float, b_lng: float) -> float:
    radius = 6371.0088
    phi1 = math.radians(a_lat)
    phi2 = math.radians(b_lat)
    d_phi = math.radians(b_lat - a_lat)
    d_lambda = math.radians(b_lng - a_lng)
    h = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return radius * 2 * math.atan2(math.sqrt(h), math.sqrt(1 - h))


def estimate_commute_minutes(area: dict, destination: str, destination_location: dict | None = None) -> int:
    explicit = area.get("commuteMinutes", {}).get(destination) if destination_location is None else None
    if explicit:
        return int(explicit)

    dest = destination_location or DESTINATIONS[destination]
    km = haversine_km(float(area["lat"]), float(area["lng"]), dest["lat"], dest["lng"])
    transfer_penalty = max(2, 10 - float(area.get("transitScore", 70)) / 15)
    return int(round(10 + km * 2.65 + transfer_penalty))


def recommendation_reason(area: dict, minutes: int, query: Query) -> str:
    evidence = area.get("evidence", {})
    safety_counts = evidence.get("safetyEnvCounts") or area.get("safetyEnvSummary", {}).get("counts", {})
    monthly_rent = round(float(area.get("rentMonthly10k") or 0))
    budget_delta = round(float(query.budget) - monthly_rent)
    destination_label = query.destination_location.get("label") or DESTINATIONS[query.destination]["label"]
    budget_text = "예산 내" if budget_delta >= 0 else f"예산 {abs(budget_delta)}만원 초과"
    soc_text = soc_summary_text(area, query.persona)
    return (
        f"{destination_label}까지 {minutes}분, 월세 중앙값 {monthly_rent}만원, "
        f"{soc_text}, "
        f"치안시설 {safety_counts.get('police', 0)}개·CCTV {safety_counts.get('cctv', 0)}대 근거로 "
        f"{budget_text} 생활권입니다."
    )


def normalize_query(raw: dict[str, list[str]]) -> Query:
    def number(name: str, default: float, minimum: float, maximum: float) -> float:
        try:
            value = float(raw.get(name, [default])[0])
        except (TypeError, ValueError):
            value = default
        return clamp(value, minimum, maximum)

    destination = raw.get("destination", ["gangnam"])[0]
    if destination not in DESTINATIONS:
        destination = "gangnam"

    destination_query = raw.get("destinationQuery", [""])[0].strip()
    destination_address = raw.get("destinationAddress", [""])[0].strip()
    if destination_query:
        validate_destination_scope(destination_query, destination_address)
    destination_location = dict(DESTINATIONS[destination])
    destination_lat = raw.get("destinationLat", [""])[0].strip()
    destination_lng = raw.get("destinationLng", [""])[0].strip()
    if destination_lat and destination_lng:
        try:
            destination_location = {
                "label": destination_query or DESTINATIONS[destination]["label"],
                "address": destination_address or destination_query or DESTINATIONS[destination]["address"],
                "lat": float(destination_lat),
                "lng": float(destination_lng),
                "source": "prototype_address_input" if destination_query else "preset",
            }
        except ValueError:
            destination_location = dict(DESTINATIONS[destination])
    elif destination_query:
        resolved = resolve_location(destination_address or destination_query, known_locations())
        destination_location = {
            **resolved,
            "label": destination_query,
            "address": destination_address or destination_query,
        }

    persona = raw.get("persona", ["single"])[0]
    if persona not in VALID_PERSONAS:
        persona = "single"

    default_weights = PERSONA_DEFAULT_WEIGHTS.get(persona, DEFAULT_WEIGHTS)
    weights = {
        "commute": number("commuteWeight", default_weights["commute"], 0, 100),
        "cost": number("costWeight", default_weights["cost"], 0, 100),
        "service": number("serviceWeight", default_weights["service"], 0, 100),
        "safety": number("safetyWeight", default_weights["safety"], 0, 100),
    }

    try:
        limit = int(raw.get("limit", [8])[0])
    except (TypeError, ValueError):
        limit = 8

    return Query(
        budget=number("budget", 70, 20, 250),
        destination=destination,
        destination_query=destination_query,
        destination_location=destination_location,
        persona=persona,
        weights=weights,
        limit=max(1, min(limit, 50)),
    )


def load_dataset() -> dict:
    with DATA_PATH.open(encoding="utf-8") as file:
        return json.load(file)


def runtime_meta(meta: dict) -> dict:
    return {
        **meta,
        "transitSource": TMAP_TRANSIT_SOURCE_META,
    }


def destination_addresses() -> dict[str, str]:
    return {key: value["address"] for key, value in DESTINATIONS.items()}


def compact_location_text(value: object) -> str:
    return re.sub(r"\s+", "", str(value or "")).lower()


def seoul_dong_parts(*values: object) -> dict:
    text = " ".join(str(value or "") for value in values)
    compact = compact_location_text(text)
    district_match = re.search(r"서울(?:특별시)?([가-힣]+구)", compact)
    tail = compact[district_match.end():] if district_match else ""
    dong_match = re.search(r"([가-힣]+동(?:\d가)?)", tail) if district_match else None
    road_match = re.search(r"([가-힣0-9]+(?:대로|로|길)(?:\d+길)?)", tail) if district_match else None
    return {
        "ok": bool("서울" in compact and district_match and (dong_match or road_match)),
        "district": district_match.group(1) if district_match else "",
        "dong": dong_match.group(1) if dong_match else "",
        "road": road_match.group(1) if road_match else "",
    }


def _average_location(items: list[dict]) -> tuple[float, float]:
    lat_values = [float(item.get("lat")) for item in items if item.get("lat") is not None]
    lng_values = [float(item.get("lng")) for item in items if item.get("lng") is not None]
    return sum(lat_values) / len(lat_values), sum(lng_values) / len(lng_values)


SEOUL_DISTRICT_DISPLAY_ORDER = [
    "강서구",
    "강북구",
    "영등포구",
    "양천구",
    "성동구",
    "동대문구",
    "중랑구",
    "강남구",
    "종로구",
    "강동구",
    "관악구",
    "광진구",
    "구로구",
    "금천구",
    "노원구",
    "도봉구",
    "동작구",
    "마포구",
    "서대문구",
    "서초구",
    "성북구",
    "송파구",
    "용산구",
    "은평구",
    "중구",
]


def _scope_match_text(*values: object) -> str:
    return compact_location_text(" ".join(str(value or "") for value in values)).replace("서울특별시", "서울시")


def _district_sort_key(district: str) -> tuple[int, str]:
    try:
        return (SEOUL_DISTRICT_DISPLAY_ORDER.index(district), district)
    except ValueError:
        return (len(SEOUL_DISTRICT_DISPLAY_ORDER), district)


def _find_district_in_query(compact_query: str, districts: list[str]) -> str:
    for district in sorted(districts, key=len, reverse=True):
        district_compact = _scope_match_text(district)
        if district_compact and district_compact in compact_query:
            return district
    return ""


def _find_dong_in_query(compact_query: str, dongs: list[str]) -> str:
    for dong in sorted(dongs, key=len, reverse=True):
        dong_compact = _scope_match_text(dong)
        if dong_compact and dong_compact in compact_query:
            return dong
    return ""


def hierarchical_local_location_suggestions(query: str, limit: int) -> list[dict]:
    compact_query = _scope_match_text(query)
    if not compact_query:
        return []

    apartment_dataset, _, _ = load_apartment_dataset()
    by_district: dict[str, list[dict]] = {}
    by_dong: dict[tuple[str, str], list[dict]] = {}
    for apartment in apartment_dataset.get("apartments", []):
        district = str(apartment.get("district") or "").strip()
        dong = str(apartment.get("dong") or "").strip()
        if not district or apartment.get("lat") is None or apartment.get("lng") is None:
            continue
        by_district.setdefault(district, []).append(apartment)
        if dong:
            by_dong.setdefault((district, dong), []).append(apartment)

    districts = sorted(by_district, key=_district_sort_key)
    selected_district = _find_district_in_query(compact_query, districts)
    dongs = sorted({dong for district, dong in by_dong if district == selected_district}) if selected_district else []
    selected_dong = _find_dong_in_query(compact_query, dongs) if dongs else ""
    suggestions: list[dict] = []

    if not selected_district:
        city_query = compact_query in {"서", "서울", "서울시", "서울특별시"} or "서울시".startswith(compact_query)
        if city_query:
            suggestions.append(
                {
                    "type": "city",
                    "label": "서울시",
                    "address": "서울시",
                    "lat": 37.5665,
                    "lng": 126.9780,
                    "district": "",
                    "dong": "",
                    "source": "local_city_scope",
                    "selectable": False,
                    "drilldown": True,
                }
            )
        for district in districts:
            label = f"서울시 {district}"
            match_text = _scope_match_text(label, label.replace("서울시", "서울특별시"), label.replace("서울시", "서울"))
            if not city_query and compact_query not in match_text:
                continue
            lat, lng = _average_location(by_district[district])
            suggestions.append(
                {
                    "type": "district",
                    "label": label,
                    "address": label,
                    "lat": lat,
                    "lng": lng,
                    "district": district,
                    "dong": "",
                    "source": "local_apartment_district",
                    "selectable": False,
                    "drilldown": True,
                }
            )
            if len(suggestions) >= limit:
                return suggestions[:limit]
        return suggestions[:limit]

    district_items = by_district[selected_district]
    district_label = f"서울시 {selected_district}"
    district_lat, district_lng = _average_location(district_items)

    if not selected_dong:
        district_index = compact_query.find(_scope_match_text(selected_district))
        district_tail = compact_query[district_index + len(_scope_match_text(selected_district)):] if district_index >= 0 else ""
        if not district_tail:
            suggestions.append(
                {
                    "type": "district",
                    "label": district_label,
                    "address": district_label,
                    "lat": district_lat,
                    "lng": district_lng,
                    "district": selected_district,
                    "dong": "",
                    "source": "local_apartment_district",
                    "selectable": False,
                    "drilldown": True,
                }
            )
        for dong in dongs:
            label = f"{selected_district} {dong}"
            address = f"서울시 {selected_district} {dong}"
            if compact_query not in _scope_match_text(address, label) and not _scope_match_text(address).startswith(compact_query):
                continue
            dong_lat, dong_lng = _average_location(by_dong[(selected_district, dong)])
            suggestions.append(
                {
                    "type": "dong",
                    "label": label,
                    "address": address,
                    "lat": dong_lat,
                    "lng": dong_lng,
                    "district": selected_district,
                    "dong": dong,
                    "source": "local_apartment_dong",
                    "selectable": True,
                    "drilldown": True,
                }
            )
            if len(suggestions) >= limit:
                return suggestions[:limit]
        return suggestions[:limit]

    dong_items = sorted(
        by_dong.get((selected_district, selected_dong), []),
        key=lambda item: (-(int(item.get("households") or 0)), str(item.get("name") or "")),
    )
    dong_label = f"{selected_district} {selected_dong}"
    dong_address = f"서울시 {selected_district} {selected_dong}"
    dong_lat, dong_lng = _average_location(dong_items)
    suggestions.append(
        {
            "type": "dong",
            "label": dong_label,
            "address": dong_address,
            "lat": dong_lat,
            "lng": dong_lng,
            "district": selected_district,
            "dong": selected_dong,
            "source": "local_apartment_dong",
            "selectable": True,
        }
    )

    for apartment in dong_items:
        name = str(apartment.get("name") or "").strip()
        if not name:
            continue
        label = f"{selected_dong} {name}"
        address = str(apartment.get("address") or dong_address)
        blob = _scope_match_text(label, address, name)
        if compact_query not in blob and not _scope_match_text(dong_address).startswith(compact_query):
            continue
        suggestions.append(
            {
                "type": "apartment",
                "label": label,
                "address": address,
                "lat": apartment.get("lat"),
                "lng": apartment.get("lng"),
                "district": selected_district,
                "dong": selected_dong,
                "apartmentName": name,
                "source": "local_apartment_name",
                "selectable": True,
            }
        )
        if len(suggestions) >= limit:
            break

    return suggestions[:limit]


def local_location_suggestions(query: str, limit: int) -> list[dict]:
    return hierarchical_local_location_suggestions(query, limit)
    compact_query = compact_location_text(query).replace("서울특별시", "서울")
    if not compact_query:
        return []

    apartment_dataset, _, _ = load_apartment_dataset()
    by_district: dict[str, list[dict]] = {}
    by_dong: dict[tuple[str, str], list[dict]] = {}
    for apartment in apartment_dataset.get("apartments", []):
        district = str(apartment.get("district") or "").strip()
        dong = str(apartment.get("dong") or "").strip()
        if not district or apartment.get("lat") is None or apartment.get("lng") is None:
            continue
        by_district.setdefault(district, []).append(apartment)
        if dong:
            by_dong.setdefault((district, dong), []).append(apartment)

    suggestions: list[dict] = []
    for district, items in sorted(by_district.items()):
        label = f"서울특별시 {district}"
        match_blob = f"{label} {label.replace('서울특별시', '서울')}"
        if compact_query not in compact_location_text(match_blob):
            continue

        lat, lng = _average_location(items)
        suggestions.append(
            {
                "type": "district",
                "label": label,
                "address": label,
                "lat": lat,
                "lng": lng,
                "district": district,
                "dong": "",
                "source": "local_apartment_district",
                "selectable": False,
                "hint": "동까지 선택하면 이동할 수 있습니다.",
            }
        )
        for (dong_district, dong), dong_items in sorted(by_dong.items()):
            if dong_district != district:
                continue
            dong_label = f"서울특별시 {district} {dong}"
            dong_blob = f"{dong_label} {dong_label.replace('서울특별시', '서울')}"
            if compact_query not in compact_location_text(dong_blob) and compact_query not in compact_location_text(match_blob):
                continue
            dong_lat, dong_lng = _average_location(dong_items)
            suggestions.append(
                {
                    "type": "dong",
                    "label": dong_label,
                    "address": dong_label,
                    "lat": dong_lat,
                    "lng": dong_lng,
                    "district": district,
                    "dong": dong,
                    "source": "local_apartment_dong",
                    "selectable": True,
                    "hint": "서울 구·동 기준 위치",
                }
            )
            if len(suggestions) >= limit:
                break
        if len(suggestions) >= limit:
            break

    return suggestions[:limit]


def normalize_location_suggestion(location: dict) -> dict:
    parts = seoul_dong_parts(location.get("address"), location.get("roadAddress"), location.get("label"))
    address = str(location.get("address") or location.get("roadAddress") or location.get("label") or "")
    source = str(location.get("source") or "")
    return {
        "type": "place" if "keyword" in source else "address",
        "label": location.get("label") or address,
        "address": address,
        "roadAddress": location.get("roadAddress", ""),
        "lat": location.get("lat"),
        "lng": location.get("lng"),
        "district": parts["district"],
        "dong": parts["dong"],
        "category": location.get("category", ""),
        "source": source,
        "selectable": parts["ok"],
        "hint": "장소 주소의 서울 구·동 확인됨" if parts["ok"] else "서울 구·동이 확인되는 후보만 이동할 수 있습니다.",
    }


def location_suggestions_response(raw: dict[str, list[str]]) -> dict:
    query = single_value(raw, "query").strip()
    try:
        limit = int(single_value(raw, "limit", "8"))
    except ValueError:
        limit = 8
    limit = max(1, min(limit, 30))

    suggestions = local_location_suggestions(query, limit)
    compact_query = compact_location_text(query)
    has_scope_drilldown = any(item.get("drilldown") for item in suggestions)
    should_search_kakao = (
        len(compact_query) >= 2
        and compact_query not in {"서울", "서울시", "서울특별시"}
        and not has_scope_drilldown
    )
    if should_search_kakao and len(suggestions) < limit:
        for location in search_locations_with_kakao(query, limit=limit):
            suggestions.append(normalize_location_suggestion(location))
            if len(suggestions) >= limit:
                break

    deduped: list[dict] = []
    seen: set[str] = set()
    for item in suggestions:
        key = compact_location_text(f"{item.get('label')}|{item.get('address')}|{item.get('lat')}|{item.get('lng')}")
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)

    return {
        "ok": True,
        "query": query,
        "requires": "서울특별시 + 구 + 동",
        "suggestions": deduped[:limit],
        "integrations": credential_status(),
    }


def validate_destination_scope(label: str, address: str = "") -> None:
    if not label and not address:
        return
    if not seoul_dong_parts(label, address)["ok"]:
        raise ValueError("회사/목적지는 서울특별시 + 구 + 동까지 확인되는 주소나 장소를 선택해주세요.")


def decorate_dataset(dataset: dict) -> dict:
    decorated = dict(dataset)
    decorated["meta"] = {
        **runtime_meta(dataset.get("meta", {})),
        "destinationAddresses": destination_addresses(),
        "integrations": credential_status(),
    }
    decorated["areas"] = [
        {
            **area,
            "representativeAddress": AREA_ADDRESSES.get(area["id"], f"{area.get('district', '')} {area.get('station', '')}".strip()),
        }
        for area in dataset.get("areas", [])
    ]
    return decorated


def known_locations() -> dict[str, dict]:
    dataset = load_dataset()
    locations = {
        key: {"label": value["label"], "address": value["address"], "lat": value["lat"], "lng": value["lng"]}
        for key, value in DESTINATIONS.items()
    }
    for key, value in DESTINATIONS.items():
        locations[value["label"]] = locations[key]
        locations[value["address"]] = locations[key]
    for area in dataset.get("areas", []):
        address = AREA_ADDRESSES.get(area["id"], "")
        location = {
            "label": area["name"],
            "address": address,
            "name": area["name"],
            "station": area.get("station", ""),
            "lat": area["lat"],
            "lng": area["lng"],
        }
        locations[area["id"]] = location
        locations[area["name"]] = location
        if address:
            locations[address] = location
        if area.get("station"):
            locations[area["station"]] = location

    apartment_dataset, _, _ = load_apartment_dataset()
    dong_groups: dict[tuple[str, str], list[dict]] = {}
    for apartment in apartment_dataset.get("apartments", []):
        location = {
            "label": apartment.get("name", "아파트"),
            "address": apartment.get("address", ""),
            "name": apartment.get("name", ""),
            "lat": apartment.get("lat"),
            "lng": apartment.get("lng"),
        }
        locations[apartment.get("id", "")] = location
        if apartment.get("name"):
            locations[apartment["name"]] = location
        if apartment.get("address"):
            locations[apartment["address"]] = location
        district = str(apartment.get("district") or "").strip()
        dong = str(apartment.get("dong") or "").strip()
        if district and dong and apartment.get("lat") is not None and apartment.get("lng") is not None:
            dong_groups.setdefault((district, dong), []).append(apartment)
    for (district, dong), apartments in dong_groups.items():
        lat, lng = _average_location(apartments)
        address = f"서울특별시 {district} {dong}"
        location = {
            "label": address,
            "address": address,
            "name": address,
            "lat": lat,
            "lng": lng,
        }
        locations[address] = location
        locations[address.replace("서울특별시", "서울")] = location
    return locations


def score_area(area: dict, query: Query) -> dict:
    custom_destination = query.destination_location if query.destination_query else None
    minutes = estimate_commute_minutes(area, query.destination, custom_destination)
    monthly_rent = float(area.get("rentMonthly10k") or 0)
    commute_score = clamp(105 - minutes * 1.18)
    over_budget = max(0, monthly_rent - query.budget)
    under_budget = max(0, query.budget - monthly_rent)
    cost_score = clamp(82 + under_budget * 0.55 - over_budget * 1.9)
    safety_env_score = round(float(area.get("safetyScore", 70)) * 0.58 + float(area.get("carbonScore", 70)) * 0.42)
    soc_scoring = persona_soc_score(area, query.persona)
    adjusted = {
        "commute": clamp(commute_score),
        "cost": clamp(cost_score),
        "service": soc_scoring["score"],
        "safety": clamp(safety_env_score),
    }

    total_weight = sum(query.weights.values()) or sum(DEFAULT_WEIGHTS.values())
    weighted = sum(adjusted[key] * query.weights[key] for key in query.weights)
    data_confidence = (float(area.get("dataReadiness", 80)) - 80) * 0.12
    total = clamp(weighted / total_weight + data_confidence)

    result = dict(area)
    result.update(
        {
            "total": round(total),
            "minutes": minutes,
            "adjusted": {key: round(value) for key, value in adjusted.items()},
            "destination": query.destination,
            "destinationLabel": query.destination_location.get("label") or DESTINATIONS[query.destination]["label"],
            "destinationAddress": query.destination_location.get("address") or DESTINATIONS[query.destination]["address"],
            "representativeAddress": AREA_ADDRESSES.get(area["id"], f"{area.get('district', '')} {area.get('station', '')}".strip()),
            "serviceScore": soc_scoring["score"],
            "baseServiceScore": area.get("serviceScore", 0),
            "socCategoryScores": soc_scoring["categoryScores"],
            "socPersonaWeights": soc_scoring["weights"],
            "reasonText": recommendation_reason(area, minutes, query),
        }
    )
    return result


def recommendations(query: Query) -> dict:
    dataset = load_dataset()
    scored = [score_area(area, query) for area in dataset["areas"]]
    scored.sort(key=lambda area: (-area["total"], area.get("rentMonthly10k", 999), area["name"]))
    return {
        "meta": {
            **dataset.get("meta", {}),
            "destination": query.destination,
            "destinationLabel": query.destination_location.get("label") or DESTINATIONS[query.destination]["label"],
            "destinationAddress": query.destination_location.get("address") or DESTINATIONS[query.destination]["address"],
            "destinationLocation": query.destination_location,
            "destinationAddresses": destination_addresses(),
            "persona": query.persona,
            "budget": query.budget,
            "weights": query.weights,
            "returned": min(query.limit, len(scored)),
            "totalCandidates": len(scored),
            "integrations": credential_status(),
        },
        "results": scored[: query.limit],
    }


def estimate_apartment_commute_minutes(apartment: dict, area: dict, query: Query) -> int:
    custom_destination = query.destination_location if query.destination_query else None
    base_minutes = estimate_commute_minutes(area, query.destination, custom_destination)
    destination_location = query.destination_location
    apartment_distance = haversine_km(
        float(apartment["lat"]),
        float(apartment["lng"]),
        destination_location["lat"],
        destination_location["lng"],
    )
    area_distance = haversine_km(
        float(area["lat"]),
        float(area["lng"]),
        destination_location["lat"],
        destination_location["lng"],
    )
    return round(clamp(base_minutes + (apartment_distance - area_distance) * 2.2, 10, 120))


def apartment_recommendation_reason(apartment: dict, area: dict, market: dict, minutes: int, query: Query) -> str:
    monthly_rent = round(float(market.get("monthlyRent10k") or 0))
    budget_delta = round(float(query.budget) - monthly_rent)
    budget_text = "예산 내" if budget_delta >= 0 else f"예산 {abs(budget_delta)}만원 초과"
    soc_text = soc_summary_text(area, query.persona)
    return (
        f"{query.destination_location.get('label') or DESTINATIONS[query.destination]['label']}까지 {minutes}분, 추정 월세 {monthly_rent}만원, "
        f"{area.get('name', '')} 기준 {soc_text}를 반영한 "
        f"{budget_text} 아파트입니다."
    )


def score_apartment(apartment: dict, query: Query) -> dict:
    area = nearest_living_area(apartment)
    market = estimate_market(apartment, area)
    preview = build_property_preview(apartment, query.destination)
    minutes = estimate_apartment_commute_minutes(apartment, area, query)
    monthly_rent = float(market.get("monthlyRent10k") or 0)
    commute_score = clamp(105 - minutes * 1.18)
    over_budget = max(0, monthly_rent - query.budget)
    under_budget = max(0, query.budget - monthly_rent)
    cost_score = clamp(82 + under_budget * 0.55 - over_budget * 1.9)
    neighborhood_safety = float(area.get("safetyScore", 70)) * 0.58 + float(area.get("carbonScore", 70)) * 0.42
    property_safety = 100 - float(preview.get("riskScore") or 0)
    safety_score = neighborhood_safety * 0.85 + property_safety * 0.15
    soc_scoring = persona_soc_score(area, query.persona)
    adjusted = {
        "commute": clamp(commute_score),
        "cost": clamp(cost_score),
        "service": soc_scoring["score"],
        "safety": clamp(safety_score),
    }
    total_weight = sum(query.weights.values()) or sum(DEFAULT_WEIGHTS.values())
    weighted = sum(adjusted[key] * query.weights[key] for key in query.weights)
    data_confidence = (float(area.get("dataReadiness", 80)) - 80) * 0.12
    total = clamp(weighted / total_weight + data_confidence)

    return {
        **apartment,
        "propertyType": "apartment",
        "total": round(total),
        "minutes": minutes,
        "adjusted": {key: round(value) for key, value in adjusted.items()},
        "destination": query.destination,
        "destinationLabel": query.destination_location.get("label") or DESTINATIONS[query.destination]["label"],
        "destinationAddress": query.destination_location.get("address") or DESTINATIONS[query.destination]["address"],
        "representativeAddress": apartment.get("address", ""),
        "rentMonthly10k": market.get("monthlyRent10k", 0),
        "deposit10k": market.get("monthlyDeposit10k", 0),
        "jeonse10k": market.get("recentJeonse10k", 0),
        "sale10k": market.get("recentSale10k", 0),
        "pricePreview": preview,
        "priceSourceMode": market.get("sourceMode", "public_area_proxy"),
        "transitScore": area.get("transitScore", 0),
        "serviceScore": soc_scoring["score"],
        "baseServiceScore": area.get("serviceScore", 0),
        "socCategoryScores": soc_scoring["categoryScores"],
        "socPersonaWeights": soc_scoring["weights"],
        "safetyScore": area.get("safetyScore", 0),
        "carbonScore": area.get("carbonScore", 0),
        "dataReadiness": area.get("dataReadiness", 80),
        "socSummary": area.get("socSummary", {}),
        "safetyEnvSummary": area.get("safetyEnvSummary", {}),
        "recommendedFor": area.get("recommendedFor", []),
        "livingArea": {
            "id": area.get("id", ""),
            "name": area.get("name", ""),
            "district": area.get("district", ""),
            "station": area.get("station", ""),
        },
        "evidence": {
            **area.get("evidence", {}),
            "priceSourceMode": market.get("sourceMode", "public_area_proxy"),
            "livingAreaName": area.get("name", ""),
        },
        "reasonText": apartment_recommendation_reason(apartment, area, market, minutes, query),
    }


def apartment_recommendations(query: Query) -> dict:
    area_dataset = load_dataset()
    apartment_dataset, source_mode, source_error = load_apartment_dataset()
    apartments = apartment_dataset.get("apartments", [])
    scored = [score_apartment(apartment, query) for apartment in apartments]
    scored.sort(key=lambda item: (-item["total"], item.get("rentMonthly10k", 999), item.get("name", "")))
    apartment_meta = apartment_dataset.get("meta", {})
    return {
        "meta": {
            **area_dataset.get("meta", {}),
            "matchingUnit": "apartment",
            "destination": query.destination,
            "destinationLabel": query.destination_location.get("label") or DESTINATIONS[query.destination]["label"],
            "destinationAddress": query.destination_location.get("address") or DESTINATIONS[query.destination]["address"],
            "destinationLocation": query.destination_location,
            "destinationAddresses": destination_addresses(),
            "persona": query.persona,
            "budget": query.budget,
            "weights": query.weights,
            "returned": min(query.limit, len(scored)),
            "totalCandidates": len(scored),
            "apartmentSource": apartment_meta.get("source", {}),
            "apartmentSourceMode": source_mode,
            "apartmentSourceError": source_error,
            "apartmentDataComplete": bool(apartment_meta.get("complete")),
            "prototypeExpanded": bool(apartment_meta.get("prototypeExpanded")),
            "prototypeRecords": int(apartment_meta.get("prototypeRecords") or 0),
            "integrations": integration_status(),
        },
        "results": scored[: query.limit],
    }


def single_value(raw: dict[str, list[str]], name: str, default: str = "") -> str:
    return raw.get(name, [default])[0].strip()


def resolve_route_location(raw: dict[str, list[str]], prefix: str, fallback_key: str = "") -> dict:
    lat = single_value(raw, f"{prefix}Lat")
    lng = single_value(raw, f"{prefix}Lng")
    if lat and lng:
        return resolve_location(f"{lat},{lng}", known_locations())

    query = single_value(raw, prefix)
    if query:
        return resolve_location(query, known_locations())

    if fallback_key:
        return resolve_location(fallback_key, known_locations())

    raise ValueError(f"{prefix} 위치 값이 필요합니다.")


def commute_route(raw: dict[str, list[str]]) -> dict:
    origin = resolve_route_location(raw, "origin")
    destination_query = single_value(raw, "destinationQuery")
    destination_address = single_value(raw, "destinationAddress")
    if destination_query:
        validate_destination_scope(destination_query, destination_address)
    destination_key = single_value(raw, "destination", "gangnam")
    destination = resolve_route_location(raw, "destination", destination_address or destination_query or destination_key)
    if destination_query:
        destination["label"] = destination_query
        destination["address"] = destination_address or destination_query
    provider = single_value(raw, "provider", "auto")
    transport_mode = single_value(raw, "transportMode", "transit")
    route = build_commute_route(origin, destination, provider, transport_mode)
    route["credentialStatus"] = credential_status()
    return route


def integration_status() -> dict:
    return {**credential_status(), **apartment_credential_status(), **price_credential_status()}


def apartment_health() -> dict:
    dataset, source_mode, source_error = load_apartment_dataset()
    meta = dataset.get("meta", {})
    return {
        "sourceMode": source_mode,
        "sourceError": source_error,
        "complete": bool(meta.get("complete")),
        "totalRecords": int(meta.get("totalRecords") or len(dataset.get("apartments", []))),
        "availableRecords": int(meta.get("recordsWithCoordinates") or len(dataset.get("apartments", []))),
        "prototypeExpanded": bool(meta.get("prototypeExpanded")),
        "prototypeRecords": int(meta.get("prototypeRecords") or 0),
        "source": meta.get("source", {}),
    }


def select_agent_engine() -> tuple:
    """쓸 수 있는 AI 엔진과 그 상태를 고른다: Claude 키가 있으면 Claude, 없으면 로컬 Ollama.

    설정 스위치를 두지 않는 건 두 엔진의 availability()가 이미 정확하기 때문이다.
    키를 안 넣으면 과금이 없는 Ollama로, 키를 넣으면 Claude로 저절로 간다.

    LLM 연동은 선택 의존성이라 요청 시점에만 import한다(정적 빌드는 이 경로를 타지 않는다).
    둘 다 못 쓰면 (None, 사유)를 돌려주고, 호출 측은 규칙 기반 엔진으로 되돌아간다.
    """
    import agent_llm

    remote = agent_llm.availability()
    if remote["available"]:
        return agent_llm, remote

    import agent_ollama

    local = agent_ollama.availability()
    if local["available"]:
        return agent_ollama, local

    local["reason"] = f"Claude: {remote['reason']} / Ollama: {local['reason']}"
    return None, local


class Handler(BaseHTTPRequestHandler):
    server_version = "MoveValueAPI/0.1"

    def log_message(self, fmt: str, *args) -> None:
        if not getattr(self.server, "quiet", False):
            super().log_message(fmt, *args)

    def send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/api/agent-chat":
            self.send_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": f"unknown path: {parsed.path}"})
            return

        engine, state = select_agent_engine()
        if engine is None:
            self.send_json(HTTPStatus.SERVICE_UNAVAILABLE, {"ok": False, "error": state["reason"]})
            return
        agent_chat = engine.agent_chat

        try:
            length = int(self.headers.get("Content-Length") or 0)
            if length <= 0 or length > 1_000_000:
                raise ValueError("요청 본문 크기가 올바르지 않습니다.")
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            messages = payload.get("messages")
            if not isinstance(messages, list) or not messages:
                raise ValueError("messages 배열이 필요합니다.")
            result = agent_chat(messages, str(payload.get("context") or ""))
        except ValueError as exc:
            self.send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": str(exc)})
            return
        except Exception as exc:  # noqa: BLE001 - 프로토타입은 JSON 에러로 응답한다.
            self.send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"ok": False, "error": str(exc)})
            return

        self.send_json(HTTPStatus.OK if result.get("ok") else HTTPStatus.SERVICE_UNAVAILABLE, result)

    def do_HEAD(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path.startswith("/api/"):
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            return
        self.serve_static(parsed.path, head_only=True)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path

        try:
            if path == "/api/health":
                dataset = load_dataset()
                self.send_json(
                    HTTPStatus.OK,
                    {
                        "ok": True,
                        "areas": len(dataset["areas"]),
                        "source": runtime_meta(dataset["meta"]),
                        "apartments": apartment_health(),
                        "integrations": integration_status(),
                    },
                )
                return
            if path == "/api/agent-status":
                try:
                    self.send_json(HTTPStatus.OK, {"ok": True, **select_agent_engine()[1]})
                except Exception as exc:  # noqa: BLE001 - 상태 조회 실패는 폴백으로 처리한다.
                    self.send_json(
                        HTTPStatus.OK,
                        {"ok": True, "available": False, "reason": f"LLM 모듈 로드 실패: {exc}"},
                    )
                return
            if path == "/api/areas":
                self.send_json(HTTPStatus.OK, decorate_dataset(load_dataset()))
                return
            if path == "/api/geocode":
                raw = parse_qs(parsed.query)
                location = resolve_location(single_value(raw, "query"), known_locations())
                self.send_json(HTTPStatus.OK, {"ok": True, "location": location, "integrations": credential_status()})
                return
            if path == "/api/location-suggestions":
                self.send_json(HTTPStatus.OK, location_suggestions_response(parse_qs(parsed.query)))
                return
            if path == "/api/commute-route":
                self.send_json(HTTPStatus.OK, commute_route(parse_qs(parsed.query)))
                return
            if path == "/api/apartments":
                self.send_json(HTTPStatus.OK, apartments_response(parse_qs(parsed.query)))
                return
            if path == "/api/property-detail":
                self.send_json(HTTPStatus.OK, property_detail_response(parse_qs(parsed.query)))
                return
            if path == "/api/property-agent":
                self.send_json(HTTPStatus.OK, property_agent_response(parse_qs(parsed.query)))
                return
            if path == "/api/recommendations":
                query = normalize_query(parse_qs(parsed.query))
                self.send_json(HTTPStatus.OK, recommendations(query))
                return
            if path == "/api/apartment-recommendations":
                query = normalize_query(parse_qs(parsed.query))
                self.send_json(HTTPStatus.OK, apartment_recommendations(query))
                return
            self.serve_static(path)
        except ValueError as exc:
            self.send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": str(exc), "integrations": integration_status()})
        except Exception as exc:  # noqa: BLE001 - API should return JSON error in prototype mode.
            self.send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"ok": False, "error": str(exc)})

    def serve_static(self, path: str, head_only: bool = False) -> None:
        if path in {"", "/", "/app", "/app/"}:
            target = APP_DIR / "index.html"
        elif path.startswith("/app/"):
            target = APP_DIR / unquote(path.removeprefix("/app/"))
        else:
            target = APP_DIR / unquote(path.lstrip("/"))

        target = target.resolve()
        if not (target == APP_DIR.resolve() or APP_DIR.resolve() in target.parents):
            self.send_error(HTTPStatus.FORBIDDEN)
            return
        if not target.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        body = target.read_bytes()
        content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        if content_type.startswith("text/") or target.suffix in {".js", ".json"}:
            content_type += "; charset=utf-8"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if not head_only:
            self.wfile.write(body)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run MoveValue API and web prototype.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5173)
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), Handler)
    server.quiet = args.quiet
    print(f"MoveValue API listening at http://{args.host}:{args.port}/")
    server.serve_forever()


if __name__ == "__main__":
    main()
