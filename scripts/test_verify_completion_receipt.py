"""Offline positive/negative tests; synthetic fixtures are not real news verification."""
import copy
import hashlib
import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from verify_completion_receipt import validate


class ReceiptGateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "evidence.txt").write_text("Official index value 100.25 on 2026-10-30.\nexit 0\n", encoding="utf-8")
        digest = hashlib.sha256((self.root / "evidence.txt").read_bytes()).hexdigest()
        self.now = datetime(2026, 10, 31, 3, 0, tzinfo=timezone.utc)
        self.data = {
            "version": 1, "task_type": "news", "claim": "COMPLETED", "recorded_at": "2026-10-31T02:00:00+00:00",
            "actions": [{"id": "source-check", "status": "DONE", "evidence": [{
                "kind": "source", "path": "evidence.txt", "sha256": digest,
                "must_contain": "index value 100.25", "url": "https://example.org/official",
                "observed_at": "2026-10-31T01:55:00+00:00"
            }]}],
            "news": {
                "market_timezone": "Europe/Bucharest", "local_date": "2026-10-30",
                "first_published_at": "2026-10-30T08:00:00+00:00",
                "event_at": "2026-10-30T09:00:00+00:00",
                "indicators": [{"name": "index", "unit": "points", "basis": "last_close", "market_state": "CLOSED",
                                "source_url": "https://example.org/official", "as_of": "2026-10-30T09:00:00+00:00",
                                "reported": "100.25", "official": "100.25"}],
            }
        }

    def check(self, data=None):
        return validate(data or self.data, self.root, now=self.now)

    def test_valid_fixture_has_no_structural_errors(self):
        self.assertEqual(self.check(), [])

    def test_no_actions_fails(self):
        self.data["actions"] = []
        self.assertIn("NO_ACTIONS", self.check())

    def test_done_without_evidence_fails(self):
        self.data["actions"][0]["evidence"] = []
        self.assertIn("ACTION_0_NO_EVIDENCE", self.check())

    def test_missing_file_fails(self):
        self.data["actions"][0]["evidence"][0]["path"] = "fake.txt"
        self.assertIn("ACTION_0_EVIDENCE_0_UNREADABLE_OR_INVALID", self.check())

    def test_bad_digest_fails(self):
        self.data["actions"][0]["evidence"][0]["sha256"] = "0" * 64
        self.assertIn("ACTION_0_EVIDENCE_0_SHA_MISMATCH", self.check())

    def test_path_traversal_fails(self):
        self.data["actions"][0]["evidence"][0]["path"] = "../../etc/hosts"
        self.assertIn("ACTION_0_EVIDENCE_0_UNREADABLE_OR_INVALID", self.check())

    def test_invalid_source_url_fails(self):
        self.data["actions"][0]["evidence"][0]["url"] = "http://example.org"
        self.assertIn("ACTION_0_EVIDENCE_0_SOURCE_URL_INVALID", self.check())

    def test_old_news_fails(self):
        self.data["news"]["first_published_at"] = "2026-10-29T08:00:00+00:00"
        self.assertIn("NEWS_NOT_TARGET_LOCAL_DAY:first_published_at", self.check())

    def test_wrong_data_fails(self):
        self.data["news"]["indicators"][0]["reported"] = "101.25"
        self.assertIn("INDICATOR_0_MISMATCH", self.check())

    def test_missing_market_basis_fails(self):
        self.data["news"]["indicators"][0]["basis"] = ""
        self.assertIn("INDICATOR_0_INCOMPLETE", self.check())

    def test_wrong_image_is_blocked(self):
        self.data["news"]["image"] = {"original_url": "https://example.org/photo.jpg",
                                        "article_url": "https://example.org/article", "same_event": False,
                                        "reuse_rights_checked": True}
        self.assertIn("IMAGE_NOT_VERIFIED", self.check())

    def test_claim_completed_but_blocked_action_fails(self):
        self.data["actions"][0]["status"] = "BLOCKED"
        self.assertIn("ACTION_0_INCOMPLETE", self.check())

    def test_stale_receipt_fails(self):
        self.data["recorded_at"] = "2026-10-25T02:00:00+00:00"
        self.assertIn("STALE_OR_FUTURE_RECEIPT", self.check())

    def test_command_with_nonzero_exit_fails(self):
        e = self.data["actions"][0]["evidence"][0]
        e.update(kind="command", command="python -m unittest", exit_code=1)
        self.assertIn("ACTION_0_EVIDENCE_0_COMMAND_NOT_SUCCESSFUL", self.check())


if __name__ == "__main__":
    unittest.main()
