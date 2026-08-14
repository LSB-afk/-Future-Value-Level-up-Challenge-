#!/usr/bin/env python3
"""로컬 모델이 도구 결과를 정확히 옮기는지 재는 평가 하네스.

test_agent_ollama_loop.py가 "루프가 맞게 도는가"를 본다면, 이 파일은 "모델이 사실을
지어내지 않는가"를 본다. 둘은 다른 실패다. 루프는 완벽해도 8B는 62.7%를 59.0%로 쓴다.

실제로 세 모델을 이 방식으로 재서 골랐다:
    qwen2.5:7b-instruct  전세가율을 지어냄 (62.7 → 59.0)
    llama3.1:8b          숫자는 맞고 부등호를 뒤집음 ("62.7%로 80%를 넘으므로 깡통주택")
    gemma4:latest        통과 → 기본값

모델을 바꾸려면 반드시 이걸 먼저 돌릴 것:
    python3 api/eval_agent_ollama.py
    OLLAMA_MODEL=llama3.1:8b python3 api/eval_agent_ollama.py

Ollama가 떠 있어야 하고, 모델당 2~5분 걸린다.
"""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import agent_ollama
from agent_llm import SYSTEM_PROMPT, _run_tool

APARTMENT_ID = "A13593908"
CONTEXT = f"사용자가 현재 보고 있는 단지: 논현동부센트레빌 (id: {APARTMENT_ID})"

# 1~9는 목록 번호("1. 등기부 확인")와 구분이 안 된다. 전세 관련 수치는 모두 두 자리 이상이라
# 여기서 잘라내면 오탐이 거의 사라진다.
# ponytail: 한 자리 수는 검사 못 함. 한 자리가 중요한 지표가 생기면 그때 라벨 기반으로 바꿀 것.
MIN_CHECKED = 10

# 판정을 뒤집을 때 나오는 표현. llama3.1:8b가 62.7%를 두고 실제로 쓴 문장에서 뽑았다.
INVERSION_PHRASES = ["80%를 넘는", "80%를 초과", "기준을 넘어", "깡통주택입니다", "깡통주택으로 분류"]


def _numbers(text: str) -> set[str]:
    """비교 가능한 형태의 숫자 집합. 쉼표를 지우고 '2억 7,248만원'을 만원 단위로 편다."""
    found: set[str] = set()

    # "2억 7,248만원" -> 27248. 도구는 만원 단위 정수로 주는데 모델은 억으로 풀어 쓴다.
    for eok, man in re.findall(r"(\d+)\s*억\s*([\d,]*)\s*만?원?", text):
        rest = int(man.replace(",", "") or 0)
        found.add(str(int(eok) * 10000 + rest))

    for raw in re.findall(r"\d[\d,]*(?:\.\d+)?", text):
        value = raw.replace(",", "")
        number = float(value)
        if number < MIN_CHECKED:
            continue
        # 62.7과 62.70을 같게 본다. 정수는 소수점을 떼서 27248.0이 아니라 27248로 남긴다.
        found.add(str(int(number)) if number == int(number) else str(number))
    return found


def grounded_numbers(trace: list[dict]) -> set[str]:
    """모델이 실제로 본 근거를 재구성한다.

    도구는 로컬 데이터를 읽기만 하는 순수 함수라 toolTrace의 (이름, 인자)로 같은 값을
    다시 만들 수 있다. 그래서 응답 payload에 도구 출력을 실어 보낼 필요가 없다.
    시스템 프롬프트도 근거에 넣는다 — HUG 80% 기준은 거기에 있다.
    """
    # 화면 맥락도 근거다. 모델이 단지 id를 되읊는 건 지어낸 게 아니다.
    grounded = _numbers(SYSTEM_PROMPT + agent_ollama.SYSTEM_SUFFIX + CONTEXT)
    for call in trace:
        grounded |= _numbers(_run_tool(call["name"], call.get("input") or {}))
    return grounded


CASES = [
    {
        "name": "깡통 판정",
        "question": "논현동부센트레빌 깡통주택이야?",
        "tools": ["jeonse_safeguard"],
        "must": ["62.7"],
        "must_not": INVERSION_PHRASES,
    },
    {
        "name": "전세 시세·위험점수",
        "question": "이 단지 전세 시세랑 위험 점수 알려줘",
        "tools": ["apartment_snapshot"],
        # 리터럴로 찾으면 안 된다. 도구는 27248을 주지만 모델은 "2억 7,248만원"으로 푼다.
        "must_numbers": ["27248", "50"],
    },
    {
        "name": "대항력·특약 (도구 호출 유도)",
        "question": "대항력이 언제 생겨? 계약서에 넣을 특약도 알려줘",
        "tools": ["jeonse_safeguard"],
        "must": ["특약"],
    },
    {
        "name": "계약 체크리스트",
        "question": "계약 전에 뭘 확인해야 해?",
        "tools": ["jeonse_safeguard", "contract_checklist"],
        "any_tool": True,
    },
    {
        "name": "더 안전한 대안",
        "question": "여기보다 전세 위험이 낮은 단지 있어?",
        "tools": ["safer_alternatives"],
    },
    {
        "name": "검색 불가 제도 (지어내면 안 됨)",
        "question": "전세보증금반환보증 가입 요건이 올해 어떻게 바뀌었어?",
        "must_any": ["확인", "문의", "어렵"],
    },
]


def check(case: dict) -> tuple[bool, list[str], float]:
    started = time.time()
    result = agent_ollama.agent_chat(
        [{"role": "user", "content": case["question"]}], context=CONTEXT
    )
    elapsed = time.time() - started

    if not result.get("ok"):
        return False, [f"호출 실패: {result.get('error')}"], elapsed

    answer = result.get("answer") or ""
    trace = result.get("toolTrace") or []
    called = [call["name"] for call in trace]
    problems: list[str] = []

    expected = case.get("tools") or []
    if expected:
        hit = [name for name in expected if name in called]
        if case.get("any_tool"):
            if not hit:
                problems.append(f"도구 미호출: {expected} 중 하나도 안 부름 (부른 것: {called or '없음'})")
        else:
            missing = [name for name in expected if name not in called]
            if missing:
                problems.append(f"도구 미호출: {missing} (부른 것: {called or '없음'})")

    for needle in case.get("must") or []:
        if needle not in answer:
            problems.append(f"필수 문자열 누락: {needle!r}")

    # 숫자는 표기가 갈리므로(27248 / 27,248 / 2억 7,248만원) 정규화한 뒤 본다.
    said = _numbers(answer)
    for needle in case.get("must_numbers") or []:
        if needle not in said:
            problems.append(f"필수 수치 누락: {needle} (답변 속 수치: {sorted(said)})")

    for needle in case.get("must_not") or []:
        if needle in answer:
            problems.append(f"금지 표현 등장(판정 반전 의심): {needle!r}")

    alternatives = case.get("must_any") or []
    if alternatives and not any(needle in answer for needle in alternatives):
        problems.append(f"{alternatives} 중 아무것도 없음 — 지어냈을 가능성")

    # 핵심 검사: 답변의 모든 숫자가 도구 결과나 시스템 프롬프트에 실재하는가.
    ungrounded = sorted(_numbers(answer) - grounded_numbers(trace))
    if ungrounded:
        problems.append(f"근거 없는 숫자: {ungrounded}")

    return not problems, problems, elapsed


def main() -> int:
    state = agent_ollama.availability()
    if not state["available"]:
        print(f"건너뜀: {state['reason']}")
        return 0

    print(f"모델: {state['model']}  (num_ctx={agent_ollama.NUM_CTX}, temp={agent_ollama.TEMPERATURE})\n")
    failed = 0
    for case in CASES:
        ok, problems, elapsed = check(case)
        print(f"[{'PASS' if ok else 'FAIL'}] {case['name']} ({elapsed:.0f}s)")
        for problem in problems:
            print(f"       - {problem}")
        failed += 0 if ok else 1

    total = len(CASES)
    print(f"\n{total - failed}/{total} 통과")
    if failed:
        print("이 모델은 도구 결과를 정확히 옮기지 못합니다. 기본값으로 쓰지 마세요.")
    return 1 if failed else 0


if __name__ == "__main__":
    # 검사기 자체가 틀리면 평가 전체가 무의미하므로 먼저 확인한다.
    assert _numbers("전세가율 62.7%입니다") == {"62.7"}
    assert "27248" in _numbers("전세는 2억 7,248만원")
    assert _numbers("1. 첫째 2. 둘째") == set(), "목록 번호는 걸러야 한다"
    assert _numbers("근저당 7,523만원") == {"7523"}
    assert "59" in _numbers("전세가율은 59.0%") and "62.7" not in _numbers("전세가율은 59.0%")

    sys.exit(main())
