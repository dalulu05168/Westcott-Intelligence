import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'integrations/telegram'))
import unittest
from datetime import datetime, timezone
import hashlib
from morning_source_intake import build, MARKET_SCOPES
from news_radar import RadarError

NOW=datetime(2026,10,19,4,45,tzinfo=timezone.utc)  # 07:45 Bucharest

def rss(url, headline="Official economic development"):
    return f'''<?xml version="1.0"?>
    <rss version="2.0"><channel><item><title>{headline}</title>
    <link>{url}</link><pubDate>Mon, 19 Oct 2026 04:10:00 GMT</pubDate>
    </item></channel></rss>'''.encode()

class MorningIntakeTests(unittest.TestCase):
    def test_makes_only_unreviewed_candidates(self):
        def fetch(feed):
            return rss("https://" + feed["article_hosts"][0] + "/release-20261019")
        def inspect(item):
            return {**item, "body_fetch_status":"FETCHED_FOR_REVIEW",
                    "source_text_sha256":hashlib.sha256(b"original body").hexdigest(),
                    "source_text_snapshot":"original body", "source_text_truncated":False}
        result=build(NOW,fetch,inspect)
        self.assertEqual(result["status"],"OFFICIAL_INTAKE_UNREVIEWED")
        self.assertEqual(len(result["coverage"]),len(MARKET_SCOPES))
        self.assertTrue(result["candidates"])
        self.assertTrue(all(not x["telegram_publishable"] for x in result["candidates"]))
        self.assertFalse(result["delivery_allowed"])
        self.assertFalse(result["google_docs_current_revision_loaded"])
        self.assertFalse(result["us_index_close_snapshot_ready"])
        country_sets={x["source_id"]:x["market_scopes"] for x in result["candidates"]}
        self.assertEqual(country_sets["insee_conjuncture"],["FR"])
        self.assertEqual(country_sets["bvb_market"],["RO"])
        self.assertEqual(country_sets["fed_monetary"],["US"])

    def test_unavailable_original_body_never_approved(self):
        def fetch(feed):
            return rss("https://" + feed["article_hosts"][0] + "/release-20261019")
        def inspect(item):
            return {**item,"body_fetch_status":"UNAVAILABLE","source_text_truncated":True}
        result=build(NOW,fetch,inspect)
        self.assertTrue(all(x["evidence_status"]=="SOURCE_BODY_UNAVAILABLE" for x in result["candidates"]))
        self.assertFalse(result["delivery_allowed"])

    def test_feed_failure_does_not_fake_coverage(self):
        def fetch(feed):
            if feed["id"]=="insee_conjuncture":raise RadarError("Blocked")
            return rss("https://" + feed["article_hosts"][0] + "/release-20261019")
        result=build(NOW,fetch,lambda item: {"body_fetch_status":"UNAVAILABLE"})
        self.assertIn({"feed_id":"insee_conjuncture","status":"ERROR"},result["coverage"])
        self.assertFalse(result["telegram_sent"])

    def test_invalid_timezone(self):
        with self.assertRaises(ValueError):
            build(datetime(2026,10,19,7,0),lambda f: b"")
if __name__=="__main__":
    unittest.main()
