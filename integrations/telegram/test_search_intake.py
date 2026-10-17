"""Search discoveries must reach the same evidence queue without self-approval."""
import copy
import hashlib
import unittest
from search_intake import merge_search


class SearchIntakeTests(unittest.TestCase):
    def setUp(self):
        self.edition = {'status': 'COMPLETE', 'window_start': '2026-10-17T13:00:00Z',
                        'window_end': '2026-10-17T14:00:00Z', 'candidates': [],
                        'coverage': [{'feed_id': 'existing', 'status': 'OK'}],
                        'truncated': False, 'telegram_publishable': False}
        self.search = {'searches': [{'region': r, 'query': r + ' official news',
                        'searched_at': '2026-10-17T14:01:00Z', 'status': 'OK'}
                        for r in ('RO', 'FR', 'US', 'GLOBAL')], 'articles': [{
                        'article_url': 'https://www.energy.gov/articles/release',
                        'publisher_basis_url': 'https://www.energy.gov/',
                        'published_at': '2026-10-17T13:30:00Z',
                        'source': 'US Department of Energy', 'title': 'Official release'}]}

    def inspector(self, row):
        body = 'Original publisher body for independent semantic review.'
        return {**row, 'source_text_snapshot': body,
                'source_text_sha256': hashlib.sha256(body.encode()).hexdigest(),
                'source_text_truncated': False, 'body_fetch_status': 'FETCHED_FOR_REVIEW'}

    def test_discovered_article_enters_empty_feed_queue_without_becoming_approved(self):
        result = merge_search(self.edition, self.search, self.inspector)
        self.assertEqual(len(result['candidates']), 1)
        row = result['candidates'][0]
        self.assertEqual(row['article_url'], self.search['articles'][0]['article_url'])
        self.assertEqual(row['intake_status'], 'UNREVIEWED')
        self.assertFalse(result['telegram_publishable'])
        self.assertEqual(self.edition['candidates'], [])

    def test_missing_regional_search_is_not_called_complete(self):
        self.search['searches'].pop()
        with self.assertRaisesRegex(ValueError, 'regional search'):
            merge_search(self.edition, self.search, self.inspector)

    def test_private_url_rejected_before_inspector(self):
        self.search['articles'][0]['article_url'] = 'https://127.0.0.1/secret'
        with self.assertRaises(ValueError):
            merge_search(self.edition, self.search, lambda _: self.fail('private URL fetched'))

    def test_old_article_is_recorded_as_excluded_without_retiming(self):
        self.search['articles'][0]['published_at'] = '2026-10-16T13:30:00Z'
        result = merge_search(self.edition, self.search, lambda _: self.fail('old article fetched'))
        self.assertEqual(result['candidates'], [])
        self.assertEqual(result['search_intake']['excluded'][0]['reason'], 'OUTSIDE_WINDOW')
        self.assertEqual(result['window_end'], self.edition['window_end'])

    def test_unreadable_candidate_is_retained_and_blocks_complete_comparison(self):
        def unavailable(row):
            return {**row, 'body_fetch_status': 'UNAVAILABLE'}
        result = merge_search(self.edition, self.search, unavailable)
        self.assertEqual(len(result['candidates']), 1)
        self.assertEqual(result['status'], 'INCOMPLETE')

    def test_duplicate_url_does_not_fill_another_slot(self):
        self.search['articles'] *= 2
        result = merge_search(self.edition, self.search, self.inspector)
        self.assertEqual(len(result['candidates']), 1)

    def test_failed_feed_stays_incomplete_after_successful_search(self):
        self.edition['status'] = 'INCOMPLETE'
        self.assertEqual(merge_search(self.edition, self.search, self.inspector)['status'], 'INCOMPLETE')

    def test_failed_search_or_invalid_hash_does_not_silently_drop_unknown_news(self):
        bad = copy.deepcopy(self.search)
        bad['searches'][0]['status'] = 'ERROR'
        with self.assertRaises(ValueError):
            merge_search(self.edition, bad, self.inspector)
        def wrong_hash(row):
            return {**self.inspector(row), 'source_text_sha256': 'wrong'}
        self.assertEqual(merge_search(self.edition, self.search, wrong_hash)['status'], 'INCOMPLETE')

    def test_candidate_cap_is_an_error_not_a_complete_truncated_ranking(self):
        with self.assertRaisesRegex(ValueError, 'candidate limit'):
            merge_search(self.edition, self.search, self.inspector, max_candidates=0)
