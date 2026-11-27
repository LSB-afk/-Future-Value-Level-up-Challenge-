"""집주인 서류 제출과 임차인의 원문 근거 확인. PDF 원본은 저장하지 않는다."""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import os
import re
import secrets
import sqlite3
import subprocess
import sys
import threading
import time
import unicodedata
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path


MAX_PDF_BYTES = 4 * 1024 * 1024
REQUEST_LIFETIME = 7 * 86400
MAX_REQUESTS = 1000
PDF_SLOTS = threading.BoundedSemaphore(2)
KINDS = {
    "fixedDate": ("확정일자부여현황", "확정일자부여정보", "선순위임차보증금확인서", "타전세계약체결내역확인서"),
    "moveIn": ("전입세대확인서", "전입세대열람내역"),
    "nationalTax": ("납세증명서", "국세납세증명서"),
    "localTax": ("지방세납세증명",),
}
_STATEMENT_TITLES = {"선순위임차보증금확인서", "타전세계약체결내역확인서"}
_ADDRESS_FIELD = re.compile(r"^\s*(?:소\s*재\s*지(?:\s*주소)?|(?:주택|부동산|건물|물건|대상)\s*(?:의\s*)?"
                            r"(?:소\s*재\s*지|주\s*소)|도로명\s*주소|주\s*소)\s*[:：]?\s*(.*)$")
_PARTIAL = re.compile(r"(?:일부(?:세대|호실|임차|보증금)|(?:세대|호실|보증금)(?:일부|미포함|제외)|"
                      r"(?:부분합계|확인된(?:세대|호실)만|(?:세대|호실)누락))")
_ISSUE_LABEL = r"(?:발급(?:일자|일시|일)|발행(?:일자|일시|일)|교부(?:일자|일시|일)|작성(?:일자|일))"
_EXPIRY_LABEL = r"(?:유효기간(?:의?만료일)?|유효기한|만료일)"
_TOTAL_LABEL = r"(?:선순위(?:임차|임대차)?보증금(?:의)?(?:총액|총계|합계(?:금액)?))"
_BUILDING_SCOPE = r"(?:(?:해당)?(?:건물|주택|다가구)전체|전체(?:건물|주택|세대|호실))"
_SCOPED_TOTAL_LABEL = rf"(?:[\(\[]?{_BUILDING_SCOPE}[)\]]?)?{_TOTAL_LABEL}(?:[\(\[]?{_BUILDING_SCOPE}[)\]]?)?"
_MONEY = re.compile(r"^(?:금)?(?:(\d+(?:\.\d+)?)억)?(?:(\d+(?:\.\d+)?)(천만|백만|십만|만|천)?)?원(?:정)?$")
_DATE = re.compile(r"(?<!\d)((?:19|20)\d\d)\s*(?:[-./]|년)\s*(\d{1,2})\s*(?:[-./]|월)\s*(\d{1,2})(?!\d)")
_UNITS = {"": 1, "천": 1000, "만": 10000, "십만": 100000, "백만": 1000000, "천만": 10000000}
_KST = timezone(timedelta(hours=9))


class DocumentRequestError(ValueError):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status


def _today():
    return datetime.now(_KST).date()


def _norm(value):
    return unicodedata.normalize("NFKC", value)


def _compact(text):
    return "".join(_norm(text).split())


def _address_key(value):
    # A space between numbers separates building and unit identifiers.
    normalized = re.sub(r"(?<=\d)\s+(?=\d)", "|", _norm(value))
    normalized = re.sub(r"^(서울|부산|대구|인천|광주|대전|울산|세종)(?:특별자치시|특별시|광역시|시)?(?=\s)", r"\1 ", normalized)
    return "".join(normalized.split())


def _requested_building(address):
    """Drop only the requested room number; retain the entire lot, building and 동."""
    raw = _norm(address).strip()
    room = re.search(r"(?:[\s,]+|(?<=동))제?\s*[Bb]?\d+(?:-\d+)?\s*호(?:실)?$", raw)
    if not room:
        return None
    base = raw[:room.start()].strip()
    if not re.search(r"(?:로|길|동|리|가)\s+(?:산\s*)?\d+", base):
        return None
    return _address_key(base)


def _fingerprint(secret):
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()


def _invalid_token():
    return DocumentRequestError(404, "서류 요청을 찾을 수 없거나 유효기간이 지났습니다.")


def private_db_file(name):
    """A 0600 SQLite file under the document store, which must stay outside the served repository."""
    root = Path(os.environ.get("FITHOME_DOCUMENT_STORE") or Path.home() / ".fithome" / "document-requests").expanduser().resolve()
    repo = Path(__file__).resolve().parents[1]
    if root == repo or repo in root.parents:
        raise DocumentRequestError(503, "서류 저장 경로를 서비스 공개 폴더 밖에 설정해 주세요.")
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    dbfile = root / name
    with os.fdopen(os.open(dbfile, os.O_RDWR | os.O_CREAT, 0o600), "rb"):
        pass
    return dbfile


@contextmanager
def _db():
    dbfile = private_db_file("requests.sqlite3")
    conn = sqlite3.connect(dbfile, timeout=5)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA foreign_keys=ON")
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS requests (
                id INTEGER PRIMARY KEY, owner TEXT NOT NULL UNIQUE, recipient TEXT NOT NULL UNIQUE,
                address TEXT NOT NULL, requested TEXT NOT NULL, expires INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS documents (
                request_id INTEGER NOT NULL REFERENCES requests(id) ON DELETE CASCADE,
                kind TEXT NOT NULL, fingerprint TEXT NOT NULL, detail TEXT NOT NULL,
                PRIMARY KEY(request_id, kind)
            );
        """)
        with conn:
            conn.execute("DELETE FROM requests WHERE expires <= ?", (int(time.time()),))
        yield conn
    finally:
        conn.close()


def _request(conn, payload, role):
    secret = payload.get(role + "Token")
    if not isinstance(secret, str) or not re.fullmatch(r"[A-Za-z0-9_-]{43}", secret):
        raise _invalid_token()
    column = {"owner": "owner", "recipient": "recipient"}[role]
    row = conn.execute(f"SELECT * FROM requests WHERE {column}=? AND expires>?",
                       (_fingerprint(secret), int(time.time()))).fetchone()
    if row is None:
        raise _invalid_token()
    return row


def _public(row):
    return {"ok": True, "address": row["address"], "requested": json.loads(row["requested"]),
            "expiresAt": datetime.fromtimestamp(row["expires"], timezone.utc).isoformat()}


def _validate_requested(kinds):
    if (not isinstance(kinds, list) or not kinds or len(kinds) > len(KINDS) or
            any(not isinstance(k, str) or k not in KINDS for k in kinds) or len(set(kinds)) != len(kinds)):
        raise DocumentRequestError(400, "요청할 서류 종류를 확인해 주세요.")


def create_request(payload):
    address = payload.get("address")
    kinds = payload.get("requested", list(KINDS))
    if not isinstance(address, str) or not 4 <= len(address.strip()) <= 220 or any(ord(c) < 32 for c in address):
        raise DocumentRequestError(400, "요청할 주택의 전체 주소를 입력해 주세요.")
    _validate_requested(kinds)
    owner, recipient = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    with _db() as conn, conn:
        conn.execute("BEGIN IMMEDIATE")
        if conn.execute("SELECT COUNT(*) FROM requests").fetchone()[0] >= MAX_REQUESTS:
            raise DocumentRequestError(429, "서류 요청을 추가할 수 없습니다. 잠시 후 다시 시도해 주세요.")
        conn.execute("INSERT INTO requests(owner,recipient,address,requested,expires) VALUES(?,?,?,?,?)",
                     (_fingerprint(owner), _fingerprint(recipient), address.strip(), json.dumps(kinds),
                      int(time.time()) + REQUEST_LIFETIME))
        row = _request(conn, {"ownerToken": owner}, "owner")
        return {**_public(row), "ownerToken": owner, "recipientToken": recipient}


def _current_evidence(doc):
    """Recheck documented expiry and FitHome's freshness rule even for accepted evidence."""
    from jeonse_verdict import REGISTRY_FRESH_DAYS

    today = _today()
    issues = []
    if doc.get("expiresOn") and doc["expiresOn"] < today.isoformat():
        issues.append("문서에 표시된 유효기한이 지났습니다.")
    if doc["kind"] == "fixedDate" and doc.get("issuedAt"):
        age = (today - date.fromisoformat(doc["issuedAt"])).days
        if age > REGISTRY_FRESH_DAYS:
            issues.append(f"핏홈은 선순위 변동을 반영하기 위해 최근 {REGISTRY_FRESH_DAYS}일 이내에 발급·작성한 자료를 사용합니다. 새 서류를 요청해 주세요.")
        elif age < 0:
            issues.append("발급일이 미래 날짜입니다.")
    if issues:
        doc["status"] = "needs_review"
        doc["amount10k"] = None
        doc["issues"].extend(issue for issue in issues if issue not in doc["issues"])
    return doc


def _owner_view(conn, row):
    docs = [_current_evidence(json.loads(item[0])) for item in conn.execute(
        "SELECT detail FROM documents WHERE request_id=? ORDER BY kind", (row["id"],))]
    prior = None
    for doc in docs:
        if doc["kind"] == "fixedDate" and doc["status"] == "confirmed":
            prior = doc["amount10k"]
    return {**_public(row), "documents": docs, "priorDeposits10k": prior}


def get_request(payload):
    with _db() as conn:
        return _owner_view(conn, _request(conn, payload, "owner"))


def extend_request(payload):
    additions = payload.get("requested")
    _validate_requested(additions)
    with _db() as conn, conn:
        conn.execute("BEGIN IMMEDIATE")
        row = _request(conn, payload, "owner")
        merged = list(dict.fromkeys([*json.loads(row["requested"]), *additions]))
        conn.execute("UPDATE requests SET requested=? WHERE id=?", (json.dumps(merged), row["id"]))
        return _owner_view(conn, _request(conn, payload, "owner"))


def confirmed_prior(owner_token, address):
    if not isinstance(address, str) or not owner_token:
        return None
    try:
        with _db() as conn:
            row = _request(conn, {"ownerToken": owner_token}, "owner")
            if _address_key(row["address"]) == _address_key(address):
                return _owner_view(conn, row)["priorDeposits10k"]
    except DocumentRequestError as exc:
        if exc.status != 404:
            raise
    return None


def get_recipient(payload):
    with _db() as conn:
        row = _request(conn, payload, "recipient")
        submitted = [r[0] for r in conn.execute("SELECT kind FROM documents WHERE request_id=?", (row["id"],))]
        return {**_public(row), "submitted": submitted}


def _pdf_lines(raw):
    """Run the installed text extractor in a short-lived process. No document is written to disk."""
    if not PDF_SLOTS.acquire(blocking=False):
        raise DocumentRequestError(429, "다른 서류를 읽는 중입니다. 잠시 후 다시 제출해 주세요.")
    try:
        process = subprocess.run([sys.executable, "-I", str(Path(__file__).resolve()), "--pdf-lines"],
                                 input=raw, capture_output=True, timeout=10)
    except subprocess.TimeoutExpired:
        raise DocumentRequestError(422, "제한 시간 안에 읽지 못했습니다. 해당 서류만 담은 PDF로 제출해 주세요.") from None
    finally:
        PDF_SLOTS.release()
    if process.returncode == 3:
        raise DocumentRequestError(503, "서버의 PDF 읽기 모듈을 사용할 수 없습니다.")
    if process.returncode != 0:
        raise DocumentRequestError(422, "PDF를 읽지 못했습니다. 잠금 없는 25쪽 이하의 원본 PDF로 제출해 주세요.")
    return json.loads(process.stdout)


def _extract_worker():
    import resource
    resource.setrlimit(resource.RLIMIT_CPU, (6, 7))
    if sys.platform.startswith("linux"):
        resource.setrlimit(resource.RLIMIT_AS, (768 * 1024 * 1024, 768 * 1024 * 1024))
    try:
        import pymupdf
    except ImportError:
        pymupdf = None
    try:
        raw = sys.stdin.buffer.read(MAX_PDF_BYTES + 1)
        if len(raw) > MAX_PDF_BYTES:
            return 2
        if pymupdf is not None:
            document = pymupdf.open(stream=raw, filetype="pdf")
            if document.needs_pass or not 1 <= len(document) <= 25:
                return 2
            texts = (page.get_text() for page in document)
        else:
            from io import BytesIO
            import pypdf
            import pypdf.filters as filters
            if hasattr(filters, "ZLIB_MAX_OUTPUT_LENGTH"):
                filters.ZLIB_MAX_OUTPUT_LENGTH = 8 * 1024 * 1024
            document = pypdf.PdfReader(BytesIO(raw), strict=False)
            if document.is_encrypted or not 1 <= len(document.pages) <= 25:
                return 2
            texts = (page.extract_text() or "" for page in document.pages)
        pages, count = [], 0
        for content in texts:
            count += len(content)
            if count > 125000:
                return 2
            pages.append(content.splitlines())
        print(json.dumps(pages, ensure_ascii=False))
    except ImportError:
        return 3
    except Exception:
        return 2
    return 0


def _date_in(text):
    hits = _DATE.findall(_norm(text))
    if len(hits) != 1:
        return None
    try:
        return date(*map(int, hits[0])).isoformat()
    except ValueError:
        return None


def _amount_in(value):
    if "," in value and any(not re.fullmatch(r"[0-9]{1,3}(?:,[0-9]{3})+", group)
                            for group in re.findall(r"[0-9,]*,[0-9,]*", value)):
        return None
    raw = value.replace(",", "")
    m = _MONEY.fullmatch(raw)
    if not m or not (m[1] or m[2]):
        return None
    won = Decimal(m[1] or "0") * 100000000 + Decimal(m[2] or "0") * _UNITS[m[3] or ""]
    if won > 10000000000000 or won != int(won):
        return None
    return int(won) / 10000


def _field(line, label):
    matched = re.fullmatch(label + r"\s*[:：]?\s*(.*)", _compact(line))
    return matched[1] if matched else None


def _evidence(field, page, line, text):
    # Retain source lines, not complete certificates or personal register numbers.
    safe = re.sub(r"(?<!\d)\d{6}\s*[-‐–]\s*[1-8]\d{6}(?!\d)", "[개인번호 가림]", text.strip())
    return {"field": field, "page": page, "line": line, "text": safe[:350]}


def _analyze(kind, address, pages):
    evidence, dates, expiries, addresses, amounts, issues = [], [], [], [], [], []
    titles = set()
    entries = []
    notes = []
    partial_total = False
    whole_building = False
    for page_index, lines in enumerate(pages, 1):
        for i, raw in enumerate(lines):
            if not raw.strip():
                continue
            line = _compact(raw)
            for title in KINDS[kind]:
                if title in line and len(line) <= 64 and not (kind == "nationalTax" and "지방세" in line):
                    if title not in titles:
                        evidence.append(_evidence("title", page_index, i + 1, raw))
                    titles.add(title)
            marker = _ADDRESS_FIELD.fullmatch(_norm(raw))
            if marker:
                value = marker[1]
                evidence.append(_evidence("address", page_index, i + 1, raw))
                if not value and i + 1 < len(lines):
                    value = lines[i + 1]
                    evidence.append(_evidence("address", page_index, i + 2, value))
                addresses.append(_address_key(value))
            for key, label, output in (("issuedAt", _ISSUE_LABEL, dates),
                                       ("expiresOn", _EXPIRY_LABEL, expiries)):
                value = _field(raw, label)
                if value is None:
                    continue
                evidence.append(_evidence(key, page_index, i + 1, raw))
                if not value and i + 1 < len(lines):
                    value = _compact(lines[i + 1])
                    evidence.append(_evidence(key, page_index, i + 2, lines[i + 1]))
                output.append(_date_in(value))
            if kind == "fixedDate":
                if _PARTIAL.search(line):
                    partial_total = True
                    evidence.append(_evidence("entry", page_index, i + 1, raw))
                if re.fullmatch(rf"(?:대상범위|산정범위|확인범위|적용범위|범위)[:：]?{_BUILDING_SCOPE}", line):
                    whole_building = True
                    evidence.append(_evidence("scope", page_index, i + 1, raw))
                value = _field(raw, _SCOPED_TOTAL_LABEL)
                if value is not None:
                    if re.search(_BUILDING_SCOPE, line):
                        whole_building = True
                    evidence.append(_evidence("amount", page_index, i + 1, raw))
                    if not value and i + 1 < len(lines):
                        value = _compact(lines[i + 1])
                        evidence.append(_evidence("amount", page_index, i + 2, lines[i + 1]))
                    amounts.append(_amount_in(value))
                elif len(entries) < 8 and (
                    ("보증금" in line and re.search(r"\d.*원", line))
                    or re.fullmatch(r"(?:금)?[\d,억천만백십.]+(?:원(?:정)?)", line)
                    or re.fullmatch(r"\d{1,3}(?:,\d{3}){2,}", line)
                ):
                    entries.append(_evidence("entry", page_index, i + 1, raw))
    evidence.extend(entries)
    if not titles:
        issues.append("문서 제목으로 요청한 서류 종류를 확인할 수 없습니다.")
    expected = _address_key(address)
    # Only an entire address value is accepted. Prefixes, another unit and multiple targets do not match.
    matched = bool(addresses) and all(a == expected for a in addresses)
    address_status = "matched" if matched else ("different" if addresses else "missing")
    building_key = _requested_building(address) if kind == "fixedDate" else None
    building_match = building_key and addresses and all(a == building_key for a in addresses)
    if not matched and building_match and whole_building:
        matched = True
        address_status = "whole_building"
        notes.append("호수를 제외한 건물 주소가 일치하고, 원문에 건물 전체가 산정 범위로 표시되어 있습니다.")
    if kind in {"nationalTax", "localTax"}:
        address_status = "taxpayer_address"
        notes.append("납세증명서 주소는 납세자 주소일 수 있습니다. 임대인과 납세자가 동일한지 원본으로 확인하세요.")
    elif not matched:
        issues.append("호수가 빠진 자료는 해당 건물 전체의 선순위 보증금 합계임을 원문에 명시하고 동·건물번호를 확인해 주세요."
                      if building_match else "요청 주소와 같은 소재지를 원문에서 확인해 주세요.")
    issued = dates[0] if dates and len(set(dates)) == 1 else None
    if not issued or issued > _today().isoformat():
        issues.append("발급일이 없거나 여러 날짜이거나 미래 날짜입니다.")
    expires = expiries[0] if expiries and len(set(expiries)) == 1 else None
    if expiries and (not expires or expires < _today().isoformat() or (issued and expires < issued)):
        issues.append("문서의 유효기한을 확인할 수 없거나 이미 지났습니다.")
    amount = amounts[0] if len(amounts) == 1 else None
    if partial_total:
        issues.append("일부 세대 또는 제외 금액을 나타내는 문구가 있어 건물 전체의 선순위 총액으로 반영할 수 없습니다.")
    if kind == "fixedDate" and amount is None:
        issues.append("선순위 보증금 총액을 한 줄로 확인할 수 없습니다. 개별 계약 행은 합산하지 않습니다.")
    if not any(any(line.strip() for line in page) for page in pages):
        issues.insert(0, "이미지 PDF에서 텍스트를 읽지 못했습니다. 텍스트가 포함된 원본 PDF가 필요합니다.")
    document_type = kind
    if kind == "fixedDate":
        if titles.intersection(_STATEMENT_TITLES):
            document_type = "landlordStatement"
            notes.append("임대인이 제출한 확인서입니다. 공공기관이 선순위 금액을 확인한 자료는 아닙니다.")
        elif titles:
            document_type = "fixedDateRecord"
        if amount is None and entries:
            notes.append("금액이 적힌 원문 행입니다. 각 행의 순위와 현존 여부는 별도로 확인하세요.")
    if len(evidence) > 45:
        issues.append("여러 기록이 섞여 있습니다. 해당 물건의 서류를 따로 제출해 주세요.")
    if issues:
        amount = None
    return _current_evidence({"kind": kind, "documentType": document_type, "notes": notes,
            "status": "needs_review" if issues else "ready", "addressMatched": matched, "addressStatus": address_status,
            "issuedAt": issued, "expiresOn": expires, "amount10k": amount, "issues": issues,
            "evidence": evidence[:45]})


def submit_document(payload):
    kind = payload.get("kind")
    with _db() as conn:
        row = _request(conn, payload, "recipient")
        if kind not in json.loads(row["requested"]):
            raise DocumentRequestError(400, "이 요청에 포함된 서류를 선택해 주세요.")
    data = payload.get("fileBase64")
    if not isinstance(data, str) or len(data) > ((MAX_PDF_BYTES + 2) // 3) * 4:
        raise DocumentRequestError(413, "서류 하나당 4MB 이하 PDF를 제출해 주세요.")
    try:
        raw = base64.b64decode(data, validate=True)
    except (ValueError, binascii.Error):
        raise DocumentRequestError(400, "파일 형식이 올바르지 않습니다.") from None
    if len(raw) > MAX_PDF_BYTES or not raw.startswith(b"%PDF-"):
        raise DocumentRequestError(400, "4MB 이하 PDF 파일을 제출해 주세요.")
    fingerprint = hashlib.sha256(raw).hexdigest()
    with _db() as conn:
        cached = conn.execute("SELECT detail FROM documents WHERE request_id=? AND kind=? AND fingerprint=?",
                              (row["id"], kind, fingerprint)).fetchone()
        if cached:
            return {"ok": True, "kind": kind, "status": _current_evidence(json.loads(cached[0]))["status"]}
    detail = _analyze(kind, row["address"], _pdf_lines(raw))
    detail["fingerprint"] = fingerprint
    with _db() as conn, conn:
        conn.execute("BEGIN IMMEDIATE")
        row = _request(conn, payload, "recipient")
        # Retries of identical documents preserve an owner's confirmation.
        conn.execute("""INSERT INTO documents(request_id,kind,fingerprint,detail) VALUES(?,?,?,?)
                        ON CONFLICT(request_id,kind) DO UPDATE SET fingerprint=excluded.fingerprint,detail=excluded.detail
                        WHERE documents.fingerprint != excluded.fingerprint""",
                     (row["id"], kind, fingerprint, json.dumps(detail, ensure_ascii=False)))
        current = conn.execute("SELECT detail FROM documents WHERE request_id=? AND kind=?", (row["id"], kind)).fetchone()
        return {"ok": True, "kind": kind, "status": _current_evidence(json.loads(current[0]))["status"]}


def review_request(payload):
    with _db() as conn, conn:
        conn.execute("BEGIN IMMEDIATE")
        row = _request(conn, payload, "owner")
        kind, fingerprint = payload.get("kind"), payload.get("fingerprint")
        if not isinstance(kind, str) or kind not in KINDS or not isinstance(fingerprint, str):
            raise DocumentRequestError(400, "확인할 문서를 지정해 주세요.")
        doc = next((d for d in _owner_view(conn, row)["documents"] if d["kind"] == kind), None)
        if not doc or doc["fingerprint"] != fingerprint:
            raise DocumentRequestError(409, "서류가 변경되었습니다. 최신 자료를 다시 확인해 주세요.")
        if doc["status"] not in {"ready", "confirmed"}:
            raise DocumentRequestError(422, "주소·발급일과 필요한 원문을 대조할 수 있는 서류가 필요합니다.")
        doc["status"] = "confirmed"
        conn.execute("UPDATE documents SET detail=? WHERE request_id=? AND kind=?",
                     (json.dumps(doc, ensure_ascii=False), row["id"], kind))
        return _owner_view(conn, row)


def confirmed_tax(owner_token, address):
    """같은 주소 요청에서 국세·지방세 납세증명서를 모두 원문 확인했으면 True."""
    if not isinstance(address, str) or not owner_token:
        return False
    try:
        with _db() as conn:
            row = _request(conn, {"ownerToken": owner_token}, "owner")
            if _address_key(row["address"]) == _address_key(address):
                confirmed = {doc["kind"] for doc in _owner_view(conn, row)["documents"] if doc["status"] == "confirmed"}
                return {"nationalTax", "localTax"} <= confirmed
    except DocumentRequestError as exc:
        if exc.status != 404:
            raise
    return False


if __name__ == "__main__" and sys.argv[1:] == ["--pdf-lines"]:
    raise SystemExit(_extract_worker())
