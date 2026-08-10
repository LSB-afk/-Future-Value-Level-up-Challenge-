#!/usr/bin/env python3
"""agent_chat의 도구 호출 루프 검증.

실제 API 키 없이도 루프가 맞는지 확인해야 해서 anthropic 모듈을 가짜로 끼워 넣는다.
검증 대상: 도구 호출 → 실행 → 결과 회신 → 최종 답변, 거부 처리, 루프 상한.
"""

from __future__ import annotations

import json
import os
import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))


class _Block:
    def __init__(self, **fields):
        self.__dict__.update(fields)


class _Usage:
    input_tokens = 100
    output_tokens = 50


class _Response:
    def __init__(self, content, stop_reason="end_turn"):
        self.content = content
        self.stop_reason = stop_reason
        self.model = "claude-opus-5"
        self.usage = _Usage()


def install_fake_anthropic(scripted):
    """scripted: 호출 순서대로 돌려줄 _Response 목록."""
    calls = []

    class _Messages:
        def create(self, **kwargs):
            # messages는 호출 후에도 계속 변형되므로 호출 시점 상태를 얕게 복사해 둔다.
            snapshot = dict(kwargs)
            snapshot["messages"] = [dict(m) for m in kwargs.get("messages", [])]
            calls.append(snapshot)
            return scripted.pop(0)

    class _Client:
        def __init__(self, *args, **kwargs):
            self.messages = _Messages()

    module = types.ModuleType("anthropic")
    module.Anthropic = _Client
    sys.modules["anthropic"] = module
    return calls


def reload_agent_llm():
    sys.modules.pop("agent_llm", None)
    import agent_llm

    return agent_llm


os.environ["ANTHROPIC_API_KEY"] = "test-key-not-real"

# 1. 도구를 한 번 호출한 뒤 답하는 정상 흐름
calls = install_fake_anthropic([
    _Response([
        _Block(type="tool_use", id="tu_1", name="lookup_apartment", input={"query": "논현동부센트레빌"}),
    ]),
    _Response([_Block(type="text", text="전세가율 기준으로 여력이 있습니다.")]),
])
agent_llm = reload_agent_llm()

assert agent_llm.availability()["key"] is True
result = agent_llm.agent_chat([{"role": "user", "content": "이 단지 깡통이야?"}], context="테스트 맥락")
assert result["ok"] is True, result
assert result["answer"] == "전세가율 기준으로 여력이 있습니다."
assert [t["name"] for t in result["toolTrace"]] == ["lookup_apartment"]
assert result["usage"]["inputTokens"] == 100

# 두 번째 요청에는 tool_result가 실려 나가야 한다
second = calls[1]["messages"]
assert second[-1]["role"] == "user"
assert second[-1]["content"][0]["type"] == "tool_result"
assert second[-1]["content"][0]["tool_use_id"] == "tu_1"
payload = json.loads(second[-1]["content"][0]["content"])
assert payload["name"] == "논현동부센트레빌", payload

# 시스템 프롬프트에 화면 맥락이 붙는다
assert "테스트 맥락" in calls[0]["system"]
assert calls[0]["model"] == "claude-opus-5"
assert calls[0]["output_config"]["effort"] == "medium"
assert len(calls[0]["tools"]) == len(agent_llm.TOOL_SCHEMAS)

# 2. 여러 도구를 한 턴에 호출해도 결과가 모두 회신된다
calls = install_fake_anthropic([
    _Response([
        _Block(type="tool_use", id="a", name="apartment_snapshot", input={"apartment_id": "A13593908"}),
        _Block(type="tool_use", id="b", name="jeonse_safeguard", input={"apartment_id": "A13593908"}),
    ]),
    _Response([_Block(type="text", text="확인했습니다.")]),
])
agent_llm = reload_agent_llm()
result = agent_llm.agent_chat([{"role": "user", "content": "확인해줘"}])
assert result["ok"] is True
assert len(calls[1]["messages"][-1]["content"]) == 2
assert {t["name"] for t in result["toolTrace"]} == {"apartment_snapshot", "jeonse_safeguard"}

# 3. 존재하지 않는 단지를 물어도 루프가 죽지 않고 에러를 모델에 전달한다
calls = install_fake_anthropic([
    _Response([_Block(type="tool_use", id="x", name="apartment_snapshot", input={"apartment_id": "없는단지"})]),
    _Response([_Block(type="text", text="해당 단지를 찾지 못했습니다.")]),
])
agent_llm = reload_agent_llm()
result = agent_llm.agent_chat([{"role": "user", "content": "없는 단지"}])
assert result["ok"] is True
assert "error" in json.loads(calls[1]["messages"][-1]["content"][0]["content"])

# 4. 안전 정책 거부는 사용자에게 그대로 알린다
install_fake_anthropic([_Response([], stop_reason="refusal")])
agent_llm = reload_agent_llm()
result = agent_llm.agent_chat([{"role": "user", "content": "..."}])
assert result["ok"] is False and "거부" in result["error"], result

# 5. 도구만 계속 부르면 상한에서 멈춘다 (무한 루프 방지)
agent_llm = reload_agent_llm()
loop = [
    _Response([_Block(type="tool_use", id=f"t{i}", name="lookup_apartment", input={"query": "논현동부센트레빌"})])
    for i in range(agent_llm.MAX_TURNS)
]
install_fake_anthropic(loop)
agent_llm = reload_agent_llm()
result = agent_llm.agent_chat([{"role": "user", "content": "루프"}])
assert result["ok"] is False and "넘었습니다" in result["error"], result

# 6. 빈 대화는 API를 호출하지 않는다
install_fake_anthropic([])
agent_llm = reload_agent_llm()
assert agent_llm.agent_chat([])["ok"] is False

print("agent_llm loop test OK")
