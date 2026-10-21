"""Regression tests for the Westcott fail-closed candidate gate."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from gate_candidate import check_one  # noqa: E402


class CandidateGateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT)
        self.addCleanup(self.temp.cleanup)
        self.bundle = Path(self.temp.name)
        self.draft = self.bundle / "draft.txt"
        self.manifest = self.bundle / "manifest.json"

    def make_bundle(self, text="===== 资讯助理 =====\n今天先看看市场有哪些新变化。\n", **overrides):
        self.draft.write_text(text, encoding="utf-8")
        payload = {
            "task_mode": "WESTCOTT_SCENE",
            "scene": "general",
            "story_date": "2026-10-22",
            "release_status": "CANDIDATE",
            "activity": False,
            "draft_sha256": hashlib.sha256(self.draft.read_bytes()).hexdigest(),
            "source_receipts": {
                name: {"status": "READ", "reference": f"test-ref:{name}"}
                for name in ("github_rules", "google_docs", "notion_corrections", "identity_roster")
            }
        }
        payload.update(overrides)
        self.manifest.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return self.manifest

    def test_valid_static_candidate_passes(self):
        self.assertEqual([], check_one(self.make_bundle()))

    def test_missing_source_is_blocked(self):
        self.make_bundle(source_receipts={})
        self.assertTrue(any("github_rules" in e for e in check_one(self.manifest)))

    def test_changed_draft_is_blocked(self):
        self.make_bundle()
        self.draft.write_text("===== 资讯助理 =====\n改过但没有更新校验值\n", encoding="utf-8")
        self.assertTrue(any("sha256 mismatch" in e for e in check_one(self.manifest)))

    def test_old_teacher_is_blocked(self):
        self.make_bundle(text="===== 先生 =====\nHenry先生今晚讲课。\n")
        self.assertTrue(any("OLD_TEACHER" in e for e in check_one(self.manifest)))

    def test_cannot_self_publish(self):
        self.make_bundle(release_status="PUBLISHED")
        self.assertTrue(any("release_status" in e for e in check_one(self.manifest)))


if __name__ == "__main__":
    unittest.main()
