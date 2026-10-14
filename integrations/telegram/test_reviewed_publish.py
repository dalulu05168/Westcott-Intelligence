"""Offline tests for original-article Telegram publishing; no network side effects."""
import os
import sys
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(__file__))
import bridge
import reviewed_publish as pub


class OriginalArticleTests(unittest.TestCase):
    def ledger(self):
        now = datetime.now(timezone.utc).isoformat()
        return {
            "event_id": "verified-news-00001", "executed_at": now,
            "sources": {
                "s1": {"url": "https://news.example.org/article-12",
                       "access_status": "BODY_READ", "source_type": "official",
                       "origin_id": "agency",
                       "retrieved_at": now, "published_at": now}},
            "claims": [{
                "id": "c1", "text": "已核实的财经事实。", "kind": "fact",
                "review_status": "CONFIRMED", "reviewed_by": "human",
                "evidence": [{"source_id": "s1", "excerpt": "已核实的财经事实。",
                              "locator": "section 1", "supports_exact_claim": True}],
                "numbers": []
            }],
            "publish_claim_ids": ["c1"]
        }

    def approved_photo(self):
        return {
            "source_id": "s1",
            "article_url": "https://news.example.org/article-12",
            "image_url": "https://images.example.org/story-12.jpg",
            "matches_article_reviewed": True,
            "reuse_permission_verified": True,
            "reviewed_by": "human",
            "rights_evidence_url": "https://news.example.org/permission"
        }

    def test_without_image_uses_article_link_not_generated_art(self):
        prepared = pub.prepare(self.ledger(), "news/approved/reviewed.json")
        self.assertEqual(prepared["media"]["image_url"], None)
        self.assertEqual(prepared["media"]["image_decision"], "original_article_link_preview")
        self.assertEqual(prepared["media"]["article_url"], "https://news.example.org/article-12")
        self.assertTrue(prepared["text"].startswith("===== 资讯助理 =====\n"))
        self.assertIn("https://news.example.org/article-12", prepared["text"])
        self.assertNotIn("topic", prepared)

    def test_approved_image_from_exact_supported_article(self):
        ledger = self.ledger()
        ledger["original_image"] = self.approved_photo()
        prepared = pub.prepare(ledger, "news/approved/reviewed.json")
        self.assertEqual(prepared["media"]["image_url"], "https://images.example.org/story-12.jpg")
        self.assertEqual(prepared["media"]["image_decision"], "verified_original_publisher_photo")

    def test_image_without_reuse_permission_is_not_uploaded(self):
        ledger = self.ledger()
        ledger["original_image"] = {**self.approved_photo(), "reuse_permission_verified": False}
        prepared = pub.prepare(ledger, "news/approved/reviewed.json")
        self.assertIsNone(prepared["media"]["image_url"])
        self.assertEqual(prepared["media"]["image_decision"],
                         "original_article_link_preview_rights_unverified")

    def test_image_must_match_claim_source(self):
        ledger = self.ledger()
        ledger["original_image"] = {**self.approved_photo(), "article_url": "https://news.example.org/other"}
        with self.assertRaises(pub.PublicationError):
            pub.prepare(ledger, "news/approved/reviewed.json")
        ledger = self.ledger()
        ledger["original_image"] = {**self.approved_photo(), "source_id": "other"}
        with self.assertRaises(pub.PublicationError):
            pub.prepare(ledger, "news/approved/reviewed.json")

    def test_strict_public_https_urls(self):
        for bad in ("http://news.example.org/article", "https://localhost/a",
                    "https://127.0.0.1/a", "https://[::1]/a",
                    "https://user:password@site.example.org/a",
                    "https://site.example.org:8080/a", "https://site.example.org/a#frag",
                    "https://site.example.org/a\r\nbad", "https://intranet/a"):
            with self.subTest(url=bad), self.assertRaises(pub.PublicationError):
                pub.validate_public_https(bad)
        self.assertEqual(pub.validate_public_https("https://news.example.org/rates"),
                         "https://news.example.org/rates")

    def test_unreviewed_and_unknown_claims_block(self):
        ledger = self.ledger()
        ledger["claims"][0]["review_status"] = "UNVERIFIED"
        with self.assertRaises(pub.PublicationError):
            pub.prepare(ledger, "news/approved/reviewed.json")
        ledger = self.ledger()
        ledger["publish_claim_ids"] = ["unknown"]
        with self.assertRaises(pub.PublicationError):
            pub.prepare(ledger, "news/approved/reviewed.json")

    def test_path_staleness_and_news_fingerprint(self):
        ledger = self.ledger()
        p = pub.prepare(ledger, "news/approved/valid.json")
        ledger["event_id"] = "different-news-00002"
        self.assertEqual(p["fingerprint"],
                         pub.prepare(ledger, "news/approved/valid.json")["fingerprint"])
        with self.assertRaises(pub.PublicationError):
            pub.prepare(ledger, "../../bad.json")
        with self.assertRaises(pub.PublicationError):
            pub.prepare(ledger, "news/approved/valid.json",
                        now=datetime(2030, 1, 1, tzinfo=timezone.utc))

    def test_preview_only_saves_text_not_image(self):
        prepared = pub.prepare(self.ledger(), "news/approved/reviewed.json")
        env = {"GITHUB_TOKEN": "secret", "GITHUB_REPOSITORY": "owner/repo", "GITHUB_REF_NAME": "main"}
        with patch.object(pub, "github_store_asset",
                          return_value="https://github.com/owner/repo/blob/main/news/previews/text.txt") as write:
            with patch.object(pub, "inspect_article", side_effect=pub.SourceMediaError("blocked")):
                preview = pub.save_preview(prepared, env)
        self.assertEqual(write.call_count, 1)
        self.assertTrue(write.call_args.args[0].endswith(".txt"))
        self.assertEqual(preview["original_image_url"], None)

    def test_publish_requires_explicit_confirmation(self):
        p = pub.prepare(self.ledger(), "news/approved/reviewed.json")
        with patch.object(pub, "reserve") as reserve:
            with self.assertRaises(pub.PublicationError):
                pub.publish(p, {})
            reserve.assert_not_called()

    def test_pending_persists_for_unknown_delivery(self):
        p = pub.prepare(self.ledger(), "news/approved/reviewed.json")
        env = {"PUBLISH_CONFIRMATION": pub.CONFIRM}
        with patch.object(pub, "reserve", return_value=("audit/id.json", {}, "sha")):
            with patch.object(pub, "send_group_news_from_official_article",
                              side_effect=RuntimeError("timeout")):
                with self.assertRaisesRegex(pub.PublicationError, "uncertain"):
                    pub.publish(p, env)

    def test_pub_records_official_image_receipt(self):
        ledger = self.ledger()
        ledger["original_image"] = self.approved_photo()
        p = pub.prepare(ledger, "news/approved/reviewed.json")
        env = {"PUBLISH_CONFIRMATION": pub.CONFIRM,
               "GITHUB_TOKEN": "secret", "GITHUB_REPOSITORY": "owner/repo"}
        r = {"group_title": "资讯快报", "photo_message_id": 41,
             "message_ids": [42], "image_delivery": "source_photo"}
        with patch.object(pub, "reserve",
                          return_value=("audit/id.json", {"event_id": p["event_id"]}, "sha")):
            with patch.object(pub, "inspect_article", return_value={
                "image_candidate_url": "https://images.example.org/story-12.jpg",
                "canonical_matches_article": True,
            }):
                with patch.object(pub, "send_group_news_from_official_article", return_value=r) as send:
                    with patch.object(pub, "github_write") as audit:
                        receipt = pub.publish(p, env)
        self.assertEqual(receipt["photo_message_id"], 41)
        self.assertEqual(audit.call_args.args[1]["image_delivery"], "source_photo")
        self.assertEqual(send.call_args.args[2], "https://images.example.org/story-12.jpg")

    def test_preview_discovers_publisher_photo_but_cannot_claim_reuse(self):
        prepared = pub.prepare(self.ledger(), "news/approved/reviewed.json")
        fake = {"article_url": "https://news.example.org/article-12",
                "image_candidate_url": "https://images.example.org/original.jpg",
                "title": "Official report", "verified_for_reuse": False}
        with patch.object(pub, "inspect_article", return_value=fake):
            preview = pub.inspect_media_for_preview(prepared)
        self.assertEqual(preview["image_candidate_url"], "https://images.example.org/original.jpg")
        self.assertFalse(preview["verified_for_reuse"])

    def test_licensed_image_blocks_before_reservation_if_article_mismatch(self):
        ledger = self.ledger()
        ledger["original_image"] = self.approved_photo()
        prepared = pub.prepare(ledger, "news/approved/reviewed.json")
        with patch.object(pub, "inspect_article", return_value={
            "image_candidate_url": "https://images.example.org/unrelated.jpg",
            "canonical_matches_article": True
        }), patch.object(pub, "reserve") as reserve:
            with self.assertRaises(pub.PublicationError):
                pub.publish(prepared, {"PUBLISH_CONFIRMATION": pub.CONFIRM})
            reserve.assert_not_called()

    def test_licensed_image_unreachable_blocks_before_reservation(self):
        ledger = self.ledger()
        ledger["original_image"] = self.approved_photo()
        prepared = pub.prepare(ledger, "news/approved/reviewed.json")
        with patch.object(pub, "inspect_article", side_effect=pub.SourceMediaError("403")), patch.object(pub, "reserve") as reserve:
            with self.assertRaises(pub.PublicationError):
                pub.publish(prepared, {"PUBLISH_CONFIRMATION": pub.CONFIRM})
            reserve.assert_not_called()

    def test_telegram_original_photo_and_text_send(self):
        calls = []
        def call(token, method, body=None):
            calls.append((method, body))
            if method == "getMe":
                return {"id": 88, "is_bot": True, "username": "NuvexaCheckBot"}
            if method == "getChat":
                return {"id": -1001, "type": "supergroup", "title": "资讯快报"}
            if method == "sendPhoto":
                return {"message_id": 70}
            if method == "sendMessage":
                return {"message_id": 71}
            raise AssertionError(method)
        env = {"TELEGRAM_BOT_TOKEN": "secret", "TELEGRAM_CHAT_ID": "-1001"}
        with patch.object(bridge, "call_api", side_effect=call):
            receipt = bridge.send_group_news_from_official_article(
                "===== 资讯助理 =====\n消息", "https://news.example.org/article",
                "https://images.example.org/actual-photo.jpg", env)
        self.assertEqual([x[0] for x in calls], ["getMe", "getChat", "sendPhoto", "sendMessage"])
        self.assertEqual(calls[2][1]["photo"], "https://images.example.org/actual-photo.jpg")
        self.assertEqual(receipt["photo_message_id"], 70)

    def test_telegram_native_article_preview_without_image(self):
        calls = []
        def call(token, method, body=None):
            calls.append((method, body))
            if method == "getMe":
                return {"id": 88, "is_bot": True, "username": "NuvexaCheckBot"}
            if method == "getChat":
                return {"id": -1001, "type": "supergroup", "title": "资讯快报"}
            if method == "sendMessage":
                return {"message_id": 72}
            raise AssertionError(method)
        with patch.object(bridge, "call_api", side_effect=call):
            receipt = bridge.send_group_news_from_official_article(
                "===== 资讯助理 =====\n消息", "https://news.example.org/article", None,
                {"TELEGRAM_BOT_TOKEN": "secret", "TELEGRAM_CHAT_ID": "-1001"})
        self.assertEqual([x[0] for x in calls], ["getMe", "getChat", "sendMessage"])
        self.assertEqual(calls[-1][1]["link_preview_options"]["url"],
                         "https://news.example.org/article")
        self.assertIsNone(receipt["photo_message_id"])
        self.assertEqual(receipt["image_delivery"], "article_link_preview")


if __name__ == "__main__":
    unittest.main()
