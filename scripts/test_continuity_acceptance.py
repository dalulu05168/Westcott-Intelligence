import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import continuity_acceptance as ca
import editorial_runtime_v21 as rt

ROOT = Path(__file__).resolve().parents[1]


class ContinuityAcceptanceTest(unittest.TestCase):
    def setUp(self):
        self.snapshot=rt.load(ROOT/'memory/sources/google-doc-20261018.json')
        self.roster={p['id']:p for p in rt.load(ROOT/'skills/p004-chat-suite/characters/final-identity-65.json')['people']}
        self.policy=rt.load(ROOT/rt.POLICY)
        self.courses=rt.load(ROOT/'planning/course-progress-v2.1.json')

    def fixture(self):
        # Entirely isolated test source. No future quote, real submission or adoption.
        snapshot=copy.deepcopy(self.snapshot)
        snapshot['revisionId']='SIMULATION_ONLY_SUNDAY_ADOPTION_FIXTURE'
        snapshot['source_kind']='ACCEPTANCE_FIXTURE_NOT_LIVE'
        tab=next(t['tabId'] for t in snapshot['tabs'] if t['title']=='10/18')
        snapshot['paragraphs']=[p for p in snapshot['paragraphs'] if p['tabId']!=tab]
        scene=[{'id':'fixture-1','speaker_id':'25','text':'这次先把研究依据看明白，别只盯着价格。'}]
        snapshot['paragraphs'] += [{'tabId':tab,'startIndex':1,'text':'===== 资讯助理 =====\n晚上好，以下仅为隔离验收场景。\n25男：\n'+scene[0]['text']+'\n===== 资讯助理 =====\n今天交流结束，晚安。\n'}]
        days,_=rt.parse_snapshot(snapshot,self.roster,2026)
        confirmation={'confirmed_by_user':True,'confirmation_reference':'SIMULATION_ONLY_NOT_ACTUAL_USER_ADOPTION',
                      'scene_sha256':ca.scene_digest(scene),'formal_revision':snapshot['revisionId']}
        return snapshot,days,scene,confirmation

    def test_candidate_does_not_enter_actual_formal_history(self):
        _,_,scene,confirmation=self.fixture()
        days,_=rt.parse_snapshot(self.snapshot,self.roster,2026)
        with self.assertRaisesRegex(ValueError,'ABSENT_OR_AMBIGUOUS'):
            ca.verify_adoption(scene,days,confirmation,confirmation['formal_revision'],story_date='2026-10-18')

    def test_isolated_adoption_projection_is_idempotent(self):
        snapshot,days,scene,confirmation=self.fixture()
        proposed=ca.verify_adoption(scene,days,confirmation,snapshot['revisionId'],story_date='2026-10-18')
        once=ca.project_events([],proposed)
        twice=ca.project_events(once,proposed)
        self.assertEqual(once,twice)
        self.assertFalse(once[0]['real_trade_verified'])

    def test_user_confirmation_without_revision_cannot_adopt(self):
        snapshot,days,scene,confirmation=self.fixture()
        confirmation['formal_revision']='another'
        with self.assertRaisesRegex(ValueError,'REVISION_MISMATCH'):
            ca.verify_adoption(scene,days,confirmation,snapshot['revisionId'],story_date='2026-10-18')

    def test_removed_formal_text_cannot_keep_adoption(self):
        snapshot,days,scene,confirmation=self.fixture()
        days['2026-10-18']=[r for r in days['2026-10-18'] if r['speaker_id']!='25']
        with self.assertRaisesRegex(ValueError,'ABSENT_OR_AMBIGUOUS'):
            ca.verify_adoption(scene,days,confirmation,snapshot['revisionId'],story_date='2026-10-18')

    def test_old_day_same_words_do_not_prove_current_day_adoption(self):
        snapshot,days,scene,confirmation=self.fixture()
        rows=days.pop('2026-10-18')
        for row in rows: row['date']='2026-10-16'
        days['2026-10-16']=rows
        with self.assertRaisesRegex(ValueError,'ABSENT_OR_AMBIGUOUS'):
            ca.verify_adoption(scene,days,confirmation,snapshot['revisionId'],story_date='2026-10-18')

    def test_sunday_to_monday_three_sessions_are_plans_not_events(self):
        snapshot,days,_,_=self.fixture();checkpoint=rt.checkpoint(days,snapshot,rt.source_digest(snapshot))
        self.assertEqual(checkpoint['story_phase'],'EVENING_CLOSED')
        for period in ('MORNING','AFTERNOON','EVENING'):
            plan=ca.next_session_plan('2026-10-19',period,checkpoint,self.policy,self.courses)
            self.assertEqual(plan['research_order'],'PENDING_USER_SLOT')
            self.assertEqual(plan['market_data'],'REFRESH_AT_ACTUAL_SESSION')
            self.assertFalse(plan['adopted'])
            self.assertNotIn('price',plan)
        self.assertIn('KDJ',plan['course_material'])
        self.assertNotEqual(plan['course_status'],'COMPLETED_IN_FORMAL_STORY')

    def test_new_python_process_recovers_formal_state_without_chat_history(self):
        # New process tests disk-only recovery; it is not a claim that another chat ran.
        code="import sys,json;sys.path.insert(0,'scripts');import editorial_runtime_v21 as r;d=r.load('memory/derived/v2.1/members/25.json');print(json.dumps({'name':d['identity']['name'],'has_foje':any('FOJE' in x['text'] for x in d['recent_examples']),'quantity':d['dynamic_records'][0]['quantity']}))"
        result=subprocess.run([sys.executable,'-c',code],cwd=ROOT,capture_output=True,text=True,encoding='utf-8',check=True)
        recovered=json.loads(result.stdout)
        self.assertTrue(recovered['has_foje'])
        self.assertIsNone(recovered['quantity'])

    def test_formal_sunday_in_production_projection_without_simulation_data(self):
        # A date is not a simulation marker: 2026-10-18 now has formal Google Doc history.
        history=rt.load(ROOT/'memory/derived/v2.1/effective-history.json')
        sunday=history.get('2026-10-18',[])
        self.assertTrue(sunday, 'Formal 2026-10-18 history must not be discarded')
        formal_tab=next(t['tabId'] for t in self.snapshot['tabs'] if t['title']=='10/18')
        for row in sunday:
            with self.subTest(formal_sunday_row=row.get('id')):
                self.assertEqual(row.get('date'),'2026-10-18')
                self.assertEqual(row.get('status'),'PRESENT_IN_FORMAL_DOCUMENT')
                self.assertEqual(row.get('source_tab_id'),formal_tab)
                self.assertTrue(row.get('source_revision'))

        # Reject test-fixture provenance/markers on any date, without excluding real dates.
        for date,rows in history.items():
            for row in rows:
                with self.subTest(date=date,record=row.get('id')):
                    data=json.dumps(row,ensure_ascii=False,sort_keys=True)
                    self.assertNotIn('SIMULATION_ONLY',data)
                    self.assertNotIn('ACCEPTANCE_FIXTURE_NOT_LIVE',data)
                    self.assertNotIn('以下仅为隔离验收场景',data)


if __name__=='__main__':unittest.main()
