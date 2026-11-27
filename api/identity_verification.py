"""Scoped, transient PortOne V2 identity verification receipts for a FitHome report."""
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from http.client import HTTPSConnection, HTTPException
import json
import os
import re
import secrets
import sqlite3
from threading import Lock
import time
import unicodedata
from urllib.parse import urlencode

from document_requests import DocumentRequestError, private_db_file


PENDING_SECONDS = 600
VERIFIED_SECONDS = 3600
_guard = Lock()
_challenges = {}


class IdentityVerificationError(DocumentRequestError):
    pass


@dataclass
class _Challenge:
    scope: str
    verification_id: str
    expires: float
    started: float
    verified_at: str = ""
    checking: bool = False


def _config():
    return tuple(os.environ.get("FITHOME_PORTONE_" + suffix, "").strip()
                 for suffix in ("STORE_ID", "CHANNEL_KEY", "API_SECRET"))


def _scope(payload):
    fields = []
    for name in ("reportKey", "address"):
        value = payload.get(name)
        if not isinstance(value, str) or not 1 <= len(value.strip()) <= 256 or "\x00" in value:
            raise IdentityVerificationError(400, "점검 중인 매물의 주소를 확인해 주세요.")
        fields.append(unicodedata.normalize("NFC", " ".join(value.split())))
    return sha256("\x00".join(fields).encode()).hexdigest()


@contextmanager
def _db():
    # 서버 재시작·다중 워커에서도 인증 완료를 유지한다. 해시된 토큰·매물 범위·완료 시각만 남긴다.
    conn = sqlite3.connect(private_db_file("access.sqlite3"), timeout=5)
    try:
        conn.execute("""CREATE TABLE IF NOT EXISTS identity_receipts (
            key TEXT PRIMARY KEY, scope TEXT NOT NULL, verified_at TEXT NOT NULL, expires REAL NOT NULL)""")
        yield conn
    finally:
        conn.close()


def _token_key(payload):
    token = payload.get("challengeToken")
    if not isinstance(token, str) or not re.fullmatch(r"[A-Za-z0-9_-]{43}", token):
        raise IdentityVerificationError(404, "이 매물의 인증 시간이 지났어요. 다시 시작해 주세요.")
    return sha256(token.encode()).digest()


def _stored(key):
    try:
        with _db() as conn:
            row = conn.execute("SELECT scope, verified_at, expires FROM identity_receipts WHERE key=? AND expires>?",
                               (key.hex(), time.time())).fetchone()
    except (sqlite3.Error, OSError):
        raise IdentityVerificationError(503, "인증 기록을 확인하지 못했어요. 잠시 후 다시 시도해 주세요.") from None
    return _Challenge(row[0], "", row[2], 0, row[1]) if row else None


def _save(key, entry):
    try:
        with _db() as conn, conn:
            conn.execute("DELETE FROM identity_receipts WHERE expires <= ?", (time.time(),))
            conn.execute("INSERT OR REPLACE INTO identity_receipts VALUES (?,?,?,?)",
                         (key.hex(), entry.scope, entry.verified_at, entry.expires))
    except (sqlite3.Error, OSError):
        raise IdentityVerificationError(503, "인증 결과를 저장하지 못했어요. 잠시 후 다시 확인해 주세요.") from None


def _lookup(payload):
    key = _token_key(payload)
    entry = _challenges.get(key) or _stored(key)
    if entry is None or entry.scope != _scope(payload) or entry.expires <= time.time():
        raise IdentityVerificationError(404, "이 매물의 인증 시간이 지났어요. 다시 시작해 주세요.")
    return entry


def _public(entry):
    return {"available": True, "status": "verified" if entry.verified_at else "pending",
            "expiresAt": datetime.fromtimestamp(entry.expires, timezone.utc).isoformat(),
            "verifiedAt": entry.verified_at or None}


def identity_status(payload):
    if not all(_config()):
        return {"available": False, "status": "unavailable", "reason": "본인인증 기관이 아직 연결되지 않았어요."}
    if not payload.get("challengeToken"):
        return {"available": True, "status": "unverified"}
    with _guard:
        return _public(_lookup(payload))


def start_verification(payload):
    store, channel, secret = _config()
    if not (store and channel and secret):
        raise IdentityVerificationError(503, "본인인증 기관이 아직 연결되지 않았어요.")
    if payload.get("consent") is not True:
        raise IdentityVerificationError(400, "인증 요청에 동의한 뒤 진행해 주세요.")
    scope = _scope(payload)
    token = secrets.token_urlsafe(32)
    now = time.time()
    entry = _Challenge(scope, "FH" + secrets.token_hex(16), now + PENDING_SECONDS, now)
    with _guard:
        for key in [key for key, row in _challenges.items() if row.expires <= now]:
            del _challenges[key]
        if len(_challenges) >= 2048:
            raise IdentityVerificationError(429, "인증 요청이 많아요. 잠시 후 다시 시도해 주세요.")
        _challenges[sha256(token.encode()).digest()] = entry
    return {**_public(entry), "challengeToken": token,
            "sdk": {"storeId": store, "channelKey": channel, "identityVerificationId": entry.verification_id}}


def _provider_lookup(verification_id, store, secret):
    connection = HTTPSConnection("api.portone.io", timeout=8)
    try:
        path = "/identity-verifications/" + verification_id + "?" + urlencode({"storeId": store})
        connection.request("GET", path, headers={"Authorization": "PortOne " + secret, "Accept": "application/json"})
        response = connection.getresponse()
        if response.status == 404:
            return {"status": "READY"}
        if response.status != 200:
            raise IdentityVerificationError(502, "인증 기관의 결과를 불러오지 못했어요. 잠시 후 다시 확인해 주세요.")
        raw = response.read(131073)
        if len(raw) > 131072:
            raise ValueError
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise ValueError
        # Only these non-personal fields survive the HTTP result.
        return {field: data.get(field) for field in ("id", "status", "channel", "verifiedAt")}
    except (HTTPException, OSError, ValueError) as exc:
        if isinstance(exc, IdentityVerificationError):
            raise
        raise IdentityVerificationError(502, "인증 기관의 응답을 확인할 수 없어요.") from None
    finally:
        connection.close()


def confirm_verification(payload):
    store, channel, secret = _config()
    if not (store and channel and secret):
        raise IdentityVerificationError(503, "본인인증 기관이 아직 연결되지 않았어요.")
    with _guard:
        entry = _lookup(payload)
        if entry.verified_at or entry.checking:
            return _public(entry)
        entry.checking = True
    try:
        result = _provider_lookup(entry.verification_id, store, secret)
        with _guard:
            _lookup(payload)  # Recheck expiry after the remote call.
            if result.get("status") == "READY":
                return _public(entry)
            if result.get("status") == "FAILED":
                entry.expires = 0
                raise IdentityVerificationError(409, "인증이 완료되지 않았어요. 새로 시작해 주세요.")
            selected = result.get("channel")
            if (result.get("status") != "VERIFIED" or result.get("id") != entry.verification_id
                    or not isinstance(selected, dict) or selected.get("key") != channel or selected.get("type") != "LIVE"):
                raise IdentityVerificationError(422, "연결한 운영 채널의 인증 결과를 확인할 수 없어요.")
            try:
                verified = datetime.fromisoformat(result["verifiedAt"].replace("Z", "+00:00"))
                if verified.tzinfo is None or not entry.started - 60 <= verified.timestamp() <= time.time() + 60:
                    raise ValueError
            except (KeyError, AttributeError, ValueError, OSError, OverflowError):
                raise IdentityVerificationError(422, "기관의 인증 완료 시각을 확인할 수 없어요.") from None
            done = _Challenge(entry.scope, "", time.time() + VERIFIED_SECONDS, entry.started,
                              verified.astimezone(timezone.utc).isoformat())
            key = _token_key(payload)
            _save(key, done)  # 저장하지 못하면 대기 상태로 남겨 다시 확인할 수 있게 한다.
            _challenges.pop(key, None)
            return _public(done)
    finally:
        with _guard:
            entry.checking = False


def require_verified(payload):
    """본인인증 기관이 연결된 서버에서는 같은 매물 범위(reportKey+address)의 인증 완료를 요구한다."""
    if not all(_config()):
        return
    try:
        with _guard:
            entry = _lookup(payload)
    except IdentityVerificationError as exc:
        if exc.status == 503:
            raise
        entry = None
    if entry is None or not entry.verified_at:
        raise IdentityVerificationError(403, "이 매물에 대한 신청자 본인인증을 먼저 완료해 주세요.")
