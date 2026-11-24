import json
from datetime import datetime, timezone
import os
import unittest
from unittest.mock import Mock, patch

import identity_verification as identity


SCOPE = {"reportKey": "listing:fithome-fixture", "address": "대전광역시 예시로 10"}
CONFIG = {"FITHOME_PORTONE_STORE_ID": "store-test", "FITHOME_PORTONE_CHANNEL_KEY": "channel-key-test",
          "FITHOME_PORTONE_API_SECRET": "not-a-real-key"}


class IdentityTest(unittest.TestCase):
    def setUp(self):
        env = patch.dict(os.environ, CONFIG)
        env.start()
        self.addCleanup(env.stop)
        identity._challenges.clear()
        self.addCleanup(identity._challenges.clear)

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
