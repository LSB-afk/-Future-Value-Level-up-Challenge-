"""등기 근거 번호와 서버 보류 규칙: 화면이 '등기부' 근거를 주장할 수 없고, 날짜가 없거나 어긋나면 계산을 멈춘다."""

import os
import tempfile
import unittest
from datetime import date
from unittest.mock import patch

import sqlite3

import evidence_store
from document_requests import DocumentRequestError
from jeonse_verdict import evaluate, validate_input
from movevalue_api import verify_trade_price
from precontract_routes import _with_registry_evidence

ADDRESS = "서울특별시 성동구 왕십리로 137 101동 1001호"
TODAY = date.today().isoformat()


def reading(**overrides):
    return {"address": ADDRESS, "issuedAt": TODAY, "mortgageMax10k": 12000, "reviewRequired": False,
            "source": "uploaded_pdf", "documentHash": "a" * 64, **overrides}


def payload(**registry):
    return {"property": {"housingType": "apartment", "address": ADDRESS}, "deposit10k": 30000,
            "price": {"basis": "market", "value10k": 80000, "source": "input"},
            "registry": {"trust": "no", "seizure": "no", **registry}}


class RegistryEvidenceTests(unittest.TestCase):
    def setUp(self):
        store = tempfile.TemporaryDirectory()
        self.addCleanup(store.cleanup)
        env = patch.dict(os.environ, {"FITHOME_DOCUMENT_STORE": store.name})
        env.start()
        self.addCleanup(env.stop)

    def test_browser_cannot_claim_registry_source(self):
        inp = validate_input(payload(mortgageMax10k=5000, issuedAt=TODAY, source="registry",
                                     mortgageSource="registry", dateSource="registry"))
        self.assertNotIn("mortgageSource", inp["registry"])
        self.assertNotIn("dateSource", inp["registry"])
        self.assertEqual(inp["registry"]["source"], "input")
        checks = {c["id"]: c for c in evaluate(inp)["checks"]}
        self.assertEqual(checks["mortgage"]["source"], "input")
        self.assertEqual(checks["registryFresh"]["source"], "input")
        self.assertIn("registry.mortgageSource", inp["sourceDowngraded"])

    def test_missing_registry_source_is_not_labelled_registry(self):
        inp = validate_input(payload(mortgageMax10k=5000, issuedAt=TODAY))
        checks = {c["id"]: c for c in evaluate(inp)["checks"]}
        self.assertEqual(checks["trust"]["source"], "input")

    def test_other_section_source_claims_are_downgraded(self):
        body = payload()
        body["landlord"] = {"source": "submitted", "taxArrears": "no"}
        body["building"] = {"source": "inspected", "violationSource": "registry", "violation": "no"}
        inp = validate_input(body)
        self.assertEqual(inp["landlord"]["source"], "input")
        self.assertEqual(inp["building"]["source"], "input")
        self.assertEqual(inp["building"]["violationSource"], "input")

    def test_evidence_id_only_for_automatic_pass(self):
        self.assertIn("evidenceId", _with_registry_evidence(reading()))
        for held in (reading(reviewRequired=True), reading(mortgageMax10k=None), reading(issuedAt=None),
                     reading(documentHash=None)):
            result = _with_registry_evidence(held)
            self.assertNotIn("evidenceId", result)
            self.assertNotIn("documentHash", result)

    def test_evidence_applies_server_values_and_label(self):
        token = _with_registry_evidence(reading())["evidenceId"]
        inp = validate_input(payload(mortgageMax10k=1, issuedAt=TODAY))
        inp, info = evidence_store.apply_registry(inp, token)
        self.assertEqual(info["status"], "applied")
        self.assertTrue(info["replacedTypedValues"])
        report = evaluate(inp)
        checks = {c["id"]: c for c in report["checks"]}
        self.assertEqual(report["ltv"]["mortgage10k"], 12000)
        self.assertEqual(checks["mortgage"]["source"], "registryUpload")  # 업로드 PDF는 진위 미검증
        self.assertEqual(checks["trust"]["source"], "input")  # 갑구는 문서에서 읽지 않았다
        token = _with_registry_evidence(reading(source="hyphen"))["evidenceId"]
        inp, info = evidence_store.apply_registry(validate_input(payload()), token)
        self.assertFalse(info["replacedTypedValues"])
        self.assertEqual({c["id"]: c for c in evaluate(inp)["checks"]}["mortgage"]["source"], "registry")

    def test_evidence_rejected_for_other_address_bad_or_expired_token(self):
        token = _with_registry_evidence(reading())["evidenceId"]
        other = payload(mortgageMax10k=1, issuedAt=TODAY)
        other["property"]["address"] = ADDRESS.replace("1001호", "1002호")
        for inp, tok in ((other, token), (payload(), "x" * 43), (payload(), "../../etc"), (payload(), 123)):
            result, info = evidence_store.apply_registry(validate_input(inp), tok)
            self.assertEqual(info["status"], "rejected")
            self.assertNotEqual((result.get("registry") or {}).get("mortgageSource"), "registry")
        with patch.object(evidence_store.time, "time", return_value=evidence_store.time.time() + 8 * 86400):
            _, info = evidence_store.apply_registry(payload(), token)
        self.assertEqual(info["status"], "rejected")

    def test_mortgage_without_date_is_held(self):
        report = evaluate(validate_input(payload(mortgageMax10k=5000)))
        self.assertTrue(report["ltv"]["mortgagePending"])
        self.assertIsNone(report["ltv"]["ratioPct"])
        mortgage = next(c for c in report["checks"] if c["id"] == "mortgage")
        self.assertIn("열람일", mortgage["note"])
        self.assertNotEqual(report["grade"], "safe")

    def test_replaced_flag_only_for_fields_actually_typed(self):
        token = _with_registry_evidence(reading(mortgageMax10k=0))["evidenceId"]
        _, info = evidence_store.apply_registry(validate_input(payload(mortgageMax10k=0)), token)
        self.assertFalse(info["replacedTypedValues"])

    def test_store_failure_keeps_paid_reading_without_evidence(self):
        for error in (sqlite3.OperationalError("locked"), OSError("disk"),
                      DocumentRequestError(503, "store")):
            with self.subTest(error=type(error).__name__), patch.object(evidence_store, "_db", side_effect=error):
                result = _with_registry_evidence(reading())
                self.assertEqual(result["mortgageMax10k"], 12000)
                self.assertNotIn("evidenceId", result)
                self.assertNotIn("documentHash", result)
                _, info = evidence_store.apply_registry(payload(), "x" * 43)
                self.assertEqual(info["status"], "rejected")

    def test_price_market_violation_labels_need_server_confirmation(self):
        body = payload(mortgageMax10k=0, issuedAt=TODAY)
        body["price"].update(official10k=50000, officialSource="registry")
        body["market"] = {"jeonse10k": 30000, "source": "inspected"}
        body["building"] = {"source": "public", "violation": "no", "use": "residential"}
        inp = validate_input(body)
        self.assertEqual(inp["price"]["officialSource"], "input")
        self.assertEqual(inp["market"]["source"], "input")
        self.assertEqual(inp["building"]["violationSource"], "input")
        # 'public'·'trade'를 주장해도 서버 단지 데이터가 없으면 낮춘다
        body["price"]["officialSource"], body["market"]["source"] = "public", "trade"
        checked = verify_trade_price(validate_input(body))
        self.assertEqual(checked["price"]["officialSource"], "input")
        self.assertEqual(checked["market"]["source"], "estimate")
        checks = {c["id"]: c for c in evaluate(checked)["checks"]}
        self.assertNotIn(checks["violation"]["source"], {"public", "registry"})

if __name__ == "__main__":
    unittest.main()
