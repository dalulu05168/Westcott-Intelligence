"""Offline publishing tests: no real Telegram or GitHub side effects."""
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
import unittest

sys.path.insert(0, os.path.dirname(__file__))
import bridge
import image_background
import reviewed_publish as pub


class NewsImageTests(unittest.TestCase):
    def test_dimensions_and_no_text_rendering(self):
        from PIL import Image
        from io import BytesIO
        for topic in image_background.TOPICS:
            with self.subTest(topic=topic):
                data = image_background.render_background(topic)
                result = Image.open(BytesIO(data))
                self.assertEqual(result.size, (1600, 900))
                self.assertEqual(result.format, "PNG")

    def test_topic_matches_evidence_and_mixed_news(self):
        self.assertEqual(image_background.select_topic(["WTI原油公布新的价格"]), "energy")
        self.assertEqual(image_background.select_topic(["半导体和人工智能芯片"]), "technology")
        self.assertEqual(image_background.select_topic(["能源与银行股票"]), "global")
        self.assertEqual(image_background.select_topic(["没有行情信息"]), "global")


class ReviewedPublicationTests(unittest.TestCase):
    def make_ledger(self):
        now = datetime.now(timezone.utc).isoformat()
        return {
            "event_id": "verified-news-00001",
            "executed_at": now,
            "sources": {
                "s1": {"url": "https://example.org/report", "access_status": "BODY_READ",
                       "source_type": "official", "origin_id": "agency",
                       "retrieved_at": now, "published_at": now},
            },
            "claims": [
                {"id": "c1", "text": "已核实原油市场公告。", "kind": "fact",
                 "review_status": "CONFIRMED", "reviewed_by": "human",
                 "evidence": [{"source_id": "s1", "excerpt": "已核实原油市场公告。",
                               "locator": "section 1", "supports_exact_claim": True}],
                 "numbers": []}
            ],
            "publish_claim_ids": ["c1"]
        }

    def test_prepare_needs_gate_and_uses_approved_facts(self):
        ledger = self.make_ledger()
        prepared = pub.prepare(ledger, "news/approved/reviewed.json")
        self.assertEqual(prepared["topic"], "energy")
        self.assertTrue(prepared["text"].startswith("===== 资讯助理 =====\n"))
        self.assertIn("https://example.org/report", prepared["text"])
        self.assertIn("c1", prepared["claim_ids"])

    def test_blocks_unreviewed_and_missing_ids(self):
        ledger = self.make_ledger()
        ledger["claims"][0]["review_status"] = "UNVERIFIED"
        with self.assertRaises(pub.PublicationError):
            pub.prepare(ledger, "news/approved/reviewed.json")
        ledger = self.make_ledger()
        ledger["publish_claim_ids"] = ["unknown"]
        with self.assertRaises(pub.PublicationError):
            pub.prepare(ledger, "news/approved/reviewed.json")

    def test_blocks_invalid_path_and_stale_review(self):
        ledger = self.make_ledger()
        with self.assertRaises(pub.PublicationError):
            pub.prepare(ledger, "../../secret.json")
        with self.assertRaises(pub.PublicationError):
            pub.prepare(ledger, "news/approved/reviewed.json",
                        now=datetime(2030, 1, 1, tzinfo=timezone.utc))

    def test_fingerprint_is_stable_across_event_renaming(self):
        ledger = self.make_ledger()
        one = pub.prepare(ledger, "news/approved/reviewed.json")
        ledger["event_id"] = "verified-news-00002"
        two = pub.prepare(ledger, "news/approved/reviewed.json")
        self.assertEqual(one["fingerprint"], two["fingerprint"])

    def test_publish_requires_confirmation_before_reserving(self):
        p = pub.prepare(self.make_ledger(), "news/approved/reviewed.json")
        with patch.object(pub, "reserve") as reserve:
            with self.assertRaises(pub.PublicationError):
                pub.publish(p, b"image", {})
            reserve.assert_not_called()

    def test_pending_reservation_is_not_rolled_back_after_uncertain_send(self):
        p = pub.prepare(self.make_ledger(), "news/approved/reviewed.json")
        env = {"PUBLISH_CONFIRMATION": pub.CONFIRM}
        with patch.object(pub, "reserve", return_value=("audit/test.json", {}, "sha")):
            with patch.object(pub, "send_group_news_with_image", side_effect=RuntimeError("network")):
                with self.assertRaisesRegex(pub.PublicationError, "uncertain"):
                    pub.publish(p, b"image", env)

    def test_success_receipts_record_photo_and_text_ids(self):
        p = pub.prepare(self.make_ledger(), "news/approved/reviewed.json")
        env = {"PUBLISH_CONFIRMATION": pub.CONFIRM,
               "GITHUB_TOKEN": "secret", "GITHUB_REPOSITORY": "owner/repo"}
        with patch.object(pub, "reserve", return_value=("audit/test.json", {"event_id":"verified-news-00001"}, "sha")):
            with patch.object(pub, "send_group_news_with_image",
                              return_value={"group_title": "资讯快报",
                                            "photo_message_id": 21,
                                            "message_ids": [22]}):
                with patch.object(pub, "github_write", return_value="next") as write:
                    receipt = pub.publish(p, b"image", env)
        self.assertEqual(receipt["photo_message_id"], 21)
        self.assertEqual(receipt["message_ids"], [22])
        self.assertEqual(write.call_args.args[1]["state"], "DELIVERED")

    def test_telegram_media_sender_calls_photo_before_text(self):
        calls = []
        fake_png = b"\x89PNG\r\n\x1a\n" + b"test"
        def fake_call_api(token, method, body=None):
            calls.append(method)
            if method == "getMe":
                return {"id": 8, "is_bot": True, "username": "NuvexaCheckBot"}
            if method == "getChat":
                return {"id": -10012345, "type": "supergroup", "title": "资讯快报"}
            if method == "sendMessage":
                return {"message_id": 31}
            raise AssertionError(method)
        with patch.object(bridge, "call_api", side_effect=fake_call_api):
            with patch.object(bridge, "call_photo_api", return_value={"message_id":30}) as photo:
                result = bridge.send_group_news_with_image(
                    "===== 资讯助理 =====\n新闻内容", fake_png,
                    {"TELEGRAM_BOT_TOKEN":"token", "TELEGRAM_CHAT_ID":"-10012345"})
        self.assertEqual(calls, ["getMe", "getChat", "sendMessage"])
        self.assertEqual(result["photo_message_id"], 30)
        self.assertEqual(result["message_ids"], [31])
        photo.assert_called_once()

    def test_photo_multipart_contains_exact_png_and_chat_id(self):
        from io import BytesIO
        from unittest.mock import patch
        png = b"\\x89PNG\\r\\n\\x1a\\n" + b"small-test"
        response = BytesIO(b'{"ok":true,"result":{"message_id":54}}')
        with patch.object(bridge.urllib.request, "urlopen", return_value=response) as mock:
            result = bridge.call_photo_api("secret", "-10012345", png)
            req = mock.call_args.args[0]
        self.assertEqual(result["message_id"], 54)
        self.assertEqual(req.get_method(), "POST")
        self.assertIn(b'filename="westcott-news.png"', req.data)
        self.assertIn(png, req.data)
        self.assertIn(b"-10012345", req.data)
        self.assertIn(b"\\r\\n", req.data)
        self.assertIn("multipart/form-data", req.get_header("Content-type"))

    def test_photo_rejects_invalid_png_before_network(self):
        with self.assertRaises(bridge.TelegramError):
            bridge.call_photo_api("token", "-1001", b"bad")


if __name__ == "__main__":
    unittest.main()
