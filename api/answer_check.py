"""④ 교정형 RAG: 답을 내보내기 전에 근거와 대조한다.

1. 인용 대조: [K번호]를 단 문장이 그 근거 조각과 글자 2-gram으로 충분히 겹치는지 본다. 겹치지 않으면
   인용 번호를 떼어 '근거가 있는 것처럼' 보이지 않게 한다(문장은 남긴다).
2. 숫자 대조: 근거(시스템 프롬프트·근거 조각·도구 결과·질문)에 없는 10 이상의 숫자가 든 문장은 뺀다.
   작은 모델이 금액·비율·기간을 지어내는 경로를 막는다.
결과에는 무엇을 고쳤는지 남겨 응답의 guard에 싣는다.
"""
from __future__ import annotations

import re

from jeonse_knowledge import _grams

MIN_CHECKED = 10
CITE_FLOOR = 0.25
CITE_RE = re.compile(r"\[K(\d+)\]")
SENTENCE_SPLIT = re.compile(r"(?<=[.!?。])\s+|\n+")
DROPPED_NOTE = "\n\n※ 근거에서 확인되지 않은 숫자가 든 문장은 뺐습니다. 금액·비율은 서류나 기관 안내로 확인하세요."


def numbers(text: str) -> set[str]:
    """비교 가능한 형태의 숫자 집합. 쉼표를 지우고 '2억 7,248만원'을 만원 단위로 편다."""
    found: set[str] = set()
    for eok, man in re.findall(r"(\d+)\s*억\s*([\d,]*)\s*만?원?", text or ""):
        found.add(str(int(eok) * 10000 + int(man.replace(",", "") or 0)))
    for raw in re.findall(r"\d[\d,]*(?:\.\d+)?", text or ""):
        value = float(raw.replace(",", ""))
        if value < MIN_CHECKED:
            continue
        found.add(str(int(value)) if value == int(value) else str(value))
    return found


def _support(sentence: str, chunk: dict) -> float:
    words = set(_grams(CITE_RE.sub("", sentence)))
    if not words:
        return 1.0
    source = set(_grams(f"{chunk.get('title', '')} {chunk.get('summary', '')} {chunk.get('text', '')}"))
    return len(words & source) / len(words)


def correct_answer(answer: str, hits: list[dict], grounding: str) -> tuple[str, dict]:
    """(고친 답, 보고). grounding에는 모델이 실제로 본 글(시스템 프롬프트·질문·도구 결과)을 모두 넣는다."""
    grounded = numbers(grounding) | numbers(" ".join(h.get("text", "") for h in hits))
    report = {"uncitedMarkers": [], "droppedSentences": []}
    kept: list[str] = []
    for sentence in SENTENCE_SPLIT.split(answer or ""):
        if not sentence.strip():
            continue
        loose = sorted(numbers(CITE_RE.sub("", sentence)) - grounded)
        if loose:
            report["droppedSentences"].append({"sentence": sentence.strip()[:120], "numbers": loose})
            continue
        for marker in set(CITE_RE.findall(sentence)):
            n = int(marker)
            if not 1 <= n <= len(hits) or _support(sentence, hits[n - 1]) < CITE_FLOOR:
                sentence = sentence.replace(f"[K{marker}]", "")
                report["uncitedMarkers"].append(f"K{marker}")
        kept.append(sentence.strip())
    fixed = "\n".join(kept).strip()
    if report["droppedSentences"]:
        fixed += DROPPED_NOTE
    return fixed, report


if __name__ == "__main__":
    hits = [{"title": "임차권등기명령", "summary": "", "text": "보증금을 돌려받지 못하면 임차권등기명령을 신청해 대항력을 유지한다."}]
    text, rep = correct_answer(
        "보증금을 못 받으면 임차권등기명령을 신청해 대항력을 유지할 수 있어요 [K1]. 신청 비용은 35000원이에요. 날씨가 좋네요 [K1].",
        hits, "질문: 보증금을 못 받았어요")
    assert "35000" not in text and rep["droppedSentences"], rep
    assert "대항력을 유지할 수 있어요 [K1]" in text and rep["uncitedMarkers"] == ["K1"], (text, rep)
    assert numbers("2억 7,248만원") >= {"27248"}
    assert correct_answer("", [], "")[0] == ""
    print("answer_check self-check OK")
