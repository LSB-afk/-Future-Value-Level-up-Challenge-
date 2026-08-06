"""Public real-estate price adapters for MoveValue.

The adapter is intentionally optional. It never requires API keys for the app
to boot, but it can enrich a selected apartment detail with MOLIT transaction
records when service keys are provided through environment variables.
"""

from __future__ import annotations

import json
import os
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Any

from env_loader import load_dotenv


load_dotenv()

MOLIT_TRADE_ENDPOINT = "https://apis.data.go.kr/1613000/RTMSDataSvcAptTradeDev/getRTMSDataSvcAptTradeDev"
MOLIT_RENT_ENDPOINT = "https://apis.data.go.kr/1613000/RTMSDataSvcAptRent/getRTMSDataSvcAptRent"
PUBLIC_PRICE_ENDPOINT = "https://api.vworld.kr/ned/data/getApartHousingPriceAttr"
KAKAO_ADDRESS_ENDPOINT = "https://dapi.kakao.com/v2/local/search/address.json"

TRADE_KEY_ENVS = ("MOLIT_APT_TRADE_KEY", "MOLIT_SERVICE_KEY", "MOLIT_API_KEY", "PUBLIC_DATA_API_KEY")
RENT_KEY_ENVS = ("MOLIT_APT_RENT_KEY", "MOLIT_SERVICE_KEY", "MOLIT_API_KEY", "PUBLIC_DATA_API_KEY")
PUBLIC_PRICE_KEY_ENVS = ("PUBLIC_PRICE_API_KEY", "OFFICIAL_PRICE_API_KEY", "MOLIT_PUBLIC_PRICE_KEY", "NSDI_API_KEY")
KAKAO_KEY_ENVS = ("KAKAO_REST_API_KEY", "MOVEVALUE_KAKAO_REST_API_KEY")

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
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(request, timeout=18) as response:  # noqa: S310 - official public API endpoint.
        return ET.fromstring(response.read())


def request_json(endpoint: str, params: dict[str, str], headers: dict[str, str] | None = None) -> dict[str, Any]:
    encoded = urllib.parse.urlencode(params, safe="%")
    request = urllib.request.Request(
        f"{endpoint}?{encoded}",
        headers={"User-Agent": "MoveValue/0.1", **(headers or {})},
    )
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(request, timeout=15) as response:  # noqa: S310 - official public API endpoint.
        return json.loads(response.read().decode("utf-8"))


def response_error(root: ET.Element) -> str:
    header = root.find(".//header")
    if header is None:
        return ""
    code = text_of(header, "resultCode")
    message = text_of(header, "resultMsg")
    if code and code not in {"00", "000", "NORMAL_CODE"}:
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


def pnu_from_address(address: str) -> tuple[str, str]:
    kakao_key = env_key(*KAKAO_KEY_ENVS)
    if not kakao_key:
        return "", "Kakao REST key is required to convert an address to PNU."
    if not address:
        return "", "Apartment address is empty."

    try:
        payload = request_json(
            KAKAO_ADDRESS_ENDPOINT,
            {"query": address},
            {"Authorization": f"KakaoAK {kakao_key}"},
        )
    except Exception as exc:  # noqa: BLE001 - live adapter must not break prototype.
        return "", f"Kakao address lookup failed: {exc}"

    documents = payload.get("documents") or []
    if not documents:
        return "", "Kakao address lookup returned no document."

    land = documents[0].get("address") or {}
    b_code = str(land.get("b_code") or "")
    main_no = str(land.get("main_address_no") or "")
    sub_no = str(land.get("sub_address_no") or "0")
    if len(b_code) < 10 or not main_no:
        return "", "Kakao address result did not include enough land-lot fields for PNU."

    san_flag = "2" if str(land.get("mountain_yn") or "").upper() == "Y" else "1"
    try:
        pnu = f"{b_code[:10]}{san_flag}{int(main_no):04d}{int(sub_no or 0):04d}"
    except ValueError:
        return "", "Kakao address lot number could not be converted to PNU."
    return pnu, ""


def _as_rows(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    if isinstance(value, dict):
        return [value]
    return []


def _public_price_to_10k(value: Any) -> int:
    amount = money_10k(value)
    if amount > 100000:
        return round(amount / 10000)
    return amount


def _public_price_from_row(row: dict[str, Any]) -> int:
    for name in ("pblntfPc", "aphusPc", "hsprc", "housePc", "price", "pblntfPrc"):
        amount = _public_price_to_10k(row.get(name))
        if amount:
            return amount
    for key, value in row.items():
        lowered = str(key).lower()
        if "pc" in lowered or "price" in lowered or "prc" in lowered:
            amount = _public_price_to_10k(value)
            if amount:
                return amount
    return 0


def fetch_public_price(apartment: dict[str, Any]) -> tuple[dict[str, Any] | None, str]:
    api_key = env_key(*PUBLIC_PRICE_KEY_ENVS)
    if not api_key:
        return None, "not_configured"

    pnu = str(apartment.get("pnu") or "")
    pnu_error = ""
    if not pnu:
        pnu, pnu_error = pnu_from_address(str(apartment.get("address") or ""))
    if not pnu:
        return None, pnu_error or "missing_pnu"

    current_year = datetime.now().year
    last_error = ""
    for year in (current_year, current_year - 1, current_year - 2):
        params = {
            "key": api_key,
            "pnu": pnu,
            "stdrYear": str(year),
            "format": "json",
            "numOfRows": "1000",
            "pageNo": "1",
        }
        try:
            payload = request_json(PUBLIC_PRICE_ENDPOINT, params)
        except Exception as exc:  # noqa: BLE001 - live adapter must not break prototype.
            last_error = str(exc)
            continue

        result = payload.get("apartHousingPrices") or {}
        code = str(result.get("resultCode") or "")
        message = str(result.get("resultMsg") or "")
        if code and code not in {"0", "00", "000", "NORMAL_CODE"}:
            last_error = f"{code}: {message}"
            if code == "INCORRECT_KEY":
                break
            continue

        rows = _as_rows(result.get("field"))
        prices = sorted(amount for amount in (_public_price_from_row(row) for row in rows) if amount)
        if not prices:
            last_error = f"no public price record for PNU {pnu} in {year}"
            continue

        return {
            "officialPrice10k": prices[len(prices) // 2],
            "pnu": pnu,
            "stdrYear": year,
            "recordCount": len(rows),
            "sampleRecords": rows[:6],
        }, ""

    return None, last_error or "no public price record"


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

    if public_price_key:
        public_record, public_error = fetch_public_price(apartment)
        live_status["publicPrice"].update(
            {
                "mode": "live_api"
                if public_record
                else ("invalid_key" if "INCORRECT_KEY" in str(public_error) else "no_matching_record"),
                "recordCount": int(public_record.get("recordCount") or 0) if public_record else 0,
                "error": public_error,
                "pnu": public_record.get("pnu") if public_record else "",
                "stdrYear": public_record.get("stdrYear") if public_record else "",
                "note": "공동주택가격속성조회 API 값을 상세 가격에 반영했습니다."
                if public_record
                else "공동주택가격속성조회 API에서 live 공시가격을 가져오지 못해 추정값을 유지했습니다.",
            }
        )
        if public_record:
            market["officialPrice10k"] = public_record["officialPrice10k"]
            market["publicPriceRecords"] = public_record["sampleRecords"]
            market["sourceMode"] = "public_price_live_partial"
            market["sourceLabel"] = "공동주택 공시가격 live 보정 + 공개 집계 정보"

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
