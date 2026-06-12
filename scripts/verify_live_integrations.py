#!/usr/bin/env python3
"""Verify MoveValue live integrations without printing secret values.

The script is intentionally safe to run without credentials. It reports which
adapters are configured, which calls reached a live API, and where the service
fell back to deterministic prototype data.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
API_DIR = ROOT / "api"
sys.path.insert(0, str(API_DIR))

from apartment_adapters import load_apartment_dataset  # noqa: E402
from movevalue_api import DESTINATIONS, build_commute_route, integration_status, known_locations  # noqa: E402
from property_model import build_property_detail  # noqa: E402
from route_adapters import geocode_with_kakao, resolve_location  # noqa: E402


DEFAULT_ORIGIN = "서울특별시 광진구 아차산로 272"
DEFAULT_DESTINATION = "서울특별시 강남구 테헤란로 152"


def compact_error(exc: Exception) -> str:
    return str(exc).replace("\n", " ")[:260]


def route_check(origin_query: str, destination_query: str, provider: str) -> dict[str, Any]:
    locations = known_locations()
    errors: list[str] = []

    try:
        origin = resolve_location(origin_query, locations)
    except Exception as exc:  # noqa: BLE001 - verification must continue through partial setup.
        errors.append(f"origin: {compact_error(exc)}")
        origin = resolve_location("서울 광진구 화양동", locations)

    try:
        destination = resolve_location(destination_query, locations)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"destination: {compact_error(exc)}")
        destination = resolve_location("gangnam", locations)

    route = build_commute_route(origin, destination, provider)
    return {
        "ok": bool(route.get("ok")),
        "provider": route.get("provider"),
        "mode": route.get("mode"),
        "originSource": origin.get("source"),
        "destinationSource": destination.get("source"),
        "totalMinutes": route.get("summary", {}).get("totalMinutes"),
        "transferCount": route.get("summary", {}).get("transferCount"),
        "fare": route.get("summary", {}).get("fare"),
        "steps": len(route.get("steps") or []),
        "notice": route.get("notice", ""),
        "adapterErrors": route.get("errors", []),
        "resolutionErrors": errors,
    }


def kakao_check(query: str) -> dict[str, Any]:
    try:
        result = geocode_with_kakao(query)
    except Exception as exc:  # noqa: BLE001
        return {"mode": "error", "ok": False, "error": compact_error(exc)}
    if not result:
        return {"mode": "not_configured_or_no_result", "ok": False}
    return {
        "mode": "live_api",
        "ok": True,
        "source": result.get("source"),
        "label": result.get("label"),
        "lat": round(float(result.get("lat", 0)), 6),
        "lng": round(float(result.get("lng", 0)), 6),
    }


def apartment_check() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    try:
        dataset, source_mode, source_error = load_apartment_dataset()
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "sourceMode": "error", "error": compact_error(exc)}, []

    apartments = list(dataset.get("apartments", []))
    meta = dataset.get("meta", {})
    return (
        {
            "ok": True,
            "sourceMode": source_mode,
            "sourceError": source_error,
            "complete": bool(meta.get("complete")),
            "totalRecords": int(meta.get("totalRecords") or len(apartments)),
            "availableRecords": int(meta.get("recordsWithCoordinates") or len(apartments)),
            "sampleNames": [item.get("name") for item in apartments[:3]],
        },
        apartments,
    )


def price_check(apartments: list[dict[str, Any]]) -> dict[str, Any]:
    if not apartments:
        return {"ok": False, "mode": "no_apartment_data"}
    try:
        detail = build_property_detail(apartments[0])
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "mode": "error", "error": compact_error(exc)}

    price = detail.get("price", {})
    live_status = price.get("liveStatus", {})
    return {
        "ok": True,
        "property": {"id": detail.get("id"), "name": detail.get("name"), "district": detail.get("district")},
        "sourceMode": price.get("sourceMode"),
        "sourceLabel": price.get("sourceLabel"),
        "molitTrade": live_status.get("molitTrade", {}),
        "molitRent": live_status.get("molitRent", {}),
        "publicPrice": live_status.get("publicPrice", {}),
        "jeonseRatio": price.get("jeonseRatio"),
        "depositOfficialRatio": price.get("depositOfficialRatio"),
    }


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    credentials = integration_status()
    apartments_report, apartments = apartment_check()
    return {
        "ok": True,
        "credentialsConfigured": credentials,
        "kakaoGeocode": kakao_check(args.destination_query),
        "commuteRoute": route_check(args.origin_query, args.destination_query, args.provider),
        "apartments": apartments_report,
        "realEstatePrice": price_check(apartments),
        "destinationCatalog": {key: value["address"] for key, value in DESTINATIONS.items()},
        "notes": [
            "환경변수 설정 여부만 표시하며 API 키 값은 출력하지 않습니다.",
            "mode=live_api이면 실제 외부 API 응답을 사용한 것입니다.",
            "mode=estimated_fallback 또는 sourceMode=snapshot이면 키 미설정/호출 실패 폴백입니다.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify MoveValue live API integrations.")
    parser.add_argument("--origin-query", default=DEFAULT_ORIGIN)
    parser.add_argument("--destination-query", default=DEFAULT_DESTINATION)
    parser.add_argument("--provider", choices=("auto", "odsay", "tmap"), default="auto")
    parser.add_argument("--json", action="store_true", help="Print raw JSON only.")
    args = parser.parse_args()

    report = build_report(args)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return

    print("MoveValue live integration verification")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
