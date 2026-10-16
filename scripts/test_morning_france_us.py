import json
from datetime import datetime
from pathlib import Path
import tempfile
import unittest
from zoneinfo import ZoneInfo

from morning_france_us import build, validate_france
from morning_france_us_delivery import check_france_package, run
from test_morning_group_delivery import market as us_market, NOW
from morning_group_delivery import DESTINATION, BOT, DOC_ID

def fr_evidence():
    return {
        "target_country": "FR", "review_status": "REVIEWED", "reviewed_by": "fixture-editor",
        "source_checked_at": "2026-10-19T07:15:00+03:00",
        "events": [{
            "event_key": "fr-official-economic-release-20261019-fixture",
            "target_country": "FR", "material_new_fact": True,
            "source_url": "https://www.insee.fr/fr/statistiques/example-fixture",
            "published_at": "2026-10-19T06:45:00+03:00",
            "source_body_sha256": "a"*64,
            "source_excerpt": "test fixture source excerpt",
            "title_cn": "法国经济报告（测试素材）",
            "fact_cn": "仅用于测试的虚构消息，禁止外发。",
            "impact_cn": "若相关趋势延续，可能影响法国经济预期。",
            "watch_cn": "后续核查官方数据。"
        }]
    }

def approved():
    us = us_market()
    fr = fr_evidence()
    preview = build(NOW, us, fr)
    assert preview['status'] == 'READY_FOR_EDITORIAL_REVIEW'
    return {
        "status": "APPROVED_FRANCE_US_MORNING", "local_date": "2026-10-19",
        "target_group_title": DESTINATION, "bot_username": BOT,
        "formal_story": {
            "document_id": DOC_ID, "revision_id": "fixture-only-revision",
            "retrieved_at": "2026-10-19T07:17:00+03:00"
        },
        "editorial_approval": {
            "approved_by": "fixture-editor", "decision": "APPROVED",
            "approved_at": "2026-10-19T07:25:00+03:00",
            "source_review_reference": "fixture-do-not-publish",
            "france_country_impact_review": "fixture-only",
            "cross_edition_dedup_review": "fixture-only",
            "member_dialogue_reviewed": False
        },
        "us_market_evidence": us, "france_evidence": fr,
        "approved_text": "\n\n".join([
            preview['opening_draft'], preview['us_recap_draft'], preview['france_draft']
        ])
    }


class FranceUsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        folder = self.root / 'skills/p004-chat-suite/characters'
        folder.mkdir(parents=True)
        (folder / 'final-identity-65.json').write_text(
            json.dumps({'people': [{'id': str(i).zfill(2),
                       'gender': '女' if i == 2 else '男'} for i in range(1,66)]}),
            encoding='utf-8')
    def tearDown(self):
        self.tmp.cleanup()

    def test_missing_france_no_fabricated_copy(self):
        p = build(NOW, us_market())
        self.assertIsNone(p['france_draft'])
        self.assertEqual(p['status'], 'HELD_FRANCE_EVIDENCE_REQUIRED')

    def test_missing_us_no_fabricated_copy(self):
        p = build(NOW, None, fr_evidence())
        self.assertEqual(p['status'], 'HELD_SOURCE_REQUIRED')
        self.assertIsNone(p['us_recap_draft'])

    def test_independent_france_and_us_draft(self):
        p = build(NOW, us_market(), fr_evidence())
        self.assertEqual(p['status'], 'READY_FOR_EDITORIAL_REVIEW')
        self.assertIn('🔴 法国', p['france_draft'])
        self.assertIn('道琼斯', p['us_recap_draft'])
        self.assertNotIn('罗马尼亚', p['france_draft'])

    def test_nonofficial_french_source_blocks(self):
        p = fr_evidence()
        p['events'][0]['source_url'] = 'https://fake-insee.fr/item'
        with self.assertRaises(ValueError):
            validate_france(p, NOW)

    def test_unreviewed_french_source_blocks(self):
        p = fr_evidence()
        p['review_status'] = 'UNREVIEWED'
        self.assertEqual(build(NOW, us_market(), p)['status'], 'HELD_FRANCE_EVIDENCE_REQUIRED')

    def test_stale_date_blocks(self):
        p=fr_evidence()
        p['events'][0]['published_at']='2026-10-08T04:00:00+03:00'
        with self.assertRaises(ValueError):
            validate_france(p, NOW)

    def test_france_us_package_accepted_structurally(self):
        s=check_france_package(approved(),NOW,self.root)
        self.assertIn('法国经济报告',s)
        self.assertIn('纳斯达克综合指数',s)

    def test_unreviewed_french_impact_blocks(self):
        p=approved()
        p['editorial_approval']['france_country_impact_review']=''
        with self.assertRaises(ValueError):
            check_france_package(p,NOW,self.root)

    def test_mismatch_telegram_target_blocks(self):
        p=approved()
        p['target_group_title']='other'
        with self.assertRaises(ValueError):
            check_france_package(p,NOW,self.root)

    def test_old_french_source_replay_blocks(self):
        receipt=self.root/'audit/telegram-delivery/test.json'
        receipt.parent.mkdir(parents=True)
        receipt.write_text(json.dumps({
            'state':'DELIVERED','evidence_urls':[fr_evidence()['events'][0]['source_url']]
        }),encoding='utf-8')
        with self.assertRaises(ValueError):
            check_france_package(approved(),NOW,self.root)

    def test_unreviewed_extra_claim_blocks(self):
        p=approved()
        p['approved_text']+='\n\n没有经过核验的市场评价'
        with self.assertRaises(ValueError):
            check_france_package(p,NOW,self.root)

    def test_gender_mismatch_blocks(self):
        p=approved()
        p['approved_text']+='\n\n02男：大家早上好'
        p['editorial_approval'].update(member_dialogue_reviewed=True,member_ids=['02'])
        with self.assertRaises(ValueError):
            check_france_package(p,NOW,self.root)

    def test_no_automatic_telegram_without_approved_file(self):
        self.assertEqual(run(NOW,self.root,{'GITHUB_EVENT_NAME':'schedule',
                          'GITHUB_REF_NAME':'main'}),'HELD')

    def test_manual_workflow_never_sends(self):
        self.assertEqual(run(NOW,self.root,{'GITHUB_EVENT_NAME':'workflow_dispatch',
                          'GITHUB_REF_NAME':'main'}),'HELD')


if __name__ == '__main__':
    unittest.main()
