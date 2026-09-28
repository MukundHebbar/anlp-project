import unittest
from anlp_project.reconstruct_gates import normalize_non_candidate_copy_annotations
class CopyAnnotationRecoveryTests(unittest.TestCase):
 def test_only_verified_fragments_removed_without_mutation(self):
  v={'status':'no_direct_reconstruction','question':None,'alignments':[{'question_span':'unknown n','public_quote':'unknown n','operation':'copy'}],'reason':'Missing length.'}
  out=normalize_non_candidate_copy_annotations(v,'The length is unknown n')
  self.assertEqual(out['alignments'],[]);self.assertEqual(out['status'],v['status']);self.assertEqual(len(v['alignments']),1)
  for changed in [{**v,'question':'A real proposed question?'},{**v,'status':'direct_candidate'},{**v,'alignments':[{'question_span':'invented','public_quote':'unknown n','operation':'copy'}]}]:
   with self.assertRaises(ValueError):normalize_non_candidate_copy_annotations(changed,'The length is unknown n')
