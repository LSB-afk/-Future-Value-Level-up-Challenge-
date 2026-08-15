#!/usr/bin/env python3
"""apartment_record_matches가 옆 단지 실거래를 끌어오지 않는지 확인한다.

고정 픽스처는 2026-07 국토교통부 전월세/매매 실거래가에서 그대로 가져왔다.
단지명이 서로의 접두어라 이름 매칭만으로는 갈리지 않는 실제 사례다.

    python3 api/test_price_record_matching.py
"""

from __future__ import annotations

from real_estate_price_adapters import apartment_record_matches, apt_name_matches, series_number

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


if __name__ == "__main__":
    test_each_complex_matches_only_itself()
    test_dong_alone_separates_when_road_is_missing()
    test_series_number_separates_same_dong()
    test_name_matching_alone_would_cross_match()
    test_match_method_is_recorded()
    print("price record matching test OK")
