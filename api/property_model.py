"""Real-estate detail model for the MoveValue property dashboard.

The model intentionally separates exact public-source fields from prototype
market estimates. Exact apartment/building fields come from Seoul OpenAptInfo;
rent/jeonse baselines come from MoveValue's 2025 Seoul rental transaction
aggregation; sale/public-price fields are deterministic estimates until the
MOLIT/PublicData keys are connected.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AREAS_PATH = ROOT / "data" / "areas.actual.json"
CURRENT_YEAR = 2026

PUBLIC_SOURCES = [
    {
        "name": "서울시 공동주택 아파트 정보",
        "url": "https://data.seoul.go.kr/dataList/OA-15818/S/1/datasetView.do",
        "fields": "단지명, 주소, 좌표, 세대수, 동수, 사용승인일, 난방/관리 방식",
        "status": "실데이터",
    },
    {
        "name": "서울시 부동산 전월세가 정보 2025 집계",
        "url": "https://data.seoul.go.kr/dataList/OA-21276/S/1/datasetView.do",
        "fields": "생활권별 월세·보증금·전세 중앙값과 예시 거래",
        "status": "실데이터 집계",
    },
    {
        "name": "국토교통부 아파트 매매 실거래가 API",
        "url": "https://www.data.go.kr/data/15126469/openapi.do",
        "fields": "단지별 매매 실거래가",
        "status": "API 키 연계 예정",
    },
    {
        "name": "국토교통부 아파트 전월세 실거래가 API",
        "url": "https://www.data.go.kr/data/15126474/openapi.do",
        "fields": "단지별 전월세 실거래가",
        "status": "API 키 연계 예정",
    },
    {
        "name": "VWorld 지오코더/지도 API",
        "url": "https://www.vworld.kr/dev/v4dv_geocoderguide2_s001.do",
        "fields": "주소-좌표 변환, 건물·토지 공간 연계",
        "status": "API 키 연계 예정",
    },
]

_AREA_CACHE: dict | None = None


def number(value, default=0.0) -> float:
    try:
        if value in {"", None}:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def integer(value, default=0) -> int:
    return int(round(number(value, default)))


def clamp(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
    return max(minimum, min(maximum, value))


def stable_ratio(key: str, minimum: float, maximum: float) -> float:
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
    value = int(digest[:10], 16) / float(0xFFFFFFFFFF)
    return minimum + (maximum - minimum) * value


def format_money_10k(value) -> str:
    amount = int(round(number(value)))
    if amount >= 10000:
        eok = amount // 10000
        rest = amount % 10000
        return f"{eok}억 {rest:,}만원" if rest else f"{eok}억원"
    return f"{amount:,}만원"


def load_areas() -> list[dict]:
    global _AREA_CACHE
    if _AREA_CACHE is None:
        with AREAS_PATH.open(encoding="utf-8") as file:
            _AREA_CACHE = json.load(file)
    return list(_AREA_CACHE.get("areas", []))


def haversine_km(a_lat: float, a_lng: float, b_lat: float, b_lng: float) -> float:
    radius = 6371.0088
    phi1 = math.radians(a_lat)
    phi2 = math.radians(b_lat)
    d_phi = math.radians(b_lat - a_lat)
    d_lambda = math.radians(b_lng - a_lng)
    h = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return radius * 2 * math.atan2(math.sqrt(h), math.sqrt(1 - h))


def normalized_district(value: str) -> str:
    text = str(value or "").strip()
    if text.startswith("서울 "):
        text = text.replace("서울 ", "", 1)
    return text


def nearest_living_area(apartment: dict) -> dict:
    areas = load_areas()
    if not areas:
        return {}

    apt_district = normalized_district(apartment.get("district", ""))
    candidates = [
        area for area in areas if apt_district and apt_district in normalized_district(area.get("district", ""))
    ] or areas
    apt_lat = number(apartment.get("lat"))
    apt_lng = number(apartment.get("lng"))
    return min(
        candidates,
        key=lambda area: haversine_km(apt_lat, apt_lng, number(area.get("lat")), number(area.get("lng"))),
    )


def building_age(apartment: dict) -> int:
    year = integer(apartment.get("approvalYear"))
    return max(0, CURRENT_YEAR - year) if year else 0


def area_options(apartment: dict) -> list[dict]:
    households = max(1, integer(apartment.get("households"), 1))
    gross_area = number(apartment.get("grossFloorAreaM2"))
    if gross_area:
        base = clamp((gross_area / households) * 0.72, 36, 135)
    else:
        base = stable_ratio(apartment.get("id", "property"), 49, 84)
    options = sorted({round(clamp(base * factor, 18, 165), 1) for factor in (0.82, 1.0, 1.22)})
    return [{"exclusiveM2": value, "pyeong": round(value / 3.3058, 1)} for value in options]


def estimate_market(apartment: dict, area: dict) -> dict:
    seed = apartment.get("id") or apartment.get("name") or apartment.get("address") or "property"
    age = building_age(apartment)
    households = max(1, integer(apartment.get("households"), 1))
    area_jeonse = max(9000, number(area.get("jeonse10k"), 26000))
    area_monthly = max(25, number(area.get("rentMonthly10k"), 65))
    area_deposit = max(500, number(area.get("deposit10k"), 1000))

    scale = stable_ratio(f"{seed}:scale", 0.88, 1.16)
    size_factor = clamp(0.94 + math.log10(max(households, 30)) * 0.045, 0.94, 1.13)
    age_factor = 1.08 if age <= 10 else 1.0 if age <= 25 else 0.93
    parking_factor = 1.03 if integer(apartment.get("parkingCount")) > households else 1.0
    recent_jeonse = area_jeonse * scale * age_factor * 0.98
    recent_sale = max(recent_jeonse / stable_ratio(f"{seed}:ratio", 0.55, 0.72), recent_jeonse * 1.18)
    recent_sale = recent_sale * size_factor * parking_factor
    official_price = recent_sale * stable_ratio(f"{seed}:official", 0.55, 0.69)
    monthly_rent = area_monthly * stable_ratio(f"{seed}:monthly", 0.92, 1.16)
    monthly_deposit = area_deposit * stable_ratio(f"{seed}:deposit", 0.85, 1.3)
    surrounding_sale = area_jeonse / 0.62
    price_change = stable_ratio(f"{seed}:change", -5.8, 8.7)
    volatility = stable_ratio(f"{seed}:volatility", 2.2, 12.5)

    return {
        "recentSale10k": round(recent_sale),
        "recentJeonse10k": round(recent_jeonse),
        "monthlyRent10k": round(monthly_rent),
        "monthlyDeposit10k": round(monthly_deposit),
        "officialPrice10k": round(official_price),
        "surroundingAverageSale10k": round(surrounding_sale),
        "surroundingAverageJeonse10k": round(area_jeonse),
        "saleGapPercent": round(((recent_sale - surrounding_sale) / surrounding_sale) * 100, 1)
        if surrounding_sale
        else 0,
        "jeonseRatio": round((recent_jeonse / recent_sale) * 100, 1) if recent_sale else 0,
        "depositOfficialRatio": round((recent_jeonse / official_price) * 100, 1) if official_price else 0,
        "priceChangeRate": round(price_change, 1),
        "volatilityRate": round(volatility, 1),
        "sourceMode": "public_area_proxy",
        "sourceLabel": "공개 단지정보 + 생활권 전월세 실거래 기반 추정",
    }


def transaction_trend(apartment: dict, market: dict) -> list[dict]:
    seed = apartment.get("id") or apartment.get("name") or "property"
    annual_change = number(market.get("priceChangeRate")) / 100
    volatility = number(market.get("volatilityRate")) / 100
    sale_now = number(market.get("recentSale10k"))
    jeonse_now = number(market.get("recentJeonse10k"))
    rent_now = number(market.get("monthlyRent10k"))
    months = [
        "2025.07",
        "2025.08",
        "2025.09",
        "2025.10",
        "2025.11",
        "2025.12",
        "2026.01",
        "2026.02",
        "2026.03",
        "2026.04",
        "2026.05",
        "2026.06",
    ]
    rows = []
    for idx, month in enumerate(months):
        progress = (idx - (len(months) - 1)) / max(1, len(months) - 1)
        wave = math.sin((idx + stable_ratio(seed, 0, 4)) * 1.27) * volatility
        factor = 1 + annual_change * progress + wave
        rows.append(
            {
                "month": month,
                "sale10k": round(sale_now * factor),
                "jeonse10k": round(jeonse_now * (1 + annual_change * progress * 0.55 + wave * 0.42)),
                "monthlyRent10k": round(rent_now * (1 + wave * 0.28), 1),
                "volume": max(1, round(stable_ratio(f"{seed}:{month}:volume", 1, 7))),
                "sourceMode": "trend_estimate",
            }
        )
    return rows


def signal_status(value: bool, warning: bool = False) -> str:
    if value:
        return "high"
    if warning:
        return "warning"
    return "ok"


def build_risk(apartment: dict, market: dict) -> dict:
    age = building_age(apartment)
    jeonse_ratio = number(market.get("jeonseRatio"))
    official_ratio = number(market.get("depositOfficialRatio"))
    volatility = number(market.get("volatilityRate"))
    surrounding_jeonse = number(market.get("surroundingAverageJeonse10k"))
    recent_jeonse = number(market.get("recentJeonse10k"))
    surrounding_gap = ((recent_jeonse - surrounding_jeonse) / surrounding_jeonse) * 100 if surrounding_jeonse else 0

    signals = [
        {
            "label": "매매가 대비 전세가율",
            "value": f"{jeonse_ratio:.1f}%",
            "status": signal_status(jeonse_ratio >= 85, jeonse_ratio >= 75),
            "evidence": f"추정 매매가 {format_money_10k(market['recentSale10k'])}, 전세가 {format_money_10k(market['recentJeonse10k'])} 기준입니다.",
        },
        {
            "label": "공시가격 대비 보증금 비율",
            "value": f"{official_ratio:.1f}%",
            "status": signal_status(official_ratio >= 120, official_ratio >= 95),
            "evidence": f"공시가격은 API 연계 전 추정값 {format_money_10k(market['officialPrice10k'])}을 사용했습니다.",
        },
        {
            "label": "주변 전세 중앙값 대비",
            "value": f"{surrounding_gap:+.1f}%",
            "status": signal_status(surrounding_gap >= 18, surrounding_gap >= 8),
            "evidence": f"생활권 전세 중앙값 {format_money_10k(surrounding_jeonse)} 대비 수준입니다.",
        },
        {
            "label": "최근 가격 변동성",
            "value": f"{volatility:.1f}%",
            "status": signal_status(volatility >= 11, volatility >= 7),
            "evidence": "실거래 API 연계 전까지 생활권 기반 변동성 추정값으로 표시합니다.",
        },
        {
            "label": "건축물 노후도",
            "value": f"{age}년" if age else "확인 필요",
            "status": signal_status(age >= 35, age >= 25),
            "evidence": f"사용승인일 {apartment.get('approvalDate') or '미제공'} 기준입니다.",
        },
        {
            "label": "등기부 권리관계",
            "value": "미입력",
            "status": "unknown",
            "evidence": "근저당, 압류, 선순위 임차권은 사용자가 등기부등본으로 별도 확인해야 합니다.",
        },
    ]

    score = 12
    weights = {"high": 20, "warning": 11, "unknown": 7, "ok": 0}
    for item in signals:
        score += weights.get(item["status"], 0)
    score = int(clamp(score, 0, 100))
    if score >= 70:
        level = "계약 전 집중 확인"
        level_key = "high"
    elif score >= 45:
        level = "주의 요소 있음"
        level_key = "warning"
    else:
        level = "낮음"
        level_key = "low"

    notable = [item for item in signals if item["status"] in {"high", "warning", "unknown"}]
    summary = (
        f"{level}: {notable[0]['label']} 등 {len(notable)}개 항목을 계약 전 확인해야 합니다."
        if notable
        else "현재 입력 데이터 기준으로 큰 위험 신호는 낮게 나타납니다."
    )
    return {
        "score": score,
        "level": level,
        "levelKey": level_key,
        "summary": summary,
        "signals": signals,
        "disclaimer": "위험 신호 점검은 계약 안전성의 법적 판정이 아니며, 등기부등본·건축물대장·임대인 세금 체납 여부 확인을 대체하지 않습니다.",
    }


def lifestyle_summary(area: dict) -> dict:
    soc = area.get("socSummary", {})
    safety = area.get("safetyEnvSummary", {})
    counts = soc.get("counts", {})
    safety_counts = safety.get("counts", {})
    return {
        "livingAreaId": area.get("id", ""),
        "livingAreaName": area.get("name", ""),
        "station": area.get("station", ""),
        "transitScore": integer(area.get("transitScore")),
        "serviceScore": integer(area.get("serviceScore")),
        "safetyScore": integer(area.get("safetyScore")),
        "carbonScore": integer(area.get("carbonScore")),
        "counts": {
            "hospital": integer(counts.get("hospital")),
            "school": integer(counts.get("school")),
            "park": integer(counts.get("park")),
            "police": integer(safety_counts.get("police")),
            "cctv": integer(safety_counts.get("cctv")),
        },
        "nearestFacilities": {
            "hospital": soc.get("nearestFacilities", {}).get("hospital"),
            "school": soc.get("nearestFacilities", {}).get("school"),
            "park": soc.get("nearestFacilities", {}).get("park"),
            "police": safety.get("nearestFacilities", {}).get("police"),
        },
    }


def ai_summary(apartment: dict, area: dict, market: dict, risk: dict) -> dict:
    lifestyle = lifestyle_summary(area)
    strengths = [
        f"{lifestyle['livingAreaName']} 생활권과 가까워 지하철 접근성 {lifestyle['transitScore']}점입니다.",
        f"월세 기준은 {format_money_10k(market['monthlyRent10k'])}로 생활권 중앙값과 비교 가능한 수준입니다.",
        f"병원 {lifestyle['counts']['hospital']}개, 학교 {lifestyle['counts']['school']}개, 공원 {lifestyle['counts']['park']}개가 생활 SOC 점수에 반영됐습니다.",
    ]
    cautions = [
        f"{item['label']} {item['value']}: {item['evidence']}"
        for item in risk["signals"]
        if item["status"] in {"high", "warning", "unknown"}
    ][:3]
    weaknesses = []
    if number(market.get("saleGapPercent")) > 8:
        weaknesses.append(f"주변 평균 매매 추정가보다 {market['saleGapPercent']}% 높아 가격 협상 여지가 제한될 수 있습니다.")
    if building_age(apartment) >= 25:
        weaknesses.append("준공 후 25년 이상 경과해 수선비, 배관, 주차 편의 확인이 필요합니다.")
    if not weaknesses:
        weaknesses.append("단지 단위 실거래·공시가격 API 키 연계 전까지 가격 정보는 추정값으로 검토해야 합니다.")

    if risk["levelKey"] == "high":
        recommendation = "전세 계약은 보수적으로 접근하고 등기부·보증보험·선순위 권리 확인 후 판단하는 것이 좋습니다."
    elif risk["levelKey"] == "warning":
        recommendation = "입지와 생활권 장점은 있으나 전세가율·공시가격 대비 비율을 계약 전 재검증해야 합니다."
    else:
        recommendation = "현재 공개 데이터 기준으로는 생활권·가격 균형이 무난하지만 권리관계 확인은 별도 필요합니다."

    return {
        "headline": f"{apartment.get('name')}은 {lifestyle['livingAreaName']} 생활권의 주거비·이동·생활 SOC를 함께 검토할 수 있는 후보입니다.",
        "strengths": strengths,
        "weaknesses": weaknesses,
        "cautions": cautions,
        "recommendation": recommendation,
    }


def build_property_preview(apartment: dict) -> dict:
    area = nearest_living_area(apartment)
    market = estimate_market(apartment, area)
    risk = build_risk(apartment, market)
    return {
        "sale10k": market["recentSale10k"],
        "saleLabel": format_money_10k(market["recentSale10k"]),
        "jeonse10k": market["recentJeonse10k"],
        "jeonseRatio": market["jeonseRatio"],
        "riskScore": risk["score"],
        "riskLevel": risk["level"],
        "riskLevelKey": risk["levelKey"],
        "sourceMode": market["sourceMode"],
    }


def build_property_detail(apartment: dict) -> dict:
    area = nearest_living_area(apartment)
    market = estimate_market(apartment, area)
    trend = transaction_trend(apartment, market)
    risk = build_risk(apartment, market)
    lifestyle = lifestyle_summary(area)
    age = building_age(apartment)
    options = area_options(apartment)

    return {
        "id": apartment.get("id"),
        "name": apartment.get("name"),
        "address": apartment.get("address"),
        "district": apartment.get("district"),
        "dong": apartment.get("dong"),
        "lat": apartment.get("lat"),
        "lng": apartment.get("lng"),
        "buildingType": apartment.get("category") or "공동주택",
        "housingType": apartment.get("housingType") or "확인 필요",
        "landUse": "주거지역(정밀 용도지역은 VWorld/토지이음 API 연계 예정)",
        "approvalDate": apartment.get("approvalDate"),
        "approvalYear": integer(apartment.get("approvalYear")),
        "buildingAge": age,
        "households": integer(apartment.get("households")),
        "buildingCount": integer(apartment.get("buildingCount")),
        "parkingCount": integer(apartment.get("parkingCount")),
        "grossFloorAreaM2": number(apartment.get("grossFloorAreaM2")),
        "areaOptions": options,
        "management": {
            "heating": apartment.get("heating") or "확인 필요",
            "method": apartment.get("managementMethod") or "확인 필요",
        },
        "price": market,
        "transactions": trend,
        "risk": risk,
        "lifestyle": lifestyle,
        "aiSummary": ai_summary(apartment, area, market, risk),
        "dataStatus": {
            "buildingInfo": "실데이터: 서울시 OpenAptInfo",
            "rentalMarket": "실데이터 집계: 서울시 2025 전월세 거래 생활권 중앙값",
            "salePrice": "추정: 국토교통부 매매 실거래가 API 키 연계 전 생활권 기반 보정",
            "officialPrice": "추정: 공동주택 공시가격 API/데이터 연계 전 보수적 보정",
            "landUse": "연계 예정: VWorld/토지이음 용도지역 데이터",
        },
        "sources": PUBLIC_SOURCES,
        "limitations": [
            "현재 단지 매매가·공시가격은 API 키 없이도 화면 검증이 가능하도록 공개 생활권 데이터 기반 추정값으로 표시합니다.",
            "전세 위험 신호는 법적 판정이 아니라 계약 전 확인 항목을 좁히기 위한 체크리스트입니다.",
            "등기부 권리관계, 세금 체납, 보증보험 가입 가능 여부는 사용자가 별도 서류로 확인해야 합니다.",
        ],
    }


def property_agent_answer(question: str, detail: dict, candidates: list[dict]) -> dict:
    text = str(question or "").strip()
    price = detail["price"]
    risk = detail["risk"]
    lifestyle = detail["lifestyle"]
    base_basis = [
        f"전세가율 {price['jeonseRatio']}%",
        f"공시가격 대비 보증금 비율 {price['depositOfficialRatio']}%",
        f"최근 매매 추정가 {format_money_10k(price['recentSale10k'])}",
        f"{lifestyle['livingAreaName']} 생활권 SOC 병원 {lifestyle['counts']['hospital']}개·학교 {lifestyle['counts']['school']}개·공원 {lifestyle['counts']['park']}개",
    ]

    safer = sorted(
        [
            item
            for item in candidates
            if item.get("id") != detail["id"] and item.get("preview", {}).get("riskScore", 100) < risk["score"]
        ],
        key=lambda item: (item["preview"]["riskScore"], abs(item["preview"]["sale10k"] - price["recentSale10k"])),
    )[:3]

    if any(token in text for token in ["비슷", "더 안전", "대안", "찾아"]):
        if safer:
            names = ", ".join(f"{item['name']}({item['preview']['riskLevel']})" for item in safer)
            answer = f"현재 스냅샷 기준 더 낮은 위험 점수 후보는 {names}입니다. 비교표에 추가해 전세가율과 생활권 점수를 함께 보세요."
        else:
            answer = "현재 로딩된 단지 중에는 더 낮은 위험 점수 후보가 충분하지 않습니다. 서울 OpenAptInfo 키를 연결하면 전체 단지에서 대안을 찾을 수 있습니다."
    elif any(token in text for token in ["전세", "괜찮", "안전", "사기", "깡통"]):
        answer = (
            f"{detail['name']} 전세는 '{risk['level']}' 단계로 보입니다. "
            f"전세가율 {price['jeonseRatio']}%, 공시가격 대비 보증금 비율 {price['depositOfficialRatio']}%가 핵심 근거입니다. "
            "계약 전에는 등기부등본의 선순위 권리, 보증보험 가능 여부, 임대인 체납 여부를 반드시 확인하세요."
        )
    elif any(token in text for token in ["왜", "추천", "장점"]):
        answer = (
            f"{detail['name']}은 {lifestyle['livingAreaName']} 생활권 기준으로 지하철 접근성 {lifestyle['transitScore']}점, "
            f"생활 SOC {lifestyle['serviceScore']}점입니다. "
            f"매매 추정가는 주변 평균 대비 {price['saleGapPercent']:+.1f}%이며, "
            f"전세 위험 신호는 {risk['level']}입니다."
        )
    else:
        answer = (
            f"{detail['name']}은 가격·생활권·위험 신호를 함께 보면 {risk['level']} 단계입니다. "
            "질문을 전세 안전성, 추천 이유, 비슷한 가격대 대안 중 하나로 구체화하면 더 정확히 답할 수 있습니다."
        )

    return {
        "answer": answer,
        "basis": base_basis,
        "suggestedComparisons": [
            {
                "id": item["id"],
                "name": item["name"],
                "saleLabel": format_money_10k(item["preview"]["sale10k"]),
                "riskLevel": item["preview"]["riskLevel"],
            }
            for item in safer
        ],
        "disclaimer": risk["disclaimer"],
    }
