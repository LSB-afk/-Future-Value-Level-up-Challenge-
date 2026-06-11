"""MoveValue data adapters for route and living-SOC evidence.

The adapters are intentionally dependency-free so the contest prototype can be
rebuilt in a clean Python environment. Live transit routing is optional and
falls back to the checked MVP table when an API key is not configured.
"""

from __future__ import annotations

import json
import math
import os
import time
import urllib.parse
import urllib.request
from typing import Any


DESTINATIONS = {
    "gangnam": {"name": "강남 업무지구", "lat": 37.4979, "lng": 127.0276},
    "yeouido": {"name": "여의도", "lat": 37.5219, "lng": 126.9245},
    "seoulStation": {"name": "서울역/도심", "lat": 37.5547, "lng": 126.9706},
    "digital": {"name": "구로디지털단지", "lat": 37.4853, "lng": 126.9015},
    "pangyo": {"name": "판교", "lat": 37.3947, "lng": 127.1112},
}

OD_SAY_ENDPOINT = "https://api.odsay.com/v1/api/searchPubTransPathT"
OD_SAY_KEY_ENV = "ODSAY_API_KEY"
OD_SAY_ALT_KEY_ENV = "MOVEVALUE_ODSAY_API_KEY"

SOC_RADIUS_METERS = 1600
SAFETY_ENV_RADIUS_METERS = 1800

FACILITY_CATALOG = [
    {"category": "hospital", "name": "건국대학교병원", "lat": 37.5404, "lng": 127.0714},
    {"category": "hospital", "name": "혜민병원", "lat": 37.5368, "lng": 127.0834},
    {"category": "hospital", "name": "서울특별시 동부병원", "lat": 37.5755, "lng": 127.0315},
    {"category": "hospital", "name": "경희대학교병원", "lat": 37.5939, "lng": 127.0515},
    {"category": "hospital", "name": "고려대학교 안암병원", "lat": 37.5870, "lng": 127.0264},
    {"category": "hospital", "name": "한양대학교병원", "lat": 37.5598, "lng": 127.0443},
    {"category": "hospital", "name": "서울특별시 보라매병원", "lat": 37.4933, "lng": 126.9248},
    {"category": "hospital", "name": "에이치플러스 양지병원", "lat": 37.4846, "lng": 126.9303},
    {"category": "hospital", "name": "강남성심병원", "lat": 37.4936, "lng": 126.9081},
    {"category": "hospital", "name": "구로성심병원", "lat": 37.4995, "lng": 126.8858},
    {"category": "hospital", "name": "여의도성모병원", "lat": 37.5186, "lng": 126.9366},
    {"category": "hospital", "name": "공덕연세이비인후과의원", "lat": 37.5449, "lng": 126.9519},
    {"category": "hospital", "name": "상암DMC의원", "lat": 37.5790, "lng": 126.8899},
    {"category": "hospital", "name": "마포보건소", "lat": 37.5661, "lng": 126.9016},
    {"category": "hospital", "name": "강서구보건소", "lat": 37.5509, "lng": 126.8495},
    {"category": "hospital", "name": "이대서울병원", "lat": 37.5577, "lng": 126.8357},
    {"category": "hospital", "name": "김포공항우리들병원", "lat": 37.5610, "lng": 126.8033},
    {"category": "school", "name": "건국대학교", "lat": 37.5410, "lng": 127.0795},
    {"category": "school", "name": "세종대학교", "lat": 37.5509, "lng": 127.0736},
    {"category": "school", "name": "광진중학교", "lat": 37.5415, "lng": 127.0832},
    {"category": "school", "name": "서울대학교", "lat": 37.4599, "lng": 126.9519},
    {"category": "school", "name": "서울대학교 사범대학 부설고등학교", "lat": 37.4820, "lng": 126.9520},
    {"category": "school", "name": "신림고등학교", "lat": 37.4775, "lng": 126.9169},
    {"category": "school", "name": "숭실대학교", "lat": 37.4964, "lng": 126.9572},
    {"category": "school", "name": "경희대학교 서울캠퍼스", "lat": 37.5963, "lng": 127.0525},
    {"category": "school", "name": "서울시립대학교", "lat": 37.5839, "lng": 127.0588},
    {"category": "school", "name": "청량고등학교", "lat": 37.5867, "lng": 127.0463},
    {"category": "school", "name": "한양대학교", "lat": 37.5572, "lng": 127.0453},
    {"category": "school", "name": "무학여자고등학교", "lat": 37.5592, "lng": 127.0325},
    {"category": "school", "name": "성동고등학교", "lat": 37.5640, "lng": 127.0300},
    {"category": "school", "name": "동양미래대학교", "lat": 37.5001, "lng": 126.8672},
    {"category": "school", "name": "구로고등학교", "lat": 37.4941, "lng": 126.8920},
    {"category": "school", "name": "영림중학교", "lat": 37.4869, "lng": 126.8973},
    {"category": "school", "name": "연세대학교", "lat": 37.5658, "lng": 126.9386},
    {"category": "school", "name": "서강대학교", "lat": 37.5510, "lng": 126.9419},
    {"category": "school", "name": "서울여자중학교", "lat": 37.5443, "lng": 126.9534},
    {"category": "school", "name": "마곡하늬중학교", "lat": 37.5685, "lng": 126.8266},
    {"category": "school", "name": "마곡중학교", "lat": 37.5605, "lng": 126.8230},
    {"category": "school", "name": "공항고등학교", "lat": 37.5618, "lng": 126.8151},
    {"category": "school", "name": "상암고등학교", "lat": 37.5766, "lng": 126.8926},
    {"category": "school", "name": "서울상암초등학교", "lat": 37.5698, "lng": 126.8980},
    {"category": "school", "name": "하늘초등학교", "lat": 37.5770, "lng": 126.8839},
    {"category": "school", "name": "방화중학교", "lat": 37.5745, "lng": 126.8119},
    {"category": "school", "name": "송정중학교", "lat": 37.5550, "lng": 126.8134},
    {"category": "school", "name": "서울공항초등학교", "lat": 37.5586, "lng": 126.8126},
    {"category": "park", "name": "서울어린이대공원", "lat": 37.5490, "lng": 127.0818},
    {"category": "park", "name": "뚝섬한강공원", "lat": 37.5307, "lng": 127.0668},
    {"category": "park", "name": "용마산공원", "lat": 37.5735, "lng": 127.0893},
    {"category": "park", "name": "청계천", "lat": 37.5699, "lng": 127.0360},
    {"category": "park", "name": "배봉산근린공원", "lat": 37.5781, "lng": 127.0655},
    {"category": "park", "name": "서울숲", "lat": 37.5444, "lng": 127.0374},
    {"category": "park", "name": "응봉근린공원", "lat": 37.5487, "lng": 127.0299},
    {"category": "park", "name": "보라매공원", "lat": 37.4928, "lng": 126.9180},
    {"category": "park", "name": "도림천", "lat": 37.4826, "lng": 126.9287},
    {"category": "park", "name": "관악산도시자연공원", "lat": 37.4684, "lng": 126.9458},
    {"category": "park", "name": "안양천", "lat": 37.4978, "lng": 126.8848},
    {"category": "park", "name": "구로거리공원", "lat": 37.4948, "lng": 126.8873},
    {"category": "park", "name": "도림천 구로디지털단지 구간", "lat": 37.4854, "lng": 126.9027},
    {"category": "park", "name": "여의도공원", "lat": 37.5261, "lng": 126.9229},
    {"category": "park", "name": "경의선숲길공원", "lat": 37.5486, "lng": 126.9454},
    {"category": "park", "name": "효창공원", "lat": 37.5451, "lng": 126.9604},
    {"category": "park", "name": "서울식물원", "lat": 37.5683, "lng": 126.8352},
    {"category": "park", "name": "마곡나루근린공원", "lat": 37.5656, "lng": 126.8278},
    {"category": "park", "name": "월드컵공원", "lat": 37.5710, "lng": 126.8858},
    {"category": "park", "name": "하늘공원", "lat": 37.5686, "lng": 126.8852},
    {"category": "park", "name": "난지한강공원", "lat": 37.5670, "lng": 126.8759},
    {"category": "park", "name": "방화근린공원", "lat": 37.5797, "lng": 126.8141},
    {"category": "park", "name": "개화산공원", "lat": 37.5724, "lng": 126.8056},
    {"category": "park", "name": "서남물재생센터공원", "lat": 37.5797, "lng": 126.8068},
    {"category": "park", "name": "강서한강공원", "lat": 37.5917, "lng": 126.8187},
]

SAFETY_ENV_CATALOG = [
    {"category": "police", "name": "화양지구대", "lat": 37.5422, "lng": 127.0717},
    {"category": "police", "name": "광진경찰서", "lat": 37.5429, "lng": 127.0836},
    {"category": "police", "name": "신림지구대", "lat": 37.4840, "lng": 126.9291},
    {"category": "police", "name": "관악경찰서", "lat": 37.4740, "lng": 126.9515},
    {"category": "police", "name": "청량리파출소", "lat": 37.5811, "lng": 127.0440},
    {"category": "police", "name": "동대문경찰서", "lat": 37.5851, "lng": 127.0451},
    {"category": "police", "name": "왕십리지구대", "lat": 37.5623, "lng": 127.0359},
    {"category": "police", "name": "성동경찰서", "lat": 37.5636, "lng": 127.0367},
    {"category": "police", "name": "구로디지털단지파출소", "lat": 37.4855, "lng": 126.8995},
    {"category": "police", "name": "구로경찰서", "lat": 37.4944, "lng": 126.8867},
    {"category": "police", "name": "공덕지구대", "lat": 37.5467, "lng": 126.9510},
    {"category": "police", "name": "마포경찰서", "lat": 37.5536, "lng": 126.9528},
    {"category": "police", "name": "마곡지구대", "lat": 37.5661, "lng": 126.8272},
    {"category": "police", "name": "강서경찰서", "lat": 37.5517, "lng": 126.8499},
    {"category": "police", "name": "상암파출소", "lat": 37.5786, "lng": 126.8895},
    {"category": "police", "name": "공항지구대", "lat": 37.5589, "lng": 126.8021},
    {"category": "cctv", "name": "화양동 생활안전 CCTV 집계점", "lat": 37.5410, "lng": 127.0705, "count": 62},
    {"category": "cctv", "name": "신림동 생활안전 CCTV 집계점", "lat": 37.4848, "lng": 126.9290, "count": 78},
    {"category": "cctv", "name": "청량리동 생활안전 CCTV 집계점", "lat": 37.5806, "lng": 127.0452, "count": 58},
    {"category": "cctv", "name": "행당동 생활안전 CCTV 집계점", "lat": 37.5612, "lng": 127.0365, "count": 55},
    {"category": "cctv", "name": "구로동 생활안전 CCTV 집계점", "lat": 37.4864, "lng": 126.9010, "count": 84},
    {"category": "cctv", "name": "공덕동 생활안전 CCTV 집계점", "lat": 37.5452, "lng": 126.9502, "count": 66},
    {"category": "cctv", "name": "마곡동 생활안전 CCTV 집계점", "lat": 37.5666, "lng": 126.8277, "count": 49},
    {"category": "cctv", "name": "상암동 생활안전 CCTV 집계점", "lat": 37.5774, "lng": 126.8904, "count": 46},
    {"category": "cctv", "name": "공항동 생활안전 CCTV 집계점", "lat": 37.5622, "lng": 126.8027, "count": 42},
]

DISTRICT_ENV_PROFILES = {
    "광진구": {"airStation": "광진구 대기측정소", "airQualityScore": 77, "greenScore": 79, "nightSafetyIndex": 76},
    "관악구": {"airStation": "관악구 대기측정소", "airQualityScore": 74, "greenScore": 84, "nightSafetyIndex": 73},
    "동대문구": {"airStation": "동대문구 대기측정소", "airQualityScore": 75, "greenScore": 76, "nightSafetyIndex": 75},
    "성동구": {"airStation": "성동구 대기측정소", "airQualityScore": 78, "greenScore": 82, "nightSafetyIndex": 78},
    "구로구": {"airStation": "구로구 대기측정소", "airQualityScore": 73, "greenScore": 75, "nightSafetyIndex": 74},
    "마포구": {"airStation": "마포구 대기측정소", "airQualityScore": 76, "greenScore": 83, "nightSafetyIndex": 77},
    "강서구": {"airStation": "강서구 대기측정소", "airQualityScore": 77, "greenScore": 86, "nightSafetyIndex": 76},
}


def clamp(value: float, low: int = 0, high: int = 100) -> int:
    return round(max(low, min(high, value)))


def haversine_meters(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    radius = 6_371_000
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lam = math.radians(lng2 - lng1)
    a = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lam / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(a))


def _odsay_key() -> str:
    return os.getenv(OD_SAY_KEY_ENV, "").strip() or os.getenv(OD_SAY_ALT_KEY_ENV, "").strip()


def _query_odsay_minutes(area_def: dict[str, Any], destination: dict[str, Any], api_key: str) -> int:
    params = {
        "SX": area_def["lng"],
        "SY": area_def["lat"],
        "EX": destination["lng"],
        "EY": destination["lat"],
        "apiKey": api_key,
        "output": "json",
    }
    url = f"{OD_SAY_ENDPOINT}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(url, headers={"User-Agent": "MoveValue/0.1"})
    with urllib.request.urlopen(request, timeout=12) as response:
        payload = json.loads(response.read().decode("utf-8"))

    if payload.get("error"):
        message = payload["error"].get("msg") or payload["error"].get("message") or "ODsay error"
        raise RuntimeError(message)

    paths = payload.get("result", {}).get("path") or []
    times = []
    for path in paths:
        total_time = path.get("info", {}).get("totalTime")
        if isinstance(total_time, (int, float)) and total_time > 0:
            times.append(int(round(total_time)))
    if not times:
        raise RuntimeError("ODsay response has no route totalTime")
    return min(times)


def build_commute_minutes(area_def: dict[str, Any], pause_seconds: float = 0.12) -> tuple[dict[str, int], dict[str, Any]]:
    """Return commute minutes and source evidence.

    With ODSAY_API_KEY set, each origin-destination pair is refreshed from the
    public-transit routing API. Any failed route falls back to the existing MVP
    table so dataset generation remains reproducible without credentials.
    """

    table = dict(area_def["commuteMinutes"])
    api_key = _odsay_key()
    if not api_key:
        return table, {
            "commuteSource": "MVP 통근시간 테이블",
            "commuteMode": "table_fallback",
            "commuteProvider": "fallback",
            "apiKeyEnv": OD_SAY_KEY_ENV,
            "fallbackUsed": True,
            "fallbackDestinations": list(table.keys()),
        }

    minutes = {}
    fallback_destinations = []
    errors = {}
    for destination_id, destination in DESTINATIONS.items():
        try:
            minutes[destination_id] = _query_odsay_minutes(area_def, destination, api_key)
            time.sleep(pause_seconds)
        except Exception as exc:  # noqa: BLE001 - fallback is intentional for offline rebuilds.
            minutes[destination_id] = table[destination_id]
            fallback_destinations.append(destination_id)
            errors[destination_id] = str(exc)

    return minutes, {
        "commuteSource": "ODsay 대중교통 경로 API",
        "commuteMode": "odsay_api_with_table_fallback" if fallback_destinations else "odsay_api",
        "commuteProvider": "odsay",
        "apiKeyEnv": OD_SAY_KEY_ENV,
        "fallbackUsed": bool(fallback_destinations),
        "fallbackDestinations": fallback_destinations,
        "errors": errors,
    }


def _nearest_facility(
    area_def: dict[str, Any],
    category: str,
    facilities: list[dict[str, Any]],
) -> dict[str, Any]:
    candidates = [item for item in facilities if item["category"] == category]
    nearest = min(
        candidates,
        key=lambda item: haversine_meters(area_def["lat"], area_def["lng"], item["lat"], item["lng"]),
    )
    distance = haversine_meters(area_def["lat"], area_def["lng"], nearest["lat"], nearest["lng"])
    return {"name": nearest["name"], "distanceMeters": round(distance)}


def build_soc_metrics(area_def: dict[str, Any]) -> dict[str, Any]:
    """Aggregate hospitals, schools, and parks around an area coordinate."""

    within = []
    for facility in FACILITY_CATALOG:
        distance = haversine_meters(area_def["lat"], area_def["lng"], facility["lat"], facility["lng"])
        if distance <= SOC_RADIUS_METERS:
            within.append({**facility, "distanceMeters": round(distance)})

    counts = {
        "hospital": sum(1 for item in within if item["category"] == "hospital"),
        "school": sum(1 for item in within if item["category"] == "school"),
        "park": sum(1 for item in within if item["category"] == "park"),
    }
    nearest = {
        "hospital": _nearest_facility(area_def, "hospital", FACILITY_CATALOG),
        "school": _nearest_facility(area_def, "school", FACILITY_CATALOG),
        "park": _nearest_facility(area_def, "park", FACILITY_CATALOG),
    }

    near_bonus = 0
    for item in nearest.values():
        near_bonus += max(0, (SOC_RADIUS_METERS - item["distanceMeters"]) / SOC_RADIUS_METERS) * 3

    score = clamp(
        46
        + min(counts["hospital"], 4) * 5.0
        + min(counts["school"], 7) * 3.1
        + min(counts["park"], 5) * 4.8
        + near_bonus
        + min(area_def.get("lineCount", 1), 5) * 1.4,
        45,
        100,
    )

    top_facilities = sorted(within, key=lambda item: item["distanceMeters"])[:8]
    return {
        "score": score,
        "source": "서울 열린데이터광장 병의원·학교·공원 좌표 스냅샷 반경 집계",
        "mode": "public_coordinate_snapshot",
        "radiusMeters": SOC_RADIUS_METERS,
        "counts": counts,
        "nearestFacilities": nearest,
        "facilityRecords": len(within),
        "sampleFacilities": [
            {
                "category": item["category"],
                "name": item["name"],
                "distanceMeters": item["distanceMeters"],
            }
            for item in top_facilities
        ],
    }


def _district_name(area_def: dict[str, Any]) -> str:
    return str(area_def.get("rentDistrict") or area_def.get("district", "")).replace("서울", "").strip()


def _nearest_from_items(items: list[dict[str, Any]], category: str) -> dict[str, Any] | None:
    candidates = [item for item in items if item["category"] == category]
    if not candidates:
        return None
    nearest = min(candidates, key=lambda item: item["distanceMeters"])
    return {
        "name": nearest["name"],
        "distanceMeters": nearest["distanceMeters"],
        **({"count": nearest["count"]} if "count" in nearest else {}),
    }


def build_safety_env_metrics(area_def: dict[str, Any], soc_metrics: dict[str, Any]) -> dict[str, Any]:
    """Aggregate public safety and environmental evidence around an area."""

    within = []
    for item in SAFETY_ENV_CATALOG:
        distance = haversine_meters(area_def["lat"], area_def["lng"], item["lat"], item["lng"])
        if distance <= SAFETY_ENV_RADIUS_METERS:
            within.append({**item, "distanceMeters": round(distance)})

    police_count = sum(1 for item in within if item["category"] == "police")
    cctv_cluster_count = sum(1 for item in within if item["category"] == "cctv")
    cctv_units = sum(int(item.get("count", 0)) for item in within if item["category"] == "cctv")
    park_count = int(soc_metrics.get("counts", {}).get("park", 0))
    nearest_park = soc_metrics.get("nearestFacilities", {}).get("park", {})
    nearest_park_distance = float(nearest_park.get("distanceMeters") or SAFETY_ENV_RADIUS_METERS)
    district_profile = DISTRICT_ENV_PROFILES.get(
        _district_name(area_def),
        {"airStation": "서울시 도시대기 측정망", "airQualityScore": 75, "greenScore": 78, "nightSafetyIndex": 75},
    )

    safety_score = clamp(
        48
        + min(police_count, 3) * 7.0
        + min(cctv_units, 90) * 0.22
        + min(area_def.get("lineCount", 1), 5) * 1.5
        + district_profile["nightSafetyIndex"] * 0.08,
        45,
        100,
    )
    park_distance_bonus = max(0, (SAFETY_ENV_RADIUS_METERS - nearest_park_distance) / SAFETY_ENV_RADIUS_METERS) * 6
    environment_score = clamp(
        49
        + min(park_count, 5) * 5.2
        + district_profile["airQualityScore"] * 0.16
        + district_profile["greenScore"] * 0.16
        + park_distance_bonus,
        45,
        100,
    )

    sample_facilities = sorted(within, key=lambda item: item["distanceMeters"])[:6]
    return {
        "safetyScore": safety_score,
        "environmentScore": environment_score,
        "source": "서울시 안전시설·CCTV 집계점, 도시대기 측정망, 공원 좌표 스냅샷 결합",
        "mode": "public_snapshot_scoring",
        "radiusMeters": SAFETY_ENV_RADIUS_METERS,
        "counts": {
            "police": police_count,
            "cctvClusters": cctv_cluster_count,
            "cctv": cctv_units,
            "park": park_count,
        },
        "nearestFacilities": {
            "police": _nearest_from_items(within, "police"),
            "cctv": _nearest_from_items(within, "cctv"),
            "park": nearest_park,
        },
        "airStation": district_profile["airStation"],
        "airQualityScore": district_profile["airQualityScore"],
        "greenScore": district_profile["greenScore"],
        "nightSafetyIndex": district_profile["nightSafetyIndex"],
        "facilityRecords": len(within),
        "sampleFacilities": [
            {
                "category": item["category"],
                "name": item["name"],
                "distanceMeters": item["distanceMeters"],
                **({"count": item["count"]} if "count" in item else {}),
            }
            for item in sample_facilities
        ],
    }


def adapter_source_meta() -> dict[str, Any]:
    return {
        "transitSource": {
            "name": "ODsay 대중교통 경로 API 어댑터",
            "url": "https://lab.odsay.com/guide/guide",
            "apiKeyEnv": OD_SAY_KEY_ENV,
            "fallback": "API 키 미설정 또는 호출 실패 시 기존 MVP 통근시간 테이블을 사용합니다.",
        },
        "socSource": {
            "name": "서울 열린데이터광장 생활 SOC 좌표 스냅샷",
            "radiusMeters": SOC_RADIUS_METERS,
            "datasets": [
                {
                    "name": "서울시 병의원 위치 정보",
                    "url": "https://data.seoul.go.kr/dataList/OA-20337/S/1/datasetView.do",
                },
                {
                    "name": "서울시 학교 기본정보",
                    "url": "https://data.seoul.go.kr/dataList/OA-20502/S/1/datasetView.do",
                },
                {
                    "name": "서울시 주요 공원현황",
                    "url": "https://data.seoul.go.kr/dataList/OA-394/S/1/datasetView.do",
                },
            ],
        },
        "safetyEnvSource": {
            "name": "서울시 안전·환경 공공데이터 스냅샷",
            "radiusMeters": SAFETY_ENV_RADIUS_METERS,
            "datasets": [
                {
                    "name": "서울시 생활안전 CCTV 및 치안시설 위치/집계 데이터",
                    "url": "https://data.seoul.go.kr/",
                },
                {
                    "name": "서울시 도시대기 측정망",
                    "url": "https://data.seoul.go.kr/",
                },
                {
                    "name": "서울시 주요 공원현황",
                    "url": "https://data.seoul.go.kr/dataList/OA-394/S/1/datasetView.do",
                },
            ],
        },
    }
