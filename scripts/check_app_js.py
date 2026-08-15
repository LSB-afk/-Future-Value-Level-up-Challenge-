#!/usr/bin/env python3
"""Fail on duplicate declarations in app/app.js.

app.js is a single 5,000줄 파일이라 브랜치 병합에서 같은 이름이 두 번 선언되기 쉽다.
JS는 이 경우 뒤에 온 쪽이 조용히 이기므로 구문 검사(node --check)로는 잡히지 않는다.
실제로 병합 59caf61이 state에 agent 키를 중복 선언해, state.agent.llmMode가 null이
아니라 undefined가 되면서 agentLlmAvailable()이 /api/agent-status를 한 번도 호출하지
않고 에이전트가 항상 규칙 기반으로 답하는 버그가 사흘간 남아 있었다.

    python3 scripts/check_app_js.py
"""

from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP_JS = ROOT / "app" / "app.js"


def state_literal(source: str) -> str:
    """const state = { ... }; 본문만 중괄호 깊이로 잘라낸다."""
    start = source.index("const state = {")
    depth = 0
    for index in range(start, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[start : index + 1]
    raise ValueError("const state = { ... } 블록이 닫히지 않았습니다.")


def duplicate_state_keys(source: str) -> list[str]:
    """state 최상위 키만 본다. 들여쓰기 2칸이 곧 최상위 깊이다."""
    keys = re.findall(r"^  ([A-Za-z_$][\w$]*):", state_literal(source), re.MULTILINE)
    return sorted(name for name, count in Counter(keys).items() if count > 1)


def duplicate_functions(source: str) -> list[str]:
    names = re.findall(r"^(?:async )?function ([A-Za-z_$][\w$]*)", source, re.MULTILINE)
    return sorted(name for name, count in Counter(names).items() if count > 1)


def main() -> int:
    source = APP_JS.read_text(encoding="utf-8")
    failures = []

    duplicate_keys = duplicate_state_keys(source)
    if duplicate_keys:
        failures.append(f"state 중복 키: {', '.join(duplicate_keys)}")

    duplicate_names = duplicate_functions(source)
    if duplicate_names:
        failures.append(f"중복 함수 정의: {', '.join(duplicate_names)}")

    for failure in failures:
        print(f"FAIL {failure}")
    if failures:
        print("\n뒤에 선언된 쪽이 이깁니다. 병합에서 남은 중복인지 확인하세요.")
        return 1

    print("OK app/app.js 중복 선언 없음")
    return 0


def demo() -> None:
    """검사기가 실제로 중복을 잡는지 확인한다."""
    broken = "const state = {\n  agent: {\n    a: 1\n  },\n  agent: {\n    b: 2\n  }\n};\n"
    assert duplicate_state_keys(broken) == ["agent"], duplicate_state_keys(broken)
    assert duplicate_functions("function f() {}\nfunction f() {}\n") == ["f"]

    clean = "const state = {\n  agent: {\n    agent: 1\n  },\n  bookmarks: {\n    b: 2\n  }\n};\n"
    assert duplicate_state_keys(clean) == [], duplicate_state_keys(clean)
    assert duplicate_functions("function f() {}\nasync function g() {}\n") == []
    print("demo OK")


if __name__ == "__main__":
    if "--demo" in sys.argv:
        demo()
    else:
        raise SystemExit(main())
