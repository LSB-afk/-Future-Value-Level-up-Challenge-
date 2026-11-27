"""주소로 현재 등기를 선택하고 PDF의 근저당 근거를 대조한다.

하이픈 상품 145의 IN0004000168(간편 주소검색), IN0004000163(회원 열람).
https://hyphen.im/product-api/view?seq=145
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import threading
import time
import unicodedata
import urllib.error
import urllib.request
from datetime import date

from document_requests import DocumentRequestError, _pdf_lines

MAX_PDF = 4 * 1024 * 1024
_PROVIDER = "하이픈 · 인터넷등기소"
_CREDS = (
    "HYPHEN_USER_ID",
    "HYPHEN_HKEY",
    "FITHOME_IROS_USER_ID",
    "FITHOME_IROS_USER_PW",
)
_SELECTIONS = {}
_LOCK = threading.Lock()
_SELECTION_TTL = 15 * 60


class RegistryError(ValueError):
    def __init__(self, message, http_status=400):
        super().__init__(message)
        self.http_status = http_status


def registry_status():
    ready = all(os.environ.get(name, "").strip() for name in _CREDS)
    return {
        "available": ready,
        "provider": _PROVIDER,
        "reason": (
            ""
            if ready
            else "등기 열람 계약 계정이 연결되지 않았습니다. 인터넷등기소에서 받은 PDF로 확인할 수 있습니다."
        ),
    }


def _address(value):
    if not isinstance(value, str):
        raise RegistryError("매물의 주소를 입력해 주세요.")
    value = " ".join(unicodedata.normalize("NFKC", value).split())
    if (
        not 5 <= len(value) <= 250
        or not re.search(r"[가-힣]", value)
        or not re.search(r"\d", value)
    ):
        raise RegistryError(
            "도로명과 건물번호 또는 지번을 포함한 전체 주소를 입력해 주세요."
        )
    return value


def _provider(endpoint, params):
    if not registry_status()["available"]:
        raise RegistryError(registry_status()["reason"], 503)
    params = {
        **params,
        "userId": os.environ[_CREDS[2]],
        "userPw": os.environ[_CREDS[3]],
    }
    req = urllib.request.Request(
        "https://api.hyphen.im/" + endpoint,
        data=json.dumps(params).encode(),
        headers={
            "Content-Type": "application/json",
            "user-id": os.environ[_CREDS[0]],
            "Hkey": os.environ[_CREDS[1]],
        },
    )

    # Never forward server credentials to a different endpoint on redirect.
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None

    try:
        opener = urllib.request.build_opener(NoRedirect)
        with opener.open(req, timeout=60) as response:
            raw = response.read(3 * MAX_PDF + 1)
        if len(raw) > 3 * MAX_PDF:
            raise RegistryError("등기 응답이 처리 가능한 크기를 초과했습니다.", 502)
        result = json.loads(raw)
    except (OSError, UnicodeError, json.JSONDecodeError, urllib.error.URLError) as exc:
        raise RegistryError(
            "등기 제공기관 응답을 확인하지 못했습니다. 유료 열람은 자동 재시도하지 않습니다.",
            502,
        ) from exc
    if (
        not isinstance(result, dict)
        or not isinstance(result.get("common"), dict)
        or result["common"].get("errYn") != "N"
        or not isinstance(result.get("data"), dict)
    ):
        raise RegistryError(
            "제공기관에서 정상 등기 결과를 받지 못했습니다. 이용 권한과 거래 내역을 확인해 주세요.",
            502,
        )
    return result["data"]


def _compact(s):
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", s))


def _units(s):
    # A legal-dong name before a lot number identifies the neighbourhood,
    # while e.g. A동 or 가동 after the house number identifies a specific block.
    s = re.sub(
        r"^.*?(?:로|길|동|리|가|읍|면)\s+(?:산\s*)?\d+(?:-\d+)?(?=\s|,|\(|$)", "", s
    )
    s = re.sub(r"([동층])(?=제?[A-Za-z0-9])", r"\1 ", s)
    result = {}
    for kind in ("동", "호"):
        value = r"[A-Za-z0-9][A-Za-z0-9-]{0,19}"
        if kind == "동":
            value += r"|[가-힣]{1,12}"
        pattern = (
            r"(?<![가-힣A-Za-z0-9-])(?:제\s*)?("
            + value
            + r")\s*"
            + kind
            + r"(?=$|[\s.,()\[\]])"
        )
        result[kind] = {
            str(int(n)) if n.isdigit() else n.upper() for n in re.findall(pattern, s)
        }
    return result


def _same_unit(address, description):
    wanted = _units(address)
    return (
        len(wanted["호"]) == 1
        and len(wanted["동"]) <= 1
        and wanted == _units(description)
    )


def _prop_id(s):
    return str(s or "").replace("-", "").strip()


def search_registry(address):
    address = _address(address)
    data = _provider(
        "in0004000168",
        {
            "kindcls": "전체",
            "admin_regn1": "전체",
            "cls_flag": "현행",
            "simple_address": address,
            "detailYn": "N",
            "pageNo": "1",
        },
    )
    entries = data.get("list")
    if not isinstance(entries, list):
        raise RegistryError("주소 검색 결과 형식을 확인할 수 없습니다.", 502)
    more = str(data.get("totPage", "1")) not in {"1", "0"} or len(entries) > 100
    matches = []
    target = _address_key(address)
    candidates = {}
    rejected_unit = rejected_address = False
    for item in entries[:100]:
        if not isinstance(item, dict):
            continue
        number = _prop_id(item.get("get부동산고유번호"))
        where = item.get("get부동산소재지번")
        kind = item.get("get구분")
        if (
            not re.fullmatch(r"\d{14}", number)
            or not isinstance(where, str)
            or kind not in {"건물", "집합건물"}
            or item.get("get상태") != "현행"
        ):
            continue
        if not target or _address_key(where) != target:
            rejected_address = True
            continue
        if kind == "집합건물" and not _same_unit(address, where):
            rejected_unit = True
            continue
        candidates[number] = (where, kind)
    condo_count = sum(kind == "집합건물" for _, kind in candidates.values())
    now = time.monotonic()
    with _LOCK:
        for token, record in list(_SELECTIONS.items()):
            if now - record[0] > _SELECTION_TTL:
                del _SELECTIONS[token]
        for number, (where, kind) in candidates.items():
            if kind == "집합건물" and (condo_count != 1 or more):
                rejected_unit = True
                continue
            if len(_SELECTIONS) >= 4096:
                del _SELECTIONS[next(iter(_SELECTIONS))]
            token = secrets.token_urlsafe(24)
            _SELECTIONS[token] = (now, address, number, where, kind)
            matches.append(
                {"id": token, "propertyId": number, "address": where, "kind": kind}
            )
    if not matches and rejected_unit:
        raise RegistryError(
            "집합건물은 매물 주소에 등기와 일치하는 동·호수를 입력해 한 세대로 특정해 주세요.",
            422,
        )
    if not matches and rejected_address:
        raise RegistryError(
            "검색 결과의 등기 소재지와 입력 주소를 대조할 수 없습니다. 매물의 정확한 지번으로 다시 검색해 주세요.",
            422,
        )
    return {"items": matches, "provider": _PROVIDER, "more": more}


def _text_lines(pdf):
    if not isinstance(pdf, bytes) or not pdf.startswith(b"%PDF-") or len(pdf) > MAX_PDF:
        raise RegistryError("4MB 이하의 등기 PDF 원본이 필요합니다.")
    try:
        pages = _pdf_lines(pdf)
    except DocumentRequestError as exc:
        raise RegistryError(str(exc), exc.status) from exc
    return [
        {"page": idx, "line": n, "text": line.strip()}
        for idx, lines in enumerate(pages, 1)
        for n, line in enumerate(lines, 1)
        if line.strip()
    ]


_SIDO = {
    "서울": "서울특별시",
    "부산": "부산광역시",
    "대구": "대구광역시",
    "인천": "인천광역시",
    "광주": "광주광역시",
    "대전": "대전광역시",
    "울산": "울산광역시",
    "세종": "세종특별자치시",
    "경기": "경기도",
    "강원": "강원특별자치도",
    "충북": "충청북도",
    "충남": "충청남도",
    "전북": "전북특별자치도",
    "전남": "전라남도",
    "경북": "경상북도",
    "경남": "경상남도",
    "제주": "제주특별자치도",
}


def _address_key(address):
    # Compare the actual city/district/street (or lot) and the whole house number.
    address = re.sub(r"^\s*\[(?:집합건물|건물|도로명주소)\]\s*", "", address)
    address = re.sub(
        r"^\S+\s+",
        lambda m: _SIDO.get(m.group().strip(), m.group().strip()) + " ",
        address.strip(),
        count=1,
    )
    m = re.match(
        r"^(.+?(?:로|길|동|리|가|읍|면))\s+(산\s*)?(\d+(?:-\d+)?)(?=\s|,|\(|$)", address
    )
    if not m or not re.search(r"(시|도|군|구)\s+", m[1]):
        return None
    return _compact(m[0])


def _empty_collateral_lines(lines):
    """Identify only empty-list annotations; None means joint collateral needs review."""
    annotations = set()
    label = r"공동(?:담보|저당)(?:목록)?"
    empty = r"(?:(?:기록사항|해당사항|해당)?(?:없음|없습니다))"
    for i, key in enumerate(lines):
        if not re.search(label, key):
            continue
        # A plain, explicitly empty list is common. A numbered list or any
        # mention elsewhere still requires inspection of the underlying rights.
        normalized = key.strip("[]【】():：.ㆍ·-")
        if re.fullmatch(label + r"[:：(\[]*" + empty + r"[)\].]*", normalized):
            annotations.add(i)
            continue
        if (
            re.fullmatch(label, normalized)
            and i + 1 < len(lines)
            and re.fullmatch(empty, lines[i + 1].strip("-ㆍ·*.,()[]"))
        ):
            annotations.update((i, i + 1))
            continue
        return None
    return annotations


def _parse_pdf(address, pdf, selected=None):
    lines = _text_lines(pdf)
    result = {
        "address": address,
        "propertyId": None,
        "issuedAt": None,
        "mortgageMax10k": None,
        "evidence": [],
        "reviewRequired": True,
        "reason": "",
        "documentHash": hashlib.sha256(pdf).hexdigest() if isinstance(pdf, bytes) else None,
    }

    def hold(message):
        result["reason"] = message
        return result

    if not lines:
        return hold(
            "텍스트를 읽을 수 없는 PDF입니다. 인터넷등기소의 텍스트 PDF 원본을 제출해 주세요."
        )
    compact = [_compact(row["text"]) for row in lines]
    text = "\n".join(compact)
    if "등기사항전부증명서" not in text:
        return hold("등기사항전부증명서 문서 제목을 확인하지 못했습니다.")

    # Only property descriptions in the title/표제부 count; owner addresses and
    # 공동담보 collateral descriptions deeper inside the deed are not this property.
    header = []
    for row, key in zip(lines, compact):
        if (
            "갑구" in key
            or "소유권에관한사항" in key
            or "을구" in key
            or key.startswith("주요등기사항요약")
        ):
            break
        header.append(row)
    head = "\n".join(_compact(row["text"]) for row in header)
    target = _address_key(address)
    address_row = next(
        (
            row
            for row in header
            if target
            and (
                _address_key(row["text"]) == target
                or re.search(re.escape(target) + r"(?![\d-])", _compact(row["text"]))
            )
        ),
        None,
    )
    if address_row is None:
        return hold("등기 표제부에서 입력한 주소와 같은 건물을 확인하지 못했습니다.")
    result["evidence"].append(address_row)
    prop_ids = {
        a + b + c
        for a, b, c in re.findall(
            r"고유번호[:：]?(\d{4})-?(\d{4})-?(\d{6})(?!\d)", text
        )
    }
    if len(prop_ids) != 1:
        return hold("하나의 부동산 고유번호를 확인할 수 없습니다.")
    result["propertyId"] = prop_ids.pop()
    if selected and result["propertyId"] != selected[2]:
        return hold("선택한 부동산과 등기의 고유번호가 다릅니다.")
    is_condo = "집합건물" in head
    if not is_condo and ("[건물]" not in head and "-건물-" not in head):
        return hold("주택 건물의 등기 종류를 확인할 수 없습니다.")
    if selected and (selected[4] == "집합건물") != is_condo:
        return hold("선택한 건물 종류와 PDF의 종류가 다릅니다.")
    if is_condo:
        # Use the apartment header (property description), not the title table's
        # area statistics / neighbouring units. Numbers in legal dong names
        # (e.g. '가양1동') are excluded by the token boundary.
        desc = [
            r["text"]
            for r in header
            if "집합건물" in _compact(r["text"]) or any(_units(r["text"]).values())
        ]
        if not _same_unit(address, " ".join(desc)) or (
            selected and not _same_unit(address, selected[3])
        ):
            return hold(
                "집합건물의 동·호수가 불분명합니다. 정확한 동·호수가 포함된 주소와 해당 PDF가 필요합니다."
            )
    dates = set()
    for row, k in zip(lines, compact):
        m = re.search(
            r"(?:발급일시|발급일자|열람일시|열람일자)[:：]?(\d{4})[년.\-/](\d{1,2})[월.\-/](\d{1,2})",
            k,
        )
        if not m:
            continue
        try:
            day = date(*map(int, m.groups()))
        except ValueError:
            continue
        if day not in dates:
            result["evidence"].append(row)
        dates.add(day)
    if len(dates) != 1:
        return hold("단일 발급·열람일을 확인하지 못했습니다.")
    issued = dates.pop()
    result["issuedAt"] = issued.isoformat()
    if not 0 <= (date.today() - issued).days <= 30:
        return hold(
            "등기 열람일이 미래이거나 30일이 지났습니다. 최근 원본을 제출해 주세요."
        )

    # Use only the official current-rights summary, never sum historical entries.
    summary = next(
        (i for i, k in enumerate(compact) if k.startswith("주요등기사항요약")), None
    )
    if summary is None:
        return hold("원문에서 현재 유효한 권리 요약을 식별할 수 없습니다.")
    starts = [
        i
        for i, k in enumerate(compact)
        if i > summary and re.search(r"\(?근\)?저당권및전세권등\(?을구\)?", k)
    ]
    if len(starts) != 1:
        return hold("을구의 현재 근저당 목록을 확인할 수 없습니다.")
    annotations = _empty_collateral_lines(compact)
    if annotations is None:
        return hold("공동담보 원문을 확인해야 근저당 합계를 반영할 수 있습니다.")
    rows = []
    for i in range(starts[0] + 1, len(lines)):
        if i in annotations:
            continue
        k = compact[i]
        if re.match(
            r"^(?:\d+[.．])?참고사항|^이증명서는|^본주요등기사항",
            k,
        ):
            break
        rows.append((lines[i], k))
    if not rows:
        return hold("을구 요약이 비어 있습니다.")
    mentions = [r for r, k in rows if "채권최고액" in k]
    result["evidence"].extend(mentions[:12])
    sensitive_rights = (
        "변경",
        "경정",
        "말소",
        "이전",
        "일부포기",
        "질권",
        "가등기",
        "가처분",
        "전세권설정",
        "저당권설정청구권",
    )
    if any(t in k for _, k in rows for t in sensitive_rights) or any(
        re.search(r"(?<!근)저당권설정", k) for _, k in rows
    ):
        return hold(
            "공동담보·변경 등 권리 관계가 있어 근저당 합계를 자동 반영하지 않았습니다."
        )
    empties = [
        r
        for r, k in rows
        if k.strip("-ㆍ·*.,()[]")
        in ("기록사항없음", "해당사항없음", "기록사항없습니다")
    ]
    if (
        empties
        and not mentions
        and not any("설정" in k or re.match(r"^\d+근저당", k) for _, k in rows)
    ):
        result["mortgageMax10k"] = 0
        result["evidence"].append(empties[0])
    else:
        # Different ranks may be summed only when each clearly starts a single
        # active mortgage, has exactly one amount, and appears only once.
        ranks = []
        amounts = []
        if empties:
            return hold(
                "을구에 권리 기록과 빈 목록 표시가 함께 있어 원문 확인이 필요합니다."
            )
        for index, (row, k) in enumerate(rows):
            if "근저당권설정" in k:
                rank = re.match(r"^(\d{1,5})근저당권설정", k)
                if not rank and k.startswith("근저당권설정") and index:
                    previous, value = rows[index - 1]
                    if previous["page"] == row["page"]:
                        rank = re.fullmatch(r"(\d{1,5})", value)
                if (
                    not rank
                    or k.count("근저당권설정") != 1
                    or len(ranks) != len(amounts)
                    or rank[1] in ranks
                ):
                    return hold(
                        "현재 근저당 순위번호와 채권최고액을 일대일로 대조할 수 없습니다."
                    )
                ranks.append(rank[1])
            if "채권최고액" in k:
                amount_line = k
                if re.search(r"채권최고액[:：]?금?$", k) and index + 1 < len(rows):
                    next_row, value = rows[index + 1]
                    if next_row["page"] == row["page"]:
                        amount_line += value
                        if len(result["evidence"]) < 27:
                            result["evidence"].append(next_row)
                amount = re.search(
                    r"채권최고액[:：]?금?([0-9]{1,3}(?:,[0-9]{3}){1,5}|[0-9]{1,16})원",
                    amount_line,
                )
                if (
                    not amount
                    or k.count("채권최고액") != 1
                    or len(ranks) != len(amounts) + 1
                ):
                    return hold("근저당마다 원 단위 채권최고액을 특정할 수 없습니다.")
                amounts.append(int(amount[1].replace(",", "")))
        if not amounts or len(ranks) != len(amounts) or len(amounts) > 12:
            return hold("원문을 검토해야 근저당 합계를 확인할 수 있습니다.")
        result["mortgageMax10k"] = sum(amounts) / 10000
    result.update(
        reviewRequired=False,
        reason="주소·열람일·현재 권리 요약을 대조했습니다. 원문 근거를 확인한 뒤 반영해 주세요.",
    )
    return result


def read_registry_pdf(address, pdf_bytes):
    result = _parse_pdf(_address(address), pdf_bytes)
    result["source"] = "uploaded_pdf"
    return result


def fetch_registry(address, property_id, confirm_charge=False):
    address = _address(address)
    if confirm_charge is not True:
        raise RegistryError("등기 주소·동호수와 유료 열람을 확인해 주세요.")
    if not registry_status()["available"]:
        raise RegistryError(registry_status()["reason"], 503)
    if not isinstance(property_id, str):
        raise RegistryError("주소를 검색하고 등기를 다시 선택해 주세요.")
    with _LOCK:
        record = _SELECTIONS.get(property_id)
        if (
            not record
            or record[1] != address
            or time.monotonic() - record[0] > _SELECTION_TTL
        ):
            raise RegistryError("유효한 주소 검색 결과를 다시 선택해 주세요.", 409)
        del _SELECTIONS[property_id]  # Do not charge twice on double-click/retry.
    _, _, number, where, kind = record
    data = _provider(
        "in0004000163",
        {
            "uniqNo": number,
            "searchDiv": "uniqNo",
            "cmortCheck": "Y",
            "pdfHex": "Y",
            "display": "1",
            "dupChk": "Y",
            "closingYn": "N",
            "excRegYn": "N",
            "kindcls": "1" if kind == "집합건물" else "3",
            "kindclsYn": "Y",
        },
    )
    out = data.get("outList")
    if not isinstance(out, dict) or _prop_id(out.get("get고유번호")) != number:
        raise RegistryError(
            "제공기관이 선택한 고유번호와 일치하는 원본을 반환하지 않았습니다.", 502
        )
    raw = data.get("pdfHexString")
    if not isinstance(raw, str) or len(raw) > 2 * MAX_PDF:
        raise RegistryError("제공기관 PDF를 읽을 수 없습니다.", 502)
    try:
        pdf = bytes.fromhex(raw)
    except ValueError as exc:
        raise RegistryError("제공기관 PDF가 손상됐습니다.", 502) from exc
    result = _parse_pdf(address, pdf, record)
    result["source"] = "hyphen"
    result["selectedAddress"] = where
    return result
