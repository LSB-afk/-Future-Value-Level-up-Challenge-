import json
from datetime import datetime, timezone
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import identity_verification as identity


SCOPE = {"reportKey": "listing:fithome-fixture", "address": "대전광역시 예시로 10"}
CONFIG = {"FITHOME_PORTONE_STORE_ID": "store-test", "FITHOME_PORTONE_CHANNEL_KEY": "channel-key-test",
          "FITHOME_PORTONE_API_SECRET": "not-a-real-key"}


class IdentityTest(unittest.TestCase):
    def setUp(self):
        self.store = self.enterContext(tempfile.TemporaryDirectory())
        env = patch.dict(os.environ, {**CONFIG, "FITHOME_DOCUMENT_STORE": self.store})
        env.start()
        self.addCleanup(env.stop)
        identity._challenges.clear()
        self.addCleanup(identity._challenges.clear)

    def verified(self, scope=SCOPE):
        start = identity.start_verification({**scope, "consent": True})
        request = {**scope, "challengeToken": start["challengeToken"]}
        with patch.object(identity, "_provider_lookup", return_value=self.response(start)):
            self.assertEqual(identity.confirm_verification(request)["status"], "verified")
        return request

    def test_completed_receipt_survives_restart_without_personal_fields(self):
        request = self.verified()
        identity._challenges.clear()  # 서버 재시작·다른 워커와 같다.
        self.assertEqual(identity.identity_status(request)["status"], "verified")
        identity.require_verified(request)
        stored = b"".join(path.read_bytes() for path in Path(self.store).iterdir())
        for secret in ("never-retain", "테스트 신청자",request["challengeToken"], SCOPE["address"]):
            self.assertNotIn(secret.encode(), stored)

    def test_gate_requires_same_scope_unexpired_completed_receipt(self):
        request = self.verified()
        for mutation in ({"reportKey": "listing:other"}, {"address": SCOPE["address"] + " 2호"},
                         {"challengeToken": None}, {"reportKey": None}):
            with self.assertRaises(identity.IdentityVerificationError) as caught:
                identity.require_verified({**request, **mutation})
            self.assertEqual(caught.exception.status, 403)
        _, pending = self.prepare()
        with self.assertRaises(identity.IdentityVerificationError) as caught:
            identity.require_verified(pending)
        self.assertEqual(caught.exception.status, 403)
        identity._challenges.clear()
        with patch.object(identity.time, "time", return_value=identity.time.time() + identity.VERIFIED_SECONDS + 1):
            with self.assertRaises(identity.IdentityVerificationError) as caught:
                identity.require_verified(request)
        self.assertEqual(caught.exception.status, 403)

    def test_gate_is_open_when_provider_is_not_connected(self):
        with patch.dict(os.environ, {"FITHOME_PORTONE_API_SECRET": ""}):
            self.assertIsNone(identity.require_verified({}))

    def prepare(self):
        start = identity.start_verification({**SCOPE, "consent": True})
        return start, {**SCOPE, "challengeToken": start["challengeToken"]}

    def response(self, start):
        return {"status": "VERIFIED", "id": start["sdk"]["identityVerificationId"],
                "verifiedAt": datetime.now(timezone.utc).isoformat(),
                "channel": {"type": "LIVE", "key": CONFIG["FITHOME_PORTONE_CHANNEL_KEY"]},
                "verifiedCustomer": {"name": "테스트 신청자", "ci": "never-retain"}}

    def test_requires_configuration_and_consent(self):
        with self.assertRaises(identity.IdentityVerificationError):
            identity.start_verification(SCOPE)
        with patch.dict(os.environ, {"FITHOME_PORTONE_API_SECRET": ""}):
            self.assertEqual(identity.identity_status(SCOPE)["status"], "unavailable")
            with self.assertRaises(identity.IdentityVerificationError):
                self.prepare()
        self.assertFalse(identity._challenges)

    def test_only_server_owned_transaction_and_scoped_token_works(self):
        start, request = self.prepare()
        self.assertRegex(start["sdk"]["identityVerificationId"], "^[A-Za-z0-9]{1,40}$")
        self.assertNotIn("not-a-real-key", str(start))
        self.assertNotIn("address", start["sdk"])
        with patch.object(identity, "_provider_lookup", return_value=self.response(start)) as provider:
            for mutation in ({"reportKey": "another"}, {"address": SCOPE["address"] + " 2호"}, {"challengeToken": "other"}):
                with self.assertRaises(identity.IdentityVerificationError):
                    identity.confirm_verification({**request, **mutation})
            provider.assert_not_called()
            result = identity.confirm_verification({**request, "status": "VERIFIED", "identityVerificationId": "forged"})
            self.assertEqual(result["status"], "verified")
            self.assertEqual(identity.confirm_verification(request), result)
            self.assertEqual(identity.identity_status(request), result)
            provider.assert_called_once_with(start["sdk"]["identityVerificationId"], CONFIG["FITHOME_PORTONE_STORE_ID"],
                                             CONFIG["FITHOME_PORTONE_API_SECRET"])
            self.assertNotIn("never-retain", str(result) + repr(identity._challenges))
            self.assertNotIn(start["sdk"]["identityVerificationId"], repr(identity._challenges))

    def test_completed_test_wrong_channel_and_wrong_id_do_not_verify(self):
        start, request = self.prepare()
        fixture = self.response(start)
        for mutation in ({"channel": {"type": "TEST", "key": CONFIG["FITHOME_PORTONE_CHANNEL_KEY"]}},
                         {"channel": {"type": "LIVE", "key": "other"}}, {"id": "other"}, {"verifiedAt": "2000-01-01T01:00:00Z"}):
            with patch.object(identity, "_provider_lookup", return_value={**fixture, **mutation}):
                with self.assertRaises(identity.IdentityVerificationError):
                    identity.confirm_verification(request)
            self.assertEqual(identity.identity_status(request)["status"], "pending")

    def test_timeout_retry_then_terminal_failure_and_expired_receipt(self):
        start, request = self.prepare()
        responses = [identity.IdentityVerificationError(502, "기관 오류"), {"status": "READY"}, {"status": "FAILED"}]
        with patch.object(identity, "_provider_lookup", side_effect=responses):
            with self.assertRaises(identity.IdentityVerificationError):
                identity.confirm_verification(request)
            self.assertEqual(identity.confirm_verification(request)["status"], "pending")
            with self.assertRaises(identity.IdentityVerificationError):
                identity.confirm_verification(request)
        with self.assertRaises(identity.IdentityVerificationError):
            identity.identity_status(request)
        _, fresh = self.prepare()
        with patch.object(identity.time, "time", return_value=identity.time.time() + identity.PENDING_SECONDS + 1):
            with self.assertRaises(identity.IdentityVerificationError):
                identity.confirm_verification(fresh)

    def test_api_uses_configured_store_and_never_returns_personal_fields(self):
        start, _ = self.prepare()
        provider_result = self.response(start)
        reply = Mock(status=200)
        reply.read.return_value = json.dumps(provider_result).encode()
        with patch.object(identity, "HTTPSConnection") as connection:
            connection.return_value.getresponse.return_value = reply
            result = identity._provider_lookup(provider_result["id"], "store-test", "secret")
            connection.return_value.request.assert_called_once_with(
                "GET", "/identity-verifications/" + provider_result["id"] + "?storeId=store-test",
                headers={"Authorization": "PortOne secret", "Accept": "application/json"})
            self.assertNotIn("verifiedCustomer", result)
            self.assertNotIn("never-retain", str(result))
            connection.return_value.close.assert_called_once()
