"""Apartment complex data adapter for the MoveValue map layer."""

from __future__ import annotations

import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

from property_model import build_property_preview


ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_PATH = ROOT / "data" / "apartments.seoul.snapshot.json"
API_NAME = "OpenAptInfo"
API_URL = "http://openapi.seoul.go.kr:8088/{key}/json/OpenAptInfo/{start}/{end}/"
API_KEY_ENVS = ("SEOUL_OPEN_API_KEY", "SEOUL_API_KEY", "MOVEVALUE_SEOUL_OPEN_API_KEY")
SOURCE_META = {
    "name": "서울시 공동주택 아파트 정보",
    "url": "https://data.seoul.go.kr/dataList/OA-15818/S/1/datasetView.do",
    "apiName": API_NAME,
    "endpoint": "http://openapi.seoul.go.kr:8088/{KEY}/json/OpenAptInfo/{START_INDEX}/{END_INDEX}/",
}

_CACHE: dict[str, dict] = {}


def seoul_open_api_key() -> str:
    for name in API_KEY_ENVS:
        value = os.getenv(name, "").strip()
        if value and value != "sample":
            return value
    return ""


def apartment_credential_status() -> dict:
    return {"seoulOpenApi": bool(seoul_open_api_key())}


def number(value, default=0):
    try:
        if value in {"", None}:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def integer(value, default=0):
    return int(round(number(value, default)))


def clean_date(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    return text.split(" ")[0]


def normalize_row(row: dict) -> dict | None:
    lat = number(row.get("YCRD"))
    lng = number(row.get("XCRD"))
    if not lat or not lng:
        return None

    approval_date = clean_date(row.get("USE_APRV_YMD"))
    approval_year = integer(approval_date[:4], 0) if approval_date[:4].isdigit() else 0
    address = row.get("APT_RDN_ADDR") or " ".join(
        part for part in [row.get("CTPV_ADDR"), row.get("SGG_ADDR"), row.get("EMD_ADDR"), row.get("DADDR")] if part
    )
    return {
        "id": str(row.get("APT_CD") or row.get("EPIS_MNG_NO") or row.get("SN")),
        "name": str(row.get("APT_NM") or row.get("DADDR") or "이름 미상").strip(),
        "category": str(row.get("CMPX_CLSF") or "공동주택").strip(),
        "address": address.strip(),
        "district": str(row.get("SGG_ADDR") or "").strip(),
        "dong": str(row.get("EMD_ADDR") or "").strip(),
        "lat": round(lat, 7),
        "lng": round(lng, 7),
        "households": integer(row.get("TNOHSH")),
        "buildingCount": integer(row.get("WHOL_DONG_CNT")),
        "approvalDate": approval_date,
        "approvalYear": approval_year,
        "housingType": str(row.get("HH_TYPE") or "").strip(),
        "heating": str(row.get("MN_MTHD") or "").strip(),
        "managementMethod": str(row.get("MNG_MTHD") or "").strip(),
        "parkingCount": integer(row.get("PRK_CNTOM")),
        "grossFloorAreaM2": round(number(row.get("GFA")), 2),
        "sourceUpdatedAt": clean_date(row.get("MDFCN_YMD")),
    }


def fetch_page(key: str, start: int, end: int) -> dict:
    url = API_URL.format(key=key, start=start, end=end)
    try:
        with urlopen(url, timeout=20) as response:  # noqa: S310 - official public API endpoint.
            return json.loads(response.read().decode("utf-8"))
    except (URLError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"서울 공동주택 API 호출 실패: {exc}") from exc


def fetch_live_dataset(key: str) -> dict:
    page_size = 1000
    first = fetch_page(key, 1, 1)
    root = first.get(API_NAME, {})
    total = int(root.get("list_total_count") or 0)
    if total <= 0:
        raise RuntimeError("서울 공동주택 API 응답에 총 건수가 없습니다.")

    apartments: list[dict] = []
    for start in range(1, total + 1, page_size):
        end = min(start + page_size - 1, total)
        payload = fetch_page(key, start, end)
        rows = payload.get(API_NAME, {}).get("row", [])
        apartments.extend(item for row in rows if (item := normalize_row(row)))
    apartments.sort(key=lambda item: (item["district"], item["dong"], item["name"]))
    return {
        "meta": {
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "source": SOURCE_META,
            "totalRecords": total,
            "recordsWithCoordinates": len(apartments),
            "complete": True,
            "coordinateFields": {"lat": "YCRD", "lng": "XCRD"},
            "note": "서울 열린데이터광장 OpenAptInfo live API에서 정규화한 공동주택 단지 데이터입니다.",
        },
        "apartments": apartments,
    }


def load_snapshot() -> dict:
    with SNAPSHOT_PATH.open(encoding="utf-8") as file:
        return json.load(file)


def load_apartment_dataset() -> tuple[dict, str, str]:
    key = seoul_open_api_key()
    if key:
        cache_key = f"live:{key[:4]}"
        if cache_key not in _CACHE:
            try:
                _CACHE[cache_key] = fetch_live_dataset(key)
            except RuntimeError as exc:
                _CACHE["last_error"] = {"error": str(exc)}
                return load_snapshot(), "snapshot_fallback", str(exc)
        return _CACHE[cache_key], "live_api", ""
    return load_snapshot(), "snapshot", ""


def parse_bounds(value: str) -> tuple[float, float, float, float] | None:
    if not value:
        return None
    try:
        south, west, north, east = [float(part) for part in value.split(",")]
    except ValueError:
        return None
    if south > north:
        south, north = north, south
    if west > east:
        west, east = east, west
    return south, west, north, east


def in_bounds(item: dict, bounds: tuple[float, float, float, float] | None) -> bool:
    if not bounds:
        return True
    south, west, north, east = bounds
    return south <= float(item["lat"]) <= north and west <= float(item["lng"]) <= east


def cluster_step(zoom: int) -> float:
    if zoom >= 15:
        return 0
    if zoom >= 14:
        return 0.006
    if zoom >= 13:
        return 0.01
    if zoom >= 12:
        return 0.018
    if zoom >= 11:
        return 0.03
    return 0.05


def apartment_feature(item: dict) -> dict:
    return {"type": "apartment", "pricePreview": build_property_preview(item), **item}


def cluster_price_preview(members: list[dict]) -> dict:
    previews = [build_property_preview(item) for item in members]
    if not previews:
        return {}
    avg_sale = sum(float(item.get("sale10k") or 0) for item in previews) / len(previews)
    avg_jeonse_ratio = sum(float(item.get("jeonseRatio") or 0) for item in previews) / len(previews)
    risk_counts = {"high": 0, "warning": 0, "low": 0}
    for item in previews:
        key = item.get("riskLevelKey") or "low"
        risk_counts[key] = risk_counts.get(key, 0) + 1
    dominant = max(risk_counts.items(), key=lambda pair: pair[1])[0]
    return {
        "sale10k": round(avg_sale),
        "jeonseRatio": round(avg_jeonse_ratio, 1),
        "riskLevelKey": dominant,
        "riskCounts": risk_counts,
    }


def cluster_apartments(apartments: list[dict], zoom: int) -> list[dict]:
    step = cluster_step(zoom)
    if not step:
        return [apartment_feature(item) for item in apartments]

    buckets: dict[tuple[int, int], list[dict]] = {}
    for item in apartments:
        key = (math.floor(float(item["lat"]) / step), math.floor(float(item["lng"]) / step))
        buckets.setdefault(key, []).append(item)

    features: list[dict] = []
    for key, members in buckets.items():
        if len(members) == 1:
            features.append(apartment_feature(members[0]))
            continue
        total_households = sum(int(item.get("households") or 0) for item in members)
        districts = sorted({item.get("district", "") for item in members if item.get("district")})
        sample_names = [item["name"] for item in sorted(members, key=lambda item: item.get("households", 0), reverse=True)[:3]]
        features.append(
            {
                "type": "cluster",
                "id": f"apt-cluster-{key[0]}-{key[1]}",
                "lat": round(sum(float(item["lat"]) for item in members) / len(members), 7),
                "lng": round(sum(float(item["lng"]) for item in members) / len(members), 7),
                "count": len(members),
                "households": total_households,
                "districts": districts[:4],
                "sampleNames": sample_names,
                "pricePreview": cluster_price_preview(members),
            }
        )
    return features


def apartments_response(raw: dict[str, list[str]]) -> dict:
    dataset, source_mode, source_error = load_apartment_dataset()
    meta = dataset.get("meta", {})
    apartments = list(dataset.get("apartments", []))
    bounds = parse_bounds(raw.get("bounds", [""])[0])
    district = raw.get("district", [""])[0].strip()
    search = raw.get("q", [""])[0].strip().lower()
    try:
        zoom = int(float(raw.get("zoom", [11])[0]))
    except (TypeError, ValueError):
        zoom = 11
    cluster = raw.get("cluster", ["true"])[0].lower() != "false"
    try:
        limit = int(raw.get("limit", [5000])[0])
    except (TypeError, ValueError):
        limit = 5000
    limit = max(1, min(limit, 10000))

    filtered = [item for item in apartments if in_bounds(item, bounds)]
    if district:
        filtered = [item for item in filtered if item.get("district") == district]
    if search:
        filtered = [
            item
            for item in filtered
            if search in item.get("name", "").lower()
            or search in item.get("address", "").lower()
            or search in item.get("dong", "").lower()
        ]
    filtered = filtered[:limit]
    features = cluster_apartments(filtered, zoom) if cluster else [apartment_feature(item) for item in filtered]

    return {
        "ok": True,
        "meta": {
            "source": meta.get("source", SOURCE_META),
            "sourceMode": source_mode,
            "sourceError": source_error,
            "complete": bool(meta.get("complete")),
            "totalRecords": int(meta.get("totalRecords") or len(apartments)),
            "availableRecords": int(meta.get("recordsWithCoordinates") or len(apartments)),
            "filteredRecords": len(filtered),
            "returnedFeatures": len(features),
            "clustered": cluster and cluster_step(zoom) > 0,
            "zoom": zoom,
            "boundsApplied": bool(bounds),
            "generatedAt": meta.get("generatedAt", ""),
            "note": meta.get("note", ""),
        },
        "features": features,
        "integrations": apartment_credential_status(),
    }
