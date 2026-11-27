#!/usr/bin/env python3
"""전세사기 지식 RAG: 검증된 근거 조각을 찾아 Agent에게 출처와 함께 넘긴다.

코퍼스는 data/jeonse_knowledge.json이다. 팀 위키의 verified 노트만 담고, 조각마다 출처 URL과
"확인 못 한 부분"(caveat)이 붙어 있다. 만드는 스크립트는 작업공간의 orchestra/build_jeonse_corpus.py.

검색은 의존성 없는 BM25다. 한국어는 형태소 분석기 없이도 글자 2-gram이 잘 맞고, 결과가 결정적이라
평가를 다시 돌려도 같은 조각이 나온다. 임베딩 모델이 없어도 돌아가야 정적 데모·로컬 Ollama 모두에서 쓸 수 있다.
"""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from functools import lru_cache
from pathlib import Path

CORPUS_PATH = Path(__file__).resolve().parents[1] / "data" / "jeonse_knowledge.json"

# 사용자 말과 노트 표현이 다른 경우를 잇는다. 왼쪽이 질문에 나오면 오른쪽 말도 함께 찾는다.
EXPANSIONS = {
    "깡통": "깡통전세 전세가율 집값 대비 보증금",
    "근생": "근린생활시설 건축물대장 용도",
    "근린생활": "근린생활시설 건축물대장 용도 주거용 반환보증 제외",
    "상가주택": "근린생활시설 건축물대장 용도 위반건축물",
    "불법건축": "위반건축물 건축물대장",
    "대리인": "위임장 인감증명서 소유자 이중계약",
    "가족": "위임장 인감증명서 소유자",
    "이름이": "소유자 등기부 갑구 신분증",
    "소액임차": "최우선변제 소액임차인 시행령",
    "최우선": "최우선변제 소액임차인",
    "보증보험": "반환보증 HUG 가입 요건",
    "보증 가입": "반환보증 HUG 가입 요건",
    "감정가": "감정평가 동시진행 시세 부풀리기 실거래",
    "신축": "동시진행 분양 시세 감정가",
    "다가구": "선순위 보증금 확정일자 전입세대 열람",
    "선순위": "선순위 보증금 확정일자 근저당",
    "신탁": "신탁원부 수탁자 동의 갑구",
    "대항력": "전입신고 다음 날 0시 확정일자 잔금",
    "전입": "대항력 전입신고 확정일자",
    "잔금": "잔금 직전 등기부 재열람 대항력",
    "특약": "특약 계약서 근저당 설정 금지",
    "상담": "전세피해 지원센터 상담",
    "피해": "전세사기피해자 특별법 지원센터",
    "중개사": "공인중개사 확인설명 중개대상물",
    "체납": "국세 지방세 체납 납세증명서 임대인 정보 제시 당해세 법정기일",
    "돌려받": "배당 우선변제 확정일자 저당권 순위 임차권등기 지급명령",
    "경매": "배당 우선변제 확정일자 저당권 최우선변제 당해세",
    "순위": "배당 우선변제 확정일자 저당권 등기 순서",
    "세금": "당해세 법정기일 국세 지방세 우선",
    "확정일자": "확정일자 전자확정일자 인터넷등기소 임대차 신고 우선변제",
    "임대차 신고": "주택임대차 신고 부동산거래관리시스템 확정일자",
    "안 돌려": "임차권등기명령 지급명령 분쟁조정위원회 보증금 반환",
    "만기": "임차권등기명령 지급명령 분쟁조정위원회 보증금 반환",
    "HF": "주택금융공사 전세지킴보증",
    "SGI": "서울보증 전세금보장신용보험",
    "위반건축물": "위반건축물 건축물대장 정부24 세움터 반환보증 제외",
    "알림": "등기 알리미 부동산 알리미 인터넷등기소",
    # B010: 매매가·전세가 괴리와 업계·수사로 본 원인
    "차이": "전세가율 부채비율 매매가 부풀림 선순위채권 괴리",
    "매매가": "전세가율 부채비율 매매가 부풀림 감정가",
    "전세가율": "부채비율 사고 구간 보증사고",
    "싸": "미끼 광고 허위매물 저가",
    "저렴": "미끼 광고 허위매물 저가",
    "비싸": "주변 대비 고가 전세 괴리",
    "역전세": "역전세 한국은행 전세가 하락 반환 재원",
    "떨어": "역전세 전세가 하락 반환 재원 다음 세입자",
    "동시진행": "동시진행 리베이트 분양대행 명의 이전 바지 임대인",
    "리베이트": "리베이트 분양대행 동시진행 판결",
    "명의": "명의 이전 바지 임대인 명의대여",
    "왜 생기": "가담 구조 특별단속 감사원 입법조사처 리베이트",
    "원인": "가담 구조 특별단속 감사원 입법조사처 리베이트",
    "중개사가": "공인중개사 가담 특별단속 특별점검 설명의무",
    "감정": "감정평가 부풀리기 감정가 보증 인정가격",
}

STOP = set("은 는 이 가 을 를 에 의 도 와 과 로 으로 하고 해 해요 돼 돼요 요 나 거 게 뭐 어떻게 있어 있어요 괜찮아 괜찮아요".split())


def _norm(text: str) -> str:
    return re.sub(r"[^0-9a-z가-힣%]", " ", str(text or "").lower())


def _grams(text: str) -> list[str]:
    grams: list[str] = []
    for word in _norm(text).split():
        if word in STOP:
            continue
        if len(word) == 1:
            grams.append(word)
            continue
        grams += [word[i:i + 2] for i in range(len(word) - 1)]
    return grams


@lru_cache(maxsize=1)
def _index() -> dict:
    data = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
    chunks = data.get("chunks") or []
    docs = []
    for chunk in chunks:
        # 제목·요약은 조각의 주제를 가장 잘 말하니 두 번 센다.
        field = f"{chunk['title']} {chunk['title']} {chunk.get('summary', '')} {chunk['text']}"
        docs.append(Counter(_grams(field)))
    df = Counter(g for doc in docs for g in doc)
    lengths = [sum(doc.values()) for doc in docs]
    return {
        "meta": data.get("meta") or {},
        "chunks": chunks,
        "docs": docs,
        "df": df,
        "avg": (sum(lengths) / len(lengths)) if lengths else 1.0,
        "lengths": lengths,
    }


def expand(query: str) -> str:
    upper = query.upper()  # "hf"·"sgi"처럼 소문자로 써도 잇는다
    extra = [value for key, value in EXPANSIONS.items() if key in query or (key.isascii() and key in upper)]
    return " ".join([query, *extra])


def _bm25(query: str, min_score: float = 1.0, extra: str = "") -> list[tuple[float, int]]:
    """(점수, 조각 번호)를 점수 순으로. 질문은 동의어 확장 후 글자 2-gram으로 맞춘다.
    extra(질문 유형 단어)는 동의어 확장을 거치지 않는다(유형 단어가 엉뚱한 주제를 켜지 않게)."""
    idx = _index()
    terms = Counter(_grams(expand(query) + " " + extra))
    if not terms:
        return []
    n = len(idx["docs"])
    k1, b = 1.4, 0.7
    scored = []
    for i, doc in enumerate(idx["docs"]):
        score = 0.0
        for term, qtf in terms.items():
            tf = doc.get(term)
            if not tf:
                continue
            idf = math.log(1 + (n - idx["df"][term] + 0.5) / (idx["df"][term] + 0.5))
            score += idf * tf * (k1 + 1) / (tf + k1 * (1 - b + b * idx["lengths"][i] / idx["avg"])) * min(qtf, 3)
        if score >= min_score:
            scored.append((score, i))
    scored.sort(reverse=True)
    return scored


def search(query: str, k: int = 4, min_score: float = 1.0) -> list[dict]:
    """질문과 가까운 근거 조각 k개. 점수가 낮으면 덜 돌려준다(엉뚱한 근거를 주느니 없는 게 낫다)."""
    idx = _index()
    scored = _bm25(query, min_score)
    if not scored:
        return []
    out, seen_slugs = [], Counter()
    for score, i in scored:
        chunk = idx["chunks"][i]
        if seen_slugs[chunk["slug"]] >= 2:  # 한 노트가 결과를 독차지하지 않게
            continue
        seen_slugs[chunk["slug"]] += 1
        out.append({**chunk, "score": round(score, 2)})
        if len(out) >= k:
            break
    return out


# ---------- ③ Agentic RAG: 질문을 나눠 찾고, 합치고, 고르게 고른다 ----------

# 질문 유형(무엇을 묻는가)을 검색어로 바꾼다. 특정 노트가 아니라 질문의 형식에 붙는 일반 규칙이다.
INTENTS = (
    ("정의", re.compile(r"뭐예요|뭔가요|무슨 뜻|뜻이|의미|이란|란 뭐|같은 말"), "정의 의미"),
    ("시점", re.compile(r"언제|시점|다시|한 번만|매번|당일|잔금 날|잔금날|직전|단계"), "시점 단계 재확인 반복 계약 전 잔금"),
    ("경로", re.compile(r"어디서|어디에|어디로|떼|발급|신청|조회|열람|볼 수|확인할 수"), "신청 발급 열람 경로 기관 방법"),
    ("기준", re.compile(r"얼마|몇 ?퍼센트|몇 ?%|한도|기준|비율|이하|이상"), "기준 한도 비율 금액 요건"),
    ("요건", re.compile(r"조건|자격|요건|대상|되나요|돼요\?|가능|할 수 있"), "요건 대상 자격 조건"),
    ("대처", re.compile(r"어떻게 해|어떡|방법|뭐부터|대처|못 받|안 줘|안 돌려"), "대처 절차 방법 순서"),
)
# 절을 나누는 자리: 문장 끝, 접속 부사, '~고/~는데/~지만' 같은 연결 어미 뒤 공백.
CLAUSE_SPLIT = re.compile(r"[?？!.。]\s*|\s+(?:그리고|또|또한|그런데|근데)\s+|(?<=[가-힣])(?:고|는데|은데|지만|면서|며)\s+(?=[가-힣])")
RRF_K = 60
DIVERSITY_FLOOR = 0.5
SUBQUERY_FLOOR = 0.3


def plan_query(question: str) -> dict:
    """질문 → 하위 질문(절)과 질문 유형. 작은 로컬 모델에게 계획을 맡기지 않고 결정적으로 만든다."""
    text = " ".join(str(question or "").split())
    clauses = [c.strip() for c in CLAUSE_SPLIT.split(text) if c and len(c.strip()) >= 6]
    subs = clauses[:3] if len(clauses) > 1 else []
    intents = [name for name, pattern, _ in INTENTS if pattern.search(text)]
    return {"question": text, "subQueries": subs, "intents": intents}


def _intent_words(query: str) -> str:
    return " ".join(words for _, pattern, words in INTENTS if pattern.search(query))


def _fuse(plan: dict, min_score: float) -> tuple[list, Counter, dict, dict]:
    """전체·하위·유형 재작성 질문(lane)별 BM25 순위를 가중 RRF로 합친다."""
    # 전체 질문은 두 주제의 관계까지 담고 있어 가중치를 더 준다.
    lanes: list[tuple[str, str, str, float]] = [("전체", plan["question"], "", 1.5)]
    lanes += [(f"하위{n + 1}", sub, "", 1.0) for n, sub in enumerate(plan["subQueries"])]
    for label, text, _, _ in list(lanes):
        words = _intent_words(text)
        if words:
            lanes.append((label + "·유형", text, words, 0.5))
    fused: Counter = Counter()
    raw: dict[int, float] = {}
    best_per_lane: dict[str, list[int]] = {}
    for label, text, extra, weight in lanes:
        ranked = _bm25(text, min_score, extra)
        best_per_lane[label] = [i for _, i in ranked]
        for rank, (score, i) in enumerate(ranked[:30]):
            fused[i] += weight / (RRF_K + rank + 1)
            raw[i] = max(raw.get(i, 0.0), score)
    return lanes, fused, raw, best_per_lane


def _select(lanes: list, fused: Counter, raw: dict, best_per_lane: dict, k: int) -> list[dict]:
    idx = _index()
    order = [i for i, _ in fused.most_common()]
    chosen: list[int] = []
    matched: dict[int, str] = {}

    def take(i: int, by: str) -> None:
        if i not in chosen and len(chosen) < k:
            chosen.append(i)
            matched[i] = by

    # 1) 하위 질문마다 그 질문의 최상위 노트를 하나씩 확보한다(복합 질문의 두 번째 주제가 밀려나지 않게).
    #    단, 그 하위 질문의 근거가 약하면(전체 1위 점수의 SUBQUERY_FLOOR 미만) 억지로 넣지 않는다.
    taken_slugs: set[str] = set()
    top_raw = max(raw.values())
    for label, *_ in lanes:
        if not label.startswith("하위") or "·" in label:
            continue
        for i in best_per_lane.get(label, []):
            slug = idx["chunks"][i]["slug"]
            if raw[i] < top_raw * SUBQUERY_FLOOR:
                break
            if slug not in taken_slugs:
                take(i, label)
                taken_slugs.add(slug)
                break
    # 2) 합친 순위로 채우되 노트당 한 조각 먼저. 다만 관련도가 1위의 절반이 안 되는 새 노트로 칸을 채우지는 않는다.
    floor = fused[order[0]] * DIVERSITY_FLOOR
    for i in order:
        slug = idx["chunks"][i]["slug"]
        if slug not in taken_slugs and fused[i] >= floor:
            take(i, "합친 순위")
            taken_slugs.add(slug)
    # 3) 칸이 남으면 같은 노트의 다음 조각.
    for i in order:
        take(i, "합친 순위")
    chosen.sort(key=lambda i: -fused[i])
    return [{**idx["chunks"][i], "score": round(raw[i], 2), "matchedBy": matched[i]} for i in chosen]


def search_agentic(query: str, k: int = 4, min_score: float = 1.0, plan: dict | None = None) -> list[dict]:
    """하위 질문별 BM25 순위를 RRF로 합치고, 하위 질문마다 근거가 한 개씩은 들어가게 고른다.

    - 전체 질문, 하위 질문, 질문 유형으로 다시 쓴 질문을 각각 검색한다(유형 재작성은 가중치 0.5).
    - 한 노트는 먼저 한 조각만 고르고, 칸이 남을 때만 같은 노트의 다른 조각을 넣는다.
    - 결과에는 어느 하위 질문으로 찾았는지(matchedBy)를 남겨 trace에서 보여 줄 수 있다."""
    lanes, fused, raw, best = _fuse(plan or plan_query(query), min_score)
    return _select(lanes, fused, raw, best, k) if fused else []


# ---------- ② GraphRAG: 위키 노트 연결로 관련 노트를 함께 끌어올린다 ----------

GRAPH_ALPHA = 0.1
GRAPH_SEEDS = 2


def graph_boost(fused: Counter, alpha: float | None = None, seeds: int | None = None) -> Counter:
    """상위 시드 노트(합친 점수 1~GRAPH_SEEDS위)와 연결된 노트의 조각을 α·(시드 관련도)만큼 올린다.

    시드 관련도는 그 노트 최고 점수를 1위로 나눈 값이고, 이웃 쪽 연결 수의 제곱근으로 나눠 허브 노트가
    연결만으로 올라오지 않게 한다. 글자로 한 번도 걸리지 않은 조각은 올리지 않는다(근거 없는 확장 방지)."""
    alpha = GRAPH_ALPHA if alpha is None else alpha
    seeds = GRAPH_SEEDS if seeds is None else seeds
    idx = _index()
    graph = (idx["meta"] or {}).get("graph") or {}
    if not fused or not graph:
        return fused
    top = max(fused.values())
    note_rel: dict[str, float] = {}
    for i, value in fused.items():
        slug = idx["chunks"][i]["slug"]
        note_rel[slug] = max(note_rel.get(slug, 0.0), value / top)
    seed_rel = dict(sorted(note_rel.items(), key=lambda kv: -kv[1])[:seeds])
    boosted: Counter = Counter()
    for i, value in fused.items():
        slug = idx["chunks"][i]["slug"]
        nbrs = graph.get(slug) or []
        support = sum(seed_rel.get(m, 0.0) for m in nbrs) / math.sqrt(max(len(nbrs), 1))
        boosted[i] = value * (1 + alpha * support)
    return boosted


def search_graph(query: str, k: int = 4, min_score: float = 1.0, plan: dict | None = None) -> list[dict]:
    """③ Agentic 검색 + ② 노트 그래프 보정."""
    lanes, fused, raw, best = _fuse(plan or plan_query(query), min_score)
    return _select(lanes, graph_boost(fused), raw, best, k) if fused else []


# ---------- ① 하이브리드: 글자 검색(BM25) + 의미 검색(bge-m3 임베딩) ----------

EMBED_PATH = CORPUS_PATH.with_name("jeonse_knowledge.embeddings.json")
EMBED_MODEL = "bge-m3"
DENSE_TOP = 10
DENSE_WEIGHT = 1.0


def _corpus_signature(chunks: list[dict]) -> str:
    import hashlib

    return hashlib.sha256("\n".join(f"{c['id']}\t{c['text']}" for c in chunks).encode()).hexdigest()[:16]


@lru_cache(maxsize=1)
def _dense_index() -> dict | None:
    """미리 계산한 조각 임베딩. 파일이 없거나 코퍼스와 어긋나면 None(→ 글자 검색만)."""
    try:
        data = json.loads(EMBED_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    chunks = _index()["chunks"]
    if data.get("signature") != _corpus_signature(chunks) or len(data.get("vectors") or []) != len(chunks):
        return None
    return data


def embed(texts: list[str], timeout: float | None = None) -> list[list[float]] | None:
    """Ollama /api/embed. 쓸 수 없으면(정적 데모·서버 꺼짐·모델 없음·시간 초과) None.
    기다리는 시간은 FITHOME_EMBED_TIMEOUT(초, 기본 6). 답변을 오래 붙잡지 않으려고 짧게 둔다."""
    import os
    import urllib.request

    if timeout is None:
        try:
            timeout = float(os.environ.get("FITHOME_EMBED_TIMEOUT") or 6)
        except ValueError:
            timeout = 6.0
    host = os.environ.get("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
    body = json.dumps({"model": EMBED_MODEL, "input": texts}).encode()
    try:
        request = urllib.request.Request(host + "/api/embed", body, {"Content-Type": "application/json"})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            vectors = json.load(response).get("embeddings")
    except Exception:  # noqa: BLE001 - 의미 검색은 보조다. 실패하면 글자 검색으로 간다.
        return None
    return vectors if isinstance(vectors, list) and len(vectors) == len(texts) else None


@lru_cache(maxsize=256)
def _embed_cached(texts: tuple[str, ...]) -> list[list[float]] | None:
    return embed(list(texts))


def _unit(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(x * x for x in vector)) or 1.0
    return [x / norm for x in vector]


def search_hybrid(query: str, k: int = 4, min_score: float = 1.0, plan: dict | None = None,
                  query_vectors: list[list[float]] | None = None) -> list[dict]:
    """③+② 위에 의미 검색 순위를 RRF로 더한다. 임베딩을 쓸 수 없으면 search_graph와 같다.

    전체 질문과 하위 질문을 한 번에 임베딩해 각각 상위 DENSE_TOP 조각을 '의미' lane으로 넣는다.
    글자로는 안 걸려도 뜻이 가까운 조각(예: '전세가율이 뭐예요' → 전세가율 정의 노트)을 끌어온다."""
    plan = plan or plan_query(query)
    lanes, fused, raw, best = _fuse(plan, min_score)
    dense = _dense_index()
    texts = [plan["question"], *plan["subQueries"]]
    vectors = query_vectors if query_vectors is not None else (_embed_cached(tuple(texts)) if dense and plan["question"] else None)
    if dense and vectors:
        matrix = dense["vectors"]
        for n, vector in enumerate(vectors):
            q = _unit(vector)
            sims = sorted(((sum(a * b for a, b in zip(q, row)), i) for i, row in enumerate(matrix)), reverse=True)
            label = "의미" if n == 0 else f"의미{n}"
            weight = DENSE_WEIGHT * (1.5 if n == 0 else 1.0)
            lanes.append((label, texts[n], "", weight))
            best[label] = [i for _, i in sims]
            for rank, (_, i) in enumerate(sims[:DENSE_TOP]):
                fused[i] += weight / (RRF_K + rank + 1)
                raw.setdefault(i, 0.0)
    return _select(lanes, graph_boost(fused), raw, best, k) if fused else []


def as_context(hits: list[dict]) -> str:
    """시스템 프롬프트에 넣는 형태. [K1] 번호로 인용하게 한다."""
    if not hits:
        return ""
    blocks = []
    for n, hit in enumerate(hits, 1):
        urls = ", ".join(s["url"] for s in hit["sources"][:2])
        caveat = f"\n  (확인 못 한 부분: {hit['caveat']})" if hit.get("caveat") else ""
        blocks.append(f"[K{n}] {hit['title']} (기준일 {hit.get('date') or '미상'})\n{hit['text']}\n  출처: {urls}{caveat}")
    return "\n\n".join(blocks)


def cited_sources(answer: str, hits: list[dict]) -> list[dict]:
    """답에 [K번호]로 인용된 조각의 출처만 화면에 보낸다."""
    used = {int(n) for n in re.findall(r"\[K(\d+)\]", answer or "")}
    sources: list[dict] = []
    for n, hit in enumerate(hits, 1):
        if n not in used:
            continue
        for source in hit["sources"][:2]:
            if all(s["url"] != source["url"] for s in sources):
                sources.append({"url": source["url"], "title": f"[K{n}] {source.get('title') or hit['title']}"})
    return sources


def tool_search_jeonse_knowledge(query: str, k: int = 4) -> str:
    """Agent 도구용. 조각과 출처를 JSON으로 돌려준다."""
    hits = search_agentic(str(query), k=max(1, min(int(k or 4), 6)))
    return json.dumps(
        {
            "query": query,
            "results": [
                {"title": h["title"], "text": h["text"], "sources": h["sources"][:2], "caveat": h.get("caveat", ""), "date": h.get("date")}
                for h in hits
            ],
            "rule": "이 결과의 문장만 근거로 쓰고 출처 URL을 밝히세요. 결과가 비었으면 확인된 자료가 없다고 말하세요.",
        },
        ensure_ascii=False,
    )


if __name__ == "__main__":
    meta = _index()["meta"]
    assert meta.get("chunks", 0) >= 20, meta
    expect = {
        "등기부 갑구에 신탁 있어요": "jeonse-trust-property-authority-check",
        "다가구 선순위 보증금이 3억이래요": "jeonse-multifamily-hidden-prior-deposits",
        "서울 보증금 6천만 원 소액임차인 최우선변제": "small-tenant-priority-payment-current",
        "HUG 보증 가입 요건": "hug-jeonse-guarantee",
        "근린생활시설 전입신고": "jeonse-illegal-use-building-check",
        "대리인과 계약 위임장": "jeonse-double-contract-fake-landlord",
        "잔금일 전입신고 대항력": "jeonse-stage-rechecks-opposability-gap",
        "경매 넘어가면 보증금 돌려받는 순서": "auction-tenant-priority-versus-registered-security",
        "집주인 세금 체납 당해세": "auction-housing-tax-priority-substitution",
        "만기인데 보증금을 안 돌려줘요": "post-contract-registry-alert-and-lease-registration",
        "HF 전세지킴보증 한도": "hf-jeonse-jikim-loan-linked-eligibility",
        "위반건축물이면 보증보험 안 돼?": "building-ledger-guarantee-and-loan-restrictions",
        "임대차 신고하면 확정일자": "post-contract-resident-date-and-lease-report",
        "매매가랑 전세가 차이가 크면 안전해?": "jeonse-price-gap-risk-map",
        "전세가율 몇 퍼센트부터 사고가 많아?": "jeonse-price-gap-risk-map",  # 구간별 사고 비율 표가 있는 정리 노트
        "전세사기는 왜 생기는 거야? 중개사가 가담해?": "jeonse-fraud-insider-structure",
        "주변보다 전세가 너무 싸요": "jeonse-cheap-listing-bait-evidence",
    }
    # 근생 질문은 근생 수법 노트나 보증 제한 노트 어느 쪽이 먼저 와도 맞다.
    alternatives = {"jeonse-illegal-use-building-check": {"building-ledger-guarantee-and-loan-restrictions"}}
    for query, slug in expect.items():
        top = [h["slug"] for h in search(query, k=3)]
        assert slug in top or alternatives.get(slug, set()) & set(top), (query, top)
    assert search("ㅋㅋㅋ") == []
    hits = search("신탁 계약해도 돼?")
    assert hits and "출처:" in as_context(hits)
    assert cited_sources("수탁자 동의가 필요합니다 [K1]", hits) and not cited_sources("인용 없음", hits)
    print(f"jeonse_knowledge self-check OK ({meta['chunks']} chunks)")
