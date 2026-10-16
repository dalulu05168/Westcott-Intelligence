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
    def test_same_event_different_evidence_and_hour_is_atomically_blocked(self):
        records = {}
        def atomic(path, record, token, repo, sha=None):
            if path in records:
                raise pub.PublicationError('already reserved')
            records[path] = record
            return 'sha'
        env = {'GITHUB_TOKEN': 'secret', 'GITHUB_REPOSITORY': 'owner/repo', 'GITHUB_REF_NAME': 'main'}
        first = pub.prepare(fixtures.OriginalArticleTests().ledger(), 'news/approved/first-event.json')
        first['target_country'] = 'RO'
        first['editorial_acceptance'] = {'slot_key': 'RO-20261016T09-01',
            'event_lock_key': 'a' * 64, 'window_end': '2026-10-16T09:37:00+00:00'}
        second = copy.deepcopy(first)
        second.update(fingerprint='b' * 64, claim_evidence_keys=['different-pdf-evidence'])
        second['editorial_acceptance']['slot_key'] = 'RO-20261016T10-02'
        with patch.object(pub, 'github_write', side_effect=atomic):
            pub.reserve(first, env)
            with self.assertRaises(pub.PublicationError):
                pub.reserve(second, env)

    def test_cross_hour_or_end_of_hour_cannot_begin_telegram_send(self):
        acceptance = {'quota_hour_key': 'RO-20261016T09'}
        for stamp in ('2026-10-16T10:00:01+00:00', '2026-10-16T09:59:50+00:00'):
            with self.assertRaises(pub.PublicationError):
                pub.check_delivery_hour(acceptance, 'RO', datetime.fromisoformat(stamp))
        pub.check_delivery_hour(acceptance, 'RO', datetime.fromisoformat('2026-10-16T09:52:00+00:00'))

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

    def test_changed_copy_has_same_underlying_evidence_identity(self):
        ledger = fixtures.OriginalArticleTests().ledger()
        first = pub.prepare(ledger, 'news/approved/first.json')
        ledger['claims'][0]['text'] = '经核验的后续新增事实。'
        self.assertNotEqual(first['fingerprint'], pub.prepare(ledger, 'news/approved/update.json')['fingerprint'])
        self.assertEqual(first['claim_evidence_keys'], pub.prepare(ledger, 'news/approved/update.json')['claim_evidence_keys'])

    def test_genuinely_new_evidence_at_same_url_has_distinct_identity(self):
        ledger = fixtures.OriginalArticleTests().ledger()
        first = pub.prepare(ledger, 'news/approved/first.json')
        ledger['claims'][0]['text'] = '新增已核实事实。'
        ledger['claims'][0]['evidence'][0]['excerpt'] = 'A genuinely new official fact.'
        second = pub.prepare(ledger, 'news/approved/update.json')
        self.assertNotEqual(first['claim_evidence_keys'], second['claim_evidence_keys'])

    def test_rewording_cannot_escape_delivered_or_pending_atomic_claim_lock(self):
        for state in ('DELIVERED', 'PENDING_DO_NOT_RETRY'):
            with self.subTest(state=state):
                records = {}
                def atomic_write(path, record, token, repo, sha=None):
                    if path in records and sha is None:
                        raise pub.PublicationError('Publication already reserved')
                    records[path] = copy.deepcopy(record)
                    return 'sha'
                ledger = fixtures.OriginalArticleTests().ledger()
                first = pub.prepare(ledger, 'news/approved/first.json')
                env = {'GITHUB_TOKEN': 'secret', 'GITHUB_REPOSITORY': 'owner/repo', 'GITHUB_REF_NAME': 'main'}
                with patch.object(pub, 'github_write', side_effect=atomic_write):
                    path, record, sha = pub.reserve(first, env)
                    records[path]['state'] = state
                    ledger['claims'][0]['text'] = '同一事实的另一种中文表述。'
                    ledger['claims'][0]['id'] = 'renamed-claim'
                    ledger['publish_claim_ids'] = ['renamed-claim']
                    ledger['event_id'] = 'renamed-event-00002'
                    second = pub.prepare(ledger, 'news/approved/renamed.json')
                    with self.assertRaisesRegex(pub.PublicationError, 'reserved'):
                        pub.reserve(second, env)

    def test_country_hour_slot_blocks_second_story_but_allows_other_country(self):
        records = {}
        def atomic_write(path, record, token, repo, sha=None):
            if path in records and sha is None:
                raise pub.PublicationError('Already reserved')
            records[path] = copy.deepcopy(record)
            return 'sha'
        env = {'GITHUB_TOKEN': 'secret', 'GITHUB_REPOSITORY': 'owner/repo', 'GITHUB_REF_NAME': 'main'}
        ledger = fixtures.OriginalArticleTests().ledger()
        ledger['target_country'] = 'RO'
        first = pub.prepare(ledger, 'news/approved/first.json')
        first['editorial_acceptance'] = {'slot_key': 'RO-20261016T09', 'window_end': '2026-10-16T09:37:00+00:00'}
        with patch.object(pub, 'github_write', side_effect=atomic_write):
            pub.reserve(first, env)
            other = copy.deepcopy(ledger)
            other['claims'][0]['text'] = 'Different genuinely new story.'
            other['claims'][0]['evidence'][0]['excerpt'] = 'New original evidence.'
            second = pub.prepare(other, 'news/approved/second.json')
            second['editorial_acceptance'] = first['editorial_acceptance']
            with self.assertRaises(pub.PublicationError):
                pub.reserve(second, env)
            ledger['target_country'] = 'FR'
            france = pub.prepare(ledger, 'news/approved/france.json')
            france['editorial_acceptance'] = {'slot_key': 'FR-20261016T09', 'window_end': '2026-10-16T09:37:00+00:00'}
            pub.reserve(france, env)

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
                patch.object(pub, 'reserve') as reserve, \
                patch.object(pub, 'validate_release', return_value={}):
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
