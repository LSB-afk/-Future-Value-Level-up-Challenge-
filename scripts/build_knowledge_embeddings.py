#!/usr/bin/env python3
"""전세 지식 코퍼스 조각을 bge-m3(Ollama)로 임베딩해 data/jeonse_knowledge.embeddings.json에 저장한다.

    python3 scripts/build_knowledge_embeddings.py

코퍼스(data/jeonse_knowledge.json)를 다시 만들면 이 스크립트도 다시 돌린다. 서명이 어긋난 임베딩은
검색이 쓰지 않는다(jeonse_knowledge._dense_index).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "api"))

from env_loader import load_dotenv  # noqa: E402

load_dotenv()

import jeonse_knowledge as kb  # noqa: E402


def main() -> int:
    chunks = kb._index()["chunks"]
    texts = [f"{c['title']}\n{c.get('summary', '')}\n{c['text']}" for c in chunks]
    vectors: list[list[float]] = []
    for start in range(0, len(texts), 16):
        batch = kb.embed(texts[start:start + 16], timeout=120)
        if batch is None:
            print("임베딩 실패: OLLAMA_HOST와 bge-m3 모델을 확인하세요.", file=sys.stderr)
            return 1
        vectors += [[round(x, 5) for x in kb._unit(v)] for v in batch]
    kb.EMBED_PATH.write_text(json.dumps({
        "model": kb.EMBED_MODEL,
        "signature": kb._corpus_signature(chunks),
        "dims": len(vectors[0]),
        "ids": [c["id"] for c in chunks],
        "vectors": vectors,
    }), encoding="utf-8")
    print(f"조각 {len(vectors)}개 × {len(vectors[0])}차원 → {kb.EMBED_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
