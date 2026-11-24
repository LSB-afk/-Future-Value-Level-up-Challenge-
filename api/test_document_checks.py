"""PDF-only evidence and property scoping for the unified document panel."""
import unittest
from datetime import timedelta
from unittest.mock import patch

import document_checks as checks


BASE = "서울특별시 은평구 통일로 838-21"
BLOCK = BASE + " 101동"
ADDRESS = BLOCK + " 301호"
DAY = checks._today().isoformat()


def building(address=ADDRESS, issue=DAY, flag="위반건축물 여부: 해당없음", title="집합건축물대장(전유부, 갑)"):
    return [title, "도로명주소: " + address, "발급일자: " + issue, "주용도: 공동주택(아파트)", flag]


class Checks(unittest.TestCase):
    def test_building_real_pdf_and_original_line_locations(self):
        import pymupdf
        with pymupdf.open() as pdf:
            page = pdf.new_page()
            for n, line in enumerate(building()):
                page.insert_text((25, 38 + n * 23), line, fontsize=11, fontname="korea")
            result = checks.read_document_pdf("building", ADDRESS, pdf.tobytes())
        self.assertEqual((result["status"], result["addressStatus"], result["scope"]), ("ready", "exact", "unit"))
        self.assertEqual(result["issuedAt"], DAY)
        finding = next(f for f in result["findings"] if f["field"] == "violation")
        self.assertEqual(finding["code"], "no")
        self.assertIn("해당 없음", finding["value"])
        self.assertTrue(any(e["page"] == 1 and e["line"] == 5 for e in result["evidence"]))

    def test_no_flag_never_means_no_violation(self):
        for flag in ("", "위반건축물", "위반건축물 여부", "위반건축물 여부: □있음 □없음", "변동사항: 위반건축물 해제"):
            with self.subTest(flag=flag):
                result = checks._analyze("building", ADDRESS, [building(flag=flag)])
                self.assertEqual(result["status"], "needs_review")
                self.assertFalse(any(f["field"] == "violation" for f in result["findings"]))
        for flag in ("[위반건축물]", "위반건축물 여부: 해당"):
            result = checks._analyze("building", ADDRESS, [building(flag=flag)])
            violation = next(item for item in result["findings"] if item["field"] == "violation")
            self.assertEqual((result["status"], violation["value"], violation["code"]), ("ready", "위반건축물로 기재", "yes"))
            for mismatch in (building(address=ADDRESS + "9", flag=flag), building(issue="2020-01-01", flag=flag)):
                blocked = checks._analyze("building", ADDRESS, [mismatch])
                self.assertFalse(any(f.get("code") == "yes" for f in blocked["findings"]))
        result = checks._analyze("building", ADDRESS, [building() + ["[위반건축물]"]])
        self.assertEqual(result["status"], "needs_review")

    def test_stale_date_and_other_address_suppress_favorable_findings(self):
        for rows in (building(address=ADDRESS.replace("301호", "302호")), building(address=ADDRESS.replace("101동", "102동")),
                     building(address=ADDRESS.replace("838-21", "838-210")), building(issue="무효"),
                     building(issue=(checks._today() - timedelta(days=31)).isoformat()),
                     building(issue=(checks._today() + timedelta(days=1)).isoformat()),
                     building(title="설명자료입니다. 건축물대장 확인 요망"), [], building() + ["발급일자: 2025-01-01"]):
            with self.subTest(rows=rows):
                result = checks._analyze("building", ADDRESS, [rows])
                self.assertEqual((result["status"], result["findings"]), ("needs_review", []))

    def test_building_vs_unit_and_separate_room_header(self):
        result = checks._analyze("building", ADDRESS, [building(address=BLOCK, title="집합건축물대장(표제부, 갑)")])
        self.assertEqual((result["status"], result["addressStatus"], result["scope"]), ("ready", "whole_building", "building"))
        unit_only = building(address=BASE) + ["동명칭", "101동", "호명칭", "301호"]
        self.assertEqual(checks._analyze("building", ADDRESS, [unit_only])["addressStatus"], "exact")
        self.assertTrue(checks._analyze("building", BASE, [unit_only])["issues"])
        self.assertEqual(checks._analyze("building", ADDRESS, [building(address=BLOCK)])["status"], "needs_review")

    def test_other_target_unrelated_findings_multiple_pages(self):
        unknown = checks._analyze("building", ADDRESS, [building(flag=""), ["위반건축물 여부: 없음"]])
        self.assertEqual((unknown["status"], unknown["findings"]), ("needs_review", []))
        repeated_title = ["집합건축물대장(전유부, 갑)", "위반건축물 여부: 없음"]
        self.assertEqual(checks._analyze("building", ADDRESS, [building(flag=""), repeated_title])["findings"], [])
        another = building(address=ADDRESS.replace("301호", "302호"))
        self.assertEqual(checks._analyze("building", ADDRESS, [building(), another])["status"], "needs_review")

    def test_broker_cross_check_no_personal_addresses_or_ids_kept(self):
        rows = ["중개대상물 확인·설명서[Ⅰ] (주거용 건축물)", "① 대상물건의 표시", "소재지", ADDRESS,
                "작성일자: " + DAY, "중개사무소 등록번호: 11380-2024-00001",
                "소유자 현황", "주소: 개인정보주소 33", "소유자 성명: 홍길동", "주민등록번호: 900101-1234567"]
        result = checks._analyze("broker", ADDRESS, [rows])
        self.assertEqual((result["status"], result["findings"][0]["value"]), ("ready", "11380-2024-00001"))
        for private in ["홍길동", "개인정보주소", "900101"]:
            self.assertNotIn(private, str(result))
        self.assertIn("공제", result["notes"][0])
        rows[5] = "중개사무소 등록번호: 900101-1234567"
        self.assertFalse(checks._analyze("broker", ADDRESS, [rows])["findings"])
        rows = [rows[0], "중개사무소 소재지: " + ADDRESS, "작성일자: " + DAY]
        self.assertFalse(checks._analyze("broker", ADDRESS, [rows])["addressMatched"])

    def test_numbered_broker_form_recognizes_receipt_date_and_signatory_field(self):
        today = checks._today()
        pages = [["(2쪽 중 제1쪽)", "중개대상물 확인·설명서 [Ⅰ]", "① 대상물건의 표시", "소재지", ADDRESS],
                 ["(2쪽 중 제2쪽)", "손해배상책임 보장 증명서류(사본 또는 전자문서)를 수령합니다.",
                  f"{today.year}년 {today.month}월 {today.day}일", "개업공인중개사", "등록번호", "11380-2024-00001"]]
        result = checks._analyze("broker", ADDRESS, pages)
        self.assertEqual((result["status"], result["issuedAt"], result["findings"][0]["value"]),
                         ("ready", DAY, "11380-2024-00001"))
        pages[1][0] = "(2쪽 중 제1쪽)"
        self.assertEqual(checks._analyze("broker", ADDRESS, pages)["status"], "needs_review")

    def test_bad_kind_address_or_body_are_rejected_before_pdf_worker(self):
        with patch.object(checks, "_pdf_lines") as worker:
            for fields in [("ownerId", ADDRESS, b"%PDF-doc"), ("building", "x", b"%PDF-doc"),
                           ("building", ADDRESS, b"plain"), ("building", ADDRESS, b"%PDF-" + b"x" * checks.MAX_PDF_BYTES)]:
                with self.assertRaises(checks.DocumentRequestError):
                    checks.read_document_pdf(*fields)
            worker.assert_not_called()


if __name__ == "__main__":
    unittest.main()
