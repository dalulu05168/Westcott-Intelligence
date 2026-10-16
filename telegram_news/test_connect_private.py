"""Prevent accidental use of the existing Telegram group Chat ID in private tests."""
import os
import unittest
from unittest.mock import patch

import connect_private


class PrivateSecretIsolationTests(unittest.TestCase):
    def test_missing_new_private_secret_cannot_fallback_to_group(self):
        env = {
            "TELEGRAM_BOT_TOKEN": "sample-token",
            "TELEGRAM_CHAT_ID": "-1001234567890",
            "CONNECT_MODE": "test",
        }
        with patch.dict(os.environ, env, clear=True), patch.object(
                connect_private, "api", return_value={"username": "NuvexaCheckBot"}):
            with self.assertRaisesRegex(RuntimeError, "TELEGRAM_PRIVATE_CHAT_ID"):
                connect_private.main()

    def test_private_test_uses_only_new_numeric_secret(self):
        env = {
            "TELEGRAM_BOT_TOKEN": "sample-token",
            "TELEGRAM_CHAT_ID": "-1001234567890",
            "TELEGRAM_PRIVATE_CHAT_ID": "12345678",
            "CONNECT_MODE": "test",
        }
        with patch.dict(os.environ, env, clear=True), patch.object(
                connect_private, "api", return_value={"username": "NuvexaCheckBot"}), patch.object(
                connect_private, "ensure_private_destination", return_value=True) as verify, patch.object(
                connect_private, "send_message", return_value=99) as send:
            connect_private.main()
            verify.assert_called_once_with("sample-token", "12345678")
            self.assertEqual(send.call_args.args[1], "12345678")

    def test_private_test_rejects_wrong_target_type_before_message(self):
        env = {
            "TELEGRAM_BOT_TOKEN": "sample-token",
            "TELEGRAM_CHAT_ID": "-1001234567890",
            "TELEGRAM_PRIVATE_CHAT_ID": "12345678",
            "CONNECT_MODE": "test",
        }
        with patch.dict(os.environ, env, clear=True), patch.object(
                connect_private, "api", return_value={"username": "NuvexaCheckBot"}), patch.object(
                connect_private, "ensure_private_destination", side_effect=RuntimeError("not private")), patch.object(
                connect_private, "send_message") as send:
            with self.assertRaisesRegex(RuntimeError, "not private"):
                connect_private.main()
            send.assert_not_called()


if __name__ == "__main__":
    unittest.main()
