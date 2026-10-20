"""Static acceptance tests for the Romania-first US/global impact editorial policy.

These validate checked-in policy consistency, not live news verification or delivery.
"""
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
POLICY = "skills/p004-chat-suite/references/romania-us-global-market-linkage-v2.3.md"
REFERENCED_BY = (
    "skills/p004-chat-suite/SKILL.md",
    "skills/p004-director/SKILL.md",
    "skills/p004-writer/SKILL.md",
    "skills/p004-teacher/SKILL.md",
    "skills/p004-assistant/SKILL.md",
    "skills/p004-members/SKILL.md",
    "skills/p004-chat-suite/references/pre-post-market-editorial-v1.7.md",
    "skills/p004-chat-suite/references/daily-editorial-and-memory-v1.6.md",
    "skills/p004-chat-suite/references/five-skill-workflow-v1.5.md",
    "skills/p004-chat-suite/references/session-rules.md",
    "skills/p004-chat-suite/references/editorial-execution-v1.8.md",
)

class RomaniaGlobalNewsLinkagePolicyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = json.loads((ROOT / "config/editorial-policy-v2.1.json").read_text(encoding="utf-8"))
        cls.rule = (ROOT / POLICY).read_text(encoding="utf-8")

    def test_romania_first_and_market_scope(self):
        settings = self.policy["news_linkage"]
        self.assertEqual(settings["priority_market"], "RO")
        self.assertTrue({"US", "EU", "GLOBAL"}.issubset(settings["related_markets_to_check"]))
        self.assertTrue(settings["editorial_guidance_only"])

    def test_confirmed_response_is_distinct_from_potential_channel(self):
        settings = self.policy["news_linkage"]
        self.assertEqual(set(settings["eligible_romania_relevance"]),
                         {"ROMANIA_VERIFIED_RESPONSE", "ROMANIA_POTENTIAL_CHANNEL"})
        self.assertIn("NO_DEMONSTRABLE_LINK", settings["romania_relevance_states"])
        self.assertTrue(settings["requires_separate_evidence_for_causation"])
        self.assertTrue(settings["requires_specific_transmission_chain"])
        for phrase in ("ROMANIA_VERIFIED_RESPONSE", "ROMANIA_POTENTIAL_CHANNEL",
                       "NO_DEMONSTRABLE_LINK"):
            self.assertIn(phrase, self.rule)

    def test_required_context_fields_are_documented(self):
        for field in self.policy["news_linkage"]["required_internal_fields"]:
            self.assertIn(field, self.rule)
        self.assertTrue(self.policy["news_linkage"]["requires_data_time_and_market_phase"])

    def test_romanian_daily_news_windows_and_existing_limits(self):
        for time in ("07:30", "09:00", "14:00", "16:00", "20:00"):
            self.assertIn(time, self.rule)
        self.assertIn("1—2条", self.rule)
        self.assertEqual(self.policy["active_ids"], [1, 42])
        self.assertFalse(self.policy["delivery"]["enabled_by_upgrade"])

    def test_five_skills_and_editorial_references_point_to_new_rule(self):
        self.assertEqual(self.policy["news_linkage"]["guidance_document"], POLICY)
        for path in REFERENCED_BY:
            with self.subTest(path=path):
                s = (ROOT / path).read_text(encoding="utf-8")
                self.assertIn("romania-us-global-market-linkage-v2.3.md", s)

if __name__ == "__main__":
    unittest.main()
