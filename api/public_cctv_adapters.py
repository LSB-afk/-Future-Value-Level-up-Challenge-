"""Public Data Portal CCTV adapter for nearby safety cameras."""

from __future__ import annotations

import json
import math
import os
import time
import urllib.parse
import urllib.request
from typing import Any

from env_loader import load_dotenv


API_URL = "http://apis.data.go.kr/1741000/cctv_info/info"
API_KEY_ENVS = ("PUBLIC_CCTV_API_KEY", "CCTV_API_KEY", "MOVEVALUE_CCTV_API_KEY")
DEFAULT_RADIUS_METERS = 1000
MAX_RADIUS_METERS = 20000
PAGE_SIZE = 100
MAX_PAGES_PER_DISTRICT = 80
CACHE_SECONDS = 60 * 60 * 12

_CACHE: dict[str, tuple[float, list[dict[str, Any]]]] = {}

load_dotenv()


def _env_key() -> str:
    load_dotenv()
    for name in API_KEY_ENVS:
        value = os.getenv(name, "").strip()
        if value and value != "sample":
            return value
    return ""


def public_cctv_status() -> dict[str, Any]:
    return {
        "publicCctv": bool(_env_key()),
        "publicCctvRadiusMeters": DEFAULT_RADIUS_METERS,
        "publicCctvSource": "Public Data Portal",
    }


def _single_value(raw: dict[str, list[str]], name: str, default: str = "") -> str:
    return raw.get(name, [default])[0].strip()


def _number(value: Any) -> float | None:
    try:
        if value in {"", None, "-"}:
            return None
        return float(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def _integer(value: Any, default: int = 0) -> int:
    number = _number(value)
    return int(round(number)) if number is not None else default


def _field(row: dict[str, Any], *names: str, default: str = "") -> str:
    for name in names:
        value = row.get(name)
        if value not in {"", None}:
            return str(value).strip()
    return default


def _lat_lng(row: dict[str, Any]) -> tuple[float, float] | None:
    lat = _number(_field(row, "WGS84_LAT", "LAT", "PSTN_LAT", "LTTD", "위도"))
    lng = _number(_field(row, "WGS84_LOT", "WGS84_LON", "LOT", "LON", "PSTN_LOT", "LGTD", "경도"))
    if lat is None or lng is None:
        return None
    if not (33 <= lat <= 39 and 124 <= lng <= 132):
        return None
    return lat, lng


def _haversine_meters(a_lat: float, a_lng: float, b_lat: float, b_lng: float) -> float:
    radius = 6371008.8
    phi1 = math.radians(a_lat)
    phi2 = math.radians(b_lat)
    d_phi = math.radians(b_lat - a_lat)
    d_lambda = math.radians(b_lng - a_lng)
    h = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return radius * 2 * math.atan2(math.sqrt(h), math.sqrt(1 - h))


def _clean_district(value: str) -> str:
    district = str(value or "").strip()
    district = district.replace("서울특별시", "").replace("서울시", "").replace("서울", "").strip()
    return district


def _district_query(value: str) -> str:
    district = _clean_district(value)
    if not district:
        return ""
    return f"서울특별시 {district}"


def _request_page(api_key: str, condition_name: str, condition_value: str, page: int) -> dict[str, Any]:
    params = {
        "serviceKey": api_key,
        "pageNo": page,
        "numOfRows": PAGE_SIZE,
        "returnType": "json",
        condition_name: condition_value,
    }
    query = urllib.parse.urlencode(params, safe="%")
    request = urllib.request.Request(f"{API_URL}?{query}", headers={"User-Agent": "MoveValue/0.1"})
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(request, timeout=10) as response:
        body = response.read().decode("utf-8", errors="replace")
    try:
        return json.loads(body)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"CCTV API가 JSON이 아닌 응답을 반환했습니다: {body[:160]}") from exc


def _items_from_payload(payload: dict[str, Any]) -> tuple[list[dict[str, Any]], int]:
    if "OpenAPI_ServiceResponse" in payload:
        header = payload.get("OpenAPI_ServiceResponse", {}).get("cmmMsgHeader", {})
        message = header.get("returnAuthMsg") or header.get("errMsg") or "CCTV API 인증 오류"
        raise RuntimeError(str(message))

    response = payload.get("response") or payload
    header = response.get("header") or {}
    result_code = str(header.get("resultCode") or header.get("resultCd") or "")
    if result_code and result_code not in {"00", "0", "INFO-000"}:
        raise RuntimeError(str(header.get("resultMsg") or header.get("resultMessage") or result_code))

    body = response.get("body") or response
    total_count = _integer(body.get("totalCount") or body.get("totalCnt") or body.get("total_count"), 0)
    items_raw = body.get("items") or body.get("item") or []
    if isinstance(items_raw, dict) and "item" in items_raw:
        items_raw = items_raw.get("item") or []
    if isinstance(items_raw, dict):
        items_raw = [items_raw]
    if not isinstance(items_raw, list):
        items_raw = []
    return [item for item in items_raw if isinstance(item, dict)], total_count


def _normalize_cctv(row: dict[str, Any], origin_lat: float, origin_lng: float) -> dict[str, Any] | None:
    coords = _lat_lng(row)
    if not coords:
        return None
    lat, lng = coords
    address = _field(row, "LCTN_ROAD_NM_ADDR", "LCTN_LOTNO_ADDR", "ADDR", "소재지도로명주소", "소재지지번주소")
    name = _field(row, "INSTL_PLC_NM", "LCTN_NM", "CCTV_NM", "설치장소명", default="CCTV")
    camera_count = max(1, _integer(_field(row, "CAM_CNTOM", "CCTV_CNT", "CAMERA_CNT", "카메라대수"), 1))
    distance = round(_haversine_meters(origin_lat, origin_lng, lat, lng))
    return {
        "id": _field(row, "SN", "ID", "CCTV_ID", default=f"{lat:.6f},{lng:.6f},{name}"),
        "category": "cctv",
        "name": name,
        "distanceMeters": distance,
        "lat": lat,
        "lng": lng,
        "address": address,
        "purpose": _field(row, "INSTL_PURPS_TYPE_NM", "PRPS_NM", "설치목적구분"),
        "manager": _field(row, "MNG_INST_NM", "관리기관명"),
        "installedAt": _field(row, "INSTL_YM", "설치연월"),
        "count": camera_count,
        "source": "public_data_portal_cctv",
    }


def _district_rows(api_key: str, district: str) -> list[dict[str, Any]]:
    district = _clean_district(district)
    cache_key = district
    cached = _CACHE.get(cache_key)
    now = time.time()
    if cached and now - cached[0] < CACHE_SECONDS:
        return list(cached[1])

    query_specs = [
        ("cond[MNG_INST_NM::LIKE]", f"{district}청"),
        ("cond[MNG_INST_NM::LIKE]", f"서울특별시 {district}청"),
        ("cond[LCTN_ROAD_NM_ADDR::LIKE]", _district_query(district)),
        ("cond[LCTN_LOTNO_ADDR::LIKE]", _district_query(district)),
    ]
    rows_by_key: dict[str, dict[str, Any]] = {}
    for condition_name, condition_value in query_specs:
        if not condition_value:
            continue
        fetched = 0
        total_count = 0
        for page in range(1, MAX_PAGES_PER_DISTRICT + 1):
            payload = _request_page(api_key, condition_name, condition_value, page)
            page_items, total_count = _items_from_payload(payload)
            for row in page_items:
                key = _field(row, "MNG_NO", "SN", "ID", default="")
                if not key:
                    key = "|".join(
                        (
                            _field(row, "WGS84_LAT", "PSTN_LAT", "LTTD"),
                            _field(row, "WGS84_LOT", "PSTN_LOT", "LGTD"),
                            _field(row, "LCTN_ROAD_NM_ADDR", "LCTN_LOTNO_ADDR"),
                        )
                    )
                if key:
                    rows_by_key[key] = row
            fetched += len(page_items)
            if not page_items:
                break
            if total_count and fetched >= total_count:
                break
            if len(page_items) < PAGE_SIZE:
                break

    rows = list(rows_by_key.values())
    _CACHE[cache_key] = (now, rows)
    return rows


def public_cctv_response(raw: dict[str, list[str]]) -> dict[str, Any]:
    api_key = _env_key()
    try:
        lat = float(_single_value(raw, "lat"))
        lng = float(_single_value(raw, "lng"))
    except (TypeError, ValueError):
        return {"ok": False, "error": "아파트 좌표가 필요합니다.", "integrations": public_cctv_status()}

    district = _single_value(raw, "district")
    if not district:
        return {"ok": False, "error": "구 이름이 필요합니다.", "integrations": public_cctv_status()}

    try:
        radius = int(float(_single_value(raw, "radius", str(DEFAULT_RADIUS_METERS))))
    except ValueError:
        radius = DEFAULT_RADIUS_METERS
    radius = max(1, min(radius, MAX_RADIUS_METERS))

    if not api_key:
        return {
            "ok": True,
            "mode": "missing_key",
            "district": district,
            "radiusMeters": radius,
            "category": {"label": "CCTV", "count": 0, "siteCount": 0, "nearest": None, "samples": []},
            "integrations": public_cctv_status(),
        }

    try:
        rows = _district_rows(api_key, district)
        deduped: dict[str, dict[str, Any]] = {}
        for row in rows:
            item = _normalize_cctv(row, lat, lng)
            if not item or item["distanceMeters"] > radius:
                continue
            key = "|".join(
                str(value or "")
                for value in (
                    item.get("id"),
                    f"{float(item.get('lat') or 0):.6f}",
                    f"{float(item.get('lng') or 0):.6f}",
                    item.get("address"),
                )
            )
            if key not in deduped or int(item.get("distanceMeters") or 0) < int(deduped[key].get("distanceMeters") or 0):
                deduped[key] = item

        normalized = sorted(deduped.values(), key=lambda item: int(item.get("distanceMeters") or 0))
        camera_total = sum(max(1, _integer(item.get("count"), 1)) for item in normalized)
        return {
            "ok": True,
            "mode": "live_api",
            "district": district,
            "radiusMeters": radius,
            "source": "Public Data Portal CCTV API",
            "category": {
                "label": "CCTV",
                "count": camera_total,
                "siteCount": len(normalized),
                "nearest": normalized[0] if normalized else None,
                "samples": normalized[:30],
                "source": "public_data_portal_cctv",
            },
            "integrations": public_cctv_status(),
        }
    except Exception as exc:  # noqa: BLE001 - keep the UI usable with fallback data.
        return {
            "ok": True,
            "mode": "error",
            "district": district,
            "radiusMeters": radius,
            "source": "Public Data Portal CCTV API",
            "category": None,
            "error": str(exc),
            "integrations": public_cctv_status(),
        }
