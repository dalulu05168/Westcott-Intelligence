"""Regression tests: data preparation, not LLM voice-quality claims."""
import importlib.util
from pathlib import Path
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "tools/prepare_numbered_rewrite.py"
spec = importlib.util.spec_from_file_location("numbered_voice_loader", SOURCE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class TestNumberedVoiceRewrite(unittest.TestCase):
    def test_parse_multi_person(self):
        result = module.load_context("14男：我还想看看BRD是否能站稳2.02 RON。\n02女：我得再算算。")
        self.assertEqual([x["label"] for x in result["turns"]], ["14男", "02女"])
        self.assertIn("2.02 RON", result["turns"][0]["original"])

    def test_explicit_command(self):
        result = module.load_context("按14男口吻改：我还是想再看看。")
        self.assertEqual(result["turns"][0]["label"], "14男")

    def test_normalize_number(self):
        result = module.load_context("2女：数字还需要确认。")
        self.assertEqual(result["turns"][0]["label"], "02女")

    def test_gender_conflict_rejected(self):
        with self.assertRaises(module.VoiceInputError):
            module.load_context("02男：明天再看看。")

    def test_missing_label_rejected(self):
        with self.assertRaises(module.VoiceInputError):
            module.load_context("我想再看看。")

    def test_out_of_range_rejected(self):
        with self.assertRaises(module.VoiceInputError):
            module.load_context("66男：我想再看看。")

    def test_profiles_02_14_differ_despite_same_job(self):
        result = module.load_context("02女：我先看看。\n14男：我先看看。")
        people = result["people"]
        self.assertEqual(people["02"]["identity"]["occupation"], "会计师")
        self.assertEqual(people["14"]["identity"]["occupation"], "会计师")
        self.assertNotEqual(
            people["02"]["creative_personality_not_approved"]["main_behavior"],
            people["14"]["creative_personality_not_approved"]["main_behavior"])
        self.assertTrue(people["02"]["historic_speech"]["examples"])
        self.assertTrue(people["14"]["historic_speech"]["examples"])

    def test_43_65_only_text_edit_not_story(self):
        result = module.load_context("43男：先看看价格。")
        self.assertEqual(result["people"]["43"]["participation"], "edit_text_only_not_authorized_in_story")
        self.assertEqual(result["people"]["43"]["historic_speech"]["examples"], [])

    def test_65_profiles_resolve_to_authoritative_roster(self):
        for n in range(1, 66):
            with self.subTest(n=n):
                id_str = f"{n:02d}"
                r = module.load_context(f"{id_str}：这句话只用于匹配编号。")
                self.assertIn(id_str, r["people"])
                self.assertEqual(r["turns"][0]["person_id"], id_str)
                self.assertFalse(r["people"][id_str]["historic_speech"]["approved_style"])

    def test_original_facts_are_unchanged_in_context(self):
        source = "BRD 跌了3.2%，我暂时不买，等10月23日再说。"
        result = module.load_context("14男：" + source)
        self.assertEqual(result["turns"][0]["original"], source)

if __name__ == "__main__":
    unittest.main()
