#!/usr/bin/env python3
"""agent_ollama.agent_chat의 도구 호출 루프 검증.

Ollama가 떠 있지 않아도 루프가 맞는지 확인해야 해서 urlopen을 가짜로 끼워 넣는다.
검증 대상: 도구 호출 → 실행 → tool 메시지 회신 → 최종 답변, arguments 형식 차이,
num_ctx 명시, 루프 상한, 서버·모델 부재 처리.
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import agent_ollama


class _FakeResponse:
    def __init__(self, payload):
        self._body = json.dumps(payload).encode("utf-8")

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def install_fake_ollama(scripted, tags=None):
    """scripted: /api/chat 호출 순서대로 돌려줄 응답 dict 목록."""
    calls = []

    def fake_urlopen(request, timeout=None):
        body = json.loads(request.data.decode("utf-8")) if request.data else None
        calls.append({"url": request.full_url, "body": body, "timeout": timeout})
        if request.full_url.endswith("/api/tags"):
            if tags is None:
                return _FakeResponse({"models": [{"name": agent_ollama.MODEL}]})
            return _FakeResponse(tags)
        return _FakeResponse(scripted.pop(0))

    urllib.request.urlopen = fake_urlopen
    return calls


def chat(content=None, tool_calls=None, prompt_tokens=40, eval_tokens=20):
    message = {"role": "assistant", "content": content or ""}
    if tool_calls:
        message["tool_calls"] = tool_calls
    return {
        "model": agent_ollama.MODEL,
        "message": message,
        "done": True,
        "prompt_eval_count": prompt_tokens,
        "eval_count": eval_tokens,
    }


# 1. 도구를 한 번 호출한 뒤 답하는 정상 흐름
calls = install_fake_ollama([
    chat(tool_calls=[{"function": {"name": "lookup_apartment", "arguments": {"query": "논현동부센트레빌"}}}]),
    chat(content="전세가율 기준으로 여력이 있습니다."),
])
result = agent_ollama.agent_chat([{"role": "user", "content": "이 단지 깡통이야?"}], context="테스트 맥락")
assert result["ok"] is True, result
assert result["answer"] == "전세가율 기준으로 여력이 있습니다."
assert [t["name"] for t in result["toolTrace"]] == ["lookup_apartment"]
# 로컬 엔진에는 서버사이드 검색이 없다 — app.js가 출처 블록을 안 그리도록 빈 배열이어야 한다
assert result["sources"] == []
assert result["usage"]["webSearches"] == 0
# 토큰은 요청마다 따로 잡히므로 누적돼야 한다
assert result["usage"]["inputTokens"] == 80, result["usage"]
assert result["usage"]["outputTokens"] == 40, result["usage"]

# 첫 호출 전에 /api/tags로 가용성을 확인한다
assert calls[0]["url"].endswith("/api/tags"), calls[0]

# 두 번째 /api/chat 요청에는 tool 메시지가 실려 나가야 한다
chat_calls = [c for c in calls if c["url"].endswith("/api/chat")]
sent = chat_calls[1]["body"]["messages"]
assert sent[-1]["role"] == "tool", sent[-1]
assert sent[-1]["tool_name"] == "lookup_apartment"
payload = json.loads(sent[-1]["content"])
assert payload["name"] == "논현동부센트레빌", payload

# 시스템 프롬프트가 첫 메시지로 붙고 화면 맥락이 들어간다
assert sent[0]["role"] == "system"
assert "테스트 맥락" in sent[0]["content"]
# web_search가 없다는 사실을 모델에게 알려야 검색한 척하지 않는다
assert "web_search 도구가 없습니다" in sent[0]["content"]

# num_ctx를 명시하지 않으면 Ollama 기본값이 프롬프트를 조용히 잘라 도구 설명이 사라진다
assert chat_calls[0]["body"]["options"]["num_ctx"] == agent_ollama.NUM_CTX
assert chat_calls[0]["body"]["stream"] is False
# Anthropic input_schema가 Ollama function parameters로 옮겨져야 한다
tools = chat_calls[0]["body"]["tools"]
assert len(tools) == len(agent_ollama.TOOL_SCHEMAS)
assert tools[0]["type"] == "function"
assert tools[0]["function"]["parameters"]["type"] == "object", tools[0]

# 2. arguments가 JSON 문자열로 와도(버전·모델 차이) 도구가 돈다
install_fake_ollama([
    chat(tool_calls=[{"function": {"name": "lookup_apartment", "arguments": '{"query": "논현동부센트레빌"}'}}]),
    chat(content="찾았습니다."),
])
result = agent_ollama.agent_chat([{"role": "user", "content": "찾아줘"}])
assert result["ok"] is True and result["toolTrace"][0]["input"] == {"query": "논현동부센트레빌"}, result

# 3. 여러 도구를 한 턴에 부르면 각각 tool 메시지로 회신된다
calls = install_fake_ollama([
    chat(tool_calls=[
        {"function": {"name": "apartment_snapshot", "arguments": {"apartment_id": "A13593908"}}},
        {"function": {"name": "jeonse_safeguard", "arguments": {"apartment_id": "A13593908"}}},
    ]),
    chat(content="확인했습니다."),
])
result = agent_ollama.agent_chat([{"role": "user", "content": "확인해줘"}])
assert result["ok"] is True
assert {t["name"] for t in result["toolTrace"]} == {"apartment_snapshot", "jeonse_safeguard"}
sent = [c for c in calls if c["url"].endswith("/api/chat")][1]["body"]["messages"]
assert [m["role"] for m in sent[-2:]] == ["tool", "tool"], sent[-2:]

# 4. 없는 단지를 물어도 루프가 죽지 않고 에러를 모델에 전달한다
calls = install_fake_ollama([
    chat(tool_calls=[{"function": {"name": "apartment_snapshot", "arguments": {"apartment_id": "없는단지"}}}]),
    chat(content="해당 단지를 찾지 못했습니다."),
])
result = agent_ollama.agent_chat([{"role": "user", "content": "없는 단지"}])
assert result["ok"] is True
sent = [c for c in calls if c["url"].endswith("/api/chat")][1]["body"]["messages"]
assert "error" in json.loads(sent[-1]["content"])

# 5. 도구 없이 바로 답해도 된다
install_fake_ollama([chat(content="등기부는 제가 확인할 수 없습니다.")])
result = agent_ollama.agent_chat([{"role": "user", "content": "등기부 봐줘"}])
assert result["ok"] is True and result["answer"] == "등기부는 제가 확인할 수 없습니다."
assert result["toolTrace"] == []

# 6. 도구만 계속 부르면 상한에서 멈춘다 (무한 루프 방지)
install_fake_ollama([
    chat(tool_calls=[{"function": {"name": "lookup_apartment", "arguments": {"query": "논현동부센트레빌"}}}])
    for _ in range(agent_ollama.MAX_TURNS)
])
result = agent_ollama.agent_chat([{"role": "user", "content": "루프"}])
assert result["ok"] is False and "넘었습니다" in result["error"], result

# 7. 빈 대화는 모델을 호출하지 않는다
install_fake_ollama([])
assert agent_ollama.agent_chat([])["ok"] is False

# 8. 모델을 안 받아뒀으면 pull을 안내한다
install_fake_ollama([], tags={"models": [{"name": "전혀-다른-모델"}]})
state = agent_ollama.availability()
assert state["available"] is False and "ollama pull" in state["reason"], state
assert agent_ollama.agent_chat([{"role": "user", "content": "x"}])["ok"] is False

# 9. Ollama가 안 떠 있으면 사유를 돌려주고, 호출 측이 규칙 기반으로 폴백한다
def _refuse(request, timeout=None):
    raise urllib.error.URLError("Connection refused")


urllib.request.urlopen = _refuse
state = agent_ollama.availability()
assert state["available"] is False and "연결하지 못했습니다" in state["reason"], state
result = agent_ollama.agent_chat([{"role": "user", "content": "안녕"}])
assert result["ok"] is False and result["availability"]["backend"] == "ollama"

print("agent_ollama loop test OK")
