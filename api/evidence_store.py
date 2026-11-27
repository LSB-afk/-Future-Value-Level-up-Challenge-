"""Server-issued evidence IDs that bind values read from a registry document to one property.

The browser keeps only the random ID. A verdict request that presents the ID gets the values the
server read from the document; values or source labels typed in the browser stay "input".
"""
from __future__ import annotations

import hashlib
import json
import re
import secrets
import sqlite3
import time
from contextlib import contextmanager

from document_requests import DocumentRequestError, _address_key, private_db_file

LIFETIME_SECONDS = 7 * 86400
MAX_ROWS = 20000
_TOKEN = re.compile(r"[A-Za-z0-9_-]{43}")
# 제공기관 열람본과 사용자가 올린 PDF를 구분한다. 업로드 PDF는 형식만 대조했고 진위는 확인하지 않았다.
SOURCE_LABEL_KEYS = {"hyphen": "registry", "uploaded_pdf": "registryUpload"}


@contextmanager
def _db():
    conn = sqlite3.connect(private_db_file("evidence.sqlite3"), timeout=5)
    try:
        conn.execute("""CREATE TABLE IF NOT EXISTS evidence (
            key TEXT PRIMARY KEY, kind TEXT NOT NULL, address TEXT NOT NULL,
            document TEXT NOT NULL, detail TEXT NOT NULL, expires INTEGER NOT NULL)""")
        yield conn
    finally:
        conn.close()


def _key(token):
    return hashlib.sha256(token.encode()).hexdigest()


def issue_registry(result, document_hash):
    """Return an evidence ID for a registry reading that passed every automatic check, else None.

    The document hash is kept as an audit record of which file produced the values."""
    if result.get("reviewRequired") is not False or result.get("mortgageMax10k") is None or not result.get("issuedAt"):
        return None
    detail = {"mortgageMax10k": result["mortgageMax10k"], "issuedAt": result["issuedAt"],
              "source": result.get("source") or "uploaded_pdf"}
    token = secrets.token_urlsafe(32)
    now = int(time.time())
    with _db() as conn, conn:
        conn.execute("DELETE FROM evidence WHERE expires <= ?", (now,))
        conn.execute("DELETE FROM evidence WHERE key IN (SELECT key FROM evidence ORDER BY expires DESC LIMIT -1 OFFSET ?)",
                     (MAX_ROWS - 1,))
        conn.execute("INSERT INTO evidence VALUES (?,?,?,?,?,?)",
                     (_key(token), "registry", _address_key(result.get("address") or ""), document_hash,
                      json.dumps(detail), now + LIFETIME_SECONDS))
    return token


def resolve_registry(token, address):
    """(values, None) for a live ID issued for this address, else (None, reason)."""
    if not isinstance(token, str) or not _TOKEN.fullmatch(token):
        return None, "등기 근거 번호 형식이 올바르지 않습니다."
    with _db() as conn:
        row = conn.execute("SELECT address, detail FROM evidence WHERE key=? AND kind='registry' AND expires>?",
                           (_key(token), int(time.time()))).fetchone()
    if row is None:
        return None, "등기 근거가 만료됐거나 없습니다. 등기부를 다시 대조해 주세요."
    if not isinstance(address, str) or row[0] != _address_key(address):
        return None, "다른 주소의 등기 근거입니다."
    return json.loads(row[1]), None


def apply_registry(payload, token):
    """Replace registry amount/date with the server-held reading. Returns (payload, info for the response)."""
    if not token:
        return payload, None
    try:
        values, reason = resolve_registry(token, (payload.get("property") or {}).get("address", ""))
    except (sqlite3.Error, DocumentRequestError, OSError):
        # Fail closed: without the stored reading, typed values stay "input".
        values, reason = None, "등기 근거를 확인하지 못했습니다. 잠시 뒤 다시 시도해 주세요."
    if values is None:
        return payload, {"status": "rejected", "reason": reason}
    registry = dict(payload.get("registry") or {})
    typed_amount, typed_date = registry.get("mortgageMax10k"), registry.get("issuedAt")
    replaced = ((typed_amount not in (None, "") and _as_float(typed_amount) != values["mortgageMax10k"])
                or (typed_date not in (None, "") and typed_date != values["issuedAt"]))
    label = SOURCE_LABEL_KEYS.get(values["source"], "registryUpload")
    registry.update(mortgageMax10k=values["mortgageMax10k"], issuedAt=values["issuedAt"],
                    mortgageSource=label, dateSource=label)
    return {**payload, "registry": registry}, {
        "status": "applied", "source": values["source"], "issuedAt": values["issuedAt"],
        "mortgageMax10k": values["mortgageMax10k"], "replacedTypedValues": replaced}


def _as_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
