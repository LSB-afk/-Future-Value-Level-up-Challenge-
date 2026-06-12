"""Public real-estate price adapters for MoveValue.

The adapter is intentionally optional. It never requires API keys for the app
to boot, but it can enrich a selected apartment detail with MOLIT transaction
records when service keys are provided through environment variables.
"""

from __future__ import annotations

import os
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Any


MOLIT_TRADE_ENDPOINT = "https://apis.data.go.kr/1613000/RTMSDataSvcAptTradeDev/getRTMSDataSvcAptTradeDev"
MOLIT_RENT_ENDPOINT = "https://apis.data.go.kr/1613000/RTMSDataSvcAptRent/getRTMSDataSvcAptRent"

TRADE_KEY_ENVS = ("MOLIT_APT_TRADE_KEY", "MOLIT_SERVICE_KEY", "MOLIT_API_KEY", "PUBLIC_DATA_API_KEY")
RENT_KEY_ENVS = ("MOLIT_APT_RENT_KEY", "MOLIT_SERVICE_KEY", "MOLIT_API_KEY", "PUBLIC_DATA_API_KEY")
PUBLIC_PRICE_KEY_ENVS = ("PUBLIC_PRICE_API_KEY", "OFFICIAL_PRICE_API_KEY", "MOLIT_PUBLIC_PRICE_KEY", "NSDI_API_KEY")

SEOUL_LAWD_CODES = {
    "종로구": "11110",
    "중구": "11140",
    "용산구": "11170",
    "성동구": "11200",
    "광진구": "11215",
    "동대문구": "11230",
    "중랑구": "11260",
    "성북구": "11290",
    "강북구": "11305",
    "도봉구": "11320",
    "노원구": "11350",
    "은평구": "11380",
    "서대문구": "11410",
    "마포구": "11440",
    "양천구": "11470",
    "강서구": "11500",
    "구로구": "11530",
    "금천구": "11545",
    "영등포구": "11560",
    "동작구": "11590",
    "관악구": "11620",
    "서초구": "11650",
    "강남구": "11680",
    "송파구": "11710",
    "강동구": "11740",
}


def env_key(*names: str) -> str:
    for name in names:
        value = os.getenv(name, "").strip()
        if value:
            return value
    return ""


def price_credential_status() -> dict[str, bool]:
    return {
        "molitTrade": bool(env_key(*TRADE_KEY_ENVS)),
        "molitRent": bool(env_key(*RENT_KEY_ENVS)),
        "publicPrice": bool(env_key(*PUBLIC_PRICE_KEY_ENVS)),
    }


def lawd_code_for(apartment: dict[str, Any]) -> str:
    district = str(apartment.get("district") or "")
    if district in SEOUL_LAWD_CODES:
        return SEOUL_LAWD_CODES[district]
    address = str(apartment.get("address") or "")
    for name, code in SEOUL_LAWD_CODES.items():
        if name in address:
            return code
    return ""


def recent_deal_months(count: int = 9) -> list[str]:
    now = datetime.now()
    year = now.year
    month = now.month
    rows = []
    for _ in range(count):
        rows.append(f"{year}{month:02d}")
        month -= 1
        if month == 0:
            year -= 1
            month = 12
    return rows


def normalize_name(value: str) -> str:
    return re.sub(r"[^0-9a-z가-힣]", "", str(value or "").lower())


def money_10k(value: Any) -> int:
    text = str(value or "").replace(",", "").replace(" ", "").strip()
    if not text:
        return 0
    try:
        return int(round(float(text)))
    except ValueError:
        return 0


def text_of(item: ET.Element, *names: str) -> str:
    for name in names:
        node = item.find(name)
        if node is not None and node.text:
            return node.text.strip()
    return ""


def request_xml(endpoint: str, params: dict[str, str]) -> ET.Element:
    encoded = urllib.parse.urlencode(params, safe="%")
    request = urllib.request.Request(f"{endpoint}?{encoded}", headers={"User-Agent": "MoveValue/0.1"})
    with urllib.request.urlopen(request, timeout=18) as response:  # noqa: S310 - official public API endpoint.
        return ET.fromstring(response.read())


def response_error(root: ET.Element) -> str:
    header = root.find(".//header")
    if header is None:
        return ""
    code = text_of(header, "resultCode")
    message = text_of(header, "resultMsg")
    if code and code != "00":
        return f"{code}: {message or '공공데이터 API 오류'}"
    return ""


def apt_name_matches(apartment: dict[str, Any], record_name: str) -> bool:
    target = normalize_name(apartment.get("name", ""))
    candidate = normalize_name(record_name)
    if not target or not candidate:
        return False
    return target in candidate or candidate in target


def parse_trade_item(item: ET.Element) -> dict[str, Any]:
    return {
        "type": "매매",
        "name": text_of(item, "aptNm", "아파트"),
        "amount10k": money_10k(text_of(item, "dealAmount", "거래금액")),
        "exclusiveM2": float(text_of(item, "excluUseAr", "전용면적") or 0),
        "floor": text_of(item, "floor", "층"),
        "dealYear": text_of(item, "dealYear", "년"),
        "dealMonth": text_of(item, "dealMonth", "월"),
        "dealDay": text_of(item, "dealDay", "일"),
        "sourceMode": "molit_trade_api",
    }


def parse_rent_item(item: ET.Element) -> dict[str, Any]:
    return {
        "type": "전월세",
        "name": text_of(item, "aptNm", "아파트"),
        "deposit10k": money_10k(text_of(item, "deposit", "보증금액")),
        "monthlyRent10k": money_10k(text_of(item, "monthlyRent", "월세금액")),
        "exclusiveM2": float(text_of(item, "excluUseAr", "전용면적") or 0),
        "floor": text_of(item, "floor", "층"),
        "dealYear": text_of(item, "dealYear", "년"),
        "dealMonth": text_of(item, "dealMonth", "월"),
        "dealDay": text_of(item, "dealDay", "일"),
        "sourceMode": "molit_rent_api",
    }


def fetch_molit_records(
    endpoint: str,
    service_key: str,
    lawd_code: str,
    parser,
    apartment: dict[str, Any],
    months: int = 9,
) -> tuple[list[dict[str, Any]], str]:
    records: list[dict[str, Any]] = []
    last_error = ""
    for deal_ym in recent_deal_months(months):
        params = {
            "serviceKey": service_key,
            "LAWD_CD": lawd_code,
            "DEAL_YMD": deal_ym,
            "pageNo": "1",
            "numOfRows": "100",
        }
        try:
            root = request_xml(endpoint, params)
        except Exception as exc:  # noqa: BLE001 - live adapter must not break prototype.
            last_error = str(exc)
            continue
        error = response_error(root)
        if error:
            last_error = error
            continue
        for item in root.findall(".//item"):
            parsed = parser(item)
            if parsed.get("amount10k") or parsed.get("deposit10k"):
                if apt_name_matches(apartment, parsed.get("name", "")):
                    records.append(parsed)
        if records:
            break
    return records, last_error


def status_base(configured: bool, lawd_code: str, label: str) -> dict[str, Any]:
    if not configured:
        mode = "not_configured"
        note = f"{label} API 키가 환경변수에 없어 추정값을 사용합니다."
    elif not lawd_code:
        mode = "missing_lawd_code"
        note = "법정동 코드 매핑이 없어 live 조회를 건너뜁니다."
    else:
        mode = "configured"
        note = "API 키와 법정동 코드가 있어 live 조회를 시도할 수 있습니다."
    return {"configured": configured, "lawdCode": lawd_code, "mode": mode, "recordCount": 0, "note": note}


def enrich_market_from_live(apartment: dict[str, Any], fallback_market: dict[str, Any]) -> dict[str, Any]:
    market = dict(fallback_market)
    lawd_code = lawd_code_for(apartment)
    trade_key = env_key(*TRADE_KEY_ENVS)
    rent_key = env_key(*RENT_KEY_ENVS)
    public_price_key = env_key(*PUBLIC_PRICE_KEY_ENVS)

    live_status = {
        "molitTrade": status_base(bool(trade_key), lawd_code, "국토교통부 아파트 매매 실거래가"),
        "molitRent": status_base(bool(rent_key), lawd_code, "국토교통부 아파트 전월세 실거래가"),
        "publicPrice": {
            "configured": bool(public_price_key),
            "mode": "requires_pnu_mapping" if public_price_key else "not_configured",
            "recordCount": 0,
            "note": "공동주택 공시가격은 PNU/공시가격 식별자 매핑 후 live 보정합니다."
            if public_price_key
            else "공시가격 API 키가 없어 생활권 기반 추정값을 사용합니다.",
        },
    }

    if trade_key and lawd_code:
        records, error = fetch_molit_records(MOLIT_TRADE_ENDPOINT, trade_key, lawd_code, parse_trade_item, apartment)
        live_status["molitTrade"].update(
            {
                "mode": "live_api" if records else "no_matching_record",
                "recordCount": len(records),
                "error": error,
                "note": "단지명 매칭 실거래가를 상세 가격에 반영했습니다." if records else "최근 9개월 내 단지명 매칭 매매 실거래가가 없습니다.",
            }
        )
        if records:
            recent = sorted(records, key=lambda item: (item.get("dealYear", ""), item.get("dealMonth", ""), item.get("dealDay", "")), reverse=True)[0]
            market["recentSale10k"] = recent["amount10k"]
            market["molitTradeRecords"] = records[:6]
            market["sourceMode"] = "molit_live_trade_partial"
            market["sourceLabel"] = "국토교통부 매매 실거래가 live 보정 + 공개 단지정보"

    if rent_key and lawd_code:
        records, error = fetch_molit_records(MOLIT_RENT_ENDPOINT, rent_key, lawd_code, parse_rent_item, apartment)
        jeonse_records = [item for item in records if not item.get("monthlyRent10k")]
        monthly_records = [item for item in records if item.get("monthlyRent10k")]
        live_status["molitRent"].update(
            {
                "mode": "live_api" if records else "no_matching_record",
                "recordCount": len(records),
                "error": error,
                "note": "단지명 매칭 전월세 실거래가를 상세 가격에 반영했습니다." if records else "최근 9개월 내 단지명 매칭 전월세 실거래가가 없습니다.",
            }
        )
        if jeonse_records:
            recent = sorted(jeonse_records, key=lambda item: (item.get("dealYear", ""), item.get("dealMonth", ""), item.get("dealDay", "")), reverse=True)[0]
            market["recentJeonse10k"] = recent["deposit10k"]
        if monthly_records:
            recent = sorted(monthly_records, key=lambda item: (item.get("dealYear", ""), item.get("dealMonth", ""), item.get("dealDay", "")), reverse=True)[0]
            market["monthlyDeposit10k"] = recent["deposit10k"]
            market["monthlyRent10k"] = recent["monthlyRent10k"]
        if records:
            market["molitRentRecords"] = records[:6]
            market["sourceMode"] = "molit_live_trade_rent_partial"
            market["sourceLabel"] = "국토교통부 실거래가 live 보정 + 공개 단지정보"

    if market.get("recentSale10k"):
        market["jeonseRatio"] = round((float(market.get("recentJeonse10k") or 0) / float(market["recentSale10k"])) * 100, 1)
        market["saleGapPercent"] = round(
            ((float(market["recentSale10k"]) - float(market.get("surroundingAverageSale10k") or market["recentSale10k"])) / float(market.get("surroundingAverageSale10k") or market["recentSale10k"])) * 100,
            1,
        )
    if market.get("officialPrice10k"):
        market["depositOfficialRatio"] = round((float(market.get("recentJeonse10k") or 0) / float(market["officialPrice10k"])) * 100, 1)

    market["liveStatus"] = live_status
    return market
