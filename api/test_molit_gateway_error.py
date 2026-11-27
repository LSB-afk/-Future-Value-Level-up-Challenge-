"""국토부 실거래 API 게이트웨이 오류가 '거래 없음'이 아니라 'API 오류'로 보고되는지."""
import unittest
import xml.etree.ElementTree as ET
from unittest.mock import patch

import real_estate_price_adapters as rea

GATEWAY_ERROR = """<?xml version="1.0" encoding="UTF-8"?>
<OpenAPI_ServiceResponse><cmmMsgHeader><errMsg>HTTP_ERROR</errMsg>
<returnAuthMsg>HTTP 에러</returnAuthMsg><returnReasonCode>04</returnReasonCode></cmmMsgHeader></OpenAPI_ServiceResponse>"""
NORMAL_EMPTY = """<response><header><resultCode>000</resultCode><resultMsg>OK</resultMsg></header>
<body><items></items><totalCount>0</totalCount></body></response>"""


class GatewayErrorTests(unittest.TestCase):
    def test_gateway_error_is_an_error(self):
        self.assertEqual(rea.response_error(ET.fromstring(GATEWAY_ERROR)), "04: HTTP 에러")
        self.assertEqual(rea.response_error(ET.fromstring(NORMAL_EMPTY)), "")

    def test_month_fetch_reports_gateway_error(self):
        with patch.object(rea, "request_xml", return_value=ET.fromstring(GATEWAY_ERROR)):
            items, error, partial = rea._fetch_month_pages(rea.MOLIT_TRADE_ENDPOINT, "key", "11680", "202609",
                                                           rea.parse_trade_item)
        self.assertEqual((items, partial), ([], False))
        self.assertIn("04", error)


if __name__ == "__main__":
    unittest.main()
