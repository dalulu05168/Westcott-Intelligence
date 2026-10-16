import copy
import json
from pathlib import Path
import unittest

try:
    import editorial_execution as execution
except ImportError:
    execution = None

ROOT = Path(__file__).resolve().parents[1]


class EditorialExecutionTest(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(execution, 'Missing mandatory editorial execution layer')

    def context(self, members=('10', '15')):
        return execution.build_context(ROOT, '2026-10-16', list(members))

    def test_oct16_archive_parses_staff_and_member_in_original_order(self):
        archive = json.loads((ROOT / 'memory/daily/2026-10-16/formal-google-doc-snapshot.json').read_text())
        adapted, live = execution.adapt_snapshot(archive, '2026-10-16')
        self.assertFalse(live)
        days, conflicts = execution.snapshot_messages(adapted, __import__('datetime').date(2026, 10, 16),
                                                       {p['id']: p for p in json.loads((ROOT / 'skills/p004-chat-suite/characters/final-identity-65.json').read_text())['people']})
        rows = days['2026-10-16']
        self.assertGreater(len(rows), 25)
        self.assertEqual(rows[0]['speaker_id'], 'news_assistant')
        self.assertEqual(rows[-1]['speaker_id'], 'news_assistant')
        self.assertIn('下午再见', rows[-1]['text'])
        self.assertTrue(any(m['speaker_id'] == '25' for m in rows))
        self.assertTrue(any(c.get('type') == 'DATE_ATTRIBUTION_REQUIRES_REVIEW' for c in conflicts))
        c = execution.build_context(ROOT, '2026-10-16', ['25'], snapshot=archive)
        self.assertEqual(c['freshness'], 'ARCHIVE_SNAPSHOT_REQUIRES_DOCUMENT_REFRESH')
        self.assertTrue(c['members']['25']['history'])

    def test_undated_monthly_tab_refuses_silent_attribution(self):
        snapshot = {'documentId': execution.FORMAL_DOC_ID, 'revisionId': 'r',
                    'retrieved_at': '2026-10-16T12:00:00+03:00',
                    'tabs': [{'tabId': 't.0', 'title': '⭕️🔟月汇总'}],
                    'paragraphs': [{'tabId': 't.0', 'text': '===== 资讯助理 =====\\n测试'}]}
        with self.assertRaisesRegex(ValueError, 'UNVERIFIED_DATE_BOUNDARY'):
            execution.build_context(ROOT, '2026-10-16', ['25'], snapshot=snapshot)

    def test_archived_snapshot_missing_date_provenance_is_rejected(self):
        archive = json.loads((ROOT / 'memory/daily/2026-10-16/formal-google-doc-snapshot.json').read_text())
        archive.pop('date_attribution')
        with self.assertRaisesRegex(ValueError, 'SNAPSHOT_DATE_UNVERIFIED'):
            execution.build_context(ROOT, '2026-10-16', ['25'], snapshot=archive)

    def test_dated_tab_retains_teacher_and_assistant_turns(self):
        snapshot = {'documentId': execution.FORMAL_DOC_ID, 'revisionId': 'r',
                    'retrieved_at': '2026-10-16T12:00:00+03:00',
                    'tabs': [{'tabId': 'x', 'title': '10/16'}],
                    'paragraphs': [{'tabId': 'x', 'text':
                                    '===== 资讯助理 =====\n开始\n===== 先生 =====\n课程\n25男：\n收到'}]}
        adapted, live = execution.adapt_snapshot(snapshot, '2026-10-16')
        self.assertTrue(live)
        days, conflicts = execution.snapshot_messages(adapted, __import__('datetime').date(2026, 10, 16),
                                                       {p['id']: p for p in json.loads((ROOT / 'skills/p004-chat-suite/characters/final-identity-65.json').read_text())['people']})
        self.assertEqual([r['speaker_id'] for r in days['2026-10-16']],
                         ['news_assistant', 'teacher', '25'])
        self.assertEqual(conflicts, [])

    def test_id_is_the_key_even_when_names_match(self):
        with self.assertRaisesRegex(ValueError, 'OUTSIDE_ACTIVE_RANGE'):
            self.context(('41', '62'))
        self.assertEqual(self.context(('01',))['members']['01']['identity']['name'], 'Ion Dumitrescu')

    def test_no_persona_history_created_for_missing_history(self):
        c = self.context(('06',))
        self.assertEqual(c['members']['06']['history'], [])
        self.assertEqual(c['members']['06']['history_status'], 'NO_ADOPTED_RECORDS_IN_LOADED_SOURCES')
        self.assertEqual(c['members']['06']['voice_status'], 'CREATIVE_DRAFT_NOT_USER_APPROVED')

    def test_quarantined_lines_never_become_history(self):
        c = self.context()
        ids = {m['id'] for p in c['members'].values() for m in p['history']}
        self.assertNotIn('20261013-M060', ids)
        self.assertNotIn('M053', ids)
        self.assertTrue(c['members']['15']['history'])
        self.assertTrue(all(m['speaker_id'] == '15' for m in c['members']['15']['history']))

    def test_real_direct_exchange_is_separate_from_candidate_pairing(self):
        c = self.context(('09', '10', '15', '35'))
        available = {m['id'] for member in c['members'].values() for m in member['history']}
        self.assertTrue(all(seed['evidence_message_ids'] and set(seed['evidence_message_ids']).issubset(available)
                            for seed in c['documented_interactions']))
        self.assertEqual(len(c['candidate_pairings']), 1)
        self.assertEqual(c['candidate_pairings'][0]['member_ids'], ['09', '35'])

    def test_file_change_invalidates_context_receipt(self):
        c = self.context()
        self.assertEqual(execution.check_receipt(c, ROOT), [])
        key = next(iter(c['source_hashes']))
        c['source_hashes'][key] = 'tampered'
        self.assertIn('SOURCE_CHANGED:' + key, execution.check_receipt(c, ROOT))

    def test_latest_doc_replaces_old_day_instead_of_double_counting(self):
        snapshot = {'documentId': execution.FORMAL_DOC_ID, 'revisionId': 'revision-test',
                    'retrieved_at': '2026-10-16T00:00:00+03:00',
                    'tabs': [{'tabId': 'tab14', 'title': '10/14'}],
                    'paragraphs': [{'tabId': 'tab14', 'startIndex': 1,
                                    'text': '15男：\n这次修订后的原句。'}]}
        c = execution.build_context(ROOT, '2026-10-16', ['15'], snapshot=snapshot)
        self.assertEqual(len([m for m in c['members']['15']['history'] if m['date'] == '2026-10-14']), 1)
        self.assertEqual([m for m in c['members']['15']['history'] if m['date'] == '2026-10-14'][0]['text'], '这次修订后的原句。')
        self.assertNotIn('20261014-M108', {m['id'] for m in c['members']['15']['history']})

    def test_missing_latest_doc_does_not_claim_fresh_memory(self):
        self.assertEqual(self.context()['freshness'], 'ARCHIVE_ONLY_REQUIRES_DOCUMENT_REFRESH')

    def test_empty_snapshot_cannot_certify_current_memory(self):
        with self.assertRaisesRegex(ValueError, 'EMPTY_OR_INCOMPLETE_FORMAL_SNAPSHOT'):
            execution.build_context(ROOT, '2026-10-16', ['15'], snapshot={
                'documentId': execution.FORMAL_DOC_ID, 'revisionId': 'r',
                'retrieved_at': '2026-10-16T00:00:00+03:00', 'tabs': [], 'paragraphs': []})

    def test_malformed_scenes_fail_closed_instead_of_crashing(self):
        for scene in [None, {}, [None], [{'id': []}], [{'id': 'x', 'speaker_id': '10', 'text': '好', 'claim_ids': None}]]:
            with self.subTest(scene=scene):
                self.assertEqual(execution.review_scene(scene, self.context())['status'], 'BLOCK')

    def test_empty_scene_is_not_a_completed_script(self):
        self.assertIn('EMPTY_SCENE', execution.review_scene([], self.context())['errors'])

    def test_nontext_turn_cannot_crash_following_turn(self):
        for body in [None, 123, [], {}]:
            self.assertEqual(execution.review_scene([
                {'id': 'a', 'speaker_id': '15', 'gender': '男', 'text': body},
                {'id': 'b', 'speaker_id': '10', 'gender': '女', 'text': '下一句'}], self.context())['status'], 'BLOCK')

    def test_future_snapshot_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'FUTURE_SNAPSHOT'):
            execution.build_context(ROOT, '2026-10-16', ['15'], snapshot={
                'documentId': execution.FORMAL_DOC_ID, 'revisionId': 'r',
                'retrieved_at': '2026-10-17T00:00:00+03:00', 'tabs': [], 'paragraphs': []})

    def test_scene_requires_current_source(self):
        self.assertIn('CURRENT_DOCUMENT_NOT_LOADED', execution.review_scene([], self.context())['errors'])

    def test_wrong_gender_and_unknown_history_are_blocked(self):
        c = self.context(); c['freshness'] = 'CURRENT_DOCUMENT_LOADED'
        scene = [{'id': 's1', 'speaker_id': '10', 'gender': '男', 'text': '我昨天交了作业。', 'memory_refs': ['invented']}]
        result = execution.review_scene(scene, c)
        self.assertIn('GENDER_MISMATCH:s1', result['errors'])
        self.assertIn('UNSUPPORTED_MEMORY:s1', result['errors'])

    def test_member_to_member_reply_and_callback_survive_review(self):
        c = self.context(); c['freshness'] = 'CURRENT_DOCUMENT_LOADED'
        reference = c['members']['15']['history'][-1]['id']
        scene = [{'id': 'a', 'speaker_id': '15', 'gender': '男', 'text': '我还是有个问题。', 'memory_refs': [reference]},
                 {'id': 'b', 'speaker_id': '10', 'gender': '女', 'text': '你具体是觉得例子太简单，还是想听后面的条件？', 'reply_to': 'a'}]
        result = execution.review_scene(scene, c)
        self.assertEqual(result['errors'], [])
        self.assertEqual(result['member_to_member_replies'], 1)

    def test_future_reply_is_blocked(self):
        c = self.context(); c['freshness'] = 'CURRENT_DOCUMENT_LOADED'
        self.assertIn('INVALID_REPLY_TARGET:s1', execution.review_scene([
            {'id': 's1', 'speaker_id': '10', 'gender': '女', 'text': '同意。', 'reply_to': 'later'}], c)['errors'])

    def test_lecture_completed_does_not_mean_homework_received(self):
        refs = {'m1': {'text': '今晚请做一道练习。'}}
        self.assertFalse(execution.validate_state_change({'state': 'homework_received', 'evidence_ids': ['m1'], 'evidence_support_reviewed': False}, refs))
        self.assertFalse(execution.validate_state_change({'state': 'homework_received', 'evidence_ids': ['missing'], 'evidence_support_reviewed': True}, refs))

    def test_duplicate_news_uses_evidence_not_title_or_claim_id(self):
        ledger = {'sources': {'s': {'url': 'https://example.org/report?utm_source=a'}},
                  'claims': [{'id': 'old', 'evidence': [{'source_id': 's', 'excerpt': 'Revenue increased 5 percent.'}]}], 'publish_claim_ids': ['old']}
        old = execution.evidence_keys(ledger)
        rewritten = copy.deepcopy(ledger)
        rewritten['claims'][0].update(id='new', text='换个标题重新播报')
        rewritten['publish_claim_ids'] = ['new']
        rewritten['sources']['s']['url'] = 'https://example.org/report?utm_source=b'
        self.assertEqual(old, execution.evidence_keys(rewritten))

    def test_new_evidence_is_not_erased_by_old_event(self):
        self.assertEqual(execution.new_evidence_keys(['old', 'new'], [{'state': 'DELIVERED', 'evidence_keys': ['old']}]), ['new'])
        self.assertEqual(execution.new_evidence_keys(['old'], [{'state': 'DRAFT', 'evidence_keys': ['old']}]), ['old'])

    def test_existing_telegram_pending_receipt_blocks_repeat(self):
        self.assertEqual(execution.new_evidence_keys(['old'], [{'state': 'PENDING_DO_NOT_RETRY', 'claim_evidence_keys': ['old']}]), [])


if __name__ == '__main__':
    unittest.main()
