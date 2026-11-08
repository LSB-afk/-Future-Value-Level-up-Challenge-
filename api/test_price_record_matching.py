#!/usr/bin/env python3
"""apartment_record_matches가 옆 단지 실거래를 끌어오지 않는지 확인한다.

고정 픽스처는 2026-07 국토교통부 전월세/매매 실거래가에서 그대로 가져왔다.
단지명이 서로의 접두어라 이름 매칭만으로는 갈리지 않는 실제 사례다.

    python3 api/test_price_record_matching.py
"""

from __future__ import annotations

from real_estate_price_adapters import (
    apartment_record_matches,
    apt_name_matches,
    area_bucket,
    normalize_name,
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


if __name__ == "__main__":
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
