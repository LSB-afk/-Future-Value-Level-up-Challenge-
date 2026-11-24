import os
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from unittest.mock import patch

import fitz

import registry_lookup as registry


ADDRESS = "대전광역시 유성구 대학로 123"
FULL_UNIT = ADDRESS + " 102동 301호"
ID = "11012020123456"
NOW = date.today().isoformat()
UNIT_DESC = "[집합건물] " + ADDRESS + " 제102동 제3층 제301호"
RIGHTS = ["1 근저당권설정", "채권최고액 금120,000,000원"]


def document(rights=RIGHTS, desc="[건물] " + ADDRESS, issued_at=NOW, prop_id=ID):
    rows = [
        "등기사항전부증명서",
        desc,
        "고유번호 " + prop_id,
        "열람일시: " + issued_at,
        "갑구",
        "주요 등기사항 요약 (참고용)",
        "3. (근)저당권 및 전세권 등 (을구)",
        *rights,
        "참고사항",
    ]
    with fitz.open() as doc:
        page = doc.new_page()
        for n, line in enumerate(rows):
            page.insert_text((16, 30 + n * 20), line, fontname="korea", fontsize=11)
        return doc.tobytes()


class RegistryTest(unittest.TestCase):
    def test_single_active_row_and_exact_evidence(self):
        result = registry.read_registry_pdf(ADDRESS, document())
        self.assertFalse(result["reviewRequired"], result["reason"])
        self.assertEqual(result["mortgageMax10k"], 12000)
        self.assertEqual(result["issuedAt"], NOW)
        self.assertTrue(
            any(
                "120,000,000" in r["text"] and r["page"] == 1
                for r in result["evidence"]
            )
        )

    def test_distinct_active_mortgage_ranks_and_duplicate_guard(self):
        rows = RIGHTS + ["3 근저당권설정", "채권최고액 금50,000,000원"]
        self.assertEqual(
            registry.read_registry_pdf(ADDRESS, document(rows))["mortgageMax10k"], 17000
        )
        duplicate = RIGHTS + ["1 근저당권설정", "채권최고액 금50,000,000원"]
        self.assertTrue(
            registry.read_registry_pdf(ADDRESS, document(duplicate))["reviewRequired"]
        )

    def test_pdf_table_cells_across_lines_and_empty_joint_annotation(self):
        rows = [
            "1",
            "근저당권설정",
            "채권최고액",
            "금120,000,000원",
            "공동담보목록 없음",
            "4",
            "근저당권설정",
            "채권최고액 금80,000,000원",
        ]
        result = registry.read_registry_pdf(ADDRESS, document(rows))
        self.assertEqual(result["mortgageMax10k"], 20000, result)
        self.assertTrue(
            any("120,000,000원" in row["text"] for row in result["evidence"])
        )
        self.assertIsNone(
            registry.read_registry_pdf(ADDRESS, document(rows + ["기록사항 없음"]))[
                "mortgageMax10k"
            ]
        )

    def test_unambiguous_empty_section(self):
        r = registry.read_registry_pdf(ADDRESS, document(["기록사항 없음"]))
        self.assertEqual(r["mortgageMax10k"], 0)

    def test_reject_units_other_address_old_and_multiple_or_cancelled_liens(self):
        fixtures = [
            (FULL_UNIT, document(desc=UNIT_DESC.replace("301호", "302호"))),
            (ADDRESS, document(desc=UNIT_DESC)),
            (ADDRESS, document(desc="[건물] " + ADDRESS + "4")),
            (ADDRESS, document(issued_at="2000-01-01")),
            (ADDRESS, document(rights=RIGHTS + ["공동담보목록"])),
            (ADDRESS, document(rights=RIGHTS + ["말소"])),
            (
                ADDRESS,
                document(rights=RIGHTS + ["2 근저당권설정", "채권최고액 금5,000만원"]),
            ),
            (ADDRESS, document(rights=[])),
        ]
        for addr, fixture in fixtures:
            with self.subTest(addr=addr):
                result = registry.read_registry_pdf(addr, fixture)
                self.assertTrue(result["reviewRequired"], result)
                self.assertIsNone(result["mortgageMax10k"])

    def test_matching_selected_unit(self):
        result = registry.read_registry_pdf(FULL_UNIT, document(desc=UNIT_DESC))
        self.assertFalse(result["reviewRequired"], result)

    def test_named_blocks_have_to_match_even_with_one_candidate(self):
        for block in ("A", "가", "101-1"):
            desc = "[집합건물] " + ADDRESS + " " + block + "동 제301호"
            self.assertTrue(
                registry.read_registry_pdf(ADDRESS + " 301호", document(desc=desc))[
                    "reviewRequired"
                ]
            )
            result = registry.read_registry_pdf(
                ADDRESS + " " + block + "동 301호", document(desc=desc)
            )
            self.assertFalse(result["reviewRequired"], result)

    def test_account_missing_never_fetches(self):
        with patch.dict(os.environ, {k: "" for k in registry._CREDS}), patch.object(
            registry.urllib.request, "build_opener"
        ) as opener:
            with self.assertRaises(registry.RegistryError):
                registry.search_registry(ADDRESS)
            opener.assert_not_called()

    def test_incomplete_condo_address_never_offers_paid_selection(self):
        entry = {
            "get부동산고유번호": ID,
            "get부동산소재지번": UNIT_DESC,
            "get구분": "집합건물",
            "get상태": "현행",
        }
        for addr, entries in [
            (ADDRESS, [entry]),
            (ADDRESS + " 301호", [entry]),
            (FULL_UNIT, [entry, {**entry, "get부동산고유번호": "11012020123457"}]),
            (
                FULL_UNIT,
                [{**entry, "get부동산소재지번": UNIT_DESC.replace("123", "1234")}],
            ),
        ]:
            with self.subTest(addr=addr), patch.object(
                registry, "_provider", return_value={"list": entries}
            ) as provider:
                with self.assertRaises(registry.RegistryError):
                    registry.search_registry(addr)
                self.assertEqual(provider.call_count, 1)
                self.assertEqual(provider.call_args.args[0], "in0004000168")
        self.assertTrue(
            registry.read_registry_pdf(ADDRESS + " 301호", document(desc=UNIT_DESC))[
                "reviewRequired"
            ]
        )

    def test_explicitly_absent_joint_collateral_does_not_hide_rights(self):
        for marker in [["공동담보목록 없음"], ["공동담보목록", "기록사항 없음"]]:
            result = registry.read_registry_pdf(ADDRESS, document(RIGHTS + marker))
            self.assertEqual(result["mortgageMax10k"], 12000, result)
            self.assertIsNone(
                registry.read_registry_pdf(ADDRESS, document(marker))["mortgageMax10k"]
            )
        for marker in [
            ["공동담보목록 제 2020-11호"],
            ["공동담보목록 없음", "공동담보 목록 제123호"],
        ]:
            self.assertIsNone(
                registry.read_registry_pdf(ADDRESS, document(RIGHTS + marker))[
                    "mortgageMax10k"
                ]
            )

    def test_pdf_page_and_process_limits(self):
        with fitz.open() as doc:
            for _ in range(26):
                doc.new_page()
            with self.assertRaises(registry.RegistryError) as failure:
                registry.read_registry_pdf(ADDRESS, doc.tobytes())
        self.assertEqual(failure.exception.http_status, 422)
        with patch.object(
            registry,
            "_pdf_lines",
            side_effect=registry.DocumentRequestError(429, "요청 대기"),
        ):
            with self.assertRaises(registry.RegistryError) as failure:
                registry.read_registry_pdf(ADDRESS, document())
        self.assertEqual(failure.exception.http_status, 429)

    def test_checked_selection_tied_to_address_and_once_only(self):
        counter = []

        def provider(endpoint, payload):
            if endpoint == "in0004000168":
                return {
                    "list": [
                        {
                            "get부동산고유번호": ID,
                            "get부동산소재지번": UNIT_DESC,
                            "get구분": "집합건물",
                            "get상태": "현행",
                        }
                    ]
                }
            self.assertEqual(payload["display"], "1")
            counter.append(1)
            return {
                "outList": {"get고유번호": ID},
                "pdfHexString": document(desc=UNIT_DESC).hex(),
            }

        with patch.object(registry, "_provider", side_effect=provider), patch.dict(
            os.environ, {k: "test" for k in registry._CREDS}
        ):
            item = registry.search_registry(FULL_UNIT)["items"][0]
            for addr, confirm in [
                (FULL_UNIT, False),
                ("대전광역시 유성구 대학로 987", True),
            ]:
                with self.assertRaises(registry.RegistryError):
                    registry.fetch_registry(addr, item["id"], confirm)

            def fetch(_):
                try:
                    return registry.fetch_registry(FULL_UNIT, item["id"], True)
                except registry.RegistryError:
                    return None

            with ThreadPoolExecutor(max_workers=2) as ex:
                outcomes = list(ex.map(fetch, range(2)))
            self.assertEqual(len(counter), 1)
            success = next(r for r in outcomes if r)
            self.assertEqual(success["mortgageMax10k"], 12000)

    def test_scanned_or_corrupt_pdf(self):
        with self.assertRaises(registry.RegistryError):
            registry.read_registry_pdf(ADDRESS, b"bad file")
        with fitz.open() as doc:
            doc.new_page()
            result = registry.read_registry_pdf(ADDRESS, doc.tobytes())
        self.assertTrue(result["reviewRequired"])


if __name__ == "__main__":
    unittest.main()
