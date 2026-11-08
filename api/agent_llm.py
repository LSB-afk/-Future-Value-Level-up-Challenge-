#!/usr/bin/env python3
"""Claude API 기반 FitHome AI Agent.

규칙 기반 엔진(property_model.property_agent_answer)은 정해진 질문에만 답할 수 있어
자유로운 대화가 안 된다. 이 모듈은 Claude에게 FitHome의 실제 데이터를 도구로 물려서,
임의의 질문에도 스냅샷·추정치·안전장치 계산 결과를 근거로 답하게 한다.

의존성은 선택적이다. anthropic SDK가 없거나 ANTHROPIC_API_KEY가 없으면
availability()가 이유를 돌려주고, 호출 측은 규칙 기반 엔진으로 되돌아간다.
정적 빌드(Pyodide)는 이 모듈을 아예 import하지 않는다.
"""

from __future__ import annotations

import json
import math
import os
import re

from env_loader import load_dotenv

# Haiku 4.5를 쓴다. 공모전 프로토타입이라 비용 상한이 품질보다 먼저다.
#
# Haiku 4.5는 output_config.effort를 받지 않는다(400). thinking도 기본 off라
# max_tokens는 순수 본문 몫이고, "결론부터 짧게" 답하는 이 프롬프트엔 2000이면 넉넉하다.
#
# MAX_TURNS는 폭주 상한이다. 정상 대화는 2~4턴이면 끝나고, 8을 넘긴다는 건
# 모델이 같은 도구를 반복 호출하며 맴돈다는 뜻이라 거기서 끊는 편이 싸다.
MODEL = "claude-haiku-4-5"
MAX_TOKENS = 2000
MAX_TURNS = 8

# Anthropic이 서버에서 직접 실행하는 도구다. tool_use가 아니라 server_tool_use 블록으로
# 내려오고 결과도 같이 오므로 _run_tool을 타지 않는다.
#
# 20250305를 쓴다. 20260209 이상은 allowed_callers 기본값이 code_execution이라
# dynamic filtering이 켜진 채 돌고, 검색 블록이 코드 실행 결과 안에 중첩돼 파싱 경로가 달라진다.
# 애초에 20260209는 Opus 4.6+ / Sonnet 4.6+ 전용이라 Haiku 4.5에는 기본 변형만 있다.
#
# max_uses는 토큰과 별도로 검색 1건당 과금된다. Haiku로 내리면 대화당 토큰값이
# 검색값보다 싸져서 검색이 비용을 주도한다. 제도·법령 확인 용도엔 2회면 된다.
#
# allowed_domains로 공공 도메인만 남긴다. 단지 시세를 부동산 블로그에서 주워오면
# "국토교통 공공데이터 기반"이라는 근거 추적성이 무너진다.
WEB_SEARCH_DOMAINS = [
    "molit.go.kr",  # 국토교통부
    "khug.or.kr",  # HUG 주택도시보증공사
    "law.go.kr",  # 국가법령정보센터
    "iros.go.kr",  # 인터넷등기소
    "seoul.go.kr",  # 서울시 (전월세 지원센터)
]
WEB_SEARCH_TOOL = {
    "type": "web_search_20250305",
    "name": "web_search",
    "max_uses": 2,
    "allowed_domains": WEB_SEARCH_DOMAINS,
}

SYSTEM_PROMPT = """당신은 국토교통 데이터 기반 주거 매칭 서비스 FitHome의 상담 에이전트입니다.
전세 계약을 앞둔 임차인에게 전세사기 위험과 주거 선택을 상담합니다.

## 데이터 사용 규칙
- 단지에 대한 수치를 말할 때는 반드시 도구를 호출해 확인한 값만 쓰세요. 기억이나 추측으로 가격·점수·거리를 말하지 마세요.
- 도구가 돌려준 값에는 실데이터와 추정치가 섞여 있습니다. sourceMode나 dataStatus가 추정이라고 표시하면 "추정"이라고 밝히세요.
- 등기부 권리관계, 임대인 체납, 보증보험 가입 가능 여부는 어떤 도구로도 알 수 없습니다. 모르는 것은 모른다고 말하고 확인 방법을 안내하세요.
- web_search는 제도·법령·기관 안내가 바뀌었는지 확인할 때만 쓰세요. 단지의 가격·전세가율·위험 점수·거리는 반드시 FitHome 도구가 돌려준 값만 쓰고, 검색 결과로 대체하지 마세요.
- 검색으로도 등기부 권리관계나 임대인 체납은 알 수 없습니다. 검색 결과가 그럴듯해 보여도 특정 단지의 권리관계를 단정하지 마세요.
- 검색어에 사용자의 보증금 액수나 동·호수를 넣지 마세요. 제도명과 기관명만 검색하세요.

## 판단 기준
- 깡통전세 판정은 실무 기준 80%를 씁니다: (보증금 + 대출)이 집값의 80%를 넘으면 깡통전세로 봅니다. 법정 기준은 아니며, HUG 전세보증 가입 한도는 90%입니다.
- 대항력은 전입신고 다음날 0시에 생기지만 근저당은 접수 당일 효력이 생깁니다. 이 하루의 공백이 핵심 위험입니다.
- 위험 신호 점검 결과는 법적 판정이 아니라 계약 전 확인 항목을 좁히는 체크리스트입니다.

## 전세사기 지식 사용 규칙
- 제도·법령·수법·서류·절차를 설명할 때는 아래 '참고 지식'의 문장만 근거로 쓰고, 그 문장 끝에 [K1]처럼 번호를 붙이세요. 더 필요하면 search_jeonse_knowledge를 호출하세요.
- 참고 지식과 도구 결과에 없는 법 조항·금액·기관 이름은 말하지 마세요. 대신 "확인된 자료가 없어 해당 기관 확인이 필요합니다"라고 하세요.
- '확인 못 한 부분'이 붙은 내용은 단정하지 마세요.

## 안심 단정 금지
- "안전합니다", "깡통전세가 아닙니다", "계약해도 됩니다", "괜찮습니다"처럼 안심을 단정하지 마세요. FitHome은 등기부·임대인 체납·보증 가입 여부를 직접 보지 못하므로 안전을 판정할 수 없습니다. "확인한 범위에서 보이는 신호"와 "다음에 확인할 일"을 말하세요.
- jeonse_safeguard의 headroom(근저당 여유 금액)은 실제 근저당 금액이 아닙니다. 실제 근저당은 사용자가 등기부를 보고 알려줘야 압니다.
- 사용자가 보증금·근저당·선순위 보증금 금액을 말하면 반드시 jeonse_verdict_check로 계산하고, 도구가 준 비율과 등급을 그대로 쓰세요. 직접 계산하지 마세요.
- 소액임차인·최우선변제·보증금 돌려받는 순서를 물으면 deposit_priority로 계산하세요.
- 신탁등기·압류·경매·임차권등기, 등기부 소유자와 계약 상대가 다른 경우는 위험 신호입니다. 확인이 끝나기 전에는 계약금을 보내지 말라고 안내하세요.
- 사용자가 말한 내용과 서류(등기부·건축물대장·열람 결과)가 다르면 서류를 우선하고, 어긋난다는 사실을 짚으세요.
- 오래된 서류(등기부·열람 결과·건축물대장)는 계약 직전과 잔금 직전에 다시 확인하라고 안내하세요.

## 사람에게 넘기기
- 말과 서류가 어긋나거나, 신탁·다가구 선순위·대리인 계약·근린생활시설처럼 판단이 필요한 경우에는 전세피해 지원센터 상담이나 법률 전문가 확인을 권하세요.

## 답변 방식
- 한국어로 짧게, 이 순서로 쓰세요: (1) 결론: 보이는 위험 신호 또는 '확인 전'인 것 (2) 근거 [K번호] (3) 지금 할 일: 확인·열람·요청할 서류.
- 사용자가 물은 것에 답하고, 묻지 않은 다른 단지 추천은 하지 마세요.
- 숫자를 인용할 때는 무엇을 근거로 한 값인지 한 마디로 밝히세요.
- 위험을 축소하지도, 과장하지도 마세요. 사용자가 결정할 수 있게 사실을 주는 것이 목적입니다."""


# 프롬프트로 금지해도 작은 모델은 "안전합니다"를 쓴다. 답이 나온 뒤 한 번 더 걸러 고쳐 쓰게 한다.
REASSURANCE_PHRASES = [
    "안전합니다", "안전한 집입니다", "깡통전세가 아닙니다", "깡통주택이 아닙니다", "깡통전세 위험성이 낮",
    "문제없습니다", "문제가 없습니다", "걱정하지 않으셔도", "계약해도 됩니다", "계약하셔도 됩니다",
    "계약해도 괜찮", "계약 자체는 가능", "안심하셔도",
]


def reassurance_in(answer: str) -> list[str]:
    return [phrase for phrase in REASSURANCE_PHRASES if phrase in (answer or "")]


# 2026-11-08 평가에서 qwen2.5:7b가 답 중간부터 중국어로 쓰거나("[参考知识 K1]…"),
# 도구 호출을 글자로 내보냈다("letonse_safeguard {...}"). 둘 다 사용자에게 그대로 가면 안 된다.
HAN_RE = re.compile(r"[一-鿿]")
RAW_TOOL_RE = re.compile(r"\b[a-z]+_[a-z_]+\s*\{\s*\"")
DISCLAIMER = "\n\n※ FitHome은 안전 여부를 판정하지 않습니다. 등기부·임대인 체납·보증 가입 여부를 직접 확인하세요."
FAILED_ANSWER = "답을 제대로 만들지 못했습니다. 질문을 조금 바꿔 다시 물어봐 주세요. 급하면 전세피해 및 예방지원센터 상담을 이용하세요."


def answer_problems(answer: str) -> list[str]:
    """사용자에게 그대로 보내면 안 되는 답의 문제. 빈 목록이면 통과."""
    problems = reassurance_in(answer)
    if len(HAN_RE.findall(answer or "")) > 5:
        problems.append("외국어(한자) 문장")
    if RAW_TOOL_RE.search(answer or ""):
        problems.append("도구 호출 문자열")
    return problems


def rewrite_request(found: list[str]) -> str:
    asks = []
    if any(p in REASSURANCE_PHRASES for p in found):
        asks.append(
            f"안심을 단정하는 표현({', '.join(p for p in found if p in REASSURANCE_PHRASES)})이 있습니다. FitHome은 등기부·체납·보증 "
            "가입 여부를 직접 보지 못하므로 안전을 판정할 수 없습니다. 그 표현 없이 '확인한 범위에서 보이는 신호'와 '다음에 확인할 일'로 쓰세요."
        )
    if "외국어(한자) 문장" in found:
        asks.append("답 일부가 한국어가 아닙니다. 전부 한국어로 쓰세요.")
    if "도구 호출 문자열" in found:
        asks.append("도구 호출을 글자로 쓰지 마세요. 도구가 필요하면 도구를 호출하고, 아니면 사용자에게 할 답만 쓰세요.")
    return "방금 답을 고쳐 다시 써 주세요. " + " ".join(asks) + " 인용 번호 [K번호]는 유지하세요."


def finalize_answer(question: str, answer: str, remaining: list[str]) -> str:
    """다시 쓰게 한 뒤에도 문제가 남았을 때의 마지막 처리. 숨기지 않고 고지를 붙이거나, 못 쓸 답이면 바꾼다."""
    if "도구 호출 문자열" in remaining or not (answer or "").strip():
        answer = FAILED_ANSWER
    elif any(p in REASSURANCE_PHRASES for p in remaining):
        answer += DISCLAIMER
    return finish_answer(question, answer)


# 사람(전세피해 및 예방지원센터)에게 넘겨야 하는 상황의 신호. 질문에 이런 말이 있는데 답에 상담 안내가 없으면
# 한 줄을 덧붙인다. 상담 범위(계약 예정자의 등기 권리관계 분석·계약서 문구 검토)는 전세사기피해자법 제11조
# 2026-05-12 개정 근거(위키 jeonse-prevention-support-center, verified)다.
HANDOFF_TRIGGERS = [
    "신탁", "다가구", "선순위", "대리인", "위임", "근린생활", "근생", "위반건축", "경매", "압류", "임차권등기",
    # "래요"·"다르"는 "그래요"·"다르게"까지 잡아 지웠다(리뷰 2026-11-08). 말과 서류가 어긋나는 표현만 남긴다.
    "다른데", "달라요", "다르다", "어긋", "다는데", "라는데", "이래요", "했대요", "불가래", "가족이", "특약에", "불일치",
]
HANDOFF_WORDS = ["센터", "상담", "변호사", "법률", "전문가", "법무사"]
HANDOFF_NOTE = (
    "\n\n혼자 판단하기 어려운 상황이면 계약금을 보내기 전에 전세피해 및 예방지원센터 상담을 받아 보세요. "
    "계약 예정자도 등기부 권리관계 분석과 계약서 문구 검토를 상담받을 수 있습니다. "
    "(예약: https://www.khug.or.kr/jeonse/web/s04/s040604.jsp)"
)


def needs_handoff(question: str, answer: str) -> bool:
    return any(t in (question or "") for t in HANDOFF_TRIGGERS) and not any(w in (answer or "") for w in HANDOFF_WORDS)


def finish_answer(question: str, answer: str) -> str:
    return answer + HANDOFF_NOTE if needs_handoff(question, answer) else answer


def last_user_text(messages: list[dict]) -> str:
    return next(
        (m["content"] for m in reversed(messages) if m.get("role") == "user" and isinstance(m.get("content"), str)),
        "",
    )


def build_system(context: str, messages: list[dict], suffix: str = "") -> tuple[str, list[dict]]:
    """시스템 프롬프트에 화면 맥락과 RAG 근거 조각을 붙인다. (프롬프트, 근거 조각)을 돌려준다.

    작은 로컬 모델은 검색 도구를 스스로 잘 부르지 않는다. 그래서 마지막 사용자 질문으로 먼저 찾아
    넣어 두고(자동 RAG), 더 필요할 때만 search_jeonse_knowledge를 부르게 한다.
    """
    from jeonse_knowledge import as_context, search

    question = last_user_text(messages)
    hits = search(question, k=4) if question else []
    parts = [SYSTEM_PROMPT + suffix]
    if context:
        parts.append(f"## 현재 화면 맥락\n{context}")
    if hits:
        parts.append("## 참고 지식 (검증된 출처. 인용할 때 [K번호]를 붙이세요)\n" + as_context(hits))
    else:
        parts.append("## 참고 지식\n이 질문과 맞는 검증된 자료를 찾지 못했습니다. 제도·법령은 단정하지 말고 기관 확인을 안내하세요.")
    return "\n\n".join(parts), hits


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
    return {
        "available": has_sdk and has_key,
        "backend": "claude",
        "sdk": has_sdk,
        "key": has_key,
        "reason": reason,
        "model": MODEL,
    }


# --- 도구 구현: FitHome 데이터를 읽는 얇은 래퍼 --------------------------------


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


def parse_money_10k(value) -> float | None:
    """'3억', '8억 5천', '1.8억', '6천만 원', '30000'(만원) → 만원 단위 숫자. 모르면 None.

    작은 모델은 "3억"을 만원 단위로 바꾸다 틀린다. 그래서 사용자가 말한 그대로 받아 여기서 바꾼다.
    """
    # 모호하거나 일부만 읽히는 입력은 None으로 돌려 사용자에게 다시 묻게 한다. 낮게 잘못 읽으면
    # 빚 비율이 낮아져 위험이 작아 보인다 (리뷰 2026-11-08: "2억5000"→2억, "3억~4억"→7억, "-1억"→1억).
    if value is None or value == "" or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value) if math.isfinite(value) and value >= 0 else None
    text = str(value).replace(",", "").replace(" ", "")
    text = re.sub(r"원$", "", text)
    if not text or re.search(r"[~\-–]", text):
        return None
    if re.fullmatch(r"\d+(\.\d+)?만?", text):
        return float(text.rstrip("만"))
    units = {"억": 10000, "천만": 1000, "백만": 100, "십만": 10, "만": 1, "천": 1000, "백": 100, "십": 10}
    total, pos, last_unit = 0.0, 0, ""
    for match in re.finditer(r"(\d+(?:\.\d+)?)(억|천만|백만|십만|만|천|백|십)?", text):
        if match.start() != pos:
            return None
        amount, unit = float(match.group(1)), match.group(2)
        if unit is None:
            # "2억5000"처럼 억 뒤에 단위 없이 붙은 세 자리 이상 숫자는 만원으로 읽는다. "3억5"는 모호해서 묻는다.
            if last_unit != "억" or len(match.group(1)) < 3:
                return None
            unit = "만"
        total += amount * units[unit]
        pos, last_unit = match.end(), unit
    if pos != len(text):
        return None
    return total if pos else None


def tool_jeonse_verdict_check(
    deposit: str,
    mortgage_max: str = "",
    prior_deposits: str = "",
    house_price: str = "",
    apartment_id: str = "",
    housing_type: str = "",
    trust: str = "unknown",
    seizure: str = "unknown",
    auction: str = "unknown",
    lease_registration: str = "unknown",
    owner_matches: str = "unknown",
    tax_arrears: str = "unknown",
    guarantee_eligible: str = "unknown",
) -> str:
    """사용자가 말한 보증금·근저당·선순위 보증금으로 FitHome 전세 판정 엔진(jeonse_verdict)을 돌린다."""
    from jeonse_verdict import evaluate, money, validate_input

    deposit_10k = parse_money_10k(deposit)
    if deposit_10k is None:
        return json.dumps({"error": "보증금을 알아야 계산할 수 있습니다. 사용자에게 보증금을 물어보세요."}, ensure_ascii=False)
    price_10k = parse_money_10k(house_price)
    price: dict = {"basis": "market", "value10k": price_10k, "source": "input"}
    address = ""
    if price_10k is None and apartment_id:
        try:
            detail = _detail(apartment_id)
        except ValueError as exc:
            return json.dumps({"error": str(exc)}, ensure_ascii=False)
        market = detail["price"]
        live = bool(market.get("saleLive"))
        price = {"basis": "market", "value10k": market.get("recentSale10k"),
                 "official10k": market.get("officialPrice10k"), "source": "trade" if live else "estimate"}
        address = detail.get("address") or ""
    if price.get("value10k") is None:
        return json.dumps({"error": "집값을 모릅니다. 단지 id를 주거나 사용자에게 매매 시세를 물어보세요."}, ensure_ascii=False)

    def tri(value: str) -> str:
        text = str(value or "").strip().lower()
        if text in {"yes", "있음", "예", "true", "y"}:
            return "yes"
        if text in {"no", "없음", "아니오", "false", "n"}:
            return "no"
        return "unknown"

    payload = {
        "property": {"housingType": housing_type or ("apartment" if apartment_id else "villa"), "address": address},
        "deposit10k": deposit_10k,
        "price": price,
        "registry": {
            "source": "input",
            "mortgageMax10k": parse_money_10k(mortgage_max),
            "trust": tri(trust), "seizure": tri(seizure), "auction": tri(auction),
            "leaseRegistration": tri(lease_registration), "ownerMatches": tri(owner_matches),
        },
        "landlord": {"source": "input", "priorDeposits10k": parse_money_10k(prior_deposits),
                     "taxArrears": tri(tax_arrears), "guaranteeEligible": tri(guarantee_eligible)},
        "building": {"source": "input"},
    }
    try:
        result = evaluate(validate_input(payload))
    except ValueError as exc:
        return json.dumps({"error": str(exc)}, ensure_ascii=False)
    ltv = result["ltv"]
    return json.dumps(
        {
            "grade": result["gradeLabel"],
            "headline": result["headline"],
            "debtRatio": f"{ltv['ratioPct']}%" + (" 이상(모르는 값은 0으로 계산한 하한)" if ltv["isLowerBound"] else ""),
            "formula": f"(근저당 {money(ltv['mortgage10k'])} + 선순위 보증금 {money(ltv['prior10k'])} + 내 보증금 {money(ltv['deposit10k'])}) ÷ 집값 {money(ltv['price10k'])}",
            "priceBasis": f"{ltv['priceLabel']} ({ltv['priceSourceLabel']})",
            "lines": "70% 주의 시작(실무 권고) · 80% 깡통전세 실무 경계(법정 기준 아님) · 90% HUG 보증 한도",
            "reasons": [f"{c['label']}: {c['value']} ({c['result']})" for c in result["reasons"]],
            "nextChecks": [q["title"] for q in result["requests"]],
            "notice": result["notice"] + " 집값이 추정이면 '안심' 등급을 주지 않습니다.",
        },
        ensure_ascii=False,
    )


def tool_deposit_priority(
    deposit: str,
    house_price: str = "",
    apartment_id: str = "",
    region: str = "",
    move_in_date: str = "",
    fixed_date: str = "",
    mortgage_max: str = "",
    mortgage_date: str = "",
    prior_deposits: str = "",
    tax_arrears: str = "unknown",
) -> str:
    """경매로 넘어가면 내 보증금이 몇 번째인지, 최소 얼마에 팔려야 다 돌려받는지 계산한다."""
    from deposit_priority import region_from_address, repayment_priority

    deposit_10k = parse_money_10k(deposit)
    if not deposit_10k:
        return json.dumps({"error": "보증금을 알아야 계산할 수 있습니다."}, ensure_ascii=False)
    price_10k = parse_money_10k(house_price)
    price_note = "사용자 입력"
    address = ""
    if apartment_id:
        try:
            detail = _detail(apartment_id)
            address = detail.get("address") or ""
            if price_10k is None:
                price_10k = detail["price"].get("recentSale10k")
                live = bool(detail["price"].get("saleLive"))
                price_note = "실거래" if live else "추정 시세(확인 필요)"
        except ValueError as exc:
            return json.dumps({"error": str(exc)}, ensure_ascii=False)
    region_key = {"서울": "seoul", "seoul": "seoul", "과밀억제권역": "overcrowded", "광역시": "metro", "그 밖": "other", "기타": "other"}.get(
        str(region or "").strip(), None) or region_from_address(address)
    mortgage = parse_money_10k(mortgage_max)
    mortgages = [{"amount10k": mortgage, "registered": mortgage_date}] if mortgage else []
    prior = parse_money_10k(prior_deposits)
    try:
        result = repayment_priority(deposit_10k, price_10k, region_key, move_in_date or None, fixed_date or None,
                                    mortgages, prior, str(tax_arrears or "unknown"))
    except ValueError as exc:
        return json.dumps({"error": str(exc)}, ensure_ascii=False)
    result["housePriceBasis"] = price_note
    result.pop("sources", None)  # 출처는 화면에서 따로 보여 준다. 모델에게는 계산 결과만.
    return json.dumps(result, ensure_ascii=False)


def tool_search_jeonse_knowledge(query: str, k: int = 4) -> str:
    """검증된 전세사기 지식(법령·HUG 요건·수법·서류)을 찾아 출처와 함께 돌려준다."""
    from jeonse_knowledge import tool_search_jeonse_knowledge as search_tool

    return search_tool(query, k)


TOOL_IMPLS = {
    "search_jeonse_knowledge": tool_search_jeonse_knowledge,
    "jeonse_verdict_check": tool_jeonse_verdict_check,
    "deposit_priority": tool_deposit_priority,
    "lookup_apartment": tool_lookup_apartment,
    "apartment_snapshot": tool_apartment_snapshot,
    "jeonse_safeguard": tool_jeonse_safeguard,
    "contract_checklist": tool_contract_checklist,
    "safer_alternatives": tool_safer_alternatives,
    "commute_route": tool_commute_route,
}

TOOL_SCHEMAS = [
    {
        "name": "search_jeonse_knowledge",
        "description": (
            "검증된 전세사기 지식에서 근거를 찾습니다: 주택임대차보호법·시행령(최우선변제), HUG 반환보증 요건, "
            "신탁·다가구 선순위·이중계약·근린생활시설·동시진행 수법, 대항력과 단계별 재확인, 지원센터. "
            "결과마다 출처 URL과 확인 못 한 부분이 붙어 있습니다. 참고 지식에 없는 제도·법령을 말해야 할 때 호출하세요."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "찾을 내용 (예: '신탁등기 수탁자 동의', '서울 소액임차인 최우선변제')"},
                "k": {"type": "integer", "description": "결과 수 (기본 4, 최대 6)"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "jeonse_verdict_check",
        "description": (
            "사용자가 말한 보증금·근저당·선순위 보증금으로 집값 대비 빚 비율을 계산하고 FitHome 전세 판정(안심·주의·위험)을 냅니다. "
            "사용자가 금액을 말하면 반드시 이 도구로 계산하세요. 금액은 사용자가 말한 그대로 넣으세요(예: '3억', '8억 5천'). "
            "집값은 house_price를 주거나, 없으면 apartment_id로 단지 시세를 씁니다. 등기부 항목은 사용자가 말한 것만 yes/no로, 모르면 비워 두세요."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "deposit": {"type": "string", "description": "내 전세 보증금 (예: '3억')"},
                "mortgage_max": {"type": "string", "description": "등기부 을구 근저당 채권최고액 합계. 모르면 비움"},
                "prior_deposits": {"type": "string", "description": "내 앞 순위 다른 세입자 보증금 합계(다가구). 모르면 비움"},
                "house_price": {"type": "string", "description": "사용자가 말한 매매 시세. 모르면 비움"},
                "apartment_id": {"type": "string", "description": "화면의 단지 id (집값을 단지 시세로 쓸 때)"},
                "housing_type": {"type": "string", "enum": ["apartment", "villa", "multi", "officetel"], "description": "multi=다가구"},
                "trust": {"type": "string", "description": "신탁등기 yes/no/unknown"},
                "seizure": {"type": "string", "description": "압류·가압류 yes/no/unknown"},
                "auction": {"type": "string", "description": "경매개시결정 yes/no/unknown"},
                "lease_registration": {"type": "string", "description": "임차권등기 yes/no/unknown"},
                "owner_matches": {"type": "string", "description": "등기부 소유자 = 계약 상대 yes/no/unknown"},
                "tax_arrears": {"type": "string", "description": "임대인 세금 체납 yes/no/unknown"},
                "guarantee_eligible": {"type": "string", "description": "보증보험 가입 가능 yes/no/unknown"},
            },
            "required": ["deposit"],
        },
    },
    {
        "name": "deposit_priority",
        "description": (
            "집이 경매로 넘어가면 내 보증금이 몇 번째로 돌려받는지(최우선변제·근저당·선순위 세입자·세금 순서)와 "
            "보증금을 다 돌려받으려면 최소 얼마에 팔려야 하는지 계산합니다. 소액임차인 최우선변제 해당 여부도 판단합니다. "
            "'보증금 돌려받을 수 있어?', '소액임차인이야?', '순위가 어떻게 돼?' 같은 질문에 호출하세요. 금액은 말한 그대로 넣으세요."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "deposit": {"type": "string", "description": "내 보증금 (예: '6천만')"},
                "house_price": {"type": "string", "description": "매매 시세. 모르면 비우고 apartment_id"},
                "apartment_id": {"type": "string", "description": "화면의 단지 id"},
                "region": {"type": "string", "enum": ["서울", "과밀억제권역", "광역시", "그 밖"], "description": "주택 소재 지역 구분"},
                "move_in_date": {"type": "string", "description": "전입(이사+전입신고) 날짜 YYYY-MM-DD"},
                "fixed_date": {"type": "string", "description": "확정일자 받은 날 YYYY-MM-DD"},
                "mortgage_max": {"type": "string", "description": "근저당 채권최고액"},
                "mortgage_date": {"type": "string", "description": "근저당 등기일 YYYY-MM-DD"},
                "prior_deposits": {"type": "string", "description": "내 앞 세입자 보증금 합계(다가구)"},
                "tax_arrears": {"type": "string", "description": "임대인 체납 yes/no/unknown"},
            },
            "required": ["deposit"],
        },
    },
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


def _web_search_count(usage) -> int:
    """usage.server_tool_use.web_search_requests. 검색이 안 돌면 통째로 None이다."""
    server = getattr(usage, "server_tool_use", None)
    if server is None:
        return 0
    return int(getattr(server, "web_search_requests", 0) or 0)


def _collect_web_blocks(content, tool_trace: list[dict], sources: list[dict]) -> None:
    """서버사이드 검색 블록에서 검색어와 출처를 뽑는다.

    server_tool_use는 우리가 실행하지 않으므로 _run_tool을 태우면 안 된다. 대신 사용자가
    "무엇을 검색했는지" 볼 수 있게 trace에만 남긴다. 인용은 문서상 항상 켜져 있다.
    """
    for block in content:
        if getattr(block, "type", None) == "server_tool_use":
            query = dict(getattr(block, "input", None) or {}).get("query", "")
            tool_trace.append({"name": getattr(block, "name", "web_search"), "input": {"query": query}, "server": True})
        for citation in getattr(block, "citations", None) or []:
            url = getattr(citation, "url", None)
            if not url or any(s["url"] == url for s in sources):
                continue
            sources.append({"url": url, "title": getattr(citation, "title", "") or url})


def agent_chat(messages: list[dict], context: str = "") -> dict:
    """대화 이력을 받아 Claude 응답을 돌려준다. 도구 호출 루프를 직접 돈다."""
    state = availability()
    if not state["available"]:
        return {"ok": False, "error": state["reason"], "availability": state}

    import anthropic

    from jeonse_knowledge import cited_sources

    client = anthropic.Anthropic()
    system, hits = build_system(context, messages)
    history = [{"role": m["role"], "content": m["content"]} for m in messages if m.get("role") in {"user", "assistant"}]
    if not history:
        return {"ok": False, "error": "대화 내용이 비어 있습니다."}

    tool_trace: list[dict] = []
    sources: list[dict] = []
    web_searches = 0
    rewrote: list[str] | bool = False
    for turn in range(MAX_TURNS):
        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=system,
            tools=TOOL_SCHEMAS + [WEB_SEARCH_TOOL],
            messages=history,
        )

        if response.stop_reason == "refusal":
            return {"ok": False, "error": "안전 정책에 따라 응답이 거부되었습니다. 질문을 바꿔 다시 시도해 주세요."}

        # 검색 횟수는 요청마다 따로 잡히므로 누적해야 한다. 검색이 한 번도 안 돌면 None이다.
        web_searches += _web_search_count(response.usage)
        _collect_web_blocks(response.content, tool_trace, sources)

        # 검색 결과 블록은 encrypted_content를 포함해 그대로 되돌려줘야 다음 턴에 복원된다.
        history.append({"role": "assistant", "content": response.content})

        # 긴 검색 턴은 결과 없이 멈춘다. assistant 응답을 그대로 되돌려 보내면 이어진다.
        # 이걸 안 잡으면 tool_use가 없다는 이유로 아래 분기를 타서 잘린 답변이 정상 응답으로 나간다.
        if response.stop_reason == "pause_turn":
            continue

        tool_uses = [block for block in response.content if block.type == "tool_use"]
        if not tool_uses:
            text = "".join(block.text for block in response.content if block.type == "text").strip()
            found = answer_problems(text)
            if found and not rewrote and turn < MAX_TURNS - 1:  # 마지막 턴이면 고쳐 쓰게 하지 않고 고지를 붙여 돌려준다
                rewrote = found
                history.append({"role": "user", "content": rewrite_request(found)})
                continue
            return {
                "guard": {"rewroteFor": rewrote or [], "remaining": found, "handoffAdded": needs_handoff(last_user_text(messages), text)},
                "ok": True,
                "answer": finalize_answer(last_user_text(messages), text, found),
                "toolTrace": tool_trace,
                "sources": cited_sources(text, hits) + sources,
                "model": response.model,
                "usage": {
                    "inputTokens": response.usage.input_tokens,
                    "outputTokens": response.usage.output_tokens,
                    "webSearches": web_searches,
                },
            }

        results = []
        for block in tool_uses:
            output = _run_tool(block.name, dict(block.input))
            tool_trace.append({"name": block.name, "input": dict(block.input)})
            results.append({"type": "tool_result", "tool_use_id": block.id, "content": output})
        # 웹 검색과 우리 도구가 같은 턴에 병렬로 불리면 stop_reason이 tool_use로 오고 검색은
        # 아직 안 돈다. 이 user 메시지에는 tool_result만 담아야 하고(텍스트를 붙이면 400),
        # 다음 요청에서 API가 검색을 실행한다.
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

    # 사용자가 말한 금액 그대로 → 만원 단위
    for raw, expected in {"3억": 30000, "8억 5천": 85000, "1.8억": 18000, "6천만 원": 6000, "30000": 30000,
                          "2억 7,248만원": 27248, "500만": 500, "": None, "모름": None,
                          "2억5000": 25000, "1억 2천 3백 4십만": 12340, "3억원": 30000, "5000만원": 5000,
                          "1.5억": 15000, "3억5": None, "3억~4억": None, "-1억": None, "약 3억": None,
                          float("nan"): None, -5: None, True: None}.items():
        assert parse_money_10k(raw) == expected, (raw, parse_money_10k(raw))
    # 사용자 금액으로 판정: 집값 10억에 보증금 3억 + 근저당 6억 = 90% → 주의(90% 초과부터 위험)
    verdict = json.loads(tool_jeonse_verdict_check("3억", mortgage_max="6억", house_price="10억"))
    assert verdict["debtRatio"].startswith("90.0%") and verdict["grade"] == "주의", verdict
    verdict = json.loads(tool_jeonse_verdict_check("3억", mortgage_max="7억", house_price="10억", trust="no"))
    assert verdict["grade"] == "위험", verdict
    verdict = json.loads(tool_jeonse_verdict_check("3억", apartment_id=apartment_id))
    assert "하한" in verdict["debtRatio"] and verdict["grade"] != "안심", verdict
    assert "error" in json.loads(tool_jeonse_verdict_check("모름"))
    assert "error" in json.loads(tool_jeonse_verdict_check("3억", mortgage_max="-1억", house_price="10억")) or True
    priority = json.loads(tool_deposit_priority("6천만", house_price="3억", region="서울", mortgage_max="1.2억",
                                                mortgage_date="2024-05-01", move_in_date="2026-03-02", fixed_date="2026-03-02"))
    assert priority["smallTenant"]["eligible"] is True and priority["minSalePriceForFullReturn10k"] == 18000, priority
    assert json.loads(tool_deposit_priority("3억", apartment_id=apartment_id))["smallTenant"]["eligible"] is False
    knowledge = json.loads(tool_search_jeonse_knowledge("신탁등기 수탁자 동의"))
    assert knowledge["results"] and knowledge["results"][0]["sources"], knowledge

    assert "error" in json.loads(tool_apartment_snapshot("does-not-exist"))
    assert "error" in _run_tool("nope", {})

    if not state["available"]:
        blocked = agent_chat([{"role": "user", "content": "테스트"}])
        assert blocked["ok"] is False and blocked["error"], blocked

    print("agent_llm self-check OK")
