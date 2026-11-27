#!/usr/bin/env python3
"""전세 지식 RAG 검색 벤치마크. 검색 방식별 Recall@k·MRR·복합 질문 완전 정답률을 잰다.

    python3 api/eval_rag_retrieval.py            # 쓸 수 있는 방식 전부
    python3 api/eval_rag_retrieval.py --json out.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BENCH = HERE / "rag_benchmark.json"


def methods() -> dict:
    import jeonse_knowledge as kb

    found = {"bm25": lambda q, k: kb.search(q, k=k)}
    for name in ("search_agentic", "search_graph", "search_hybrid"):
        fn = getattr(kb, name, None)
        if fn is not None:
            found[name.replace("search_", "")] = lambda q, k, fn=fn: fn(q, k=k)
    return found


def score(search, items: list[dict], k: int = 4) -> dict:
    recall, rr, full_multi, multi = 0.0, 0.0, 0, 0
    misses = []
    for item in items:
        hits = search(item["q"], k)
        slugs = [h["slug"] for h in hits]
        gold = item["gold"]
        got = [g for g in gold if g in slugs]
        recall += len(got) / len(gold)
        first = next((i for i, s in enumerate(slugs) if s in gold), None)
        rr += 1 / (first + 1) if first is not None else 0
        if item.get("multi"):
            multi += 1
            full_multi += len(got) == len(gold)
        if len(got) < len(gold):
            misses.append({"q": item["q"], "missing": [g for g in gold if g not in slugs], "got": slugs})
    n = len(items)
    return {"recall@%d" % k: round(recall / n, 3), "mrr": round(rr / n, 3),
            "multiFull": f"{full_multi}/{multi}", "misses": misses}


def main() -> int:
    bench = json.loads(BENCH.read_text(encoding="utf-8"))
    report = {}
    for split in ("items", "heldout"):
        for name, fn in methods().items():
            r = score(fn, bench[split])
            report[f"{split}:{name}"] = r
            label = "개발용" if split == "items" else "검증용"
            print(f"{label} {name:9} Recall@4 {r['recall@4']:.3f}  MRR {r['mrr']:.3f}  복합 질문 완전 정답 {r['multiFull']}  놓친 질문 {len(r['misses'])}")
    if "--json" in sys.argv:
        Path(sys.argv[sys.argv.index("--json") + 1]).write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
