"""전세 안심 판정 엔진.

입력(집 정보, 등기부 값, 임대인 정보, 확인 요청 상태)을 받아 등급과 근거를 돌려준다.
K Car 진단 대시보드처럼 항목마다 "기준 · 이 집 값 · 결과 · 출처"를 남겨서,
등급이 어떤 근거로 나왔는지 화면에서 그대로 보여줄 수 있게 한다.

다가구의 선순위 보증금은 제출 서류에서 확인한 합계만 사용한다. 미확인이면 금액 판정을 보류한다.
기준선 근거:
- 70%: 주의 시작 (FitHome 자체 기준, 공식 기준 아님)
- 80%: 깡통전세 실무 경계 (법정 기준 아님)
- 90%: HUG 전세보증 한도 (보증금 + 선순위채권 ≤ HUG 인정 주택가격 × 90%). 입력한 집값과 HUG 인정가격은 다를 수 있다.
- 공시가격 × 140%: HUG가 공시가격 환산액을 먼저 쓰는 주택(연립·다세대·다가구 등)의 주택가격 산정 방식.
  이때 (보증금 + 선순위채권) 상한이 공시가격의 126%가 된다. 아파트·오피스텔은 시세가 먼저다.
"""

from __future__ import annotations

from datetime import date, datetime
from math import isfinite

from jeonse_guide import (
    DEPOSIT_MISSING_LABEL, MORTGAGE_PENDING_LABEL, PRIOR_PENDING_LABEL, aftercare, deposit_guide,
    documents, guarantees, market_gap_check, pending_senior_reason, repayment,
)

LINES = [
    # 70%는 공식 기준을 찾지 못한 FitHome 자체 주의선이다(전체 QA Sol V01).
    {"pct": 70, "label": "주의 시작", "basis": "FitHome 자체 기준(공식 기준 아님)"},
    {"pct": 80, "label": "깡통전세 경계", "basis": "실무 기준(법정 기준 아님)"},
    # HUG 한도는 HUG 인정 주택가격 기준이라, 입력한 집값으로 그린 이 선을 'HUG 한도'라고 단정하지 않는다(최종 재점검 Sol V06).
    {"pct": 90, "label": "90% 선", "basis": "HUG 반환보증 한도는 HUG 인정가격 × 90% − 선순위채권 (입력한 집값과 다를 수 있음)"},
]
OFFICIAL_TO_PRICE = 1.4  # HUG 공시가격 환산 방식(연립·다세대 등): 주택가격 = 공시가격 × 140%
HUG_DEPOSIT_CAP = 1.26  # 140% × 90%. (보증금 + 선순위채권) 기준이며 공시가격 환산 주택에만 맞다
STRESS_DROP = 0.10  # 집값 하락 가정. 판정에는 쓰지 않고 보여 주기만 한다.
RECENT_OWNERSHIP_DAYS = 90
REGISTRY_FRESH_DAYS = 30

HOUSING_LABELS = {"apartment": "아파트", "villa": "빌라·다세대", "multi": "다가구", "officetel": "오피스텔"}
SOURCE_LABELS = {
    "inspected": "핏홈 점검",
    "submitted": "제출 서류",
    "reviewedPdf": "사용자가 원문 대조",
    "trade": "실거래",
    "public": "공공데이터",
    "registry": "등기부",
    "registryUpload": "제출한 등기부 PDF",
    "input": "입력값",
    "estimate": "추정",
    "report": "제보",
    "request": "확인 요청",
    "none": "미확인",
}
AREA_LABELS = {"rights": "권리관계", "ratio": "가격·비율", "landlord": "임대인", "building": "건물", "reports": "제보"}
REQUEST_STATUS_LABELS = {
    "none": "요청 전",
    "requested": "요청함",
    "received": "받음",
    "refused": "거절",
    "noResponse": "무응답",
}


SECTIONS = ("property", "price", "registry", "landlord", "building", "requests", "inspection",
            "auction", "listing", "market", "schedule", "center")
MONEY_FIELDS = (
    ("deposit10k",), ("price", "value10k"), ("price", "official10k"),
    ("registry", "mortgageMax10k"), ("landlord", "priorDeposits10k"),
)
DATE_FIELDS = (("registry", "issuedAt"), ("registry", "lastOwnershipChange"))
# 화면(브라우저)이 주장할 수 있는 집값 출처. "핏홈 점검"은 시연용 예시에서만, "실거래"는 서버가 확인한 뒤에만 인정한다.
CLIENT_PRICE_SOURCES = {"input", "estimate", "trade", "public", "none"}
# 등기·임대인·건물 근거도 서버가 정한다. 화면은 '입력값'만 주장할 수 있고, 등기부 근거는 서버가 발급한
# 근거 번호로만 붙는다(evidence_store). 건물 출처 'public'은 서버가 준 건축HUB 값을 화면이 되돌려 보낸 것이다.
CLIENT_SECTION_SOURCES = {
    "registry": ("source", {"input", "none"}),
    "landlord": ("source", {"input", "none"}),
    "building": ("source", {"input", "public", "none"}),
}
SERVER_ONLY_FIELDS = (("registry", "mortgageSource"), ("registry", "dateSource"))
# 공시가격·전세 시세 출처. 'public'·'trade'는 서버(movevalue_api.verify_trade_price)가 단지 데이터와 맞을 때만 남긴다.
CLIENT_FIELD_SOURCES = (
    ("price", "officialSource", {"public", "estimate", "input", "none"}),
    ("market", "source", {"trade", "estimate", "input", "none"}),
)
# 위반 표시는 '있음'만 PDF에서 인정한다(build_checks). 화면이 위반을 주장해도 판정이 더 조심스러워질 뿐이다.
CLIENT_VIOLATION_SOURCES = {"input", "reviewedPdf"}
MAX_MONEY_10K = 10_000_000  # 1,000억원. 이보다 크면 단위를 잘못 넣은 것이다.


def validate_input(inp, today: date | None = None) -> dict:
    """요청 본문을 검사해 잘못된 값은 ValueError(→ 400)로 돌려보내고, 믿을 수 없는 출처는 낮춘다."""
    if not isinstance(inp, dict):
        raise ValueError("JSON 객체가 필요합니다.")
    today = today or date.today()
    scalar = (str, int, float, bool, type(None))
    for key in SECTIONS:
        if key in inp and inp[key] is not None and not isinstance(inp[key], dict):
            raise ValueError(f"{key}는 객체여야 합니다.")
        for field, value in (inp.get(key) or {}).items():
            if not isinstance(value, scalar):
                raise ValueError(f"{key}.{field}는 숫자나 글자여야 합니다.")
    for key in ("deposit10k", "key", "isDemo", "asOf", "feedbackCount"):
        if not isinstance(inp.get(key), scalar):
            raise ValueError(f"{key}는 숫자나 글자여야 합니다.")
    if "history" in inp and not isinstance(inp["history"], (list, type(None))):
        raise ValueError("history는 배열이어야 합니다.")
    for event in inp.get("history") or []:
        if not isinstance(event, dict) or not all(isinstance(v, scalar) for v in event.values()):
            raise ValueError("history 항목은 {date, kind, title, detail} 객체여야 합니다.")
    for path in MONEY_FIELDS:
        holder = inp if len(path) == 1 else (inp.get(path[0]) or {})
        value = holder.get(path[-1])
        if value in (None, ""):
            continue
        number = _num(value)
        label = ".".join(path)
        if number is None:
            raise ValueError(f"{label}는 숫자(만원 단위)여야 합니다.")
        if number < 0:
            raise ValueError(f"{label}는 0 이상이어야 합니다.")
        if number > MAX_MONEY_10K:
            raise ValueError(f"{label}가 너무 큽니다. 만원 단위인지 확인하세요.")
    # 주소만으로 연 리포트는 서류부터 확인할 수 있게 두고, 보증금이 없으면 금액 판정을 보류한다.
    if _num(inp.get("deposit10k")) == 0:
        raise ValueError("보증금(deposit10k, 만원)을 0보다 큰 값으로 입력해야 판정할 수 있습니다.")
    # 판정 기준일은 서버가 정한다. 화면이 과거 asOf를 보내 오래된 등기부를 '최신'으로 만들 수 있었다(Astra-03).
    # 시연용 예외도 두지 않는다. isDemo 문자열 "false"가 참으로 읽혀 과거 기준일이 통과했다(재점검 Astra-03).
    if "asOf" in inp:
        inp = {k: v for k, v in inp.items() if k != "asOf"}
    price = inp.get("price") or {}
    if _num(price.get("value10k")) == 0 and price.get("basis", "market") != "official":
        raise ValueError("집값(price.value10k)은 0보다 커야 합니다.")
    for section, key in DATE_FIELDS:
        raw = (inp.get(section) or {}).get(key)
        if raw in (None, ""):
            continue
        parsed = _date(raw)
        if parsed is None:
            raise ValueError(f"{section}.{key}는 YYYY-MM-DD 날짜여야 합니다.")
        if parsed > today:
            raise ValueError(f"{section}.{key}가 오늘({today.isoformat()})보다 뒤입니다.")
    downgraded = []
    source = price.get("source")
    if source is not None and source not in CLIENT_PRICE_SOURCES:
        if source == "inspected" and inp.get("isDemo") is True:
            pass
        else:
            inp = {**inp, "price": {**price, "source": "input"}}
            downgraded.append(f"{source}→input")
    for section, field in SERVER_ONLY_FIELDS:
        holder = inp.get(section) or {}
        if field in holder:
            downgraded.append(f"{section}.{field}:{holder[field]}→삭제")
            inp = {**inp, section: {k: v for k, v in holder.items() if k != field}}
    for section, (field, allowed) in CLIENT_SECTION_SOURCES.items():
        holder = inp.get(section) or {}
        claimed = holder.get(field)
        if claimed is not None and claimed not in allowed:
            downgraded.append(f"{section}.{field}:{claimed}→input")
            inp = {**inp, section: {**holder, field: "input"}}
        elif claimed is None and section == "registry" and holder:
            # 출처가 빠진 등기 값을 '등기부'로 표시하던 기본값을 막는다.
            inp = {**inp, section: {**holder, field: "input"}}
    for section, field, allowed in CLIENT_FIELD_SOURCES:
        holder = inp.get(section) or {}
        claimed = holder.get(field)
        if claimed is not None and claimed not in allowed:
            downgraded.append(f"{section}.{field}:{claimed}→input")
            inp = {**inp, section: {**holder, field: "input"}}
    building = inp.get("building") or {}
    violation_source = building.get("violationSource")
    if violation_source not in (None, *CLIENT_VIOLATION_SOURCES):
        downgraded.append(f"building.violationSource:{violation_source}→input")
        inp = {**inp, "building": {**building, "violationSource": "input"}}
    elif violation_source is None and building.get("violation") not in (None, "", "unknown"):
        # 위반 여부를 보냈는데 근거가 없으면 건물 출처('공공데이터')를 빌리지 않고 입력값으로 본다.
        inp = {**inp, "building": {**building, "violationSource": "input"}}
    if downgraded:
        inp = {**inp, "sourceDowngraded": ", ".join(downgraded)}
    return inp


def _num(value) -> float | None:
    if value in (None, "") or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if isfinite(number) else None  # "nan"·"inf"는 숫자로 보지 않는다


def _tri(value) -> str:
    return value if value in {"yes", "no"} else "unknown"


def _amount(value) -> float | None:
    amount = _num(value)
    return amount if amount is not None and amount >= 0 else None


def _date(value) -> date | None:
    if not value:
        return None
    try:
        return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def money(value_10k: float | None) -> str:
    if value_10k is None:
        return "미확인"
    amount = int(round(value_10k))
    sign = "-" if amount < 0 else ""
    amount = abs(amount)
    eok, man = divmod(amount, 10000)
    if eok and man:
        return f"{sign}{eok}억 {man:,}만원"
    if eok:
        return f"{sign}{eok}억원"
    return f"{sign}{man:,}만원"


def _check(area, check_id, label, standard, value, result, source, note=""):
    return {
        "id": check_id,
        "area": area,
        "areaLabel": AREA_LABELS[area],
        "label": label,
        "standard": standard,
        "value": value,
        "result": result,
        "source": source,
        "sourceLabel": SOURCE_LABELS.get(source, source),
        "note": note,
    }


def house_price(price: dict) -> tuple[float | None, str, str]:
    """(주택가격 만원, 산정 근거 문구, 출처)."""
    basis = price.get("basis") or "market"
    value = _amount(price.get("value10k"))
    official = _amount(price.get("official10k"))
    source = price.get("source") or "input"
    if basis == "official":
        if not official:
            return None, "공시가격 미입력", "none"
        return official * OFFICIAL_TO_PRICE, f"공시가격 {money(official)} × 140% (HUG 공시가격 환산 방식)", source
    if not value:
        return None, "집값 미입력", "none"
    label = {"market": "시세·감정가", "trade": "실거래가"}.get(basis, "시세")
    return value, f"{label} {money(value)}", source


def ltv_block(inp: dict, *, confirmed_prior_deposits10k=None, today: date | None = None) -> dict:
    today = today or date.today()
    housing = (inp.get("property") or {}).get("housingType") or "villa"
    deposit = _amount(inp.get("deposit10k"))
    price_input = inp.get("price") or {}
    price, price_label, price_source = house_price(price_input)
    market_basis = (price_input.get("basis") or "market") in {"market", "trade"}
    rent_ratio = round(deposit / price * 100, 1) if market_basis and price and price_source != "none" and deposit is not None else None
    registry = inp.get("registry") or {}
    landlord = inp.get("landlord") or {}
    mortgage = _amount(registry.get("mortgageMax10k"))
    mortgage_hold = ""
    # 근저당은 언제 열람한 등기부의 값인지 알아야 쓴다. 열람일이 없거나 30일을 넘으면 계산을 멈춘다.
    issued = _date(registry.get("issuedAt"))
    if mortgage is not None:
        if issued is None:
            mortgage, mortgage_hold = None, "등기부 열람일이 없어 근저당 금액을 반영하지 않았습니다. 열람일을 함께 입력해 주세요."
        elif not 0 <= (today - issued).days <= REGISTRY_FRESH_DAYS:
            mortgage, mortgage_hold = None, f"열람한 지 {REGISTRY_FRESH_DAYS}일이 넘은 등기부라 근저당 금액을 반영하지 않았습니다."
    if housing == "multi":
        # Only the caller that resolves submitted evidence can provide this value.
        prior = _amount(confirmed_prior_deposits10k)
    else:
        prior_value = landlord.get("priorDeposits10k")
        prior = 0.0 if prior_value in (None, "") else _amount(prior_value)
    pending = prior is None
    debt = None if pending or mortgage is None or deposit is None else mortgage + prior + deposit
    can_price = bool(price) and debt is not None
    ratio = round(debt / price * 100, 1) if can_price else None
    stress = round(debt / (price * (1 - STRESS_DROP)) * 100, 1) if can_price else None
    headroom = {
        str(line["pct"]): (round(price * line["pct"] / 100 - debt) if can_price else None) for line in LINES
    }
    return {
        "price10k": round(price) if price else None,
        "priceLabel": price_label,
        "priceSource": price_source,
        "priceSourceLabel": SOURCE_LABELS.get(price_source, price_source),
        "mortgage10k": mortgage,
        "mortgagePending": mortgage is None,
        "mortgageHoldReason": mortgage_hold,
        "rentToMarketPct": rent_ratio,
        "prior10k": prior,
        "priorDepositPending": pending,
        "deposit10k": deposit,
        "debt10k": round(debt) if debt is not None else None,
        "ratioPct": ratio,
        "stressDropPct": int(STRESS_DROP * 100),
        "stressRatioPct": stress,
        "isLowerBound": mortgage is None or pending,
        "lines": LINES,
        "headroom10k": headroom,
    }


def build_checks(inp: dict, ltv: dict, today: date) -> list[dict]:
    prop = inp.get("property") or {}
    housing = prop.get("housingType") or "villa"
    registry = inp.get("registry") or {}
    landlord = inp.get("landlord") or {}
    building = inp.get("building") or {}
    price = inp.get("price") or {}
    requests = inp.get("requests") or {}
    reg_source = registry.get("source") or "registry"
    land_source = landlord.get("source") or "input"
    bld_source = building.get("source") or "input"
    checks: list[dict] = []

    def tri_check(area, key, label, standard, present_result, src, note=""):
        state = _tri(registry.get(key) if area == "rights" else None)
        value = {"yes": "있음", "no": "없음", "unknown": "미확인"}[state]
        result = {"yes": present_result, "no": "pass", "unknown": "unknown"}[state]
        checks.append(_check(area, key, label, standard, value, result, src if state != "unknown" else "none", note))

    # 권리관계 (등기부 갑구·을구)
    tri_check("rights", "trust", "신탁등기", "갑구에 신탁등기가 없을 것", "danger", reg_source,
              "신탁된 집은 소유권이 신탁회사에 있어 임대인과의 계약이 무효가 될 수 있습니다.")
    tri_check("rights", "seizure", "압류·가압류", "갑구에 압류·가압류가 없을 것", "danger", reg_source)
    tri_check("rights", "auction", "경매개시결정", "경매개시결정 기록이 없을 것", "danger", reg_source)
    tri_check("rights", "leaseRegistration", "임차권등기", "을구에 임차권등기가 없을 것", "danger", reg_source,
              "앞선 세입자가 보증금을 돌려받지 못했다는 흔적입니다.")

    owner = _tri(registry.get("ownerMatches"))
    checks.append(_check(
        "rights", "ownerMatches", "소유자와 계약 상대", "등기부 소유자와 계약하는 임대인이 같을 것",
        {"yes": "일치", "no": "불일치", "unknown": "미확인"}[owner],
        {"yes": "pass", "no": "danger", "unknown": "unknown"}[owner],
        reg_source if owner != "unknown" else "none",
        "대리인과 계약하면 위임장·인감증명서를 확인해야 합니다." if owner != "yes" else "",
    ))

    changed = _date(registry.get("lastOwnershipChange"))
    if changed is None:
        checks.append(_check("rights", "recentOwnership", "최근 소유권 이전",
                             f"계약 전 {RECENT_OWNERSHIP_DAYS}일 안에 소유자가 바뀌지 않았을 것",
                             "미확인", "unknown", "none"))
    else:
        days = (today - changed).days
        recent = 0 <= days <= RECENT_OWNERSHIP_DAYS
        checks.append(_check(
            "rights", "recentOwnership", "최근 소유권 이전",
            f"계약 전 {RECENT_OWNERSHIP_DAYS}일 안에 소유자가 바뀌지 않았을 것",
            f"{changed.isoformat()} ({days}일 전)", "caution" if recent else "pass", reg_source,
            "새 집주인이 곧바로 전세를 놓는 것은 '바지 임대인' 수법과 겹칩니다." if recent else "",
        ))

    issued = _date(registry.get("issuedAt"))
    if issued is None:
        checks.append(_check("rights", "registryFresh", "등기부 열람일", f"열람 후 {REGISTRY_FRESH_DAYS}일 이내일 것",
                             "열람일 확인 필요" if registry.get("issuedAt") else "미열람", "unknown", "none"))
    else:
        age = (today - issued).days
        checks.append(_check(
            "rights", "registryFresh", "등기부 열람일", f"열람 후 {REGISTRY_FRESH_DAYS}일 이내일 것",
            f"{issued.isoformat()} ({age}일 전)" if age >= 0 else f"{issued.isoformat()} (미래 날짜)",
            "pass" if 0 <= age <= REGISTRY_FRESH_DAYS else "caution", registry.get("dateSource") or reg_source,
            "근저당은 언제든 새로 잡힐 수 있어 계약 직전과 잔금 직전에 다시 열람해야 합니다.",
        ))

    # 가격·비율
    ratio = ltv["ratioPct"]
    deposit = ltv["deposit10k"]
    pending_reason = pending_senior_reason(ltv)
    if pending_reason or deposit is None:
        price_value = ltv["price10k"]
        known_debt = (deposit or 0) + (ltv["mortgage10k"] or 0) + (ltv["prior10k"] or 0)
        already_excessive = price_value and known_debt > price_value * 0.90
        missing = pending_reason or DEPOSIT_MISSING_LABEL
        checks.append(_check("ratio", "ltv", "집값 대비 빚 비율(LTV)", "근저당·선순위 보증금·계약 보증금 확인 후 계산",
                             missing, "danger" if already_excessive else "unknown", "none",
                             "확인된 보증금과 근저당만으로 이미 90%를 초과합니다." if already_excessive else ""))
    elif ratio is None:
        checks.append(_check("ratio", "ltv", "집값 대비 빚 비율(LTV)", "근저당 + 선순위 보증금 + 내 보증금이 집값의 70% 미만일 것",
                             "집값 미입력", "unknown", "none"))
    else:
        result = "pass" if ratio < 70 else "caution" if ratio <= 90 else "danger"
        value = f"{ratio}%"
        checks.append(_check("ratio", "ltv", "집값 대비 빚 비율(LTV)",
                             "근저당 + 선순위 보증금 + 내 보증금이 집값의 70% 미만일 것",
                             value, result, ltv["priceSource"],
                             f"HUG 보증 한도는 HUG가 인정한 주택가격 × 90%에서 선순위채권을 뺀 금액입니다. 입력한 집값과 HUG 인정가격은 다를 수 있으니, 90% 근처라면 HUG에서 한도를 따로 확인하세요. 집값(매매가)이 {ltv['stressDropPct']}% 내리면 "
                             f"{ltv['stressRatioPct']}%가 됩니다(가정 계산)."))
    mortgage = ltv["mortgage10k"]
    checks.append(_check("ratio", "mortgage", "근저당 채권최고액", "등기부 을구의 근저당 합계를 확인할 것",
                         money(mortgage), "pass" if mortgage is not None else "unknown",
                         (registry.get("mortgageSource") or reg_source) if mortgage is not None else "none",
                         ltv["mortgageHoldReason"]))
    price_source = ltv["priceSource"]
    checks.append(_check("ratio", "priceBasis", "집값 근거", "집값이 확인된 값일 것(추정 아님)",
                         ltv["priceLabel"],
                         "unknown" if price_source == "none" else "caution" if price_source == "estimate" else "pass",
                         price_source))
    if housing not in {"apartment", "officetel"}:
        # 공시가격 환산 방식을 적용할 때는 선순위채권과 보증금을 함께 본다.
        standard = "보증금 + 선순위채권이 공시가격의 126% 이하일 것 (HUG 공시가격 환산 방식)"
        official = _amount(price.get("official10k"))
        if official and ltv["debt10k"] is not None:
            total = deposit + ltv["mortgage10k"] + ltv["prior10k"]
            over = total > official * HUG_DEPOSIT_CAP
            checks.append(_check("ratio", "hug126", "공시가격 대비 보증금", standard,
                                 f"{round(total / official * 100, 1)}%", "caution" if over else "pass",
                                 price.get("officialSource") or price_source,
                                 "넘으면 HUG 반환보증 한도를 넘어 가입이 어려울 수 있습니다(최종은 HUG 심사)." if over else ""))
        else:
            missing = DEPOSIT_MISSING_LABEL if deposit is None else pending_reason or "공시가격 미입력"
            checks.append(_check("ratio", "hug126", "공시가격 대비 보증금", standard, missing, "unknown", "none"))

    gap_result, gap_value = market_gap_check(inp, deposit)
    checks.append(_check("ratio", "marketGap", "시세 대비 보증금", "보증금이 주변 전세 시세보다 10% 넘게 비싸지 않을 것",
                         gap_value, gap_result, ((inp.get("market") or {}).get("source") or "none") if gap_result != "unknown" else "none",
                         "시세보다 비싼 전세는 집값이 떨어지면 바로 깡통전세가 됩니다." if gap_result == "caution" else ""))

    # 임대인
    if housing == "multi":
        prior = ltv["prior10k"]
        checks.append(_check("landlord", "priorDeposits", "선순위 보증금(다가구)",
                             "건물 전체에서 내 앞 순위 보증금 합계를 확인할 것",
                             money(prior), "pass" if prior is not None else "unknown",
                             "submitted" if prior is not None else "none",
                             "다가구는 한 등기부를 여러 세대가 나눠 써서, 나보다 먼저 대항요건·확정일자를 갖춘 세대의 보증금이 먼저 배당될 수 있습니다(소액임차인 최우선변제는 따로)."))
    else:
        prior_value = landlord.get("priorDeposits10k")
        prior = ltv["prior10k"]
        checks.append(_check("landlord", "priorDeposits", "선순위 보증금", "이 호실의 기존 임차인 보증금을 확인할 것",
                             "해당 없음(개별 등기)" if prior_value in (None, "") else money(prior),
                             "pass" if prior is not None else "unknown", land_source if prior is not None else "none"))
    tax = _tri(landlord.get("taxArrears"))
    checks.append(_check("landlord", "taxArrears", "임대인 세금 체납", "국세·지방세 체납이 없을 것",
                         {"yes": "체납 있음", "no": "체납 없음", "unknown": "미확인"}[tax],
                         {"yes": "danger", "no": "pass", "unknown": "unknown"}[tax],
                         land_source if tax != "unknown" else "none",
                         "법정기일이 내 확정일자보다 빠른 세금은 보증금보다 먼저 배당될 수 있습니다. 그 집에 붙는 당해세라도, 내가 대항요건을 갖추고 확정일자를 그 세금의 법정기일보다 먼저 받았다면 2023년 개정 특례로 그 세금에 배분될 금액 한도에서 보증금이 먼저 배분됩니다(선순위 저당권 몫은 그대로)."))
    guarantee = _tri(landlord.get("guaranteeEligible"))
    if (pending_reason or deposit is None) and guarantee == "yes":
        guarantee = "unknown"
    checks.append(_check("landlord", "guaranteeEligible", "전세보증보험 가입", "HUG 등 반환보증 가입이 가능할 것",
                         {"yes": "가능", "no": "불가", "unknown": "미확인"}[guarantee],
                         {"yes": "pass", "no": "caution", "unknown": "unknown"}[guarantee],
                         land_source if guarantee != "unknown" else "none"))
    refused = [REQUEST_TITLES[k] for k, v in requests.items() if v in {"refused", "noResponse"} and k in REQUEST_TITLES]
    checks.append(_check("landlord", "requestRefusals", "확인 요청 응답", "요청한 서류를 거절·무응답 없이 받을 것",
                         ", ".join(refused) + " 거절·무응답" if refused else "거절·무응답 없음",
                         "caution" if refused else "pass", "request",
                         "정당한 이유 없이 확인을 거부하면 그 자체가 위험 신호입니다." if refused else ""))

    # 건물
    use = building.get("use") or "unknown"
    checks.append(_check("building", "use", "건축물 용도", "건축물대장상 주거용일 것",
                         {"residential": "주거용", "nonresidential": "비주거(근린생활시설 등)", "unknown": "미확인"}.get(use, "미확인"),
                         {"residential": "pass", "nonresidential": "caution"}.get(use, "unknown"),
                         bld_source if use in {"residential", "nonresidential"} else "none",
                         building.get("ledgerNote")
                         or ("근린생활시설을 주택으로 개조한 집은 보증보험과 전세대출이 막힐 수 있습니다." if use == "nonresidential" else "")))
    violation = _tri(building.get("violation"))
    violation_source = building.get("violationSource") or bld_source
    # The PDF reader can identify an explicit violation; absence of that mark cannot confirm a clean building.
    if violation_source == "reviewedPdf" and violation != "yes":
        violation = "unknown"
    checks.append(_check("building", "violation", "위반건축물", "건축물대장에 위반건축물 표시가 없을 것",
                         {"yes": "위반건축물", "no": "해당 없음", "unknown": "미확인"}[violation],
                         {"yes": "caution", "no": "pass", "unknown": "unknown"}[violation],
                         violation_source if violation != "unknown" else "none"))

    # 제보
    reports = int(_num(inp.get("feedbackCount")) or 0)
    checks.append(_check("reports", "feedback", "미검증 문제 제보", "확인되지 않은 문제 제보가 없을 것",
                         f"{reports}건" if reports else "없음", "caution" if reports else "pass",
                         "report" if reports else "input",
                         "핏홈이 확인하기 전까지는 사실 여부가 정해지지 않은 제보입니다." if reports else ""))
    return checks


REQUEST_TITLES = {
    "fixedDate": "확정일자 부여현황",
    "taxCert": "국세·지방세 납세증명서",
    "moveIn": "전입세대확인서",
    "registryLatest": "최신 등기부등본",
    "guarantee": "보증보험 가입 가능 여부",
    "ownerId": "임대인 신분증·위임장",
}


def build_requests(inp: dict, checks_by_id: dict) -> list[dict]:
    housing = (inp.get("property") or {}).get("housingType") or "villa"
    status = inp.get("requests") or {}
    address = (inp.get("property") or {}).get("address") or "해당 주택"
    items = []

    def add(key, to, why, legal, needed):
        if not needed and status.get(key, "none") == "none":
            return
        items.append({
            "id": key,
            "title": REQUEST_TITLES[key],
            "to": to,
            "why": why,
            "legal": legal,
            "status": status.get(key, "none"),
            "statusLabel": REQUEST_STATUS_LABELS.get(status.get(key, "none"), "요청 전"),
            "template": (
                f"안녕하세요. {address} 전세 계약을 검토 중인 임차인입니다. "
                f"계약 전 확인을 위해 {REQUEST_TITLES[key]}을(를) 보여주시거나 열람에 동의해 주실 수 있을까요? "
                f"근거: {legal}. 확인이 어려우시면 사유를 알려주세요."
            ),
        })

    add("fixedDate", "임대인·중개사", "내 앞 순위 세입자의 보증금 규모를 확인합니다.",
        "주택임대차보호법 제3조의7(임대인 정보 제시 의무)",
        housing == "multi" or checks_by_id["priorDeposits"]["result"] == "unknown")
    add("taxCert", "임대인", "체납 세금이 내 보증금보다 먼저 배당되는지 확인합니다.",
        "주택임대차보호법 제3조의7(정보 제시), 국세징수법 제108조·지방세징수법 제5조(납세증명서)",
        checks_by_id["taxArrears"]["result"] == "unknown")
    add("moveIn", "임대인·중개사", "이미 전입한 세대가 있는지 확인합니다.",
        "주민등록법 제29조의2(전입세대확인서). 계약 전에는 소유자 위임·협조가 필요하고, 계약 후 임차인은 직접 신청할 수 있습니다", housing == "multi")
    add("registryLatest", "직접 열람(인터넷등기소, 1,100원)", "그사이 근저당·압류가 새로 잡혔는지 확인합니다.",
        "부동산등기법 제19조(누구나 열람 가능)",
        checks_by_id["registryFresh"]["result"] in {"unknown", "caution"})
    add("guarantee", "HUG·중개사", "보증보험 가입이 가능해야 보증금을 돌려받을 안전판이 생깁니다.",
        "HUG 전세보증금반환보증 가입 요건", checks_by_id["guaranteeEligible"]["result"] == "unknown")
    add("ownerId", "임대인", "계약 상대가 실제 소유자인지 확인합니다.",
        "대리 계약 시 위임장·인감증명서 확인(실무 권고)", checks_by_id["ownerMatches"]["result"] != "pass")
    return items


def build_stages(checks_by_id: dict, ltv: dict) -> list[dict]:
    mortgage = ltv.get("mortgage10k") or 0
    trust = checks_by_id["trust"]["result"] == "danger"
    return [
        {"id": "beforeDeposit", "label": "가계약금 보내기 전", "items": [
            {"id": "registry", "text": "등기부를 직접 열람해 소유자·근저당·신탁·압류 확인"},
            {"id": "ltv", "text": "집값 대비 빚 비율이 70% 미만인지 확인"},
            {"id": "requests", "text": "확인 요청 서류(확정일자 부여현황·납세증명서) 받기"},
            # B010: 판결로 확인된 동시진행·명의 이전 구조와 단속에서 드러난 무등록 중개에 대응하는 질문
            {"id": "concurrentSale", "text": "매매와 전세를 동시에 진행하는지, 계약 뒤 소유자가 바뀔 계획이 있는지 묻고 답을 기록하기"},
            {"id": "roles", "text": "분양 담당·등기부 소유자·중개 담당자가 누구인지, 상담한 사람이 계약서의 중개사와 같은지 확인하기"},
            *([{"id": "trustDoc", "text": "신탁원부와 신탁회사 동의서 확인 (없으면 계약하지 않기)"}] if trust else []),
        ]},
        {"id": "contractDay", "label": "계약 당일", "items": [
            {"id": "owner", "text": "신분증으로 등기부 소유자 본인인지 확인, 대리인이면 위임장·인감증명서"},
            {"id": "account", "text": "계약금은 등기부 소유자 명의 계좌로만 이체"},
            {"id": "clauses", "text": "추천 특약을 계약서에 넣기"},
        ]},
        {"id": "beforeBalance", "label": "잔금 직전", "items": [
            {"id": "registryAgain", "text": "등기부 다시 열람 — 그사이 새 근저당·소유권 이전이 없는지"},
            *([{"id": "release", "text": f"근저당({money(mortgage)}) 말소 접수 확인"}] if mortgage else []),
            {"id": "guarantee", "text": "보증보험 가입 가능 여부·사전 한도 확인 (본심사·가입은 입주·전입신고 뒤)"},
        ]},
        {"id": "moveInDay", "label": "전입 당일", "items": [
            {"id": "moveIn", "text": "이사(주택 인도)와 전입신고를 마치고 확정일자도 받기. 대항력은 인도·전입을 모두 마친 다음 날 0시부터, 우선변제는 확정일자까지 갖춰야 생깁니다"},
            {"id": "registryNextDay", "text": "다음 날 등기부를 한 번 더 열람해 당일 새 근저당이 없는지 확인"},
        ]},
    ]


def build_clauses(inp: dict, checks_by_id: dict, ltv: dict) -> list[dict]:
    housing = (inp.get("property") or {}).get("housingType") or "villa"
    clauses = [
        {"title": "권리 변동 금지",
         "text": "임대인은 임차인의 전입신고 예정일 다음 날까지 근저당권 등 담보권을 설정하지 않으며, 소유권 이전 등 임차인의 권리를 해치는 행위를 하지 않는다. 위반 시 임차인은 계약을 해제할 수 있으며 임대인은 받은 금액 전부를 즉시 반환한다.",
         "reason": "대항력은 주택 인도와 전입신고를 마친 다음 날 0시에 생기지만, 근저당은 등기가 완료되면 접수한 때부터 효력이 생깁니다.",
         "basis": "주택임대차표준계약서 권고 특약(전입신고 다음 날까지 담보권 설정 금지). 소유권 이전 금지는 FitHome 추가 예시"},
        {"title": "제시 정보와 다를 때 해제",
         "text": "임대인이 제시한 선순위 보증금·체납 정보가 사실과 다른 경우 임차인은 계약을 해제할 수 있고, 임대인은 받은 금액 전부를 반환한다.",
         "reason": "제시받은 정보가 사실과 다를 때 계약을 풀 수 있도록 특약으로 정해 둡니다.", "basis": "주택임대차표준계약서(2023) 권고 특약"},
    ]
    if (ltv.get("mortgage10k") or 0) > 0:
        clauses.append({"title": "근저당 말소",
                        "text": f"임대인은 잔금 지급과 동시에 등기부 을구의 근저당권(채권최고액 {money(ltv['mortgage10k'])})을 말소 신청하고, 말소 접수증을 임차인에게 교부한다.",
                        "reason": "내 대항요건·확정일자보다 먼저 등기된 근저당이 남아 있으면 경매 때 내 보증금보다 먼저 배당됩니다(소액임차인 최우선변제 보호액은 예외). 말소 신청 뒤 실제로 말소됐는지도 등기부로 확인하세요.", "basis": "실무 권고(당사자 합의 특약)"})
    if checks_by_id["guaranteeEligible"]["result"] != "pass":
        clauses.append({"title": "보증보험 가입 불가 시 해제",
                        "text": "임차인이 전세보증금반환보증에 가입할 수 없는 경우 계약을 해제할 수 있으며, 임대인은 받은 금액 전부를 반환한다.",
                        "reason": "보증보험이 안 되면 반환보증이라는 안전판을 쓸 수 없습니다(대항력·우선변제권은 법정 요건대로 남습니다). 가입 불가만으로 법률상 해제권이 생기지는 않아 특약으로 정합니다.", "basis": "실무 권고(표준계약서 공식 조항 아님)"})
    if housing == "multi":
        clauses.append({"title": "선순위 보증금 고지",
                        "text": "임대인은 계약일 현재 이 건물의 선순위 임대차보증금 총액을 고지하며, 고지 금액과 다른 사실이 확인되면 임차인은 계약을 해제할 수 있다.",
                        "reason": "다가구는 나보다 먼저 대항요건·확정일자를 갖춘 세대의 보증금이 먼저 배당될 수 있습니다.", "basis": "실무 권고(당사자 합의 특약)"})
    return clauses


def history_summary(events: list[dict]) -> dict:
    owners = [e for e in events if e.get("kind") == "ownership"]
    mortgages = [e for e in events if e.get("kind") in {"mortgage", "mortgageRelease"}]
    cautions = [e for e in events if e.get("kind") in {"trust", "seizure", "auction", "leaseRegistration", "report"}]
    last_owner = max((e.get("date", "") for e in owners), default="")
    return {
        "ownershipChanges": len(owners),
        "lastOwnershipChange": last_owner or None,
        "mortgageEvents": len(mortgages),
        "cautionEvents": [e.get("title") for e in cautions],
    }


def evaluate(inp: dict, today: date | None = None, *, confirmed_prior_deposits10k=None) -> dict:
    today = today or _date(inp.get("asOf")) or date.today()
    ltv = ltv_block(inp, confirmed_prior_deposits10k=confirmed_prior_deposits10k, today=today)
    checks = build_checks(inp, ltv, today)
    by_id = {c["id"]: c for c in checks}
    counts = {k: sum(1 for c in checks if c["result"] == k) for k in ("pass", "caution", "danger", "unknown")}
    if counts["danger"]:
        grade = "danger"
    elif counts["caution"] or counts["unknown"]:
        grade = "caution"
    else:
        grade = "safe"
    order = {"danger": 0, "caution": 1, "unknown": 2, "pass": 3}
    reasons = [c for c in sorted(checks, key=lambda c: order[c["result"]]) if c["result"] != "pass"][:3]

    headline = {
        "safe": "확인한 범위에서 핵심 위험 신호가 없습니다",
        "caution": f"계약 전에 확인할 항목이 {counts['caution'] + counts['unknown']}개 남았습니다",
        "danger": f"이 상태로는 계약하지 마세요 — {reasons[0]['label'] if reasons else ''}",
    }[grade]

    tags = []
    if ltv["priorDepositPending"]:
        tags.append(PRIOR_PENDING_LABEL)
        if grade == "caution" and (inp.get("property") or {}).get("housingType") == "multi":
            headline = "선순위 보증금 미확인 · 집주인이 제출한 서류에서 합계를 확인해야 합니다."
    if ltv["mortgagePending"]:
        tags.append(MORTGAGE_PENDING_LABEL)
    if ltv["deposit10k"] is None:
        tags.append(DEPOSIT_MISSING_LABEL)
    if ltv["ratioPct"] is not None:
        tags.append(f"LTV {ltv['ratioPct']}%")
    head80 = ltv["headroom10k"]["80"]
    if head80 is not None:
        tags.append(f"근저당 여유 {money(head80)}" if head80 > 0 else "80% 기준 초과")
    for key, label in (("trust", "신탁"), ("seizure", "압류"), ("leaseRegistration", "임차권등기")):
        c = by_id[key]
        tags.append(f"{label} {c['value']}")
    tags.append(f"보증보험 {by_id['guaranteeEligible']['value']}")

    events = sorted(inp.get("history") or [], key=lambda e: e.get("date", ""), reverse=True)
    prop = inp.get("property") or {}
    requests = build_requests(inp, by_id)
    return {
        "ok": True,
        "key": inp.get("key"),
        "isDemo": bool(inp.get("isDemo")),
        "property": {**prop, "housingLabel": HOUSING_LABELS.get(prop.get("housingType"), "주택")},
        "asOf": today.isoformat(),
        "grade": grade,
        "gradeLabel": {"safe": "안심", "caution": "주의", "danger": "위험"}[grade],
        "headline": headline,
        "tags": tags,
        "reasons": reasons,
        "ltv": ltv,
        "checks": checks,
        "counts": counts,
        "rights": [c for c in checks if c["area"] == "rights"],
        "requests": requests,
        "stages": build_stages(by_id, ltv),
        "clauses": build_clauses(inp, by_id, ltv),
        "history": events,
        "historySummary": history_summary(events),
        "depositGuide": deposit_guide(inp, ltv),
        "repayment": repayment(inp, ltv),
        "documents": documents(by_id, requests),
        "guarantees": guarantees(inp, ltv, by_id),
        "aftercare": aftercare(inp),
        "inspection": inp.get("inspection") or {"status": "none"},
        "notice": "판정은 법적 판정이 아니며 입력값과 공개 정보에 근거합니다. 특약 문구는 참고용이므로 계약 전 전문가 검토를 권장합니다.",
    }


if __name__ == "__main__":
    today = date(2026, 10, 30)
    clean = {
        "property": {"housingType": "apartment", "address": "서울 예시구"},
        "deposit10k": 42000,
        "price": {"basis": "market", "value10k": 90000, "official10k": 63000, "source": "input"},
        "registry": {"source": "registry", "issuedAt": "2026-10-28", "mortgageMax10k": 12000, "trust": "no",
                     "seizure": "no", "auction": "no", "leaseRegistration": "no", "ownerMatches": "yes",
                     "lastOwnershipChange": "2019-05-02"},
        "landlord": {"taxArrears": "no", "guaranteeEligible": "yes"},
        "building": {"use": "residential", "violation": "no"},
        "market": {"jeonse10k": 41000, "source": "trade"},
    }
    r = evaluate(clean, today)
    assert r["grade"] == "safe", r["reasons"]
    assert r["ltv"]["ratioPct"] == 60.0 and not r["ltv"]["isLowerBound"]
    assert r["ltv"]["stressRatioPct"] == 66.7  # 5.4억 / (9억 × 0.9)
    assert r["ltv"]["headroom10k"]["80"] == 18000  # 9억 × 80% − 5.4억

    trust = {**clean, "registry": {**clean["registry"], "trust": "yes"}}
    assert evaluate(trust, today)["grade"] == "danger"

    unknown = {**clean, "registry": {**clean["registry"], "mortgageMax10k": None}}
    r = evaluate(unknown, today)
    assert r["grade"] == "caution" and r["ltv"]["isLowerBound"]

    # 입력 검증: 잘못된 값은 ValueError(→ 400), 믿을 수 없는 출처는 낮춘다.
    def rejects(payload) -> bool:
        try:
            validate_input(payload, today)
        except ValueError:
            return True
        return False

    assert rejects([]) and rejects({"property": "x"}) and rejects({"requests": "x"}) and rejects({"history": "x"})
    assert rejects({**clean, "deposit10k": -50000})
    for started in ({k: v for k, v in clean.items() if k != "deposit10k"}, {**clean, "deposit10k": None}):
        held = evaluate(validate_input(started, today), today)
        assert held["ltv"]["ratioPct"] is None and held["ltv"]["stressRatioPct"] is None
    assert rejects({**clean, "deposit10k": 0})
    assert "asOf" not in validate_input({**clean, "asOf": "2019-01-01"}, today)
    assert rejects({**clean, "price": {**clean["price"], "value10k": -1}})
    assert rejects({**clean, "price": {**clean["price"], "value10k": 0}})
    assert rejects({**clean, "registry": {**clean["registry"], "mortgageMax10k": "abc"}})
    assert rejects({**clean, "registry": {**clean["registry"], "issuedAt": "2027-01-01"}})
    assert rejects({**clean, "registry": {**clean["registry"], "lastOwnershipChange": "어제"}})
    assert rejects({**clean, "deposit10k": "nan"}) and rejects({**clean, "deposit10k": "inf"}) and rejects({**clean, "deposit10k": [1]})
    assert rejects({**clean, "price": {**clean["price"], "source": ["trade"]}})
    assert rejects({**clean, "building": {"use": ["residential"]}}) and rejects({**clean, "history": [1]})
    assert not rejects(clean)
    spoofed = validate_input({**clean, "price": {**clean["price"], "source": "inspected"}}, today)
    assert spoofed["price"]["source"] == "input" and evaluate(spoofed, today)["ltv"]["priceSource"] == "input"
    assert validate_input({**clean, "isDemo": True, "price": {**clean["price"], "source": "inspected"}}, today)["price"]["source"] == "inspected"

    over = {**clean, "deposit10k": 72000}  # (1.2억 + 7.2억) / 9억 = 93.3%
    assert evaluate(over, today)["grade"] == "danger"

    recent = {**clean, "registry": {**clean["registry"], "lastOwnershipChange": "2026-09-15"}}
    assert evaluate(recent, today)["grade"] == "caution"

    refused = {**clean, "requests": {"taxCert": "refused"}}
    r = evaluate(refused, today)
    assert r["grade"] == "caution" and any(q["status"] == "refused" for q in r["requests"])

    villa = {**clean, "property": {"housingType": "villa"}, "deposit10k": 20000,
             "price": {"basis": "official", "official10k": 15000, "source": "input"},
             "registry": {**clean["registry"], "mortgageMax10k": 0}}
    r = evaluate(villa, today)  # 2억 / (1.5억 × 140%) = 95.2% → 위험, 공시가 126% 초과 → 주의 항목 포함
    assert r["grade"] == "danger" and r["ltv"]["price10k"] == 21000
    assert any(c["id"] == "hug126" and c["result"] == "caution" for c in r["checks"])

    pricey = {**clean, "deposit10k": 47000}  # 시세 4.1억보다 14.6% 비쌈
    assert any(c["id"] == "marketGap" and c["result"] == "caution" for c in evaluate(pricey, today)["checks"])

    multi = {**clean, "property": {"housingType": "multi"}}
    r = evaluate(multi, today)
    assert r["grade"] == "caution" and r["ltv"]["isLowerBound"]
    assert any(q["id"] == "fixedDate" for q in r["requests"])
    print("jeonse_verdict self-check OK")
