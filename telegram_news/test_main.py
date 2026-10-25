"""No-network checks for official-headline filtering, message format and 12 slots."""
import unittest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from zoneinfo import ZoneInfo

from main import LABELS, SLOTS, build_message, ensure_private_destination, item, recent, send_message

TZ = ZoneInfo("Europe/Bucharest")


class BotTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 16, 11, 15, tzinfo=TZ)
        self.notice = item("BVB", "BVB: officially confirmed press release",
                           "https://bvb.ro/AboutUs/MediaCenter/PressItem/example/100",
                           self.now - timedelta(hours=1))
        self.fed = item("FED", "Federal Reserve interest rate announcement",
                        "https://www.federalreserve.gov/newsevents/pressreleases/example.htm",
                        self.now - timedelta(hours=1))

    def test_twelve_distinct_nodes_and_fifteen_minute_lead(self):
        self.assertEqual(12, len(SLOTS))
        self.assertEqual({f"N{i:02d}" for i in range(1, 13)},
                         {details[0] for details in SLOTS.values()})
        for _, _, official, advance in SLOTS.values():
            oh, om = map(int, official.split(":"))
            ah, am = map(int, advance.split(":"))
            self.assertEqual(15, (oh * 60 + om) - (ah * 60 + am))

    def test_reject_bad_headlines_and_insecure_urls(self):
        self.assertIsNone(item("BVB", "", "https://bvb.ro", self.now))
        self.assertIsNone(item("BVB", "test", "http://bvb.ro", self.now))
        self.assertIsNone(item("BVB", "test", "https://bvb.ro", None))

    def test_global_dedup_across_nodes(self):
        self.assertEqual([], recent([self.notice], self.now, "N03", {self.notice["id"]: {}}))
        self.assertEqual([self.notice], recent([self.notice], self.now, "N03", {}))

    def test_regional_filter(self):
        self.assertEqual([self.notice],
                         recent([self.notice, self.fed], self.now, "N09", {}))

    def test_radar_ignores_trivial_and_selects_important(self):
        self.assertEqual([self.fed],
                         recent([self.notice, self.fed], self.now, "RADAR", {}))

    def test_expired_headlines_are_suppressed(self):
        old = item("BVB", "old", "https://bvb.ro/old",
                   self.now - timedelta(days=4))
        self.assertEqual([], recent([old], self.now, "N02", {}))

    def test_message_identifies_official_title_without_invented_quote(self):
        txt = build_message("N04", [self.notice], self.now)
        self.assertIn(self.notice["title"], txt)
        self.assertIn(self.notice["url"], txt)
        self.assertIn("10:45", txt)
        self.assertIn("10:30", txt)
        self.assertIn("未接入经验证的实时竞价", txt)

    def test_lesson_is_material_not_automated_role_play(self):
        txt = build_message("N10", [self.fed], self.now)
        self.assertIn("不代表Jonathan课程", txt)


    def test_private_chat_is_accepted(self):
        response = Mock(status_code=200)
        response.json.return_value = {"ok": True, "result": {"id": 12345, "type": "private"}}
        with patch("main.SESSION.post", return_value=response) as call:
            self.assertTrue(ensure_private_destination("token-do-not-log", "12345"))
            self.assertEqual(call.call_count, 1)

    def test_public_or_group_destination_rejected(self):
        response = Mock(status_code=200)
        response.json.return_value = {"ok": True, "result": {"id": -10054, "type": "supergroup"}}
        with patch("main.SESSION.post", return_value=response):
            with self.assertRaisesRegex(RuntimeError, "numeric private chat ID"):
                ensure_private_destination("token-do-not-log", "-10054")
        response.json.return_value = {"ok": True, "result": {"id": 12345, "type": "group"}}
        with patch("main.SESSION.post", return_value=response) as call:
            with self.assertRaisesRegex(RuntimeError, "not a private"):
                ensure_private_destination("token-do-not-log", "12345")
            self.assertEqual(1, call.call_count)

    def test_headline_only_send_cannot_bypass_verified_ledger(self):
        with patch("main.SESSION.post") as call:
            with self.assertRaisesRegex(RuntimeError, "reviewed evidence ledger"):
                send_message("token-do-not-log", "12345", "Official title only")
            call.assert_not_called()

    def test_private_destination_mismatch_is_rejected(self):
        response = Mock(status_code=200)
        response.json.return_value = {"ok": True, "result": {"id": 12346, "type": "private"}}
        with patch("main.SESSION.post", return_value=response):
            with self.assertRaisesRegex(RuntimeError, "ID mismatch"):
                ensure_private_destination("token-do-not-log", "12345")


if __name__ == "__main__":
    unittest.main()

