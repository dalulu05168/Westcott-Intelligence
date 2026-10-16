"""Offline regression tests for the independent Romania/France news streams."""
import os
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup
from dual_market import (PARIS, PROFILES, caption, due, host_allowed,
                         materiality, official_image, pick, us_quote_snapshot)

TZ = ZoneInfo("Europe/Bucharest")


class TwoCountryTests(unittest.TestCase):
    def test_morning_same_local_clock_is_one_hour_apart(self):
        ro_morning = datetime(2026, 10, 16, 7, 30, tzinfo=TZ).astimezone(timezone.utc)
        fr_morning = datetime(2026, 10, 16, 7, 30, tzinfo=PARIS).astimezone(timezone.utc)
        self.assertEqual(3600, (fr_morning - ro_morning).total_seconds())
        self.assertEqual((["RO"], "morning"), due(ro_morning, ""))
        self.assertEqual((["FR"], "morning"), due(fr_morning, ""))

    def test_hourly_pair_at_one_actual_instant(self):
        instant = datetime(2026, 10, 16, 9, 0, tzinfo=PARIS)
        self.assertEqual(10, instant.astimezone(TZ).hour)
        self.assertEqual((["RO", "FR"], "hourly"), due(instant, ""))

    def test_daylight_saving_and_weekends(self):
        instant = datetime(2026, 11, 2, 9, 0, tzinfo=PARIS)
        self.assertEqual(10, instant.astimezone(TZ).hour)
        self.assertEqual((["RO", "FR"], "hourly"), due(instant, ""))
        weekend = datetime(2026, 10, 17, 9, 0, tzinfo=PARIS)
        self.assertEqual(([], ""), due(weekend, ""))

    def test_country_labels_and_language(self):
        self.assertEqual(("🔵", "ro"), (PROFILES["RO"]["marker"], PROFILES["RO"]["lang"]))
        self.assertEqual(("🔴", "fr"), (PROFILES["FR"]["marker"], PROFILES["FR"]["lang"]))

    def test_source_image_must_resolve_on_original_official_site(self):
        record = {"source": "AMF", "url": "https://www.amf-france.org/fr/actualites/story"}
        good = BeautifulSoup('<meta property="og:image" content="/sites/default/files/2026/07/story.jpg">', "html.parser")
        self.assertEqual("https://www.amf-france.org/sites/default/files/2026/07/story.jpg",
                         official_image(good, record))
        bad = BeautifulSoup('<meta property="og:image" content="https://random-cdn.example/photo.jpg">', "html.parser")
        self.assertIsNone(official_image(bad, record))
        logo = BeautifulSoup('<meta property="og:image" content="/logo.jpg">', "html.parser")
        self.assertIsNone(official_image(logo, record))

    def test_unofficial_article_url_rejected(self):
        self.assertFalse(host_allowed("http://www.amf-france.org/news", ("amf-france.org",)))
        self.assertFalse(host_allowed("https://amf-france.org.evil.test/story",
                                      ("amf-france.org",)))

    def test_hourly_old_event_suppressed(self):
        now = datetime(2026, 10, 16, 11, 0, tzinfo=TZ)
        record = {"source": "BVB", "title": "Banca profit report",
                  "id": "x", "published": (now-timedelta(hours=4)).isoformat()}
        self.assertIsNone(materiality(record, "RO", now, "hourly", {}))

    def test_local_dedup_is_per_country(self):
        now = datetime(2026, 10, 16, 11, 0, tzinfo=TZ)
        record = {"source": "ECB", "title": "Interest rates and inflation",
                  "id": "shared", "published": (now-timedelta(minutes=30)).isoformat()}
        sent = {"RO|shared": {"message_id": 123}}
        self.assertEqual([], pick([record], "RO", now, "hourly", {"sent": sent}))
        self.assertEqual([record], pick([record], "FR", now, "hourly", {"sent": sent}))

    def test_reject_bogus_market_close_snapshot(self):
        with patch.dict(os.environ, {"VERIFIED_US_CLOSE_JSON":
             '{"verification":"pending","source_url":"https://nasdaq.com","as_of":"2026-10-15T16:00:00-04:00"}'}):
            self.assertIsNone(us_quote_snapshot())

    def test_only_one_caption_for_photo_and_matching_country_path(self):
        now = datetime(2026, 10, 16, 11, 0, tzinfo=TZ)
        article = {"url": "https://www.bvb.ro/AboutUs/MediaCenter/PressItem/short/123",
                   "source": "BVB"}
        text = {"headline": "Titlu", "verified_event": "Fapt verificat",
                "local_market_path": "Impact condiționat pentru BET",
                "next_watch": "Următorul raport"}
        result = caption("RO", article, text, "", now, "hourly")
        self.assertIn("🔵 România", result)
        self.assertIn("Impact condiționat pentru BET", result)
        self.assertLessEqual(len(result), 1024)


if __name__ == "__main__":
    unittest.main()
