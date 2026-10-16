import json
from datetime import datetime
from pathlib import Path
import tempfile
import unittest
from zoneinfo import ZoneInfo
from morning_group_delivery import check_package, run, DESTINATION, DOC_ID
from morning_opening import build

NOW = datetime(2026, 10, 19, 7, 30, tzinfo=ZoneInfo('Europe/Bucharest'))


def market():
    # Fixture-only numbers; never use as real market data.
    return dict(market='US', phase='REGULAR_CLOSE', session_date='2026-10-16',
        source_url='https://example.org/official-close',
        source_checked_at='2026-10-19T07:10:00+03:00', review_status='REVIEWED',
        reviewed_by='fixture-editor', evidence_reference='fixture-only',
        source_body_sha256='0' * 64,
        indices=[dict(symbol=s, close=c, previous_close=p,
            change_pct=round((c / p - 1) * 100, 2),
            quote_as_of='2026-10-16T16:00:00-04:00', phase='REGULAR_CLOSE',
            source_url='https://example.org/' + s, evidence_excerpt='fixture only')
            for s, c, p in [('DJIA', 49000., 49100.), ('SPX', 6700., 6690.), ('IXIC', 23000., 23020.)]])


def approved():
    evidence = market()
    result = build(NOW, evidence)
    return dict(status='APPROVED_FOR_MORNING_GROUP', local_date='2026-10-19',
        target_group_title=DESTINATION, bot_username='NuvexaCheckBot',
        formal_story=dict(document_id=DOC_ID, revision_id='fixture-docs-revision',
                          retrieved_at='2026-10-19T07:12:00+03:00'),
        editorial_approval=dict(approved_by='fixture-editor',
            approved_at='2026-10-19T07:20:00+03:00',
            decision='APPROVED', source_review_reference='fixture-review',
            member_dialogue_reviewed=False),
        market_evidence=evidence,
        approved_text=result['opening_draft'] + '\n\n' + result['us_recap_draft'])


class MorningGroupDeliveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        folder = self.root / 'skills/p004-chat-suite/characters'
        folder.mkdir(parents=True)
        (folder / 'final-identity-65.json').write_text(json.dumps({'people': [
            {'id': str(i).zfill(2), 'gender': '女' if i == 2 else '男'}
            for i in range(1, 66)]}), encoding='utf-8')
    def tearDown(self): self.tmp.cleanup()

    def test_valid_approved_draft(self):
        text = check_package(approved(), NOW, self.root)
        self.assertIn('标普500指数', text)

    def test_wrong_group_blocks(self):
        p = approved(); p['target_group_title'] = 'other'
        with self.assertRaises(ValueError): check_package(p, NOW, self.root)

    def test_unreviewed_market_blocks(self):
        p = approved(); p['market_evidence']['review_status'] = 'UNREVIEWED'
        with self.assertRaises(ValueError): check_package(p, NOW, self.root)

    def test_old_date_blocks(self):
        p = approved(); p['local_date'] = '2026-10-16'
        with self.assertRaises(ValueError): check_package(p, NOW, self.root)

    def test_missing_docs_revision_blocks(self):
        p = approved(); p['formal_story']['revision_id'] = ''
        with self.assertRaises(ValueError): check_package(p, NOW, self.root)

    def test_changed_numeric_wording_blocks(self):
        p = approved(); p['approved_text'] = p['approved_text'].replace('标普500指数', '错误指数')
        with self.assertRaises(ValueError): check_package(p, NOW, self.root)

    def test_unreviewed_member_blocks(self):
        p = approved(); p['approved_text'] += '\n02女：早上好'
        with self.assertRaises(ValueError): check_package(p, NOW, self.root)

    def test_approved_member_allowed(self):
        p = approved(); p['approved_text'] += '\n02女：早上好'
        p['editorial_approval'].update(member_dialogue_reviewed=True, member_ids=['02'])
        self.assertTrue(check_package(p, NOW, self.root))

    def test_member_gender_mismatch_blocks(self):
        p = approved(); p['approved_text'] += '\n02男：早上好'
        p['editorial_approval'].update(member_dialogue_reviewed=True, member_ids=['02'])
        with self.assertRaises(ValueError): check_package(p, NOW, self.root)

    def test_without_approval_no_send(self):
        self.assertEqual(run(NOW, self.root, {'GITHUB_EVENT_NAME':'schedule', 'GITHUB_REF_NAME':'main'}), 'HELD')

    def test_manual_dispatch_never_sends(self):
        self.assertEqual(run(NOW, self.root, {'GITHUB_EVENT_NAME':'workflow_dispatch', 'GITHUB_REF_NAME':'main'}), 'HELD')


if __name__ == '__main__':
    unittest.main()
