"""Deterministic offline tests for official news candidate queue; never send Telegram."""
from datetime import datetime, timedelta, timezone
import io
import json
import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(__file__))
import news_radar as radar


class OfficialRadarTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 15, 10, 0, tzinfo=timezone.utc)
        self.fed = radar.FEEDS[0]
        self.ecb = radar.FEEDS[1]

    def rss(self, date="Thu, 15 Oct 2026 09:00:00 GMT", title="Federal Reserve monetary policy decision"):
        return ("""<?xml version="1.0" ?><rss version="2.0"><channel><title>Fed releases</title>
        <item><title>""" + title + """</title>
        <link>https://www.federalreserve.gov/newsevents/pressreleases/monetary20261015a.htm</link>
        <pubDate>""" + date + """</pubDate></item>
        </channel></rss>""").encode("utf-8")

    def test_parse_actual_rss_structure_and_rank(self):
        parsed = radar.extract_items(self.rss(), self.fed)
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]["feed_id"], "fed_monetary")
        found = radar.pick_candidates(parsed, self.now)
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["intake_status"], "UNREVIEWED")
        self.assertFalse(found[0]["body_read"])
        self.assertFalse(found[0]["telegram_publishable"])
        self.assertFalse(found[0]["image_reuse_permission_verified"])

    def test_bvb_official_company_report_candidate(self):
        bvb = next(feed for feed in radar.FEEDS if feed["id"] == "bvb_market")
        rss = b"""<?xml version="1.0"?><rss version="2.0"><channel>
        <item><title>TLV - Raport financiar si dividende</title>
        <link>https://www.bvb.ro/FinancialInstruments/SelectedData/NewsItem.aspx?id=123</link>
        <pubDate>Thu, 15 Oct 2026 09:00:00 GMT</pubDate></item>
        </channel></rss>"""
        stories = radar.extract_items(rss, bvb)
        self.assertEqual(len(stories), 1)
        choices = radar.pick_candidates(stories, self.now)
        self.assertEqual(len(choices), 1)
        self.assertEqual(choices[0]["source"], "Bucharest Stock Exchange")
        self.assertFalse(choices[0]["telegram_publishable"])

    def test_atom(self):
        atom = """<feed xmlns="http://www.w3.org/2005/Atom">
        <entry><title>ECB interest rate decision</title>
        <link href="https://www.ecb.europa.eu/press/pr/date/2026/html/20261015.en.html" />
        <published>2026-10-15T09:00:00+00:00</published></entry></feed>"""
        found = radar.extract_items(atom.encode(), self.ecb)
        self.assertEqual(found[0]["source"], "European Central Bank")
        self.assertEqual(len(radar.pick_candidates(found, self.now)), 1)

    def test_fails_closed_on_redirected_host_article(self):
        malicious = self.rss().replace(b"https://www.federalreserve.gov/", b"https://example.com/")
        self.assertEqual(radar.extract_items(malicious, self.fed), [])

    def test_old_future_and_generic_not_alerted(self):
        row = radar.extract_items(self.rss(), self.fed)[0]
        self.assertFalse(radar.pick_candidates([dict(row, published_at="2026-10-01T09:00:00+00:00")], self.now))
        self.assertFalse(radar.pick_candidates([dict(row, published_at="2026-10-15T17:00:00+00:00")], self.now))
        self.assertFalse(radar.pick_candidates([dict(row, title="New office furniture announced")], self.now))

    def test_exact_story_url_dedup_across_feeds(self):
        parsed = radar.extract_items(self.rss(), self.fed)
        assert len(parsed) == 1
        candidates = radar.pick_candidates(parsed + parsed, self.now)
        self.assertEqual(len(candidates), 1)

    def test_doctype_danger_rejected(self):
        with self.assertRaises(radar.RadarError):
            radar.extract_items(b'<!DOCTYPE rss [<!ENTITY x SYSTEM "file:///etc/passwd">]><rss/>', self.fed)

    def test_feed_all_fail_stops(self):
        def broken(_):
            raise radar.RadarError("Feed unavailable")
        with self.assertRaises(radar.RadarError):
            radar.collect(broken, self.now)

    def test_partial_feed_failure_reported(self):
        def partially_broken(feed):
            if feed["id"] == "ecb_press":
                raise radar.RadarError("Blocked")
            return self.rss()
        items, errors = radar.collect(partially_broken, self.now)
        self.assertEqual(len(items), 1)
        self.assertEqual(errors[0]["source"], "ecb_press")

    def test_candidate_original_image_is_review_only(self):
        item = radar.pick_candidates(radar.extract_items(self.rss(), self.fed), self.now)[0]
        with patch("source_media.inspect_article", return_value={
            "image_candidate_url": "https://www.federalreserve.gov/images/press-photo.jpg",
            "canonical_matches_article": True,
        }):
            enriched = radar.inspect_candidate_image(item)
        self.assertEqual(enriched["image_origin"], "publisher_og_metadata")
        self.assertTrue(enriched["image_review_required"])
        self.assertFalse(enriched["image_reuse_permission_verified"])

    def test_unavailable_original_image_no_fallback_generated(self):
        item = radar.pick_candidates(radar.extract_items(self.rss(), self.fed), self.now)[0]
        def failed(_):
            raise ValueError("No original metadata")
        enriched = radar.inspect_candidate_image(item, inspector=failed)
        self.assertIsNone(enriched["original_image_candidate_url"])
        self.assertEqual(enriched["image_origin"], "metadata_unavailable")

    def test_github_duplicate_does_not_overwrite(self):
        item = radar.pick_candidates(radar.extract_items(self.rss(), self.fed), self.now)[0]
        from urllib.error import HTTPError
        with patch.object(radar.request, "urlopen", side_effect=HTTPError(
            "https://api.github.com", 422, "Already exists", {}, io.BytesIO())):
            self.assertEqual(radar.git_queue_file(item, "secret", "owner/repo"), "existing")


if __name__ == "__main__":
    unittest.main()
