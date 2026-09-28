import json,subprocess,sys,tempfile,unittest
from pathlib import Path

class AllocationReportTest(unittest.TestCase):
    def test_empty_sixteen_source_study_keeps_allocation_and_no_score(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            (root/'student.json').write_text(json.dumps({'metadata':{'original_denominator':16,'jobs':[],'arms':['onegap']},'responses':{},'sources':{}}))
            subprocess.run([sys.executable,'scripts/report_reconstruct_richer.py','--study-root',str(root)],check=True,capture_output=True)
            result=json.loads((root/'comparison.json').read_text())['arms']['onegap']
            self.assertEqual(result['denominator_all_sources'],16)
            self.assertEqual(result['reviewed_end_to_end_rate'],0)
            self.assertIsNone(result['reviewed_conditional_rate'])
            self.assertIsNone(result['mean_score_100'])
            self.assertEqual(result['rating_counts_1_to_5'], {str(i):0 for i in range(1,6)})
            self.assertIsNone(result['middle_heavy_observed'])
            self.assertIn('0/16',(root/'comparison.md').read_text())
            self.assertNotIn('/12',(root/'comparison.md').read_text())

    def test_invalid_allocation_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            (root/'student.json').write_text(json.dumps({'metadata':{'original_denominator':0,'jobs':[],'arms':[]}}))
            result=subprocess.run([sys.executable,'scripts/report_reconstruct_richer.py','--study-root',str(root)],capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0)
            self.assertIn('Allocation denominator must be a positive integer',result.stderr)

    def test_source_quarantine_is_not_labeled_transport_failure(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            (root/'run.json').write_text(json.dumps({'sources':{'1':{'question':'Underdetermined recurrence'}},'banks':{},'metadata':{'protocol':'test','required_bank_audits':{'test_prompt':[]},'source_preflight_exclusions':{'1':'Second term is unspecified'}}}))
            (root/'prestudent-content-review.json').write_text(json.dumps({'rows':[]}))
            subprocess.run([sys.executable,'scripts/freeze_reconstruct_richer_review.py','--study-root',str(root),'--bank-prompt','test_prompt'],check=True,capture_output=True)
            row=json.loads((root/'input-review.json').read_text())['rows'][0]
            self.assertFalse(row['eligible'])
            self.assertEqual(row['reason'],'Source preflight exclusion: Second term is unspecified')
