import copy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import unittest

import editorial_runtime_v21 as rt
from test_news_release_gate import valid as fact_fixture

ROOT = Path(__file__).resolve().parents[1]


class Runtime21Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.snapshot = rt.load(ROOT/'memory/sources/google-doc-20261017.json')
        cls.roster = {p['id']: p for p in rt.load(ROOT/'skills/p004-chat-suite/characters/final-identity-65.json')['people']}
        cls.decisions = rt.load(ROOT/'memory/sources/google-doc-20261017-review.json')
        cls.states = rt.load(ROOT/'memory/curated/2026-10-16-dynamic-state.json')
        cls.now = rt.timestamp(cls.snapshot['retrieved_at'])+timedelta(seconds=2)

    def execute(self, cast=('10',), **kwargs):
        check = dict(documentId=self.snapshot['documentId'], revisionId=self.snapshot['revisionId'],
                     retrieved_at=self.now.isoformat(), source_kind='TEST_FIXTURE_NOT_LIVE')
        return rt.run(ROOT, kwargs.pop('snapshot', self.snapshot), list(cast), kwargs.pop('now', self.now),
                      revision_check=kwargs.pop('revision_check', check), decisions=kwargs.pop('decisions', self.decisions),
                      state_records=kwargs.pop('state_records', self.states), **kwargs)

    def test_actual_native_tabs_empty_parent_and_future_placeholders(self):
        days, _ = rt.parse_snapshot(self.snapshot, self.roster, 2026, self.decisions)
        self.assertEqual(sorted(days), ['2026-10-14', '2026-10-15', '2026-10-16'])
        c = self.execute()['context']['checkpoint']
        self.assertEqual(c['story_phase'], 'EVENING_CLOSED')
        self.assertEqual(c['story_tab_id'], 't.gbfri5r8vs3o')
        self.assertEqual([c['counts'][x]['labelled_raw'] for x in ('MORNING','AFTERNOON','EVENING')], [32,43,36])
        self.assertEqual(c['counts']['EVENING']['unlabelled_fragments'], 1)

    def test_unlabelled_close_never_becomes_member_history(self):
        result = self.execute(('01',), decisions={}, state_records=[])
        self.assertIn('LATEST_DAY_HAS_UNREVIEWED_LABELS', result['errors'])
        self.assertNotIn('今天的社群交流到这里正式结束', result['context']['members']['01']['history'][-1]['text'])

    def test_missing_gender_needs_exact_source_review(self):
        result = self.execute(('03',), decisions={}, state_records=[])
        self.assertTrue(result['context']['checkpoint']['quarantined_blocks'])
        changed = copy.deepcopy(self.decisions); changed['snapshot_sha256'] = 'wrong'
        with self.assertRaisesRegex(ValueError, 'SOURCE_MISMATCH'):
            self.execute(decisions=changed)

    def test_10_is_always_female(self):
        self.assertEqual(self.execute()['context']['members']['10']['identity']['gender'], '女')
        result = self.execute(scene=[{'id':'s1','speaker_id':'10','gender':'男','text':'晚上好。'}])
        self.assertIn('GENDER_MISMATCH:s1', result['errors'])

    def test_25_and_38_get_evidence_despite_absent_legacy_files(self):
        result = self.execute(('25','38'))
        for pid in ('25','38'):
            self.assertTrue(any('FOJE' in r['text'] for r in result['context']['members'][pid]['history']))
            self.assertEqual(result['context']['members'][pid]['memory_access'], 'NO_SEPARATE_FILE')
        self.assertEqual(len(result['member_index']), 65)
        self.assertEqual(result['member_index']['06']['history_status'], 'NO_CONFIRMED_HISTORY_IN_LOADED_SOURCES')

    def test_quantity_cannot_be_invented(self):
        state = next(s for s in self.states if s.get('member_id')=='25')
        turn = {'id':'s1','speaker_id':'25','gender':'男','text':'继续看看FOJE。',
                'memory_refs':state['evidence_ids'], 'action_assertion':{'symbol':'FOJE','action':state['action'],'quantity':100}}
        self.assertIn('UNSUPPORTED_QUANTITY:s1', self.execute(('25',), scene=[turn])['errors'])

    def test_34_bought_40_only_conditional(self):
        bought = next(s for s in self.states if s.get('member_id')=='34')
        watching = next(s for s in self.states if s.get('member_id')=='40')
        self.assertEqual(bought['action'], 'SELF_REPORTED_BUY')
        self.assertEqual(watching['action'], 'CONDITIONAL_PLAN_NOT_PURCHASE')
        turn={'id':'s1','speaker_id':'40','gender':'男','text':'看看AA。','memory_refs':watching['evidence_ids'],
              'action_assertion':{'symbol':'AA','action':'SELF_REPORTED_BUY'}}
        self.assertIn('UNSUPPORTED_STORY_ACTION:s1', self.execute(('40',), scene=[turn])['errors'])

    def test_outside_active_range(self):
        for pid in ('41','65'):
            with self.assertRaisesRegex(ValueError,'OUTSIDE_ACTIVE_CAST'): self.execute((pid,))

    def test_completed_macd_cannot_restart(self):
        turn={'id':'s1','speaker_id':'teacher','text':'开始MACD课程。','kind':'course_start','course_id':'MACD-20261016'}
        self.assertIn('COMPLETED_COURSE_RESTART_REQUIRES_EXPLICIT_REVIEW', self.execute(scene=[turn])['errors'])

    def test_missing_quote_no_fabricated_price(self):
        for price in (None, True, float('nan'), float('inf')):
            turn={'id':'s1','speaker_id':'news_assistant','text':'行情待核。','kind':'quote','quote':{'price':price}}
            self.assertIn('INVALID_OR_MISSING_QUOTE:s1', self.execute(scene=[turn])['errors'])

    def test_retitled_same_evidence_is_not_news(self):
        ledger=fact_fixture()
        from editorial_execution import evidence_keys
        used=[{'state':'ADOPTED','evidence_keys':evidence_keys(ledger)}]
        ledger['claims'][0]['text']='测试中换一个标题，原证据不变。'
        self.assertIn('NO_NEW_NEWS_EVIDENCE',self.execute(ledger=ledger,event_history=used)['errors'])

    def test_no_news_history_blocks(self):
        self.assertIn('NEWS_HISTORY_NOT_LOADED', self.execute(ledger=fact_fixture())['errors'])

    def test_platform_acceptance_is_not_delivery(self):
        self.assertEqual(rt.delivery_status(), 'NO_RECEIPT')
        self.assertEqual(rt.delivery_status({'platform':'telegram','message_id':123}), 'PLATFORM_ACCEPTED_DELIVERY_AND_READ_UNKNOWN')
        self.assertFalse(self.execute()['publication_allowed'])

    def test_stale_missing_or_changed_revision_blocks(self):
        self.assertIn('LATEST_REVISION_NOT_RECHECKED', self.execute(revision_check=None)['errors'])
        self.assertIn('SNAPSHOT_STALE_OR_FUTURE', self.execute(now=self.now+timedelta(minutes=6))['errors'])
        check={'documentId':self.snapshot['documentId'],'revisionId':'new','retrieved_at':self.now.isoformat()}
        self.assertIn('DOCUMENT_CHANGED_DURING_READ',self.execute(revision_check=check)['errors'])

    def test_archive_read_can_happen_after_story_date(self):
        # October 17 read of October 16 history is valid when refreshed now.
        self.assertEqual(self.execute()['status'], 'CONTEXT_READY_FOR_HUMAN_REVIEW')

    def test_same_day_current_view_replaces_old_snapshot(self):
        days, _=rt.parse_snapshot(self.snapshot,self.roster,2026,self.decisions)
        context=self.execute(('01',))['context']['members']['01']['history']
        expected=[r for r in days['2026-10-16'] if r['speaker_id']=='01' and r['status']=='PRESENT_IN_FORMAL_DOCUMENT']
        self.assertEqual([r['text'] for r in context if r['date']=='2026-10-16'],[r['text'] for r in expected])

    def test_withdrawn_state_evidence_is_rejected(self):
        states=copy.deepcopy(self.states);states[0]['evidence_ids']=['withdrawn']
        with self.assertRaisesRegex(ValueError,'MISSING_OR_WITHDRAWN'):self.execute(state_records=states)

    def test_three_member_pattern_warns_without_rejecting(self):
        scene=[]
        for n in range(3):
            scene.append({'id':f'a{n}','speaker_id':'news_assistant','text':f'测试主题{n}'})
            for i in range(3):scene.append({'id':f'{n}-{i}','speaker_id':'10','text':f'测试反应{n}-{i}'})
        self.assertTrue(rt.quality_signals(scene)['warnings'])
        self.assertFalse(rt.quality_signals(scene)['automatically_approved'])

    def test_date_heading_inside_monthly_tab(self):
        snapshot=copy.deepcopy(self.snapshot)
        snapshot['tabs']=[{'tabId':'month','title':'月汇总'}]
        snapshot['paragraphs']=[{'tabId':'month','text':'10/16\n===== 资讯助理 =====\n晚上好。\n10/17\n'}]
        days,_=rt.parse_snapshot(snapshot,self.roster,2026)
        self.assertEqual(list(days), ['2026-10-16'])

    def test_invalid_scene_shape_is_blocked(self):
        self.assertIn('INVALID_SCENE_SHAPE',self.execute(scene={})['errors'])

    def test_projection_does_not_persist_live_readiness(self):
        result=self.execute(('25','38'))
        with tempfile.TemporaryDirectory() as folder:
            rt.save_projection(folder,result,'source.json')
            c=rt.load(Path(folder)/'memory/runtime/latest-checkpoint.json')
            self.assertIn('REQUIRES_REFRESH',c['freshness'])
            self.assertEqual(len(list((Path(folder)/'memory/derived/v2.1/members').glob('*.json'))),65)

    def test_committed_projection_is_reproducible(self):
        from rebuild_editorial_archive_v21 import check
        self.assertEqual(check(), [])

    def test_rule_and_memory_reads_have_receipts(self):
        hashes = self.execute()['context']['source_hashes']
        self.assertIn('config/editorial-policy-v2.1.json', hashes)
        self.assertIn('skills/p004-teacher/SKILL.md', hashes)
        self.assertIn('skills/p004-chat-suite/references/runtime-v2.1.md', hashes)
        self.assertIn('memory/long-term/relationship-seeds.json', hashes)

    def inserted_source(self):
        snapshot=copy.deepcopy(self.snapshot)
        snapshot['revisionId']='INSERTION_REGRESSION_FIXTURE_NOT_LIVE'
        for p in snapshot['paragraphs']:
            if p['tabId']=='t.gbfri5r8vs3o' and '早上好！昨晚有什么大事件吗？' in p['text']:
                p['text']+='11女\n'
                return snapshot
        self.fail('Expected source line missing')

    def test_insertion_relinks_unchanged_evidence_by_content(self):
        snapshot=self.inserted_source()
        check={'documentId':snapshot['documentId'],'revisionId':snapshot['revisionId'],'retrieved_at':self.now.isoformat()}
        result=self.execute(('25','38','34','40'),snapshot=snapshot,revision_check=check,decisions=None)
        self.assertEqual(result['errors'], [])
        self.assertEqual(result['context']['checkpoint']['story_phase'],'EVENING_CLOSED')
        record=next(r for r in result['reviewed_dynamic_records'] if r.get('member_id')=='25')
        self.assertEqual(record['reference_status'],'EXACT_CONTENT_RELINKED_AFTER_SOURCE_INSERTION')
        self.assertNotEqual(record['original_evidence_ids'],record['evidence_ids'])

    def test_empty_wrong_gender_remains_visible_not_person_history(self):
        snapshot=self.inserted_source()
        check={'documentId':snapshot['documentId'],'revisionId':snapshot['revisionId'],'retrieved_at':self.now.isoformat()}
        result=self.execute(('11',),snapshot=snapshot,revision_check=check,decisions=None)
        self.assertTrue(result['context']['checkpoint']['source_anomalies'])
        self.assertFalse(result['context']['members']['11']['history'])

    def test_same_number_and_member_with_changed_text_cannot_reuse_state(self):
        snapshot=copy.deepcopy(self.snapshot);snapshot['revisionId']='CHANGED_TEXT_REGRESSION_FIXTURE'
        for p in snapshot['paragraphs']:
            if '我上周在32.3 RON附近买的' in p['text']:
                p['text']=p['text'].replace('卖掉了一部分','没有卖过')
        check={'documentId':snapshot['documentId'],'revisionId':snapshot['revisionId'],'retrieved_at':self.now.isoformat()}
        with self.assertRaisesRegex(ValueError,'MISSING_OR_WITHDRAWN'):
            self.execute(('25',),snapshot=snapshot,revision_check=check,decisions=None)

    def test_removed_evidence_blocks_prior_state(self):
        snapshot=copy.deepcopy(self.snapshot);snapshot['revisionId']='DELETION_REGRESSION_FIXTURE'
        for p in snapshot['paragraphs']:
            if '我上周在32.3 RON附近买的' in p['text']:p['text']='\n'
        check={'documentId':snapshot['documentId'],'revisionId':snapshot['revisionId'],'retrieved_at':self.now.isoformat()}
        with self.assertRaisesRegex(ValueError,'MISSING_OR_WITHDRAWN'):
            self.execute(('25',),snapshot=snapshot,revision_check=check,decisions=None)


if __name__=='__main__':unittest.main()
