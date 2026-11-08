#!/usr/bin/env python3
"""apartment_record_matches가 옆 단지 실거래를 끌어오지 않는지 확인한다.

고정 픽스처는 2026-07 국토교통부 전월세/매매 실거래가에서 그대로 가져왔다.
단지명이 서로의 접두어라 이름 매칭만으로는 갈리지 않는 실제 사례다.

    python3 api/test_price_record_matching.py
"""

from __future__ import annotations

import threading
import time
import xml.etree.ElementTree as ET

import real_estate_price_adapters as rpa
from real_estate_price_adapters import (
    apartment_record_matches,
    apt_name_matches,
    area_bucket,
    normalize_name,
    parse_trade_item,
    price_pattern,
    select_complex,
    series_number,
)

# 서울숲아이파크는 서울숲아이파크리버포레1차의 부분 문자열이고, 전월세 레코드에는
# 도로명이 비어 있어 주소 검증만으로도 갈리지 않는다. 법정동이 유일한 구분자다.
IPARK = {"name": "서울숲아이파크", "address": "서울특별시 성동구 동일로 237", "dong": "송정동"}
RIVER1 = {"name": "서울숲아이파크리버포레", "address": "서울특별시 성동구 왕십리로 137", "dong": "성수동1가"}
RIVER2 = {"name": "서울숲 아이파크 리버포레2차", "address": "서울특별시 성동구 왕십리로 135", "dong": "성수동1가"}

RECORDS = {
    "ipark": {"name": "서울숲아이파크", "dong": "송정동", "jibun": "104", "roadName": "동일로", "roadMainNo": "00237", "roadSubNo": "0"},
    "river1": {"name": "서울숲아이파크리버포레1차", "dong": "성수동1가", "jibun": "721", "roadName": "", "roadMainNo": "", "roadSubNo": "0"},
    "river2": {"name": "서울숲아이파크리버포레2차", "dong": "성수동1가", "jibun": "723", "roadName": "", "roadMainNo": "", "roadSubNo": "0"},
}

EXPECTED = {
    "서울숲아이파크": {"ipark"},
    "서울숲아이파크리버포레": {"river1"},
    "서울숲 아이파크 리버포레2차": {"river2"},
}


def matched(apartment: dict) -> set[str]:
    return {key for key, record in RECORDS.items() if apartment_record_matches(apartment, dict(record))}


def test_each_complex_matches_only_itself() -> None:
    for apartment in (IPARK, RIVER1, RIVER2):
        hits = matched(apartment)
        expected = EXPECTED[apartment["name"]]
        assert hits == expected, f"{apartment['name']}: {sorted(hits)} != {sorted(expected)}"


def test_dong_alone_separates_when_road_is_missing() -> None:
    # 전월세 레코드는 도로명이 비어 있다. 법정동이 다르면 이름이 겹쳐도 거부해야 한다.
    assert not apartment_record_matches(IPARK, dict(RECORDS["river1"]))
    assert not apartment_record_matches(RIVER1, dict(RECORDS["ipark"]))


def test_series_number_separates_same_dong() -> None:
    # 1차와 2차는 법정동이 같아 차수로만 갈린다. 차수 표기가 없으면 1차로 본다.
    assert series_number("서울숲아이파크리버포레") == 1
    assert series_number("서울숲 아이파크 리버포레2차") == 2
    assert not apartment_record_matches(RIVER1, dict(RECORDS["river2"]))
    assert not apartment_record_matches(RIVER2, dict(RECORDS["river1"]))


def test_name_matching_alone_would_cross_match() -> None:
    """가드가 왜 필요한지 고정한다. 이름만 보면 세 단지가 서로를 받아들인다."""
    assert apt_name_matches(IPARK, RECORDS["river1"]["name"])
    assert apt_name_matches(RIVER1, RECORDS["ipark"]["name"])
    assert apt_name_matches(RIVER1, RECORDS["river2"]["name"])


def test_match_method_is_recorded() -> None:
    record = dict(RECORDS["ipark"])
    assert apartment_record_matches(IPARK, record)
    assert record["matchMethod"] in {"name", "address"}


def test_road_number_is_not_compared_with_jibun() -> None:
    """2026-11-08 실측: 래미안 원펜타스(신반포로15길 1)가 래미안원베일리(지번 1, 반포대로 333)를 끌어왔다."""
    onepentas = {"name": "래미안 원펜타스", "address": "서울특별시 서초구 신반포로15길 1", "dong": "반포동"}
    onebailey_trade = {"name": "래미안원베일리", "dong": "반포동", "jibun": "1", "roadName": "반포대로", "roadMainNo": "00333", "roadSubNo": "0"}
    onebailey_rent = {"name": "래미안원베일리", "dong": "반포동", "jibun": "1", "roadName": "", "roadMainNo": "", "roadSubNo": "0"}
    assert not apartment_record_matches(onepentas, dict(onebailey_trade))
    assert not apartment_record_matches(onepentas, dict(onebailey_rent))
    # 같은 도로명이라도 번호가 비어 있으면 같은 단지라는 근거가 아니다
    same_road_no_number = {"name": "다른단지", "dong": "반포동", "jibun": "", "roadName": "신반포로15길", "roadMainNo": "", "roadSubNo": "0"}
    assert not apartment_record_matches(onepentas, dict(same_road_no_number))


def test_select_complex_keeps_closest_name() -> None:
    """이름 포함 규칙으로 들어온 다른 단지 묶음은 버린다 (2026-11-08 옥수삼성임대 ← 옥수)."""
    apartment = {"name": "옥수삼성임대"}
    rows = [
        {"name": "옥수삼성", "jibun": "250"}, {"name": "옥수삼성", "jibun": "250"},
        {"name": "옥수", "jibun": "306"}, {"name": "옥수삼성임대111동", "jibun": "250"},
    ]
    trade, rent, info = select_complex(apartment, rows[:2], rows[2:])
    assert info["kept"] == normalize_name("옥수삼성임대111동"), info
    assert not trade and [r["name"] for r in rent] == ["옥수삼성임대111동"]
    single, _, info = select_complex({"name": "잠원신화"}, [{"name": "신화", "jibun": "54-7"}], [])
    assert len(single) == 1 and info == {"groups": 1}


def test_area_bucket_pairs_same_size() -> None:
    trade = [{"exclusiveM2": 84.9}, {"exclusiveM2": 59.8}]
    jeonse = [{"exclusiveM2": 59.7}, {"exclusiveM2": 59.9}, {"exclusiveM2": 114.0}]
    assert area_bucket(trade, jeonse) == 60.0
    assert area_bucket([{"exclusiveM2": 84.9}], [{"exclusiveM2": 59.7}]) is None


def test_price_pattern_median_surge_trend_overlap() -> None:
    def sale(m, amount):
        return {"exclusiveM2": 59.9, "dealYear": "2026", "dealMonth": str(m), "dealDay": "1", "amount10k": amount}

    def lease(m, deposit):
        return {"exclusiveM2": 59.8, "dealYear": "2026", "dealMonth": str(m), "dealDay": "2", "deposit10k": deposit}

    trade = [sale(1, 50000), sale(2, 51000), sale(3, 49000), sale(9, 70000), {**sale(9, 99000), "exclusiveM2": 84.9}]
    jeonse = [lease(1, 40000), lease(2, 41000), lease(8, 36000), lease(9, 35000), lease(3, 49500)]
    p = price_pattern(trade, jeonse, 60.0)
    assert p["saleCount"] == 4 and p["saleMedian10k"] == 50500, p  # 84㎡ 거래는 빠진다
    assert p["saleSurgePct"] == 40.0, p  # 7억 vs 그전 중앙값 5억
    assert p["jeonseTrendPct"] < 0, p  # 최근 3개월 전세가 그전보다 낮다(역전세 방향)
    assert p["depositOverSaleMonths"] == ["2026.03"], p  # 3월 보증금 4.95억 ≥ 3월 매매 4.9억
    assert price_pattern(trade, jeonse, None) == {}


def test_same_name_with_conflicting_road_number_is_rejected() -> None:
    """같은 이름이라도 같은 도로명에 건물번호가 다르면(동일로 10 ↔ 동일로 999) 다른 단지다."""
    apartment = {"name": "한빛아파트", "address": "서울특별시 성동구 동일로 10", "dong": "송정동"}
    record = {"name": "한빛", "dong": "송정동", "jibun": "5", "roadName": "동일로", "roadMainNo": "00999", "roadSubNo": "0"}
    assert apt_name_matches(apartment, record["name"])
    assert not apartment_record_matches(apartment, dict(record))
    assert apartment_record_matches(apartment, {**record, "roadMainNo": "00010"})
    assert not apartment_record_matches(apartment, {**record, "roadMainNo": "00010", "roadSubNo": "3"})
    # "동일로1길 23"의 1은 도로명 일부다. 다른 도로(동일로)의 번호와 비교하지 않는다.
    side_street = {**apartment, "address": "서울특별시 성동구 동일로1길 23"}
    assert apartment_record_matches(side_street, dict(record))


def _xml(items: list[str], total: int) -> ET.Element:
    body = "".join(f"<item>{item}</item>" for item in items)
    return ET.fromstring(
        f"<response><header><resultCode>000</resultCode></header>"
        f"<body><items>{body}</items><totalCount>{total}</totalCount></body></response>"
    )


TRADE_XML = "<aptNm>한빛</aptNm><dealAmount>{amount}</dealAmount><excluUseAr>59.9</excluUseAr><umdNm>송정동</umdNm>" \
            "<dealYear>2026</dealYear><dealMonth>7</dealMonth><dealDay>1</dealDay>{extra}"


def _with_fake_api(handler):
    """request_xml을 가짜로 바꾸고 월 캐시를 비운다. 외부 API는 부르지 않는다."""
    original = rpa.request_xml
    rpa.request_xml = handler
    rpa._MONTH_CACHE.clear()
    return original


def test_cancelled_trade_is_parsed_and_excluded() -> None:
    cancelled = ET.fromstring(f"<item>{TRADE_XML.format(amount='99,000', extra='<cdealType>O</cdealType><cdealDay>26.07.20</cdealDay>')}</item>")
    parsed = parse_trade_item(cancelled)
    assert parsed["cancelled"] is True and parsed["cancelDay"] == "26.07.20", parsed
    normal = parse_trade_item(ET.fromstring(f"<item>{TRADE_XML.format(amount='50,000', extra='<cdealType> </cdealType>')}</item>"))
    assert normal["cancelled"] is False and normal["cancelDay"] == "", normal

    root = _xml([TRADE_XML.format(amount="50,000", extra=""),
                 TRADE_XML.format(amount="99,000", extra="<cdealType>O</cdealType><cdealDay>26.07.20</cdealDay>")], 2)
    original = _with_fake_api(lambda endpoint, params: root)
    try:
        items, error, incomplete = rpa.month_items("trade", "k", "11200", "202607", parse_trade_item)
    finally:
        rpa.request_xml = original
    assert not error and not incomplete
    assert [r["amount10k"] for r in items] == [50000], items  # 해제된 9.9억 거래는 중앙값·추이에 들어가지 않는다


def test_month_items_pages_through_total_count() -> None:
    calls: list[str] = []
    old_size = rpa.MOLIT_PAGE_SIZE
    rpa.MOLIT_PAGE_SIZE = 2

    def fake(endpoint, params):
        calls.append(params["pageNo"])
        page = int(params["pageNo"])
        rows = [TRADE_XML.format(amount=str(page * 1000 + i), extra="") for i in range(2 if page < 3 else 1)]
        return _xml(rows, 5)

    original = _with_fake_api(fake)
    try:
        items, error, incomplete = rpa.month_items("trade", "k", "11200", "202607", parse_trade_item)
        assert calls == ["1", "2", "3"] and len(items) == 5 and not error and not incomplete, (calls, len(items))

        # 페이지 상한에 걸리면 불완전으로 표시하고 짧게만 캐시한다.
        old_max = rpa.MOLIT_MAX_PAGES
        rpa.MOLIT_MAX_PAGES = 2
        rpa._MONTH_CACHE.clear()
        items, error, incomplete = rpa.month_items("trade", "k", "11200", "202607", parse_trade_item)
        rpa.MOLIT_MAX_PAGES = old_max
        assert len(items) == 4 and incomplete, (len(items), incomplete)
        assert rpa._MONTH_CACHE[("trade", "11200", "202607")][1] == rpa.MONTH_FAILURE_CACHE_SECONDS
    finally:
        rpa.request_xml = original
        rpa.MOLIT_PAGE_SIZE = old_size


def test_failed_month_is_negative_cached() -> None:
    calls: list[int] = []

    def failing(endpoint, params):
        calls.append(1)
        raise OSError("timeout")

    deal_ym = rpa.recent_deal_months(1)[0]
    original = _with_fake_api(failing)
    try:
        for _ in range(3):
            items, error, _ = rpa.month_items("rent", "k", "11200", deal_ym, rpa.parse_rent_item)
            assert items == [] and "timeout" in error
        # 주변 시세 계산(district_items)도 방금 실패한 달을 다시 부르지 않고, 불완전으로 알린다.
        rows, incomplete = rpa.district_items("rent", "k", "11200", rpa.parse_rent_item, months=1)
    finally:
        rpa.request_xml = original
    assert len(calls) == 1, calls  # 실패도 5분 캐시돼 같은 달을 다시 두드리지 않는다
    assert rows == [] and incomplete
    assert rpa._MONTH_CACHE[("rent", "11200", deal_ym)][1] == rpa.MONTH_FAILURE_CACHE_SECONDS


def test_concurrent_same_month_shares_one_request() -> None:
    calls: list[int] = []
    gate = threading.Event()

    def slow(endpoint, params):
        calls.append(1)
        gate.wait(2)
        return _xml([TRADE_XML.format(amount="50,000", extra="")], 1)

    original = _with_fake_api(slow)
    results: list[tuple] = []
    try:
        threads = [threading.Thread(target=lambda: results.append(
            rpa.month_items("trade", "k", "11200", "202607", parse_trade_item))) for _ in range(5)]
        for t in threads:
            t.start()
        time.sleep(0.2)
        gate.set()
        for t in threads:
            t.join(5)
    finally:
        rpa.request_xml = original
    assert len(calls) == 1, calls
    assert len(results) == 5 and all(len(r[0]) == 1 for r in results), results


def test_jibun_conflict_rejects_same_name() -> None:
    """재점검 Astra-08: 같은 이름·같은 동이라도 단지 지번과 기록 지번이 다르면 다른 단지다."""
    apartment = {"name": "한빛", "address": "서울특별시 성동구 왕십리로 1", "dong": "성수동1가", "jibun": "10"}
    assert not apartment_record_matches(apartment, {"name": "한빛", "dong": "성수동1가", "jibun": "999", "roadName": "", "roadMainNo": "", "roadSubNo": "0"})
    assert apartment_record_matches(apartment, {"name": "한빛", "dong": "성수동1가", "jibun": "10", "roadName": "", "roadMainNo": "", "roadSubNo": "0"})
    lot_address = {"name": "한빛", "address": "서울특별시 성동구 성수동1가 10 (한빛아파트)", "dong": "성수동1가"}
    assert not apartment_record_matches(lot_address, {"name": "한빛", "dong": "성수동1가", "jibun": "999", "roadName": "", "roadMainNo": "", "roadSubNo": "0"})


if __name__ == "__main__":
    test_jibun_conflict_rejects_same_name()
    test_same_name_with_conflicting_road_number_is_rejected()
    test_cancelled_trade_is_parsed_and_excluded()
    test_month_items_pages_through_total_count()
    test_failed_month_is_negative_cached()
    test_concurrent_same_month_shares_one_request()
    test_price_pattern_median_surge_trend_overlap()
    test_road_number_is_not_compared_with_jibun()
    test_select_complex_keeps_closest_name()
    test_area_bucket_pairs_same_size()
    test_each_complex_matches_only_itself()
    test_dong_alone_separates_when_road_is_missing()
    test_series_number_separates_same_dong()
    test_name_matching_alone_would_cross_match()
    test_match_method_is_recorded()
    print("price record matching test OK")
