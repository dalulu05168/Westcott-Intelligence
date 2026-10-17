"""Offline regression checks for the configured Telegram bot identity."""
import unittest
from unittest.mock import patch
from telegram_news import readiness_probe


class Response:
    ok = True

    def __init__(self, username):
        self.username = username

    def json(self):
        return {"ok": True, "result": {"is_bot": True, "username": self.username}}


class TelegramReadinessIdentityTests(unittest.TestCase):
    @patch.object(readiness_probe.requests, "post")
    def test_accepts_selected_zhaocai_bot(self, post):
        post.return_value = Response("ZhaoCai2026Bot")
        self.assertTrue(readiness_probe.check_telegram_identity("dummy", "@ZhaoCai2026Bot"))

    @patch.object(readiness_probe.requests, "post")
    def test_rejects_old_bot_even_with_valid_token(self, post):
        post.return_value = Response("NuvexaCheckBot")
        self.assertFalse(readiness_probe.check_telegram_identity("dummy", "ZhaoCai2026Bot"))

    @patch.object(readiness_probe.requests, "post")
    def test_default_identity_uses_configured_bot(self, post):
        post.return_value = Response("ZhaoCai2026Bot")
        with patch.dict("os.environ", {"TELEGRAM_EXPECTED_BOT_USERNAME": "ZhaoCai2026Bot"}):
            self.assertTrue(readiness_probe.check_telegram_identity("dummy"))


if __name__ == "__main__":
    unittest.main()
