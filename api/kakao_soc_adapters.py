"""Kakao Local place search adapter for nearby 생활 SOC.

This adapter is intentionally separate from route_adapters.py so destination
address search and route geocoding keep their existing behavior.
"""

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

KAKAO_CATEGORY_ENDPOINT = "https://dapi.kakao.com/v2/local/search/category.json"
KAKAO_KEYWORD_ENDPOINT = "https://dapi.kakao.com/v2/local/search/keyword.json"
KAKAO_KEY_ENVS = ("KAKAO_REST_API_KEY", "MOVEVALUE_KAKAO_REST_API_KEY")
DEFAULT_RADIUS_METERS = 1000
MAX_RADIUS_METERS = 20000
PAGE_SIZE = 15
MAX_PAGES = 3
CACHE_SECONDS = 60 * 60 * 6

SOC_QUERIES: dict[str, dict[str, list[str]]] = {
    "medical": {"categories": ["HP8"], "keywords": []},
    "transport": {"categories": ["SW8"], "keywords": ["버스정류장"]},
    "convenience": {"categories": [], "keywords": ["우체국", "구청", "시청"]},
    "education": {"categories": ["SC4"], "keywords": ["어린이집", "유치원"]},
    "leisure": {"categories": [], "keywords": ["공공도서관", "문화센터", "체육센터", "구민체육센터", "구민회관", "청소년수련관"]},
    "welfare": {"categories": [], "keywords": ["복지관", "노인복지관", "경로당", "주민센터"]},
}

SOC_NAME_FILTERS = {
    "medical": {
        "allow": ("병원", "의원", "의료원", "보건소", "치과", "한의원"),
        "deny": ("약국",),
    },
    "transport": {
        "allow": ("역", "정류장", "버스"),
        "deny": (),
    },
    "convenience": {
        "allow": ("우체국", "구청", "시청"),
        "deny": ("영사관", "대사관", "충전소"),
    },
    "education": {
        "allow": ("학교", "초등", "중학", "고등", "대학교", "어린이집", "유치원"),
        "deny": ("애견", "반려", "동물", "호텔", "미용"),
    },
    "leisure": {
        "allow": ("도서관", "문화센터", "체육센터", "국민체육", "구민체육", "공공체육", "구민회관", "청소년수련관", "수련관"),
        "deny": ("공원", "헬스", "짐", "골프", "요가", "필라테스", "스크린", "주차장", "부동산", "아파트"),
    },
    "welfare": {
        "allow": ("복지", "노인", "경로당", "주민센터", "장애인"),
        "deny": ("충전소", "무인민원발급창구"),
    },
}

SOC_LABELS = {
    "medical": "의료",
    "transport": "교통",
    "convenience": "생활편의",
    "education": "교육",
    "leisure": "문화·체육",
    "welfare": "복지시설",
}

_CACHE: dict[tuple[float, float, int], tuple[float, dict[str, Any]]] = {}


def _env_key() -> str:
    load_dotenv()
    for name in KAKAO_KEY_ENVS:
        value = os.getenv(name, "").strip()
        if value:
            return value
    return ""


def kakao_soc_status() -> dict[str, Any]:
    return {
        "kakaoSoc": bool(_env_key()),
        "kakaoSocRadiusMeters": DEFAULT_RADIUS_METERS,
        "kakaoSocSource": "Kakao Local API",
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


def _request(endpoint: str, params: dict[str, Any], api_key: str) -> dict[str, Any]:
    query = urllib.parse.urlencode(params)
    request = urllib.request.Request(
        f"{endpoint}?{query}",
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

    raw_distance = document.get("distance")
    try:
        distance = int(float(raw_distance))
    except (TypeError, ValueError):
        distance = round(_haversine_meters(origin_lat, origin_lng, lat, lng))

    return {
        "id": str(document.get("id") or ""),
        "category": category,
        "name": document.get("place_name") or document.get("address_name") or SOC_LABELS.get(category, "시설"),
        "distanceMeters": distance,
        "lat": lat,
        "lng": lng,
        "address": document.get("road_address_name") or document.get("address_name") or "",
        "phone": document.get("phone") or "",
        "url": document.get("place_url") or "",
        "source": "kakao_local_api",
    }


def _place_allowed(place: dict[str, Any]) -> bool:
    rules = SOC_NAME_FILTERS.get(str(place.get("category") or ""), {})
    name = str(place.get("name") or "")
    if any(token in name for token in rules.get("deny", ())):
        return False
    allowed = rules.get("allow", ())
    return not allowed or any(token in name for token in allowed)


def _search(endpoint: str, params: dict[str, Any], api_key: str, category: str, lat: float, lng: float) -> list[dict[str, Any]]:
    places: list[dict[str, Any]] = []
    for page in range(1, MAX_PAGES + 1):
        payload = _request(endpoint, {**params, "page": page, "size": PAGE_SIZE}, api_key)
        for document in payload.get("documents") or []:
            place = _normalize_place(document, category, lat, lng)
            if place and _place_allowed(place):
                places.append(place)
        if payload.get("meta", {}).get("is_end"):
            break
    return places


def _category_places(category: str, lat: float, lng: float, radius: int, api_key: str) -> dict[str, Any]:
    query_set = SOC_QUERIES.get(category, {})
    places: list[dict[str, Any]] = []
    errors: list[str] = []

    common = {"x": lng, "y": lat, "radius": radius, "sort": "distance"}
    for category_code in query_set.get("categories", []):
        try:
            places.extend(_search(KAKAO_CATEGORY_ENDPOINT, {**common, "category_group_code": category_code}, api_key, category, lat, lng))
        except Exception as exc:  # noqa: BLE001 - keep other categories usable.
            errors.append(f"{category_code}: {exc}")

    for keyword in query_set.get("keywords", []):
        try:
            places.extend(_search(KAKAO_KEYWORD_ENDPOINT, {**common, "query": keyword}, api_key, category, lat, lng))
        except Exception as exc:  # noqa: BLE001 - keep other categories usable.
            errors.append(f"{keyword}: {exc}")

    deduped: dict[str, dict[str, Any]] = {}
    for place in places:
        key = place.get("id") or "|".join([place.get("name", ""), f"{place.get('lat'):.6f}", f"{place.get('lng'):.6f}"])
        if key not in deduped or int(place.get("distanceMeters") or 0) < int(deduped[key].get("distanceMeters") or 0):
            deduped[key] = place

    samples = sorted(deduped.values(), key=lambda item: int(item.get("distanceMeters") or 0))
    return {
        "label": SOC_LABELS.get(category, category),
        "count": len(samples),
        "nearest": samples[0] if samples else None,
        "samples": samples[:12],
        "source": "kakao_local_api",
        "errors": errors,
    }


def _empty_categories() -> dict[str, dict[str, Any]]:
    return {
        key: {"label": label, "count": 0, "nearest": None, "samples": [], "source": "kakao_local_api"}
        for key, label in SOC_LABELS.items()
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


def kakao_soc_response(raw: dict[str, list[str]]) -> dict[str, Any]:
    api_key = _env_key()
    try:
        lat, lng, apartment_id = _coords_from_query(raw)
    except (TypeError, ValueError, KeyError):
        return {"ok": False, "error": "아파트 좌표가 필요합니다.", "integrations": kakao_soc_status()}

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
            "integrations": kakao_soc_status(),
        }

    cache_key = (round(lat, 5), round(lng, 5), radius)
    cached = _CACHE.get(cache_key)
    now = time.time()
    if cached and now - cached[0] < CACHE_SECONDS:
        return {**cached[1], "cached": True}

    categories = {
        key: _category_places(key, lat, lng, radius, api_key)
        for key in SOC_LABELS
    }
    has_errors = any(item.get("errors") for item in categories.values())
    result = {
        "ok": True,
        "mode": "partial_error" if has_errors else "live_api",
        "radiusMeters": radius,
        "apartmentId": apartment_id,
        "source": "Kakao Local API",
        "categories": categories,
        "integrations": kakao_soc_status(),
    }
    _CACHE[cache_key] = (now, result)
    return result
