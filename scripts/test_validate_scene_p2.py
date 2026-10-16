import unittest
import json
from pathlib import Path
from validate_scene_p2 import inspect

class P2SceneTest(unittest.TestCase):
    def setUp(self):
        self.s={'document_id':'doc','revision_id':'rev','paragraphs':[]}
        self.rel={'seeds':[{'member_ids':['09','35'],'status':'FUTURE_DEVELOPMENT_NOT_ADOPTED_HISTORY'}]}
    def test_live_oct16_snapshot_keeps_embedded_25_turn(self):
        root=Path(__file__).resolve().parents[1]
        snap=json.loads((root/'memory/daily/2026-10-16/formal-google-doc-snapshot.json').read_text())
        r=inspect(snap,self.rel)
        self.assertEqual(r['total_turns'],33)
        codes={x['code']:x['evidence_id'] for x in r['issues']}
        self.assertEqual(codes['SPEAKER_GENDER_LABEL_MISSING'],'DOC-P562')
        self.assertEqual(codes['ADJACENT_NEAR_DUPLICATE'],'DOC-P572-P574')
        self.assertEqual(codes['EMBEDDED_MEMBER_LABEL'],'DOC-P576')
        self.assertEqual(r['review_status'],'PENDING_HUMAN_REVIEW')

    def test_member_mentions_and_only_adjacent_not_fixed_relationship(self):
        self.s['paragraphs']=[
            {'paragraph_index':10,'text':'09男：'},
            {'paragraph_index':11,'text':'18号，开盘了'},
            {'paragraph_index':12,'text':'18男：'},
            {'paragraph_index':13,'text':'哈哈，看到了'},
            {'paragraph_index':14,'text':'===== 资讯助理 ====='},
            {'paragraph_index':15,'text':'继续'}]
        q=inspect(self.s,self.rel)['quality_review']
        self.assertEqual(q['interaction']['explicit_member_mentions'][0]['mentioned_speaker'],'18')
        self.assertEqual(q['interaction']['member_to_member_adjacencies'][0]['status'],
                         'ADJACENT_ONLY_NOT_PROVEN_REPLY')
        self.assertEqual(q['semantic_status'],'PENDING_HUMAN_REVIEW')

    def test_trade_recollection_requires_evidence_and_is_not_real_trade_proof(self):
        self.s['paragraphs']=[
            {'paragraph_index':1,'text':'25男：'},
            {'paragraph_index':2,'text':'我之前买过FOJE'},
            {'paragraph_index':3,'text':'25男：'},
            {'paragraph_index':4,'text':'我上周买入，后来卖出了一部分'}]
        claims=inspect(self.s,self.rel)['quality_review']['character_trade_claims']
        self.assertEqual(claims[0]['historical_evidence'],'OLDER_ARCHIVES_NOT_EVALUATED')
        self.assertEqual(claims[1]['prior_in_scene_evidence_ids'],['DOC-P1'])
        self.assertTrue(all(x['status']=='STORY_CHARACTER_CLAIM_NOT_VERIFIED_REAL_TRADE'
                            for x in claims))

    def test_factual_market_numbers_never_auto_verified(self):
        self.s['paragraphs']=[
            {'paragraph_index':10,'text':'===== 资讯助理 ====='},
            {'paragraph_index':11,'text':'BET指数上涨1.14%，报34,886.11点'}]
        r=inspect(self.s,self.rel)
        flags=r['quality_review']['market_fact_candidates']
        self.assertEqual(len(flags),1)
        self.assertEqual(flags[0]['truth'],'UNDETERMINED')
        self.assertFalse(r['semantic_pass'])

    def test_voice_metric_is_not_character_approval(self):
        self.s['paragraphs']=[
            {'paragraph_index':1,'text':'01男：'},
            {'paragraph_index':2,'text':'为什么？'},
            {'paragraph_index':3,'text':'01男：'},
            {'paragraph_index':4,'text':'我还要再看看。'}]
        voices=inspect(self.s,self.rel)['quality_review']['voice_samples']
        self.assertEqual(voices[0]['sample_count'],2)
        self.assertEqual(voices[0]['review'],'HEURISTIC_ONLY_NOT_APPROVED_VOICE')

    def test_cross_speaker_near_duplicate_requires_review(self):
        self.s['paragraphs']=[
            {'paragraph_index':1,'text':'01男：'},
            {'paragraph_index':2,'text':'我觉得这里还需要看清楚这家公司具体的盈利来源和成本结构。'},
            {'paragraph_index':3,'text':'02女：'},
            {'paragraph_index':4,'text':'我觉得这里还需要看清楚这家公司具体的盈利来源和成本结构。'}]
        flagged=inspect(self.s,self.rel)['quality_review']['cross_speaker_similarity']
        self.assertEqual(len(flagged),1)
        self.assertEqual(flagged[0]['status'],'CROSS_SPEAKER_SIMILARITY_REVIEW')

    def test_repeated_turn_is_flagged(self):
        self.s['paragraphs']=[{'paragraph_index':1,'text':'13男：'},{'paragraph_index':2,'text':'我今天看到市场上涨了'},{'paragraph_index':3,'text':'13男：'},{'paragraph_index':4,'text':'我今天看到市场上涨了😄'}]
        r=inspect(self.s,self.rel)
        self.assertIn('ADJACENT_NEAR_DUPLICATE',[x['code'] for x in r['issues']])
        self.assertFalse(r['semantic_pass'])
    def test_missing_gender_label_is_flagged(self):
        self.s['paragraphs']=[{'paragraph_index':562,'text':'03：'},{'paragraph_index':563,'text':'早上好'}]
        r=inspect(self.s,self.rel)
        self.assertIn('SPEAKER_GENDER_LABEL_MISSING',[x['code'] for x in r['issues']])
    def test_relationship_is_never_approved(self):
        r=inspect(self.s,self.rel)
        self.assertEqual(r['relationship_guards'][0]['review'],'RELATIONSHIP_PROMOTION_REQUIRES_ADOPTED_EVIDENCE')
        self.assertEqual(r['review_status'],'PENDING_HUMAN_REVIEW')
    def test_staff_turns_preserve_order(self):
        self.s['paragraphs']=[{'paragraph_index':1,'text':'===== 资讯助理 ====='},{'paragraph_index':2,'text':'下午好'},{'paragraph_index':3,'text':'25男：'},{'paragraph_index':4,'text':'您好'}]
        self.assertEqual(inspect(self.s,self.rel)['total_turns'],2)
if __name__=='__main__': unittest.main()
