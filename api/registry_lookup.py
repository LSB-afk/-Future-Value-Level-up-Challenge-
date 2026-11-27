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
import sqlite3
import threading
import time
import unicodedata
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta, timezone

from document_requests import DocumentRequestError, _pdf_lines, private_db_file

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


class RegistryUncertain(RegistryError):
    """제공기관이 요청을 처리했는지(과금됐는지) 알 수 없는 타임아웃·연결 오류."""


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
        raise RegistryUncertain(
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


# 요약표 권리 판독: 단어가 유효 기록 행에 있으면 yes, 섹션이 '기록사항 없음'뿐이면 no, 나머지는 unknown.
# 근거에는 쪽·줄과 찾은 권리 이름만 남긴다. 같은 행의 소유자·채권자 이름은 결과에 넣지 않는다.
_RIGHT_TERMS = {
    "trust": r"신탁",
    "seizure": r"가?압류",
    "auction": r"(?:임의|강제)?경매개시결정",
    "leaseRegistration": r"(?:주택|상가건물)?임차권(?:설정)?",
}
_RIGHT_SECTIONS = (
    (("trust", "seizure", "auction"), r"소유지분을제외한소유권에관한사항\(?갑구\)?"),
    (("leaseRegistration",), r"\(?근\)?저당권및전세권등\(?을구\)?"),
)
_EMPTY_MARKS = ("기록사항없음", "해당사항없음", "기록사항없습니다")


def _summary_section(lines, compact, summary, title):
    """요약표에서 제목이 한 번만 나오는 섹션의 본문 행. 섹션이 없거나 여러 번이면 None."""
    starts = [i for i, k in enumerate(compact) if i > summary and re.search(title, k)]
    if len(starts) != 1:
        return None
    rows = []
    for i in range(starts[0] + 1, len(lines)):
        k = compact[i]
        if re.match(
            r"^\[?(?:\d+[.．])?참고사항|^이증명서는|^본주요등기사항|^\d+[.．].*(?:갑구|을구)\)?$",
            k,
        ):
            break
        if re.fullmatch(r"(?:순위번호|등기목적|접수정보|주요등기사항|대상소유자)+", k):
            continue
        rows.append((lines[i], k))
    return rows


def _summary_rights(lines, compact, summary):
    rights = dict.fromkeys(_RIGHT_TERMS, "unknown")
    evidence = []
    for keys, title in _RIGHT_SECTIONS:
        rows = _summary_section(lines, compact, summary, title)
        # 요약표는 말소되지 않은 사항만 싣는다. 말소 표시가 보이면 형식을 믿을 수 없다.
        if not rows or any("말소" in k for _, k in rows):
            continue
        if any(k.strip("-ㆍ·*.,()[]") in _EMPTY_MARKS for _, k in rows):
            if len(rows) == 1:
                row = rows[0][0]
                rights.update(dict.fromkeys(keys, "no"))
                evidence.extend(
                    {"page": row["page"], "line": row["line"], "right": key, "text": row["text"]}
                    for key in keys
                )
            continue
        for key in keys:
            for row, k in rows:
                found = re.search(_RIGHT_TERMS[key], k)
                if found:
                    rights[key] = "yes"
                    evidence.append(
                        {"page": row["page"], "line": row["line"], "right": key, "text": found[0]}
                    )
                    break
    return rights, evidence


def _parse_pdf(address, pdf, selected=None):
    lines = _text_lines(pdf)
    result = {
        "address": address,
        "propertyId": None,
        "issuedAt": None,
        "mortgageMax10k": None,
        "evidence": [],
        "rights": dict.fromkeys(_RIGHT_TERMS, "unknown"),
        "rightsEvidence": [],
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
    # 주소·고유번호·열람일을 대조한 문서에서만 갑구·을구 권리를 읽는다. 근저당 보류와는 따로 본다.
    result["rights"], result["rightsEvidence"] = _summary_rights(lines, compact, summary)
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


# 유료 열람 기록. 같은 요청 번호로는 제공기관을 두 번 부르지 않는다.
# PDF 원문과 증거 줄(이름이 들어갈 수 있다)은 남기지 않고 판독 결과만 남긴다.
_CHARGE_KEY = re.compile(r"[A-Za-z0-9_-]{16,128}")
_CHARGE_SUMMARY = ("address", "propertyId", "issuedAt", "mortgageMax10k", "reviewRequired",
                   "reason", "documentHash", "source", "selectedAddress")
_CHARGE_PENDING_SECONDS = 180  # 제공기관 타임아웃보다 길게 처리 중이면 결과를 알 수 없는 것으로 본다.
_CHARGE_RETENTION = 7 * 86400
_KST = timezone(timedelta(hours=9))


def _daily_limit():
    try:
        return max(0, int(os.environ.get("FITHOME_REGISTRY_DAILY_LIMIT", "50")))
    except ValueError:
        return 50


def _charge_db():
    conn = sqlite3.connect(private_db_file("access.sqlite3"), timeout=5, isolation_level=None)
    conn.execute("""CREATE TABLE IF NOT EXISTS registry_charges (
        key TEXT PRIMARY KEY, request TEXT NOT NULL, uniq_no TEXT NOT NULL, status TEXT NOT NULL,
        summary TEXT NOT NULL, day TEXT NOT NULL, created REAL NOT NULL, updated REAL NOT NULL)""")
    return conn


def _charge_row(key):
    conn = _charge_db()
    try:
        return conn.execute("SELECT request, status, summary, updated FROM registry_charges WHERE key=?",
                            (key,)).fetchone()
    finally:
        conn.close()


def _replay(row, request):
    stored_request, status, summary, updated = row
    if stored_request != request:
        raise RegistryError("이 요청 번호는 다른 등기 조회에 이미 쓰였습니다. 주소를 다시 검색해 주세요.", 409)
    if status == "done":
        return {**json.loads(summary), "replayed": True}
    if status == "failed":
        stored = json.loads(summary)
        raise RegistryError(stored["error"], stored["status"])
    if status == "pending" and time.time() - updated < _CHARGE_PENDING_SECONDS:
        raise RegistryError("같은 등기 조회를 처리하고 있습니다. 잠시 후 결과를 다시 확인해 주세요.", 409)
    raise RegistryError(
        "제공기관 응답이 끊겨 과금 여부 확인이 필요합니다. 이중 과금을 막기 위해 같은 요청은 다시 열람하지 않습니다. "
        "제공기관 이용 내역을 확인한 뒤 주소를 다시 검색해 주세요.",
        409,
    )


def _reserve(key, request, number):
    """호출 전에 'pending'을 먼저 남긴다. 이미 있는 요청 번호면 그 기록을 돌려준다."""
    now = time.time()
    conn = _charge_db()
    try:
        conn.execute("BEGIN IMMEDIATE")
        try:
            conn.execute("DELETE FROM registry_charges WHERE created < ?", (now - _CHARGE_RETENTION,))
            row = conn.execute("SELECT request, status, summary, updated FROM registry_charges WHERE key=?",
                               (key,)).fetchone()
            if row:
                return row
            day = datetime.now(_KST).date().isoformat()
            used = conn.execute("SELECT COUNT(*) FROM registry_charges WHERE day=?", (day,)).fetchone()[0]
            limit = _daily_limit()
            if used >= limit:
                raise RegistryError(
                    f"오늘 유료 등기 조회 한도({limit}건)를 모두 사용했습니다. 내일 다시 시도하거나 등기 PDF를 제출해 주세요.",
                    429,
                )
            conn.execute("INSERT INTO registry_charges VALUES (?,?,?,?,?,?,?,?)",
                         (key, request, number, "pending", "{}", day, now, now))
            conn.execute("COMMIT")
        except BaseException:
            conn.execute("ROLLBACK")
            raise
    finally:
        conn.close()
    return None


def _settle(key, status, summary=None):
    try:
        conn = _charge_db()
        try:
            if status is None:  # 제공기관을 부르지 않았다.
                conn.execute("DELETE FROM registry_charges WHERE key=? AND status='pending'", (key,))
            else:
                conn.execute("UPDATE registry_charges SET status=?, summary=?, updated=? WHERE key=?",
                             (status, json.dumps(summary or {}, ensure_ascii=False), time.time(), key))
        finally:
            conn.close()
    except (sqlite3.Error, OSError, DocumentRequestError):
        # 기록이 'pending'으로 남으면 같은 요청 번호의 재시도는 과금 확인 안내를 받는다.
        pass


def fetch_registry(address, property_id, confirm_charge=False, idempotency_key=None):
    """유료 열람. idempotency_key가 있으면 호출 전후를 기록하고 일일 상한을 적용한다(HTTP 경로는 항상 넘긴다)."""
    address = _address(address)
    if confirm_charge is not True:
        raise RegistryError("등기 주소·동호수와 유료 열람을 확인해 주세요.")
    if not registry_status()["available"]:
        raise RegistryError(registry_status()["reason"], 503)
    if not isinstance(property_id, str):
        raise RegistryError("주소를 검색하고 등기를 다시 선택해 주세요.")
    key = request = None
    if idempotency_key is not None:
        if not isinstance(idempotency_key, str) or not _CHARGE_KEY.fullmatch(idempotency_key):
            raise RegistryError("유료 열람 요청 번호 형식을 확인해 주세요.")
        key = hashlib.sha256(idempotency_key.encode()).hexdigest()
        request = hashlib.sha256((address + "\x00" + property_id).encode()).hexdigest()
        try:
            row = _charge_row(key)
        except (sqlite3.Error, OSError) as exc:
            raise RegistryError("유료 열람 기록을 확인하지 못해 열람하지 않았습니다.", 503) from exc
        if row:
            return _replay(row, request)
    with _LOCK:
        record = _SELECTIONS.get(property_id)
        if (
            not record
            or record[1] != address
            or time.monotonic() - record[0] > _SELECTION_TTL
        ):
            raise RegistryError("유효한 주소 검색 결과를 다시 선택해 주세요.", 409)
    if key:
        try:
            row = _reserve(key, request, record[2])
        except (sqlite3.Error, OSError) as exc:
            raise RegistryError("유료 열람 기록을 남기지 못해 열람하지 않았습니다.", 503) from exc
        if row:
            return _replay(row, request)
    with _LOCK:
        # Do not charge twice on double-click/retry.
        if _SELECTIONS.pop(property_id, None) is None:
            if key:
                _settle(key, None)
            raise RegistryError("유효한 주소 검색 결과를 다시 선택해 주세요.", 409)
    _, _, number, where, kind = record
    try:
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
    except RegistryUncertain:
        if key:
            _settle(key, "unknown")
        raise
    except RegistryError as exc:
        if key:
            _settle(key, "failed", {"error": str(exc), "status": exc.http_status})
        raise
    except BaseException:
        if key:
            _settle(key, "unknown")
        raise
    result["source"] = "hyphen"
    result["selectedAddress"] = where
    if key:
        _settle(key, "done", {name: result.get(name) for name in _CHARGE_SUMMARY})
    return result
