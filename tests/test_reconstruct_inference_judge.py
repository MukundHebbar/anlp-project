import copy
import unittest
from anlp_project.reconstruct import validate_evaluation


class InferenceJudgeTests(unittest.TestCase):
    def setUp(self):
        self.value={'status':'scored','score':4,'reason':'Checked','shortcut':False,
            'inference':{'status':'substantive','essential_content':'Area24 is introduced','reason':'The public clues do not supply the area constraint'}}

    def test_high_score_requires_substantive_inference(self):
        validate_evaluation(self.value,strict_inference=True)
        for status in ['copy_only','uncertain']:
            v=copy.deepcopy(self.value);v['inference']['status']=status
            with self.assertRaises(ValueError):validate_evaluation(v,strict_inference=True)

    def test_copy_only_requires_zero_and_shortcut(self):
        self.value.update(score=0,shortcut=True)
        self.value['inference']['status']='copy_only'
        validate_evaluation(self.value,strict_inference=True)
        self.value['shortcut']=False
        with self.assertRaises(ValueError):validate_evaluation(self.value,strict_inference=True)

    def test_legacy_p2_remains_readable_but_p3_fails_closed(self):
        del self.value['inference']
        validate_evaluation(self.value)
        with self.assertRaises(ValueError):validate_evaluation(self.value,strict_inference=True)


if __name__=='__main__':unittest.main()
