#!/usr/bin/env python3
"""로컬 Ollama 기반 MoveValue AI Agent.

agent_llm(Claude)과 같은 일을 하되 과금이 없다. 도구 구현·시스템 프롬프트·도구 스키마는
전부 agent_llm에서 그대로 가져다 쓰고, 이 모듈은 "모델을 어떻게 호출하고 응답을 어떻게
읽느냐"만 다르게 한다. 반환 dict 모양도 agent_llm.agent_chat과 동일해서
movevalue_api와 app.js는 어느 엔진이 답했는지 몰라도 된다.

의존성은 stdlib뿐이다. ollama 파이썬 패키지도, requests도 쓰지 않는다 —
이 프로젝트의 API 서버 자체가 http.server 기반이라 POST 한 번에 패키지를 더할 이유가 없다.

정적 빌드(Pyodide)는 scripts/build_pages.py의 화이트리스트 방식이라 이 파일을 담지 않는다.
브라우저에서 localhost:11434에 닿을 수도 없으므로 그게 맞다.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from agent_llm import MAX_TURNS, SYSTEM_PROMPT, TOOL_SCHEMAS, _run_tool

# OLLAMA_HOST는 ollama CLI가 쓰는 관례적 이름이라 그대로 따른다.
HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434").rstrip("/")

# 로컬 8B 세 개를 같은 질문("논현동부센트레빌 깡통주택이야?", 정답 62.7% < 80%)으로 재보고 고름.
# 셋 다 tools를 지원하지만 숫자를 옮기는 정확도가 갈렸다:
#
#   qwen2.5:7b-instruct  62.7%를 59.0%로 지어냄. temperature 0에서도 재현됨. 탈락.
#   llama3.1:8b          숫자는 맞았으나 "62.7%로 80%를 넘는다 → 깡통주택입니다"로 판정을 뒤집음.
#                        빠르지만(6~8초) 결론이 틀리면 속도는 의미가 없다. 탈락.
#   gemma4:latest        숫자·부등호·판정 문구 모두 보존. 20~37초로 제일 느리다. 채택.
#
# 바꿀 거면 반드시 위 질문으로 다시 재고 나서 바꿀 것. 속도만 보고 내리면 판정이 뒤집힌다.
MODEL = os.environ.get("OLLAMA_MODEL", "gemma4:latest")

# num_ctx를 명시하지 않으면 Ollama가 기본값(모델에 따라 4096 이하)으로 잘라버린다.
# 잘리는 쪽은 앞이라 시스템 프롬프트부터 사라진다 — 즉 숫자 접지 규칙을 잃은 채 계속 답한다.
#
# 실측: 도구 1회 호출한 한 문답이 입력 5,252토큰이었다. 도구 결과 JSON이 한 건에 2,000토큰쯤
# 되므로 3~4턴이면 8192를 넘긴다. gemma4는 131,072까지 받으니 32,768로 올려 여유를 둔다.
NUM_CTX = 32768

# 그래도 넘칠 수는 있다. 넘치면 조용히 나빠지는 게 최악이라 응답에 표시해 드러낸다.
CTX_WARN_RATIO = 0.9

# 도구를 고르고 그 결과의 숫자를 옮겨 적는 작업이라 창의성이 해롭다.
TEMPERATURE = 0.0

# 기본 5분이면 발표 도중 언로드돼 다음 질문이 다시 수십 초 걸린다.
KEEP_ALIVE = "30m"

# 로컬 8B는 첫 호출에 모델을 램에 올리느라 수십 초가 걸린다.
LOAD_TIMEOUT = 180
PROBE_TIMEOUT = 3

# web_search는 Anthropic이 서버에서 돌려주던 기능이라 로컬 엔진에는 없다.
# 프롬프트를 통째로 복제하는 대신 차이나는 부분만 덧붙인다.
SYSTEM_SUFFIX = """

## 이 엔진의 제약
- web_search 도구가 없습니다. 제도·법령이 최신인지 확인할 수 없으니, 최신 여부가 중요하면 해당 기관에서 확인하라고 안내하세요.
- 단지의 가격·전세가율·위험 점수·거리는 반드시 도구를 먼저 호출해서 받은 값만 쓰세요. 도구를 부르지 않았다면 숫자를 말하지 마세요.

## 도구를 먼저 부르세요
- 제도를 묻는 질문이어도 화면 맥락에 단지가 있으면 jeonse_safeguard를 먼저 호출하세요. 대항력·특약·깡통 판정·지원센터는 그 도구가 이 단지에 맞춘 단계별 타임라인과 특약 문구를 돌려줍니다. 기억으로 일반론만 답하면 사용자가 정작 필요한 특약 문구를 못 받습니다.
- 계약·안전성·체크리스트를 물으면 contract_checklist를, 더 안전한 곳을 물으면 safer_alternatives를 부르세요.
- 도구를 부를 수 있는 질문에 부르지 않고 답하는 것이 이 엔진의 가장 흔한 실수입니다.

## 숫자 인용 규칙 (반드시 지킬 것)
- 도구 결과의 숫자는 **그대로 복사**하세요. 반올림하지 말고, 다시 계산하지 말고, 어림잡지 마세요. 62.7이면 62.7이라고 쓰세요. 59라고 쓰면 안 됩니다.
- verdictLabel 같은 판정 문구도 도구가 준 표현을 그대로 쓰세요. "여력 보통"을 "여력이 있습니다"로 바꾸지 마세요. 위험 판정을 부드럽게 고쳐 쓰면 사용자가 잘못된 결정을 합니다.
- 도구 결과에 없는 숫자는 절대 만들지 마세요.
- 출처를 지어내지 마세요. 검색을 못 하므로 "(출처: ○○)" 같은 표기를 붙일 근거가 없습니다. 근거는 "MoveValue 도구가 돌려준 값"이라고만 밝히세요."""


def _api(path: str, payload: dict | None, timeout: int) -> dict:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(
        f"{HOST}{path}", data=data, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def availability() -> dict:
    """Ollama가 떠 있고 모델이 받아져 있는지 확인한다. agent_llm.availability()와 같은 역할."""
    try:
        tags = _api("/api/tags", None, PROBE_TIMEOUT)
    except (urllib.error.URLError, OSError, ValueError) as exc:
        return {
            "available": False,
            "backend": "ollama",
            "model": MODEL,
            "reason": f"Ollama에 연결하지 못했습니다({HOST}). `ollama serve`가 떠 있는지 확인하세요. [{exc}]",
        }

    names = {str(item.get("name") or "") for item in tags.get("models") or []}
    # `ollama run qwen2.5:7b` 처럼 :latest가 생략된 이름으로 받아둔 경우도 맞춰준다.
    if MODEL not in names and f"{MODEL}:latest" not in names:
        return {
            "available": False,
            "backend": "ollama",
            "model": MODEL,
            "reason": f"모델 {MODEL}이 없습니다. `ollama pull {MODEL}` 후 다시 시도하세요.",
        }
    return {"available": True, "backend": "ollama", "model": MODEL, "reason": ""}


def _function_tools() -> list[dict]:
    """Anthropic 스키마(input_schema)를 Ollama가 받는 function 스키마(parameters)로 옮긴다."""
    return [
        {
            "type": "function",
            "function": {
                "name": schema["name"],
                "description": schema["description"],
                "parameters": schema["input_schema"],
            },
        }
        for schema in TOOL_SCHEMAS
    ]


def _tool_args(raw) -> dict:
    """Ollama 네이티브 API는 arguments를 dict로 주지만 버전·모델에 따라 JSON 문자열로도 온다."""
    if isinstance(raw, str):
        try:
            raw = json.loads(raw or "{}")
        except json.JSONDecodeError:
            return {}
    return raw if isinstance(raw, dict) else {}


def agent_chat(messages: list[dict], context: str = "") -> dict:
    """agent_llm.agent_chat과 같은 계약. 도구 호출 루프를 직접 돈다."""
    state = availability()
    if not state["available"]:
        return {"ok": False, "error": state["reason"], "availability": state}

    system = SYSTEM_PROMPT + SYSTEM_SUFFIX
    if context:
        system += f"\n\n## 현재 화면 맥락\n{context}"

    history: list[dict] = [{"role": "system", "content": system}]
    history += [
        {"role": m["role"], "content": m["content"]}
        for m in messages
        if m.get("role") in {"user", "assistant"}
    ]
    if len(history) == 1:
        return {"ok": False, "error": "대화 내용이 비어 있습니다."}

    tool_trace: list[dict] = []
    input_tokens = 0
    output_tokens = 0
    peak_prompt = 0

    for _ in range(MAX_TURNS):
        try:
            data = _api(
                "/api/chat",
                {
                    "model": MODEL,
                    "messages": history,
                    "tools": _function_tools(),
                    "stream": False,
                    "keep_alive": KEEP_ALIVE,
                    "options": {"num_ctx": NUM_CTX, "temperature": TEMPERATURE},
                },
                LOAD_TIMEOUT,
            )
        except (urllib.error.URLError, OSError, ValueError) as exc:
            return {"ok": False, "error": f"Ollama 호출 실패: {exc}", "toolTrace": tool_trace}

        prompt_tokens = int(data.get("prompt_eval_count") or 0)
        peak_prompt = max(peak_prompt, prompt_tokens)
        input_tokens += prompt_tokens
        output_tokens += int(data.get("eval_count") or 0)

        message = data.get("message") or {}
        history.append(message)
        calls = message.get("tool_calls") or []

        if not calls:
            result = {
                "ok": True,
                "answer": str(message.get("content") or "").strip(),
                "toolTrace": tool_trace,
                # 로컬 엔진에는 서버사이드 검색이 없다. app.js는 빈 배열이면 출처를 안 그린다.
                "sources": [],
                "model": data.get("model") or MODEL,
                "usage": {
                    "inputTokens": input_tokens,
                    "outputTokens": output_tokens,
                    "webSearches": 0,
                    "peakPromptTokens": peak_prompt,
                },
            }
            # 컨텍스트가 넘치면 Ollama는 앞에서부터 자른다 — 시스템 프롬프트의 접지 규칙이
            # 먼저 사라지고 답은 멀쩡해 보인다. 조용히 나빠지느니 드러내는 편이 낫다.
            if peak_prompt > NUM_CTX * CTX_WARN_RATIO:
                result["contextWarning"] = (
                    f"대화가 길어져 컨텍스트 한계({NUM_CTX})에 근접했습니다"
                    f"(최대 {peak_prompt}토큰). 새 대화를 시작하는 편이 정확합니다."
                )
            return result

        for call in calls:
            function = call.get("function") or {}
            name = str(function.get("name") or "")
            payload = _tool_args(function.get("arguments"))
            output = _run_tool(name, payload)
            tool_trace.append({"name": name, "input": payload})
            # Anthropic은 tool_result를 한 user 메시지에 모아 보내지만 Ollama는 호출당 tool 메시지다.
            history.append({"role": "tool", "tool_name": name, "content": output})

    return {"ok": False, "error": f"도구 호출이 {MAX_TURNS}회를 넘었습니다.", "toolTrace": tool_trace}


if __name__ == "__main__":
    print("availability:", json.dumps(availability(), ensure_ascii=False))

    tools = _function_tools()
    assert len(tools) == len(TOOL_SCHEMAS)
    assert {t["function"]["name"] for t in tools} == {s["name"] for s in TOOL_SCHEMAS}
    for tool in tools:
        assert tool["function"]["parameters"]["type"] == "object", tool

    assert _tool_args('{"apartment_id": "A1"}') == {"apartment_id": "A1"}
    assert _tool_args({"apartment_id": "A1"}) == {"apartment_id": "A1"}
    assert _tool_args("깨진 JSON") == {}
    assert _tool_args(None) == {}

    print("agent_ollama self-check OK")
