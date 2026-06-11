#!/usr/bin/env python3
"""MoveValue API server.

No external runtime dependency is required. The server exposes JSON API routes
and serves the static web prototype from the same origin.
"""

from __future__ import annotations

import argparse
import json
import math
import mimetypes
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from apartment_adapters import apartment_credential_status, apartments_response, load_apartment_dataset
from route_adapters import build_commute_route, credential_status, resolve_location


ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "app"
DATA_PATH = ROOT / "data" / "areas.actual.json"


DESTINATIONS = {
    "gangnam": {"label": "강남 업무지구", "address": "서울 강남구 역삼동", "lat": 37.4979, "lng": 127.0276},
    "yeouido": {"label": "여의도", "address": "서울 영등포구 여의도동", "lat": 37.5219, "lng": 126.9245},
    "seoulStation": {"label": "서울역/도심", "address": "서울 중구 봉래동2가", "lat": 37.5563, "lng": 126.9723},
    "digital": {"label": "구로디지털단지", "address": "서울 구로구 구로동", "lat": 37.4853, "lng": 126.9015},
    "pangyo": {"label": "판교", "address": "경기도 성남시 분당구 삼평동", "lat": 37.3947, "lng": 127.1112},
}
AREA_ADDRESSES = {
    "konkuk": "서울 광진구 화양동",
    "sillim": "서울 관악구 신림동",
    "cheongnyangni": "서울 동대문구 청량리동",
    "wangsimni": "서울 성동구 행당동",
    "guro": "서울 구로구 구로동",
    "gongdeok": "서울 마포구 공덕동",
    "magok": "서울 강서구 마곡동",
    "sangam": "서울 마포구 상암동",
    "gimpoairport": "서울 강서구 공항동",
}

DEFAULT_WEIGHTS = {"commute": 35, "cost": 30, "service": 20, "safety": 15}
PERSONA_BOOST = {
    "single": {"cost": 7, "service": 2},
    "commuter": {"commute": 7, "transit": 3},
    "newlywed": {"safety": 5, "service": 5},
    "senior": {"safety": 7, "service": 4},
}
PERSONA_LABELS = {
    "single": "1인 청년",
    "commuter": "직장인",
    "newlywed": "신혼",
    "senior": "교통약자",
}


@dataclass
class Query:
    budget: float
    destination: str
    persona: str
    weights: dict[str, float]
    limit: int


def clamp(value: float, minimum: float = 0, maximum: float = 100) -> float:
    return max(minimum, min(maximum, value))


def haversine_km(a_lat: float, a_lng: float, b_lat: float, b_lng: float) -> float:
    radius = 6371.0088
    phi1 = math.radians(a_lat)
    phi2 = math.radians(b_lat)
    d_phi = math.radians(b_lat - a_lat)
    d_lambda = math.radians(b_lng - a_lng)
    h = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return radius * 2 * math.atan2(math.sqrt(h), math.sqrt(1 - h))


def estimate_commute_minutes(area: dict, destination: str) -> int:
    explicit = area.get("commuteMinutes", {}).get(destination)
    if explicit:
        return int(explicit)

    dest = DESTINATIONS[destination]
    km = haversine_km(float(area["lat"]), float(area["lng"]), dest["lat"], dest["lng"])
    transfer_penalty = max(2, 10 - float(area.get("transitScore", 70)) / 15)
    return int(round(10 + km * 2.65 + transfer_penalty))


def recommendation_reason(area: dict, minutes: int, query: Query) -> str:
    evidence = area.get("evidence", {})
    soc_counts = evidence.get("socCounts") or area.get("socSummary", {}).get("counts", {})
    safety_counts = evidence.get("safetyEnvCounts") or area.get("safetyEnvSummary", {}).get("counts", {})
    monthly_rent = round(float(area.get("rentMonthly10k") or 0))
    budget_delta = round(float(query.budget) - monthly_rent)
    destination_label = DESTINATIONS[query.destination]["label"]
    persona_label = PERSONA_LABELS.get(query.persona, "사용자")
    budget_text = "예산 내" if budget_delta >= 0 else f"예산 {abs(budget_delta)}만원 초과"
    return (
        f"{destination_label}까지 {minutes}분, 월세 중앙값 {monthly_rent}만원, "
        f"병원 {soc_counts.get('hospital', 0)}개·학교 {soc_counts.get('school', 0)}개·공원 {soc_counts.get('park', 0)}개, "
        f"치안시설 {safety_counts.get('police', 0)}개·CCTV {safety_counts.get('cctv', 0)}대 근거로 "
        f"{persona_label}에게 {budget_text} 생활권입니다."
    )


def normalize_query(raw: dict[str, list[str]]) -> Query:
    def number(name: str, default: float, minimum: float, maximum: float) -> float:
        try:
            value = float(raw.get(name, [default])[0])
        except (TypeError, ValueError):
            value = default
        return clamp(value, minimum, maximum)

    destination = raw.get("destination", ["gangnam"])[0]
    if destination not in DESTINATIONS:
        destination = "gangnam"

    persona = raw.get("persona", ["single"])[0]
    if persona not in PERSONA_BOOST:
        persona = "single"

    weights = {
        "commute": number("commuteWeight", DEFAULT_WEIGHTS["commute"], 0, 100),
        "cost": number("costWeight", DEFAULT_WEIGHTS["cost"], 0, 100),
        "service": number("serviceWeight", DEFAULT_WEIGHTS["service"], 0, 100),
        "safety": number("safetyWeight", DEFAULT_WEIGHTS["safety"], 0, 100),
    }

    try:
        limit = int(raw.get("limit", [8])[0])
    except (TypeError, ValueError):
        limit = 8

    return Query(
        budget=number("budget", 70, 20, 250),
        destination=destination,
        persona=persona,
        weights=weights,
        limit=max(1, min(limit, 50)),
    )


def load_dataset() -> dict:
    with DATA_PATH.open(encoding="utf-8") as file:
        return json.load(file)


def destination_addresses() -> dict[str, str]:
    return {key: value["address"] for key, value in DESTINATIONS.items()}


def decorate_dataset(dataset: dict) -> dict:
    decorated = dict(dataset)
    decorated["meta"] = {
        **dataset.get("meta", {}),
        "destinationAddresses": destination_addresses(),
        "integrations": credential_status(),
    }
    decorated["areas"] = [
        {
            **area,
            "representativeAddress": AREA_ADDRESSES.get(area["id"], f"{area.get('district', '')} {area.get('station', '')}".strip()),
        }
        for area in dataset.get("areas", [])
    ]
    return decorated


def known_locations() -> dict[str, dict]:
    dataset = load_dataset()
    locations = {
        key: {"label": value["label"], "address": value["address"], "lat": value["lat"], "lng": value["lng"]}
        for key, value in DESTINATIONS.items()
    }
    for key, value in DESTINATIONS.items():
        locations[value["label"]] = locations[key]
        locations[value["address"]] = locations[key]
    for area in dataset.get("areas", []):
        address = AREA_ADDRESSES.get(area["id"], "")
        location = {
            "label": area["name"],
            "address": address,
            "name": area["name"],
            "station": area.get("station", ""),
            "lat": area["lat"],
            "lng": area["lng"],
        }
        locations[area["id"]] = location
        locations[area["name"]] = location
        if address:
            locations[address] = location
        if area.get("station"):
            locations[area["station"]] = location
    return locations


def score_area(area: dict, query: Query) -> dict:
    minutes = estimate_commute_minutes(area, query.destination)
    monthly_rent = float(area.get("rentMonthly10k") or 0)
    commute_score = clamp(105 - minutes * 1.18)
    over_budget = max(0, monthly_rent - query.budget)
    under_budget = max(0, query.budget - monthly_rent)
    cost_score = clamp(82 + under_budget * 0.55 - over_budget * 1.9)
    safety_env_score = round(float(area.get("safetyScore", 70)) * 0.58 + float(area.get("carbonScore", 70)) * 0.42)
    boost = PERSONA_BOOST[query.persona]

    adjusted = {
        "commute": clamp(commute_score + boost.get("commute", 0) + boost.get("transit", 0)),
        "cost": clamp(cost_score + boost.get("cost", 0)),
        "service": clamp(float(area.get("serviceScore", 70)) + boost.get("service", 0)),
        "safety": clamp(safety_env_score + boost.get("safety", 0)),
    }

    total_weight = sum(query.weights.values()) or sum(DEFAULT_WEIGHTS.values())
    weighted = sum(adjusted[key] * query.weights[key] for key in query.weights)
    persona_match = 3 if query.persona in area.get("recommendedFor", []) else 0
    data_confidence = (float(area.get("dataReadiness", 80)) - 80) * 0.12
    total = clamp(weighted / total_weight + persona_match + data_confidence)

    result = dict(area)
    result.update(
        {
            "total": round(total),
            "minutes": minutes,
            "adjusted": {key: round(value) for key, value in adjusted.items()},
            "destination": query.destination,
            "destinationLabel": DESTINATIONS[query.destination]["label"],
            "destinationAddress": DESTINATIONS[query.destination]["address"],
            "representativeAddress": AREA_ADDRESSES.get(area["id"], f"{area.get('district', '')} {area.get('station', '')}".strip()),
            "reasonText": recommendation_reason(area, minutes, query),
        }
    )
    return result


def recommendations(query: Query) -> dict:
    dataset = load_dataset()
    scored = [score_area(area, query) for area in dataset["areas"]]
    scored.sort(key=lambda area: (-area["total"], area.get("rentMonthly10k", 999), area["name"]))
    return {
        "meta": {
            **dataset.get("meta", {}),
            "destination": query.destination,
            "destinationLabel": DESTINATIONS[query.destination]["label"],
            "destinationAddress": DESTINATIONS[query.destination]["address"],
            "destinationAddresses": destination_addresses(),
            "persona": query.persona,
            "budget": query.budget,
            "weights": query.weights,
            "returned": min(query.limit, len(scored)),
            "totalCandidates": len(scored),
            "integrations": credential_status(),
        },
        "results": scored[: query.limit],
    }


def single_value(raw: dict[str, list[str]], name: str, default: str = "") -> str:
    return raw.get(name, [default])[0].strip()


def resolve_route_location(raw: dict[str, list[str]], prefix: str, fallback_key: str = "") -> dict:
    lat = single_value(raw, f"{prefix}Lat")
    lng = single_value(raw, f"{prefix}Lng")
    if lat and lng:
        return resolve_location(f"{lat},{lng}", known_locations())

    query = single_value(raw, prefix)
    if query:
        return resolve_location(query, known_locations())

    if fallback_key:
        return resolve_location(fallback_key, known_locations())

    raise ValueError(f"{prefix} 위치 값이 필요합니다.")


def commute_route(raw: dict[str, list[str]]) -> dict:
    origin = resolve_route_location(raw, "origin")
    destination_query = single_value(raw, "destinationQuery")
    destination_key = single_value(raw, "destination", "gangnam")
    destination = resolve_route_location(raw, "destination", destination_query or destination_key)
    provider = single_value(raw, "provider", "auto")
    route = build_commute_route(origin, destination, provider)
    route["credentialStatus"] = credential_status()
    return route


def integration_status() -> dict:
    return {**credential_status(), **apartment_credential_status()}


def apartment_health() -> dict:
    dataset, source_mode, source_error = load_apartment_dataset()
    meta = dataset.get("meta", {})
    return {
        "sourceMode": source_mode,
        "sourceError": source_error,
        "complete": bool(meta.get("complete")),
        "totalRecords": int(meta.get("totalRecords") or len(dataset.get("apartments", []))),
        "availableRecords": int(meta.get("recordsWithCoordinates") or len(dataset.get("apartments", []))),
        "source": meta.get("source", {}),
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "MoveValueAPI/0.1"

    def log_message(self, fmt: str, *args) -> None:
        if not getattr(self.server, "quiet", False):
            super().log_message(fmt, *args)

    def send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_HEAD(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path.startswith("/api/"):
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            return
        self.serve_static(parsed.path, head_only=True)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path

        try:
            if path == "/api/health":
                dataset = load_dataset()
                self.send_json(
                    HTTPStatus.OK,
                    {
                        "ok": True,
                        "areas": len(dataset["areas"]),
                        "source": dataset["meta"],
                        "apartments": apartment_health(),
                        "integrations": integration_status(),
                    },
                )
                return
            if path == "/api/areas":
                self.send_json(HTTPStatus.OK, decorate_dataset(load_dataset()))
                return
            if path == "/api/geocode":
                raw = parse_qs(parsed.query)
                location = resolve_location(single_value(raw, "query"), known_locations())
                self.send_json(HTTPStatus.OK, {"ok": True, "location": location, "integrations": credential_status()})
                return
            if path == "/api/commute-route":
                self.send_json(HTTPStatus.OK, commute_route(parse_qs(parsed.query)))
                return
            if path == "/api/apartments":
                self.send_json(HTTPStatus.OK, apartments_response(parse_qs(parsed.query)))
                return
            if path == "/api/recommendations":
                query = normalize_query(parse_qs(parsed.query))
                self.send_json(HTTPStatus.OK, recommendations(query))
                return
            self.serve_static(path)
        except ValueError as exc:
            self.send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": str(exc), "integrations": integration_status()})
        except Exception as exc:  # noqa: BLE001 - API should return JSON error in prototype mode.
            self.send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"ok": False, "error": str(exc)})

    def serve_static(self, path: str, head_only: bool = False) -> None:
        if path in {"", "/", "/app", "/app/"}:
            target = APP_DIR / "index.html"
        elif path.startswith("/app/"):
            target = APP_DIR / unquote(path.removeprefix("/app/"))
        else:
            target = APP_DIR / unquote(path.lstrip("/"))

        target = target.resolve()
        if not (target == APP_DIR.resolve() or APP_DIR.resolve() in target.parents):
            self.send_error(HTTPStatus.FORBIDDEN)
            return
        if not target.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        body = target.read_bytes()
        content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        if content_type.startswith("text/") or target.suffix in {".js", ".json"}:
            content_type += "; charset=utf-8"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if not head_only:
            self.wfile.write(body)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run MoveValue API and web prototype.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5173)
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), Handler)
    server.quiet = args.quiet
    print(f"MoveValue API listening at http://{args.host}:{args.port}/")
    server.serve_forever()


if __name__ == "__main__":
    main()
