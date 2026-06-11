#!/usr/bin/env python3
"""Build a lightweight Seoul apartment complex snapshot for the map layer."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from json import JSONDecodeError
from urllib.error import URLError
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = ROOT / "data" / "apartments.seoul.snapshot.json"
API_NAME = "OpenAptInfo"
API_URL = "http://openapi.seoul.go.kr:8088/{key}/json/OpenAptInfo/{start}/{end}/"
API_KEY_ENVS = ("SEOUL_OPEN_API_KEY", "SEOUL_API_KEY", "MOVEVALUE_SEOUL_OPEN_API_KEY")


def api_key() -> str:
    for name in API_KEY_ENVS:
        value = os.getenv(name, "").strip()
        if value:
            return value
    raise SystemExit(
        "서울 열린데이터광장 API 키가 필요합니다. "
        "예: SEOUL_OPEN_API_KEY=발급키 python3 scripts/build_apartment_snapshot.py"
    )


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
            body = response.read().decode("utf-8")
            return json.loads(body)
    except URLError as exc:
        raise SystemExit(f"서울 공동주택 API 호출 실패: {exc}") from exc
    except JSONDecodeError as exc:
        preview = body[:180].replace("\n", " ")
        raise SystemExit(f"서울 공동주택 API가 JSON이 아닌 응답을 반환했습니다: {preview}") from exc


def fetch_all(key: str) -> tuple[list[dict], int, bool]:
    page_size = 5 if key == "sample" else 1000
    first = fetch_page(key, 1, 1)
    root = first.get(API_NAME, {})
    total = int(root.get("list_total_count") or 0)
    if total <= 0:
        raise SystemExit(f"서울 공동주택 API 응답에 총 건수가 없습니다: {first}")

    apartments: list[dict] = []
    if key == "sample":
        payload = fetch_page(key, 1, 5)
        rows = payload.get(API_NAME, {}).get("row", [])
        apartments.extend(item for row in rows if (item := normalize_row(row)))
        return apartments, total, False

    for start in range(1, total + 1, page_size):
        end = min(start + page_size - 1, total)
        payload = fetch_page(key, start, end)
        rows = payload.get(API_NAME, {}).get("row", [])
        apartments.extend(item for row in rows if (item := normalize_row(row)))
    return apartments, total, True


def main() -> None:
    key = api_key()
    apartments, total, complete = fetch_all(key)
    apartments.sort(key=lambda item: (item["district"], item["dong"], item["name"]))
    payload = {
        "meta": {
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "source": {
                "name": "서울시 공동주택 아파트 정보",
                "url": "https://data.seoul.go.kr/dataList/OA-15818/S/1/datasetView.do",
                "apiName": API_NAME,
                "endpoint": "http://openapi.seoul.go.kr:8088/{KEY}/json/OpenAptInfo/{START_INDEX}/{END_INDEX}/",
            },
            "totalRecords": total,
            "recordsWithCoordinates": len(apartments),
            "complete": complete,
            "coordinateFields": {"lat": "YCRD", "lng": "XCRD"},
            "note": "지도 표시를 위해 단지명, 주소, 좌표, 세대수, 동수, 사용승인일, 주차대수만 정규화한 파생 스냅샷입니다. sample 키로 생성한 경우 전체가 아니라 5건 미리보기입니다.",
        },
        "apartments": apartments,
    }
    OUTPUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(apartments):,}/{total:,} apartments to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
