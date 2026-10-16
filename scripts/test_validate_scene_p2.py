import unittest
from validate_scene_p2 import inspect

class P2SceneTest(unittest.TestCase):
    def setUp(self):
        self.s={'document_id':'doc','revision_id':'rev','paragraphs':[]}
        self.rel={'seeds':[{'member_ids':['09','35'],'status':'FUTURE_DEVELOPMENT_NOT_ADOPTED_HISTORY'}]}
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
