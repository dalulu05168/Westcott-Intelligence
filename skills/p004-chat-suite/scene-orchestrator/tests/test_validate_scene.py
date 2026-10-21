import importlib.util
from pathlib import Path
import unittest

modpath=Path(__file__).resolve().parents[1]/'tools/validate_scene.py'
spec=importlib.util.spec_from_file_location('scene_validation',modpath)
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
PEOPLE=[{'id':f'{n:02d}','gender':'女' if n in (2,7,10,16,17,21,26,27,37,39,42) else '男'} for n in range(1,66)]

class TestSceneStaticGate(unittest.TestCase):
    def check(self,s,**kw): return module.analyze(s,PEOPLE,**kw)
    def codes(self,s,**kw): return {i['code'] for i in self.check(s,**kw)['issues']}
    def test_good_scene(self): self.assertTrue(self.check('===== 资讯助理 =====\n大家好。\n01男：我还得看看这个图。\n02女：你说哪条线？')['pass'])
    def test_42_allowed(self): self.assertTrue(self.check('42女：我觉得有必要再解释一下。')['pass'])
    def test_43_blocked(self): self.assertIn('OUT_OF_RANGE',self.codes('43男：今天我也想说两句。'))
    def test_wrong_gender(self): self.assertIn('GENDER_MISMATCH',self.codes('10男：我跟你想法不太一样。'))
    def test_markdown(self): self.assertIn('MARKDOWN_BOLD',self.codes('01男：**非常同意**'))
    def test_teacher(self): self.assertIn('OLD_TEACHER',self.codes('===== 先生 =====\nHenry先生晚上好。'))
    def test_duplicate(self): self.assertIn('DUPLICATE_TURN',self.codes('01男：我还是想确认一下是不是这样。\n02女：我还是想确认一下是不是这样。'))
    def test_activity_bad(self): self.assertIn('ACTIVITY_ORDER',self.codes('今天的活动开始。上期结果是B。',activity=True))
    def test_activity_good(self): self.assertTrue(self.check('上一期活动结果已核实：B。今天的活动题目来了。',activity=True)['pass'])
    def test_activity_missing_result(self): self.assertIn('MISSING_PREVIOUS_RESULT',self.codes('今天的活动题目来了。',activity=True))
    def test_empty(self): self.assertIn('EMPTY',self.codes(''))
    def test_unpadded_warning(self): self.assertIn('NON_PADDED_LABEL',self.codes('1男：我觉得还需要继续观察。'))
    def test_invalid_label(self): self.assertIn('INVALID_LABEL',self.codes('2女 我也是'))
    def test_pending_result(self): self.assertIn('PENDING_PREVIOUS_RESULT',self.codes('上一期活动结果待核实。今天的活动题目先拟定。',activity=True))

    def test_morning_lesson_lead_blocked(self):
        rules={'rules':[{'status':'approved','scene':'morning','forbidden_lead_terms':['昨晚的学习收获'],'required_lead_terms':['美股','罗马尼亚','盘前','市场']}]}
        result=self.check('===== 资讯助理 =====\n今天先聊聊昨晚的学习收获。',scene='morning',corrections=rules)
        self.assertIn('MORNING_LESSON_LEAD',{x['code'] for x in result['issues']})
        self.assertFalse(result['pass'])
    def test_morning_market_lead_allowed_static(self):
        rules={'rules':[{'status':'approved','scene':'morning','forbidden_lead_terms':['昨晚的学习收获'],'required_lead_terms':['美股','罗马尼亚','盘前','市场']}]}
        result=self.check('===== 资讯助理 =====\n早上好，先看隔夜美股市场资讯。',scene='morning',corrections=rules)
        self.assertNotIn('MORNING_NO_MARKET_LEAD',{x['code'] for x in result['issues']})
    def test_morning_missing_snapshot_blocked(self):
        self.assertIn('MISSING_CORRECTIONS',self.codes('===== 资讯助理 =====\n美股市场资讯。',scene='morning'))

    def test_morning_snapshot_has_no_approved_rule(self):
        result=self.check('===== 资讯助理 =====\\n美股市场资讯。',scene='morning',corrections={'rules':[{'status':'draft','scene':'morning'}]})
        self.assertFalse(result['pass'])

    def test_morning_wrong_lead_with_market_keyword(self):
        rules={'rules':[{'status':'approved','scene':'morning','forbidden_lead_terms':['昨晚的学习收获'],'required_lead_terms':['美股']}]}
        result=self.check('===== 资讯助理 =====\\n先说昨晚的学习收获，然后再看美股。',scene='morning',corrections=rules)
        self.assertIn('MORNING_LESSON_LEAD',{x['code'] for x in result['issues']})

if __name__=='__main__': unittest.main()
