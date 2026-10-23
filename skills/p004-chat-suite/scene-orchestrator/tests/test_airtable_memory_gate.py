"""Regression tests for evidence-first Airtable memory reconciliation."""
import importlib.util
from pathlib import Path
import unittest

FILE = Path(__file__).resolve().parents[1] / "tools" / "airtable_memory_gate.py"
SPEC = importlib.util.spec_from_file_location("airtable_memory_gate", FILE)
gate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gate)


class AirtableMemoryGateTests(unittest.TestCase):
    def setUp(self):
        self.roster = {"people":[{"id":f"{n:02d}","gender":"女" if n in (2,10,21,42)
                                  else "男"} for n in range(1,66)]}
        self.doc = {"documentId":gate.FORMAL_DOCUMENT_ID,"revisionId":"REV-1",
                    "tabId":"t.official", "date":"2026-10-23",
                    "paragraphs":[{"text":s} for s in
                                  ("===== 资讯助理 =====", "开群",
                                   "02女：\x0b这个地方我没明白。",
                                   "14男：", "别急，我也没懂。")]}
        self.saved = [{"证据ID":"EW-old-02","人物编号":"02","原话":"这个地方我没明白。",
                       "剧情日期":"2026-10-23","正式页签":"t.official",
                       "原文段落索引":"p2—p2 (0起算)","审核状态":"已核对",
                       "文档修订号":"REV-0"}]

    def test_same_quote_preserves_identity(self):
        out = gate.reconcile(self.doc, self.roster, self.saved)
        self.assertEqual(out["status"], "CHANGES_PROPOSED")
        self.assertEqual(out["reused_ids"], ["EW-old-02"])
        self.assertEqual(len(out["ready_to_create"]), 1)
        self.assertEqual(out["ready_to_create"][0]["member_id"], "14")

    def test_second_run_is_idempotent(self):
        first = gate.reconcile(self.doc, self.roster, self.saved)
        extra = first["ready_to_create"][0]
        saved = self.saved + [{"证据ID":extra["evidence_id"],
                               "人物编号":extra["member_id"],"原话":extra["text"],
                               "剧情日期":"2026-10-23","正式页签":"t.official",
                               "原文段落索引":"p3—p4 (0起算)"}]
        out = gate.reconcile(self.doc, self.roster, saved)
        self.assertEqual(out["status"], "NO_CHANGE")
        self.assertEqual(len(out["ready_to_create"]), 0)

    def test_paragraph_insertion_detected_as_move_not_new(self):
        self.doc["paragraphs"].insert(1, {"text":"额外公告"})
        out = gate.reconcile(self.doc, self.roster, self.saved)
        self.assertEqual(out["reused_ids"], ["EW-old-02"])
        self.assertEqual(out["moved_for_review"][0]["new_position"], 3)
        self.assertEqual(len(out["ready_to_create"]), 1)

    def test_edited_text_not_silently_added(self):
        self.doc["paragraphs"][2]["text"] = "02女：\x0b这张图我还是没明白。"
        out = gate.reconcile(self.doc, self.roster, self.saved)
        self.assertEqual(out["status"], "REVIEW_REQUIRED")
        self.assertEqual(len(out["ready_to_create"]), 0)
        self.assertEqual(out["held_new"][0]["member_id"], "02")
        self.assertEqual(out["conflicts"][0]["type"], "MISSING_OR_EDITED")

    def test_deletion_not_erased(self):
        self.doc["paragraphs"] = self.doc["paragraphs"][:2]
        out = gate.reconcile(self.doc, self.roster, self.saved)
        self.assertEqual(out["status"], "REVIEW_REQUIRED")
        self.assertEqual(len(out["reused_ids"]), 0)
        self.assertEqual(out["conflicts"][0]["evidence_id"],"EW-old-02")

    def test_wrong_gender_is_quarantined(self):
        self.doc["paragraphs"][2]["text"] = "02男：冒用女性身份"
        out = gate.reconcile(self.doc, self.roster, self.saved)
        self.assertTrue(any(x["type"] == "ROLE_MISMATCH" for x in out["conflicts"]))
        self.assertEqual(out["ready_to_create"], [])

    def test_43_to_65_never_auto_import(self):
        self.doc["paragraphs"].append({"text":"43男：不应自动出场"})
        out = gate.reconcile(self.doc, self.roster, self.saved)
        self.assertTrue(any(x["type"] == "ROLE_MISMATCH" for x in out["conflicts"]))

    def test_rejects_fake_source(self):
        self.doc["documentId"] = "another-document"
        with self.assertRaisesRegex(ValueError,"SOURCE_BLOCKED"):
            gate.reconcile(self.doc, self.roster, self.saved)

    def test_different_date_never_paired(self):
        old = dict(self.saved[0], **{"剧情日期":"2026-10-22"})
        out = gate.reconcile(self.doc, self.roster, [old])
        self.assertEqual(len(out["reused_ids"]), 0)
        self.assertEqual(out["stored_evidence_rows"], 0)

    def test_verified_quotes_are_source_attributed(self):
        self.saved[0]["审核状态"] = "已核对"
        out = gate.member_context(self.saved, "02")
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["证据ID"],"EW-old-02")
        self.assertEqual(gate.member_context(self.saved, "03"), [])

    def test_duplicate_stored_id_is_blocked(self):
        out = gate.reconcile(self.doc, self.roster, [self.saved[0],self.saved[0]])
        self.assertEqual(out["status"],"REVIEW_REQUIRED")
        self.assertTrue(any(x["type"]=="DUPLICATE_OR_MISSING_ID" for x in out["conflicts"]))


if __name__ == "__main__":
    unittest.main()
