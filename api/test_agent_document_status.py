"""AI Agent의 document_status 도구: 서버가 가진 서류 근거만 읽고, 토큰은 모델 입력·응답에 나가지 않는다."""

import http.client
import json
import os
import sys
import tempfile
import threading
import types
import unittest
import urllib.request
from datetime import date, timedelta
from http.server import ThreadingHTTPServer
from unittest.mock import patch

import agent_llm
import agent_ollama
import document_requests
import evidence_store

ADDRESS = "서울특별시 성동구 왕십리로 137 101동 1001호"
TODAY = date.today().isoformat()


def reading(**overrides):
    return {"address": ADDRESS, "issuedAt": TODAY, "mortgageMax10k": 12000, "reviewRequired": False,
            "source": "uploaded_pdf", **overrides}


def status(report_state):
    result = json.loads(agent_llm._run_tool("document_status", {}, report_state))
    return result, {row["item"]: row for row in result["items"]}


REGISTRY = "등기부 을구 근저당(채권최고액)"
PRIOR = "선순위 임차보증금(확정일자 자료)"
TAX = "임대인 납세증명서"


class DocumentStatusTests(unittest.TestCase):
    def setUp(self):
        store = tempfile.TemporaryDirectory()
        self.addCleanup(store.cleanup)
        env = patch.dict(os.environ, {"FITHOME_DOCUMENT_STORE": store.name})
        env.start()
        self.addCleanup(env.stop)

    def owner_with_prior(self, amount10k=35000, issued=TODAY):
        created = document_requests.create_request({"address": ADDRESS, "requested": ["fixedDate", "nationalTax"]})
        detail = {"kind": "fixedDate", "status": "confirmed", "amount10k": amount10k, "issuedAt": issued,
                  "expiresOn": None, "issues": [], "fingerprint": "f" * 64, "landlordName": "홍길동"}
        with document_requests._db() as conn, conn:
            row = conn.execute("SELECT id FROM requests").fetchone()
            conn.execute("INSERT INTO documents VALUES (?,?,?,?)", (row[0], "fixedDate", "f" * 64, json.dumps(detail)))
        return created["ownerToken"]

    # --- 등기 근거: 없음 / 있음 / 다른 주소 / 만료 ---

    def test_no_registry_evidence_is_unknown(self):
        result, items = status({"address": ADDRESS, "housingType": "apartment"})
        self.assertTrue(result["reportOpen"])
        self.assertEqual(items[REGISTRY]["status"], "미확인")
        self.assertIn("대조한 등기부가 없습니다", items[REGISTRY]["reason"])
        self.assertNotIn("amount10k", items[REGISTRY])

    def test_registry_evidence_returns_server_values_and_basis_date(self):
        token = evidence_store.issue_registry(reading(), "a" * 64)
        _, items = status({"address": ADDRESS, "registryEvidenceId": token})
        row = items[REGISTRY]
        self.assertEqual(row["status"], "서류 확인")
        self.assertEqual(row["basisDate"], TODAY)
        self.assertEqual(row["amount10k"], 12000)
        self.assertEqual(row["amountLabel"], "1억 2,000만원")
        self.assertIn("진위 미확인", row["source"])

    def test_registry_evidence_for_another_address_is_rejected(self):
        token = evidence_store.issue_registry(reading(), "a" * 64)
        _, items = status({"address": "서울특별시 성동구 왕십리로 137 101동 1002호", "registryEvidenceId": token})
        self.assertEqual(items[REGISTRY]["status"], "미확인")
        self.assertIn("다른 주소", items[REGISTRY]["reason"])
        self.assertNotIn("amount10k", items[REGISTRY])

    def test_expired_registry_evidence_is_unknown(self):
        with patch.object(evidence_store, "LIFETIME_SECONDS", -10):
            token = evidence_store.issue_registry(reading(), "a" * 64)
        _, items = status({"address": ADDRESS, "registryEvidenceId": token})
        self.assertEqual(items[REGISTRY]["status"], "미확인")
        self.assertIn("만료", items[REGISTRY]["reason"])

    def test_stale_registry_reading_needs_new_reading(self):
        old = (date.today() - timedelta(days=40)).isoformat()
        token = evidence_store.issue_registry(reading(issuedAt=old), "a" * 64)
        _, items = status({"address": ADDRESS, "registryEvidenceId": token})
        self.assertEqual(items[REGISTRY]["status"], "미확인")
        self.assertEqual(items[REGISTRY]["basisDate"], old)
        self.assertIn("다시 열람", items[REGISTRY]["reason"])
        self.assertNotIn("amount10k", items[REGISTRY])

    # --- 다가구 선순위·납세증명서 ---

    def test_confirmed_prior_deposit_has_amount_and_date_without_personal_data(self):
        owner = self.owner_with_prior()
        raw = agent_llm._run_tool("document_status", {}, {"address": ADDRESS, "housingType": "multi",
                                                           "documentOwnerToken": owner})
        items = {row["item"]: row for row in json.loads(raw)["items"]}
        self.assertEqual(items[PRIOR]["status"], "서류 확인")
        self.assertEqual(items[PRIOR]["amount10k"], 35000)
        self.assertEqual(items[PRIOR]["basisDate"], TODAY)
        for secret in (owner, ADDRESS, "홍길동", "f" * 64):
            self.assertNotIn(secret, raw)

    def test_prior_for_another_address_or_without_token_is_unknown(self):
        owner = self.owner_with_prior()
        _, items = status({"address": "서울특별시 성동구 왕십리로 137 101동 1002호", "documentOwnerToken": owner})
        self.assertEqual(items[PRIOR]["status"], "미확인")
        _, items = status({"address": ADDRESS})
        self.assertEqual(items[PRIOR]["status"], "미확인")
        self.assertEqual(items[TAX]["status"], "미확인")

    def test_tax_status_without_lane_function_is_unknown(self):
        owner = self.owner_with_prior()
        with patch.object(document_requests, "confirmed_tax", None, create=True):
            _, items = status({"address": ADDRESS, "documentOwnerToken": owner})
        self.assertEqual(items[TAX]["status"], "미확인")
        self.assertIn("아직 연결되지 않았습니다", items[TAX]["reason"])

    def test_tax_status_uses_confirmed_tax_when_present(self):
        owner = self.owner_with_prior()
        seen = []

        def confirmed_tax(token, address):
            seen.append((token, address))
            return True

        with patch.object(document_requests, "confirmed_tax", confirmed_tax, create=True):
            raw = agent_llm._run_tool("document_status", {}, {"address": ADDRESS, "documentOwnerToken": owner})
        items = {row["item"]: row for row in json.loads(raw)["items"]}
        self.assertEqual(seen, [(owner, ADDRESS)])
        self.assertEqual(items[TAX]["status"], "서류 확인")
        self.assertNotIn(owner, raw)
        with patch.object(document_requests, "confirmed_tax", lambda token, address: False, create=True):
            _, items = status({"address": ADDRESS, "documentOwnerToken": owner})
        self.assertEqual(items[TAX]["status"], "미확인")

    def test_without_report_everything_is_unknown_and_model_arguments_are_ignored(self):
        token = evidence_store.issue_registry(reading(), "a" * 64)
        result = json.loads(agent_llm._run_tool("document_status", {"address": ADDRESS, "registryEvidenceId": token}))
        self.assertFalse(result["reportOpen"])
        self.assertEqual({row["status"] for row in result["items"]}, {"미확인"})
        self.assertIn("보증보험 가입 가능 여부", result["neverChecked"])


class ReportStateValidationTests(unittest.TestCase):
    def test_bad_fields_are_dropped(self):
        token = "A" * 43
        cleaned = agent_llm.clean_report_state({"address": f"  {ADDRESS} ", "housingType": "castle",
                                                "registryEvidenceId": "짧음", "documentOwnerToken": token, "extra": "x"})
        self.assertEqual(cleaned, {"address": ADDRESS, "documentOwnerToken": token})
        self.assertIsNone(agent_llm.clean_report_state(None))
        for address in ("", "abc", "가" * 221, "서울\n성동구", 123):
            self.assertIsNone(agent_llm.clean_report_state({"address": address, "documentOwnerToken": token}))
        with self.assertRaises(ValueError):
            agent_llm.clean_report_state(["not", "an", "object"])


class SchemaTests(unittest.TestCase):
    def test_schema_names_match_implementations(self):
        names = [schema["name"] for schema in agent_llm.TOOL_SCHEMAS]
        self.assertEqual(len(names), len(set(names)))
        self.assertEqual(set(names), set(agent_llm.TOOL_IMPLS))
        self.assertIn("document_status", names)
        self.assertEqual({t["function"]["name"] for t in agent_ollama._function_tools()}, set(names))
        schema = next(s for s in agent_llm.TOOL_SCHEMAS if s["name"] == "document_status")
        self.assertEqual(schema["input_schema"]["properties"], {})

    def test_prompt_and_notices_no_longer_claim_fithome_cannot_see_documents(self):
        for text in (agent_llm.SYSTEM_PROMPT, agent_llm.DISCLAIMER, agent_llm.SAFE_FALLBACK):
            self.assertNotIn("직접 보지 못", text)
            self.assertNotIn("어떤 도구로도", text)
        self.assertIn("document_status", agent_llm.SYSTEM_PROMPT)
        self.assertIn("'확인 필요'", agent_llm.SYSTEM_PROMPT)
        self.assertIn("판정하지 않습니다", agent_llm.DISCLAIMER)
        self.assertIn("판정하지 않습니다", agent_llm.SAFE_FALLBACK)


class ReassuranceGuardTests(unittest.TestCase):
    EVIDENCE = ["신탁등기 없음(서류 확인)", "근저당 채권최고액 1억 2,000만원(서류 확인, 등기부 열람일 기준)",
                "임대인 납세증명서 서류 확인, 발급일 이후 체납은 모릅니다.", "선순위 보증금 3억 5,000만원(서류 확인)"]

    def test_evidence_sentences_are_not_reassurance(self):
        for sentence in self.EVIDENCE:
            with self.subTest(sentence=sentence):
                self.assertEqual(agent_llm.reassurance_in(sentence), [])
                self.assertEqual(agent_llm.strip_problem_sentences(sentence), sentence)

    def test_stripping_reassurance_keeps_evidence_lines(self):
        answer = "이 집은 안전합니다.\n" + "\n".join(self.EVIDENCE)
        final = agent_llm.finalize_answer("q", answer, agent_llm.reassurance_in(answer))
        self.assertNotIn("안전합니다", final)
        for sentence in self.EVIDENCE:
            self.assertIn(sentence, final)
        self.assertIn("판정하지 않습니다", final)

    def test_confirmation_needed_is_not_turned_into_safe(self):
        self.assertTrue(agent_llm.reassurance_in("확인 필요 등급이라 안전합니다."))


class _Block:
    def __init__(self, **fields):
        self.__dict__.update(fields)


class _Response:
    def __init__(self, content):
        self.content = content
        self.stop_reason = "end_turn"
        self.model = "claude-haiku-4-5"
        self.usage = _Block(input_tokens=1, output_tokens=1)


class TokenLeakTests(unittest.TestCase):
    def setUp(self):
        store = tempfile.TemporaryDirectory()
        self.addCleanup(store.cleanup)
        env = patch.dict(os.environ, {"FITHOME_DOCUMENT_STORE": store.name, "ANTHROPIC_API_KEY": "test-key-not-real",
                                      "FITHOME_ANSWER_CHECK": "off"})
        env.start()
        self.addCleanup(env.stop)
        self.evidence = evidence_store.issue_registry(reading(), "a" * 64)
        self.owner = document_requests.create_request({"address": ADDRESS})["ownerToken"]
        self.report = agent_llm.clean_report_state({"address": ADDRESS, "housingType": "multi",
                                                    "registryEvidenceId": self.evidence, "documentOwnerToken": self.owner})

    def test_claude_loop_never_sends_tokens_to_model_or_trace(self):
        calls = []
        scripted = [_Response([_Block(type="tool_use", id="d1", name="document_status", input={})]),
                    _Response([_Block(type="text", text="근저당 1억 2,000만원(서류 확인). 납세증명서는 미확인입니다.")])]

        class _Messages:
            def create(self, **kwargs):
                # 모델에게 가는 요청 전체(시스템·도구·메시지)를 호출 시점 그대로 글자로 남긴다.
                calls.append(json.dumps(kwargs, ensure_ascii=False, default=lambda o: getattr(o, "__dict__", str(o))))
                return scripted.pop(0)

        fake = types.ModuleType("anthropic")
        fake.Anthropic = lambda *a, **k: types.SimpleNamespace(messages=_Messages())
        with patch.dict(sys.modules, {"anthropic": fake}):
            result = agent_llm.agent_chat([{"role": "user", "content": "등기부 확인됐어?"}], "단지: 테스트", self.report)
        self.assertTrue(result["ok"], result)
        self.assertEqual([t["name"] for t in result["toolTrace"]], ["document_status"])
        self.assertIn("서류 확인", calls[1])  # 도구 결과는 모델에게 간다
        for secret in (self.evidence, self.owner):
            for sent in calls:
                self.assertNotIn(secret, sent)
            self.assertNotIn(secret, json.dumps(result, ensure_ascii=False))

    def test_ollama_loop_never_sends_tokens_to_model_or_trace(self):
        sent = []
        scripted = [{"message": {"role": "assistant", "content": "",
                                 "tool_calls": [{"function": {"name": "document_status", "arguments": {}}}]}},
                    {"message": {"role": "assistant", "content": "근저당은 서류 확인, 납세증명서는 미확인입니다."}}]

        class _Raw:
            def __init__(self, payload):
                self.body = json.dumps(payload).encode()

            def read(self):
                return self.body

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        def fake_urlopen(request, timeout=None):
            if request.full_url.endswith("/api/tags"):
                return _Raw({"models": [{"name": agent_ollama.MODEL}]})
            sent.append(request.data.decode("utf-8"))
            return _Raw(scripted.pop(0))

        with patch.object(urllib.request, "urlopen", fake_urlopen):
            result = agent_ollama.agent_chat([{"role": "user", "content": "선순위 확인됐어?"}], "", self.report)
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["toolTrace"], [{"name": "document_status", "input": {}}])
        self.assertIn("\\uc11c\\ub958 \\ud655\\uc778", sent[1])  # '서류 확인'이 도구 결과로 실린다
        for secret in (self.evidence, self.owner):
            for body in sent:
                self.assertNotIn(secret, body)
            self.assertNotIn(secret, json.dumps(result, ensure_ascii=False))


class AgentChatRouteTests(unittest.TestCase):
    """/api/agent-chat이 reportState를 검증해 엔진에 도구 맥락으로만 넘기는지."""

    def setUp(self):
        import movevalue_api

        self.received = []
        engine = types.SimpleNamespace(agent_chat=lambda messages, context="", report_state=None: (
            self.received.append((context, report_state)) or {"ok": True, "answer": "ok"}))
        route = patch.object(movevalue_api, "select_agent_engine", lambda: (engine, {"available": True}))
        route.start()
        self.addCleanup(route.stop)
        server = ThreadingHTTPServer(("127.0.0.1", 0), movevalue_api.Handler)
        server.quiet = True
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        self.port = server.server_address[1]

    def post(self, body):
        # test_agent_ollama_loop가 urllib.request.urlopen을 가짜로 바꿔 두므로 http.client로 직접 보낸다.
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        self.addCleanup(conn.close)
        conn.request("POST", "/api/agent-chat", json.dumps(body), {"Content-Type": "application/json"})
        response = conn.getresponse()
        return response.status, json.loads(response.read())

    def test_report_state_is_cleaned_and_passed(self):
        token = "B" * 43
        code, _ = self.post({"messages": [{"role": "user", "content": "q"}], "context": "c",
                             "reportState": {"address": ADDRESS, "housingType": "multi", "documentOwnerToken": token,
                                             "registryEvidenceId": "../../etc"}})
        self.assertEqual(code, 200)
        self.assertEqual(self.received[-1], ("c", {"address": ADDRESS, "housingType": "multi", "documentOwnerToken": token}))
        self.post({"messages": [{"role": "user", "content": "q"}]})
        self.assertEqual(self.received[-1], ("", None))

    def test_non_object_report_state_is_bad_request(self):
        code, body = self.post({"messages": [{"role": "user", "content": "q"}], "reportState": "token"})
        self.assertEqual(code, 400)
        self.assertFalse(body["ok"])


if __name__ == "__main__":
    unittest.main()
