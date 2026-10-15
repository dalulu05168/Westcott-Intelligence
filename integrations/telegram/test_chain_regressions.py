"""Regression coverage for evidence bypass, identity and duplicate releases."""
import copy
import io
import contextlib
import os
import sys
import unittest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(__file__))
import bridge
import news_radar as radar
import reviewed_publish as pub
import source_media as media
import test_reviewed_publish as fixtures


class ChainRegressions(unittest.TestCase):
    def test_raw_send_cannot_bypass_evidence_ledger(self):
        with patch.object(bridge, 'send_group_news', return_value={}) as send, contextlib.redirect_stderr(io.StringIO()):
            with patch.dict(os.environ, {'WESTCOTT_APPROVED_NEWS_TEXT': '===== 资讯助理 =====\n未经核验'}, clear=True):
                self.assertEqual(bridge.main(['send']), 1)
            send.assert_not_called()

    def test_claim_renumbering_does_not_change_duplicate_key(self):
        ledger = fixtures.OriginalArticleTests().ledger()
        first = pub.prepare(ledger, 'news/approved/first.json')
        ledger['claims'][0]['id'] = 'new-local-id'
        ledger['publish_claim_ids'] = ['new-local-id']
        self.assertEqual(first['fingerprint'], pub.prepare(ledger, 'news/approved/renamed.json')['fingerprint'])

    def test_changed_fact_at_same_url_is_distinct_update(self):
        ledger = fixtures.OriginalArticleTests().ledger()
        first = pub.prepare(ledger, 'news/approved/first.json')
        ledger['claims'][0]['text'] = '经核验的后续新增事实。'
        self.assertNotEqual(first['fingerprint'], pub.prepare(ledger, 'news/approved/update.json')['fingerprint'])

    def test_query_identifies_different_article(self):
        result = media.inspect_markup('https://news.example.org/story?id=1',
            '<head><link rel="canonical" href="https://news.example.org/story?id=2"></head>')
        self.assertFalse(result['canonical_matches_article'])

    def test_body_snapshot_excludes_script_content(self):
        result = media.inspect_markup('https://news.example.org/story',
            '<head><title>News</title></head><body><script>fake claim</script><article>Official&nbsp;fact.</article></body>')
        self.assertEqual(result.get('source_text'), 'Official fact.')
        self.assertEqual(len(result.get('source_text_sha256', '')), 64)

    def test_bvb_translation_attachments_grouped_with_html(self):
        base = {'title': 'S.N.G.N. ROMGAZ S.A. (SNG)', 'published_at': '2026-10-15T08:34:12+00:00',
                'source': 'Bucharest Stock Exchange', 'feed_id': 'bvb_market'}
        page = 'https://bvb.ro/FinancialInstruments/SelectedData/NewsItem/SNG-contract/7B957'
        rows = [{**base, 'article_url': 'https://bvb.ro/infocont/infocont26/SNG_report-ro.pdf'},
                {**base, 'article_url': 'https://bvb.ro/infocont/infocont26/SNG_report-en.pdf'},
                {**base, 'article_url': page}]
        choices = radar.pick_candidates(rows, datetime(2026, 10, 15, 10, tzinfo=timezone.utc))
        self.assertEqual(len(choices), 1)
        self.assertEqual(choices[0]['article_url'], page)
        self.assertEqual(len(choices[0]['related_source_urls']), 3)
        self.assertFalse(choices[0]['telegram_publishable'])

    def test_unrelated_bvb_pages_not_merged_for_same_issuer_timestamp(self):
        base = {'title': 'ROMGAZ (SNG)', 'published_at': '2026-10-15T08:34:12+00:00',
                'source': 'Bucharest Stock Exchange', 'feed_id': 'bvb_market'}
        rows = [{**base, 'article_url': 'https://bvb.ro/FinancialInstruments/SelectedData/NewsItem/SNG/a'},
                {**base, 'article_url': 'https://bvb.ro/FinancialInstruments/SelectedData/NewsItem/SNG/b'}]
        self.assertEqual(len(radar.pick_candidates(rows, datetime(2026, 10, 15, 10, tzinfo=timezone.utc))), 2)

    def test_candidate_snapshot_is_not_review_approval(self):
        row = {'article_url': 'https://news.example.org/story', 'body_read': False, 'telegram_publishable': False}
        enriched = radar.inspect_candidate_image(row, inspector=lambda _: {
            'source_text': 'Official fact.', 'source_text_sha256': 'a' * 64,
            'canonical_matches_article': True, 'image_candidate_url': None})
        self.assertEqual(enriched.get('source_text_snapshot'), 'Official fact.')
        self.assertFalse(enriched['body_read'])
        self.assertFalse(enriched['telegram_publishable'])

    def test_changed_original_excerpt_blocks_before_telegram(self):
        prepared = pub.prepare(fixtures.OriginalArticleTests().ledger(), 'news/approved/reviewed.json')
        with patch.object(pub, 'inspect_article', return_value={
            'source_text': 'Unrelated material', 'canonical_matches_article': True}), \
                patch.object(pub, 'reserve') as reserve:
            with self.assertRaisesRegex(pub.PublicationError, 'excerpt'):
                pub.publish(prepared, {'PUBLISH_CONFIRMATION': pub.CONFIRM})
            reserve.assert_not_called()

    def test_original_evidence_recheck_records_hash(self):
        prepared = pub.prepare(fixtures.OriginalArticleTests().ledger(), 'news/approved/reviewed.json')
        with patch.object(pub, 'inspect_article', return_value={
            'source_text': '已核实的财经事实。', 'canonical_matches_article': True}):
            result = pub.confirm_original_evidence(prepared)
        self.assertEqual(len(result[0]['source_text_sha256']), 64)

    def test_old_article_cannot_be_refreshed_by_new_review_timestamp(self):
        ledger = fixtures.OriginalArticleTests().ledger()
        ledger['sources']['s1']['published_at'] = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
        with self.assertRaises(pub.PublicationError):
            pub.prepare(ledger, 'news/approved/old.json')


if __name__ == '__main__':
    unittest.main()
