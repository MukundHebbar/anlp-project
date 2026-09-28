import importlib.util
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location('valid100',Path(__file__).resolve().parents[1]/'scripts/run_reconstruct_valid100.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class ValidHundredChecks(unittest.TestCase):
    def state(self):
        return {'items':{'10':{'input_status':'accepted'}},'records':{
            'student:10':{'output':{'question':'q','justification':'j'}},
            'judge_fidelity:10':{'output':{'status':'scored','premise_fidelity':{'score':2},'target_fidelity':{'score':2}}},
            'judge_validity:10':{'output':{'status':'scored','evidence_integration':{'score':1},'mathematical_validity':{'score':0},'shortcut':{'present':False}}}}}

    def test_low_score_is_eligible(self):
        self.assertTrue(m.complete(self.state(),10))

    def test_rejected_input_is_not_eligible(self):
        s=self.state();s['items']['10']['input_status']='rejected'
        self.assertFalse(m.complete(s,10))

    def test_zero_shortcut_with_missing_fidelity_is_not_complete(self):
        s=self.state();s['records'].pop('judge_fidelity:10')
        s['records']['judge_validity:10']['output']['shortcut']['present']=True
        self.assertFalse(m.complete(s,10))

    def test_unresolved_judge_is_not_complete(self):
        s=self.state();s['records']['judge_validity:10']['output']['status']='needs_review'
        self.assertFalse(m.complete(s,10))

    def test_question_dedup_ignores_whitespace_and_case(self):
        self.assertEqual(m.normalize_question(' Find X\n + 1 '),m.normalize_question('find x+1'))
