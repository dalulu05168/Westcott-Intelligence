"""Group transport readiness is not dependent on an unrelated private ID."""
import unittest
from unittest.mock import Mock, patch

from readiness_probe import check_existing_group, valid_existing_group_id


class GroupReadinessTests(unittest.TestCase):
    def test_existing_negative_group_secret_is_valid(self):
        self.assertTrue(valid_existing_group_id("-1001234567890"))
        self.assertFalse(valid_existing_group_id("12345678"))
        self.assertFalse(valid_existing_group_id("@channel"))
        self.assertFalse(valid_existing_group_id(""))

    def test_telegram_must_report_matching_group_title(self):
        good = Mock(ok=True)
        good.json.return_value = {
            "ok": True, "result": {"type": "supergroup", "title": "🌐~~~资讯快报"}}
        with patch("readiness_probe.requests.post", return_value=good):
            self.assertTrue(check_existing_group("secret", "-100123", "🌐~~~资讯快报"))
            self.assertFalse(check_existing_group("secret", "-100123", "资讯快报"))

    def test_a_private_chat_is_not_the_existing_news_group(self):
        item = Mock(ok=True)
        item.json.return_value = {
            "ok": True, "result": {"type": "private", "title": "🌐~~~资讯快报"}}
        with patch("readiness_probe.requests.post", return_value=item):
            self.assertFalse(check_existing_group("secret", "-100123", "🌐~~~资讯快报"))


if __name__ == "__main__":
    unittest.main()
