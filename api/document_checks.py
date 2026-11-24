"""Extract bounded, labelled evidence from tenant-supplied PDFs. No file or identity is retained."""
from __future__ import annotations

import re
from datetime import date

from document_requests import (
    MAX_PDF_BYTES, DocumentRequestError, _address_key, _compact, _date_in, _evidence,
    _norm, _pdf_lines, _requested_building, _today,
)
from jeonse_verdict import REGISTRY_FRESH_DAYS


# Only target-property fields are eligible. In particular, 개인 주소 and 중개사무소 소재지
# also occur on real forms and must never match the report address.
_LABELS = {
    "road": ("도로명주소",),
    "site": ("주택소재지", "건축물소재지", "대지위치", "물건소재지", "대상물건소재지", "중개대상물소재지"),
    "siteSection": ("소재지",),
    "unit": ("호명칭", "호수", "전유부호명칭"),
    "block": ("동명칭", "동명칭및번호"),
    "issuedAt": ("발급일자", "발급일시", "발급일", "교부일", "작성일자", "작성일", "확인·설명일", "확인설명일"),
    "use": ("주용도", "전유부분용도", "전유부용도"),
    "violation": ("위반건축물여부", "위반건축물표시", "위반건축물"),
    "officeNumber": ("중개사무소개설등록번호", "중개사무소등록번호", "개설등록번호"),
    "officeSection": ("등록번호",),
}
FIELD_NAMES = {label: field for field, labels in _LABELS.items() for label in labels}
_FIELD_RE = re.compile(
    r"^\s*(" + "|".join(r"\s*".join(map(re.escape, label)) for label in sorted(FIELD_NAMES, key=len, reverse=True))
    + r")\s*[:：]?\s*(.*?)\s*$"
)
_BUILDING_TITLE = re.compile(r"(?:일반|집합)?건축물대장(?:총괄표제부)?(?:[（(\[].{0,18}[）)\]])?(?:갑|을)?")
_BROKER_TITLE = re.compile(r"중개대상물확인[·ㆍ・.]?설명서(?:\[?[IVⅠⅡⅢ1-4]+\]?)?(?:\(주거용건축물\))?")
_POSITIVE = {"예", "여", "있음", "해당", "해당함", "지정", "위반건축물"}
_NEGATIVE = {"아니오", "부", "없음", "해당없음", "비해당", "아님"}
_UNIT = re.compile(r"(?:제)?([Bb]?\d{1,5}(?:-\d{1,5})?)호(?:실)?$")
_BLOCK = re.compile(r"(?:제)?([가-하A-Za-z]|\d{1,5}(?:-\d{1,5})?)동$")
_USES = re.compile(r"(?:(?:제[12]종)?근린생활시설|단독주택|공동주택|아파트|다가구주택|다세대주택|"
                   r"연립주택|다중주택|오피스텔|업무시설|숙박시설|기숙사|판매시설|교육연구시설|"
                   r"노유자시설|문화및집회시설|제조업소|창고시설|공장|주차장|부대시설|복리시설|[(),/·및])+")
_PRIVATE_FIELD = re.compile(r"(?:소유자|주민등록번호|법인등록번호|성명|전화번호|연락처|휴대폰|이메일|전자우편)\s*[:：]")
_PRIVATE_NUMBER = re.compile(r"(?<!\d)(?:\d{6}[\s\-‐–]?[1-8][\d*]{6}|0\d{1,2}[- ]\d{3,4}[- ]\d{4})(?!\d)")


def _excerpt(field, page, line, raw):
    raw = _PRIVATE_FIELD.split(raw, maxsplit=1)[0].strip()
    safe = _PRIVATE_NUMBER.sub("[개인정보 가림]", raw)
    safe = re.sub(r"[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}", "[이메일 가림]", safe)
    return _evidence(field, page, line, safe)


def _address_parts(value):
    """Keep building and room identifiers separate from street/lot numbers."""
    text = _norm(value).strip()
    unit, block = "", ""
    room = re.search(r"(?:[\s,]+|(?<=동))(?:제\s*)?([Bb]?\d+(?:-\d+)?)\s*호(?:실)?$", text)
    if room:
        unit, text = room[1].upper(), text[:room.start()].strip()
    dong = re.search(r"[\s,]+(?:제\s*)?([가-하A-Za-z]|\d+(?:-\d+)?)\s*동$", text)
    if dong:
        block, text = dong[1].upper(), text[:dong.start()].strip()
    return _address_key(text), block, unit


def _address_status(address, fields, scope):
    expected = _address_parts(address)
    road = bool(re.search(r"(?:로|길)\s*\d", _norm(address)))
    # A 대지위치 (lot address) and a 도로명주소 often coexist on the same form.
    locations = fields["road"] if road and fields["road"] else fields["site"] or fields["road"]
    if not locations:
        return "missing"
    if len({_address_parts(value) for value in locations}) != 1:
        return "different"
    location, block, room = _address_parts(locations[0])
    for field, pattern, present in (("block", _BLOCK, block), ("unit", _UNIT, room)):
        if not fields[field]:
            continue
        values = {m[1].upper() if (m := pattern.fullmatch(_compact(v))) else None for v in fields[field]}
        if len(values) != 1 or None in values or (present and present not in values):
            return "different"
        if field == "block":
            block = values.pop()
        else:
            room = values.pop()
    if (location, block) != expected[:2]:
        return "different"
    if scope == "unit" and (not expected[2] or not room):
        return "different"
    if room == expected[2]:
        return "exact"
    if not room and expected[2] and scope == "building" and _requested_building(address):
        return "whole_building"
    return "different"


def _read_fields(kind, pages):
    fields = {name: [] for name in _LABELS}
    scopes, evidence, record_pages, address_pages = set(), [], set(), set()
    numbered_pages = set()
    for page, rows in enumerate(pages, 1):
        in_subject = False
        for pos, raw in enumerate(rows):
            key = _compact(raw)
            if re.fullmatch(rf"\(?{len(pages)}쪽중제?{page}쪽\)?", key):
                numbered_pages.add(page)
                continue
            title = _BUILDING_TITLE.fullmatch(key) if kind == "building" else _BROKER_TITLE.fullmatch(key)
            if title:
                scope = ("unit" if "전유부" in key else "building" if ("일반" in key or "표제부" in key)
                         else "unspecified")
                scopes.add(scope)
                evidence.append(_excerpt("title", page, pos + 1, raw))
                continue
            if kind == "broker" and "대상물건의표시" in key and len(key) < 18:
                in_subject = True
            if any(word in key for word in ("소유자현황", "중개사무소", "계약당사자", "권리관계")):
                in_subject = False
            if kind == "building" and key in {"[위반건축물]", "(위반건축물)"}:
                fields["violation"].append("지정")
                evidence.append(_excerpt("violation", page, pos + 1, raw))
                record_pages.add(page)
                continue
            if kind == "broker" and _date_in(raw) and re.fullmatch(r"\d{4}년\d{1,2}월\d{1,2}일", key):
                # The official signature date immediately follows the acknowledgement of receipt.
                previous = _compact("".join(rows[max(0, pos - 3):pos]))
                if "수령합니다" in previous and "증명서류" in previous:
                    fields["issuedAt"].append(raw)
                    evidence.append(_excerpt("issuedAt", page, pos + 1, raw))
            match = _FIELD_RE.fullmatch(_norm(raw))
            if not match:
                continue
            field = FIELD_NAMES[_compact(match[1])]
            if field == "siteSection":
                if not in_subject:
                    continue
                field = "site"
            if field == "officeSection":
                if kind != "broker" or "개업공인중개사" not in _compact("".join(rows[max(0, pos - 3):pos])):
                    continue
                field = "officeNumber"
            if field == "officeNumber" and kind != "broker":
                continue
            if field in {"violation", "use"} and kind != "building":
                continue
            value = match[2]
            next_line = False
            if not value and pos + 1 < len(rows):
                candidate = rows[pos + 1].strip()
                if candidate and not _FIELD_RE.fullmatch(_norm(candidate)):
                    value, next_line = candidate, True
            # A split blank label must not capture an owner's personal row as its value.
            if value and (_PRIVATE_FIELD.search(value) or _PRIVATE_NUMBER.search(value)):
                continue
            if field in {"site", "road"} and not re.search(r"[가-힣].*\d", value):
                continue
            if field in {"unit", "block"}:
                pattern = _UNIT if field == "unit" else _BLOCK
                if not pattern.fullmatch(_compact(value)):
                    fields[field].append("")
                    continue
            if field == "issuedAt" and not _date_in(value):
                fields[field].append("")
                continue
            if field == "officeNumber" and not re.fullmatch(r"\d{4,5}-\d{4}-\d{4,6}", _compact(value)):
                continue
            if field == "use" and (len(_compact(value)) > 60 or not _USES.fullmatch(_compact(value))):
                continue
            if field == "violation" and _compact(value) not in _POSITIVE | _NEGATIVE:
                # A bare label, an instruction or unchecked options cannot prove non-violation.
                value, next_line = "", False
            fields[field].append(value)
            evidence.append(_excerpt(field, page, pos + 1, raw))
            if next_line:
                evidence.append(_excerpt(field, page, pos + 2, rows[pos + 1]))
            if field in {"site", "road"}:
                address_pages.add(page)
            if field in {"violation", "officeNumber", "use"}:
                record_pages.add(page)
    single_numbered_form = len(pages) == len(numbered_pages) and 1 in address_pages
    return scopes, fields, evidence, record_pages <= address_pages or single_numbered_form


def read_document_pdf(kind, address, pdf):
    if not isinstance(kind, str) or kind not in {"building", "broker"}:
        raise DocumentRequestError(400, "건축물대장 또는 중개대상물 확인·설명서를 선택해 주세요.")
    if (not isinstance(address, str) or not 5 <= len(address.strip()) <= 220
            or not re.search(r"[가-힣]", address) or not re.search(r"\d", address)
            or any(ord(c) < 32 for c in address)):
        raise DocumentRequestError(400, "동·호를 포함한 점검 주소를 확인해 주세요.")
    if not isinstance(pdf, bytes) or not pdf.startswith(b"%PDF-") or len(pdf) > MAX_PDF_BYTES:
        raise DocumentRequestError(400, "4MB 이하 텍스트 PDF를 선택해 주세요.")
    pages = _pdf_lines(pdf)
    return _analyze(kind, address, pages)


def _analyze(kind, address, pages):
    scopes, fields, evidence, sourced = _read_fields(kind, pages)
    scope = next(iter(scopes)) if len(scopes) == 1 else "unspecified"
    status = _address_status(address, fields, scope)
    dates = {_date_in(raw) for raw in fields["issuedAt"]}
    issued = next(iter(dates)) if len(dates) == 1 else None
    issues, notes, findings = [], [], []
    if not scopes:
        issues.append("원문 제목에서 요청한 종류의 서류를 확인할 수 없습니다.")
    if len(scopes) > 1 or not sourced or len(evidence) > 50:
        issues.append("여러 서류의 항목이 섞였거나 원문 위치가 불분명합니다. 해당 주택의 서류 한 건을 선택해 주세요.")
    if status not in {"exact", "whole_building"}:
        issues.append("서류의 물건 소재지와 점검 주소의 건물·동·호를 대조할 수 없습니다.")
    if status == "whole_building":
        notes.append("건물 단위 서류입니다. 이 호실의 면적과 전유부분은 별도로 확인해 주세요.")
    if not issued or not 0 <= (_today() - date.fromisoformat(issued)).days <= REGISTRY_FRESH_DAYS:
        issues.append(f"핏홈 대조에는 발급·작성일이 표시된 최근 {REGISTRY_FRESH_DAYS}일 이내 자료가 필요합니다.")
    if not issues:
        if kind == "building":
            values = {_compact(v) for v in fields["violation"]}
            if values and (values <= _POSITIVE or values <= _NEGATIVE):
                positive = values <= _POSITIVE
                findings.append({"field": "violation", "label": "위반건축물 표기", "code": "yes" if positive else "no",
                                 "value": "위반건축물로 기재" if positive else "해당 없음으로 기재"})
            else:
                issues.append("위반건축물 여부가 명시된 값을 확인하지 못했습니다. 원문의 표시를 확인해 주세요.")
            uses = {_compact(raw) for raw in fields["use"]}
            if len(uses) == 1:
                findings.append({"field": "use", "label": "대장에 적힌 용도", "value": uses.pop()})
        else:
            numbers = {_compact(raw) for raw in fields["officeNumber"]}
            if len(numbers) == 1:
                findings.append({"field": "officeNumber", "label": "설명서의 사무소 등록번호", "value": numbers.pop()})
            else:
                issues.append("이 설명서에서 하나의 중개사무소 등록번호를 특정할 수 없습니다.")
    if kind == "broker":
        notes.append("등록 영업 상태와 공제 가입 여부는 등록관청·공제기관 확인이 필요합니다.")
    return {"kind": kind, "source": "uploaded_pdf", "status": "needs_review" if issues else "ready",
            "addressMatched": status in {"exact", "whole_building"}, "addressStatus": status,
            "scope": scope, "issuedAt": issued, "findings": findings, "issues": issues,
            "notes": notes, "evidence": evidence[:50]}
