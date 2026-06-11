#!/usr/bin/env python3
"""Build a compact MoveValue dataset from real public-data snapshots."""

from __future__ import annotations

import csv
import json
import statistics
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from movevalue_adapters import adapter_source_meta, build_commute_minutes, build_safety_env_metrics, build_soc_metrics


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
OUT = ROOT / "data" / "areas.actual.json"
SEOUL_RENT_ZIP = RAW_DIR / "seoul_rent_2025.zip"
SEOUL_RENT_URL = "https://datafile.seoul.go.kr/bigfile/iot/inf/nio_download.do?&useCache=false"
MAX_RENT_EXAMPLES_PER_BUCKET = 160


AREA_DEFINITIONS = [
    {
        "id": "konkuk",
        "name": "건대입구",
        "district": "서울 광진구",
        "rentDistrict": "광진구",
        "rentDongs": ["화양동", "자양동"],
        "lat": 37.5405,
        "lng": 127.0692,
        "station": "건대입구역",
        "lineCount": 2,
        "commuteMinutes": {"gangnam": 24, "yeouido": 44, "seoulStation": 28, "digital": 54, "pangyo": 50},
        "recommendedFor": ["single", "commuter"],
        "insight": "환승 접근성과 생활편의가 균형적이며 청년층 체감 편익이 높다.",
    },
    {
        "id": "sillim",
        "name": "신림",
        "district": "서울 관악구",
        "rentDistrict": "관악구",
        "rentDongs": ["신림동"],
        "lat": 37.4842,
        "lng": 126.9297,
        "station": "신림역",
        "lineCount": 2,
        "commuteMinutes": {"gangnam": 29, "yeouido": 24, "seoulStation": 33, "digital": 17, "pangyo": 56},
        "recommendedFor": ["single", "commuter"],
        "insight": "예산 효율이 높고 주요 업무지구 통근 수요에 적합하다.",
    },
    {
        "id": "cheongnyangni",
        "name": "청량리",
        "district": "서울 동대문구",
        "rentDistrict": "동대문구",
        "rentDongs": ["청량리동", "전농동", "용두동"],
        "lat": 37.5802,
        "lng": 127.045,
        "station": "청량리역",
        "lineCount": 4,
        "commuteMinutes": {"gangnam": 35, "yeouido": 46, "seoulStation": 21, "digital": 58, "pangyo": 61},
        "recommendedFor": ["single", "senior"],
        "insight": "광역철도 환승과 동북권 접근성이 좋아 장거리 이동 수요에 유리하다.",
    },
    {
        "id": "wangsimni",
        "name": "왕십리",
        "district": "서울 성동구",
        "rentDistrict": "성동구",
        "rentDongs": ["행당동", "도선동", "하왕십리동", "상왕십리동"],
        "lat": 37.5615,
        "lng": 127.0378,
        "station": "왕십리역",
        "lineCount": 4,
        "commuteMinutes": {"gangnam": 27, "yeouido": 36, "seoulStation": 19, "digital": 48, "pangyo": 52},
        "recommendedFor": ["commuter", "newlywed"],
        "insight": "환승 접근성이 높고 도심·업무지구 양방향 통근 균형이 좋다.",
    },
    {
        "id": "guro",
        "name": "구로디지털단지",
        "district": "서울 구로구",
        "rentDistrict": "구로구",
        "rentDongs": ["구로동"],
        "lat": 37.4853,
        "lng": 126.9015,
        "station": "구로디지털단지역",
        "lineCount": 1,
        "commuteMinutes": {"gangnam": 37, "yeouido": 20, "seoulStation": 35, "digital": 6, "pangyo": 63},
        "recommendedFor": ["single", "commuter"],
        "insight": "IT 직장인 통근 효율이 높고 월세 부담 대비 업무 접근성이 좋다.",
    },
    {
        "id": "gongdeok",
        "name": "공덕",
        "district": "서울 마포구",
        "rentDistrict": "마포구",
        "rentDongs": ["공덕동", "도화동", "염리동"],
        "lat": 37.5445,
        "lng": 126.9511,
        "station": "공덕역",
        "lineCount": 4,
        "commuteMinutes": {"gangnam": 38, "yeouido": 15, "seoulStation": 11, "digital": 32, "pangyo": 66},
        "recommendedFor": ["commuter", "public"],
        "insight": "여의도·서울역 접근이 뛰어나지만 월 주거비 부담이 높은 편이다.",
    },
    {
        "id": "magok",
        "name": "마곡나루",
        "district": "서울 강서구",
        "rentDistrict": "강서구",
        "rentDongs": ["마곡동"],
        "lat": 37.5673,
        "lng": 126.8272,
        "station": "마곡나루역",
        "lineCount": 2,
        "commuteMinutes": {"gangnam": 55, "yeouido": 31, "seoulStation": 39, "digital": 34, "pangyo": 80},
        "recommendedFor": ["newlywed", "public"],
        "insight": "업무지구·공항 접근성이 강하고 신혼·가족형 생활 인프라가 안정적이다.",
    },
    {
        "id": "sangam",
        "name": "상암DMC",
        "district": "서울 마포구",
        "rentDistrict": "마포구",
        "rentDongs": ["상암동"],
        "lat": 37.577,
        "lng": 126.8897,
        "station": "디지털미디어시티역",
        "lineCount": 3,
        "commuteMinutes": {"gangnam": 53, "yeouido": 29, "seoulStation": 26, "digital": 45, "pangyo": 76},
        "recommendedFor": ["commuter", "public"],
        "insight": "미디어·콘텐츠 업무지구와 공항철도 접근성이 강점이다.",
    },
    {
        "id": "gimpoairport",
        "name": "김포공항",
        "district": "서울 강서구",
        "rentDistrict": "강서구",
        "rentDongs": ["공항동", "방화동"],
        "lat": 37.5625,
        "lng": 126.8019,
        "station": "김포공항역",
        "lineCount": 5,
        "commuteMinutes": {"gangnam": 62, "yeouido": 33, "seoulStation": 36, "digital": 38, "pangyo": 88},
        "recommendedFor": ["public", "commuter"],
        "insight": "광역·공항 접근성이 높아 출장·다거점 이동 수요에 강하다.",
    },
]


def download_seoul_rent_zip() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    if SEOUL_RENT_ZIP.exists() and SEOUL_RENT_ZIP.stat().st_size > 1_000_000:
        return

    payload = urllib.parse.urlencode({"infId": "OA-21276", "seq": "40", "infSeq": "3"}).encode()
    request = urllib.request.Request(SEOUL_RENT_URL, data=payload, method="POST")
    with urllib.request.urlopen(request, timeout=120) as response:
        SEOUL_RENT_ZIP.write_bytes(response.read())


def read_rent_rows():
    with zipfile.ZipFile(SEOUL_RENT_ZIP) as archive:
        names = archive.namelist()
        if not names:
            raise RuntimeError("서울 전월세 ZIP 안에 CSV 파일이 없습니다.")
        with archive.open(names[0]) as raw:
            text = (line.decode("cp949") for line in raw)
            reader = csv.DictReader(text)
            for row in reader:
                yield row


def to_float(value: str) -> float | None:
    try:
        return float(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def median(values: list[float]) -> float:
    if not values:
        return 0
    return round(statistics.median(values), 1)


def contract_month(value: str) -> str:
    text = str(value or "").strip()
    if len(text) >= 6 and text[:6].isdigit():
        return f"{text[:4]}.{text[4:6]}"
    return text


def compact_rent_example(row: dict, *, dong: str, area: float, deposit: float, monthly: float) -> dict:
    return {
        "contractMonth": contract_month(row.get("계약일", "")),
        "dong": dong,
        "rentType": row.get("전월세구분") or "",
        "areaM2": round(area, 1),
        "deposit10k": round(deposit),
        "monthlyRent10k": round(monthly),
        "buildingUse": row.get("건물용도") or "",
        "floor": row.get("층") or "",
    }


def build_rent_index() -> dict:
    index: dict[tuple[str, str], dict[str, list[float] | list[dict] | int]] = {}
    district_index: dict[str, dict[str, list[float] | list[dict] | int]] = {}

    for row in read_rent_rows():
        district = row.get("자치구명", "")
        dong = row.get("법정동명", "")
        rent_type = row.get("전월세구분")
        area = to_float(row.get("임대면적"))
        deposit = to_float(row.get("보증금(만원)"))
        monthly = to_float(row.get("임대료(만원)"))
        if not district or not dong or area is None or deposit is None or monthly is None:
            continue
        if area < 15 or area > 85:
            continue

        example = compact_rent_example(row, dong=dong, area=area, deposit=deposit, monthly=monthly)
        for target in (
            index.setdefault((district, dong), {"monthly": [], "deposit": [], "jeonse": [], "examples": [], "count": 0}),
            district_index.setdefault(district, {"monthly": [], "deposit": [], "jeonse": [], "examples": [], "count": 0}),
        ):
            target["count"] = int(target["count"]) + 1
            if rent_type == "월세" and monthly > 0:
                target["monthly"].append(monthly)
                target["deposit"].append(deposit)
            elif rent_type == "전세" and deposit > 0:
                target["jeonse"].append(deposit)
            if len(target["examples"]) < MAX_RENT_EXAMPLES_PER_BUCKET:
                target["examples"].append(example)

    return {"dong": index, "district": district_index}


def select_rent_examples(rows: list[dict], rent_monthly: float, jeonse: float, limit: int = 4) -> list[dict]:
    examples = [example for data in rows for example in data.get("examples", [])]
    if not examples:
        return []

    monthly_examples = [
        item for item in examples if item.get("rentType") == "월세" and float(item.get("monthlyRent10k") or 0) > 0
    ]
    jeonse_examples = [
        item for item in examples if item.get("rentType") == "전세" and float(item.get("deposit10k") or 0) > 0
    ]

    monthly_examples.sort(key=lambda item: (abs(float(item["monthlyRent10k"]) - rent_monthly), item.get("contractMonth", "")))
    jeonse_examples.sort(key=lambda item: (abs(float(item["deposit10k"]) - jeonse), item.get("contractMonth", "")))

    selected = monthly_examples[:3] + jeonse_examples[:1]
    if len(selected) < limit:
        fallback = sorted(
            examples,
            key=lambda item: (
                0 if item.get("rentType") == "월세" else 1,
                abs(float(item.get("monthlyRent10k") or 0) - rent_monthly),
                item.get("contractMonth", ""),
            ),
        )
        selected.extend(fallback)

    unique = []
    seen = set()
    for item in selected:
        key = (
            item.get("contractMonth"),
            item.get("dong"),
            item.get("rentType"),
            item.get("areaM2"),
            item.get("deposit10k"),
            item.get("monthlyRent10k"),
        )
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
        if len(unique) >= limit:
            break
    return unique


def build_areas() -> list[dict]:
    download_seoul_rent_zip()
    rent_index = build_rent_index()

    areas = []
    for area_def in AREA_DEFINITIONS:
        rows = []
        matched_dongs = []
        for dong in area_def["rentDongs"]:
            data = rent_index["dong"].get((area_def["rentDistrict"], dong))
            if data:
                rows.append(data)
                matched_dongs.append(dong)
        fallback_used = False
        if not rows:
            district_data = rent_index["district"].get(area_def["rentDistrict"])
            if district_data:
                rows.append(district_data)
                fallback_used = True

        monthly_pool = [value for data in rows for value in data["monthly"]]
        deposit_pool = [value for data in rows for value in data["deposit"]]
        jeonse_pool = [value for data in rows for value in data["jeonse"]]
        matched_records = sum(int(data["count"]) for data in rows)

        rent_monthly = median(monthly_pool)
        deposit = median(deposit_pool)
        jeonse = median(jeonse_pool)
        transit_score = min(98, 68 + area_def["lineCount"] * 6)
        commute_minutes, commute_evidence = build_commute_minutes(area_def)
        soc_metrics = build_soc_metrics(area_def)
        service_score = soc_metrics["score"]
        safety_env_metrics = build_safety_env_metrics(area_def, soc_metrics)
        safety_score = safety_env_metrics["safetyScore"]
        carbon_score = safety_env_metrics["environmentScore"]
        rent_examples = select_rent_examples(rows, rent_monthly, jeonse)
        data_readiness = 94 if not fallback_used else 88
        if commute_evidence["commuteProvider"] == "odsay" and not commute_evidence["fallbackUsed"]:
            data_readiness += 2
        if soc_metrics["facilityRecords"] >= 3:
            data_readiness += 1
        if safety_env_metrics["facilityRecords"] >= 2:
            data_readiness += 1

        areas.append(
            {
                "id": area_def["id"],
                "name": area_def["name"],
                "district": area_def["district"],
                "lat": area_def["lat"],
                "lng": area_def["lng"],
                "station": area_def["station"],
                "rentMonthly10k": rent_monthly,
                "deposit10k": deposit,
                "jeonse10k": jeonse,
                "transitScore": transit_score,
                "serviceScore": min(100, service_score),
                "socScore": min(100, service_score),
                "safetyScore": min(100, safety_score),
                "carbonScore": min(100, carbon_score),
                "dataReadiness": min(100, data_readiness),
                "commuteMinutes": commute_minutes,
                "socSummary": {
                    "radiusMeters": soc_metrics["radiusMeters"],
                    "counts": soc_metrics["counts"],
                    "nearestFacilities": soc_metrics["nearestFacilities"],
                    "facilityRecords": soc_metrics["facilityRecords"],
                    "sampleFacilities": soc_metrics["sampleFacilities"],
                },
                "safetyEnvSummary": {
                    "radiusMeters": safety_env_metrics["radiusMeters"],
                    "counts": safety_env_metrics["counts"],
                    "nearestFacilities": safety_env_metrics["nearestFacilities"],
                    "airStation": safety_env_metrics["airStation"],
                    "airQualityScore": safety_env_metrics["airQualityScore"],
                    "greenScore": safety_env_metrics["greenScore"],
                    "nightSafetyIndex": safety_env_metrics["nightSafetyIndex"],
                    "facilityRecords": safety_env_metrics["facilityRecords"],
                    "sampleFacilities": safety_env_metrics["sampleFacilities"],
                },
                "rentExamples": rent_examples,
                "recommendedFor": area_def["recommendedFor"],
                "insight": area_def["insight"],
                "evidence": {
                    "rentSource": "서울시 부동산 전월세가 정보 2025 파일",
                    "rentDistrict": area_def["rentDistrict"],
                    "rentDongs": matched_dongs or area_def["rentDongs"],
                    "matchedRentRecords": matched_records,
                    "rentExampleCount": len(rent_examples),
                    "rentExamplePrivacy": "공개 전월세 파일에서 상세 지번·건물명은 제외하고 계약월·법정동·면적·보증금·월세·건물용도만 표시",
                    "fallbackUsed": fallback_used,
                    "rentFallbackUsed": fallback_used,
                    "stationCoordinateSource": "서울시 역사마스터 정보 및 공개 좌표 검증",
                    "commuteSource": commute_evidence["commuteSource"],
                    "commuteMode": commute_evidence["commuteMode"],
                    "commuteProvider": commute_evidence["commuteProvider"],
                    "commuteFallbackUsed": commute_evidence["fallbackUsed"],
                    "commuteFallbackDestinations": commute_evidence["fallbackDestinations"],
                    "commuteApiKeyEnv": commute_evidence["apiKeyEnv"],
                    "commuteErrors": commute_evidence.get("errors", {}),
                    "socSource": soc_metrics["source"],
                    "socMode": soc_metrics["mode"],
                    "socRadiusMeters": soc_metrics["radiusMeters"],
                    "socCounts": soc_metrics["counts"],
                    "socNearestFacilities": soc_metrics["nearestFacilities"],
                    "socFacilityRecords": soc_metrics["facilityRecords"],
                    "safetyEnvSource": safety_env_metrics["source"],
                    "safetyEnvMode": safety_env_metrics["mode"],
                    "safetyEnvRadiusMeters": safety_env_metrics["radiusMeters"],
                    "safetyEnvCounts": safety_env_metrics["counts"],
                    "safetyEnvNearestFacilities": safety_env_metrics["nearestFacilities"],
                    "safetyEnvFacilityRecords": safety_env_metrics["facilityRecords"],
                    "airStation": safety_env_metrics["airStation"],
                },
            }
        )
    return areas


def main() -> None:
    areas = build_areas()
    source_meta = adapter_source_meta()
    payload = {
        "meta": {
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "scope": "서울 주요 환승·업무 생활권 MVP",
            "housingSource": {
                "name": "서울시 부동산 전월세가 정보",
                "year": 2025,
                "url": "https://data.seoul.go.kr/dataList/OA-21276/S/1/datasetView.do",
            },
            "stationSource": {
                "name": "서울시 역사마스터 정보",
                "url": "https://data.seoul.go.kr/dataList/OA-21232/S/1/datasetView.do",
            },
            **source_meta,
            "note": "주거비는 2025년 서울시 전월세 전체 파일에서 15~85㎡ 거래를 생활권 법정동 기준으로 집계한 중앙값입니다. 통근시간은 대중교통 경로 API 어댑터가 우선이며, API 키가 없으면 MVP 테이블로 폴백합니다. 생활 SOC는 병원·학교·공원 좌표 반경 집계 기반입니다. 안전·환경은 치안시설·CCTV 집계점·도시대기 측정망·공원 접근성 스냅샷을 결합합니다.",
        },
        "areas": areas,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUT} ({len(areas)} areas)")


if __name__ == "__main__":
    main()
