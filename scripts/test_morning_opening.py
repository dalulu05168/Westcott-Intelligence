import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from morning_opening import build

NOW = datetime(2026, 10, 16, 7, 30, tzinfo=ZoneInfo("Europe/Bucharest"))

def valid_data():
    # Numeric examples are test fixtures ONLY, never news or trade history.
    return {
        "market": "US",
        "phase": "REGULAR_CLOSE",
        "session_date": "2026-10-15",
        "source_url": "https://example.org/official-close",
        "source_checked_at": "2026-10-16T07:20:00+03:00",
        "review_status": "REVIEWED",
        "reviewed_by": "test-reviewer",
        "evidence_reference": "test-fixture-not-a-publication",
        "source_body_sha256": "0" * 64,
        "indices": [
            {
                "symbol": sym,
                "close": close,
                "previous_close": previous,
                "change_pct": round((close / previous - 1) * 100, 2),
                "quote_as_of": "2026-10-15T16:00:00-04:00",
                "phase": "REGULAR_CLOSE",
                "source_url": f"https://example.org/{sym}",
                "evidence_excerpt": "fixture value only",
            }
            for sym, close, previous in [
                ("DJIA", 49000.0, 49100.0),
                ("SPX", 6700.0, 6690.0),
                ("IXIC", 23000.0, 23020.0),
            ]
        ],
    }

class TestMorningOpening(unittest.TestCase):
    def test_missing_market_evidence_never_invents_recaps(self):
        result = build(NOW)
        self.assertEqual(result["status"], "HELD_SOURCE_REQUIRED")
        self.assertIsNone(result["us_recap_draft"])
        self.assertFalse(result["delivery_allowed"])
        self.assertFalse(result["telegram_sent"])
        self.assertFalse(result["member_dialogue_generated"])

    def test_verified_structured_input_yields_review_only_draft(self):
        result = build(NOW, valid_data())
        self.assertEqual(result["status"], "READY_FOR_EDITORIAL_REVIEW")
        self.assertIn("2026年10月15日", result["us_recap_draft"])
        self.assertIn("道琼斯工业平均指数", result["us_recap_draft"])
        self.assertFalse(result["delivery_allowed"])
        self.assertFalse(result["formal_google_docs_loaded"])

    def test_reject_future_or_wrong_trading_day(self):
        value = valid_data()
        value["session_date"] = "2026-10-16"
        self.assertEqual(build(NOW, value)["status"], "HELD_INVALID_MARKET_EVIDENCE")

    def test_reject_inconsistent_percent_change(self):
        value = valid_data()
        value["indices"][0]["change_pct"] = 4.2
        self.assertEqual(build(NOW, value)["status"], "HELD_INVALID_MARKET_EVIDENCE")

    def test_reject_missing_source_claim(self):
        value = valid_data()
        del value["indices"][0]["evidence_excerpt"]
        self.assertEqual(build(NOW, value)["status"], "HELD_INVALID_MARKET_EVIDENCE")

    def test_reject_unreviewed_input(self):
        value = valid_data()
        value["review_status"] = "UNREVIEWED"
        self.assertEqual(build(NOW, value)["status"], "HELD_INVALID_MARKET_EVIDENCE")

if __name__ == "__main__":
    unittest.main()
