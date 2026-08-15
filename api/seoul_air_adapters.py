"""Seoul Open API adapter for district-level real-time air quality."""

from __future__ import annotations

import json
import os
import time
import urllib.parse
import urllib.request
from typing import Any

from env_loader import load_dotenv


API_NAME = "ListAirQualityByDistrictService"
API_URL = "http://openapi.seoul.go.kr:8088/{key}/json/ListAirQualityByDistrictService/1/25/"
API_KEY_ENVS = (
    "SEOUL_AIR_API_KEY",
    "SEOUL_OPEN_API_KEY",
    "SEOUL_API_KEY",
    "MOVEVALUE_SEOUL_OPEN_API_KEY",
)
CACHE_SECONDS = 60 * 30

_CACHE: tuple[float, dict[str, Any]] | None = None

load_dotenv()


def _env_key() -> str:
    load_dotenv()
    for name in API_KEY_ENVS:
        value = os.getenv(name, "").strip()
        if value and value != "sample":
            return value
    return ""


def seoul_air_status() -> dict[str, Any]:
    return {
        "seoulAir": bool(_env_key()),
        "seoulAirSource": "Seoul Open API",
        "seoulAirApi": API_NAME,
    }


def _single_value(raw: dict[str, list[str]], name: str, default: str = "") -> str:
    return raw.get(name, [default])[0].strip()


def _compact(value: str) -> str:
    return (
        str(value or "")
        .replace("서울특별시", "")
        .replace("서울시", "")
        .replace("서울", "")
        .replace(" ", "")
        .strip()
    )


def _number(value: Any) -> float | None:
    try:
        if value in {"", None, "-"}:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _grade_score(grade: str, cai: float | None) -> int:
    text = str(grade or "").strip()
    if text == "1":
        return 100
    if text == "2":
        return 75
    if text == "3":
        return 45
    if text == "4":
        return 15
    if "좋음" in text:
        return 100
    if "보통" in text:
        return 75
    if "매우" in text and "나쁨" in text:
        return 15
    if "나쁨" in text:
        return 45
    if cai is None:
        return 0
    if cai <= 50:
        return 100
    if cai <= 100:
        return 75
    if cai <= 250:
        return 45
    return 15


def _grade_label(grade: str) -> str:
    text = str(grade or "").strip()
    return {
        "1": "좋음",
        "2": "보통",
        "3": "나쁨",
        "4": "매우나쁨",
    }.get(text, text or "정보 없음")


def _field(row: dict[str, Any], *names: str, default: str = "") -> str:
    for name in names:
        value = row.get(name)
        if value not in {"", None}:
            return str(value).strip()
    return default


def _station_name(row: dict[str, Any]) -> str:
    return _field(row, "MSRSTN_NM", "MSRSTE_NM", "MSRSTENAME", "MSRSTE_NM_KOR", "STATION_NM")


def _normalize_row(row: dict[str, Any]) -> dict[str, Any]:
    station = _station_name(row)
    grade = _field(row, "IDEX_NM", "CAI_GRD", "GRADE", "INDEX_NM")
    cai = _number(_field(row, "IDEX_MVL", "CAI", "MAXINDEX", "INDEX_MVL"))
    pm10 = _number(_field(row, "PM", "PM10", "PM10_VALUE"))
    pm25 = _number(_field(row, "FPM", "PM25", "PM2_5", "PM25_VALUE"))
    measured_at = _field(row, "MSRMT_YMD", "MSRDT", "MSRDATE", "DATA_TIME", "UPDATE_DT")
    score = _grade_score(grade, cai)
    grade_label = _grade_label(grade)
    return {
        "label": "대기환경",
        "station": station,
        "district": station,
        "grade": grade_label,
        "score": score,
        "cai": cai,
        "pm10": pm10,
        "pm25": pm25,
        "mainPollutant": _field(row, "ARPLT_MAIN", "POLLUTANT", "MAIN_POLLUTANT"),
        "measuredAt": measured_at,
        "source": "seoul_open_api",
        "nearest": {
            "category": "air",
            "name": f"{station} 대기측정소" if station else "대기측정소",
            "distanceMeters": None,
            "source": "seoul_open_api",
        },
    }


def _fetch_rows(api_key: str) -> list[dict[str, Any]]:
    global _CACHE
    now = time.time()
    if _CACHE and now - _CACHE[0] < CACHE_SECONDS:
        return list(_CACHE[1].get("rows", []))

    url = API_URL.format(key=urllib.parse.quote(api_key, safe=""))
    request = urllib.request.Request(url, headers={"User-Agent": "MoveValue/0.1"})
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(request, timeout=7) as response:
        payload = json.loads(response.read().decode("utf-8"))

    service = payload.get(API_NAME) or payload.get("ListAirQualityByDistrictService") or {}
    result = service.get("RESULT") or {}
    code = str(result.get("CODE") or "")
    if code and code != "INFO-000":
        message = result.get("MESSAGE") or "서울시 대기환경 API 호출에 실패했습니다."
        raise RuntimeError(f"{code}: {message}")

    rows = service.get("row") or []
    if not isinstance(rows, list):
        rows = []
    _CACHE = (now, {"rows": rows})
    return rows


def seoul_air_response(raw: dict[str, list[str]]) -> dict[str, Any]:
    api_key = _env_key()
    district = _single_value(raw, "district")
    if not district:
        return {"ok": False, "error": "구 이름이 필요합니다.", "integrations": seoul_air_status()}

    if not api_key:
        return {
            "ok": True,
            "mode": "missing_key",
            "district": district,
            "source": "Seoul Open API",
            "air": None,
            "integrations": seoul_air_status(),
        }

    try:
        rows = _fetch_rows(api_key)
        target = _compact(district)
        matched = next((row for row in rows if _compact(_station_name(row)) == target), None)
        if not matched:
            matched = next((row for row in rows if target and target in _compact(_station_name(row))), None)
        if not matched:
            return {
                "ok": True,
                "mode": "not_found",
                "district": district,
                "source": "Seoul Open API",
                "air": None,
                "integrations": seoul_air_status(),
            }
        return {
            "ok": True,
            "mode": "live_api",
            "district": district,
            "source": "Seoul Open API",
            "air": _normalize_row(matched),
            "integrations": seoul_air_status(),
        }
    except Exception as exc:  # noqa: BLE001 - expose status without crashing the page.
        return {
            "ok": True,
            "mode": "error",
            "district": district,
            "source": "Seoul Open API",
            "air": None,
            "error": str(exc),
            "integrations": seoul_air_status(),
        }
