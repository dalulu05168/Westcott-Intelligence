"""Static evidence and negative regression tests for member stock ledger."""
import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import member_stock_ledger as ledger


class MemberStockLedgerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data, cls.curated = ledger.load()

    def test_baseline_65_individual_indexes(self):
        report = ledger.validate_ledger(self.data, self.curated)
        self.assertEqual(report["indexed_identities"], 65)
        self.assertEqual(report["reviewed_story_state_records"], 10)
        self.assertEqual(report["members_with_records"], 9)
        self.assertEqual(report["real_broker_trades_verified"], 0)
        self.assertEqual(len(self.data["by_member"]["41"]), 0)
        self.assertEqual(len(self.data["by_member"]["42"]), 0)
        self.assertEqual(len(self.data["by_member"]["43"]), 0)

    def test_existing_record_25_partial_sale_not_full_exit(self):
        rec = [r for r in ledger.query(self.data, member="25")["records"] if r["symbol"] == "FOJE"]
        self.assertEqual(len(rec), 1)
        self.assertEqual(rec[0]["symbol"], "FOJE")
        self.assertEqual(rec[0]["action"], "SELF_REPORTED_HOLD_AND_PARTIAL_SALE")
        self.assertIsNone(rec[0]["reported_quantity"])

    def test_38_and_34_have_story_buy_and_40_has_only_plan(self):
        self.assertEqual(ledger.query(self.data, member="38")["records"][0]["action"], "SELF_REPORTED_BUY")
        self.assertEqual(ledger.query(self.data, member="34")["records"][0]["action"], "SELF_REPORTED_BUY")
        self.assertEqual(ledger.query(self.data, member="40")["records"][0]["action"], "CONDITIONAL_PLAN_NOT_PURCHASE")
        self.assertEqual(len(ledger.query(self.data, symbol="AA")["records"]), 2)

    def test_member_identity_mismatch_blocks(self):
        changed = copy.deepcopy(self.data)
        changed["records"][0]["member_id"] = "41"
        with self.assertRaisesRegex(ValueError, "SOURCE_IDENTITY_OR_ACTION_MISMATCH"):
            ledger.validate_ledger(changed, self.curated)

    def test_unverified_buy_cannot_be_written_over_plan(self):
        changed = copy.deepcopy(self.data)
        changed["records"][3]["action"] = "SELF_REPORTED_BUY"
        with self.assertRaisesRegex(ValueError, "SOURCE_IDENTITY_OR_ACTION_MISMATCH"):
            ledger.validate_ledger(changed, self.curated)

    def test_no_fake_real_trade_or_financial_result(self):
        for field, val, error in (
            ("real_trade_verified", True, "STORY_NOT_REAL_BROKER_PROOF"),
            ("outcome_or_position_estimate", 1200, "UNVERIFIED_HOLDINGS_OR_PNL"),
            ("reported_quantity", 100, "UNSUPPORTED_NUMERIC_FIELD"),
            ("actual_execution_time", "2026-10-16T14:30", "FABRICATED_EXECUTION_TIME"),
        ):
            with self.subTest(field=field):
                d = copy.deepcopy(self.data)
                d["records"][0][field] = val
                with self.assertRaisesRegex(ValueError, error):
                    ledger.validate_ledger(d, self.curated)

    def test_no_invented_recommendation_link_or_double_count(self):
        for field, value, err in (
            ("recommendation_id", "fake-recommendation", "UNSUPPORTED_RECOMMENDATION_LINK"),
            ("id", self.data["records"][1]["id"], "DUPLICATE_OR_INVALID_EVENT_ID"),
        ):
            with self.subTest(field=field):
                d = copy.deepcopy(self.data)
                d["records"][0][field] = value
                with self.assertRaisesRegex(ValueError, err):
                    ledger.validate_ledger(d, self.curated)

    def test_missing_or_reassigned_evidence_blocks(self):
        d = copy.deepcopy(self.data)
        d["records"][2]["source_evidence_ids"] = ["invented"]
        with self.assertRaisesRegex(ValueError, "SOURCE_EVIDENCE_MISMATCH"):
            ledger.validate_ledger(d, self.curated)

    def test_index_mismatch_blocks(self):
        d = copy.deepcopy(self.data)
        d["by_member"]["34"] = []
        with self.assertRaisesRegex(ValueError, "MEMBER_INDEX_NOT_RECONCILED"):
            ledger.validate_ledger(d, self.curated)

    def test_inactive_member_new_story_blocks(self):
        d = copy.deepcopy(self.data)
        d["records"][0]["member_id"] = "43"
        with self.assertRaisesRegex(ValueError, "INACTIVE_MEMBER_CANNOT_PARTICIPATE"):
            ledger.validate_ledger(d, self.curated)

    def test_snn_annotation_does_not_become_real_execution(self):
        events = ledger.query(self.data, symbol="SNN")["records"]
        self.assertEqual({r["member_id"] for r in events}, {"01", "14", "24", "25", "27", "28"})
        self.assertTrue(all(r["action"] == "AUTHOR_MARKED_FOLLOW_RECOMMENDATION" and r["reported_price"] is None for r in events))
        changed = copy.deepcopy(self.data)
        changed["records"][-1]["action"] = "SELF_REPORTED_BUY"
        with self.assertRaisesRegex(ValueError, "SOURCE_IDENTITY_OR_ACTION_MISMATCH"):
            ledger.validate_ledger(changed, self.curated)

    def test_new_event_wrong_date_is_rejected(self):
        changed = copy.deepcopy(self.data)
        changed["records"][-1]["story_date"] = "2026-10-20"
        with self.assertRaisesRegex(ValueError, "SOURCE_DATE_MISMATCH"):
            ledger.validate_ledger(changed, self.curated)

    def test_query_unknown_member_blocks(self):
        with self.assertRaisesRegex(ValueError, "UNKNOWN_MEMBER"):
            ledger.query(self.data, member="66")


if __name__ == "__main__":
    unittest.main()
