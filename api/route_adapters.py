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

from env_loader import load_dotenv


load_dotenv()

OD_SAY_ENDPOINT = "https://api.odsay.com/v1/api/searchPubTransPathT"
TMAP_TRANSIT_ENDPOINT = "https://apis.openapi.sk.com/transit/routes"
TMAP_CAR_ENDPOINT = "https://apis.openapi.sk.com/tmap/routes?version=1&format=json"
TMAP_WALK_ENDPOINT = "https://apis.openapi.sk.com/tmap/routes/pedestrian?version=1&format=json"
KAKAO_ADDRESS_ENDPOINT = "https://dapi.kakao.com/v2/local/search/address.json"

OD_SAY_KEY_ENV = "ODSAY_API_KEY"
OD_SAY_ALT_KEY_ENV = "MOVEVALUE_ODSAY_API_KEY"
TMAP_KEY_ENV = "TMAP_APP_KEY"
TMAP_ALT_KEY_ENV = "MOVEVALUE_TMAP_APP_KEY"
TMAP_GENERAL_KEY_ENV = "TMAP_GENERAL_APP_KEY"
TMAP_GENERAL_ALT_KEY_ENV = "MOVEVALUE_TMAP_GENERAL_APP_KEY"
TMAP_CAR_KEY_ENV = "TMAP_CAR_APP_KEY"
TMAP_CAR_ALT_KEY_ENV = "MOVEVALUE_TMAP_CAR_APP_KEY"
TMAP_WALK_KEY_ENV = "TMAP_WALK_APP_KEY"
TMAP_WALK_ALT_KEY_ENV = "MOVEVALUE_TMAP_WALK_APP_KEY"
KAKAO_KEY_ENV = "KAKAO_REST_API_KEY"
KAKAO_ALT_KEY_ENV = "MOVEVALUE_KAKAO_REST_API_KEY"


def env_key(*names: str) -> str:
    load_dotenv()
    for name in names:
        value = os.getenv(name, "").strip()
        if value:
            return value
    return ""


def tmap_general_key() -> str:
    return env_key(TMAP_GENERAL_KEY_ENV, TMAP_GENERAL_ALT_KEY_ENV)


def tmap_car_key() -> str:
    return env_key(
        TMAP_GENERAL_KEY_ENV,
        TMAP_GENERAL_ALT_KEY_ENV,
        TMAP_CAR_KEY_ENV,
        TMAP_CAR_ALT_KEY_ENV,
    )


def tmap_walk_key() -> str:
    return env_key(
        TMAP_GENERAL_KEY_ENV,
        TMAP_GENERAL_ALT_KEY_ENV,
        TMAP_WALK_KEY_ENV,
        TMAP_WALK_ALT_KEY_ENV,
    )


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
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(request, timeout=10) as response:
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
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(request, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(round(float(value)))
    except (TypeError, ValueError):
        return default


def _seconds_to_minutes(value: Any, default: int = 0) -> int:
    seconds = _safe_int(value, default)
    return round(seconds / 60) if seconds > 180 else seconds


def _tmap_seconds_to_minutes(value: Any, default: int = 0) -> int:
    seconds = _safe_int(value, default)
    if seconds <= 0:
        return default
    return max(1, round(seconds / 60))


def _parse_linestring(linestring: Any) -> list[dict[str, Any]]:
    coordinates: list[dict[str, Any]] = []
    if not isinstance(linestring, str):
        return coordinates
    for point in linestring.split(" "):
        parts = point.split(",")
        if len(parts) != 2:
            continue
        try:
            coordinates.append({"lng": float(parts[0]), "lat": float(parts[1])})
        except ValueError:
            pass
    return coordinates


def _parse_geojson_coordinates(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    if len(value) >= 2 and not isinstance(value[0], list):
        try:
            lng = float(value[0])
            lat = float(value[1])
        except (TypeError, ValueError):
            return []
        if 33 <= lat <= 39 and 124 <= lng <= 132:
            return [{"lng": lng, "lat": lat}]
        return []

    coordinates: list[dict[str, Any]] = []
    for item in value:
        coordinates.extend(_parse_geojson_coordinates(item))
    return coordinates


def _append_linestring(coordinates: list[dict[str, Any]], linestring: Any) -> None:
    coordinates.extend(_parse_linestring(linestring))


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
        leg_coordinates: list[dict[str, Any]] = []
        leg_coordinates.extend(_parse_linestring(leg.get("passShape", {}).get("linestring")))
        for walk_step in leg.get("steps") or []:
            leg_coordinates.extend(_parse_linestring(walk_step.get("linestring")))
        steps.append(
            {
                "mode": mode,
                "route": leg.get("route") or leg.get("routeName") or leg.get("routeColor") or "",
                "startName": start.get("name") or leg.get("startName") or "",
                "endName": end.get("name") or leg.get("endName") or "",
                "minutes": _seconds_to_minutes(leg.get("sectionTime") or leg.get("duration")),
                "distanceMeters": _safe_int(leg.get("distance")),
                "coordinates": leg_coordinates,
            }
        )
        coordinates.extend(leg_coordinates)
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
        "count": 1,
    }
    return _normalize_tmap(
        _request_json(
            TMAP_TRANSIT_ENDPOINT,
            method="POST",
            headers={"accept": "application/json", "appKey": app_key},
            body=body,
        ),
        origin,
        destination,
    )


def _normalize_tmap_car(payload: dict[str, Any], origin: dict[str, Any], destination: dict[str, Any]) -> dict[str, Any]:
    features = payload.get("features") or []
    if not isinstance(features, list) or not features:
        message = payload.get("error", {}).get("message") or payload.get("message") or "TMAP 자동차 경로 응답이 비어 있습니다."
        raise RuntimeError(message)

    summary_props = next(
        (
            feature.get("properties", {})
            for feature in features
            if isinstance(feature, dict) and feature.get("properties", {}).get("totalDistance") is not None
        ),
        {},
    )
    total_distance = _safe_int(summary_props.get("totalDistance"))
    total_seconds = _safe_int(summary_props.get("totalTime"))
    total_minutes = _tmap_seconds_to_minutes(total_seconds) if total_seconds else 0
    toll_fare = _safe_int(summary_props.get("totalFare"))
    taxi_fare = _safe_int(summary_props.get("taxiFare"))

    steps = []
    coordinates = [origin]
    line_distance_sum = 0
    for feature in features:
        if not isinstance(feature, dict):
            continue
        geometry = feature.get("geometry") or {}
        properties = feature.get("properties") or {}
        line_coordinates = _parse_geojson_coordinates(geometry.get("coordinates"))
        if geometry.get("type") != "LineString" or len(line_coordinates) < 2:
            continue

        distance = _safe_int(properties.get("distance"))
        line_distance_sum += distance
        seconds = _safe_int(properties.get("time"))
        minutes = _tmap_seconds_to_minutes(seconds) if seconds else 0
        if not minutes and total_minutes and total_distance and distance:
            minutes = max(1, round(total_minutes * distance / total_distance))

        route_name = properties.get("name") or properties.get("description") or "주행 구간"
        steps.append(
            {
                "mode": "자동차",
                "route": route_name,
                "startName": origin["label"] if not steps else "",
                "endName": "",
                "minutes": minutes,
                "distanceMeters": distance,
                "coordinates": line_coordinates,
            }
        )
        coordinates.extend(line_coordinates)

    if steps:
        steps[-1]["endName"] = destination["label"]
    if not total_distance:
        total_distance = line_distance_sum
    if not total_minutes and total_distance:
        total_minutes = max(1, round(total_distance / 1000 / 30 * 60))
    if not steps:
        steps = [
            {
                "mode": "자동차",
                "route": "TMAP 자동차 경로",
                "startName": origin["label"],
                "endName": destination["label"],
                "minutes": total_minutes,
                "distanceMeters": total_distance,
            }
        ]
    coordinates.append(destination)

    return {
        "ok": True,
        "provider": "tmap",
        "mode": "live_api",
        "transportMode": "car",
        "origin": origin,
        "destination": destination,
        "summary": {
            "totalMinutes": total_minutes,
            "fare": toll_fare,
            "estimatedCost": toll_fare or taxi_fare,
            "taxiFare": taxi_fare,
            "distanceMeters": total_distance,
            "totalWalkMeters": 0,
            "transferCount": 0,
            "trafficLabel": "실시간 교통 반영",
            "pathType": "tmap_car",
        },
        "steps": steps,
        "coordinates": coordinates,
        "notice": "TMAP 자동차 경로안내 API 결과입니다. 교통정보 옵션을 포함해 실제 도로 경로를 표시합니다.",
    }


def route_with_tmap_car(origin: dict[str, Any], destination: dict[str, Any]) -> dict[str, Any]:
    app_key = tmap_car_key()
    if not app_key:
        raise RuntimeError(f"{TMAP_GENERAL_KEY_ENV} 또는 {TMAP_CAR_KEY_ENV}가 설정되어 있지 않습니다.")
    body = {
        "startX": str(origin["lng"]),
        "startY": str(origin["lat"]),
        "endX": str(destination["lng"]),
        "endY": str(destination["lat"]),
        "reqCoordType": "WGS84GEO",
        "resCoordType": "WGS84GEO",
        "startName": urllib.parse.quote(str(origin.get("label") or "출발")),
        "endName": urllib.parse.quote(str(destination.get("label") or "도착")),
        "searchOption": "0",
        "trafficInfo": "Y",
        "totalValue": 1,
    }
    return _normalize_tmap_car(
        _request_json(
            TMAP_CAR_ENDPOINT,
            method="POST",
            headers={"accept": "application/json", "appKey": app_key},
            body=body,
        ),
        origin,
        destination,
    )


def _normalize_tmap_walk(payload: dict[str, Any], origin: dict[str, Any], destination: dict[str, Any]) -> dict[str, Any]:
    features = payload.get("features") or []
    if not isinstance(features, list) or not features:
        message = payload.get("error", {}).get("message") or payload.get("message") or "TMAP 보행자 경로 응답이 비어 있습니다."
        raise RuntimeError(message)

    summary_props = next(
        (
            feature.get("properties", {})
            for feature in features
            if isinstance(feature, dict) and feature.get("properties", {}).get("totalDistance") is not None
        ),
        {},
    )
    total_distance = _safe_int(summary_props.get("totalDistance"))
    total_seconds = _safe_int(summary_props.get("totalTime"))
    total_minutes = _tmap_seconds_to_minutes(total_seconds) if total_seconds else 0

    steps = []
    coordinates = [origin]
    line_distance_sum = 0
    for feature in features:
        if not isinstance(feature, dict):
            continue
        geometry = feature.get("geometry") or {}
        properties = feature.get("properties") or {}
        line_coordinates = _parse_geojson_coordinates(geometry.get("coordinates"))
        if geometry.get("type") != "LineString" or len(line_coordinates) < 2:
            continue

        distance = _safe_int(properties.get("distance"))
        line_distance_sum += distance
        seconds = _safe_int(properties.get("time"))
        minutes = _tmap_seconds_to_minutes(seconds) if seconds else 0
        if not minutes and total_minutes and total_distance and distance:
            minutes = max(1, round(total_minutes * distance / total_distance))

        route_name = properties.get("description") or properties.get("name") or "도보 이동"
        steps.append(
            {
                "mode": "도보",
                "route": route_name,
                "startName": origin["label"] if not steps else "",
                "endName": "",
                "minutes": minutes,
                "distanceMeters": distance,
                "coordinates": line_coordinates,
            }
        )
        coordinates.extend(line_coordinates)

    if steps:
        steps[-1]["endName"] = destination["label"]
    if not total_distance:
        total_distance = line_distance_sum
    if not total_minutes and total_distance:
        total_minutes = max(1, round(total_distance / 1000 / 4.5 * 60))
    if not steps:
        steps = [
            {
                "mode": "도보",
                "route": "TMAP 보행자 경로",
                "startName": origin["label"],
                "endName": destination["label"],
                "minutes": total_minutes,
                "distanceMeters": total_distance,
            }
        ]
    coordinates.append(destination)

    return {
        "ok": True,
        "provider": "tmap",
        "mode": "live_api",
        "transportMode": "walk",
        "origin": origin,
        "destination": destination,
        "summary": {
            "totalMinutes": total_minutes,
            "fare": 0,
            "stepCount": round(total_distance / 0.72) if total_distance else 0,
            "distanceMeters": total_distance,
            "totalWalkMeters": total_distance,
            "transferCount": 0,
            "pathType": "tmap_walk",
        },
        "steps": steps,
        "coordinates": coordinates,
        "notice": "TMAP 보행자 경로안내 API 결과입니다. 실제 보행 경로를 지도에 표시합니다.",
    }


def route_with_tmap_walk(origin: dict[str, Any], destination: dict[str, Any]) -> dict[str, Any]:
    app_key = tmap_walk_key()
    if not app_key:
        raise RuntimeError(f"{TMAP_GENERAL_KEY_ENV} 또는 {TMAP_WALK_KEY_ENV}가 설정되어 있지 않습니다.")
    body = {
        "startX": str(origin["lng"]),
        "startY": str(origin["lat"]),
        "endX": str(destination["lng"]),
        "endY": str(destination["lat"]),
        "angle": 20,
        "speed": 30,
        "reqCoordType": "WGS84GEO",
        "resCoordType": "WGS84GEO",
        "startName": urllib.parse.quote(str(origin.get("label") or "출발")),
        "endName": urllib.parse.quote(str(destination.get("label") or "도착")),
        "searchOption": "0",
        "sort": "index",
    }
    return _normalize_tmap_walk(
        _request_json(
            TMAP_WALK_ENDPOINT,
            method="POST",
            headers={"accept": "application/json", "appKey": app_key},
            body=body,
        ),
        origin,
        destination,
    )


def _bicycle_minutes(distance_meters: int) -> int:
    if distance_meters <= 0:
        return 0
    return max(3, round((distance_meters / 1000) / 15 * 60))


def _normalize_tmap_bicycle(payload: dict[str, Any], origin: dict[str, Any], destination: dict[str, Any]) -> dict[str, Any]:
    route = _normalize_tmap_walk(payload, origin, destination)
    summary = dict(route.get("summary") or {})
    steps = [dict(step) for step in route.get("steps") or []]
    distance_meters = _safe_int(summary.get("distanceMeters"))
    total_minutes = _bicycle_minutes(distance_meters)

    if not total_minutes:
        total_minutes = max(3, round(_safe_int(summary.get("totalMinutes")) * 0.45))

    for step in steps:
        step_distance = _safe_int(step.get("distanceMeters"))
        step["mode"] = "자전거"
        step["route"] = step.get("route") or "자전거 이동"
        if step_distance and distance_meters and total_minutes:
            step["minutes"] = max(1, round(total_minutes * step_distance / distance_meters))
        elif step.get("minutes"):
            step["minutes"] = max(1, round(_safe_int(step.get("minutes")) * 0.45))

    summary.update(
        {
            "totalMinutes": total_minutes,
            "fare": 0,
            "estimatedCalories": round((distance_meters / 1000) * 28) if distance_meters else 0,
            "distanceMeters": distance_meters,
            "totalWalkMeters": 0,
            "transferCount": 0,
            "pathType": "tmap_walk_derived_bicycle",
            "routeBasis": "tmap_walk_api",
        }
    )

    return {
        **route,
        "provider": "tmap",
        "mode": "derived_estimate",
        "transportMode": "bicycle",
        "summary": summary,
        "steps": steps,
        "notice": "TMAP 보행자 경로안내 API의 실제 보행 경로선을 기반으로 자전거 평균 주행속도 15km/h를 적용한 예상 경로입니다. 자전거 전용 경로 API 결과는 아닙니다.",
    }


def route_with_tmap_bicycle(origin: dict[str, Any], destination: dict[str, Any]) -> dict[str, Any]:
    app_key = tmap_walk_key()
    if not app_key:
        raise RuntimeError(f"{TMAP_GENERAL_KEY_ENV} 또는 {TMAP_WALK_KEY_ENV}가 설정되어 있지 않습니다.")
    body = {
        "startX": str(origin["lng"]),
        "startY": str(origin["lat"]),
        "endX": str(destination["lng"]),
        "endY": str(destination["lat"]),
        "angle": 20,
        "speed": 30,
        "reqCoordType": "WGS84GEO",
        "resCoordType": "WGS84GEO",
        "startName": urllib.parse.quote(str(origin.get("label") or "출발")),
        "endName": urllib.parse.quote(str(destination.get("label") or "도착")),
        "searchOption": "30",
        "sort": "index",
    }
    return _normalize_tmap_bicycle(
        _request_json(
            TMAP_WALK_ENDPOINT,
            method="POST",
            headers={"accept": "application/json", "appKey": app_key},
            body=body,
        ),
        origin,
        destination,
    )


def fallback_route(
    origin: dict[str, Any],
    destination: dict[str, Any],
    reason: str,
    transport_mode: str = "transit",
) -> dict[str, Any]:
    mode = transport_mode if transport_mode in {"car", "transit", "bicycle", "walk"} else "transit"
    direct_km = haversine_km(origin["lat"], origin["lng"], destination["lat"], destination["lng"])
    distance_factors = {"car": 1.25, "transit": 1.18, "bicycle": 1.15, "walk": 1.12}
    route_km = max(0.1, direct_km * distance_factors[mode])
    distance_meters = round(route_km * 1000)

    if mode == "car":
        total_minutes = max(5, round(4 + route_km / 30 * 60))
        estimated_cost = max(1000, round(route_km * 180 / 100) * 100)
        summary = {
            "totalMinutes": total_minutes,
            "fare": estimated_cost,
            "estimatedCost": estimated_cost,
            "distanceMeters": distance_meters,
            "totalWalkMeters": 0,
            "transferCount": 0,
            "trafficLabel": "보통",
            "pathType": "estimated_car",
        }
        steps = [{
            "mode": "자동차",
            "route": "추천 자동차 경로",
            "startName": origin["label"],
            "endName": destination["label"],
            "minutes": total_minutes,
            "distanceMeters": distance_meters,
        }]
    elif mode == "bicycle":
        total_minutes = max(5, round(route_km / 15 * 60))
        summary = {
            "totalMinutes": total_minutes,
            "fare": 0,
            "estimatedCalories": round(route_km * 28),
            "distanceMeters": distance_meters,
            "totalWalkMeters": 0,
            "transferCount": 0,
            "pathType": "estimated_bicycle",
        }
        steps = [{
            "mode": "자전거",
            "route": "추천 자전거 경로",
            "startName": origin["label"],
            "endName": destination["label"],
            "minutes": total_minutes,
            "distanceMeters": distance_meters,
        }]
    elif mode == "walk":
        total_minutes = max(5, round(route_km / 4.5 * 60))
        summary = {
            "totalMinutes": total_minutes,
            "fare": 0,
            "stepCount": round(distance_meters / 0.72),
            "distanceMeters": distance_meters,
            "totalWalkMeters": distance_meters,
            "transferCount": 0,
            "pathType": "estimated_walk",
        }
        steps = [{
            "mode": "도보",
            "route": "추천 도보 경로",
            "startName": origin["label"],
            "endName": destination["label"],
            "minutes": total_minutes,
            "distanceMeters": distance_meters,
        }]
    else:
        total_minutes = max(12, round(10 + direct_km * 2.9))
        walk_meters = round(min(1800, 350 + direct_km * 75))
        summary = {
            "totalMinutes": total_minutes,
            "fare": 1550 if direct_km < 10 else 1750,
            "distanceMeters": distance_meters,
            "totalWalkMeters": walk_meters,
            "transferCount": 1 if direct_km > 7 else 0,
            "pathType": "estimated_transit",
        }
        steps = [
            {"mode": "도보", "route": "", "startName": origin["label"], "endName": "인근 역/정류장", "minutes": 7, "distanceMeters": min(walk_meters, 700)},
            {"mode": "대중교통", "route": "추천 대중교통 경로", "startName": "인근 역/정류장", "endName": "목적지 인근", "minutes": max(5, total_minutes - 14), "distanceMeters": max(0, distance_meters - walk_meters)},
            {"mode": "도보", "route": "", "startName": "목적지 인근", "endName": destination["label"], "minutes": 7, "distanceMeters": min(walk_meters, 700)},
        ]

    mode_label = {"car": "자동차", "transit": "대중교통", "bicycle": "자전거", "walk": "도보"}[mode]
    return {
        "ok": True,
        "provider": "fallback",
        "mode": "estimated_fallback",
        "transportMode": mode,
        "origin": origin,
        "destination": destination,
        "summary": summary,
        "steps": steps,
        "coordinates": [origin, destination],
        "notice": f"현재 프로토타입은 {mode_label} 이동을 거리 기반으로 추정합니다. 실제 경로 API 연동 시 도로망 기반 최적 경로로 대체됩니다. 사유: {reason}",
    }


def build_commute_route(
    origin: dict[str, Any],
    destination: dict[str, Any],
    provider: str = "auto",
    transport_mode: str = "transit",
) -> dict[str, Any]:
    errors = []
    selected_mode = transport_mode if transport_mode in {"car", "transit", "bicycle", "walk"} else "transit"
    if selected_mode == "car":
        try:
            return route_with_tmap_car(origin, destination)
        except Exception as exc:  # noqa: BLE001 - fallback keeps prototype available.
            errors.append(f"tmap_car: {exc}")
            fallback = fallback_route(origin, destination, "; ".join(errors), selected_mode)
            fallback["errors"] = errors
            return fallback

    if selected_mode == "walk":
        try:
            return route_with_tmap_walk(origin, destination)
        except Exception as exc:  # noqa: BLE001 - fallback keeps prototype available.
            errors.append(f"tmap_walk: {exc}")
            fallback = fallback_route(origin, destination, "; ".join(errors), selected_mode)
            fallback["errors"] = errors
            return fallback

    if selected_mode == "bicycle":
        try:
            return route_with_tmap_bicycle(origin, destination)
        except Exception as exc:  # noqa: BLE001 - fallback keeps prototype available.
            errors.append(f"tmap_bicycle: {exc}")
            fallback = fallback_route(origin, destination, "; ".join(errors), selected_mode)
            fallback["errors"] = errors
            return fallback

    if selected_mode != "transit":
        return fallback_route(origin, destination, "해당 이동수단 경로 API 연동 전", selected_mode)

    requested = provider if provider in {"auto", "odsay", "tmap"} else "auto"
    providers = ["odsay", "tmap"] if requested == "auto" else [requested]

    for name in providers:
        try:
            if name == "odsay":
                route = route_with_odsay(origin, destination)
                route["transportMode"] = selected_mode
                return route
            if name == "tmap":
                route = route_with_tmap(origin, destination)
                route["transportMode"] = selected_mode
                return route
        except Exception as exc:  # noqa: BLE001 - fallback keeps prototype available.
            errors.append(f"{name}: {exc}")

    fallback = fallback_route(origin, destination, "; ".join(errors) or "사용 가능한 경로 API 키 없음", selected_mode)
    fallback["errors"] = errors
    return fallback


def credential_status() -> dict[str, bool]:
    tmap_transit = bool(env_key(TMAP_KEY_ENV, TMAP_ALT_KEY_ENV))
    tmap_general = bool(tmap_general_key())
    tmap_car = bool(tmap_car_key())
    tmap_walk = bool(tmap_walk_key())
    return {
        "odsay": bool(env_key(OD_SAY_KEY_ENV, OD_SAY_ALT_KEY_ENV)),
        "tmap": tmap_transit,
        "tmapTransit": tmap_transit,
        "tmapGeneral": tmap_general,
        "tmapCar": tmap_car,
        "tmapWalk": tmap_walk,
        "tmapBicycle": tmap_walk,
        "kakao": bool(env_key(KAKAO_KEY_ENV, KAKAO_ALT_KEY_ENV)),
    }
