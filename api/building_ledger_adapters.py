#!/usr/bin/env python3
"""건축물대장(국토교통부 건축HUB 건축물대장정보 서비스) 어댑터.

전세 계약 전에 건물 용도(주거용인지, 근린생활시설이 섞였는지)와 사용승인일을 자동으로 확인한다.
조회 키(시군구·법정동 코드, 본번·부번)는 매칭된 매매 실거래 기록(sggCd·umdCd·bonbun·bubun)에서 얻는다.

한계 (숨기지 않는다)
- 표제부는 동(棟) 단위다. 계약할 호실의 용도는 전유부(호수)로 따로 확인해야 한다.
- 지금 연동한 표제부 응답에서는 위반건축물 여부를 찾지 못했다. 건축물대장을 발급해 확인해야 하므로 위반 여부는 항상 '미확인'으로 둔다.
"""

from __future__ import annotations

import os
import re
import threading
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from typing import Any

from env_loader import load_dotenv

load_dotenv()

TITLE_ENDPOINT = "https://apis.data.go.kr/1613000/BldRgstHubService/getBrTitleInfo"
KEY_ENVS = ("BUILDING_HUB_API_KEY", "MOLIT_SERVICE_KEY", "PUBLIC_DATA_API_KEY", "MOLIT_API_KEY")
CACHE_SECONDS = 24 * 3600
TIMEOUT = 8
_CACHE: dict[tuple[str, str, str, str], tuple[float, dict]] = {}
_LOCK = threading.Lock()

RESIDENTIAL = ("공동주택", "단독주택")
NONRESIDENTIAL_MARK = "근린생활"
VIOLATION_NOTE = (
    "지금 연동한 건축물대장 API 응답으로는 위반건축물 여부를 자동 확인하지 못했습니다. 정부24에서 건축물대장을 발급해 "
    "'위반건축물' 표시가 있는지 확인하세요. 표시가 없다고 모든 위반이 없다는 뜻은 아닙니다."
)


def _key() -> str:
    for name in KEY_ENVS:
        value = os.getenv(name, "").strip()
        if value:
            return value
    return ""


def classify(items: list[dict[str, str]]) -> dict[str, Any]:
    """주건축물의 주용도·기타용도로 주거용 여부를 가른다."""
    main = [i for i in items if i.get("mainAtchGbCdNm", "주건축물") == "주건축물"] or items
    purposes = sorted({p.strip() for i in main for p in [i.get("mainPurpsCdNm", ""), *re.split(r"[,，]", i.get("etcPurps", ""))] if p.strip()})
    if not main:
        use = "unknown"
    elif all(i.get("mainPurpsCdNm", "") in RESIDENTIAL for i in main):
        use = "mixed" if any(NONRESIDENTIAL_MARK in i.get("etcPurps", "") for i in main) else "residential"
    elif any(NONRESIDENTIAL_MARK in i.get("mainPurpsCdNm", "") for i in main):
        use = "nonresidential"
    else:
        use = "unknown"
    approvals = sorted({i.get("useAprDay", "").strip() for i in main if i.get("useAprDay", "").strip()})
    note = {
        "residential": "건축물대장 주용도가 모두 주거용(공동·단독주택)입니다. 계약할 호실의 용도는 전유부로 확인하세요.",
        "mixed": "일부 동에 근린생활시설이 섞여 있습니다. 계약할 호실이 주거용인지 전유부(호수)로 확인하세요. 근린생활시설 호실은 보증보험·전세대출이 막힐 수 있습니다.",
        "nonresidential": "주용도가 근린생활시설입니다. 주거용이 아닌 호실은 보증보험·전세대출이 막힐 수 있습니다.",
        "unknown": "건축물대장 용도를 판단하지 못했습니다. 건축물대장을 발급해 확인하세요.",
    }[use]
    return {
        "use": use,
        "purposes": purposes[:8],
        "buildings": len(main),
        "approvalDate": approvals[0] if approvals else "",
        "note": note,
        "violation": "unknown",
        "violationNote": VIOLATION_NOTE,
    }


ERROR_CACHE_SECONDS = 600


def _remember_error(cache_key: tuple, result: dict) -> dict:
    """실패도 10분 기억한다. 아니면 API가 느리거나 막혔을 때 판정 요청마다 최대 8초씩 기다린다."""
    with _LOCK:
        _CACHE[cache_key] = (time.time() - CACHE_SECONDS + ERROR_CACHE_SECONDS, result)
    return result


def building_ledger(sgg: str, umd: str, bonbun: str, bubun: str) -> dict[str, Any]:
    """시군구·법정동·본번·부번으로 표제부를 조회해 용도를 분류한다. 실패해도 예외 없이 사유를 돌려준다."""
    base = {"source": "국토교통부 건축HUB 건축물대장 표제부", "configured": bool(_key())}
    if not base["configured"]:
        return {**base, "mode": "not_configured", "use": "unknown", "violation": "unknown", "violationNote": VIOLATION_NOTE}
    if not (sgg and umd and bonbun):
        return {**base, "mode": "no_lot", "use": "unknown", "violation": "unknown", "violationNote": VIOLATION_NOTE,
                "note": "매칭된 매매 실거래 기록이 없어 건축물대장 조회 키(지번)를 얻지 못했습니다."}
    cache_key = (sgg, umd, bonbun.zfill(4), (bubun or "0").zfill(4))
    with _LOCK:
        hit = _CACHE.get(cache_key)
    if hit and time.time() - hit[0] < CACHE_SECONDS:
        return hit[1]
    params = {"serviceKey": _key(), "sigunguCd": sgg, "bjdongCd": umd, "platGbCd": "0",
              "bun": cache_key[2], "ji": cache_key[3], "numOfRows": "100", "pageNo": "1"}
    try:
        request = urllib.request.Request(f"{TITLE_ENDPOINT}?{urllib.parse.urlencode(params)}", headers={"User-Agent": "MoveValue/0.1"})
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(request, timeout=TIMEOUT) as response:  # noqa: S310 - official public API endpoint.
            root = ET.fromstring(response.read())
    except Exception as exc:  # noqa: BLE001 - live adapter must not break prototype.
        return _remember_error(cache_key, {**base, "mode": "error", "error": str(exc), "use": "unknown",
                                           "violation": "unknown", "violationNote": VIOLATION_NOTE})
    code = (root.findtext(".//resultCode") or "").strip()
    if code and code not in {"00", "000"}:
        return _remember_error(cache_key, {**base, "mode": "error", "error": f"{code}: {root.findtext('.//resultMsg')}",
                                           "use": "unknown", "violation": "unknown", "violationNote": VIOLATION_NOTE})
    items = [{child.tag: (child.text or "").strip() for child in item} for item in root.findall(".//item")]
    if not items:
        result = {**base, "mode": "no_record", "use": "unknown", "violation": "unknown", "violationNote": VIOLATION_NOTE,
                  "note": "이 지번으로 건축물대장 표제부를 찾지 못했습니다."}
    else:
        result = {**base, "mode": "live_api", **classify(items)}
    with _LOCK:
        _CACHE[cache_key] = (time.time(), result)
    return result


def ledger_for_market(market: dict[str, Any]) -> dict[str, Any]:
    record = market.get("molitLatestTradeRecord") or {}
    return building_ledger(record.get("sggCd", ""), record.get("umdCd", ""), record.get("bonbun", ""), record.get("bubun", ""))


if __name__ == "__main__":
    apt = [{"mainAtchGbCdNm": "주건축물", "mainPurpsCdNm": "공동주택", "etcPurps": "공동주택(아파트)", "useAprDay": "20001027"}]
    assert classify(apt)["use"] == "residential"
    mixed = apt + [{"mainAtchGbCdNm": "주건축물", "mainPurpsCdNm": "공동주택", "etcPurps": "공동주택(아파트),근린생활시설(상가)"}]
    assert classify(mixed)["use"] == "mixed"
    shop = [{"mainAtchGbCdNm": "주건축물", "mainPurpsCdNm": "제2종근린생활시설", "etcPurps": "고시원"}]
    assert classify(shop)["use"] == "nonresidential"
    parking = apt + [{"mainAtchGbCdNm": "부속건축물", "mainPurpsCdNm": "공동주택", "etcPurps": "지하주차장"}]
    assert classify(parking)["buildings"] == 1, "부속건축물은 용도 판단에서 뺀다"
    assert classify(apt)["violation"] == "unknown", "위반 여부는 API에 없으므로 항상 미확인"
    assert building_ledger("", "", "", "")["mode"] in {"no_lot", "not_configured"}
    print("building_ledger self-check OK")
