"""Kakao Local place search adapter for safety-related nearby facilities."""

from __future__ import annotations

import json
import math
import os
import time
import urllib.parse
import urllib.request
from typing import Any

from env_loader import load_dotenv


load_dotenv()

KAKAO_KEYWORD_ENDPOINT = "https://dapi.kakao.com/v2/local/search/keyword.json"
KAKAO_KEY_ENVS = ("KAKAO_REST_API_KEY", "MOVEVALUE_KAKAO_REST_API_KEY")
DEFAULT_RADIUS_METERS = 1000
MAX_RADIUS_METERS = 20000
PAGE_SIZE = 15
MAX_PAGES = 3
CACHE_SECONDS = 60 * 60 * 6

SAFETY_QUERIES: dict[str, list[str]] = {
    "police": ["경찰", "경찰서", "지구대", "파출소", "치안센터"],
    "green": ["공원"],
}

SAFETY_LABELS = {
    "police": "치안시설",
    "green": "녹지 접근",
}

SAFETY_NAME_FILTERS = {
    "police": {
        "allow": ("경찰", "경찰서", "지구대", "파출소", "치안센터"),
        "deny": ("전기차", "충전소"),
    },
    "green": {
        "allow": ("공원",),
        "deny": ("주차장", "부동산", "아파트"),
    },
}

_CACHE: dict[tuple[float, float, int], tuple[float, dict[str, Any]]] = {}


def _env_key() -> str:
    load_dotenv()
    for name in KAKAO_KEY_ENVS:
        value = os.getenv(name, "").strip()
        if value:
            return value
    return ""


def kakao_safety_status() -> dict[str, Any]:
    return {
        "kakaoSafety": bool(_env_key()),
        "kakaoSafetyRadiusMeters": DEFAULT_RADIUS_METERS,
        "kakaoSafetySource": "Kakao Local API",
    }


def _single_value(raw: dict[str, list[str]], name: str, default: str = "") -> str:
    return raw.get(name, [default])[0].strip()


def _haversine_meters(a_lat: float, a_lng: float, b_lat: float, b_lng: float) -> float:
    radius = 6371008.8
    phi1 = math.radians(a_lat)
    phi2 = math.radians(b_lat)
    d_phi = math.radians(b_lat - a_lat)
    d_lambda = math.radians(b_lng - a_lng)
    h = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return radius * 2 * math.atan2(math.sqrt(h), math.sqrt(1 - h))


def _request(params: dict[str, Any], api_key: str) -> dict[str, Any]:
    query = urllib.parse.urlencode(params)
    request = urllib.request.Request(
        f"{KAKAO_KEYWORD_ENDPOINT}?{query}",
        headers={"Authorization": f"KakaoAK {api_key}", "User-Agent": "MoveValue/0.1"},
    )
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(request, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def _normalize_place(document: dict[str, Any], category: str, origin_lat: float, origin_lng: float) -> dict[str, Any] | None:
    try:
        lat = float(document["y"])
        lng = float(document["x"])
    except (KeyError, TypeError, ValueError):
        return None

    try:
        distance = int(float(document.get("distance")))
    except (TypeError, ValueError):
        distance = round(_haversine_meters(origin_lat, origin_lng, lat, lng))

    return {
        "id": str(document.get("id") or ""),
        "category": category,
        "name": document.get("place_name") or SAFETY_LABELS.get(category, "시설"),
        "distanceMeters": distance,
        "lat": lat,
        "lng": lng,
        "address": document.get("road_address_name") or document.get("address_name") or "",
        "phone": document.get("phone") or "",
        "url": document.get("place_url") or "",
        "source": "kakao_local_api",
    }


def _place_allowed(place: dict[str, Any]) -> bool:
    rules = SAFETY_NAME_FILTERS.get(str(place.get("category") or ""), {})
    name = str(place.get("name") or "")
    if any(token in name for token in rules.get("deny", ())):
        return False
    allowed = rules.get("allow", ())
    return not allowed or any(token in name for token in allowed)


def _search_keyword(keyword: str, category: str, lat: float, lng: float, radius: int, api_key: str) -> list[dict[str, Any]]:
    places: list[dict[str, Any]] = []
    common = {"query": keyword, "x": lng, "y": lat, "radius": radius, "sort": "distance"}
    for page in range(1, MAX_PAGES + 1):
        payload = _request({**common, "page": page, "size": PAGE_SIZE}, api_key)
        for document in payload.get("documents") or []:
            place = _normalize_place(document, category, lat, lng)
            if place and _place_allowed(place):
                places.append(place)
        if payload.get("meta", {}).get("is_end"):
            break
    return places


def _category_places(category: str, lat: float, lng: float, radius: int, api_key: str) -> dict[str, Any]:
    places: list[dict[str, Any]] = []
    errors: list[str] = []
    for keyword in SAFETY_QUERIES.get(category, []):
        try:
            places.extend(_search_keyword(keyword, category, lat, lng, radius, api_key))
        except Exception as exc:  # noqa: BLE001 - keep other safety categories usable.
            errors.append(f"{keyword}: {exc}")

    deduped: dict[str, dict[str, Any]] = {}
    for place in places:
        key = place.get("id") or "|".join([place.get("name", ""), f"{place.get('lat'):.6f}", f"{place.get('lng'):.6f}"])
        if key not in deduped or int(place.get("distanceMeters") or 0) < int(deduped[key].get("distanceMeters") or 0):
            deduped[key] = place

    samples = sorted(deduped.values(), key=lambda item: int(item.get("distanceMeters") or 0))
    return {
        "label": SAFETY_LABELS.get(category, category),
        "count": len(samples),
        "nearest": samples[0] if samples else None,
        "samples": samples[:12],
        "source": "kakao_local_api",
        "errors": errors,
    }


def _empty_categories() -> dict[str, dict[str, Any]]:
    return {
        key: {"label": label, "count": 0, "nearest": None, "samples": [], "source": "kakao_local_api"}
        for key, label in SAFETY_LABELS.items()
    }


def _coords_from_query(raw: dict[str, list[str]]) -> tuple[float, float, str]:
    apartment_id = _single_value(raw, "id")
    if apartment_id:
        from apartment_adapters import load_apartment_dataset

        dataset, _, _ = load_apartment_dataset()
        for item in dataset.get("apartments", []):
            if str(item.get("id")) == apartment_id:
                return float(item["lat"]), float(item["lng"]), apartment_id

    lat = float(_single_value(raw, "lat"))
    lng = float(_single_value(raw, "lng"))
    return lat, lng, apartment_id


def kakao_safety_response(raw: dict[str, list[str]]) -> dict[str, Any]:
    api_key = _env_key()
    try:
        lat, lng, apartment_id = _coords_from_query(raw)
    except (TypeError, ValueError, KeyError):
        return {"ok": False, "error": "아파트 좌표가 필요합니다.", "integrations": kakao_safety_status()}

    try:
        radius = int(float(_single_value(raw, "radius", str(DEFAULT_RADIUS_METERS))))
    except ValueError:
        radius = DEFAULT_RADIUS_METERS
    radius = max(1, min(radius, MAX_RADIUS_METERS))

    if not api_key:
        return {
            "ok": True,
            "mode": "missing_key",
            "radiusMeters": radius,
            "apartmentId": apartment_id,
            "source": "Kakao Local API",
            "categories": _empty_categories(),
            "integrations": kakao_safety_status(),
        }

    cache_key = (round(lat, 5), round(lng, 5), radius)
    cached = _CACHE.get(cache_key)
    now = time.time()
    if cached and now - cached[0] < CACHE_SECONDS:
        return {**cached[1], "cached": True}

    categories = {key: _category_places(key, lat, lng, radius, api_key) for key in SAFETY_LABELS}
    result = {
        "ok": True,
        "mode": "partial_error" if any(item.get("errors") for item in categories.values()) else "live_api",
        "radiusMeters": radius,
        "apartmentId": apartment_id,
        "source": "Kakao Local API",
        "categories": categories,
        "integrations": kakao_safety_status(),
    }
    _CACHE[cache_key] = (now, result)
    return result
