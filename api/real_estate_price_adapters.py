"""Public real-estate price adapters for MoveValue.

The adapter is intentionally optional. It never requires API keys for the app
to boot, but it can enrich a selected apartment detail with MOLIT transaction
records when service keys are provided through environment variables.
"""

from __future__ import annotations

import json
import os
import re
import statistics
import threading
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from difflib import SequenceMatcher
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
MOLIT_REQUEST_TIMEOUT_SECONDS = max(3, int(os.getenv("MOLIT_REQUEST_TIMEOUT_SECONDS", "6") or 6))
MOLIT_FETCH_WORKERS = max(1, min(8, int(os.getenv("MOLIT_FETCH_WORKERS", "6") or 6)))

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


def recent_deal_months(count: int = 12) -> list[str]:
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
    text = str(value or "").lower()
    replacements = {
        "이편한세상": "e편한세상",
        "e-편한세상": "e편한세상",
        "e 편한세상": "e편한세상",
        "이-편한세상": "e편한세상",
        "래미안아파트": "래미안",
        "자이아파트": "자이",
        "아파트": "",
        "단지": "",
        "주상복합": "",
        "공동주택": "",
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    return re.sub(r"[^0-9a-z가-힣]", "", text)


def name_tokens(value: str) -> set[str]:
    normalized = normalize_name(value)
    return {
        token
        for token in re.findall(r"[가-힣]+|[a-z]+|\d+", normalized)
        if len(token) >= 2 or token.isdigit()
    }


def normalize_address(value: str) -> str:
    return re.sub(r"[^0-9a-z가-힣]", "", str(value or "").lower())


def extract_address_numbers(value: str) -> tuple[str, str]:
    text = str(value or "")
    matches = re.findall(r"(\d+)(?:-(\d+))?", text)
    if not matches:
        return "", ""
    main, sub = matches[-1]
    return main, sub or "0"


def same_number_pair(left: tuple[str, str], right: tuple[str, str]) -> bool:
    if not left[0] or not right[0]:
        return False
    try:
        return int(left[0]) == int(right[0]) and int(left[1] or 0) == int(right[1] or 0)
    except ValueError:
        return False


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
    with opener.open(request, timeout=MOLIT_REQUEST_TIMEOUT_SECONDS) as response:  # noqa: S310 - official public API endpoint.
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
    if target in candidate or candidate in target:
        return True

    target_tokens = name_tokens(apartment.get("name", ""))
    candidate_tokens = name_tokens(record_name)
    if target_tokens and target_tokens.issubset(candidate_tokens):
        return True
    if candidate_tokens and candidate_tokens.issubset(target_tokens):
        return True
    if len(target_tokens & candidate_tokens) >= 2:
        return True

    return SequenceMatcher(None, target, candidate).ratio() >= 0.82


def record_address_matches(apartment: dict[str, Any], record: dict[str, Any]) -> bool:
    apartment_address = str(apartment.get("address") or "")
    apartment_dong = str(apartment.get("dong") or "")
    record_dong = str(record.get("dong") or "")
    if record_dong and apartment_dong and record_dong != apartment_dong and record_dong not in apartment_address:
        return False

    road_name = str(record.get("roadName") or "")
    road_number = (str(record.get("roadMainNo") or ""), str(record.get("roadSubNo") or "0"))
    jibun = str(record.get("jibun") or "")

    # 도로명이 같아도 번호가 비었거나 다르면 같은 단지라고 볼 근거가 없다. 같은 길에 단지가 여럿 있다.
    normalized_address = normalize_address(apartment_address)
    if road_name and road_number[0] and normalize_address(road_name) in normalized_address:
        if same_number_pair(extract_address_numbers(apartment_address), road_number):
            return True

    # 지번은 단지의 지번과만 비교한다. 단지 주소는 도로명이라, 도로명 번호(신반포로15길 "1")를
    # 지번("1")과 비교하면 옆 단지(래미안원베일리 반포동 1)를 끌어온다. 2026-11-08 실측 버그.
    apartment_jibun = str(apartment.get("jibun") or "")
    if jibun and apartment_jibun:
        if same_number_pair(extract_address_numbers(apartment_jibun), extract_address_numbers(jibun)):
            return True

    return False


def record_dong_conflicts(apartment: dict[str, Any], record: dict[str, Any]) -> bool:
    """법정동이 서로 다르면 같은 단지일 수 없다."""
    apartment_dong = str(apartment.get("dong") or "")
    record_dong = str(record.get("dong") or "")
    if not apartment_dong or not record_dong or record_dong == apartment_dong:
        return False
    return record_dong not in str(apartment.get("address") or "")


def record_road_conflicts(apartment: dict[str, Any], record: dict[str, Any]) -> bool:
    """단지 주소와 레코드가 같은 도로명인데 건물번호(본번·부번)가 다르면 다른 단지다.

    이름이 같아도(동일로 10의 "OO아파트" ↔ 동일로 999의 "OO아파트") 주소가 명시적으로 어긋나면 거부한다.
    단지 주소에서 도로명 바로 뒤 번호만 읽는다("동일로1길 23"의 1은 도로명 일부라 건물번호가 아니다).
    """
    road_name = str(record.get("roadName") or "").strip()
    try:
        record_main = int(str(record.get("roadMainNo") or "0"))
        record_sub = int(str(record.get("roadSubNo") or "0"))
    except ValueError:
        return False
    if not road_name or not record_main:
        return False
    match = re.search(
        rf"(?<![0-9가-힣]){re.escape(road_name)}\s*(\d+)(?:-(\d+))?(?![\d길가])",
        str(apartment.get("address") or ""),
    )
    if not match:
        return False
    return (int(match.group(1)), int(match.group(2) or 0)) != (record_main, record_sub)


def series_number(name: str) -> int:
    """단지명 끝의 N차를 읽는다. 차수 표기가 없으면 1차로 본다."""
    match = re.search(r"(\d+)차", normalize_name(name))
    return int(match.group(1)) if match else 1


def apartment_record_matches(apartment: dict[str, Any], record: dict[str, Any]) -> bool:
    # 단지명이 서로의 접두어인 경우가 흔하다. 서울숲아이파크(송정동)는
    # 서울숲아이파크리버포레1차(성수동1가)의 부분 문자열이라 이름만으로는 갈리지 않고,
    # 전월세 레코드에는 도로명이 비어 있어 이름 매칭이 먼저 통과하면 주소 검증이
    # 아예 실행되지 않는다. 법정동과 차수는 이름 매칭에도 선행 조건으로 건다.
    record_name = record.get("name", "")
    if record_dong_conflicts(apartment, record):
        return False
    if series_number(apartment.get("name", "")) != series_number(record_name):
        return False
    if record_road_conflicts(apartment, record):
        return False
    # 단지 지번을 알고 있으면 지번이 다른 기록도 다른 단지다(재점검 Astra-08). 지금 스냅샷엔 지번이 없지만 들어오면 바로 쓴다.
    # 지번 필드가 없어도 주소가 지번 주소("성수동1가 656-234")면 그 번호를 쓴다(재점검 Astra-08).
    lot_text = str(apartment.get("jibun") or "")
    if not lot_text:
        # 지번 뒤에 "(한빛아파트)" 같은 괄호 설명이 붙어도 읽는다(최종 재점검 Astra-08).
        lot_match = re.search(r"(?:동|가|리)\s*(\d+(?:-\d+)?)\s*(?:\([^)]*\))?\s*$", str(apartment.get("address") or ""))
        lot_text = lot_match.group(1) if lot_match else ""
    apartment_jibun = extract_address_numbers(lot_text)
    record_jibun = extract_address_numbers(str(record.get("jibun") or ""))
    if apartment_jibun[0] and record_jibun[0] and not same_number_pair(apartment_jibun, record_jibun):
        return False

    if apt_name_matches(apartment, record_name):
        record["matchMethod"] = "name"
        return True
    if record_address_matches(apartment, record):
        record["matchMethod"] = "address"
        return True
    return False


def road_sub_no(item: ET.Element) -> str:
    return text_of(item, "roadNmBubun", "roadNmSubNo", "도로명부번") or "0"


def parse_trade_item(item: ET.Element) -> dict[str, Any]:
    return {
        "type": "매매",
        "name": text_of(item, "aptNm", "아파트"),
        "amount10k": money_10k(text_of(item, "dealAmount", "거래금액")),
        "exclusiveM2": float(text_of(item, "excluUseAr", "전용면적") or 0),
        "dong": text_of(item, "umdNm", "법정동"),
        "jibun": text_of(item, "jibun", "지번"),
        "roadName": text_of(item, "roadNm", "도로명"),
        "roadMainNo": text_of(item, "roadNmBonbun", "roadNmMainNo", "도로명건물본번호코드"),
        "roadSubNo": road_sub_no(item),
        "floor": text_of(item, "floor", "층"),
        "dealYear": text_of(item, "dealYear", "년"),
        "dealMonth": text_of(item, "dealMonth", "월"),
        "dealDay": text_of(item, "dealDay", "일"),
        **cancel_fields(item),
        **lot_fields(item),
        "sourceMode": "molit_trade_api",
    }


def parse_rent_item(item: ET.Element) -> dict[str, Any]:
    return {
        "type": "전월세",
        "name": text_of(item, "aptNm", "아파트"),
        "deposit10k": money_10k(text_of(item, "deposit", "보증금액")),
        "monthlyRent10k": money_10k(text_of(item, "monthlyRent", "월세금액")),
        "exclusiveM2": float(text_of(item, "excluUseAr", "전용면적") or 0),
        "dong": text_of(item, "umdNm", "법정동"),
        "jibun": text_of(item, "jibun", "지번"),
        "roadName": text_of(item, "roadNm", "도로명"),
        "roadMainNo": text_of(item, "roadNmBonbun", "roadNmMainNo", "도로명건물본번호코드"),
        "roadSubNo": road_sub_no(item),
        "floor": text_of(item, "floor", "층"),
        "dealYear": text_of(item, "dealYear", "년"),
        "dealMonth": text_of(item, "dealMonth", "월"),
        "dealDay": text_of(item, "dealDay", "일"),
        **cancel_fields(item),
        **lot_fields(item),
        "sourceMode": "molit_rent_api",
    }


def cancel_fields(item: ET.Element) -> dict[str, Any]:
    """해제(취소) 거래 표시. 국토부는 해제된 거래도 cdealType="O"·cdealDay(해제사유 발생일)를 달아 그대로 내려준다.
    해제 거래는 실제로 성사되지 않았으므로 가격·중앙값·추이 계산에서 뺀다(month_items에서 거른다)."""
    cancel_type = text_of(item, "cdealType", "해제여부").upper()
    cancel_day = text_of(item, "cdealDay", "해제사유발생일")
    return {"cancelled": cancel_type in {"O", "Y"} or bool(cancel_day), "cancelDay": cancel_day}


def lot_fields(item: ET.Element) -> dict[str, str]:
    """건축물대장 조회에 쓸 시군구·법정동 코드와 본번·부번. 매매 API에만 있고 전월세에는 비어 있을 수 있다."""
    return {
        "sggCd": text_of(item, "sggCd"),
        "umdCd": text_of(item, "umdCd"),
        "bonbun": text_of(item, "bonbun"),
        "bubun": text_of(item, "bubun"),
        "aptSeq": text_of(item, "aptSeq"),
    }


# 한 구(LAWD)의 한 달치 거래는 단지마다 다시 받을 이유가 없다. 상세 화면 한 번에 24번(12개월 × 매매·전월세)
# 호출하던 것을, 같은 구 안에서는 처음 한 번만 받는다. 실거래 신고는 한 달 단위로 쌓이므로 6시간이면 충분히 새롭다.
MONTH_CACHE_SECONDS = 6 * 3600
# 실패·불완전(페이지 일부 실패, 페이지 상한 도달) 결과는 짧게만 캐시한다. 같은 달을 몇 초 사이에 다시
# 두드리지 않게 하되, 일시 장애가 6시간 동안 "거래 없음"으로 굳지 않게 한다.
MONTH_FAILURE_CACHE_SECONDS = 5 * 60
MOLIT_PAGE_SIZE = 1000
MOLIT_MAX_PAGES = 10
# 키 → (저장 시각, TTL, 거래, 오류, 불완전 여부)
_MONTH_CACHE: dict[tuple[str, str, str], tuple[float, float, list[dict[str, Any]], str, bool]] = {}
_MONTH_INFLIGHT: dict[tuple[str, str, str], threading.Event] = {}
_MONTH_LOCK = threading.Lock()


def _fetch_month_pages(endpoint: str, service_key: str, lawd_code: str, deal_ym: str, parser) -> tuple[list[dict[str, Any]], str, bool]:
    """totalCount만큼 페이지를 넘겨 받는다. 첫 페이지가 실패하면 오류, 뒤 페이지 실패·상한 도달은 불완전으로 표시."""
    items: list[dict[str, Any]] = []
    total = 0
    for page in range(1, MOLIT_MAX_PAGES + 1):
        params = {"serviceKey": service_key, "LAWD_CD": lawd_code, "DEAL_YMD": deal_ym,
                  "pageNo": str(page), "numOfRows": str(MOLIT_PAGE_SIZE)}
        try:
            root = request_xml(endpoint, params)
            error = response_error(root)
        except Exception as exc:  # noqa: BLE001 - live adapter must not break prototype.
            error = str(exc)
        if error:
            return (items, error, True) if page > 1 else ([], error, False)
        page_items = root.findall(".//item")
        try:
            total = int(text_of(root, ".//totalCount") or 0)
        except ValueError:
            total = 0
        items.extend(parser(item) for item in page_items)
        if not page_items or len(page_items) < MOLIT_PAGE_SIZE or (total and page * MOLIT_PAGE_SIZE >= total):
            return items, "", False
    return items, "", True  # 상한까지 받고도 남았다


def month_items(endpoint: str, service_key: str, lawd_code: str, deal_ym: str, parser) -> tuple[list[dict[str, Any]], str, bool]:
    """한 구·한 달의 전체 거래(매칭 전, 해제 거래 제외). (거래, 오류, 불완전 여부)를 돌려준다.

    완전한 성공은 6시간, 실패·불완전은 5분 캐시한다. 같은 키를 동시에 요청하면 한 스레드만 API를 부르고
    나머지는 그 결과를 기다려 함께 쓴다.
    """
    key = (endpoint, lawd_code, deal_ym)
    while True:
        with _MONTH_LOCK:
            hit = _MONTH_CACHE.get(key)
            if hit and time.time() - hit[0] < hit[1]:
                return hit[2], hit[3], hit[4]
            waiter = _MONTH_INFLIGHT.get(key)
            if waiter is None:
                _MONTH_INFLIGHT[key] = threading.Event()
                break
        # 다른 스레드가 같은 달을 받는 중이다. 끝나면 캐시를 다시 본다(그 스레드가 죽었으면 이쪽이 받는다).
        waiter.wait(timeout=MOLIT_REQUEST_TIMEOUT_SECONDS * (MOLIT_MAX_PAGES + 1))

    try:
        raw, error, incomplete = _fetch_month_pages(endpoint, service_key, lawd_code, deal_ym, parser)
        items = [parsed for parsed in raw
                 if (parsed.get("amount10k") or parsed.get("deposit10k")) and not parsed.get("cancelled")]
        ttl = MONTH_CACHE_SECONDS if not error and not incomplete else MONTH_FAILURE_CACHE_SECONDS
        with _MONTH_LOCK:
            _MONTH_CACHE[key] = (time.time(), ttl, items, error, incomplete)
        return items, error, incomplete
    finally:
        with _MONTH_LOCK:
            event = _MONTH_INFLIGHT.pop(key, None)
        if event:
            event.set()


def district_items(endpoint: str, service_key: str, lawd_code: str, parser, months: int = 12) -> tuple[list[dict[str, Any]], bool]:
    """같은 구의 최근 거래 전체(캐시에서)와 불완전 여부(실패한 달·잘린 달이 있으면 True). 주변 시세 비교에 쓴다."""
    rows: list[dict[str, Any]] = []
    incomplete = False
    for deal_ym in recent_deal_months(months):
        items, error, partial = month_items(endpoint, service_key, lawd_code, deal_ym, parser)
        rows.extend(items)
        incomplete = incomplete or bool(error) or partial
    return rows, incomplete


def _record_key(record: dict[str, Any]) -> tuple[str, str, str]:
    return (record.get("dealYear", ""), record.get("dealMonth", "").zfill(2), record.get("dealDay", "").zfill(2))


def select_complex(apartment: dict[str, Any], trade: list[dict[str, Any]], rent: list[dict[str, Any]]) -> tuple[list, list, dict]:
    """매칭된 기록에 이름이 다른 단지가 섞였으면 단지명과 가장 가까운 묶음 하나만 남긴다.

    이름 포함 규칙은 "잠원신화"↔"신화"처럼 국토부 표기가 짧은 경우를 살리지만, "옥수삼성임대"↔"옥수"처럼
    다른 단지도 끌어온다. 묶음 = (정규화한 단지명, 지번 본번). 이름이 가장 비슷한 묶음, 같으면 기록이 많은 묶음.
    """
    target = normalize_name(apartment.get("name", ""))
    groups: dict[tuple[str, str], int] = {}
    for record in [*trade, *rent]:
        key = (normalize_name(record.get("name", "")), extract_address_numbers(record.get("jibun", ""))[0])
        groups[key] = groups.get(key, 0) + 1
    if len(groups) <= 1:
        return trade, rent, {"groups": len(groups)}

    def score(item: tuple[tuple[str, str], int]) -> tuple[bool, float, int]:
        # 단지명을 통째로 품은 이름("옥수삼성임대111동" ⊃ "옥수삼성임대")이 짧은 이름("옥수삼성")보다 우선한다.
        (name, _), count = item
        return bool(target) and target in name, SequenceMatcher(None, target, name).ratio(), count

    (best_name, best_lot), _ = max(groups.items(), key=score)

    def keep(record: dict[str, Any]) -> bool:
        name = normalize_name(record.get("name", ""))
        lot = extract_address_numbers(record.get("jibun", ""))[0]
        return name == best_name and (not lot or not best_lot or lot == best_lot)

    dropped = sorted({name for (name, _), _ in groups.items() if name != best_name})
    return [r for r in trade if keep(r)], [r for r in rent if keep(r)], {"groups": len(groups), "kept": best_name, "dropped": dropped}


def area_bucket(trade: list[dict[str, Any]], jeonse: list[dict[str, Any]]) -> float | None:
    """매매와 전세가 모두 있는 전용면적(1㎡ 반올림) 중 거래가 가장 많은 것. 없으면 None."""
    sale_areas = {round(float(r.get("exclusiveM2") or 0)) for r in trade if r.get("exclusiveM2")}
    counts: dict[int, int] = {}
    for record in [*trade, *jeonse]:
        area = round(float(record.get("exclusiveM2") or 0))
        if area and area in sale_areas and any(round(float(j.get("exclusiveM2") or 0)) == area for j in jeonse):
            counts[area] = counts.get(area, 0) + 1
    if not counts:
        return None
    return float(max(counts.items(), key=lambda item: (item[1], item[0]))[0])


def _ym(record: dict[str, Any]) -> int:
    try:
        return int(record.get("dealYear") or 0) * 12 + int(record.get("dealMonth") or 0)
    except ValueError:
        return 0


def price_pattern(trade: list[dict[str, Any]], jeonse: list[dict[str, Any]], bucket: float | None) -> dict[str, Any]:
    """같은 평형 실거래로 본 가격 모양 (B010 제안 P2·P3·P5).

    - 중앙값·건수: 최근 1건 대신 12개월 중앙값으로 전세가율을 계산한다(한 건의 이상치에 흔들리지 않게).
    - 매매가 급등: 최근 매매가가 이 단지의 그전 같은 평형 매매 중앙값보다 얼마나 높은지. 기준선은 두지 않는다(참고).
    - 전세 추이: 최근 3개월 전세 중앙값 vs 그 전 중앙값. 역전세(전세가 하락) 방향을 본다(참고).
    - 같은 달 겹침: 같은 달에 같은 평형의 전세 보증금이 매매가 이상인 거래가 있으면, 정의상 그 거래 시점에
      보증금이 집값 이상이었다는 뜻이다(깡통). 동·호가 공개되지 않아 같은 호실인지는 알 수 없다.
    """
    if bucket is None:
        return {}
    sales = sorted((r for r in trade if round(float(r.get("exclusiveM2") or 0)) == bucket), key=_record_key)
    leases = sorted((r for r in jeonse if round(float(r.get("exclusiveM2") or 0)) == bucket), key=_record_key)
    out: dict[str, Any] = {"saleCount": len(sales), "jeonseCount": len(leases)}
    if sales:
        out["saleMedian10k"] = round(statistics.median(float(r["amount10k"]) for r in sales))
    if leases:
        out["jeonseMedian10k"] = round(statistics.median(float(r["deposit10k"]) for r in leases))
    if len(sales) >= 4:
        earlier = statistics.median(float(r["amount10k"]) for r in sales[:-1])
        out["saleSurgePct"] = round((float(sales[-1]["amount10k"]) - earlier) / earlier * 100, 1)
        out["saleSurgeBasis"] = f"최근 매매 1건 vs 그전 같은 평형 매매 {len(sales) - 1}건 중앙값"
    if leases:
        newest = _ym(leases[-1])
        recent = [float(r["deposit10k"]) for r in leases if newest - _ym(r) < 3]
        before = [float(r["deposit10k"]) for r in leases if newest - _ym(r) >= 3]
        if len(recent) >= 2 and len(before) >= 2:
            base = statistics.median(before)
            out["jeonseTrendPct"] = round((statistics.median(recent) - base) / base * 100, 1)
            out["jeonseTrendBasis"] = f"최근 3개월 전세 {len(recent)}건 중앙값 vs 그전 {len(before)}건 중앙값"
    # 그 달의 가장 비싼 매매와 비교한다. 가장 싼 매매(저층 등)와 비교하면 고층 전세 한 건으로도 경고가 떠서 오탐이 많다(B011 리뷰).
    sale_by_month: dict[int, float] = {}
    for r in sales:
        sale_by_month[_ym(r)] = max(sale_by_month.get(_ym(r), 0.0), float(r["amount10k"]))
    overlap = sorted({
        f"{r.get('dealYear')}.{str(r.get('dealMonth')).zfill(2)}"
        for r in leases
        if _ym(r) in sale_by_month and float(r["deposit10k"]) >= sale_by_month[_ym(r)]
    })
    out["depositOverSaleMonths"] = overlap
    return out


def fetch_molit_records(
    endpoint: str,
    service_key: str,
    lawd_code: str,
    parser,
    apartment: dict[str, Any],
    months: int = 12,
) -> tuple[list[dict[str, Any]], str, bool]:
    """(매칭된 기록, 마지막 오류, 불완전 여부). 실패한 달·잘린 달이 하나라도 있으면 불완전이다."""
    records: list[dict[str, Any]] = []
    last_error = ""
    incomplete = False
    deal_months = recent_deal_months(months)

    def fetch_month(deal_ym: str) -> tuple[list[dict[str, Any]], str, bool]:
        items, error, partial = month_items(endpoint, service_key, lawd_code, deal_ym, parser)
        month_records = []
        for parsed in items:
            parsed = dict(parsed)  # 캐시 원본에 matchMethod가 섞이지 않게 복사
            if apartment_record_matches(apartment, parsed):
                month_records.append(parsed)
        return month_records, error, partial

    with ThreadPoolExecutor(max_workers=min(MOLIT_FETCH_WORKERS, len(deal_months))) as executor:
        futures = [executor.submit(fetch_month, deal_ym) for deal_ym in deal_months]
        for future in as_completed(futures):
            month_records, error, partial = future.result()
            if error:
                last_error = error
            incomplete = incomplete or bool(error) or partial
            records.extend(month_records)

    records.sort(
        key=lambda item: (item.get("dealYear", ""), item.get("dealMonth", ""), item.get("dealDay", "")),
        reverse=True,
    )
    return records, last_error, incomplete


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
    market["officialPriceLive"] = False
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

    trade_records, trade_error, trade_incomplete = (
        fetch_molit_records(MOLIT_TRADE_ENDPOINT, trade_key, lawd_code, parse_trade_item, apartment)
        if trade_key and lawd_code else ([], "", False)
    )
    rent_records, rent_error, rent_incomplete = (
        fetch_molit_records(MOLIT_RENT_ENDPOINT, rent_key, lawd_code, parse_rent_item, apartment)
        if rent_key and lawd_code else ([], "", False)
    )
    trade_records, rent_records, complex_info = select_complex(apartment, trade_records, rent_records)
    market["complexMatch"] = complex_info
    jeonse_records = [item for item in rent_records if not item.get("monthlyRent10k")]
    monthly_records = [item for item in rent_records if item.get("monthlyRent10k")]

    # 전세가율은 같은 평형의 매매와 전세로만 계산한다. 84㎡ 매매와 59㎡ 전세를 나누면 의미 없는 비율이 나온다.
    bucket = area_bucket(trade_records, jeonse_records)

    def latest(rows: list[dict[str, Any]], area: float | None = None) -> dict[str, Any] | None:
        pool = [r for r in rows if area is None or round(float(r.get("exclusiveM2") or 0)) == area]
        return max(pool, key=_record_key) if pool else None

    market["areaM2"] = bucket
    market["areaMatched"] = bucket is not None
    market.update(price_pattern(trade_records, jeonse_records, bucket))
    # sourceMode는 전월세만 붙어도 molit_*가 된다. 매매가·전세가가 각각 실거래인지는 따로 표시해야
    # 추정 매매가를 '실거래'로 믿는 일이 없다 (2026-11-08 옥수삼성임대: 전월세만 매칭, 매매가는 추정).
    market["saleLive"] = False
    market["jeonseLive"] = False

    if trade_key and lawd_code:
        live_status["molitTrade"].update(
            {
                "mode": "live_api" if trade_records else "no_matching_record",
                "recordCount": len(trade_records),
                "error": trade_error,
                # 실패한 달·페이지 상한에 걸린 달이 있어 12개월 전체를 다 받지 못했다(건수·중앙값이 덜 모였을 수 있음).
                "incomplete": trade_incomplete,
                "note": "단지명/주소 매칭 실거래가를 상세 가격에 반영했습니다." if trade_records else "최근 12개월 내 단지명/주소 매칭 매매 실거래가가 없습니다.",
            }
        )
        recent = latest(trade_records, bucket) or latest(trade_records)
        if recent:
            market["saleLive"] = True
            market["recentSale10k"] = recent["amount10k"]
            market["molitLatestTradeRecord"] = recent
            market["molitTradeRecordsForTrend"] = trade_records
            market["molitTradeRecords"] = sorted(trade_records, key=_record_key, reverse=True)[:6]
            market["sourceMode"] = "molit_live_trade_partial"
            market["sourceLabel"] = "국토교통부 매매 실거래가 live 보정 + 공개 단지정보"

    if rent_key and lawd_code:
        live_status["molitRent"].update(
            {
                "mode": "live_api" if rent_records else "no_matching_record",
                "recordCount": len(rent_records),
                "error": rent_error,
                "incomplete": rent_incomplete,
                "note": "단지명/주소 매칭 전월세 실거래가를 상세 가격에 반영했습니다." if rent_records else "최근 12개월 내 단지명/주소 매칭 전월세 실거래가가 없습니다.",
            }
        )
        recent = latest(jeonse_records, bucket) or latest(jeonse_records)
        if recent:
            market["jeonseLive"] = True
            market["recentJeonse10k"] = recent["deposit10k"]
            market["molitLatestJeonseRecord"] = recent
            # 같은 구·비슷한 평형(±10%)의 다른 단지 전세 중앙값. 추정 생활권 평균 대신 실거래로 비교한다.
            ref_area = float(recent.get("exclusiveM2") or 0)
            own = normalize_name(recent.get("name", ""))
            district_rows, district_incomplete = district_items(MOLIT_RENT_ENDPOINT, rent_key, lawd_code, parse_rent_item)
            peers = [
                float(r["deposit10k"])
                for r in district_rows
                if not r.get("monthlyRent10k") and ref_area
                and abs(float(r.get("exclusiveM2") or 0) - ref_area) <= ref_area * 0.1
                and normalize_name(r.get("name", "")) != own
            ]
            if len(peers) >= 5:
                market["districtJeonseMedian10k"] = round(statistics.median(peers))
                market["districtJeonseCount"] = len(peers)
                market["districtJeonseBasis"] = f"같은 구 전용 {ref_area:.0f}㎡ ±10% 전세 실거래 {len(peers)}건 중앙값(최근 12개월)"
                market["districtJeonseIncomplete"] = district_incomplete
        recent = latest(monthly_records)
        if recent:
            market["monthlyDeposit10k"] = recent["deposit10k"]
            market["monthlyRent10k"] = recent["monthlyRent10k"]
            market["molitLatestMonthlyRecord"] = recent
        if rent_records:
            market["molitRentRecordsForTrend"] = rent_records
            market["molitRentRecords"] = sorted(rent_records, key=_record_key, reverse=True)[:6]
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
            market["officialPriceLive"] = True
            # 실거래가 이미 붙었으면 sourceMode(실거래 여부 판단에 쓰임)를 덮어쓰지 않는다.
            if not str(market.get("sourceMode") or "").startswith("molit"):
                market["sourceMode"] = "public_price_live_partial"
                market["sourceLabel"] = "공동주택 공시가격 live 보정 + 공개 집계 정보"

    if market.get("saleLive") and market.get("jeonseLive") and market.get("saleMedian10k") and market.get("jeonseMedian10k"):
        # 같은 평형 12개월 중앙값끼리 나눈다. 최근 1건씩 나누면 부풀린 매매 한 건이 비율을 낮춰 안전해 보이게 한다(B010).
        market["jeonseRatio"] = round(float(market["jeonseMedian10k"]) / float(market["saleMedian10k"]) * 100, 1)
        market["jeonseRatioBasis"] = f"전용 {market['areaM2']:.0f}㎡ 매매 {market['saleCount']}건·전세 {market['jeonseCount']}건 중앙값"
    elif market.get("recentSale10k"):
        market["jeonseRatio"] = round((float(market.get("recentJeonse10k") or 0) / float(market["recentSale10k"])) * 100, 1)
    if market.get("recentSale10k"):
        market["saleGapPercent"] = round(
            ((float(market["recentSale10k"]) - float(market.get("surroundingAverageSale10k") or market["recentSale10k"])) / float(market.get("surroundingAverageSale10k") or market["recentSale10k"])) * 100,
            1,
        )
    if market.get("officialPrice10k"):
        market["depositOfficialRatio"] = round((float(market.get("recentJeonse10k") or 0) / float(market["officialPrice10k"])) * 100, 1)

    market["liveStatus"] = live_status
    return market
