import importlib.util
import unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('verifier',Path(__file__).resolve().parents[1]/'scripts/run_reconstruct_math_verifier.py')
v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)
class MathVerifierValidationTests(unittest.TestCase):
    def test_rejects_unattributed_or_inconsistent_certificates(self):
        response={'question':'Find x.','justification':'All graphs are trees.','assumptions':[]}
        good={'status':'invalid','question_answer_correct':True,'verification_sound':False,'reason':'False universal graph claim.','checks':[{'claim_quote':'All graphs are trees.','verdict':'false','evidence':'A triangle is not a tree.'}]}
        self.assertEqual(v.validate(good,response)['status'],'invalid')
        for altered in [dict(good,status='valid'),dict(good,verification_sound=True),dict(good,checks=[{'claim_quote':'Unstated text','verdict':'false','evidence':'Counterexample'}])]:
            with self.assertRaises(AssertionError):v.validate(altered,response)
