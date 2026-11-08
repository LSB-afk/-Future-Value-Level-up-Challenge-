#!/usr/bin/env python3
"""build_risk의 위험 등급과 신호 상태를 고정한다 (B011, 2026-11-08 리뷰 반영).

    python3 api/test_risk_signals.py
"""

from __future__ import annotations

from property_model import build_risk

APT = {"category": "아파트", "approvalDate": "2010-01-01"}
VILLA = {"category": "연립주택", "approvalDate": "2010-01-01"}


def live_market(**extra) -> dict:
    base = {
        "recentSale10k": 50000, "recentJeonse10k": 30000, "jeonseRatio": 60.0, "saleLive": True, "jeonseLive": True,
        "areaMatched": True, "areaM2": 60.0, "saleMedian10k": 50000, "jeonseMedian10k": 30000, "saleCount": 5,
        "jeonseCount": 8, "jeonseRatioBasis": "전용 60㎡ 매매 5건·전세 8건 중앙값", "depositOverSaleMonths": [],
        "officialPriceLive": False, "officialPrice10k": 30000, "depositOfficialRatio": 100.0,
    }
    return {**base, **extra}


def signal(risk: dict, label: str) -> dict:
    return next(s for s in risk["signals"] if s["label"] == label)


def test_high_signal_reaches_top_level() -> None:
    # 리뷰 H1: 점수 상한이 70 미만이 되어 깡통(80%↑)도 '주의'에 머물렀다
    risk = build_risk(APT, live_market(jeonseRatio=85.0))
    assert signal(risk, "매매가 대비 전세가율")["status"] == "high"
    assert risk["levelKey"] == "high", risk["level"]


def test_clean_live_apartment_can_be_low() -> None:
    # 리뷰 M3: 등기부(늘 미확인)와 아파트 공시가(참고)는 '확인 필요' 판단에서 빼서 '낮음'도 가능해야 한다
    risk = build_risk(APT, live_market())
    assert risk["levelKey"] == "low", (risk["level"], [(s["label"], s["status"]) for s in risk["signals"]])


def test_estimated_prices_are_not_low() -> None:
    risk = build_risk(APT, {**live_market(), "saleLive": False, "jeonseLive": False, "areaMatched": None})
    assert risk["levelKey"] == "unknown", risk["level"]


def test_official_126_rule_only_for_non_apartments() -> None:
    # 아파트는 HUG가 시세를 먼저 쓰므로 공시가 126%는 참고(info), 연립·다세대에는 주의 기준
    over = live_market(officialPriceLive=True, depositOfficialRatio=140.0)
    assert signal(build_risk(APT, over), "공시가격 대비 전세 시세")["status"] == "info"
    assert signal(build_risk(VILLA, over), "공시가격 대비 전세 시세")["status"] == "warning"


def test_reference_signals_are_not_scored() -> None:
    plain = build_risk(APT, live_market())
    noisy = build_risk(APT, live_market(saleSurgePct=60.0, jeonseTrendPct=-30.0, districtJeonseMedian10k=10000,
                                        districtJeonseBasis="같은 구"))
    assert plain["score"] == noisy["score"], (plain["score"], noisy["score"])
    assert all(s["status"] == "info" for s in noisy["signals"] if "(참고)" in s["label"])


def test_same_month_deposit_over_sale_warns() -> None:
    risk = build_risk(APT, live_market(depositOverSaleMonths=["2026.03"]))
    assert signal(risk, "같은 달 보증금 ≥ 매매가")["status"] == "warning" and risk["levelKey"] == "warning"


if __name__ == "__main__":
    test_high_signal_reaches_top_level()
    test_clean_live_apartment_can_be_low()
    test_estimated_prices_are_not_low()
    test_official_126_rule_only_for_non_apartments()
    test_reference_signals_are_not_scored()
    test_same_month_deposit_over_sale_warns()
    print("risk signals test OK")
