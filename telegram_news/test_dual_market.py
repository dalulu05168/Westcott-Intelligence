"""Offline regression tests for the independent Romania/France news streams."""
import os
import unittest
import json
import fitz
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup
from dual_market import (PARIS, PROFILES, caption, due, host_allowed, fetch_original,
                         materiality, official_image, pick, us_quote_snapshot, feed_items, localize)

TZ = ZoneInfo("Europe/Bucharest")


class TwoCountryTests(unittest.TestCase):
    def test_morning_same_local_clock_is_one_hour_apart(self):
        ro_morning = datetime(2026, 10, 16, 7, 30, tzinfo=TZ).astimezone(timezone.utc)
        fr_morning = datetime(2026, 10, 16, 7, 30, tzinfo=PARIS).astimezone(timezone.utc)
        self.assertEqual(3600, (fr_morning - ro_morning).total_seconds())
        self.assertEqual((["RO"], "morning"), due(ro_morning, ""))
        self.assertEqual((["FR"], "morning"), due(fr_morning, ""))

    def test_hourly_pair_at_one_actual_instant(self):
        instant = datetime(2026, 10, 16, 9, 0, tzinfo=PARIS)
        self.assertEqual(10, instant.astimezone(TZ).hour)
        self.assertEqual((["RO", "FR"], "hourly"), due(instant, ""))

    def test_daylight_saving_and_weekends(self):
        instant = datetime(2026, 11, 2, 9, 0, tzinfo=PARIS)
        self.assertEqual(10, instant.astimezone(TZ).hour)
        self.assertEqual((["RO", "FR"], "hourly"), due(instant, ""))
        weekend = datetime(2026, 10, 17, 9, 0, tzinfo=PARIS)
        self.assertEqual(([], ""), due(weekend, ""))

    def test_country_labels_and_language(self):
        self.assertEqual(("🔵", "zh-CN"), (PROFILES["RO"]["marker"], PROFILES["RO"]["lang"]))
        self.assertEqual(("🔴", "zh-CN"), (PROFILES["FR"]["marker"], PROFILES["FR"]["lang"]))
        self.assertEqual("罗马尼亚", PROFILES["RO"]["label"])
        self.assertEqual("法国", PROFILES["FR"]["label"])

    def test_source_image_must_resolve_on_original_official_site(self):
        record = {"source": "AMF", "url": "https://www.amf-france.org/fr/actualites/story"}
        good = BeautifulSoup('<meta property="og:image" content="/sites/default/files/2026/07/story.jpg">', "html.parser")
        self.assertEqual("https://www.amf-france.org/sites/default/files/2026/07/story.jpg",
                         official_image(good, record))
        bad = BeautifulSoup('<meta property="og:image" content="https://random-cdn.example/photo.jpg">', "html.parser")
        self.assertIsNone(official_image(bad, record))
        logo = BeautifulSoup('<meta property="og:image" content="/logo.jpg">', "html.parser")
        self.assertIsNone(official_image(logo, record))

    def test_unofficial_article_url_rejected(self):
        self.assertFalse(host_allowed("http://www.amf-france.org/news", ("amf-france.org",)))
        self.assertFalse(host_allowed("https://amf-france.org.evil.test/story",
                                      ("amf-france.org",)))

    def test_hourly_old_event_suppressed(self):
        now = datetime(2026, 10, 16, 11, 0, tzinfo=TZ)
        record = {"source": "BVB", "title": "Banca profit report",
                  "id": "x", "published": (now-timedelta(hours=4)).isoformat()}
        self.assertIsNone(materiality(record, "RO", now, "hourly", {}))

    def test_local_dedup_is_per_country(self):
        now = datetime(2026, 10, 16, 11, 0, tzinfo=TZ)
        record = {"source": "ECB", "title": "Interest rates and inflation",
                  "id": "shared", "published": (now-timedelta(minutes=30)).isoformat()}
        sent = {"RO|shared": {"message_id": 123}}
        self.assertEqual([], pick([record], "RO", now, "hourly", {"sent": sent}))
        self.assertEqual([record], pick([record], "FR", now, "hourly", {"sent": sent}))

    def test_reject_bogus_market_close_snapshot(self):
        with patch.dict(os.environ, {"TWELVE_DATA_API_KEY": ""}):
            self.assertIsNone(us_quote_snapshot())

    def test_only_one_caption_for_photo_and_matching_country_path(self):
        now = datetime(2026, 10, 16, 11, 0, tzinfo=TZ)
        article = {"url": "https://www.bvb.ro/AboutUs/MediaCenter/PressItem/short/123",
                   "source": "BVB"}
        text = {"headline": "罗马尼亚金融公告", "verified_event": "官方披露已发布",
                "local_market_path": "BET 指数相关板块影响仍待核实",
                "next_watch": "关注下一份上市公司报告"}
        result = caption("RO", article, text, "", now, "hourly")
        self.assertIn("🔵 罗马尼亚｜财经资讯快报", result)
        self.assertIn("BET 指数相关板块影响仍待核实", result)
        self.assertNotIn("Impact condiționat", result)
        self.assertLessEqual(len(result), 1024)


    def test_bvb_issuer_feed_uses_original_time_and_prevents_unofficial_link(self):
        fixture = """<rss version="2.0"><channel>
        <item><title>Banca publica rezultate financiare</title>
        <link>https://bvb.ro/FinancialInstruments/SelectedData/NewsItem/SNG-raport/ABCDE</link>
        <pubDate>Fri, 16 Oct 2026 06:40:00 GMT</pubDate></item>
        <item><title>Malicious entry</title>
        <link>https://bvb.ro.attacker.test/notices</link>
        <pubDate>Fri, 16 Oct 2026 06:42:00 GMT</pubDate></item>
        <item><title>Missing date entry</title>
        <link>https://bvb.ro/notice2</link></item></channel></rss>"""
        response = Mock(status_code=200, content=fixture.encode("utf-8"))
        response.raise_for_status.return_value = None
        with patch("dual_market.SESSION.get", return_value=response):
            items = feed_items("BVB_FIN", "https://www.bvb.ro/Rss2/LastFinancialData.ashx", TZ)
        self.assertEqual(1, len(items))
        self.assertEqual("BVB_FIN", items[0]["source"])
        self.assertIn("2026-10-16T09:40", items[0]["published"])
        self.assertTrue(items[0]["url"].endswith("/ABCDE"))

    def test_local_relevance_rejects_nonfinancial_marketing(self):
        now = datetime(2026, 10, 16, 11, 0, tzinfo=PARIS)
        record = {"source": "FR_GOV", "title": "Journée du patrimoine: visite",
                  "id": "visitor", "published": (now-timedelta(minutes=20)).isoformat()}
        self.assertIsNone(materiality(record, "FR", now, "hourly", {}))
        record["title"] = "Énergie: tarifs et financement du secteur"
        self.assertIsNotNone(materiality(record, "FR", now, "hourly", {}))


    def test_central_bank_rate_decision_beats_generic_energy_announcement(self):
        now = datetime(2026, 10, 16, 10, 0, tzinfo=PARIS)
        timestamp = (now - timedelta(minutes=18)).isoformat()
        items = [
            {"source": "FR_GOV", "id": "gov", "title": "Énergie: réunion de concertation",
             "published": timestamp},
            {"source": "ECB", "id": "ecb", "title": "ECB announces monetary policy interest rates decision",
             "published": timestamp},
        ]
        first = pick(items, "FR", now, "hourly", {"sent": {}})[0]
        self.assertEqual("ecb", first["id"])


    def test_bvb_official_pdf_source_and_original_page_render(self):
        pdf = fitz.open()
        page = pdf.new_page()
        disclosure = ("SOCIETATEA ABC S.A. Raport financiar: venituri și profit. "
                      "Acest document descrie raportul aprobat și datele contabile, "
                      "fără a indica randamente de piață. " * 3)
        page.insert_textbox(fitz.Rect(45, 80, 560, 500), disclosure, fontsize=10)
        payload = pdf.tobytes()
        pdf.close()
        fake_response = Mock(content=payload, headers={"Content-Type": "application/pdf"})
        fake_response.raise_for_status.return_value = None
        record = {
            "source": "BVB_FIN",
            "url": "https://bvb.ro/infocont/infocont26/ABC_document.pdf",
            "title": "ABC S.A. - Raport financiar",
        }
        with patch("dual_market.SESSION.get", return_value=fake_response):
            verified = fetch_original(record)
        self.assertIsNotNone(verified)
        media, body = verified
        self.assertEqual("official_pdf_page1", media["kind"])
        self.assertTrue(media["preview_png"].startswith(bytes([137, 80, 78, 71])))
        self.assertIn("Raport financiar", body)

    def test_unsupported_non_official_pdf_remains_blocked(self):
        record = {
            "source": "BVB_FIN",
            "url": "https://an-unofficial-site.example/foo.pdf",
            "title": "Example",
        }
        with patch("dual_market.SESSION.get") as req:
            self.assertIsNone(fetch_original(record))
            req.assert_not_called()


    def test_us_after_market_window_sends_same_two_country_pair(self):
        # Friday NY regular session close corresponds to Friday 22:00 Paris
        # and later Friday after-hours are covered until Saturday 02:00 Paris.
        friday = datetime(2026, 10, 16, 23, 0, tzinfo=PARIS)
        saturday_after = datetime(2026, 10, 17, 1, 0, tzinfo=PARIS)
        self.assertEqual((["RO", "FR"], "hourly"), due(friday, ""))
        self.assertEqual((["RO", "FR"], "hourly"), due(saturday_after, ""))
        self.assertEqual(([], ""), due(datetime(2026, 10, 17, 9, tzinfo=PARIS), ""))

    def test_morning_without_market_data_never_invents_index_values(self):
        now = datetime(2026, 10, 16, 7, 30, tzinfo=TZ)
        record = {"url": "https://bvb.ro/news", "source": "BVB"}
        analysis = {"headline": "罗马尼亚财务报告", "verified_event": "官方公告已核实",
                    "local_market_path": "可能影响相关板块，行情变化尚未确认",
                    "next_watch": "关注下次官方披露"}
        text = caption("RO", record, analysis, "", now, "morning", None)
        self.assertIn("数据尚未核实", text)
        self.assertNotIn("Nasdaq Composite:", text)


    def test_both_countries_publish_same_language_distinct_markets(self):
        ro = {"source": "BVB", "url": "https://bvb.ro/official"}
        fr = {"source": "AMF", "url": "https://www.amf-france.org/fr/official"}
        ro_analysis = {"headline": "罗马尼亚企业公告", "verified_event": "银行债券公告已发布",
                       "local_market_path": "对布加勒斯特市场的影响需结合流动性观察",
                       "next_watch": "观察 BET 与成交量"}
        fr_analysis = {"headline": "法国监管公告", "verified_event": "法国金融监管机构发布公告",
                       "local_market_path": "对法国市场的影响需结合 CAC 40 相关板块",
                       "next_watch": "观察后续正式公告"}
        now = datetime(2026, 10, 16, 10, 0, tzinfo=timezone.utc)
        ro_text = caption("RO", ro, ro_analysis, "", now, "hourly")
        fr_text = caption("FR", fr, fr_analysis, "", now, "hourly")
        self.assertIn("🔵 罗马尼亚｜财经资讯快报", ro_text)
        self.assertIn("🔴 法国｜财经资讯快报", fr_text)
        self.assertIn("对罗马尼亚市场的潜在影响", ro_text)
        self.assertIn("对法国市场的潜在影响", fr_text)
        self.assertIn("官方来源", fr_text)
        self.assertNotIn("Actualité financière", fr_text)
        self.assertNotIn("Știrea financiară", ro_text)

    def test_ai_editor_chinese_output_from_foreign_official_original(self):
        source = ("Communiqué officiel sur les banques et la politique monétaire, "
                  "publié par une autorité financière européenne.")
        record = {"source": "AMF", "title": "Communiqué officiel",
                  "url": "https://www.amf-france.org/fr/test"}
        valid = {"headline": "法国金融监管公告", "verified_event": "监管部门发布金融公告",
                 "local_market_path": "法国银行股可能受到影响，实际反应尚待确认",
                 "next_watch": "关注监管部门进一步披露",
                 "evidence_excerpt": source[:65]}
        response = Mock(ok=True)
        response.json.return_value = {"output": [
            {"content": [{"type": "output_text", "text": json.dumps(valid, ensure_ascii=False)}]}
        ]}
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-secret", "OPENAI_NEWS_MODEL": "test-model"}), \
             patch("dual_market.requests.post", return_value=response) as post:
            result = localize(record, source, "FR")
        self.assertEqual(valid, result)
        sent_prompt = post.call_args.kwargs["json"]["instructions"]
        self.assertIn("Simplified Chinese ONLY", sent_prompt)
        self.assertIn("Romania and France", sent_prompt)
        self.assertIn("verbatim source-language quotation", sent_prompt)

    def test_ai_editor_rejects_non_chinese_news_text(self):
        source = ("Communiqué officiel sur les banques et la politique monétaire, "
                  "publié par une autorité financière européenne.")
        record = {"source": "AMF", "title": "Communiqué officiel",
                  "url": "https://www.amf-france.org/fr/test"}
        invalid = {"headline": "Actualité financière",
                   "verified_event": "Décision officielle publiée",
                   "local_market_path": "Impact possible sur CAC 40",
                   "next_watch": "Surveiller l'annonce",
                   "evidence_excerpt": source[:65]}
        response = Mock(ok=True)
        response.json.return_value = {"output": [
            {"content": [{"type": "output_text", "text": json.dumps(invalid, ensure_ascii=False)}]}
        ]}
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-secret", "OPENAI_NEWS_MODEL": "test-model"}), \
             patch("dual_market.requests.post", return_value=response):
            self.assertIsNone(localize(record, source, "FR"))


if __name__ == "__main__":
    unittest.main()
