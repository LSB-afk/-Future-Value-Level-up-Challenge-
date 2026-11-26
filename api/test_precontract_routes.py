"""HTTP integration between the private document inbox and the public-facing verdict."""
import base64
from datetime import date
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
        self.enterContext(patch.dict(os.environ, {"FITHOME_DOCUMENT_STORE": directory}))
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
