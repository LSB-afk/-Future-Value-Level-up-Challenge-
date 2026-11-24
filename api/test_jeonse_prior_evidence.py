"""다가구 선순위 자료가 확인돼야 금액 추정이 가능한지 검증한다."""

import unittest
from datetime import date

from jeonse_verdict import evaluate


class PriorEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.payload = {
            "property": {"housingType": "multi", "address": "대전광역시 유성구"},
            "deposit10k": 20000,
            "price": {"basis": "market", "value10k": 50000, "source": "input"},
            "registry": {"mortgageMax10k": 0, "trust": "no", "seizure": "no",
                         "auction": "no", "leaseRegistration": "no"},
            "building": {"use": "residential", "violation": "no"},
            "landlord": {"taxArrears": "no", "guaranteeEligible": "yes"},
            "auction": {"ratePct": 80},
        }

    def check_pending(self, report):
        self.assertTrue(report["ltv"]["priorDepositPending"])
        self.assertIsNone(report["ltv"]["prior10k"])
        self.assertIsNone(report["ltv"]["ratioPct"])
        self.assertIsNone(report["ltv"]["debt10k"])
        self.assertTrue(all(v is None for v in report["ltv"]["headroom10k"].values()))
        self.assertIsNone(report["depositGuide"]["senior10k"])
        self.assertTrue(all(x["max10k"] is None and x["fits"] is None for x in report["depositGuide"]["lines"]))
        self.assertIn("선순위 보증금 미확인", report["depositGuide"]["headline"])
        self.assertFalse(report["repayment"]["available"])
        self.assertIsNone(report["repayment"].get("myRecovered10k"))
        self.assertIsNone(report["guarantees"]["hugMax10k"])
        self.assertIn("선순위 보증금", report["guarantees"]["unknowns"])
        self.assertNotEqual(report["guarantees"]["status"], "likely")
        self.assertIn("선순위 보증금 미확인", report["tags"])
        self.assertFalse(any("근저당 여유" in t or "LTV" in t or "보증보험 가능" in t for t in report["tags"]))

    def test_manual_number_or_received_status_cannot_confirm_amount(self):
        self.payload["landlord"].update(priorDeposits10k=0, priorDepositsConfirmed=True)
        self.payload["requests"] = {"fixedDate": "received"}
        self.check_pending(evaluate(self.payload))

    def test_invalid_evidence_stays_pending(self):
        for amount in (None, -1, float("nan"), float("inf"), True, "잘못된 값"):
            with self.subTest(amount=amount):
                self.check_pending(evaluate(self.payload, confirmed_prior_deposits10k=amount))

    def test_independent_risks_remain_visible_during_hold(self):
        self.payload["registry"]["seizure"] = "yes"
        report = evaluate(self.payload)
        self.check_pending(report)
        self.assertEqual(report["grade"], "danger")
        self.assertEqual(report["guarantees"]["status"], "unlikely")

    def test_known_debt_alone_can_still_raise_danger(self):
        self.payload["registry"]["mortgageMax10k"] = 40000
        report = evaluate(self.payload)
        self.check_pending(report)
        self.assertEqual(report["grade"], "danger")
        self.assertEqual(report["guarantees"]["status"], "unlikely")

    def test_confirmed_amount_overrides_manual_and_allows_estimates(self):
        self.payload["landlord"]["priorDeposits10k"] = 1
        for amount, recovered in ((0, 20000), (35000, 4600)):
            with self.subTest(amount=amount):
                report = evaluate(self.payload, confirmed_prior_deposits10k=amount)
                self.assertFalse(report["ltv"]["priorDepositPending"])
                self.assertEqual(report["ltv"]["prior10k"], amount)
                self.assertEqual(report["repayment"]["myRecovered10k"], recovered)
                prior = next(c for c in report["checks"] if c["id"] == "priorDeposits")
                self.assertEqual(prior["result"], "pass")

    def test_apartments_keep_existing_estimates(self):
        self.payload["property"]["housingType"] = "apartment"
        report = evaluate(self.payload)
        self.assertFalse(report["ltv"]["priorDepositPending"])
        self.assertTrue(report["repayment"]["available"])

    def test_unconfirmed_mortgage_holds_amounts_for_every_housing_type(self):
        self.payload["price"].update(value10k=73314, source="estimate")
        self.payload["deposit10k"] = 42000
        for housing in ("apartment", "villa", "officetel", "multi"):
            for invalid in (None, -1, "not a number", float("inf"), float("nan"), False):
                with self.subTest(housing=housing, invalid=invalid):
                    self.payload["property"]["housingType"] = housing
                    self.payload["registry"]["mortgageMax10k"] = invalid
                    report = evaluate(self.payload, confirmed_prior_deposits10k=0)
                    ltv = report["ltv"]
                    self.assertTrue(ltv["mortgagePending"])
                    self.assertEqual(ltv["rentToMarketPct"], 57.3)
                    self.assertEqual(ltv["priceSource"], "estimate")
                    for field in ("mortgage10k", "debt10k", "ratioPct"):
                        self.assertIsNone(ltv[field])
                    self.assertTrue(all(v is None for v in ltv["headroom10k"].values()))
                    self.assertIsNone(report["depositGuide"]["senior10k"])
                    self.assertTrue(all(line["fits"] is None and line["max10k"] is None for line in report["depositGuide"]["lines"]))
                    self.assertFalse(report["repayment"]["available"])
                    self.assertIsNone(report["guarantees"]["hugMax10k"])
                    self.assertEqual(report["guarantees"]["status"], "check")
                    checks = {c["id"]: c["result"] for c in report["checks"]}
                    self.assertEqual(["unknown"] * 3, [checks[k] for k in ("mortgage", "ltv", "guaranteeEligible")])
                    self.assertFalse(any("근저당 여유" in t or "LTV" in t or "보증보험 가능" in t for t in report["tags"]))

    def test_stale_mortgage_reopens_hold_and_zero_is_a_valid_amount(self):
        today = date(2026, 11, 24)
        self.payload["registry"].update(mortgageMax10k=0, source="input", mortgageSource="registry", dateSource="registry")
        for issued, pending in (("2026-10-25", False), ("2026-10-24", True),
                                ("2026-11-25", True), ("오류", True), ("", False)):
            with self.subTest(issued=issued):
                self.payload["registry"]["issuedAt"] = issued
                report = evaluate(self.payload, today, confirmed_prior_deposits10k=0)
                self.assertEqual(report["ltv"]["mortgagePending"], pending)
                self.assertEqual(report["ltv"]["ratioPct"], None if pending else 40.0)
                checks = {c["id"]: c for c in report["checks"]}
                self.assertEqual(checks["seizure"]["source"], "input")
                if issued == "2026-10-25":
                    self.assertEqual(checks["mortgage"]["source"], "registry")
                    self.assertEqual(checks["registryFresh"]["source"], "registry")
                if pending:
                    self.assertNotEqual(checks["registryFresh"]["result"], "pass")

    def test_reviewed_positive_violation_remains_visible_with_pending_mortgage(self):
        self.payload["registry"]["mortgageMax10k"] = None
        cases = (("yes", "reviewedPdf", "caution"), ("yes", "input", "caution"),
                 ("unknown", "reviewedPdf", "unknown"), ("no", "reviewedPdf", "unknown"),
                 ("no", "input", "pass"))
        for value, source, result in cases:
            with self.subTest(value=value, source=source):
                self.payload["building"].update(violation=value, source="input", violationSource=source)
                report = evaluate(self.payload)
                checks = {c["id"]: c for c in report["checks"]}
                self.assertTrue(report["ltv"]["mortgagePending"])
                self.assertEqual(checks["violation"]["result"], result)
                self.assertEqual(checks["use"]["source"], "input")
                self.assertEqual(report["grade"], "caution")
                if value == "yes" and source == "reviewedPdf":
                    self.assertEqual(checks["violation"]["sourceLabel"], "사용자가 원문 대조")
                if result == "unknown":
                    self.assertEqual(checks["violation"]["source"], "none")

    def test_pending_mortgage_preserves_independent_danger(self):
        self.payload["registry"]["mortgageMax10k"] = None
        self.payload["deposit10k"] = 51000
        report = evaluate(self.payload, confirmed_prior_deposits10k=0)
        self.assertIsNone(report["ltv"]["ratioPct"])
        self.assertEqual(report["grade"], "danger")
        self.assertEqual(report["guarantees"]["status"], "unlikely")

    def test_rent_to_market_ratio_needs_a_market_denominator(self):
        self.payload["price"] = {"basis": "official", "official10k": 50000, "value10k": 55000}
        self.assertIsNone(evaluate(self.payload)["ltv"]["rentToMarketPct"])
        for invalid in (None, False, 0, -1, float("nan"), float("inf")):
            with self.subTest(value=invalid):
                self.payload["price"] = {"basis": "market", "value10k": invalid}
                self.assertIsNone(evaluate(self.payload)["ltv"]["rentToMarketPct"])

    def test_unentered_deposit_holds_estimates_even_after_prior_confirmation(self):
        del self.payload["deposit10k"]
        self.payload["price"]["official10k"] = 45000
        self.payload["market"] = {"jeonse10k": 20000}
        for prior in (None, 0, 10000):
            with self.subTest(prior=prior):
                report = evaluate(self.payload, confirmed_prior_deposits10k=prior)
                ltv = report["ltv"]
                self.assertIsNone(ltv["deposit10k"])
                self.assertIsNone(ltv["debt10k"])
                self.assertIsNone(ltv["ratioPct"])
                self.assertTrue(all(v is None for v in ltv["headroom10k"].values()))
                guide = report["depositGuide"]
                self.assertIsNone(guide["deposit10k"])
                self.assertIsNone(guide["gapPct"])
                self.assertTrue(all(x["max10k"] is None and x["fits"] is None for x in guide["lines"]))
                self.assertFalse(report["repayment"]["available"])
                self.assertEqual(report["guarantees"]["status"], "check")
                self.assertIsNone(report["guarantees"]["hugMax10k"])
                checks = {c["id"]: c["result"] for c in report["checks"]}
                for name in ("ltv", "hug126", "marketGap", "guaranteeEligible"):
                    self.assertEqual(checks[name], "unknown")

    def test_address_only_and_explicit_zero_have_distinct_results(self):
        report = evaluate({"property": {"housingType": "multi", "address": "대전광역시 유성구"}})
        self.check_pending(report)
        self.assertIsNone(report["depositGuide"]["deposit10k"])
        self.payload["deposit10k"] = 0
        report = evaluate(self.payload, confirmed_prior_deposits10k=0)
        self.assertEqual(report["ltv"]["deposit10k"], 0)
        self.assertEqual(report["ltv"]["debt10k"], 0)


if __name__ == "__main__":
    unittest.main()
