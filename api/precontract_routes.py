"""Private, same-origin JSON endpoints for the precontract document workflow."""
from __future__ import annotations

import base64
import binascii
import hmac
import os
from http import HTTPStatus
from ipaddress import ip_address
from urllib.parse import urlsplit


PREFIXES = ("/api/document-requests/", "/api/registry/", "/api/document-checks/", "/api/identity/", "/api/building-register/")
UPLOAD_PATHS = {"/api/registry/upload", "/api/document-requests/submit", "/api/document-checks/read"}
MAX_UPLOAD_JSON = 6 * 1024 * 1024
MAX_PDF_BYTES = 4 * 1024 * 1024


def private_api(path):
    return path.startswith(PREFIXES) or path == "/api/jeonse-verdict"


def accepts_json(handler):
    # A cross-site HTML form must never be able to submit a file or trigger a fee.
    if handler.headers.get_content_type() != "application/json":
        handler.send_json(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, {"ok": False, "error": "JSON 요청이 필요합니다."})
        return False
    origin = handler.headers.get("Origin")
    valid_origin = True
    if origin:
        try:
            parsed = urlsplit(origin)
            valid_origin = parsed.scheme in {"http", "https"} and parsed.netloc == handler.headers.get("Host")
        except ValueError:
            valid_origin = False
    if not valid_origin or handler.headers.get("Sec-Fetch-Site") == "cross-site":
        handler.send_json(HTTPStatus.FORBIDDEN, {"ok": False, "error": "핏홈 화면에서 다시 요청해 주세요."})
        return False
    return True


def read_pdf(payload):
    encoded = payload.get("fileBase64")
    if not isinstance(encoded, str) or len(encoded) > ((MAX_PDF_BYTES + 2) // 3) * 4:
        raise ValueError("4MB 이하 PDF 파일을 선택해 주세요.")
    try:
        pdf = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("PDF 파일을 읽을 수 없습니다.") from exc
    if len(pdf) > MAX_PDF_BYTES or not pdf.startswith(b"%PDF-"):
        raise ValueError("4MB 이하 PDF 파일을 선택해 주세요.")
    return pdf


def _provider_access(handler, token_env, header):
    # This prototype has no merchant/customer authentication to authorize provider fees.
    # Never spend the configured merchant balance through a publicly reachable endpoint.
    gateway_key = os.environ.get(token_env)
    if gateway_key and hmac.compare_digest(gateway_key.encode(), handler.headers.get(header, "").encode()):
        return True
    host = urlsplit("//" + handler.headers.get("Host", "")).hostname
    return (ip_address(handler.client_address[0]).is_loopback and host in {"localhost", "127.0.0.1", "::1"}
            and not any(handler.headers.get(name) for name in ("Forwarded", "X-Forwarded-For", "X-Forwarded-Host")))


def handle_post(handler, path):
    from document_requests import (DocumentRequestError, create_request, get_recipient,
                                   get_request, review_request, submit_document)
    from registry_lookup import RegistryError, fetch_registry, read_registry_pdf, registry_status, search_registry

    document_routes = {
        "/api/document-requests/create": create_request,
        "/api/document-requests/recipient": get_recipient,
        "/api/document-requests/status": get_request,
        "/api/document-requests/submit": submit_document,
        "/api/document-requests/review": review_request,
    }

    try:
        if not accepts_json(handler):
            return
        limit = MAX_UPLOAD_JSON if path in UPLOAD_PATHS else 64 * 1024
        payload = handler.read_json_body(max_bytes=limit)
        if path in document_routes:
            result = document_routes[path](payload)
        elif path == "/api/document-requests/extend":
            from document_requests import extend_request
            result = extend_request(payload)
        elif path == "/api/document-checks/read":
            from document_checks import read_document_pdf
            result = read_document_pdf(payload.get("kind"), payload.get("address"), read_pdf(payload))
        elif path in {"/api/building-register/status", "/api/building-register/lookup"}:
            from building_register import building_status, lookup_building
            result = building_status() if path.endswith("/status") else lookup_building(payload.get("address"))
        elif path in {"/api/identity/status", "/api/identity/start", "/api/identity/confirm"}:
            from identity_verification import identity_status, start_verification, confirm_verification
            if not _provider_access(handler, "FITHOME_IDENTITY_GATEWAY_TOKEN", "X-FitHome-Identity-Gateway"):
                reason = "이 서버에는 본인확인기관이 연결되어 있지 않습니다."
                if path != "/api/identity/status":
                    handler.send_json(HTTPStatus.FORBIDDEN, {"ok": False, "error": reason})
                    return
                result = {"available": False, "status": "unavailable", "reason": reason}
            else:
                identity_routes = {"/api/identity/status": identity_status, "/api/identity/start": start_verification,
                                   "/api/identity/confirm": confirm_verification}
                result = identity_routes[path](payload)
        elif path == "/api/registry/upload":
            result = read_registry_pdf(payload.get("address", ""), read_pdf(payload))
        elif path in {"/api/registry/status", "/api/registry/search", "/api/registry/fetch"}:
            if not _provider_access(handler, "FITHOME_REGISTRY_GATEWAY_TOKEN", "X-FitHome-Gateway"):
                reason = "이 서버에서 유료 등기 조회를 사용할 수 없습니다. 등기 PDF를 제출할 수 있습니다."
                if path != "/api/registry/status":
                    handler.send_json(HTTPStatus.FORBIDDEN, {"ok": False, "error": reason})
                    return
                result = {"available": False, "provider": "Hyphen", "reason": reason}
            elif path == "/api/registry/status":
                result = registry_status()
            elif path == "/api/registry/search":
                result = search_registry(payload.get("address", ""))
            else:
                result = fetch_registry(payload.get("address", ""), payload.get("propertyId", ""),
                                        confirm_charge=payload.get("confirmCharge") is True)
        else:
            handler.send_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "지원하지 않는 서류 요청입니다."})
            return
        handler.send_json(HTTPStatus.OK, {"ok": True, **result})
    except DocumentRequestError as exc:
        handler.send_json(exc.status, {"ok": False, "error": str(exc)})
    except RegistryError as exc:
        handler.send_json(exc.http_status, {"ok": False, "error": str(exc)})
    except (ValueError, TypeError, RecursionError):
        handler.send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": "주소와 파일 형식을 확인해 주세요."})
    except (BrokenPipeError, ConnectionResetError):
        return
    except Exception:
        # Token, document text and provider payloads must not be exposed in diagnostics.
        handler.send_json(HTTPStatus.INTERNAL_SERVER_ERROR,
                          {"ok": False, "error": "서류를 처리하지 못했습니다. 잠시 후 다시 시도해 주세요."})
