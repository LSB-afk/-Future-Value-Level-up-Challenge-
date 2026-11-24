"""Scoped, transient PortOne V2 identity verification receipts for a FitHome report."""
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from http.client import HTTPSConnection, HTTPException
import json
import os
import re
import secrets
from threading import Lock
import time
import unicodedata
from urllib.parse import urlencode

from document_requests import DocumentRequestError


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


def _lookup(payload):
    token = payload.get("challengeToken")
    if not isinstance(token, str) or not re.fullmatch(r"[A-Za-z0-9_-]{43}", token):
        raise IdentityVerificationError(404, "이 매물의 인증 시간이 지났어요. 다시 시작해 주세요.")
    key = sha256(token.encode()).digest()
    entry = _challenges.get(key)
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
            entry.verified_at = verified.astimezone(timezone.utc).isoformat()
            entry.expires = time.time() + VERIFIED_SECONDS
            entry.verification_id = ""
            return _public(entry)
    finally:
        with _guard:
            entry.checking = False
