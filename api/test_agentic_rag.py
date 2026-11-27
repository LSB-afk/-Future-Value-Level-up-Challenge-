"""③ Agentic RAG: 질문 분해·유형 재작성·하위 질문 근거 확보·조회 계획 기록."""
import unittest

import jeonse_knowledge as kb
from agent_llm import build_system, knowledge_trace


class AgenticRagTests(unittest.TestCase):
    def test_plan_splits_clauses_and_tags_intents(self):
        plan = kb.plan_query("다가구 원룸인데 근저당은 적어요. 선순위 보증금은 어떻게 확인하고 보증보험은 돼요?")
        self.assertGreaterEqual(len(plan["subQueries"]), 2)
        self.assertIn("요건", plan["intents"])
        self.assertEqual(kb.plan_query("전세가율이 뭐예요?")["subQueries"], [])
        self.assertIn("정의", kb.plan_query("전세가율이 뭐예요?")["intents"])

    def test_each_strong_subquery_gets_evidence(self):
        q = "계약 후 등기 변동을 알림으로 받고 싶고, 전입신고는 언제 해야 대항력이 생겨요?"
        slugs = {h["slug"] for h in kb.search_agentic(q)}
        self.assertIn("post-contract-registry-alert-and-lease-registration", slugs)
        self.assertIn("post-contract-resident-date-and-lease-report", slugs)

    def test_single_topic_keeps_depth_multi_topic_spreads(self):
        # 단일 주제 질문은 노트당 두 조각까지(깊이), 복합 질문은 노트당 한 조각 먼저(폭).
        single = kb.search_agentic("등기부 볼 때 갑구 을구에서 뭘 확인해야 해요")
        self.assertLessEqual(max(sum(h["slug"] == s for h in single) for s in {h["slug"] for h in single}), 2)
        multi = kb.search_agentic("신탁 등기가 있고 집주인 대리인이 나왔어요. 뭘 확인해야 해요?")
        slugs = [h["slug"] for h in multi]
        self.assertEqual(len(slugs), len(set(slugs)))

    def test_one_chunk_per_note_before_repeats_and_k_respected(self):
        hits = kb.search_agentic("신탁 등기가 있고 집주인 대리인이 나왔어요. 뭘 확인해야 해요?", k=4)
        self.assertLessEqual(len(hits), 4)
        slugs = [h["slug"] for h in hits]
        self.assertEqual(len(slugs), len(set(slugs)))
        self.assertTrue(all(h.get("matchedBy") for h in hits))

    def test_intent_words_do_not_trigger_synonym_topics(self):
        # '정의' 유형 단어가 동의어 사전(예: '차이')을 켜서 엉뚱한 주제를 끌어오지 않는다.
        self.assertNotIn("차이", " ".join(words for _, _, words in kb.INTENTS))

    def test_empty_and_noise_queries(self):
        self.assertEqual(kb.search_agentic(""), [])
        self.assertEqual(kb.search_agentic("ㅋㅋㅋ"), [])

    def test_agent_uses_agentic_hits_and_records_plan(self):
        messages = [{"role": "user", "content": "집주인 체납도 걱정되고 경매 넘어가면 소액임차인으로 얼마나 받는지도 궁금해요"}]
        system, hits = build_system("", messages)
        self.assertIn("[K1]", system)
        plan = knowledge_trace(messages, hits)
        from agent_llm import RAG_DEFAULT
        self.assertEqual(plan["method"], RAG_DEFAULT)
        self.assertEqual(len(plan["found"]), len(hits))
        self.assertGreaterEqual(len(plan["subQueries"]), 2)


class GraphHybridTests(unittest.TestCase):
    def test_graph_is_built_and_boost_keeps_lexical_support(self):
        graph = kb._index()["meta"].get("graph") or {}
        self.assertTrue(graph and all(graph.values()))
        from collections import Counter
        fused = Counter({0: 1.0})
        boosted = kb.graph_boost(fused)
        self.assertEqual(set(boosted), {0})  # 글자로 안 걸린 조각은 추가하지 않는다
        self.assertGreaterEqual(boosted[0], fused[0])

    def test_hybrid_falls_back_to_graph_without_embeddings(self):
        from unittest.mock import patch
        q = "다가구 원룸인데 근저당은 적어요. 선순위 보증금은 어떻게 확인하고 보증보험은 돼요?"
        with patch.object(kb, "embed", return_value=None):
            kb._embed_cached.cache_clear()
            self.assertEqual([h["id"] for h in kb.search_hybrid(q)], [h["id"] for h in kb.search_graph(q)])
        kb._embed_cached.cache_clear()

    def test_hybrid_dense_lane_can_add_meaning_matches(self):
        dense = kb._dense_index()
        if dense is None:
            self.skipTest("임베딩 파일 없음")
        idx = kb._index()["chunks"]
        target = next(i for i, c in enumerate(idx) if c["slug"] == "jeonse-ratio")
        vector = dense["vectors"][target]
        hits = kb.search_hybrid("전세가율이 뭐예요?", query_vectors=[vector])
        self.assertIn("jeonse-ratio", [h["slug"] for h in hits])
        self.assertTrue(any(h["matchedBy"].startswith("의미") or h["slug"] == "jeonse-ratio" for h in hits))

    def test_stale_embeddings_are_ignored(self):
        from unittest.mock import patch
        kb._dense_index.cache_clear()
        with patch.object(kb, "_corpus_signature", return_value="다른 코퍼스"):
            self.assertIsNone(kb._dense_index())
        kb._dense_index.cache_clear()


if __name__ == "__main__":
    unittest.main()
