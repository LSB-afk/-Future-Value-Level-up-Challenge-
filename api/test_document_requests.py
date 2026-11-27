"""Regression checks for private request links, evidence extraction and review gating."""

import base64
import os
import sqlite3
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

import document_requests as requests


ADDRESS = "대전광역시 유성구 예시로 10 201호"
DAY = requests._today().isoformat()
CONSENT = {"consent": {"version": requests.CONSENT_VERSION, "agreed": True}}


def lines(total="선순위 임차보증금 총액: 350,000,000원", address=ADDRESS,
          issued=DAY, title="확정일자 부여현황"):
    return [title, "주택 소재지: " + address, "발급일: " + issued, total]


def pdf(lines_to_write):
    import pymupdf
    with pymupdf.open() as doc:
        page = doc.new_page()
        for n, line in enumerate(lines_to_write):
            page.insert_text((35, 50 + n * 18), line, fontname="korea", fontsize=10)
        return doc.tobytes()


class Evidence(unittest.TestCase):
    def analyze(self, content):
        return requests._analyze("fixedDate", ADDRESS, [content])

    def test_original_line_citation_and_exact_amount(self):
        doc = self.analyze(lines("선순위 임차보증금 합계: 금3억 5,000만원"))
        self.assertEqual((doc["status"], doc["documentType"], doc["amount10k"]),
                         ("ready", "fixedDateRecord", 35000))
        self.assertEqual(doc["evidence"][-1],
                         {"field": "amount", "page": 1, "line": 4, "text": "선순위 임차보증금 합계: 금3억 5,000만원"})

    def test_missing_ambiguous_mismatched_expired_or_future_is_unknown(self):
        tomorrow = (requests._today() + timedelta(days=1)).isoformat()
        yesterday = (requests._today() - timedelta(days=1)).isoformat()
        for case in [
            [], lines(title="참고자료"), lines(address=ADDRESS + "동"), lines(address=ADDRESS[:-4]),
            lines(address=ADDRESS + "0"), lines(issued=tomorrow), lines() + ["102호실 제외"], lines(issued="2024-02-30"),
            lines() + ["유효기한: " + yesterday], lines() + ["발급일: " + yesterday],
            lines("보증금: 300만원"), lines("선순위 보증금: 300만원"),
            lines("선순위 보증금 총액: 3,50,00원"), lines("선순위 보증금 합계: 3,000~4,000만원"),
            lines() + ["선순위 보증금 합계: 2억원"],
            lines("보증금 1억 원") + ["50,000,000", "월세: 50만원"],
        ]:
            with self.subTest(case=case):
                doc = self.analyze(case)
                self.assertEqual(doc["status"], "needs_review")
                self.assertIsNone(doc["amount10k"])
        self.assertTrue(any(e["field"] == "entry" for e in self.analyze(lines("금3,000,000원"))["evidence"]))

    def test_supporting_statement_and_taxpayer_address(self):
        doc = self.analyze(lines(title="타전세계약체결내역 확인서", total="선순위 보증금 총액: 0원"))
        self.assertEqual((doc["status"], doc["documentType"], doc["amount10k"]), ("ready", "landlordStatement", 0))
        self.assertTrue(doc["notes"])
        tax = requests._analyze("localTax", ADDRESS, [["지방세 납세증명서", "주소: 납세자주소", "발급일: " + DAY]])
        self.assertEqual((tax["status"], tax["addressStatus"], tax["amount10k"]), ("ready", "taxpayer_address", None))
        wrong = requests._analyze("nationalTax", ADDRESS, [["지방세 납세증명서", "발급일: " + DAY]])
        self.assertEqual(wrong["status"], "needs_review")

    def test_address_units_and_city_alias(self):
        self.assertTrue(self.analyze(lines(address=ADDRESS.replace("대전광역시", "대전")))["addressMatched"])
        self.assertFalse(self.analyze(lines(address=ADDRESS.replace("10 201", "102 01")))["addressMatched"])

    def test_whole_building_totals_allow_only_the_omitted_room(self):
        building = "대전광역시 유성구 예시로 10-2 101동"
        target = building + " 제201호"
        scoped_total = "건물 전체 선순위 임차보증금 총액: 3억원"
        def analyze(source, total=scoped_total, extra=None):
            content = lines(address=source, total=total)
            return requests._analyze("fixedDate", target, [content + (extra or [])])
        doc = analyze(building)
        self.assertEqual((doc["status"], doc["addressStatus"], doc["amount10k"]),
                         ("ready", "whole_building", 30000))
        self.assertEqual(analyze(building, "선순위 보증금 합계: 3억원", ["산정 범위: 건물 전체"])["status"], "ready")
        for source in (building + " 203호", building.replace("101동", "102동"), building.replace(" 101동", ""),
                       building.replace("10-2", "10-20"), building.replace("예시로", "예시길")):
            with self.subTest(source=source):
                self.assertEqual(analyze(source)["status"], "needs_review")
        self.assertEqual(analyze(building, "선순위 보증금 총액: 3억원")["status"], "needs_review")
        self.assertEqual(analyze(building, extra=["일부 세대 제외"])["status"], "needs_review")

    def test_prior_issue_date_is_product_freshness_not_printed_expiry(self):
        for age, status in ((30, "ready"), (31, "needs_review")):
            doc = self.analyze(lines(issued=(requests._today() - timedelta(days=age)).isoformat()))
            self.assertEqual(doc["status"], status)
            if age == 31:
                self.assertIsNone(doc["amount10k"])
                self.assertTrue(any("핏홈" in issue and "30일" in issue for issue in doc["issues"]))

    def test_two_line_fields_and_another_unit(self):
        doc = self.analyze(["선순위 임차보증금 확인서", "주택 소재지", ADDRESS, "발급일", DAY,
                            "선순위 보증금 합계", "10,000원"])
        self.assertEqual(doc["amount10k"], 1)
        self.assertEqual([v["line"] for v in doc["evidence"] if v["field"] == "address"], [2, 3])


class Lifecycle(unittest.TestCase):
    def setUp(self):
        store = tempfile.TemporaryDirectory()
        self.addCleanup(store.cleanup)
        self.store = Path(store.name)
        env = patch.dict(os.environ, {"FITHOME_DOCUMENT_STORE": store.name})
        env.start()
        self.addCleanup(env.stop)
        self.created = requests.create_request({"address": ADDRESS, "requested": ["fixedDate"]})
        self.owner = {"ownerToken": self.created["ownerToken"]}
        self.recipient = {"recipientToken": self.created["recipientToken"]}

    def submit(self, data, consent=CONSENT):
        return requests.submit_document({**self.recipient, **consent, "kind": "fixedDate",
                                         "fileBase64": base64.b64encode(data).decode("ascii")})

    def test_recipient_sees_consent_terms_and_submit_requires_current_consent(self):
        terms = requests.get_recipient(self.recipient)["consent"]
        self.assertEqual(terms["version"], requests.CONSENT_VERSION)
        self.assertEqual([t["title"] for t in terms["terms"]], ["이용 목적", "임차인에게 보이는 범위", "보관 기간", "원본 PDF"])
        old = {"version": "2000-01-01", "agreed": True}
        with patch.object(requests, "_pdf_lines", return_value=[lines()]) as read:
            for consent in [{}, {"consent": None}, {"consent": {"version": requests.CONSENT_VERSION}},
                            {"consent": {"version": requests.CONSENT_VERSION, "agreed": "true"}},
                            {"consent": {"agreed": True}}, {"consent": old}]:
                with self.subTest(consent=consent), self.assertRaises(requests.DocumentRequestError) as cm:
                    self.submit(b"%PDF-consent", consent)
                self.assertEqual(cm.exception.status, 400)
                self.assertIn("동의", str(cm.exception))
            read.assert_not_called()
        self.assertEqual(requests.get_request(self.owner)["documents"], [])

    def test_submission_records_consent_version_and_time(self):
        before = requests.datetime.now(requests.timezone.utc).replace(microsecond=0)
        with patch.object(requests, "_pdf_lines", return_value=[lines(title="선순위 임차보증금 확인서")]):
            self.assertEqual(self.submit(b"%PDF-consent")["status"], "ready")
        doc = requests.get_request(self.owner)["documents"][0]
        self.assertEqual(doc["consentVersion"], requests.CONSENT_VERSION)
        consented = requests.datetime.fromisoformat(doc["consentAt"])
        self.assertEqual(consented.utcoffset(), timedelta(0))
        self.assertLessEqual(before, consented)
        # 세입자 화면에는 제출자를 확인된 임대인으로 적지 않는다.
        self.assertTrue(any("링크로 제출된 서류" in note for note in doc["notes"]))
        self.assertFalse(any("임대인이 제출" in note for note in doc["notes"]))
        confirmed = requests.review_request({**self.owner, "kind": "fixedDate", "fingerprint": doc["fingerprint"]})
        self.assertEqual(confirmed["documents"][0]["consentAt"], doc["consentAt"])

    def test_role_separation_and_private_storage(self):
        for func, value in [(requests.get_request, self.created["recipientToken"]),
                            (requests.get_recipient, self.created["ownerToken"])]:
            with self.subTest(func=func), self.assertRaises(requests.DocumentRequestError) as cm:
                func({"ownerToken": value, "recipientToken": value})
            self.assertEqual(cm.exception.status, 404)
        recipient_status = requests.get_recipient(self.recipient)
        self.assertFalse({"ownerToken", "documents", "priorDeposits10k"} & recipient_status.keys())
        db = self.store / "requests.sqlite3"
        self.assertEqual(db.stat().st_mode & 0o777, 0o600)
        for token in [*self.owner.values(), *self.recipient.values()]:
            self.assertNotIn(token.encode(), db.read_bytes())

    def test_submit_confirm_retry_and_replace(self):
        try:
            data = pdf(lines())
        except ImportError:
            self.skipTest("한국어 원본 PDF 생성에는 PyMuPDF가 필요합니다.")
        self.assertEqual(self.submit(data)["status"], "ready")
        state = requests.get_request(self.owner)
        self.assertIsNone(state["priorDeposits10k"])
        before = state["documents"][0]
        confirm = {**self.owner, "kind": "fixedDate", "fingerprint": before["fingerprint"]}
        self.assertEqual(requests.review_request(confirm)["priorDeposits10k"], 35000)
        self.assertEqual(requests.confirmed_prior(self.created["ownerToken"], ADDRESS), 35000)
        self.assertIsNone(requests.confirmed_prior(self.created["ownerToken"], ADDRESS + "0"))
        self.assertEqual(self.submit(data)["status"], "confirmed")
        self.assertEqual(self.submit(pdf(lines(total="선순위 보증금 총액: 0원")))["status"], "ready")
        self.assertIsNone(requests.get_request(self.owner)["priorDeposits10k"])
        with self.assertRaises(requests.DocumentRequestError) as cm:
            requests.review_request(confirm)
        self.assertEqual(cm.exception.status, 409)
        fresh = requests.get_request(self.owner)["documents"][0]
        self.assertEqual(requests.review_request({**confirm, "fingerprint": fresh["fingerprint"]})["priorDeposits10k"], 0)
        self.assertNotIn(b"%PDF-", (self.store / "requests.sqlite3").read_bytes())
        self.assertEqual(requests.get_recipient(self.recipient)["submitted"], ["fixedDate"])
        self.assertEqual(self.submit(pdf([]))["status"], "needs_review")
        self.assertIsNone(requests.get_request(self.owner)["priorDeposits10k"])

    def test_concurrent_retries_publish_one_complete_document(self):
        raw = b"%PDF-synthetic"  # parsing itself is covered by the real PDF round trip
        with patch.object(requests, "_pdf_lines", return_value=[lines()]):
            with ThreadPoolExecutor(max_workers=4) as pool:
                outcomes = list(pool.map(self.submit, [raw] * 4))
        self.assertEqual({o["status"] for o in outcomes}, {"ready"})
        state = requests.get_request(self.owner)
        self.assertEqual(len(state["documents"]), 1)
        doc = state["documents"][0]
        confirm = {**self.owner, "kind": doc["kind"], "fingerprint": doc["fingerprint"]}
        with ThreadPoolExecutor(max_workers=3) as pool:
            reviewed = list(pool.map(requests.review_request, [confirm] * 3))
        self.assertTrue(all(s["priorDeposits10k"] == 35000 for s in reviewed))

    def test_extend_existing_request_is_additive_and_owner_only(self):
        with patch.object(requests, "_pdf_lines", return_value=[lines()]):
            self.submit(b"%PDF-example")
        doc = requests.get_request(self.owner)["documents"][0]
        requests.review_request({**self.owner, "kind": "fixedDate", "fingerprint": doc["fingerprint"]})
        additions = [["moveIn"], ["nationalTax"], ["localTax"], ["nationalTax"]]
        with ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(lambda kinds: requests.extend_request({**self.owner, "requested": kinds}), additions))
        view = requests.get_request(self.owner)
        self.assertEqual(set(view["requested"]), set(requests.KINDS))
        self.assertEqual(view["expiresAt"], self.created["expiresAt"])
        self.assertEqual(view["priorDeposits10k"], 35000)
        self.assertEqual(requests.get_recipient(self.recipient)["requested"], view["requested"])
        with self.assertRaises(requests.DocumentRequestError):
            requests.extend_request({**self.recipient, "requested": ["nationalTax"]})
        with self.assertRaises(requests.DocumentRequestError):
            requests.extend_request({**self.owner, "requested": ["identityCard"]})

    def test_maturing_stored_confirmation_relocks_at_read(self):
        today = requests._today()
        issued = (today - timedelta(days=30)).isoformat()
        raw = b"%PDF-freshness"
        with patch.object(requests, "_pdf_lines", return_value=[lines(issued=issued)]):
            self.assertEqual(self.submit(raw)["status"], "ready")
        doc = requests.get_request(self.owner)["documents"][0]
        confirm = {**self.owner, "kind": "fixedDate", "fingerprint": doc["fingerprint"]}
        self.assertEqual(requests.review_request(confirm)["priorDeposits10k"], 35000)
        with patch.object(requests, "_today", return_value=today + timedelta(days=1)):
            self.assertIsNone(requests.confirmed_prior(self.owner["ownerToken"], ADDRESS))
            self.assertEqual(requests.get_request(self.owner)["documents"][0]["status"], "needs_review")
            self.assertEqual(self.submit(raw)["status"], "needs_review")
            with self.assertRaises(requests.DocumentRequestError) as blocked:
                requests.review_request(confirm)
            self.assertEqual(blocked.exception.status, 422)

    def test_unconfirmed_unknown_and_expired_tokens_remain_blocked(self):
        self.assertIsNone(requests.confirmed_prior(self.created["recipientToken"], ADDRESS))
        with sqlite3.connect(self.store / "requests.sqlite3") as db:
            db.execute("UPDATE requests SET expires=1")
        self.assertIsNone(requests.confirmed_prior(self.created["ownerToken"], ADDRESS))
        with self.assertRaises(requests.DocumentRequestError) as cm:
            requests.get_recipient(self.recipient)
        self.assertEqual(cm.exception.status, 404)

    def test_unrequested_invalid_and_oversize_submission(self):
        for payload, status in [
            ({"kind": "nationalTax", "fileBase64": ""}, 400),
            ({"kind": "fixedDate", "fileBase64": "!"}, 400),
            ({"kind": "fixedDate", "fileBase64": base64.b64encode(b"text").decode()}, 400),
            ({"kind": "fixedDate", "fileBase64": "A" * (6 * 1024 * 1024)}, 413),
        ]:
            with self.subTest(status=status), self.assertRaises(requests.DocumentRequestError) as cm:
                requests.submit_document({**self.recipient, **CONSENT, **payload})
            self.assertEqual(cm.exception.status, status)


if __name__ == "__main__":
    unittest.main()
