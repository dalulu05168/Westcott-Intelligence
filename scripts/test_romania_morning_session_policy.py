"""Check morning group window and date-aware Romanian DST conversion.

This is a repository policy regression test, not proof of scheduling or delivery.
"""
import json
from datetime import datetime, timezone
from pathlib import Path
import unittest
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
MASTER = "skills/p004-chat-suite/references/romania-morning-session-v2.4.md"
RULES = (
    "skills/p004-chat-suite/SKILL.md",
    "skills/p004-director/SKILL.md",
    "skills/p004-assistant/SKILL.md",
    "skills/p004-writer/SKILL.md",
    "skills/p004-teacher/SKILL.md",
    "skills/p004-members/SKILL.md",
    "skills/p004-chat-suite/references/sop.md",
    "skills/p004-chat-suite/references/five-skill-workflow-v1.5.md",
    "skills/p004-chat-suite/references/daily-editorial-and-memory-v1.6.md",
    "skills/p004-chat-suite/references/session-rules.md",
    "skills/p004-chat-suite/references/romania-us-global-market-linkage-v2.3.md",
    "skills/p004-chat-suite/references/pre-post-market-editorial-v1.7.md",
    "skills/p004-chat-suite/references/drama-and-language.md",
    "skills/p004-chat-suite/references/weekly-activities.md",
    "skills/p004-chat-suite/references/runtime-v2.1.md",
)


class MorningWindowTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = json.loads((ROOT / "config/editorial-policy-v2.1.json").read_text(encoding="utf-8"))
        cls.morning = cls.policy["group_sessions"]["morning"]

    def test_local_morning_and_midday_break(self):
        self.assertEqual(self.policy["timezone"], "Europe/Bucharest")
        self.assertEqual((self.morning["open"], self.morning["close"]), ("08:00", "11:00"))
        self.assertEqual((self.morning["summary_prep_start"], self.morning["summary_prep_end"]), ("10:45", "11:00"))
        self.assertEqual(self.policy["group_sessions"]["midday"], {
            "start": "11:00", "end": "14:00", "group_status": "CLOSED",
        })

    def test_prep_is_not_early_group_opening(self):
        p = self.policy["group_sessions"]["preparation"]
        self.assertEqual(p["daily_brief"], "07:30")
        self.assertEqual((p["n01_review_start"], p["n01_review_end"]), ("07:35", "07:50"))
        self.assertTrue(p["outside_group_session"])

    def test_2026_october_dst_transition(self):
        tz = ZoneInfo("Europe/Bucharest")
        for year, month, day, expected_open_utc, expected_close_utc in (
            (2026, 10, 20, 5, 8),
            (2026, 10, 24, 5, 8),
            (2026, 10, 25, 6, 9),
            (2026, 10, 26, 6, 9),
        ):
            with self.subTest(day=day):
                open_utc = datetime(year, month, day, 8, tzinfo=tz).astimezone(timezone.utc)
                close_utc = datetime(year, month, day, 11, tzinfo=tz).astimezone(timezone.utc)
                self.assertEqual((open_utc.hour, close_utc.hour),
                                 (expected_open_utc, expected_close_utc))

    def test_existing_persona_and_delivery_safety_preserved(self):
        self.assertEqual(self.policy["active_ids"], [1, 42])
        self.assertFalse(self.policy["delivery"]["enabled_by_upgrade"])
        sessions = self.policy["group_sessions"]
        self.assertTrue(sessions["uses_iana_timezone"])
        self.assertEqual(sessions["seasonal_utc_offset"], "AUTO_BY_LOCAL_DATE")
        self.assertTrue(sessions["delivery_schedules_unchanged"])

    def test_five_skills_and_editorial_rules_link_to_master(self):
        self.assertTrue((ROOT / MASTER).is_file())
        self.assertEqual(self.policy["group_sessions"]["guidance_document"], MASTER)
        for path in RULES:
            with self.subTest(path=path):
                text = (ROOT / path).read_text(encoding="utf-8")
                self.assertIn("romania-morning-session-v2.4.md", text)
        sop = (ROOT / "skills/p004-chat-suite/references/sop.md").read_text(encoding="utf-8")
        self.assertIn("|10:45|", sop)


if __name__ == "__main__":
    unittest.main()
