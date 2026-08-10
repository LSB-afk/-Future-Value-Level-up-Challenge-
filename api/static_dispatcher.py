#!/usr/bin/env python3
"""Route /api/* URLs to MoveValue response builders without an HTTP server.

Used by the GitHub Pages static build: app/static-api.js runs this module in
Pyodide and converts (status, body) pairs into fetch Response objects.
Routing mirrors movevalue_api.Handler.do_GET.
"""

from __future__ import annotations

import json
from urllib.parse import parse_qs, urlparse

import movevalue_api as api


def _route(path: str, raw: dict[str, list[str]]):
    if path == "/api/health":
        dataset = api.load_dataset()
        return {
            "ok": True,
            "areas": len(dataset["areas"]),
            "source": api.runtime_meta(dataset["meta"]),
            "apartments": api.apartment_health(),
            "integrations": api.integration_status(),
        }
    if path == "/api/agent-status":
        # 정적 빌드는 서버가 없어 API 키를 보관할 수 없다. 항상 규칙 기반으로 답한다.
        return {
            "ok": True,
            "available": False,
            "reason": "정적 데모에는 서버가 없어 Claude API 키를 보관할 수 없습니다. 규칙 기반 엔진으로 답변합니다.",
        }
    if path == "/api/areas":
        return api.decorate_dataset(api.load_dataset())
    if path == "/api/geocode":
        location = api.resolve_location(api.single_value(raw, "query"), api.known_locations())
        return {"ok": True, "location": location, "integrations": api.credential_status()}
    if path == "/api/location-suggestions":
        return api.location_suggestions_response(raw)
    if path == "/api/commute-route":
        return api.commute_route(raw)
    if path == "/api/apartments":
        return api.apartments_response(raw)
    if path == "/api/property-detail":
        return api.property_detail_response(raw)
    if path == "/api/property-agent":
        return api.property_agent_response(raw)
    if path == "/api/recommendations":
        return api.recommendations(api.normalize_query(raw))
    if path == "/api/apartment-recommendations":
        return api.apartment_recommendations(api.normalize_query(raw))
    return None


def handle(url: str) -> tuple[int, str]:
    parsed = urlparse(url)
    try:
        payload = _route(parsed.path, parse_qs(parsed.query))
        if payload is None:
            return 404, json.dumps({"ok": False, "error": f"unknown path: {parsed.path}"}, ensure_ascii=False)
        return 200, json.dumps(payload, ensure_ascii=False)
    except ValueError as exc:
        return 400, json.dumps(
            {"ok": False, "error": str(exc), "integrations": api.integration_status()}, ensure_ascii=False
        )
    except Exception as exc:  # noqa: BLE001 - mirror movevalue_api prototype behaviour
        return 500, json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False)


if __name__ == "__main__":
    from urllib.parse import quote

    status, body = handle("/api/apartments?cluster=false&limit=1")
    assert status == 200, body[:300]
    feature = json.loads(body)["features"][0]
    props = feature.get("properties", feature)
    first = quote(str(props.get("id") or feature.get("id")))
    origin = quote(str(props.get("address") or props.get("representativeAddress") or ""))
    destination = quote("서울특별시 강남구 역삼동")
    checks = [
        "/api/health",
        "/api/areas",
        f"/api/geocode?query={destination}",
        f"/api/location-suggestions?query={destination}&limit=5",
        f"/api/commute-route?origin={origin}&provider=tmap&transportMode=transit&destinationQuery={destination}",
        f"/api/property-detail?id={first}",
        f"/api/property-agent?id={first}",
        f"/api/apartment-recommendations?budget=70&destination={destination}&persona=single",
    ]
    for url in checks:
        status, body = handle(url)
        assert status == 200, (url, status, body[:300])
        json.loads(body)
    assert handle("/api/nope")[0] == 404
    print("static_dispatcher self-check OK")
