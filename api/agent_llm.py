#!/usr/bin/env python3
"""Claude API 기반 MoveValue AI Agent.

규칙 기반 엔진(property_model.property_agent_answer)은 정해진 질문에만 답할 수 있어
자유로운 대화가 안 된다. 이 모듈은 Claude에게 MoveValue의 실제 데이터를 도구로 물려서,
임의의 질문에도 스냅샷·추정치·안전장치 계산 결과를 근거로 답하게 한다.

의존성은 선택적이다. anthropic SDK가 없거나 ANTHROPIC_API_KEY가 없으면
availability()가 이유를 돌려주고, 호출 측은 규칙 기반 엔진으로 되돌아간다.
정적 빌드(Pyodide)는 이 모듈을 아예 import하지 않는다.
"""

from __future__ import annotations

import json
import os

from env_loader import load_dotenv

# Opus 5는 thinking이 기본 on이고 max_tokens가 thinking+본문을 함께 제한한다.
# 대화형이라 effort는 medium으로 두고 토큰은 넉넉히 잡는다.
MODEL = "claude-opus-5"
MAX_TOKENS = 8000
EFFORT = "medium"
MAX_TURNS = 24

SYSTEM_PROMPT = """당신은 국토교통 데이터 기반 주거 매칭 서비스 MoveValue의 상담 에이전트입니다.
전세 계약을 앞둔 임차인에게 전세사기 위험과 주거 선택을 상담합니다.

## 데이터 사용 규칙
- 단지에 대한 수치를 말할 때는 반드시 도구를 호출해 확인한 값만 쓰세요. 기억이나 추측으로 가격·점수·거리를 말하지 마세요.
- 도구가 돌려준 값에는 실데이터와 추정치가 섞여 있습니다. sourceMode나 dataStatus가 추정이라고 표시하면 "추정"이라고 밝히세요.
- 등기부 권리관계, 임대인 체납, 보증보험 가입 가능 여부는 어떤 도구로도 알 수 없습니다. 모르는 것은 모른다고 말하고 확인 방법을 안내하세요.

## 판단 기준
- 깡통주택 판정은 HUG 기준을 씁니다: (보증금 + 대출)이 집값의 80%를 넘으면 깡통주택.
- 대항력은 전입신고 다음날 0시에 생기지만 근저당은 접수 당일 효력이 생깁니다. 이 하루의 공백이 핵심 위험입니다.
- 위험 신호 점검 결과는 법적 판정이 아니라 계약 전 확인 항목을 좁히는 체크리스트입니다.

## 답변 방식
- 한국어로, 결론부터 말하고 근거를 뒤에 붙이세요.
- 짧게 쓰세요. 사용자가 물은 것에 답하고, 묻지 않은 내용을 덧붙이지 마세요.
- 숫자를 인용할 때는 무엇을 근거로 한 값인지 한 마디로 밝히세요.
- 위험을 축소하지도, 과장하지도 마세요. 사용자가 결정할 수 있게 사실을 주는 것이 목적입니다."""


def availability() -> dict:
    """SDK와 키가 준비됐는지 확인한다. 호출 측이 폴백 여부를 정하는 근거."""
    load_dotenv()
    has_key = bool(os.environ.get("ANTHROPIC_API_KEY", "").strip())
    try:
        import anthropic  # noqa: F401

        has_sdk = True
    except ImportError:
        has_sdk = False

    if not has_sdk:
        reason = "anthropic SDK가 설치되지 않았습니다. pip install anthropic"
    elif not has_key:
        reason = "ANTHROPIC_API_KEY가 없습니다. .env에 키를 넣으세요."
    else:
        reason = ""
    return {"available": has_sdk and has_key, "sdk": has_sdk, "key": has_key, "reason": reason, "model": MODEL}


# --- 도구 구현: MoveValue 데이터를 읽는 얇은 래퍼 -------------------------------


def _detail(apartment_id: str) -> dict:
    from property_adapters import property_detail_response

    return property_detail_response({"id": [str(apartment_id)]})["detail"]


def tool_lookup_apartment(query: str) -> str:
    """단지명이나 주소로 단지를 찾아 id와 기본 정보를 돌려준다."""
    from property_adapters import find_apartment

    try:
        apartment = find_apartment({"q": [str(query)]})
    except ValueError as exc:
        return json.dumps({"error": str(exc)}, ensure_ascii=False)
    return json.dumps(
        {
            "id": apartment.get("id"),
            "name": apartment.get("name"),
            "address": apartment.get("address"),
            "district": apartment.get("district"),
            "dong": apartment.get("dong"),
            "category": apartment.get("category"),
            "approvalDate": apartment.get("approvalDate"),
        },
        ensure_ascii=False,
    )


def tool_apartment_snapshot(apartment_id: str) -> str:
    """단지의 가격 추정, 전세 위험 신호, 생활 인프라 점수를 돌려준다."""
    try:
        detail = _detail(apartment_id)
    except ValueError as exc:
        return json.dumps({"error": str(exc)}, ensure_ascii=False)
    return json.dumps(
        {
            "name": detail["name"],
            "address": detail["address"],
            "buildingAge": detail["buildingAge"],
            "households": detail["households"],
            "price": detail["price"],
            "risk": {
                "score": detail["risk"]["score"],
                "level": detail["risk"]["level"],
                "signals": detail["risk"]["signals"],
            },
            "lifestyle": detail["lifestyle"],
            "dataStatus": detail["dataStatus"],
        },
        ensure_ascii=False,
    )


def tool_jeonse_safeguard(apartment_id: str) -> str:
    """깡통주택 판정, 정보 사각지대, 대항력 타임라인, 가까운 지원센터를 돌려준다."""
    try:
        detail = _detail(apartment_id)
    except ValueError as exc:
        return json.dumps({"error": str(exc)}, ensure_ascii=False)
    return json.dumps(detail.get("safeguard", {}), ensure_ascii=False)


def tool_contract_checklist(apartment_id: str) -> str:
    """계약 전 확인 체크리스트를 돌려준다. 임대인 동의가 필요한 항목이 표시된다."""
    try:
        detail = _detail(apartment_id)
    except ValueError as exc:
        return json.dumps({"error": str(exc)}, ensure_ascii=False)
    return json.dumps(detail["risk"].get("contractChecklist", []), ensure_ascii=False)


def tool_safer_alternatives(apartment_id: str, limit: int = 5) -> str:
    """이 단지보다 전세 위험 점수가 낮은 대안 단지를 돌려준다."""
    from property_adapters import comparison_candidates

    try:
        detail = _detail(apartment_id)
    except ValueError as exc:
        return json.dumps({"error": str(exc)}, ensure_ascii=False)

    current = detail["risk"]["score"]
    rows = [
        {
            "id": item["id"],
            "name": item["name"],
            "address": item["address"],
            "riskScore": item["preview"]["riskScore"],
            "riskLevel": item["preview"]["riskLevel"],
            "saleLabel": item["preview"]["saleLabel"],
            "jeonseRatio": item["preview"]["jeonseRatio"],
        }
        for item in comparison_candidates()
        if item.get("id") != detail["id"] and item.get("preview", {}).get("riskScore", 100) < current
    ]
    rows.sort(key=lambda row: row["riskScore"])
    return json.dumps({"currentRiskScore": current, "alternatives": rows[: max(1, int(limit))]}, ensure_ascii=False)


def tool_commute_route(apartment_id: str, destination: str, transport_mode: str = "transit") -> str:
    """단지에서 목적지까지의 통근 경로(소요시간, 환승, 요금)를 돌려준다."""
    from route_adapters import build_commute_route, resolve_location

    try:
        detail = _detail(apartment_id)
    except ValueError as exc:
        return json.dumps({"error": str(exc)}, ensure_ascii=False)

    origin = {"label": detail["name"], "lat": detail["lat"], "lng": detail["lng"], "source": "apartment"}
    try:
        target = resolve_location(str(destination), _known_locations())
    except ValueError as exc:
        return json.dumps({"error": f"목적지 해석 실패: {exc}"}, ensure_ascii=False)

    route = build_commute_route(origin, target, "tmap", str(transport_mode))
    return json.dumps(
        {
            "origin": detail["name"],
            "destination": target.get("label"),
            "totalMinutes": route.get("totalMinutes"),
            "transfers": route.get("transfers"),
            "walkMeters": route.get("walkMeters"),
            "fare": route.get("fare"),
            "sourceMode": route.get("sourceMode"),
        },
        ensure_ascii=False,
    )


def _known_locations() -> dict:
    # movevalue_api.known_locations를 쓰면 순환 import가 되므로 생활권만으로 최소 집합을 만든다.
    from property_model import load_areas

    locations: dict = {}
    for area in load_areas():
        key = str(area.get("name") or "")
        if not key:
            continue
        locations[key] = {
            "label": area.get("name"),
            "address": area.get("representativeAddress") or area.get("name"),
            "name": area.get("name"),
            "station": area.get("station"),
            "lat": area.get("lat"),
            "lng": area.get("lng"),
        }
    return locations


TOOL_IMPLS = {
    "lookup_apartment": tool_lookup_apartment,
    "apartment_snapshot": tool_apartment_snapshot,
    "jeonse_safeguard": tool_jeonse_safeguard,
    "contract_checklist": tool_contract_checklist,
    "safer_alternatives": tool_safer_alternatives,
    "commute_route": tool_commute_route,
}

TOOL_SCHEMAS = [
    {
        "name": "lookup_apartment",
        "description": (
            "단지명이나 주소 일부로 아파트 단지를 찾아 내부 id를 얻습니다. "
            "사용자가 단지를 이름으로 언급했는데 id를 모를 때 가장 먼저 호출하세요."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "단지명 또는 주소 일부"}},
            "required": ["query"],
        },
    },
    {
        "name": "apartment_snapshot",
        "description": (
            "단지의 매매·전세·월세 추정가, 전세가율, 공시가격, 전세 위험 신호 6종, 생활 SOC/안전 점수, "
            "각 값이 실데이터인지 추정인지 알려주는 dataStatus를 돌려줍니다. "
            "가격이나 위험도를 언급하기 전에 호출하세요."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"apartment_id": {"type": "string", "description": "단지 id"}},
            "required": ["apartment_id"],
        },
    },
    {
        "name": "jeonse_safeguard",
        "description": (
            "전세사기 안전장치를 돌려줍니다: HUG 80% 기준 깡통주택 자동 판정과 근저당 여력 금액, "
            "주택 유형별 정보 사각지대, 임대인 동의 없이 확인 가능한 경로, 동의가 필요한 항목과 거부 시 대응, "
            "대항력 확보 타임라인과 특약 문구, 가장 가까운 전세피해 예방지원센터. "
            "깡통 여부·계약 안전성·특약·상담센터 질문에 호출하세요."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"apartment_id": {"type": "string", "description": "단지 id"}},
            "required": ["apartment_id"],
        },
    },
    {
        "name": "contract_checklist",
        "description": "계약 전 확인 체크리스트를 돌려줍니다. 각 항목에 우선순위와 임대인 동의 필요 여부가 붙어 있습니다.",
        "input_schema": {
            "type": "object",
            "properties": {"apartment_id": {"type": "string", "description": "단지 id"}},
            "required": ["apartment_id"],
        },
    },
    {
        "name": "safer_alternatives",
        "description": "이 단지보다 전세 위험 점수가 낮은 대안 단지를 위험도 순으로 돌려줍니다. 더 안전한 곳을 물을 때 호출하세요.",
        "input_schema": {
            "type": "object",
            "properties": {
                "apartment_id": {"type": "string", "description": "기준 단지 id"},
                "limit": {"type": "integer", "description": "최대 개수 (기본 5)"},
            },
            "required": ["apartment_id"],
        },
    },
    {
        "name": "commute_route",
        "description": (
            "단지에서 목적지까지 소요시간·환승·도보거리·요금을 돌려줍니다. "
            "sourceMode가 live가 아니면 거리 기반 추정이므로 그렇게 밝히세요."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "apartment_id": {"type": "string", "description": "출발 단지 id"},
                "destination": {"type": "string", "description": "목적지 주소 또는 생활권명"},
                "transport_mode": {
                    "type": "string",
                    "enum": ["transit", "car", "bicycle", "walk"],
                    "description": "이동 수단 (기본 transit)",
                },
            },
            "required": ["apartment_id", "destination"],
        },
    },
]


def _run_tool(name: str, payload: dict) -> str:
    impl = TOOL_IMPLS.get(name)
    if impl is None:
        return json.dumps({"error": f"알 수 없는 도구: {name}"}, ensure_ascii=False)
    try:
        return impl(**payload)
    except Exception as exc:  # noqa: BLE001 - 도구 실패는 모델이 읽고 대처해야 한다.
        return json.dumps({"error": f"{name} 실행 실패: {exc}"}, ensure_ascii=False)


def agent_chat(messages: list[dict], context: str = "") -> dict:
    """대화 이력을 받아 Claude 응답을 돌려준다. 도구 호출 루프를 직접 돈다."""
    state = availability()
    if not state["available"]:
        return {"ok": False, "error": state["reason"], "availability": state}

    import anthropic

    client = anthropic.Anthropic()
    system = SYSTEM_PROMPT if not context else f"{SYSTEM_PROMPT}\n\n## 현재 화면 맥락\n{context}"
    history = [{"role": m["role"], "content": m["content"]} for m in messages if m.get("role") in {"user", "assistant"}]
    if not history:
        return {"ok": False, "error": "대화 내용이 비어 있습니다."}

    tool_trace: list[dict] = []
    for _ in range(MAX_TURNS):
        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=system,
            output_config={"effort": EFFORT},
            tools=TOOL_SCHEMAS,
            messages=history,
        )

        if response.stop_reason == "refusal":
            return {"ok": False, "error": "안전 정책에 따라 응답이 거부되었습니다. 질문을 바꿔 다시 시도해 주세요."}

        history.append({"role": "assistant", "content": response.content})

        tool_uses = [block for block in response.content if block.type == "tool_use"]
        if not tool_uses:
            text = "".join(block.text for block in response.content if block.type == "text").strip()
            return {
                "ok": True,
                "answer": text,
                "toolTrace": tool_trace,
                "model": response.model,
                "usage": {
                    "inputTokens": response.usage.input_tokens,
                    "outputTokens": response.usage.output_tokens,
                },
            }

        results = []
        for block in tool_uses:
            output = _run_tool(block.name, dict(block.input))
            tool_trace.append({"name": block.name, "input": dict(block.input)})
            results.append({"type": "tool_result", "tool_use_id": block.id, "content": output})
        history.append({"role": "user", "content": results})

    return {"ok": False, "error": f"도구 호출이 {MAX_TURNS}회를 넘었습니다.", "toolTrace": tool_trace}


if __name__ == "__main__":
    state = availability()
    print("availability:", json.dumps(state, ensure_ascii=False))

    names = {schema["name"] for schema in TOOL_SCHEMAS}
    assert names == set(TOOL_IMPLS), (names, set(TOOL_IMPLS))
    for schema in TOOL_SCHEMAS:
        assert schema["input_schema"]["type"] == "object"
        for field in schema["input_schema"]["required"]:
            assert field in schema["input_schema"]["properties"], (schema["name"], field)

    found = json.loads(tool_lookup_apartment("논현동부센트레빌"))
    assert found.get("id"), found
    apartment_id = found["id"]

    snapshot = json.loads(tool_apartment_snapshot(apartment_id))
    assert snapshot["price"]["recentJeonse10k"] > 0, snapshot
    assert len(snapshot["risk"]["signals"]) >= 5

    safeguard = json.loads(tool_jeonse_safeguard(apartment_id))
    assert safeguard["gaptong"]["thresholdPct"] == 80.0
    assert safeguard["center"]["phone"]

    assert json.loads(tool_contract_checklist(apartment_id))
    alternatives = json.loads(tool_safer_alternatives(apartment_id, limit=3))
    assert len(alternatives["alternatives"]) <= 3

    route = json.loads(tool_commute_route(apartment_id, "강남 업무지구"))
    assert route.get("totalMinutes", 0) > 0 or route.get("error"), route

    assert "error" in json.loads(tool_apartment_snapshot("does-not-exist"))
    assert "error" in _run_tool("nope", {})

    if not state["available"]:
        blocked = agent_chat([{"role": "user", "content": "테스트"}])
        assert blocked["ok"] is False and blocked["error"], blocked

    print("agent_llm self-check OK")
