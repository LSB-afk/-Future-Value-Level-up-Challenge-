import unittest
import xml.etree.ElementTree as ET
from unittest.mock import patch

import building_register as building
from document_requests import DocumentRequestError

ROAD = "서울특별시 은평구 통일로 838-21"
LOT = "서울특별시 은평구 불광동 111번지"
PNU = "1138010300101110000"


def response(rows, code="00"):
    root = ET.fromstring("<response><header/><body><items/></body></response>")
    ET.SubElement(root.find("header"), "resultCode").text = code
    ET.SubElement(root.find("body"), "totalCount").text = str(len(rows))
    for row in rows:
        item = ET.SubElement(root.find("body/items"), "item")
        for name, value in row.items():
            ET.SubElement(item, name).text = value
    return root


class BuildingLookupTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(patch.object(building, "env_key", return_value="test"))
        self.geo = self.enterContext(patch.object(building, "pnu_from_address", return_value=(PNU, "")))
        self.http = self.enterContext(patch.object(building, "request_xml"))
        self.row = {"newPlatPlc": ROAD, "platPlc": LOT, "dongNm": "101동", "sigunguCd": "11380",
                    "bun": "0111", "mainPurpsCdNm": "공동주택", "useAprDay": "20200322", "grndFlrCnt": "13"}

    def test_match_at_building_scope_with_no_unit_disclosure(self):
        self.http.return_value = response([self.row, {**self.row, "dongNm": "102동"}])
        result = building.lookup_building(ROAD + " 101동 301호")
        self.geo.assert_called_once_with(ROAD)
        self.assertEqual(len(result["records"]), 1)
        self.assertEqual(result["records"][0]["approvedAt"], "2020-03-22")
        self.assertNotIn("violation", result["records"][0])

    def test_land_lot_address_with_suffix(self):
        self.http.return_value = response([self.row])
        self.assertEqual(building.lookup_building(LOT)["records"][0]["mainUse"], "공동주택")

    def test_no_cross_address_or_lot_matches(self):
        self.http.return_value = response([{**self.row, "bun": "0112"}, {**self.row, "newPlatPlc": ROAD+"0"}])
        self.assertEqual(building.lookup_building(ROAD)["records"], [])

    def test_disconnected_or_declined_provider(self):
        with patch.object(building, "env_key", return_value=""):
            self.assertFalse(building.building_status()["available"])
            with self.assertRaises(DocumentRequestError):
                building.lookup_building(ROAD)
            self.geo.assert_not_called()
        self.http.return_value = response([], "30")
        with self.assertRaises(DocumentRequestError) as failed:
            building.lookup_building(ROAD)
        self.assertEqual(failed.exception.status, 502)
