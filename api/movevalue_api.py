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
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from apartment_adapters import apartment_credential_status, apartments_response, load_apartment_dataset
from property_adapters import property_agent_response, property_detail_response
from property_model import build_property_preview, estimate_market, nearest_living_area
from real_estate_price_adapters import price_credential_status
from route_adapters import build_commute_route, credential_status, resolve_location


ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "app"
DATA_PATH = ROOT / "data" / "areas.actual.json"


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

DEFAULT_WEIGHTS = {"commute": 35, "cost": 30, "service": 20, "safety": 15}
VALID_PERSONAS = {"single", "commuter", "newlywed", "senior"}
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
    "commuter": {"medical": 10, "transport": 40, "convenience": 25, "education": 5, "leisure": 10, "welfare": 5},
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
    destination_location = dict(DESTINATIONS[destination])
    destination_lat = raw.get("destinationLat", [""])[0].strip()
    destination_lng = raw.get("destinationLng", [""])[0].strip()
    if destination_lat and destination_lng:
        try:
            destination_location = {
                "label": destination_query or DESTINATIONS[destination]["label"],
                "address": destination_query or DESTINATIONS[destination]["address"],
                "lat": float(destination_lat),
                "lng": float(destination_lng),
                "source": "prototype_address_input" if destination_query else "preset",
            }
        except ValueError:
            destination_location = dict(DESTINATIONS[destination])
    elif destination_query:
        resolved = resolve_location(destination_query, known_locations())
        destination_location = {
            **resolved,
            "label": destination_query,
            "address": destination_query,
        }

    persona = raw.get("persona", ["single"])[0]
    if persona not in VALID_PERSONAS:
        persona = "single"

    weights = {
        "commute": number("commuteWeight", DEFAULT_WEIGHTS["commute"], 0, 100),
        "cost": number("costWeight", DEFAULT_WEIGHTS["cost"], 0, 100),
        "service": number("serviceWeight", DEFAULT_WEIGHTS["service"], 0, 100),
        "safety": number("safetyWeight", DEFAULT_WEIGHTS["safety"], 0, 100),
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


def destination_addresses() -> dict[str, str]:
    return {key: value["address"] for key, value in DESTINATIONS.items()}


def decorate_dataset(dataset: dict) -> dict:
    decorated = dict(dataset)
    decorated["meta"] = {
        **dataset.get("meta", {}),
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
    destination_key = single_value(raw, "destination", "gangnam")
    destination = resolve_route_location(raw, "destination", destination_query or destination_key)
    if destination_query:
        destination["label"] = destination_query
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
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

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
                        "source": dataset["meta"],
                        "apartments": apartment_health(),
                        "integrations": integration_status(),
                    },
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
