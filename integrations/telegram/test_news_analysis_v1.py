import unittest

from news_analysis_v1 import VERSION, NewsAnalysisError, validate_news_v1


class NewsAnalysisV1Tests(unittest.TestCase):
    def fixture(self):
        texts = {
            "event": ("🌐 ELLERY WESTCOTT｜财经资讯快报\n"
                      "🌍 市场地区：罗马尼亚\n📰 新闻主题：央行发表政策声明\n"
                      "🕒 事件时间：官方发布时间 2026-10-18T10:00:00Z\n"
                      "📊 影响程度：中\n📌 事件概述\n央行公布新的政策声明以及正式经济评估。"),
            "interpretation": "🔍 核心解读\n政策变化可能影响融资成本和银行预期。",
            "impact": ("📈 市场影响\n已证实反应：目前暂无经官方行情核实的市场反应。\n"
                       "潜在影响：本国银行板块可能因融资成本预期调整而重新定价。\n"
                       "尚不确定：对本币汇率及国债收益率的具体方向仍无法确定。\n"
                       "影响理由：政策信息涉及较广的融资市场和银行预期。\n"
                       "影响周期：短期关注市场定价，中期观察融资及盈利指标。"),
            "watch": ("🎯 后续关注重点\n"
                      "① 下一次央行决议公告｜观察时间/条件：以央行公布的政策日程为准\n"
                      "② 下一次价格统计公告｜观察时间/条件：以统计局公开数据发布日期为准"),
            "change": ("🔔 判断变化条件\n"
                       "增强条件：新决议进一步确认原先的政策倾向。\n"
                       "减弱条件：后续正式数据推翻原有政策假设。\n"
                       "验证依据：检查央行政策公告与统计部门后续数据。"),
        }
        claims = []
        for role, value in texts.items():
            claim = {"id": role, "content_section": role, "text": value,
                     "kind": "fact" if role == "event" else "analysis"}
            if role != "event":
                claim.update({"target_country": "RO", "conditional": True,
                              "boundary_text": "分析不等于已发生的行情。"})
            claims.append(claim)
        ledger = {"target_country": "RO", "content_standard": VERSION,
                  "local_impact_claim_id": "impact", "watch_next_claim_id": "watch",
                  "publish_claim_ids": list(texts), "claims": claims}
        return ledger, list(texts.values())

    def test_valid_structure_passes_without_claiming_source_truth(self):
        ledger, facts = self.fixture()
        result = validate_news_v1(ledger, facts)
        self.assertEqual(result["status"], "STRUCTURE_VERIFIED_ONLY")
        self.assertEqual(result["watch_point_count"], 2)

    def test_missing_new_standard_or_section_blocks(self):
        ledger, facts = self.fixture()
        del ledger["content_standard"]
        with self.assertRaisesRegex(NewsAnalysisError, "STANDARD_REQUIRED"):
            validate_news_v1(ledger, facts)
        ledger, facts = self.fixture()
        ledger["claims"] = [c for c in ledger["claims"] if c["content_section"] != "change"]
        with self.assertRaisesRegex(NewsAnalysisError, "MISSING_SECTION"):
            validate_news_v1(ledger, facts)

    def test_vague_or_non_actionable_watch_blocks(self):
        ledger, facts = self.fixture()
        watch = next(c for c in ledger["claims"] if c["content_section"] == "watch")
        watch["text"] = "🎯 后续关注重点\n① 继续关注市场变化\n② 暂无情况"
        facts[3] = watch["text"]
        with self.assertRaises(NewsAnalysisError):
            validate_news_v1(ledger, facts)

    def test_market_effect_must_distinguish_confirmed_potential_unknown(self):
        ledger, facts = self.fixture()
        impact = next(c for c in ledger["claims"] if c["content_section"] == "impact")
        impact["text"] = impact["text"].replace("已证实反应：", "市场肯定上涨：")
        facts[2] = impact["text"]
        with self.assertRaisesRegex(NewsAnalysisError, "MISSING_FIELD"):
            validate_news_v1(ledger, facts)

    def test_country_mismatch_blocks(self):
        ledger, facts = self.fixture()
        ledger["target_country"] = "FR"
        for c in ledger["claims"]:
            if c["kind"] == "analysis":
                c["target_country"] = "FR"
        with self.assertRaisesRegex(NewsAnalysisError, "COUNTRY_MISMATCH"):
            validate_news_v1(ledger, facts)


if __name__ == "__main__":
    unittest.main()
