import importlib.util
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location('final100',Path(__file__).resolve().parents[1]/'scripts/run_reconstruct_final100.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class FinalRunChecks(unittest.TestCase):
 def setUp(self):
  self.ev={'final_answer':'6','clues':[{'id':f'c{i}','sentence':f'observation {i}'} for i in range(1,5)],'rendered_clues':'1. observation 1\n2. observation 2\n3. observation 3\n4. observation 4'}
  self.audit={'status':'ACCEPT','source_answer_correct':True,'distinct_observations':True,'checks':[{'id':f'c{i}','supported':True,'understandable':True,'reason':'Supported'} for i in range(1,5)],'direct_question_copy':False,'premise_target_bundle_exposed':False,'complete_solution_exposed':False,'public_quotes':['observation 1'],'missing_essential_element':'area','inference_required':'Infer from answer','reason':'A missing area remains'}
 def test_valid_four_clue_audit(self):
  self.assertIs(m.validate_audit(self.audit,self.ev),self.audit)
 def test_acceptance_with_leak_rejected(self):
  self.audit['direct_question_copy']=True
  with self.assertRaisesRegex(AssertionError,'Contradictory'):m.validate_audit(self.audit,self.ev)
 def test_private_source_quote_rejected(self):
  self.audit['public_quotes']=['area24']
  with self.assertRaisesRegex(AssertionError,'Nonpublic'):m.validate_audit(self.audit,self.ev)
 def test_missing_clue_audit_rejected(self):
  self.audit['checks'].pop()
  with self.assertRaisesRegex(AssertionError,'Incomplete'):m.validate_audit(self.audit,self.ev)
 def test_copy_claim_needs_public_support(self):
  out={'status':'direct_candidate','question':'Find area24.','alignments':[{'question_span':'area24','public_quote':'area24','operation':'copy'}],'reason':'Copied'}
  with self.assertRaises(AssertionError):m.validate_copy(out,self.ev)
 def test_bank_requires_six_distinct_clues(self):
  bank={'status':'OK','clues':[{'id':f'c{i}','sentence':'same','hidden_support':'source'} for i in range(6)],'withheld':'area','private_certificate':'check'}
  with self.assertRaisesRegex(AssertionError,'Duplicate'):m.validate_bank(bank)

if __name__=='__main__':unittest.main()
