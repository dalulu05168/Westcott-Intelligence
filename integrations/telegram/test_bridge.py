"""Offline tests: no Telegram network traffic is performed."""
import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(__file__))
import bridge


class TelegramBridgeTests(unittest.TestCase):
    def test_rejects_non_group_destination(self):
        with patch.object(bridge, "call_api", return_value={"id": 3, "type": "private"}):
            with self.assertRaises(bridge.TelegramError):
                bridge.group_target("secret", "3")

    def test_rejects_wrong_group_title(self):
        with patch.object(bridge, "call_api", return_value={
            "id": -10012345, "type": "supergroup", "title": "其他群组"
        }):
            with self.assertRaisesRegex(bridge.TelegramError, "title mismatch"):
                bridge.group_target("secret", "-10012345")

    def test_requires_assistant_heading(self):
        for text in ("", "hello", "===== 先生 =====\nNews"):
            with self.subTest(text=text), self.assertRaises(bridge.TelegramError):
                bridge.validated_message(text)

    def test_utf16_safe_chunks(self):
        source = "😊" * 2500
        parts = list(bridge.chunks(source))
        self.assertEqual(source, "".join(parts))
        self.assertTrue(all(len(p.encode("utf-16-le")) // 2 <= 3900 for p in parts))

    def test_sends_group_and_returns_message_id(self):
        calls = []

        def fake_api(token, method, body=None):
            calls.append((token, method, body))
            if method == "getMe":
                return {"id": 99, "is_bot": True, "username": "NuvexaCheckBot"}
            if method == "getChat":
                return {"id": -10012345, "type": "supergroup", "title": "🌐~~~资讯快报"}
            if method == "sendMessage":
                return {"message_id": 428, "chat": {"id": -10012345}}
            raise AssertionError(method)

        env = {"TELEGRAM_BOT_TOKEN": "secret", "TELEGRAM_CHAT_ID": "-10012345"}
        with patch.object(bridge, "call_api", side_effect=fake_api):
            receipt = bridge.send_group_news("===== 资讯助理 =====\n已核验消息。", env)
        self.assertEqual(receipt["message_ids"], [428])
        self.assertEqual(calls[2][2]["chat_id"], "-10012345")
        self.assertNotIn("parse_mode", calls[2][2])
        self.assertEqual(calls[0][1], "getMe")

    def test_rejects_wrong_bot_username(self):
        with patch.object(bridge, "call_api", return_value={
            "id": 100, "is_bot": True, "username": "WrongBot"
        }):
            with self.assertRaisesRegex(bridge.TelegramError, "username mismatch"):
                bridge.verify_bot_identity("secret")

    def test_accepts_selected_bot_username(self):
        with patch.object(bridge, "call_api", return_value={
            "id": 100, "is_bot": True, "username": "NuvexaCheckBot"
        }):
            account = bridge.verify_bot_identity("secret")
        self.assertEqual(account["username"], "NuvexaCheckBot")

    def test_missing_credentials(self):
        with self.assertRaises(bridge.TelegramError):
            bridge.send_group_news("===== 资讯助理 =====\n测试", {})

    def test_discover_filters_private_chats(self):
        updates = [
            {"message": {"chat": {"id": 123, "type": "private"}}},
            {"message": {"chat": {"id": -1007, "type": "supergroup", "title": "🌐~~~资讯快报"}}},
        ]
        def fake_api(token, method, body=None):
            if method == "getMe":
                return {"id": 99, "is_bot": True, "username": "NuvexaCheckBot"}
            if method == "getUpdates":
                return updates
            raise AssertionError(method)
        with patch.object(bridge, "call_api", side_effect=fake_api):
            found = bridge.discover_groups({"TELEGRAM_BOT_TOKEN": "secret"})
        self.assertEqual([item["chat_id"] for item in found], [-1007])


if __name__ == "__main__":
    unittest.main()
