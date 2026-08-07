#!/usr/bin/env python3
"""전세사기 예방 보강 지표.

HUG 전세사기예방센터(khug.or.kr/jeonse)가 공개한 기준을 그대로 쓰되,
그 사이트가 사용자에게 떠넘긴 5가지 부담을 계산으로 대신 처리한다.

1. 임대인 동의가 필요한 정보 -> 동의 없이 확인 가능한 경로를 먼저 제시하고,
   동의 거부 자체를 계약 판단 신호로 다룬다.
2. 선순위 보증금 사각지대 -> 주택 유형별로 등기부에 안 잡히는 항목을 명시한다.
3. 안전계약 컨설팅 8개소 -> 단지에서 가장 가까운 센터와 운영요일을 붙인다.
4. 대항력 1일 공백 -> 잔금일 기준 위험 구간과 특약 문구를 생성한다.
5. 등기부 해석 부담 -> 깡통주택 80% 기준을 "근저당 얼마까지 안전한가"로 환산한다.
"""

from __future__ import annotations

import math

# HUG 깡통주택 정의: (보증금 + 대출) 합계가 집값의 80%를 넘는 주택.
GAPTONG_THRESHOLD_PCT = 80.0

# 전국 전세피해 및 예방지원센터. 주소/전화/운영요일은 HUG 공고 기준이고,
# 좌표는 8개 광역 거점을 거리 순으로 고르기 위한 근사값이다(랭킹 용도로만 사용).
SUPPORT_CENTERS = [
    {
        "name": "서울(강서) 전세피해 및 예방지원센터",
        "address": "서울특별시 강서구 화곡로 179, 대한상공회의소 서울기술교육센터 2층",
        "phone": "02-6917-8119",
        "days": "월·화·목·금",
        "lat": 37.5410,
        "lng": 126.8410,
    },
    {
        "name": "경기 전세피해 및 예방지원센터",
        "address": "경기도 수원시 영통구 도청로 50, 복합시설관 1층",
        "phone": "031-242-2450",
        "days": "화·수·목",
        "lat": 37.2894,
        "lng": 127.0538,
    },
    {
        "name": "인천 전세피해 및 예방지원센터",
        "address": "인천광역시 부평구 열우물로 90, 부평더샵센트럴시티 상가 A동 305호",
        "phone": "032-440-1803",
        "days": "월·화·목·금",
        "lat": 37.4869,
        "lng": 126.7150,
    },
    {
        "name": "부산 전세피해 및 예방지원센터",
        "address": "부산광역시 연제구 중앙대로 1001, 부산광역시청 1층",
        "phone": "051-888-5101",
        "days": "월·화·수·목",
        "lat": 35.1795,
        "lng": 129.0756,
    },
    {
        "name": "대전 전세피해 및 예방지원센터",
        "address": "대전광역시 중구 중앙로 101, 옛 충남도청사 본관 2층",
        "phone": "042-270-6536",
        "days": "월·화·목·금",
        "lat": 36.3280,
        "lng": 127.4230,
    },
    {
        "name": "대구 전세피해 및 예방지원센터",
        "address": "대구광역시 북구 연암로 40, 대구광역시청 산격청사 별관3동 2층",
        "phone": "053-803-4984",
        "days": "월·화·목·금",
        "lat": 35.8900,
        "lng": 128.6030,
    },
    {
        "name": "광주 전세피해 및 예방지원센터",
        "address": "광주광역시 서구 내방로 111, 광주광역시청 1층",
        "phone": "062-613-4875",
        "days": "월·화·금",
        "lat": 35.1600,
        "lng": 126.8515,
    },
    {
        "name": "전남 전세피해 및 예방지원센터",
        "address": "전라남도 순천시 해룡면 매안로 16, 전남 동부지역본부 內",
        "phone": "061-286-7972",
        "days": "수·목·금",
        "lat": 34.9430,
        "lng": 127.5340,
    },
]

CENTER_HOURS = "10:00~17:00 (점심 12:00~13:00), 주말·공휴일 휴무"

# 임대인 동의 없이 임차인이 직접 확인할 수 있는 경로.
SELF_SERVE_CHECKS = [
    {
        "label": "등기부등본(등기사항전부증명서)",
        "target": "소유자, 근저당, 압류·가압류, 신탁, 선순위 임차권",
        "how": "대법원 인터넷등기소에서 누구나 열람 700원",
        "url": "http://www.iros.go.kr/PMainJ.jsp",
    },
    {
        "label": "상습 채무불이행자 명단",
        "target": "HUG 구상채권 2억원 이상 누적된 임대인",
        "how": "HUG 전세사기예방센터에서 임대인 성명으로 조회",
        "url": "https://www.khug.or.kr/jeonse/web/s01/s010320.jsp",
    },
    {
        "label": "보증금 미반환 임대사업자 명단",
        "target": "판결·조정 후에도 1억원 이상 미반환한 등록임대사업자",
        "how": "국토교통부·렌트홈 공개 명단 조회",
        "url": "https://www.khug.or.kr/jeonse/web/s01/s010502.jsp",
    },
    {
        "label": "공인중개사 등록 여부",
        "target": "무자격 중개, 자격증 대여 여부",
        "how": "국가공간정보포털 부동산중개업 조회",
        "url": "https://www.nsdi.go.kr/",
    },
    {
        "label": "다가구 전입세대 확정일자 열람",
        "target": "나보다 앞선 세입자들의 보증금 총액",
        "how": "주민센터에서 임대차 계약 예정자도 열람 가능",
        "url": "https://www.khug.or.kr/jeonse/web/s02/s020402.jsp",
    },
]

# 임대인 동의가 있어야 확인되는 정보. 거부당했을 때가 진짜 문제라 대응책을 함께 둔다.
CONSENT_REQUIRED_CHECKS = [
    {
        "label": "미납 국세·지방세 열람",
        "why": "당해세는 확정일자보다 앞서 배당되어 보증금을 먼저 잠식한다.",
        "ifRefused": "거부 자체를 위험 신호로 본다. 계약을 이어간다면 '미납 조세 없음'을 특약에 넣고 위반 시 계약 해제·손해배상 조항을 함께 기재한다.",
    },
    {
        "label": "납세증명서·사회보험 완납증명서",
        "why": "최우선 임금채권은 최우선변제 보증금과 같은 순위로 배당된다.",
        "ifRefused": "임대인이 법인·사업자면 특히 확인이 필요하다. 거부 시 보증금 규모를 낮추거나 전세보증금반환보증 가입을 계약 조건으로 요구한다.",
    },
]


def _haversine_km(a_lat: float, a_lng: float, b_lat: float, b_lng: float) -> float:
    radius = 6371.0
    d_lat = math.radians(b_lat - a_lat)
    d_lng = math.radians(b_lng - a_lng)
    inner = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(a_lat)) * math.cos(math.radians(b_lat)) * math.sin(d_lng / 2) ** 2
    )
    return radius * 2 * math.asin(math.sqrt(inner))


def _money(value_10k: float) -> str:
    amount = int(round(float(value_10k or 0)))
    if amount >= 10000:
        eok, man = divmod(amount, 10000)
        return f"{eok}억 {man:,}만원" if man else f"{eok}억원"
    return f"{amount:,}만원"


def gaptong_verdict(market: dict) -> dict:
    """전세가율을 HUG 80% 기준과 대조해 '근저당 얼마까지 안전한가'로 바꾼다."""
    sale = float(market.get("recentSale10k") or 0)
    jeonse = float(market.get("recentJeonse10k") or 0)
    ratio = (jeonse / sale * 100) if sale else 0.0
    headroom_pct = GAPTONG_THRESHOLD_PCT - ratio
    headroom_10k = max(0.0, sale * headroom_pct / 100)

    if sale <= 0 or jeonse <= 0:
        key, label = "unknown", "판정 불가"
        detail = "매매가 또는 전세가 추정치가 없어 깡통주택 기준을 계산할 수 없습니다."
    elif ratio >= GAPTONG_THRESHOLD_PCT:
        key, label = "danger", "깡통주택 기준 초과"
        detail = (
            f"근저당이 0원이어도 보증금만으로 집값의 {ratio:.1f}%를 차지해 "
            f"HUG 깡통주택 기준({GAPTONG_THRESHOLD_PCT:.0f}%)을 이미 넘습니다."
        )
    elif headroom_pct < 10:
        key, label = "warning", "여력 거의 없음"
        detail = (
            f"근저당이 {_money(headroom_10k)}만 잡혀도 깡통주택 기준을 넘습니다. "
            "등기부 을구에서 채권최고액을 반드시 확인하세요."
        )
    elif headroom_pct < 20:
        key, label = "caution", "여력 보통"
        detail = f"근저당 채권최고액이 {_money(headroom_10k)}을 넘으면 깡통주택 기준을 초과합니다."
    else:
        key, label = "safe", "여력 있음"
        detail = f"근저당 채권최고액 {_money(headroom_10k)}까지는 깡통주택 기준 아래에 머뭅니다."

    return {
        "ratioPct": round(ratio, 1),
        "thresholdPct": GAPTONG_THRESHOLD_PCT,
        "headroomPct": round(max(0.0, headroom_pct), 1),
        "headroom10k": round(headroom_10k, 1),
        "headroomLabel": _money(headroom_10k),
        "verdictKey": key,
        "verdictLabel": label,
        "detail": detail,
        "basis": "HUG 기준: (보증금 + 대출) 합계가 집값의 80%를 넘으면 깡통주택",
    }


def blind_spots(apartment: dict) -> list[dict]:
    """주택 유형별로 등기부·시세에 잡히지 않는 항목을 명시한다."""
    category = str(apartment.get("category") or "")
    households = int(apartment.get("households") or 0)
    rows = []

    if any(token in category for token in ("연립", "다세대", "도시형")):
        rows.append(
            {
                "label": "공동담보 설정",
                "level": "warning",
                "detail": "연립·다세대·도시형생활주택은 여러 호실이 하나의 근저당에 묶이는 공동담보가 흔합니다. 등기부 을구의 공동담보목록까지 확인해야 합니다.",
            }
        )
    if "다가구" in category or "단독" in category:
        rows.append(
            {
                "label": "선순위 보증금 미표시",
                "level": "danger",
                "detail": "다가구주택은 앞선 세입자들의 보증금이 등기부에 전혀 나타나지 않습니다. 주민센터에서 전입세대 확정일자 열람으로 별도 합산해야 합니다.",
            }
        )
    if households and households <= 30:
        rows.append(
            {
                "label": "시세 표본 부족",
                "level": "warning",
                "detail": f"{households}세대 소규모 단지는 실거래 사례가 적어 시세 추정 오차가 큽니다. 신축이라면 준공 전 분양가에 기대지 말고 인근 준공 후 거래를 확인하세요.",
            }
        )
    elif not households:
        rows.append(
            {
                "label": "세대수 미제공",
                "level": "warning",
                "detail": "공공 단지 데이터에 세대수가 비어 있어 단지 규모를 판단할 수 없습니다. 화면의 0세대는 실제 값이 아니라 누락입니다. 건축물대장으로 확인하세요.",
            }
        )
    if not apartment.get("approvalDate"):
        rows.append(
            {
                "label": "사용승인일 미제공",
                "level": "warning",
                "detail": "건축물대장으로 사용승인일과 위반건축물 등재 여부를 직접 확인해야 합니다.",
            }
        )

    rows.append(
        {
            "label": "등기부 권리관계",
            "level": "info",
            "detail": "근저당·압류·신탁·선순위 임차권은 어떤 시세 데이터에도 담기지 않습니다. 계약 전과 잔금 직전 두 번 열람하세요.",
        }
    )
    return rows


def tenancy_timeline(apartment: dict) -> dict:
    """대항력 1일 공백을 단계로 펼치고 그 구간을 막는 특약 문구를 만든다."""
    name = str(apartment.get("name") or "해당 주택")
    address = str(apartment.get("address") or "")
    return {
        "gapSummary": "전입신고의 대항력은 다음날 0시에 생기지만, 근저당 설정과 소유권 이전은 접수 당일 즉시 효력이 생깁니다. 이 하루가 주택임대차보호법의 구조적 공백입니다.",
        "steps": [
            {
                "day": "계약일",
                "action": "확정일자 먼저 받기",
                "detail": "확정일자는 입주 전에도 계약서만 있으면 받을 수 있습니다. 임대차 신고를 하면 자동 부여됩니다.",
                "risk": "safe",
            },
            {
                "day": "잔금일 당일",
                "action": "잔금 전 등기부 재열람",
                "detail": "접수 중인 등기는 '신청사건 처리 중'으로 표시됩니다. 표시가 보이면 잔금을 지급하지 마세요.",
                "risk": "danger",
            },
            {
                "day": "잔금일 당일",
                "action": "전입신고 + 점유 개시",
                "detail": "실제 거주와 전입신고를 모두 마쳐야 대항력 요건이 채워집니다.",
                "risk": "warning",
            },
            {
                "day": "잔금 다음날 0시",
                "action": "대항력 발생",
                "detail": "이 시점 전에 설정된 근저당은 내 보증금보다 앞섭니다.",
                "risk": "warning",
            },
            {
                "day": "잔금 +2~3일",
                "action": "등기부 3차 확인",
                "detail": "특약대로 근저당·신탁등기가 말소됐는지, 새 등기가 붙지 않았는지 확인합니다.",
                "risk": "safe",
            },
        ],
        "clauses": [
            {
                "title": "소유권·근저당 동결 특약",
                "text": (
                    f"임대인은 잔금 지급일 다음날까지 {name}({address})에 대하여 "
                    "소유권 이전, 근저당권 설정, 전세권 설정 등 일체의 권리 변동 행위를 하지 아니한다. "
                    "이를 위반한 경우 임차인은 계약을 해제할 수 있고, 임대인은 보증금 전액을 즉시 반환하며 손해를 배상한다."
                ),
            },
            {
                "title": "미납 조세 없음 확약 특약",
                "text": (
                    "임대인은 계약 체결일 현재 국세 및 지방세 체납 사실이 없음을 확약하며, "
                    "임차인의 요청 시 납세증명서를 제출한다. 사실과 다를 경우 임차인은 계약을 해제할 수 있고 "
                    "임대인은 보증금 전액을 즉시 반환한다."
                ),
            },
            {
                "title": "선순위 권리 말소 특약",
                "text": (
                    "임대인은 잔금 지급일까지 기존 근저당권 및 신탁등기를 말소하고 그 말소 사실을 "
                    "등기사항전부증명서로 임차인에게 확인시킨다. 말소가 완료되지 아니한 경우 "
                    "임차인은 잔금 지급을 거절하거나 계약을 해제할 수 있다."
                ),
            },
        ],
    }


def nearest_center(apartment: dict) -> dict | None:
    lat = apartment.get("lat")
    lng = apartment.get("lng")
    if lat is None or lng is None:
        return None
    ranked = sorted(
        SUPPORT_CENTERS,
        key=lambda center: _haversine_km(float(lat), float(lng), center["lat"], center["lng"]),
    )
    best = ranked[0]
    distance = _haversine_km(float(lat), float(lng), best["lat"], best["lng"])
    return {
        **best,
        "distanceKm": round(distance, 1),
        "hours": CENTER_HOURS,
        "service": "공인중개사(안전계약 컨설턴트)가 등기부등본·건축물대장을 함께 검토합니다. 예비 임차인도 계약 전에 이용할 수 있습니다.",
        "note": "상담은 참고용이며 법적 책임을 부담하지 않습니다. 센터별 운영 요일이 다르니 유선 예약 후 방문하세요.",
        "reserveUrl": "https://www.khug.or.kr/jeonse/web/s04/s040604.jsp",
    }


def build_safeguard(apartment: dict, market: dict) -> dict:
    return {
        "gaptong": gaptong_verdict(market),
        "blindSpots": blind_spots(apartment),
        "selfServeChecks": SELF_SERVE_CHECKS,
        "consentChecks": CONSENT_REQUIRED_CHECKS,
        "timeline": tenancy_timeline(apartment),
        "center": nearest_center(apartment),
        "source": {
            "label": "HUG 전세사기예방센터",
            "url": "https://www.khug.or.kr/jeonse/web/s01/s010102.jsp",
        },
    }


if __name__ == "__main__":
    over = gaptong_verdict({"recentSale10k": 50000, "recentJeonse10k": 42000})
    assert over["verdictKey"] == "danger", over
    tight = gaptong_verdict({"recentSale10k": 50000, "recentJeonse10k": 37500})  # 75%
    assert tight["verdictKey"] == "warning" and tight["headroom10k"] == 2500.0, tight
    roomy = gaptong_verdict({"recentSale10k": 50000, "recentJeonse10k": 25000})  # 50%
    assert roomy["verdictKey"] == "safe" and roomy["headroom10k"] == 15000.0, roomy
    assert gaptong_verdict({})["verdictKey"] == "unknown"

    seoul = {"name": "테스트단지", "address": "서울시", "lat": 37.5, "lng": 127.0, "category": "아파트", "households": 500}
    assert nearest_center(seoul)["name"].startswith("서울"), nearest_center(seoul)
    busan = {**seoul, "lat": 35.18, "lng": 129.07}
    assert nearest_center(busan)["name"].startswith("부산")
    assert nearest_center({"name": "x"}) is None

    villa = blind_spots({"category": "연립주택", "households": 20, "approvalDate": "1998-01-01"})
    labels = [row["label"] for row in villa]
    assert "공동담보 설정" in labels and "시세 표본 부족" in labels, labels
    missing = [row["label"] for row in blind_spots({"category": "아파트", "households": 0, "approvalDate": "1998-01-01"})]
    assert "세대수 미제공" in missing and "시세 표본 부족" not in missing, missing
    big = [row["label"] for row in blind_spots({"category": "아파트", "households": 500, "approvalDate": "1998-01-01"})]
    assert big == ["등기부 권리관계"], big
    assert len(build_safeguard(seoul, {"recentSale10k": 50000, "recentJeonse10k": 37500})["timeline"]["clauses"]) == 3
    print("jeonse_safeguard self-check OK")
