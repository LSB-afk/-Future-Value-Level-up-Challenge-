"""유료 등기 열람의 일일 상한·영속 요청 번호(이중 과금 방지) 점검. 제공기관 호출은 모두 mock."""
from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import socket
import tempfile
import threading
import unittest
from unittest.mock import patch

import registry_lookup as registry

REAL_PROVIDER = registry._provider

ADDRESS = "대전광역시 유성구 대학로 123"
ID = "11012020123456"
KEY = "fh-test-key-0000000001"
PARSED = {"address": ADDRESS, "propertyId": ID, "issuedAt": "2026-11-28", "mortgageMax10k": 12000,
          "evidence": [{"text": "근저당권자 홍길동 800101-1234567"}], "reviewRequired": False,
          "reason": "대조했습니다.", "documentHash": "ab" * 32}


class RegistryBillingTest(unittest.TestCase):
    def setUp(self):
        self.store = self.enterContext(tempfile.TemporaryDirectory())
        self.enterContext(patch.dict(os.environ, {"FITHOME_DOCUMENT_STORE": self.store,
                                                  "FITHOME_REGISTRY_DAILY_LIMIT": "",
                                                  **{name: "test" for name in registry._CREDS}}))
        self.enterContext(patch.object(registry, "_parse_pdf", return_value=dict(PARSED)))
        self.calls = []
        self.fail_with = None
        self.enterContext(patch.object(registry, "_provider", side_effect=self.provider))
        registry._SELECTIONS.clear()
        self.addCleanup(registry._SELECTIONS.clear)

    def provider(self, endpoint, params):
        if endpoint == "in0004000168":
            return {"list": [{"get부동산고유번호": ID, "get부동산소재지번": "[건물] " + ADDRESS,
                              "get구분": "건물", "get상태": "현행"}]}
        self.calls.append(params["uniqNo"])
        if self.fail_with:
            raise self.fail_with
        return {"outList": {"get고유번호": ID}, "pdfHexString": b"%PDF-1.4".hex()}

    def select(self):
        return registry.search_registry(ADDRESS)["items"][0]["id"]

    def fetch(self, selection, key=KEY, address=ADDRESS):
        return registry.fetch_registry(address, selection, confirm_charge=True, idempotency_key=key)

    def assert_status(self, status, call):
        with self.assertRaises(registry.RegistryError) as caught:
            call()
        self.assertEqual(caught.exception.http_status, status, str(caught.exception))
        return str(caught.exception)

    def test_same_key_calls_provider_once_and_replays_reading_only(self):
        selection = self.select()
        first = self.fetch(selection)
        again = self.fetch(selection)
        self.assertEqual(self.calls, [ID])
        self.assertTrue(again["replayed"])
        self.assertEqual(again["mortgageMax10k"], 12000)
        self.assertEqual(again["documentHash"], PARSED["documentHash"])
        self.assertNotIn("evidence", again)
        self.assertEqual(first["evidence"], PARSED["evidence"])
        stored = b"".join(path.read_bytes() for path in Path(self.store).iterdir())
        for secret in ("홍길동", "800101", "%PDF", KEY):
            self.assertNotIn(secret.encode(), stored)
        # 같은 번호를 다른 조회에 다시 쓰면 재생하지 않는다.
        self.assert_status(409, lambda: self.fetch(self.select(), address=ADDRESS + " 별관"))

    def test_concurrent_same_key_charges_once(self):
        selection = self.select()
        gate = threading.Event()

        def slow(endpoint, params):
            gate.wait(2)
            return self.provider(endpoint, params)

        def attempt(_):
            try:
                return self.fetch(selection)
            except registry.RegistryError as exc:
                return exc.http_status, str(exc)

        with patch.object(registry, "_provider", side_effect=slow), ThreadPoolExecutor(max_workers=3) as pool:
            futures = [pool.submit(attempt, n) for n in range(3)]
            threading.Timer(0.3, gate.set).start()
            outcomes = [future.result() for future in futures]
        self.assertEqual(self.calls, [ID])
        self.assertEqual(sum(isinstance(item, dict) for item in outcomes), 1, outcomes)
        # 선택 항목 소비가 아니라 먼저 남긴 'pending' 기록이 중복 호출을 막는다.
        for item in outcomes:
            if not isinstance(item, dict):
                self.assertEqual(item[0], 409)
                self.assertIn("처리하고 있습니다", item[1])

    def test_stale_pending_is_treated_as_unknown_charge(self):
        selection = self.select()
        registry._reserve(registry.hashlib.sha256(KEY.encode()).hexdigest(),
                          registry.hashlib.sha256((ADDRESS + "\x00" + selection).encode()).hexdigest(), ID)
        self.assertIn("처리하고 있습니다", self.assert_status(409, lambda: self.fetch(selection)))
        later = registry.time.time() + registry._CHARGE_PENDING_SECONDS + 1
        with patch.object(registry.time, "time", return_value=later):
            self.assertIn("과금 여부 확인", self.assert_status(409, lambda: self.fetch(selection)))
        self.assertEqual(self.calls, [])

    def test_timeout_leaves_unknown_and_same_key_retry_needs_billing_check(self):
        selection = self.select()
        self.fail_with = registry.RegistryUncertain("응답 없음", 502)
        self.assert_status(502, lambda: self.fetch(selection))
        self.fail_with = None
        message = self.assert_status(409, lambda: self.fetch(selection))
        self.assertIn("과금 여부 확인", message)
        self.assertEqual(self.calls, [ID])

    def test_socket_timeout_inside_provider_is_uncertain(self):
        selection = self.select()
        with patch.object(registry, "_provider", new=REAL_PROVIDER), \
                patch.object(registry.urllib.request, "build_opener") as opener:
            opener.return_value.open.side_effect = socket.timeout("timed out")
            self.assert_status(502, lambda: self.fetch(selection))
        self.assertIn("과금 여부 확인", self.assert_status(409, lambda: self.fetch(selection)))
        opener.return_value.open.assert_called_once()

    def test_definite_failure_is_replayed_without_calling_again(self):
        selection = self.select()
        self.fail_with = registry.RegistryError("제공기관에서 정상 등기 결과를 받지 못했습니다.", 502)
        first = self.assert_status(502, lambda: self.fetch(selection))
        self.fail_with = None
        self.assertEqual(self.assert_status(502, lambda: self.fetch(selection)), first)
        self.assertEqual(self.calls, [ID])

    def test_daily_limit_returns_429_before_calling(self):
        with patch.dict(os.environ, {"FITHOME_REGISTRY_DAILY_LIMIT": "2"}):
            used = [self.select() for _ in range(2)]
            for n, selection in enumerate(used):
                self.fetch(selection, key=KEY + str(n))
            selection = self.select()
            self.assertIn("한도", self.assert_status(429, lambda: self.fetch(selection, key=KEY + "x")))
            self.assertEqual(len(self.calls), 2)
            # 이미 끝난 요청의 재생은 제공기관을 부르지 않으므로 상한과 무관하다.
            self.assertTrue(self.fetch(used[0], key=KEY + "0")["replayed"])
        self.assertEqual(registry._daily_limit(), 50)

    def test_invalid_key_and_unchecked_selection_do_not_reserve(self):
        selection = self.select()
        for bad in ("short", "x" * 129, "has space in it!!", 1234567890123456):
            self.assert_status(400, lambda: self.fetch(selection, key=bad))
        self.assert_status(409, lambda: self.fetch("not-a-selection", key=KEY))
        self.assertEqual(self.calls, [])
        with patch.dict(os.environ, {"FITHOME_REGISTRY_DAILY_LIMIT": "1"}):
            self.fetch(selection, key=KEY)  # 앞선 거절은 하루 상한을 쓰지 않았다.
        self.assertEqual(self.calls, [ID])

    def test_other_key_on_same_uniq_no_is_refused_while_pending_or_unknown(self):
        selection = self.select()
        self.fail_with = registry.RegistryUncertain("응답 없음", 502)
        self.assert_status(502, lambda: self.fetch(selection))  # 'unknown'으로 남는다.
        self.fail_with = None
        self.assertIn("과금 여부 확인", self.assert_status(409, lambda: self.fetch(self.select(), key=KEY + "2")))
        self.assertEqual(self.calls, [ID])
        # 24시간이 지나면 다시 열람할 수 있다.
        later = registry.time.time() + registry._CHARGE_UNCERTAIN_SECONDS + 1
        with patch.object(registry.time, "time", return_value=later):
            self.fetch(self.select(), key=KEY + "3")
        self.assertEqual(self.calls, [ID, ID])

    def test_error_after_provider_returns_is_charged_failed(self):
        selection = self.select()
        with patch.object(registry, "_parse_pdf", side_effect=registry.RegistryError("PDF 판독 실패", 502)):
            first = self.assert_status(502, lambda: self.fetch(selection))
        statuses = [row[0] for row in registry._charge_db().execute("SELECT status FROM registry_charges")]
        self.assertEqual(statuses, ["charged_failed"])
        self.assertEqual(self.assert_status(502, lambda: self.fetch(selection)), first)  # 재생, 제공기관 재호출 없음
        self.assertEqual(self.calls, [ID])
        # 제공기관 호출 자체가 실패하면 과금되지 않았으므로 'failed'다.
        self.fail_with = registry.RegistryError("제공기관 오류", 502)
        self.assert_status(502, lambda: self.fetch(self.select(), key=KEY + "f"))
        statuses = [row[0] for row in registry._charge_db().execute("SELECT status FROM registry_charges ORDER BY created")]
        self.assertEqual(statuses, ["charged_failed", "failed"])


if __name__ == "__main__":
    unittest.main()
