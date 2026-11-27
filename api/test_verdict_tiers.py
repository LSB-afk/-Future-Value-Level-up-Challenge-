"""4단계 등급(위험 > 주의 > 확인 필요 > 안심)과 근거 수준, 납세증명서 연결을 검증한다."""

import base64
import json
import os
import sqlite3
import tempfile
import threading
import unittest
from datetime import date
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from unittest.mock import patch

import document_requests as requests
import evidence_store
from jeonse_verdict import evaluate, validate_input
from precontract_routes import _with_registry_evidence

ADDRESS = "서울특별시 성동구 왕십리로 137 101동 1001호"
TODAY = date.today().isoformat()
DAY = requests._today().isoformat()


def typed(**overrides):
    """사용자가 직접 입력한 값만 있는 아파트. 위험·주의 신호는 없다."""
    body = {
        "property": {"housingType": "apartment", "address": ADDRESS},
        "deposit10k": 30000,
        "price": {"basis": "market", "value10k": 80000, "source": "input"},
        "registry": {"issuedAt": TODAY, "mortgageMax10k": 12000, "trust": "no", "seizure": "no", "auction": "no",
                     "leaseRegistration": "no", "ownerMatches": "yes", "lastOwnershipChange": "2019-05-02"},
        "landlord": {"taxArrears": "no", "guaranteeEligible": "yes"},
        "building": {"use": "residential", "violation": "no"},
    }
    body.update(overrides)
    return body


def verified(**overrides):
    """서버가 확인한 값(실거래 집값, 등기부 근거, 확인한 납세증명서)을 붙인 상태. evaluate에 바로 넘긴다."""
    body = typed(**overrides)
    body["price"] = {**body["price"], "source": "trade"}
    body["registry"] = {**body["registry"], "mortgageSource": "registry", "dateSource": "registry"}
    body["landlord"] = {**body["landlord"], "taxSource": "submitted"}
    return body


def checks(report):
    return {c["id"]: c for c in report["checks"]}


class TierTests(unittest.TestCase):
    def test_four_grades_and_labels(self):
        cases = {
            "safe": verified(),
            "check": typed(),
            "caution": verified(registry={**verified()["registry"], "lastOwnershipChange": TODAY}),
            "danger": verified(registry={**verified()["registry"], "seizure": "yes"}),
        }
        labels = {"safe": "안심", "check": "확인 필요", "caution": "주의", "danger": "위험"}
        for grade, body in cases.items():
            with self.subTest(grade=grade):
                report = evaluate(body)
                self.assertEqual((report["grade"], report["gradeLabel"]), (grade, labels[grade]))
        self.assertIn("확인해야", evaluate(typed())["headline"])

    def test_every_check_has_core_and_evidence(self):
        for check in evaluate(typed())["checks"]:
            with self.subTest(check=check["id"]):
                self.assertIsInstance(check["core"], bool)
                self.assertIn(check["evidence"], {"document", "reviewed", "input", "none"})
                self.assertTrue(check["evidenceLabel"])

    def test_typed_values_only_need_checking(self):
        report = evaluate(validate_input(typed()))
        self.assertEqual(report["grade"], "check")
        self.assertEqual(report["counts"]["caution"], 0)
        gaps = {g["id"]: g["evidence"] for g in report["coreGaps"]}
        for key in ("mortgage", "priceBasis", "taxArrears", "trust", "registryFresh"):
            self.assertEqual(gaps[key], "input")
        self.assertTrue(all(c["core"] for c in report["reasons"]))
        self.assertLessEqual(len(report["reasons"]), 3)
        self.assertTrue(any(t.startswith("핵심 직접 입력") for t in report["tags"]))

    def test_unchecked_land_register_values_are_unconfirmed(self):
        body = typed()
        body["registry"] = {k: v for k, v in body["registry"].items() if k not in {"trust", "lastOwnershipChange"}}
        report = evaluate(validate_input(body))
        by_id = checks(report)
        self.assertEqual((by_id["trust"]["result"], by_id["trust"]["evidence"]), ("unknown", "none"))
        self.assertEqual(by_id["recentOwnership"]["evidence"], "none")
        self.assertEqual(report["grade"], "check")
        self.assertTrue(any(t.startswith("핵심 미확인") for t in report["tags"]))

    def test_estimated_price_needs_checking_instead_of_caution(self):
        body = verified()
        body["price"]["source"] = "estimate"
        report = evaluate(body)
        price = checks(report)["priceBasis"]
        self.assertEqual((price["result"], price["evidence"]), ("unknown", "none"))
        self.assertEqual(report["grade"], "check")
        self.assertIn("priceBasis", {g["id"] for g in report["coreGaps"]})

    def test_market_comparison_is_auxiliary(self):
        report = evaluate(verified())
        gap = checks(report)["marketGap"]
        self.assertEqual((gap["result"], gap["core"]), ("unknown", False))
        self.assertEqual(report["grade"], "safe")
        pricey = evaluate(verified(market={"jeonse10k": 26000, "source": "trade"}))  # 시세보다 15.4% 비쌈
        self.assertEqual(checks(pricey)["marketGap"]["result"], "caution")
        self.assertEqual(pricey["grade"], "caution")

    def test_apartment_building_items_are_auxiliary_but_villa_items_are_core(self):
        body = verified(building={"source": "input"})
        self.assertEqual(evaluate(body)["grade"], "safe")
        villa = verified(property={"housingType": "villa", "address": ADDRESS}, building={"source": "input"})
        villa["price"].update(official10k=60000, officialSource="public")
        report = evaluate(villa)
        by_id = checks(report)
        self.assertTrue(by_id["use"]["core"] and by_id["violation"]["core"] and by_id["hug126"]["core"])
        self.assertEqual(report["grade"], "check")

    def test_inspected_price_source_is_never_document_evidence_even_with_demo_flag(self):
        body = typed(isDemo=True, price={"basis": "market", "value10k": 1234, "source": "inspected"})
        inp = validate_input(body)
        self.assertEqual(inp["price"]["source"], "input")
        self.assertEqual(checks(evaluate(inp))["priceBasis"]["evidence"], "input")
        # validate_input을 거치지 않고 evaluate에 바로 넘겨도 서류 근거가 아니다.
        self.assertNotEqual(checks(evaluate(body))["priceBasis"]["evidence"], "document")

    def test_villa_with_server_sources_still_needs_violation_check(self):
        # 의도된 동작: 위반건축물 '없음'은 서버가 읽은 근거가 아직 없어 빌라는 '안심'에 이르지 못한다.
        villa = verified(property={"housingType": "villa", "address": ADDRESS}, building={"source": "public", "use": "residential", "violation": "no"})
        villa["price"].update(official10k=60000, officialSource="public")
        villa["registry"].update(rightsSource="registryUpload", rightsKeys="trust,seizure,auction,leaseRegistration")
        report = evaluate(villa)
        self.assertEqual(report["grade"], "check")
        self.assertEqual({g["id"] for g in report["coreGaps"]}, {"violation"})

    def test_multi_without_confirmed_prior_needs_checking(self):
        body = verified(property={"housingType": "multi", "address": ADDRESS})
        report = evaluate(body)
        self.assertEqual(report["grade"], "check")
        self.assertIn("priorDeposits", {g["id"] for g in report["coreGaps"]})
        self.assertIn("선순위 보증금 미확인", report["headline"])
        prior = checks(evaluate(body, confirmed_prior_deposits10k=0))["priorDeposits"]
        self.assertEqual((prior["result"], prior["evidence"], prior["core"]), ("pass", "document", True))

    def test_danger_wins_over_unconfirmed(self):
        body = typed(registry={"trust": "yes"})
        report = evaluate(validate_input(body))
        self.assertEqual(report["grade"], "danger")
        self.assertTrue(report["coreGaps"])
        self.assertEqual(report["reasons"][0]["id"], "trust")

    def test_client_cannot_claim_rights_or_tax_sources(self):
        body = typed()
        body["registry"]["rightsSource"] = "registry"
        body["landlord"]["taxSource"] = "submitted"
        inp = validate_input(body)
        self.assertNotIn("rightsSource", inp["registry"])
        self.assertNotIn("taxSource", inp["landlord"])
        self.assertIn("registry.rightsSource", inp["sourceDowngraded"])
        self.assertIn("landlord.taxSource", inp["sourceDowngraded"])
        by_id = checks(evaluate(inp))
        self.assertEqual(by_id["trust"]["evidence"], "input")
        self.assertEqual(by_id["taxArrears"]["evidence"], "input")

    def test_server_rights_source_is_a_document(self):
        body = verified()
        body["registry"]["rightsSource"] = "registryUpload"
        body["registry"]["rightsKeys"] = "trust,seizure"
        by_id = checks(evaluate(body))
        self.assertEqual((by_id["trust"]["evidence"], by_id["trust"]["source"]), ("document", "registryUpload"))
        # 서버가 읽지 않은 항목은 같은 등기부를 반영한 상태의 사용자 체크(원문 대조 입력)로 남는다.
        self.assertEqual(by_id["auction"]["evidence"], "reviewed")
        self.assertNotEqual(by_id["auction"]["source"], "registryUpload")
        self.assertEqual(by_id["ownerMatches"]["evidence"], "reviewed")

    def test_client_cannot_send_rights_keys(self):
        body = verified()
        body["registry"]["rightsKeys"] = "trust"
        self.assertNotIn("rightsKeys", validate_input(body)["registry"])


class RegistryEvidenceTierTests(unittest.TestCase):
    def setUp(self):
        store = tempfile.TemporaryDirectory()
        self.addCleanup(store.cleanup)
        env = patch.dict(os.environ, {"FITHOME_DOCUMENT_STORE": store.name})
        env.start()
        self.addCleanup(env.stop)

    def test_applied_registry_evidence_makes_user_checks_reviewed(self):
        token = _with_registry_evidence({"address": ADDRESS, "issuedAt": TODAY, "mortgageMax10k": 12000,
                                         "reviewRequired": False, "source": "uploaded_pdf",
                                         "documentHash": "a" * 64})["evidenceId"]
        inp = validate_input(typed(price={"basis": "market", "value10k": 80000, "source": "trade"}))
        inp, info = evidence_store.apply_registry(inp, token)
        self.assertEqual(info["status"], "applied")
        # 납세증명서 확인은 서버(처리부)가 붙인다.
        inp["landlord"] = {**inp["landlord"], "taxArrears": "no", "taxSource": "submitted"}
        report = evaluate(inp)
        by_id = checks(report)
        self.assertEqual(by_id["mortgage"]["evidence"], "document")
        self.assertEqual(by_id["registryFresh"]["evidence"], "document")
        for key in ("trust", "seizure", "auction", "leaseRegistration", "ownerMatches", "recentOwnership"):
            self.assertEqual(by_id[key]["evidence"], "reviewed", key)
        self.assertEqual(by_id["taxArrears"]["evidence"], "document")
        self.assertEqual(report["grade"], "safe", report["coreGaps"])


def tax_lines(title):
    return [title, "주소: 납세자주소", "발급일: " + DAY]


class ConfirmedTaxTests(unittest.TestCase):
    def setUp(self):
        store = tempfile.TemporaryDirectory()
        self.addCleanup(store.cleanup)
        env = patch.dict(os.environ, {"FITHOME_DOCUMENT_STORE": store.name})
        env.start()
        self.addCleanup(env.stop)
        self.created = requests.create_request({"address": ADDRESS, "requested": ["nationalTax", "localTax"]})
        self.owner = self.created["ownerToken"]

    def submit(self, kind, title):
        with patch.object(requests, "_pdf_lines", return_value=[tax_lines(title)]):
            requests.submit_document({"recipientToken": self.created["recipientToken"], "kind": kind,
                                      "consent": {"version": requests.CONSENT_VERSION, "agreed": True},
                                      "fileBase64": base64.b64encode(b"%PDF-" + kind.encode()).decode()})

    def confirm(self, kind):
        doc = next(d for d in requests.get_request({"ownerToken": self.owner})["documents"] if d["kind"] == kind)
        requests.review_request({"ownerToken": self.owner, "kind": kind, "fingerprint": doc["fingerprint"]})

    def test_both_certificates_must_be_confirmed(self):
        self.assertFalse(requests.confirmed_tax(self.owner, ADDRESS))
        self.submit("nationalTax", "국세 납세증명서")
        self.submit("localTax", "지방세 납세증명서")
        self.assertFalse(requests.confirmed_tax(self.owner, ADDRESS))  # 제출만 하고 원문 확인 전
        self.confirm("nationalTax")
        self.assertFalse(requests.confirmed_tax(self.owner, ADDRESS))
        self.confirm("localTax")
        self.assertTrue(requests.confirmed_tax(self.owner, ADDRESS))
        self.assertFalse(requests.confirmed_tax(self.owner, ADDRESS.replace("1001호", "1002호")))
        self.assertFalse(requests.confirmed_tax(self.created["recipientToken"], ADDRESS))
        self.assertFalse(requests.confirmed_tax(None, ADDRESS))
        self.assertFalse(requests.confirmed_tax("x" * 43, ADDRESS))

    def verdict_client(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), __import__("movevalue_api").Handler)
        server.quiet = True
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(thread.join)
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)

        def verdict(body):
            conn = HTTPConnection("127.0.0.1", server.server_port, timeout=5)
            try:
                conn.request("POST", "/api/jeonse-verdict", json.dumps(body), {"Content-Type": "application/json"})
                response = conn.getresponse()
                data = json.loads(response.read())
                self.assertEqual(response.status, 200, data)
                return data
            finally:
                conn.close()
        return verdict

    def confirm_both(self):
        self.submit("nationalTax", "국세 납세증명서")
        self.submit("localTax", "지방세 납세증명서")
        self.confirm("nationalTax")
        self.confirm("localTax")

    def test_confirmed_certificates_do_not_override_typed_arrears_yes(self):
        verdict = self.verdict_client()
        self.confirm_both()
        body = typed(landlord={"taxArrears": "yes"}, documentOwnerToken=self.owner)
        tax = checks(verdict(body))["taxArrears"]
        self.assertEqual(tax["result"], "danger")
        self.assertNotEqual(tax["evidence"], "document")
        self.assertNotEqual(tax["source"], "submitted")

    def test_document_store_failure_fails_closed_without_dropping_connection(self):
        verdict = self.verdict_client()
        self.confirm_both()
        body = typed(landlord={"taxArrears": "unknown"}, documentOwnerToken=self.owner)
        for error in (sqlite3.OperationalError("locked"), OSError("disk"), requests.DocumentRequestError(503, "store")):
            with self.subTest(error=type(error).__name__), patch.object(requests, "confirmed_tax", side_effect=error):
                report = verdict(body)
                self.assertNotEqual(checks(report)["taxArrears"]["evidence"], "document")
        with patch.object(requests, "confirmed_prior", side_effect=sqlite3.OperationalError("locked")):
            multi = typed(property={"housingType": "multi", "address": ADDRESS}, documentOwnerToken=self.owner)
            prior = checks(verdict(multi))["priorDeposits"]
            self.assertNotEqual(prior["evidence"], "document")
            self.assertNotEqual(checks(verdict(multi))["taxArrears"]["evidence"], "document")

    def test_verdict_route_uses_confirmed_certificates_for_any_housing_type(self):
        verdict = self.verdict_client()
        body = typed(landlord={"taxArrears": "unknown", "taxSource": "submitted"}, documentOwnerToken=self.owner)
        tax = checks(verdict(body))["taxArrears"]
        self.assertEqual((tax["result"], tax["evidence"]), ("unknown", "none"))
        self.submit("nationalTax", "국세 납세증명서")
        self.submit("localTax", "지방세 납세증명서")
        self.confirm("nationalTax")
        self.confirm("localTax")
        for housing in ("apartment", "villa"):
            with self.subTest(housing=housing):
                body["property"] = {"housingType": housing, "address": ADDRESS}
                tax = checks(verdict(body))["taxArrears"]
                self.assertEqual((tax["result"], tax["evidence"], tax["source"]), ("pass", "document", "submitted"))


if __name__ == "__main__":
    unittest.main()
