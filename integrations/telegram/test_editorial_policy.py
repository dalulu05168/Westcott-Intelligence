"""Acceptance tests for the user's mandatory photo and per-country top-one rule."""
import copy
import hashlib
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
sys.path.insert(0, os.path.dirname(__file__))
import editorial_policy as policy


class EditorialPolicyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.now = datetime(2026, 10, 16, 9, 52, tzinfo=timezone.utc)
        self.body = 'Official source evidence for a monetary policy announcement.'
        self.digest = hashlib.sha256(self.body.encode()).hexdigest()
        self.edition = {
            'status': 'COMPLETE', 'window_start': '2026-10-16T08:37:00+00:00',
            'window_end': '2026-10-16T09:37:00+00:00',
            'coverage': [{'feed_id': 'test_feed', 'status': 'OK'}],
            'required_feed_ids': ['test_feed'], 'truncated': False,
            'candidates': [self.candidate('a'), self.candidate('b')],
        }
        self.path = 'news/editions/20261016t0937z.json'
        (self.root / self.path).parent.mkdir(parents=True)
        self.save()
        self.prepared = {
            'target_country': 'RO', 'media': {'image_url': 'https://publisher.example/story.jpg',
                'image_decision': 'verified_original_publisher_photo',
                'article_url': 'https://publisher.example/a'},
            'sources': ['https://publisher.example/a'],
            'local_impact_claim_id': 'impact', 'watch_next_claim_id': 'watch',
            'claim_ids': ['fact', 'impact', 'watch'],
            'claim_kinds': {'fact': 'fact', 'impact': 'analysis', 'watch': 'analysis'},
            'claim_countries': {'impact': 'RO', 'watch': 'RO'},
            'hourly_selection': {'edition_path': self.path, 'edition_sha256': self.edition_digest,
                'selected_candidate_id': 'a', 'assessments': [self.review('a', 5), self.review('b', 3)]},
        }

    def candidate(self, ident):
        return {'id': ident, 'article_url': 'https://publisher.example/' + ident,
                'published_at': '2026-10-16T09:15:00+00:00',
                'source_text_snapshot': self.body, 'source_text_sha256': self.digest,
                'source_text_truncated': False, 'body_fetch_status': 'FETCHED_FOR_REVIEW'}

    def review(self, ident, score):
        return {'candidate_id': ident, 'relevant': True, 'reviewed_by': 'reviewer',
                'body_sha256': self.digest, 'support_excerpt': 'monetary policy announcement',
                'rationale': '根据原文，比较当地市场覆盖、传导渠道、事件量级及即时影响。',
                'scores': {key: score for key in policy.WEIGHTS}}

    def save(self):
        text = json.dumps(self.edition, ensure_ascii=False, sort_keys=True)
        (self.root / self.path).write_text(text, encoding='utf-8')
        self.edition_digest = hashlib.sha256(text.encode()).hexdigest()

    def check(self, prepared=None):
        return policy.validate_release(prepared or self.prepared, self.root, self.now,
                                       expected_feed_ids={'test_feed'})

    def test_valid_top_one_returns_country_hour_slot(self):
        result = self.check()
        self.assertEqual(result['winner_id'], 'a')
        self.assertEqual(result['slot_key'], 'RO-20261016T09')

    def test_missing_photo_cannot_use_link_preview(self):
        self.prepared['media']['image_url'] = None
        with self.assertRaisesRegex(policy.PolicyError, 'photo'):
            self.check()

    def test_missing_country_or_comparison_blocks(self):
        for key in ('target_country', 'hourly_selection'):
            changed = copy.deepcopy(self.prepared)
            del changed[key]
            with self.assertRaises(policy.PolicyError):
                self.check(changed)

    def test_lower_rank_cannot_be_selected_even_with_photo(self):
        self.prepared['hourly_selection']['selected_candidate_id'] = 'b'
        self.prepared['media']['article_url'] = 'https://publisher.example/b'
        with self.assertRaisesRegex(policy.PolicyError, 'highest'):
            self.check()

    def test_omitted_candidate_or_duplicate_review_blocks(self):
        for reviews in ([self.review('a', 5)], [self.review('a', 5), self.review('a', 5)]):
            self.prepared['hourly_selection']['assessments'] = reviews
            with self.assertRaises(policy.PolicyError):
                self.check()

    def test_incomplete_or_truncated_coverage_cannot_claim_maximum(self):
        for field, value in [('status', 'INCOMPLETE'), ('truncated', True), ('coverage', [])]:
            with self.subTest(field=field):
                self.edition[field] = value
                self.save()
                self.prepared['hourly_selection']['edition_sha256'] = self.edition_digest
                with self.assertRaises(policy.PolicyError):
                    self.check()
                self.edition[field] = {'status': 'COMPLETE', 'truncated': False,
                    'coverage': [{'feed_id': 'test_feed', 'status': 'OK'}]}[field]

    def test_outside_hour_and_stale_edition_block(self):
        self.edition['candidates'][0]['published_at'] = '2026-10-16T08:00:00+00:00'
        self.save()
        self.prepared['hourly_selection']['edition_sha256'] = self.edition_digest
        with self.assertRaises(policy.PolicyError):
            self.check()
        with self.assertRaises(policy.PolicyError):
            policy.validate_release(self.prepared, self.root, self.now + timedelta(hours=2),
                                    expected_feed_ids={'test_feed'})

    def test_unread_body_or_fabricated_evidence_blocks(self):
        self.prepared['hourly_selection']['assessments'][0]['support_excerpt'] = 'invented'
        with self.assertRaises(policy.PolicyError):
            self.check()

    def test_country_specific_impact_and_watch_are_required(self):
        self.prepared['local_impact_claim_id'] = 'fact'
        with self.assertRaises(policy.PolicyError):
            self.check()

    def test_path_traversal_and_wrong_digest_block(self):
        for path in ('../../private.json', 'news/approved/test.json'):
            self.prepared['hourly_selection']['edition_path'] = path
            with self.assertRaises(policy.PolicyError):
                self.check()

    def test_low_impact_hour_stays_silent(self):
        self.prepared['hourly_selection']['assessments'] = [self.review('a', 1), self.review('b', 2)]
        with self.assertRaises(policy.PolicyError):
            self.check()

    def test_publisher_blocks_legacy_text_only_before_any_send(self):
        from unittest.mock import patch
        import reviewed_publish as pub
        import test_reviewed_publish as fixtures
        prepared = pub.prepare(fixtures.OriginalArticleTests().ledger(), 'news/approved/test.json')
        prepared['target_country'] = 'RO'
        with patch.object(pub, 'reserve') as reserve, patch.object(pub, 'send_group_news_from_official_article') as send:
            with self.assertRaisesRegex(pub.PublicationError, 'photo'):
                pub.publish(prepared, {'PUBLISH_CONFIRMATION': pub.CONFIRM})
            reserve.assert_not_called()
            send.assert_not_called()

    def test_original_article_body_photo_is_accepted_for_source_match(self):
        from unittest.mock import patch
        import reviewed_publish as pub
        prepared = {'media': {'article_url': 'https://publisher.example/a',
                             'image_url': 'https://publisher.example/story.jpg'}}
        with patch.object(pub, 'inspect_article', return_value={
            'image_candidate_url': None, 'canonical_matches_article': True,
            'article_image_candidates': [{'url': 'https://publisher.example/story.jpg'}]}):
            pub.confirm_original_photo_source(prepared)


if __name__ == '__main__':
    unittest.main()
