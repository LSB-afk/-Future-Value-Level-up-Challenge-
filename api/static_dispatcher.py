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
    if path == "/api/property-feedback":
        return {"ok": True, "items": api.list_feedback(api.single_value(raw, "key"))}
    return None


def _route_post(path: str, body: str | None):
    """Mirrors movevalue_api.Handler.do_POST for the JSON endpoints the report page calls."""
    if path == "/api/property-feedback":
        # 정적 데모(GitHub Pages)에는 저장할 서버가 없다. 404 대신 이유를 알려 준다(재점검 Astra-20).
        raise ValueError("정적 데모에서는 제보를 저장하지 않습니다. 서버 버전(로컬 실행)에서 이용해 주세요.")
    if path not in {"/api/jeonse-verdict", "/api/deposit-priority"}:
        return None
    payload = json.loads(body or "")
    if not isinstance(payload, dict):
        raise ValueError("JSON 객체가 필요합니다.")
    if path == "/api/deposit-priority":
        return api.deposit_priority_response(payload)
    payload = api.verify_trade_price(api.validate_jeonse_input(payload))
    key = str(payload.get("key") or "")
    payload["feedbackCount"] = len(api.list_feedback(key)) if key else 0
    result = api.evaluate_jeonse(payload)
    if payload.get("sourceDowngraded"):
        result["sourceDowngraded"] = payload["sourceDowngraded"]
    return result


def handle(url: str, method: str = "GET", body: str | None = None) -> tuple[int, str]:
    """(status, JSON body). POST needs the fetch shim to pass init.method and init.body."""
    parsed = urlparse(url)
    try:
        if str(method or "GET").upper() == "POST":
            payload = _route_post(parsed.path, body)
        else:
            payload = _route(parsed.path, parse_qs(parsed.query))
        if payload is None:
            return 404, json.dumps({"ok": False, "error": f"unknown path: {parsed.path}"}, ensure_ascii=False)
        return 200, json.dumps(payload, ensure_ascii=False)
    except ValueError as exc:  # includes json.JSONDecodeError
        return 400, json.dumps(
            {"ok": False, "error": str(exc), "integrations": api.integration_status()}, ensure_ascii=False
        )
    except (TypeError, OverflowError, AttributeError) as exc:
        if str(method or "GET").upper() != "POST":
            return 500, json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False)
        # 서버(do_POST)와 같이, 검증이 놓친 이상한 본문 형식은 400으로 알린다.
        return 400, json.dumps({"ok": False, "error": f"요청 형식이 올바르지 않습니다: {type(exc).__name__}"}, ensure_ascii=False)
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
    assert handle("/api/property-feedback?key=apt:none")[0] == 200
    assert handle("/api/jeonse-verdict", "POST", "not json")[0] == 400
    assert handle("/api/jeonse-verdict", "POST", "[]")[0] == 400
    assert handle("/api/nope", "POST", "{}")[0] == 404
    verdict_body = json.dumps({
        "property": {"housingType": "apartment", "address": "서울 예시구"},
        "deposit10k": 42000,
        "price": {"basis": "market", "value10k": 90000, "source": "input"},
    })
    status, body = handle("/api/jeonse-verdict", "POST", verdict_body)
    assert status == 200 and json.loads(body).get("grade"), (status, body[:300])
    status, body = handle("/api/deposit-priority", "POST", json.dumps({"deposit10k": 30000, "address": "서울특별시 성동구"}))
    assert status == 200, (status, body[:300])
    print("static_dispatcher self-check OK")
