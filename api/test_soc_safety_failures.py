#!/usr/bin/env python3
"""카카오 조회가 실패하면 시설 0개가 아니라 '모름'으로 알리고, 실패 결과는 짧게만 캐시하는지 확인한다.

외부 API는 부르지 않는다(_request를 가짜로 바꾼다).

    python3 api/test_soc_safety_failures.py
"""

from __future__ import annotations

import kakao_safety_adapters as safety
import kakao_soc_adapters as soc

PLACE = {"id": "1", "place_name": "OO경찰서 지구대", "x": "127.0", "y": "37.5", "distance": "300"}


def _run(module, request, response_fn, raw):
    original_request, original_key = module._request, module._env_key
    module._request = request
    module._env_key = lambda: "test-key"
    module._CACHE.clear()
    try:
        return response_fn(raw)
    finally:
        module._request, module._env_key = original_request, original_key


def test_safety_all_failed_is_unknown_not_zero() -> None:
    def failing(params, api_key):
        raise OSError("timeout")

    result = _run(safety, failing, safety.kakao_safety_response, {"lat": ["37.5"], "lng": ["127.0"]})
    assert result["status"] == "failed" and result["mode"] == "partial_error", result
    assert sorted(result["failedCategories"]) == ["green", "police"], result
    for item in result["categories"].values():
        assert item["count"] is None and item["ok"] is False and item["status"] == "failed", item
    entry = next(iter(safety._CACHE.values()))
    assert entry[2] == safety.FAILURE_CACHE_SECONDS  # 6시간이 아니라 5분


def test_safety_partial_and_ok() -> None:
    def police_only_fails_once(params, api_key):
        if params["query"] == "지구대":
            raise OSError("timeout")
        return {"documents": [PLACE] if params["query"] != "공원" else [], "meta": {"is_end": True}}

    result = _run(safety, police_only_fails_once, safety.kakao_safety_response, {"lat": ["37.5"], "lng": ["127.0"]})
    police, green = result["categories"]["police"], result["categories"]["green"]
    assert police["status"] == "partial" and police["count"] == 1 and police["ok"] is False, police
    assert green["status"] == "ok" and green["count"] == 0 and green["ok"] is True, green  # 진짜 0개
    assert result["status"] == "partial" and result["partialCategories"] == ["police"] and result["failedCategories"] == []

    ok = _run(safety, lambda params, api_key: {"documents": [], "meta": {"is_end": True}},
              safety.kakao_safety_response, {"lat": ["37.5"], "lng": ["127.0"]})
    assert ok["status"] == "ok" and ok["mode"] == "live_api" and ok["failedCategories"] == []
    assert next(iter(safety._CACHE.values()))[2] == safety.CACHE_SECONDS


def test_soc_failed_category_is_unknown() -> None:
    def medical_fails(endpoint, params, api_key):
        if params.get("category_group_code") == "HP8":
            raise OSError("timeout")
        return {"documents": [], "meta": {"is_end": True}}

    result = _run(soc, medical_fails, soc.kakao_soc_response, {"lat": ["37.5"], "lng": ["127.0"]})
    assert result["categories"]["medical"]["count"] is None, result["categories"]["medical"]
    assert result["failedCategories"] == ["medical"] and result["status"] == "partial", result
    assert result["categories"]["transport"]["count"] == 0 and result["categories"]["transport"]["ok"]
    assert next(iter(soc._CACHE.values()))[2] == soc.FAILURE_CACHE_SECONDS
    # 기존 키는 그대로 있다
    assert {"ok", "mode", "radiusMeters", "categories", "integrations", "source"} <= set(result)


if __name__ == "__main__":
    test_safety_all_failed_is_unknown_not_zero()
    test_safety_partial_and_ok()
    test_soc_failed_category_is_unknown()
    print("soc/safety failure test OK")
