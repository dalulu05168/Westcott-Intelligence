"""Offline safety and matching tests for original publisher image metadata."""
import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(__file__))
import source_media as media


class OriginalSourceImageTests(unittest.TestCase):
    def test_publisher_og_image_and_canonical_detected(self):
        markup = """<html><head>
        <meta property="og:title" content="Original Company Earnings Report"/>
        <meta property="og:image" content="/photos/earnings.jpg"/>
        <link rel="canonical" href="https://news.example.org/market/company"/>
        </head><body><img src="/unrelated.jpg"></body></html>"""
        result = media.inspect_markup("https://news.example.org/market/company", markup)
        self.assertEqual(result["image_candidate_url"],
                         "https://news.example.org/photos/earnings.jpg")
        self.assertEqual(result["image_metadata_field"], "og:image")
        self.assertEqual(result["title"], "Original Company Earnings Report")
        self.assertTrue(result["canonical_matches_article"])
        self.assertFalse(result["verified_for_reuse"])

    def test_prefers_open_graph_to_twitter_image(self):
        markup = """<head><meta name="twitter:image" content="https://images.example.org/twitter.png">
        <meta property="og:image:secure_url" content="https://images.example.org/main.png"></head>"""
        result = media.inspect_markup("https://news.example.org/market", markup)
        self.assertEqual(result["image_candidate_url"],
                         "https://images.example.org/main.png")

    def test_no_media_does_not_fabricate_image(self):
        result = media.inspect_markup("https://news.example.org/market", "<head><title>News</title></head>")
        self.assertIsNone(result["image_candidate_url"])
        self.assertEqual(result["title"], "News")

    def test_mismatched_canonical_marks_ambiguous_not_verified(self):
        markup = '<head><link rel="canonical" href="https://news.example.org/unrelated"></head>'
        result = media.inspect_markup("https://news.example.org/actual", markup)
        self.assertFalse(result["canonical_matches_article"])

    def test_bad_image_metadata_is_not_selected(self):
        result = media.inspect_markup(
            "https://news.example.org/market",
            '<head><meta property="og:image" content="http://127.0.0.1/secret"></head>')
        self.assertIsNone(result["image_candidate_url"])

    def test_rejects_private_and_untrusted_urls(self):
        for url in ("http://news.example.org/a", "https://127.0.0.1/x",
                    "https://[::1]/image", "https://localhost/a",
                    "https://news.example.org:8080/a",
                    "https://someone:pass@news.example.org/a",
                    "https://news.example.org/a\r\nsecret",
                    "https://news.example.org/a#fragment"):
            with self.subTest(url=url), self.assertRaises(media.SourceMediaError):
                media.public_https(url)

    def test_dns_private_address_denied(self):
        with patch.object(media.socket, "getaddrinfo", return_value=[
            (2, 1, 6, '', ('10.0.0.5', 443))
        ]):
            with self.assertRaises(media.SourceMediaError):
                media.public_dns("news.example.org")

    def test_direct_reuters_jpg_url_recognized_without_fetch(self):
        url = ("https://www.reuters.com/resizer/v2/F7CJVSFRJFN4ZL7CPAUE5NW2DE.jpg"
               "?auth=sample&width=1920&quality=80")
        def forbidden_fetch(_):
            raise AssertionError("The direct photo must not be parsed as an article")
        found = media.inspect_news_url(url, fetcher=forbidden_fetch)
        self.assertEqual(found["status"], "IMAGE_URL_RECOGNIZED")
        self.assertEqual(found["input_type"], "direct_image_url")
        self.assertEqual(found["image_candidate_url"], url)
        self.assertFalse(found["matches_news_article"])
        self.assertFalse(found["verified_for_reuse"])

    def test_article_url_still_inspects_html(self):
        url = "https://news.example.org/story"
        found = media.inspect_news_url(
            url, fetcher=lambda _: '<head><meta property="og:image" content="/one.jpg"></head>')
        self.assertEqual(found["status"], "ARTICLE_METADATA_INSPECTED")
        self.assertEqual(found["image_candidate_url"], "https://news.example.org/one.jpg")

    def test_does_not_trust_invalid_photo_url(self):
        with self.assertRaises(media.SourceMediaError):
            media.inspect_news_url("http://127.0.0.1/secret.jpg")

    def test_inspection_uses_injected_fetcher_without_network(self):
        fake = lambda url: '<head><meta property="og:image" content="https://cdn.example.org/photo.webp"></head>'
        result = media.inspect_article("https://news.example.org/story", fetcher=fake)
        self.assertEqual(result["image_candidate_url"], "https://cdn.example.org/photo.webp")


if __name__ == "__main__":
    unittest.main()
