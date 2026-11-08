#!/usr/bin/env python3
"""보증금 반환 순위(경매 배당 순서) 이해용 계산기.

법적 배당표가 아니다. 집이 경매로 넘어갈 때 "내 보증금 앞에 누가 얼마나 있는가"와
"보증금을 다 돌려받으려면 최소 얼마에 팔려야 하는가"를 보여 주는 계산이다.
경매 비용, 체납 세금액, 임금채권, 배당요구 여부, 같은 날 경합은 알 수 없으므로 '확인 필요'로 남긴다.
낙찰가율 같은 가정은 넣지 않는다.

근거 (팀 위키 verified 노트, 2026-11-08 Sol 조사 + Sonnet 교차 검증)
- 대항력: 주택 인도 + 주민등록 → 다음 날부터 (주택임대차보호법 제3조제1항)
- 우선변제: 대항요건 + 확정일자 → 둘 중 늦은 날 기준으로 담보권 등기일과 선후 비교 (제3조의2제2항)
- 소액임차인 최우선변제: 경매신청 등기 전 대항요건, 지역별 보증금 상한·보호액, 주택가액 1/2 한도 (제8조, 시행령 제10·11조)
  금액은 2023-02-21 시행분. 그 전에 설정된 담보권과의 관계에는 종전 기준이 적용된다.
- 당해세 특례: 대항요건과 확정일자를 갖춘 임차인의 보증금은, 확정일자보다 법정기일이 늦은 그 집의 당해세
  (국세: 상속세·증여세·종합부동산세, 국세기본법 제35조제7항, 2023-04-01 이후 매각결정·매각허가결정분 /
   지방세: 재산세·소방분 지역자원시설세·재산세에 붙는 지방교육세, 지방세기본법 제71조제6항, 2023-05-04 이후분)에
  배분될 금액 한도에서 그 징수 순서를 대신한다. 선순위 저당권자 몫에는 영향이 없다.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

# 주택임대차보호법 시행령 제10조(보호액)·제11조(보증금 상한), 2023-02-21 시행. 단위: 만원
SMALL_TENANT = {
    "seoul": {"label": "서울특별시", "cap": 16500, "protected": 5500},
    "overcrowded": {"label": "과밀억제권역(서울 제외)·세종·용인·화성·김포", "cap": 14500, "protected": 4800},
    "metro": {"label": "광역시(과밀억제권역·군 제외)·안산·광주·파주·이천·평택", "cap": 8500, "protected": 2800},
    "other": {"label": "그 밖의 지역", "cap": 7500, "protected": 2500},
}
SMALL_TENANT_SINCE = date(2023, 2, 21)
SOURCES = [
    {"title": "주택임대차보호법 제3조(대항력)", "url": "https://www.law.go.kr/법령/주택임대차보호법/제3조"},
    {"title": "주택임대차보호법 제3조의2(우선변제)", "url": "https://www.law.go.kr/법령/주택임대차보호법/제3조의2"},
    {"title": "주택임대차보호법 제8조(소액보증금)", "url": "https://www.law.go.kr/법령/주택임대차보호법/제8조"},
    {"title": "시행령 제10·11조(지역별 금액)", "url": "https://www.law.go.kr/lsLinkCommonInfo.do?chrClsCd=010202&lspttninfSeq=130113"},
    {"title": "국세기본법 제35조(당해세 특례)", "url": "https://www.law.go.kr/LSW/lsSideInfoP.do?lsiSeq=289999&joNo=0035&joBrNo=00&docCls=jo&urlMode=lsScJoRltInfoR"},
]


def _date(value) -> date | None:
    if isinstance(value, date):
        return value
    try:
        return datetime.strptime(str(value or "")[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def money(value_10k: float | None) -> str:
    if value_10k is None:
        return "미확인"
    amount = int(round(value_10k))
    eok, man = divmod(amount, 10000)
    if eok and man:
        return f"{eok}억 {man:,}만원"
    return f"{eok}억원" if eok else f"{man:,}만원"


def region_from_address(address: str) -> str | None:
    """서울만 주소로 확정한다. 다른 지역은 과밀억제권역 여부가 시·군마다 달라 사용자에게 묻는다."""
    return "seoul" if str(address or "").startswith(("서울", "서울특별시")) else None


def repayment_priority(
    deposit10k: float,
    house_price10k: float | None = None,
    region: str | None = None,
    move_in_date=None,
    fixed_date=None,
    mortgages: list[dict] | None = None,
    prior_tenants10k: float | None = None,
    tax_arrears: str = "unknown",
    today: date | None = None,
    mortgage_status: str = "auto",
) -> dict:
    """mortgage_status: 'none'(등기부에 근저당 없음 확인) | 'known'(mortgages에 금액이 있음) | 'unknown'(모름).
    'auto'면 mortgages가 있으면 known, 없으면 unknown이다. 근저당을 모르는데 '없음'으로 계산하면 보호액과 최소 매각가를
    확정해 버린다(전체 QA Astra-05).
    """
    if deposit10k is None or deposit10k <= 0:
        raise ValueError("보증금(만원)이 필요합니다.")
    if house_price10k is not None and house_price10k <= 0:
        raise ValueError("집값은 0보다 커야 합니다.")
    today = today or date.today()
    move_in = _date(move_in_date)
    fixed = _date(fixed_date)
    if any(d and d.year > today.year + 5 for d in (move_in, fixed)):
        raise ValueError("전입일·확정일자가 너무 먼 미래입니다. 날짜를 확인하세요.")
    opposable = move_in + timedelta(days=1) if move_in else None
    my_date = max(opposable, fixed) if opposable and fixed else None
    unknowns: list[str] = []
    if not move_in:
        unknowns.append("전입(주택 인도+주민등록) 날짜 — 대항력은 다음 날 0시부터")
    if not fixed:
        unknowns.append("확정일자 받은 날")

    claims: list[dict] = []

    # 1) 소액임차인 최우선변제
    rule = SMALL_TENANT.get(region or "")
    small = {"eligible": None, "protected10k": None, "note": ""}
    mortgage_dates = [_date(m.get("registered")) for m in mortgages or []]
    old_mortgage = any(d and d < SMALL_TENANT_SINCE for d in mortgage_dates)
    # 등기일을 모르는 근저당은 2023-02-21 전 것일 수 있다. 현행 금액을 단정하지 않는다(리뷰 2026-11-08).
    undated_mortgage = any(d is None for d in mortgage_dates)
    amounts_unknown = any(m.get("amount10k") in (None, "") for m in mortgages or [])
    if mortgage_status == "auto":
        mortgage_status = "known" if mortgages else "unknown"
    mortgage_unknown = mortgage_status == "unknown" or amounts_unknown
    if mortgage_unknown:
        unknowns.append("근저당 유무·금액·등기일(등기부 을구)")
    if rule is None:
        small["note"] = "지역을 알아야 소액임차인 해당 여부를 판단할 수 있습니다(서울 외 지역은 과밀억제권역 여부 확인)."
        unknowns.append("주택 소재 지역 구분")
    elif deposit10k > rule["cap"]:
        small.update(eligible=False, note=f"{rule['label']} 소액임차인 보증금 상한 {money(rule['cap'])}을 넘어 최우선변제 대상이 아닙니다.")
    elif old_mortgage:
        small.update(eligible=None, note=(
            f"2023-02-21 전에 설정된 근저당이 있어 그 근저당과의 관계에는 종전 기준이 적용됩니다. "
            "종전 금액은 확인된 자료가 없어 계산하지 않았습니다."))
        unknowns.append("종전 소액임차인 기준 금액")
    elif mortgage_status == "unknown":
        small.update(eligible=None, note=(
            f"보증금은 {rule['label']} 소액임차인 상한({money(rule['cap'])} 이하, 보호액 최대 {money(rule['protected'])}) 안이지만, 근저당이 있는지·언제 설정됐는지 몰라 적용 기준(현행·종전)과 "
            "보호액을 정할 수 없습니다. 등기부 을구를 확인해 근저당 금액과 접수일을 넣어 주세요."))
    elif undated_mortgage:
        small.update(eligible=None, note=(
            f"보증금은 {rule['label']} 소액임차인 상한({money(rule['cap'])} 이하, 보호액 최대 {money(rule['protected'])}) 안이지만, 근저당 등기일을 몰라 어느 기준(현행·종전)이 적용되는지 "
            "정할 수 없습니다. 등기부 을구에서 근저당 접수일을 확인하세요."))
        unknowns.append("근저당 등기일")
    else:
        half_cap = house_price10k / 2 if house_price10k else None
        protected = min(rule["protected"], deposit10k, half_cap if half_cap is not None else deposit10k)
        small.update(eligible=True, protected10k=protected, note=(
            f"{rule['label']} 기준(보증금 {money(rule['cap'])} 이하) 소액임차인입니다. 최대 {money(protected)}까지 근저당보다 먼저 받을 수 있습니다. "
            "단, 경매신청 등기 전에 전입·점유를 갖춰야 하고, 소액임차인 전체 보호액은 주택가액의 1/2을 넘지 못해 다른 소액임차인이 있으면 줄어듭니다."
            + (f" (이 집의 1/2 한도: {money(half_cap)})" if half_cap else "")))
        claims.append({"rank": "최우선", "who": "나(소액임차인 보호액)", "amount10k": protected, "basis": "주택임대차보호법 제8조, 시행령 제10·11조"})

    # 2) 담보권과 내 확정일자 보증금의 선후
    ahead_known = 0.0
    for m in mortgages or []:
        if m.get("amount10k") in (None, ""):
            claims.append({"rank": "내 앞(금액 미확인)", "who": "근저당(채권최고액)", "amount10k": None,
                           "basis": "주택임대차보호법 제3조의2", "note": "금액을 몰라 계산에 넣지 못했습니다. 등기부 을구의 채권최고액을 확인하세요."})
            continue
        amount = float(m.get("amount10k") or 0)
        registered = _date(m.get("registered"))
        if registered and my_date:
            if registered < my_date:
                position, note = "내 앞", f"근저당 등기({registered})가 내 우선변제 기준일({my_date})보다 빠릅니다."
            elif registered == my_date:
                position, note = "내 앞(같은 날 — 확인 필요)", "같은 날 경합은 판례·사건별 확인이 필요해 보수적으로 앞에 둡니다."
            else:
                position, note = "내 뒤", f"근저당 등기({registered})가 내 우선변제 기준일({my_date})보다 늦습니다."
        else:
            position, note = "내 앞(날짜 미확인)", "등기일이나 내 전입·확정일자를 몰라 보수적으로 앞에 둡니다."
        if position.startswith("내 앞"):
            ahead_known += amount
        claims.append({"rank": position, "who": "근저당(채권최고액)", "amount10k": amount, "basis": "주택임대차보호법 제3조의2, 부동산등기법 제4조", "note": note})

    if prior_tenants10k:
        ahead_known += float(prior_tenants10k)
        claims.append({"rank": "내 앞(날짜 미확인)", "who": "선순위 임차인 보증금", "amount10k": float(prior_tenants10k),
                       "basis": "다가구 확정일자 부여현황", "note": "앞 세입자의 전입·확정일자를 몰라 보수적으로 앞에 둡니다."})
    elif prior_tenants10k is None:
        unknowns.append("다른 세입자 보증금(다가구면 확정일자 부여현황)")

    # 3) 세금
    tax_note = {
        "yes": "체납 세금이 있습니다. 법정기일이 내 확정일자보다 빠른 세금은 앞설 수 있고, 금액을 몰라 계산에 넣지 못했습니다.",
        "no": "임대인이 체납이 없다고 확인했습니다(납세증명서로 확인 권장).",
        "unknown": "체납 세금은 확인 전입니다. 납세증명서를 요청하세요.",
    }.get(tax_arrears, "체납 세금은 확인 전입니다.")
    tax_note += (" 그 집에 붙는 세금(국세: 상속세·증여세·종합부동산세, 지방세: 재산세·소방분 지역자원시설세·재산세에 붙는 지방교육세)은 "
                 "내가 대항요건을 갖추고 확정일자를 그 법정기일보다 먼저 받았다면 그 세금에 배분될 금액 한도에서 보증금이 먼저 배분됩니다(국세 2023-04-01, 지방세 2023-05-04 이후 매각결정·매각허가결정분). 선순위 저당권 몫에는 영향이 없습니다.")
    if tax_arrears != "no":
        unknowns.append("임대인 체납 세금액과 법정기일")

    my_amount = deposit10k - (small["protected10k"] or 0)
    claims.append({"rank": "내 순서", "who": "나(확정일자 보증금)" if small["protected10k"] else "나(보증금)",
                   "amount10k": my_amount, "basis": "주택임대차보호법 제3조의2",
                   "note": f"우선변제 기준일 {my_date}" if my_date else "전입·확정일자를 받아야 우선변제 순위가 생깁니다."})

    needed = ahead_known + deposit10k
    ratio = round(needed / house_price10k * 100, 1) if house_price10k else None
    return {
        "ok": True,
        "deposit10k": deposit10k,
        "myPriorityDate": my_date.isoformat() if my_date else None,
        "opposabilityDate": opposable.isoformat() if opposable else None,
        "smallTenant": small,
        "claims": claims,
        "aheadKnown10k": round(ahead_known),
        "minSalePriceForFullReturn10k": round(needed),
        "minSalePriceIsLowerBound": mortgage_unknown or prior_tenants10k is None,
        "minSalePriceLabel": (f"경매로 최소 {money(needed)} 이상에 팔려야 보증금 전액이 돌아올 수 있습니다(경매 비용·세금·임금채권 제외 계산)."
                              + (" 근저당·다른 세입자 보증금을 모르는 상태라 실제로는 이보다 높을 수 있습니다." if (mortgage_unknown or prior_tenants10k is None) else "")),
        "vsHousePricePct": ratio,
        "taxNote": tax_note,
        "unknowns": unknowns,
        "notice": "법적 배당 계산이 아니라 순서를 이해하기 위한 계산입니다. 실제 배당은 경매 비용, 체납 세금, 임금채권, 배당요구 여부에 따라 달라지므로 전세피해 및 예방지원센터나 법률 전문가에게 확인하세요.",
        "sources": SOURCES,
    }


if __name__ == "__main__":
    today = date(2026, 11, 8)
    # 서울 보증금 6천만: 소액임차인(상한 1억6,500) → 최대 5,500만 최우선
    r = repayment_priority(6000, 30000, "seoul", "2026-03-02", "2026-03-02", [{"amount10k": 12000, "registered": "2024-05-01"}], 0, today=today)
    assert r["smallTenant"]["eligible"] is True and r["smallTenant"]["protected10k"] == 5500
    assert r["myPriorityDate"] == "2026-03-03"  # 대항력은 전입 다음 날, 확정일자와 늦은 쪽
    assert r["aheadKnown10k"] == 12000 and r["minSalePriceForFullReturn10k"] == 18000
    # 근저당이 내 기준일보다 늦으면 내 뒤
    r = repayment_priority(30000, 80000, "seoul", "2025-01-10", "2025-01-10", [{"amount10k": 20000, "registered": "2025-06-01"}], 0, today=today)
    assert r["claims"][0]["rank"] == "내 뒤" and r["aheadKnown10k"] == 0
    # 같은 날 전입·근저당: 대항력은 다음 날이라 근저당이 앞
    r = repayment_priority(30000, 80000, "seoul", "2025-01-10", "2025-01-10", [{"amount10k": 20000, "registered": "2025-01-10"}], 0, today=today)
    assert r["claims"][0]["rank"] == "내 앞"
    # 2023-02-21 전 근저당 → 종전 기준이라 보호액을 단정하지 않음
    r = repayment_priority(6000, 30000, "seoul", "2026-03-02", "2026-03-02", [{"amount10k": 12000, "registered": "2022-01-01"}], 0, today=today)
    assert r["smallTenant"]["eligible"] is None and r["smallTenant"]["protected10k"] is None
    # 상한 초과, 지역 모름
    assert repayment_priority(20000, 50000, "seoul", today=today)["smallTenant"]["eligible"] is False
    r = repayment_priority(6000, 30000, None, today=today)
    assert r["smallTenant"]["eligible"] is None and any("지역" in u for u in r["unknowns"])
    # 근저당 유무를 모르면 보호액을 확정하지 않는다 (전체 QA Astra-05)
    r = repayment_priority(6000, 30000, "seoul", "2026-03-02", "2026-03-02", [], 0, today=today)
    assert r["smallTenant"]["eligible"] is None and r["minSalePriceIsLowerBound"], r["smallTenant"]
    r = repayment_priority(6000, 30000, "seoul", "2026-03-02", "2026-03-02", [], 0, today=today, mortgage_status="none")
    assert r["smallTenant"]["eligible"] is True and not r["minSalePriceIsLowerBound"]
    # 2023-02-21 뒤 근저당이면 금액을 몰라도 현행 기준은 정해진다. 다만 최소 매각가는 하한이다.
    r = repayment_priority(6000, 30000, "seoul", "2026-03-02", "2026-03-02", [{"amount10k": None, "registered": "2025-01-01"}], 0, today=today)
    assert r["smallTenant"]["eligible"] is True and r["minSalePriceIsLowerBound"]
    # 근저당 날짜를 모르면 현행 금액을 단정하지 않는다
    r = repayment_priority(6000, 30000, "seoul", "2026-03-02", "2026-03-02", [{"amount10k": 12000, "registered": ""}], 0, today=today)
    assert r["smallTenant"]["eligible"] is None and "근저당 등기일" in r["unknowns"]
    # 보호액은 주택가액 1/2을 넘지 못한다
    assert repayment_priority(5500, 9000, "seoul", today=today, mortgage_status="none")["smallTenant"]["protected10k"] == 4500
    for bad in (dict(deposit10k=0), dict(deposit10k=6000, move_in_date="9999-12-31")):
        try:
            repayment_priority(**bad, today=today)
            raise AssertionError(f"거부해야 한다: {bad}")
        except ValueError:
            pass
    print("deposit_priority self-check OK")
