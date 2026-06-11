"""Runtime route and geocoding adapters for MoveValue.

API credentials are read only from environment variables. The app keeps a
deterministic fallback route so the prototype remains usable without keys.
"""

from __future__ import annotations

import json
import math
import os
import urllib.parse
import urllib.request
from typing import Any


OD_SAY_ENDPOINT = "https://api.odsay.com/v1/api/searchPubTransPathT"
TMAP_TRANSIT_ENDPOINT = "https://apis.openapi.sk.com/transit/routes"
KAKAO_ADDRESS_ENDPOINT = "https://dapi.kakao.com/v2/local/search/address.json"

OD_SAY_KEY_ENV = "ODSAY_API_KEY"
OD_SAY_ALT_KEY_ENV = "MOVEVALUE_ODSAY_API_KEY"
TMAP_KEY_ENV = "TMAP_APP_KEY"
TMAP_ALT_KEY_ENV = "MOVEVALUE_TMAP_APP_KEY"
KAKAO_KEY_ENV = "KAKAO_REST_API_KEY"
KAKAO_ALT_KEY_ENV = "MOVEVALUE_KAKAO_REST_API_KEY"


def env_key(*names: str) -> str:
    for name in names:
        value = os.getenv(name, "").strip()
        if value:
            return value
    return ""


def haversine_km(a_lat: float, a_lng: float, b_lat: float, b_lng: float) -> float:
    radius = 6371.0088
    phi1 = math.radians(a_lat)
    phi2 = math.radians(b_lat)
    d_phi = math.radians(b_lat - a_lat)
    d_lambda = math.radians(b_lng - a_lng)
    h = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return radius * 2 * math.atan2(math.sqrt(h), math.sqrt(1 - h))


def parse_coordinate_text(value: str) -> dict[str, Any] | None:
    parts = [part.strip() for part in value.replace("/", ",").split(",") if part.strip()]
    if len(parts) != 2:
        return None
    try:
        first = float(parts[0])
        second = float(parts[1])
    except ValueError:
        return None

    if 33 <= first <= 39 and 124 <= second <= 132:
        lat, lng = first, second
    elif 124 <= first <= 132 and 33 <= second <= 39:
        lat, lng = second, first
    else:
        return None

    return {
        "label": f"{lat:.5f}, {lng:.5f}",
        "lat": lat,
        "lng": lng,
        "source": "coordinate_input",
    }


def geocode_with_kakao(query: str) -> dict[str, Any] | None:
    api_key = env_key(KAKAO_KEY_ENV, KAKAO_ALT_KEY_ENV)
    if not api_key:
        return None

    params = urllib.parse.urlencode({"query": query})
    request = urllib.request.Request(
        f"{KAKAO_ADDRESS_ENDPOINT}?{params}",
        headers={"Authorization": f"KakaoAK {api_key}", "User-Agent": "MoveValue/0.1"},
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        payload = json.loads(response.read().decode("utf-8"))

    documents = payload.get("documents") or []
    if not documents:
        return None

    top = documents[0]
    address_name = top.get("road_address", {}).get("address_name") or top.get("address_name") or query
    return {
        "label": address_name,
        "lat": float(top["y"]),
        "lng": float(top["x"]),
        "source": "kakao_address_api",
    }


def resolve_location(query: str, known_locations: dict[str, dict[str, Any]]) -> dict[str, Any]:
    value = (query or "").strip()
    if not value:
        raise ValueError("위치 값이 비어 있습니다.")

    coordinate = parse_coordinate_text(value)
    if coordinate:
        return coordinate

    normalized = value.replace(" ", "").lower()
    for key, location in known_locations.items():
        candidates = [
            ("address", location.get("address", "")),
            ("label", location.get("label", "")),
            ("name", location.get("name", "")),
            ("station", location.get("station", "")),
            ("key", key),
        ]
        matched_kind = next(
            (kind for kind, candidate in candidates if normalized == str(candidate).replace(" ", "").lower()),
            "",
        )
        if matched_kind:
            return {
                "label": location.get("address") if matched_kind == "address" else location.get("label") or location.get("name") or key,
                "lat": float(location["lat"]),
                "lng": float(location["lng"]),
                "source": "known_address" if matched_kind == "address" else "known_location",
            }

    kakao = geocode_with_kakao(value)
    if kakao:
        return kakao

    raise ValueError(
        f"'{value}'를 좌표로 변환하지 못했습니다. 상세 주소 검색은 {KAKAO_KEY_ENV}가 필요합니다. 키가 없으면 기본 제공 대표 주소, 생활권명, 목적지명 또는 '37.5405,127.0692' 형식의 좌표를 입력하세요."
    )


def _request_json(url: str, *, method: str = "GET", headers: dict[str, str] | None = None, body: dict | None = None) -> dict:
    encoded_body = None
    request_headers = {"User-Agent": "MoveValue/0.1", **(headers or {})}
    if body is not None:
        encoded_body = json.dumps(body).encode("utf-8")
        request_headers.setdefault("Content-Type", "application/json")
    request = urllib.request.Request(url, data=encoded_body, method=method, headers=request_headers)
    with urllib.request.urlopen(request, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(round(float(value)))
    except (TypeError, ValueError):
        return default


def _seconds_to_minutes(value: Any, default: int = 0) -> int:
    seconds = _safe_int(value, default)
    return round(seconds / 60) if seconds > 180 else seconds


def _append_linestring(coordinates: list[dict[str, Any]], linestring: Any) -> None:
    if not isinstance(linestring, str):
        return
    for point in linestring.split(" "):
        parts = point.split(",")
        if len(parts) != 2:
            continue
        try:
            coordinates.append({"lng": float(parts[0]), "lat": float(parts[1])})
        except ValueError:
            pass


def _mode_label(raw_mode: Any, traffic_type: Any = None) -> str:
    text = str(raw_mode or "").lower()
    if traffic_type == 1 or "subway" in text or "metro" in text:
        return "지하철"
    if traffic_type == 2 or "bus" in text:
        return "버스"
    if traffic_type == 3 or "walk" in text:
        return "도보"
    if "train" in text:
        return "철도"
    return "이동"


def _normalize_odsay(payload: dict[str, Any], origin: dict[str, Any], destination: dict[str, Any]) -> dict[str, Any]:
    if payload.get("error"):
        error = payload["error"]
        if isinstance(error, list) and error:
            error = error[0]
        message = error.get("msg") or error.get("message") or "ODsay API error"
        raise RuntimeError(message)

    paths = payload.get("result", {}).get("path") or []
    if not paths:
        raise RuntimeError("ODsay 경로 응답이 비어 있습니다.")

    path = min(paths, key=lambda item: _safe_int(item.get("info", {}).get("totalTime"), 9999))
    info = path.get("info", {})
    steps = []
    for index, sub in enumerate(path.get("subPath") or [], start=1):
        traffic_type = sub.get("trafficType")
        mode = _mode_label(sub.get("trafficType"), traffic_type)
        lane = sub.get("lane") or []
        route_name = ""
        if lane and isinstance(lane, list):
            route_name = lane[0].get("name") or lane[0].get("busNo") or lane[0].get("subwayCode", "")
        start_name = sub.get("startName") or ("출발지" if index == 1 else "")
        end_name = sub.get("endName") or ("도착지" if index == len(path.get("subPath") or []) else "")
        steps.append(
            {
                "mode": mode,
                "route": route_name,
                "startName": start_name,
                "endName": end_name,
                "minutes": _safe_int(sub.get("sectionTime")),
                "distanceMeters": _safe_int(sub.get("distance")),
            }
        )

    return {
        "ok": True,
        "provider": "odsay",
        "mode": "live_api",
        "origin": origin,
        "destination": destination,
        "summary": {
            "totalMinutes": _safe_int(info.get("totalTime")),
            "fare": _safe_int(info.get("payment")),
            "totalWalkMeters": _safe_int(info.get("totalWalk")),
            "transferCount": _safe_int(info.get("busTransitCount")) + _safe_int(info.get("subwayTransitCount")),
            "pathType": info.get("trafficDistance") or info.get("mapObj") or "",
        },
        "steps": steps,
        "coordinates": [origin, destination],
        "notice": "ODsay 실시간 대중교통 경로 API 결과입니다. 지도 경로선은 출발·도착 좌표 기준으로 표시합니다.",
    }


def route_with_odsay(origin: dict[str, Any], destination: dict[str, Any]) -> dict[str, Any]:
    api_key = env_key(OD_SAY_KEY_ENV, OD_SAY_ALT_KEY_ENV)
    if not api_key:
        raise RuntimeError(f"{OD_SAY_KEY_ENV}가 설정되어 있지 않습니다.")
    params = urllib.parse.urlencode(
        {
            "SX": origin["lng"],
            "SY": origin["lat"],
            "EX": destination["lng"],
            "EY": destination["lat"],
            "apiKey": api_key,
            "output": "json",
        }
    )
    return _normalize_odsay(_request_json(f"{OD_SAY_ENDPOINT}?{params}"), origin, destination)


def _extract_tmap_itineraries(payload: dict[str, Any]) -> list[dict[str, Any]]:
    candidates = [
        payload.get("metaData", {}).get("plan", {}).get("itineraries"),
        payload.get("itineraries"),
        payload.get("routes"),
    ]
    for candidate in candidates:
        if isinstance(candidate, list) and candidate:
            return candidate
    return []


def _normalize_tmap(payload: dict[str, Any], origin: dict[str, Any], destination: dict[str, Any]) -> dict[str, Any]:
    itineraries = _extract_tmap_itineraries(payload)
    if not itineraries:
        message = payload.get("error", {}).get("message") or payload.get("message") or "TMAP 경로 응답이 비어 있습니다."
        raise RuntimeError(message)

    route = min(itineraries, key=lambda item: _safe_int(item.get("totalTime") or item.get("duration"), 999999))
    fare = route.get("fare")
    if isinstance(fare, dict):
        fare = fare.get("regular", {}).get("totalFare") or fare.get("totalFare")

    steps = []
    coordinates = [origin]
    for leg in route.get("legs") or route.get("steps") or []:
        mode = _mode_label(leg.get("mode") or leg.get("type"))
        start = leg.get("start", {}) if isinstance(leg.get("start"), dict) else {}
        end = leg.get("end", {}) if isinstance(leg.get("end"), dict) else {}
        steps.append(
            {
                "mode": mode,
                "route": leg.get("route") or leg.get("routeName") or leg.get("routeColor") or "",
                "startName": start.get("name") or leg.get("startName") or "",
                "endName": end.get("name") or leg.get("endName") or "",
                "minutes": _seconds_to_minutes(leg.get("sectionTime") or leg.get("duration")),
                "distanceMeters": _safe_int(leg.get("distance")),
            }
        )
        _append_linestring(coordinates, leg.get("passShape", {}).get("linestring"))
        for walk_step in leg.get("steps") or []:
            _append_linestring(coordinates, walk_step.get("linestring"))
    coordinates.append(destination)

    total_time = route.get("totalTime") or route.get("duration")

    return {
        "ok": True,
        "provider": "tmap",
        "mode": "live_api",
        "origin": origin,
        "destination": destination,
        "summary": {
            "totalMinutes": _seconds_to_minutes(total_time),
            "fare": _safe_int(fare),
            "totalWalkMeters": _safe_int(route.get("totalWalkDistance") or route.get("walkDistance")),
            "transferCount": _safe_int(route.get("transferCount")),
            "pathType": route.get("pathType") or "",
        },
        "steps": steps,
        "coordinates": coordinates,
        "notice": "TMAP 대중교통 경로 API 결과입니다.",
    }


def route_with_tmap(origin: dict[str, Any], destination: dict[str, Any]) -> dict[str, Any]:
    app_key = env_key(TMAP_KEY_ENV, TMAP_ALT_KEY_ENV)
    if not app_key:
        raise RuntimeError(f"{TMAP_KEY_ENV}가 설정되어 있지 않습니다.")
    body = {
        "startX": str(origin["lng"]),
        "startY": str(origin["lat"]),
        "endX": str(destination["lng"]),
        "endY": str(destination["lat"]),
        "lang": 0,
        "format": "json",
        "count": 3,
    }
    return _normalize_tmap(_request_json(TMAP_TRANSIT_ENDPOINT, method="POST", headers={"appKey": app_key}, body=body), origin, destination)


def fallback_route(origin: dict[str, Any], destination: dict[str, Any], reason: str) -> dict[str, Any]:
    km = haversine_km(origin["lat"], origin["lng"], destination["lat"], destination["lng"])
    total_minutes = max(12, round(10 + km * 2.9))
    walk_meters = round(min(1800, 350 + km * 75))
    return {
        "ok": True,
        "provider": "fallback",
        "mode": "estimated_fallback",
        "origin": origin,
        "destination": destination,
        "summary": {
            "totalMinutes": total_minutes,
            "fare": 1550 if km < 10 else 1750,
            "totalWalkMeters": walk_meters,
            "transferCount": 1 if km > 7 else 0,
            "pathType": "estimated",
        },
        "steps": [
            {"mode": "도보", "route": "", "startName": origin["label"], "endName": "인근 역/정류장", "minutes": 7, "distanceMeters": min(walk_meters, 700)},
            {"mode": "대중교통", "route": "추정 경로", "startName": "인근 역/정류장", "endName": "목적지 인근", "minutes": max(5, total_minutes - 14), "distanceMeters": round(km * 1000)},
            {"mode": "도보", "route": "", "startName": "목적지 인근", "endName": destination["label"], "minutes": 7, "distanceMeters": min(walk_meters, 700)},
        ],
        "coordinates": [origin, destination],
        "notice": f"실제 경로 API 호출이 불가해 거리 기반 추정값을 표시합니다. 사유: {reason}",
    }


def build_commute_route(
    origin: dict[str, Any],
    destination: dict[str, Any],
    provider: str = "auto",
) -> dict[str, Any]:
    errors = []
    requested = provider if provider in {"auto", "odsay", "tmap"} else "auto"
    providers = ["odsay", "tmap"] if requested == "auto" else [requested]

    for name in providers:
        try:
            if name == "odsay":
                return route_with_odsay(origin, destination)
            if name == "tmap":
                return route_with_tmap(origin, destination)
        except Exception as exc:  # noqa: BLE001 - fallback keeps prototype available.
            errors.append(f"{name}: {exc}")

    fallback = fallback_route(origin, destination, "; ".join(errors) or "사용 가능한 경로 API 키 없음")
    fallback["errors"] = errors
    return fallback


def credential_status() -> dict[str, bool]:
    return {
        "odsay": bool(env_key(OD_SAY_KEY_ENV, OD_SAY_ALT_KEY_ENV)),
        "tmap": bool(env_key(TMAP_KEY_ENV, TMAP_ALT_KEY_ENV)),
        "kakao": bool(env_key(KAKAO_KEY_ENV, KAKAO_ALT_KEY_ENV)),
    }
