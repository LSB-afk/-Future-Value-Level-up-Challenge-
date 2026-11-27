"""HTTP integration between the private document inbox and the public-facing verdict."""
import base64
from datetime import date, datetime, timezone
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
import json
import os
import tempfile
import threading
import unittest
from unittest.mock import patch

from movevalue_api import Handler


class DocumentVerdictTest(unittest.TestCase):
    def setUp(self):
        directory = self.enterContext(tempfile.TemporaryDirectory())
        # 이 PC에 본인인증 기관 설정이 있어도 기본은 '연결되지 않은 개발 환경'으로 점검한다.
        self.enterContext(patch.dict(os.environ, {"FITHOME_DOCUMENT_STORE": directory, "FITHOME_PORTONE_API_SECRET": ""}))
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.server.quiet = True
        thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(thread.join)
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)

    def post(self, path, payload, status=200, headers=None):
        conn = HTTPConnection("127.0.0.1", self.server.server_port, timeout=5)
        try:
            conn.request("POST", "/api/" + path, json.dumps(payload),
                         {"Content-Type": "application/json", **(headers or {})})
            response = conn.getresponse()
            data = json.loads(response.read())
            self.assertEqual(response.status, status, data)
            self.assertIsNone(response.getheader("Access-Control-Allow-Origin"))
            return data
        finally:
            conn.close()

    def test_provider_status_and_cross_origin_restrictions(self):
        with patch.dict(os.environ, {"FITHOME_PORTONE_API_SECRET": "", "KAKAO_REST_API_KEY": "", "MOVEVALUE_KAKAO_REST_API_KEY": ""}):
            self.assertFalse(self.post("identity/status", {})["available"])
            self.assertFalse(self.post("building-register/status", {})["available"])
        with patch("identity_verification.start_verification") as start:
            self.post("identity/start", {"consent": True}, 403, {"Origin": "https://other.invalid"})
            self.post("identity/start", {"consent": True}, 403, {"X-Forwarded-For": "198.51.100.2"})
            start.assert_not_called()
        self.post("document-checks/read", {"kind": "ownerId", "fileBase64": ""}, 400)

    def test_connected_identity_gates_paid_registry_and_document_requests(self):
        import identity_verification as identity
        scope = {"reportKey": "listing:A123-L1", "address": "서울특별시 은평구 테스트로 10"}
        fetch = {**scope, "propertyId": "selection", "confirmCharge": True, "idempotencyKey": "fh-route-key-000000001"}
        create = {**scope, "requested": ["fixedDate"]}
        with patch("registry_lookup.fetch_registry", return_value={"address": scope["address"]}) as paid:
            # 연결되지 않은 개발 환경: 지금처럼 루프백이면 인증 없이 진행한다.
            self.post("registry/fetch", fetch)
            self.post("document-requests/create", create)
            paid.assert_called_once_with(scope["address"], "selection", confirm_charge=True,
                                         idempotency_key=fetch["idempotencyKey"])
            config = {"FITHOME_PORTONE_STORE_ID": "store-test", "FITHOME_PORTONE_CHANNEL_KEY": "channel-key-test",
                      "FITHOME_PORTONE_API_SECRET": "not-a-real-key"}
            with patch.dict(os.environ, config):
                for path, payload in (("registry/fetch", fetch), ("document-requests/create", create)):
                    self.assertIn("본인인증", self.post(path, payload, 403)["error"])
                start = identity.start_verification({**scope, "consent": True})
                receipt = {"status": "VERIFIED", "id": start["sdk"]["identityVerificationId"],
                           "verifiedAt": datetime.now(timezone.utc).isoformat(),
                           "channel": {"type": "LIVE", "key": config["FITHOME_PORTONE_CHANNEL_KEY"]}}
                token = {"challengeToken": start["challengeToken"]}
                with patch.object(identity, "_provider_lookup", return_value=receipt):
                    self.post("identity/confirm", {**scope, **token})
                identity._challenges.clear()  # 다른 워커·재시작 뒤에도 저장된 인증으로 통과한다.
                for path, payload in (("registry/fetch", fetch), ("document-requests/create", create)):
                    self.post(path, {**payload, "reportKey": "listing:other", **token}, 403)
                    self.post(path, {**payload, "address": scope["address"] + " 2호", **token}, 403)
                    self.post(path, {**payload, **token})
                # 화면이 요청 번호를 보내지 않아도 서버가 만든 번호로 기록·상한을 적용한다.
                self.post("registry/fetch", {**fetch, "idempotencyKey": None, **token})
                self.assertRegex(paid.call_args.kwargs["idempotency_key"], r"^[A-Za-z0-9_-]{32}$")
                self.post("registry/fetch", {**fetch, **token}, 403, {"X-Forwarded-For": "198.51.100.2"})
            self.assertEqual(paid.call_count, 3)

    def test_listing_trade_price_is_verified_against_its_own_complex(self):
        address = "서울특별시 은평구 테스트로 10"
        detail = {"id": "A123", "address": address,
                  "price": {"saleLive": True, "recentSale10k": 72000, "saleMedian10k": 70000}}
        payload = {"key": "listing:A123-L1", "property": {"address": address},
                   "price": {"source": "trade", "value10k": 72000}, "deposit10k": None}
        with patch("movevalue_api.property_detail_response", return_value={"detail": detail}):
            held = self.post("jeonse-verdict", payload)["ltv"]
            self.assertEqual((held["priceSource"], held["price10k"]), ("trade", 70000))
            self.assertIsNone(held["ratioPct"])
            self.assertIsNone(held["stressRatioPct"])
            payload["property"]["address"] = "다른 단지"
            self.assertEqual(self.post("jeonse-verdict", payload)["ltv"]["priceSource"], "estimate")
            payload["property"]["address"] = address
            payload["key"] = "listing:A12-L1"
            self.assertEqual(self.post("jeonse-verdict", payload)["ltv"]["priceSource"], "estimate")

    def test_only_current_owner_review_releases_the_same_address(self):
        post = self.post
        address = "서울특별시 강서구 테스트로 100"
        request = post("document-requests/create", {"address": address, "requested": ["fixedDate"]})
        owner, recipient = request["ownerToken"], request["recipientToken"]
        payload = {"property": {"address": address, "housingType": "multi"}, "landlord": {"priorDeposits10k": 0},
                   "price": {"basis": "market", "value10k": 50000}, "deposit10k": 20000,
                   "registry": {"mortgageMax10k": 0}}

        def verdict(token):
            return post("jeonse-verdict", {**payload, "documentOwnerToken": token})["ltv"]

        # The PDF worker is tested separately; here the HTTP confirmation must be the sole authority.
        def submit(lines, revision):
            with patch("document_requests._pdf_lines", return_value=[lines]):
                post("document-requests/submit", {"kind": "fixedDate", "recipientToken": recipient,
                     "fileBase64": base64.b64encode(b"%PDF-" + revision).decode()})

        lines = ["확정일자 부여현황", "주택 소재지: " + address, "발급일: " + date.today().isoformat(),
                 "선순위 보증금 총액: 120,000,000원"]
        submit(lines, b"one")
        self.assertTrue(verdict(owner)["priorDepositPending"])
        expanded = post("document-requests/extend", {"ownerToken": owner, "requested": ["nationalTax"]})
        self.assertIn("nationalTax", expanded["requested"])
        self.assertIn("fixedDate", post("document-requests/recipient", {"recipientToken": recipient})["requested"])
        doc = post("document-requests/status", {"ownerToken": owner})["documents"][0]
        post("document-requests/review", {"ownerToken": owner, "kind": "fixedDate", "fingerprint": doc["fingerprint"]})
        self.assertEqual(verdict(owner)["prior10k"], 12000)
        self.assertTrue(verdict(recipient)["priorDepositPending"])
        payload["property"]["address"] += " 2호"
        self.assertTrue(verdict(owner)["priorDepositPending"])
        payload["property"]["address"] = address
        submit(lines[:-1], b"two")
        self.assertTrue(verdict(owner)["priorDepositPending"])
