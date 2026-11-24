"""계약 전·후에 필요한 정보를 판정 결과 옆에 모아 주는 안내 블록.

jeonse_verdict.evaluate()가 판정을 낸 뒤 이 모듈을 불러 다섯 덩어리를 붙인다.
- depositGuide: 시세와 비교한 이 보증금, 기준선별 최대 보증금
- repayment: 집이 경매로 넘어갈 때 누가 먼저 받는지(배당 순서)와 내 보증금 회수 추정
- documents: 체크리스트 항목과 그걸 확인할 서류를 1대1로 묶은 목록
- guarantees: 전세보증금 반환보증 가입 가능성과 예방·지원 제도 연결
- aftercare: 계약일·잔금일·만료일에서 계산한 계약 후 할 일

공공데이터를 직접 못 가져오는 정보는 공식 사이트로 연결만 한다. 값은 모두 공개 기준이며
법적 판정이 아니다. 기준값은 아래 상수에 모아 두고 출처를 함께 적는다.
"""

from __future__ import annotations

from datetime import date, timedelta
from math import isfinite

MORTGAGE_PENDING_LABEL = "근저당 미확인"
PRIOR_PENDING_LABEL = "선순위 보증금 미확인"
DEPOSIT_MISSING_LABEL = "계약 보증금 미입력"

# --- 기준값 ---------------------------------------------------------------------

# 주택임대차보호법 시행령 제10조·제11조 (2023.2.21 시행). 보증금 상한 이하일 때 최우선변제액까지 먼저 받는다.
# 최우선변제 합계는 주택가액(낙찰가)의 1/2을 넘지 못한다.
SMALL_TENANT = {
    "seoul": {"label": "서울", "limit10k": 16500, "priority10k": 5500},
    "overcrowded": {"label": "과밀억제권역·세종·용인·화성·김포", "limit10k": 14500, "priority10k": 4800},
    "metro": {"label": "광역시·안산·광주·파주·이천·평택", "limit10k": 8500, "priority10k": 2800},
    "other": {"label": "그 밖의 지역", "limit10k": 7500, "priority10k": 2500},
}
SMALL_TENANT_BASIS = "최우선변제: 주택임대차보호법 시행령 제10·11조 (2023.2.21 개정값, 현행). 적용 금액은 선순위 담보물권 설정일 기준"
OVERCROWDED_CITIES = ("인천", "의정부", "구리", "하남", "고양", "수원", "성남", "안양", "부천", "광명", "과천",
                      "의왕", "군포", "시흥", "남양주", "세종", "용인", "화성", "김포")
METRO_CITIES = ("부산", "대구", "광주광역시", "대전", "울산", "안산", "광주시", "파주", "이천", "평택")

# 낙찰가율 기본값 (지지옥션 집계, 언론 보도). 평균이라 개별 집은 더 낮을 수 있어 사용자가 바꿀 수 있게 한다.
# 서울 아파트 2026 누적 97.5%(조선비즈 2026.11.5·한국경제 2026.10.20), 빌라 서울 77.0%·경기 60.9%·인천 60.4%(2026.1~9, 비즈N 2026.10.25).
# 서울 밖 아파트는 공개 통계를 찾지 못해 85%로 둔다.
AUCTION_RATE_PCT = {
    "apartment": {"seoul": 97, "default": 85},
    "other": {"seoul": 77, "default": 60},
}
AUCTION_COST_PCT = 1.0  # 경매 집행비용, 낙찰가 대비 가정
AUCTION_BASIS = "낙찰가율: 서울 아파트 97%·서울 빌라 77%·경기·인천 빌라 약 60% (지지옥션 2026 집계 보도) — 평균값이라 직접 조정 가능"

# HUG 전세보증금반환보증 가입 요건 (2023.5.1 이후)
HUG_DEPOSIT_CAP10K = {"capital": 70000, "other": 50000}  # 수도권 7억, 그 외 5억
HUG_RATIO = 0.9  # 보증금 + 선순위채권 ≤ 주택가격 × 90%
HUG_OFFICIAL_MULTIPLIER = 1.4  # 공시가격으로 주택가격을 잡을 때 140%
HUG_SENIOR_LIMIT = {"default": 0.6, "multi": 0.8}  # 선순위채권 ≤ 주택가격 60% (다가구는 선순위 + 타세대 보증금 ≤ 80%)

LINKS = {
    "iros": ("인터넷등기소", "http://www.iros.go.kr"),
    "gov24": ("정부24", "https://www.gov.kr"),
    "gov24Fee": ("정부24 · 반환보증 보증료 지원", "https://www.gov.kr/portal/rcvfvrSvc/dtlEx/161300000103"),
    "khugApp": ("HUG 안심전세앱", "https://www.khug.or.kr/jeonse/web/s01/s010102.jsp"),
    "eais": ("세움터", "https://cloud.eais.go.kr"),
    "realtyprice": ("부동산공시가격알리미", "https://www.realtyprice.kr"),
    "rtmolit": ("국토부 실거래가 공개시스템", "https://rt.molit.go.kr"),
    "rtms": ("부동산거래관리시스템(임대차 신고)", "https://rtms.molit.go.kr"),
    "hometax": ("홈택스", "https://www.hometax.go.kr"),
    "wetax": ("위택스", "https://www.wetax.go.kr"),
    "nsdi": ("국가공간정보포털 부동산중개업 조회", "https://www.nsdi.go.kr"),
    "khug": ("HUG 안심전세포털", "https://www.khug.or.kr/jeonse"),
    "khugGuarantee": ("HUG 전세보증금반환보증", "https://www.khug.or.kr/hug/web/ig/dr/igdr000001.jsp"),
    "hf": ("HF 전세지킴보증", "https://www.hf.go.kr/ko/sub02/sub02_05_01.do"),
    "sgi": ("SGI서울보증 전세금보장신용보험", "https://m.sgic.co.kr/biz/cmw/index.html?p=CMWPRD030101F01"),
    "ecourt": ("대법원 전자소송(임차권등기명령)", "https://ecfs.scourt.go.kr"),
    "seoulHousing": ("서울 주거안심종합센터", "https://housing.seoul.go.kr/site/main/content/sh04_050100"),
}


def _num(value) -> float | None:
    if value in (None, "") or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if isfinite(number) and number >= 0 else None


def _date(value) -> date | None:
    try:
        return date.fromisoformat(str(value)[:10]) if value else None
    except ValueError:
        return None


def add_months(d: date, months: int) -> date:
    month = d.month - 1 + months
    year, month = d.year + month // 12, month % 12 + 1
    days = [31, 29 if year % 4 == 0 and (year % 100 or year % 400 == 0) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return date(year, month, min(d.day, days[month - 1]))


def money(value_10k: float | None) -> str:
    if value_10k is None:
        return "미확인"
    amount = int(round(value_10k))
    sign = "-" if amount < 0 else ""
    eok, man = divmod(abs(amount), 10000)
    if eok and man:
        return f"{sign}{eok}억 {man:,}만원"
    if eok:
        return f"{sign}{eok}억원"
    return f"{sign}{man:,}만원"


def link(key: str) -> dict:
    label, url = LINKS[key]
    return {"label": label, "url": url}


def region_of(address: str) -> str:
    text = str(address or "")
    if "서울" in text:
        return "seoul"
    if any(city in text for city in OVERCROWDED_CITIES):
        return "overcrowded"
    if any(city in text for city in METRO_CITIES):
        return "metro"
    return "other"


def is_capital(address: str) -> bool:
    text = str(address or "")
    return any(token in text for token in ("서울", "인천", "경기"))


# --- 1. 적정 보증금 ---------------------------------------------------------------

def pending_senior_reason(ltv: dict) -> str:
    if ltv.get("priorDepositPending"):
        return PRIOR_PENDING_LABEL
    if ltv["mortgage10k"] is None:
        return MORTGAGE_PENDING_LABEL
    return ""


def deposit_guide(inp: dict, ltv: dict) -> dict:
    deposit = ltv["deposit10k"]
    price = ltv["price10k"]
    pending = pending_senior_reason(ltv)
    senior = None if pending else ltv["mortgage10k"] + ltv["prior10k"]
    market = inp.get("market") or {}
    jeonse = _num(market.get("jeonse10k"))
    nearby = _num(market.get("surroundingJeonse10k"))
    listing = inp.get("listing") or {}

    def cap(pct):
        return round(price * pct / 100 - senior) if price and senior is not None and deposit is not None else None

    hug = hug_limit(inp, ltv)
    lines = [
        {"id": "safe70", "label": "안전선 (70%)", "max10k": cap(70), "note": "주의가 시작되는 실무 권고선"},
        {"id": "gaptong80", "label": "깡통전세 경계 (80%)", "max10k": cap(80), "note": "넘으면 깡통전세로 보는 실무 기준"},
        {"id": "hug", "label": "보증보험 가입선", "max10k": hug["max10k"], "note": hug["basis"]},
    ]
    for line in lines:
        line["fits"] = None if line["max10k"] is None else deposit <= line["max10k"]

    compare = jeonse or nearby
    gap_pct = round((deposit - compare) / compare * 100, 1) if compare and deposit else None
    if deposit is None:
        market_note = "계약 보증금을 입력하면 전세 시세와 비교할 수 있어요."
    elif gap_pct is None:
        market_note = "비교할 전세 시세가 없어요."
    elif gap_pct > 10:
        market_note = f"주변 전세 시세보다 {gap_pct}% 높아요. 시세보다 비싼 전세는 깡통전세로 이어지기 쉬워요."
    elif gap_pct < -15:
        market_note = f"주변 전세 시세보다 {abs(gap_pct)}% 낮아요. 너무 싼 매물은 권리관계 문제를 숨긴 경우가 있어 등기부를 꼭 보세요."
    else:
        market_note = "주변 전세 시세와 비슷한 수준이에요."

    safe_max = lines[0]["max10k"]
    if pending:
        headline = pending
    elif deposit is None:
        headline = DEPOSIT_MISSING_LABEL
    elif safe_max is None:
        headline = "집값을 알면 적정 보증금을 계산할 수 있어요."
    elif deposit <= safe_max:
        headline = f"이 보증금은 안전선 안이에요. 최대 {money(safe_max)}까지가 안전선이에요."
    else:
        headline = f"안전선보다 {money(deposit - safe_max)} 높아요. 안전선 기준 적정 보증금은 {money(max(safe_max, 0))}이에요."

    return {
        "deposit10k": deposit,
        "listingSource": listing.get("source") or "",
        "listingUrl": listing.get("url") or "",
        "marketJeonse10k": jeonse,
        "nearbyJeonse10k": nearby,
        "marketSourceLabel": market.get("sourceLabel") or "",
        "marketIsEstimate": market.get("source") == "estimate",
        "gapPct": gap_pct,
        "marketNote": market_note,
        "price10k": price,
        "senior10k": senior,
        "seniorKnown": senior is not None,
        "lines": lines,
        "headline": headline,
    }


def hug_limit(inp: dict, ltv: dict) -> dict:
    """HUG 반환보증으로 보장받을 수 있는 최대 보증금(선순위 차감)."""
    prop = inp.get("property") or {}
    housing = prop.get("housingType") or "villa"
    official = _num((inp.get("price") or {}).get("official10k"))
    region_cap = HUG_DEPOSIT_CAP10K["capital" if is_capital(prop.get("address")) else "other"]
    if housing != "apartment" and official:
        base = official * HUG_OFFICIAL_MULTIPLIER
        basis = f"공시가격 × 140% × 90% − 선순위, 보증금 한도 {money(region_cap)}"
    elif ltv["price10k"]:
        base = ltv["price10k"]
        basis = f"주택가격 × 90% − 선순위, 보증금 한도 {money(region_cap)}"
    else:
        return {"max10k": None, "basis": "주택가격이 없어 계산하지 못했어요", "regionCap10k": region_cap, "base10k": None}
    pending = pending_senior_reason(ltv)
    if pending:
        return {"max10k": None, "basis": pending, "regionCap10k": region_cap, "base10k": base}
    if ltv["deposit10k"] is None:
        return {"max10k": None, "basis": DEPOSIT_MISSING_LABEL, "regionCap10k": region_cap, "base10k": base}
    senior = ltv["mortgage10k"] + ltv["prior10k"]
    return {"max10k": round(min(base * HUG_RATIO - senior, region_cap)), "basis": basis, "regionCap10k": region_cap,
            "base10k": base}


# --- 2. 보증금 반환 순위 -------------------------------------------------------------

def repayment(inp: dict, ltv: dict) -> dict:
    pending = pending_senior_reason(ltv)
    if pending:
        return {"available": False, "note": pending}
    prop = inp.get("property") or {}
    housing = prop.get("housingType") or "villa"
    price = ltv["price10k"]
    deposit = ltv["deposit10k"]
    if deposit is None:
        return {"available": False, "note": "계약 보증금을 입력하면 경매 시 배당을 추정할 수 있어요."}
    if not price:
        return {"available": False, "note": "집값이 있어야 경매 시 배당을 추정할 수 있어요."}

    auction = inp.get("auction") or {}
    region = region_of(prop.get("address"))
    table = AUCTION_RATE_PCT["apartment" if housing == "apartment" else "other"]
    rate = _num(auction.get("ratePct")) or table.get(region, table["default"])
    sale = price * rate / 100
    pool = sale
    steps = []

    def pay(label, claim, note, mine=False):
        nonlocal pool
        paid = max(0.0, min(claim, pool))
        pool -= paid
        steps.append({"label": label, "claim10k": round(claim), "paid10k": round(paid), "note": note,
                      "isMine": mine, "known": True})
        return paid

    pay("경매 집행비용", sale * AUCTION_COST_PCT / 100, f"낙찰가의 약 {AUCTION_COST_PCT:g}% (가정)")

    small = SMALL_TENANT[region]
    my_priority = 0.0
    if deposit and deposit <= small["limit10k"]:
        claim = min(small["priority10k"], deposit, sale / 2)
        my_priority = pay("최우선변제 (내 보증금 일부)", claim,
                          f"{small['label']} 보증금 {money(small['limit10k'])} 이하 → {money(small['priority10k'])}까지 먼저",
                          mine=True)

    tax = (inp.get("landlord") or {}).get("taxArrears")
    if tax == "yes":
        steps.append({"label": "임대인 체납 세금 (당해세 등)", "claim10k": None, "paid10k": None,
                      "note": "금액을 몰라 계산에서 뺐어요. 내 확정일자보다 먼저 생긴 체납 세금은 내 순서보다 먼저 빠져나가요.",
                      "isMine": False, "known": False})

    pay("선순위 근저당", ltv["mortgage10k"], "등기부 을구 채권최고액 (내 확정일자보다 먼저 설정된 것)")
    prior = ltv["prior10k"]
    if housing == "multi" or prior:
        pay("선순위 임차보증금", prior, "나보다 먼저 전입·확정일자를 받은 세입자")
    rest = deposit - my_priority
    pay("내 보증금", rest, "전입신고 + 확정일자를 갖춘 다음 날부터 이 순서", mine=True)

    recovered = sum(s["paid10k"] or 0 for s in steps if s["isMine"])
    loss = max(0, round(deposit - recovered))
    unknown = [s["label"] for s in steps if not s["known"] and s["claim10k"] is not None]
    if tax not in {"yes", "no"}:
        unknown.append("임대인 체납 세금")
    return {
        "available": True,
        "ratePct": rate,
        "sale10k": round(sale),
        "steps": steps,
        "myRecovered10k": round(recovered),
        "myLoss10k": loss,
        "recoveryPct": round(recovered / deposit * 100, 1) if deposit else None,
        "isOptimistic": bool(unknown) or tax == "yes",
        "unknown": unknown,
        "region": small["label"],
        "basis": [SMALL_TENANT_BASIS, AUCTION_BASIS,
                  "배당 순서: 집행비용 → 최우선변제·최종 3개월 임금 → 당해세 → 확정일자·근저당 설정일 순 (주택임대차보호법 제3조의2·제8조)",
                  "당해세: 내 확정일자보다 법정기일이 늦은 당해세는 그 몫만큼 내 보증금이 먼저 받아요 (국세기본법 제35조 제7항, 2023.4.1~)"],
    }


# --- 3. 체크리스트 ↔ 서류 -----------------------------------------------------------

DOCUMENTS = [
    {"id": "registry", "title": "등기사항전부증명서 (등기부등본)", "where": "iros", "cost": "열람 700원 · 누구나",
     "consent": False, "request": "registryLatest", "items": [
         ("ownerMatches", "소유자가 계약 상대와 같은지", "갑구 › 소유자 성명"),
         ("trust", "신탁등기가 없는지", "갑구 › '신탁' 기재"),
         ("seizure", "압류·가압류·가처분이 없는지", "갑구"),
         ("auction", "경매개시결정이 없는지", "갑구"),
         ("recentOwnership", "최근 소유권 이전이 없는지", "갑구 › 접수 날짜"),
         ("mortgage", "근저당 채권최고액 합계", "을구 › 채권최고액"),
         ("leaseRegistration", "임차권등기가 없는지", "을구"),
         ("registryFresh", "열람일이 30일 이내인지", "발급 일시")]},
    {"id": "building", "title": "건축물대장", "where": "gov24", "cost": "온라인 열람·발급 무료",
     "consent": False, "request": None, "items": [
         ("use", "주용도가 주택(주거용)인지", "표제부·전유부 › 주용도"),
         ("violation", "위반건축물 표시가 없는지", "첫 장 상단 '위반건축물' 표기"),
         (None, "계약서 동·호수·면적과 같은지", "전유부 › 호명칭·면적")]},
    {"id": "price", "title": "공시가격 · 실거래가", "where": "realtyprice", "cost": "무료",
     "consent": False, "request": None, "extraLink": "rtmolit", "items": [
         ("hug126", "보증금이 공시가격의 126% 이하인지", "공동주택·개별주택 공시가격"),
         ("marketGap", "보증금이 주변 전세 시세와 비슷한지", "실거래가 공개시스템 › 전월세")]},
    {"id": "fixedDate", "title": "확정일자 부여현황", "where": "iros", "cost": "임대인 동의 필요",
     "consent": True, "request": "fixedDate", "items": [
         ("priorDeposits", "나보다 앞선 세입자 보증금 합계", "확정일자·차임·보증금 목록")]},
    {"id": "moveIn", "title": "전입세대확인서", "where": "gov24", "cost": "임대인 동의 또는 계약 후",
     "consent": True, "request": "moveIn", "items": [
         (None, "이미 전입한 세대가 있는지", "전입세대 목록")]},
    {"id": "tax", "title": "국세·지방세 납세증명서", "where": "hometax", "cost": "임대인이 발급해 제시",
     "consent": True, "request": "taxCert", "extraLink": "wetax", "items": [
         ("taxArrears", "체납 세금이 없는지", "납세증명서 › 체납 여부")]},
    {"id": "ownerId", "title": "임대인 신분증 · 위임장 · 인감증명서", "where": None, "cost": "계약 당일 대면 확인",
     "consent": True, "request": "ownerId", "items": [
         ("ownerMatches", "등기부 소유자 본인인지", "신분증 · 대리인이면 위임장과 인감증명서")]},
    {"id": "broker", "title": "중개사 등록·공제 확인 · 중개대상물 확인설명서", "where": "nsdi", "cost": "무료",
     "consent": False, "request": None, "items": [
         (None, "등록된 개업 공인중개사인지", "부동산중개업 조회 › 등록번호·상태"),
         (None, "공제증서(손해배상 보증)가 있는지", "중개사무소 게시 서류"),
         (None, "확인설명서에 권리관계·선순위가 적혔는지", "확인설명서 › 권리관계 칸")]},
    {"id": "guarantee", "title": "보증보험 가입 가능 여부 · 악성임대인 조회", "where": "khug", "cost": "무료",
     "consent": False, "request": "guarantee", "items": [
         ("guaranteeEligible", "반환보증 가입이 가능한지", "HUG·HF·SGI 상담 또는 안심전세앱"),
         (None, "임대인이 악성임대인 명단에 없는지", "안심전세포털 › 상습 채무불이행자 조회")]},
]


def documents(checks_by_id: dict, requests: list[dict]) -> list[dict]:
    req = {r["id"]: r for r in requests}
    out = []
    for doc in DOCUMENTS:
        items = []
        for check_id, text, where in doc["items"]:
            check = checks_by_id.get(check_id) if check_id else None
            items.append({
                "id": f"{doc['id']}.{check_id or len(items)}",
                "text": text,
                "where": where,
                "checkId": check_id,
                "result": check["result"] if check else None,
                "value": check["value"] if check else None,
            })
        results = [i["result"] for i in items if i["result"]]
        status = ("danger" if "danger" in results else "caution" if "caution" in results
                  else "unknown" if "unknown" in results or not results else "pass")
        links = [link(doc["where"])] if doc["where"] else []
        if doc.get("extraLink"):
            links.append(link(doc["extraLink"]))
        out.append({
            "id": doc["id"], "title": doc["title"], "cost": doc["cost"], "consent": doc["consent"],
            "links": links, "items": items, "status": status,
            "request": req.get(doc["request"]) if doc["request"] else None,
        })
    return out


# --- 4. 반환보증·지원 제도 ------------------------------------------------------------

def guarantees(inp: dict, ltv: dict, checks_by_id: dict) -> dict:
    prop = inp.get("property") or {}
    deposit = ltv["deposit10k"]
    hug = hug_limit(inp, ltv)
    blockers, unknowns = [], []
    if ltv.get("priorDepositPending"):
        unknowns.append("선순위 보증금")
    if deposit is None:
        unknowns.append("계약 보증금")
    if hug["base10k"] is None:
        unknowns.append("주택가격")
    if hug["max10k"] is not None and deposit > hug["max10k"]:
        blockers.append(f"보증금이 가입선 {money(hug['max10k'])}보다 {money(deposit - hug['max10k'])} 높아요")
    if hug["max10k"] is None and deposit is not None and deposit > hug["regionCap10k"]:
        blockers.append(f"보증금이 지역 한도 {money(hug['regionCap10k'])}를 넘어요")
    housing = prop.get("housingType") or "villa"
    if hug["base10k"]:
        senior = (ltv["mortgage10k"] or 0) + (ltv["prior10k"] or 0)
        limit = HUG_SENIOR_LIMIT["multi" if housing == "multi" else "default"]
        if hug["max10k"] is None and (deposit or 0) + senior > hug["base10k"] * HUG_RATIO:
            blockers.append("확인된 보증금과 근저당만으로 보증 한도를 넘어요")
        if senior > hug["base10k"] * limit:
            blockers.append(f"선순위채권이 주택가격의 {round(limit * 100)}%를 넘어요")
    for check_id, label in (("trust", "신탁등기"), ("seizure", "압류·가압류"), ("auction", "경매"),
                            ("leaseRegistration", "임차권등기"), ("use", "비주거 용도"), ("violation", "위반건축물")):
        if check_id == "violation" and housing == "apartment":
            continue  # HUG·SGI 모두 위반건축물 제한에서 아파트는 제외
        result = checks_by_id[check_id]["result"]
        if result in {"danger", "caution"}:
            blockers.append(f"{label} 있음")
        elif result == "unknown":
            unknowns.append(label)
    if checks_by_id["mortgage"]["result"] == "unknown":
        unknowns.append("근저당")
    status = "unlikely" if blockers else "check" if unknowns else "likely"
    status_label = {"likely": "가입 가능성 높음", "check": "확인 후 판단", "unlikely": "가입 어려움"}[status]

    products = [
        {"id": "hug", "name": "HUG 전세보증금반환보증", "status": status, "statusLabel": status_label,
         "summary": (f"보증금 한도 {money(hug['regionCap10k'])}, (보증금 + 선순위) ≤ 주택가격 90%, 선순위 ≤ 60% · "
                     "계약기간 절반 전까지 가입 · 2026.10.30부터 이사 전 사전한도심사"),
         "link": link("khugGuarantee")},
        {"id": "hf", "name": "HF 전세지킴보증", "status": "check", "statusLabel": "HF 대출 이용자만",
         "summary": "HF 전세자금보증으로 대출받은 경우에만 가입할 수 있어요. 보증료 연 0.04~0.18%.", "link": link("hf")},
        {"id": "sgi", "name": "SGI서울보증 전세금보장신용보험", "status": "check", "statusLabel": "상품 조건 확인",
         "summary": "공시가격 130%를 주택가격으로 인정, 신규 가입은 부채비율 90% 이하. 위반건축물은 불가(아파트 제외).", "link": link("sgi")},
    ]
    center = inp.get("center") or {}
    programs = [
        {"name": "HUG 안심전세앱 · 안심전세포털", "what": "시세·악성임대인 조회, 임대인 정보 동의 요청", "link": link("khug")},
        {"name": center.get("name") or "전세피해 및 예방지원센터",
         "what": (f"{center.get('address', '')} · {center.get('phone', '')} · {center.get('days', '')}".strip(" ·")
                  or "전국 8개소, 계약 전 안전계약 상담"),
         "link": {"label": "상담 예약", "url": center.get("reserveUrl") or LINKS["khug"][1]}},
        {"name": "반환보증 보증료 지원", "what": "보증금 3억 원 이하·소득 기준 충족 시 최대 40만 원 (청년·신혼부부 전액, 그 외 90%), 정부24 상시 신청",
         "link": link("gov24Fee")},
        {"name": "서울 주거안심종합센터 · 안심계약 도움", "what": "25개 구 센터 상담, 1인가구 계약 동행 · ☎ 1600-3456", "link": link("seoulHousing")},
    ]
    return {"status": status, "statusLabel": status_label, "blockers": blockers, "unknowns": unknowns,
            "hugMax10k": hug["max10k"], "hugBasis": hug["basis"], "products": products, "programs": programs,
            "region": "수도권" if is_capital(prop.get("address")) else "그 외 지역"}


# --- 5. 계약 후 관리 -----------------------------------------------------------------

def aftercare(inp: dict) -> dict:
    sched = inp.get("schedule") or {}
    contract = _date(sched.get("contractDate"))
    move_in = _date(sched.get("moveInDate"))
    end = _date(sched.get("endDate"))
    if move_in and not end:
        end = add_months(move_in, 24)  # 주택임대차 최단 존속기간 2년

    def item(key, when, title, detail, link_key=None, basis="", phase="after"):
        return {"id": key, "date": when.isoformat() if isinstance(when, date) else None,
                "when": when if isinstance(when, str) else None, "title": title, "detail": detail,
                "link": link(link_key) if link_key else None, "basis": basis, "phase": phase}

    items = [
        item("report30", (contract + timedelta(days=30)) if contract else "계약 후 30일 안",
             "주택 임대차 신고", "보증금 6천만 원 초과 또는 월세 30만 원 초과면 의무예요. 계약서를 첨부하면 확정일자가 자동으로 부여돼요 (미신고 과태료 2만~30만 원).",
             "rtms", "부동산거래신고법 제6조의2", "contract"),
        item("registryBalance", (move_in - timedelta(days=1)) if move_in else "잔금 전날·당일",
             "등기부 다시 열람", "그사이 근저당·압류·소유자 변경이 없는지 확인", "iros", phase="balance"),
        item("moveIn", move_in or "입주 당일", "전입신고 + 확정일자", "같은 날 받기. 대항력은 다음 날 0시부터 생겨요.",
             "gov24", "주택임대차보호법 제3조·제3조의2", "balance"),
        item("registryNext", (move_in + timedelta(days=1)) if move_in else "입주 다음 날",
             "등기부 한 번 더", "전입 당일 새 근저당이 잡히지 않았는지 확인", "iros", phase="balance"),
        item("guarantee", (move_in + timedelta(days=30)) if move_in else "입주 직후",
             "전세보증금 반환보증 가입", "계약기간 절반이 지나기 전에 가입해야 해요. HUG는 이사 전 사전한도심사도 받아요.", "khugGuarantee"),
        item("alert", move_in or "입주 직후", "등기 변동 알림 받기",
             "안심전세앱에서 등기를 열람(1,000원)하면 2년 6개월 동안 근저당·소유권 변동 알림을 무료로 받아요.", "khugApp"),
    ]
    if end:
        items += [
            item("renewOpen", add_months(end, -6), "갱신 요구·이사 통지 시작 (만료 6개월 전)",
                 "계약갱신요구권은 만료 6개월 전부터 2개월 전까지 쓸 수 있어요.", basis="주택임대차보호법 제6조의3"),
            item("renewClose", add_months(end, -2), "갱신 요구·통지 마감 (만료 2개월 전)",
                 "이 날이 지나면 같은 조건으로 묵시적 갱신될 수 있어요.", basis="주택임대차보호법 제6조"),
            item("end", end, "계약 만료 · 보증금 반환",
                 "반환이 늦어지면 임차권등기명령을 전자소송으로 직접 신청하세요(약 4~5만 원, 임대인에게 청구 가능). 보증 가입자는 보증 이행을 청구해요.",
                 "ecourt", "주택임대차보호법 제3조의3"),
        ]
    else:
        items.append(item("end", "만료일", "계약 만료 · 보증금 반환",
                          "만료일을 넣으면 갱신 요구 기간(6개월~2개월 전)을 계산해 드려요.", "ecourt"))
    items.append(item("victim", "보증금을 못 돌려받으면", "전세피해지원센터 상담 · 피해자 결정 신청",
                      "법률·금융·주거 지원을 받아요. 특별법 피해자 결정은 2025.5.31 이전 최초 계약·보증금 5억 원 이하가 대상이고 2027.5.31까지 신청해요.",
                      "khug", "전세사기피해자법", phase="trouble"))
    dated = sorted((i for i in items if i["date"]), key=lambda i: i["date"])
    undated = [i for i in items if not i["date"]]
    return {"hasDates": bool(contract or move_in or end), "items": dated + undated,
            "schedule": {"contractDate": contract.isoformat() if contract else None,
                         "moveInDate": move_in.isoformat() if move_in else None,
                         "endDate": end.isoformat() if end else None}}


def market_gap_check(inp: dict, deposit10k: float | None) -> tuple[str, str]:
    """(결과, 값 문구). 주변 전세 시세보다 10% 넘게 비싸면 주의."""
    market = inp.get("market") or {}
    compare = _num(market.get("jeonse10k")) or _num(market.get("surroundingJeonse10k"))
    if deposit10k is None:
        return "unknown", DEPOSIT_MISSING_LABEL
    if not compare or not deposit10k:
        return "unknown", "비교할 시세 없음"
    gap = round((deposit10k - compare) / compare * 100, 1)
    return ("caution" if gap > 10 else "pass"), f"시세 {money(compare)} 대비 {gap:+}%"


if __name__ == "__main__":
    ltv = {"deposit10k": 30000, "price10k": 40000, "mortgage10k": 8000, "prior10k": 0}
    inp = {"property": {"housingType": "villa", "address": "서울특별시 강서구 화곡동"},
           "price": {"official10k": 25000}, "market": {"jeonse10k": 26000}}
    g = deposit_guide(inp, ltv)
    assert g["lines"][0]["max10k"] == 20000 and g["lines"][0]["fits"] is False  # 4억×70% − 0.8억
    assert g["lines"][2]["max10k"] == 23500  # min(2.5억×1.4×0.9 − 0.8억, 7억)
    assert g["gapPct"] == 15.4
    r = repayment(inp, ltv)  # 서울 빌라 낙찰 3.08억(77%) → 비용 308 → 근저당 8,000 → 내 보증금 22,492/30,000
    assert r["sale10k"] == 30800 and r["myRecovered10k"] == 22492 and r["myLoss10k"] == 7508
    gs = guarantees({**inp}, ltv, {k: {"result": "pass"} for k in ("trust", "seizure", "auction", "leaseRegistration", "use", "violation", "mortgage")})
    assert gs["status"] == "unlikely"  # 보증금 3억 > 가입선 2.35억
    small = repayment({**inp, "property": {**inp["property"]}}, {**ltv, "deposit10k": 15000})
    assert small["steps"][1]["label"].startswith("최우선변제") and small["steps"][1]["paid10k"] == 5500
    a = aftercare({"schedule": {"contractDate": "2026-11-10", "moveInDate": "2026-12-20"}})
    ends = {i["id"]: i["date"] for i in a["items"]}
    assert ends["end"] == "2028-12-20" and ends["renewClose"] == "2028-10-20"
    print("jeonse_guide self-check OK")
