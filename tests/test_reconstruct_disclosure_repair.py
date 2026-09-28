import importlib.util
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location('repair',Path(__file__).resolve().parents[1]/'scripts/run_reconstruct_disclosure_repair.py')
repair=importlib.util.module_from_spec(spec)
spec.loader.exec_module(repair)


class RepairTests(unittest.TestCase):
    def test_fresh_cohort_repair_requires_three_resolved_corrobating_audits(self):
        base={'banks':{},'audits':{},'sources':{},'partitions':{'D1':[0,1,2]}}
        for index in range(3):
            key=str(index)
            base['banks'][key]={'source_index':index,'prompt':'convert_p4','output':{'status':'OK','clues':[]}}
            base['sources'][key]={'question':'Question','final_answer':'Answer','checked_solution':'Solution'}
            for prompt in ['audit_support_p1','audit_public_p4','audit_source_disclosure_p2']:
                if index==1 and prompt=='audit_source_disclosure_p2': continue
                status='ACCEPT' if prompt=='audit_support_p1' else 'REJECT'
                if index==2 and prompt=='audit_public_p4': status='ACCEPT'
                base['audits'][key+prompt]={'bank_key':key,'prompt':prompt,'output':{'status':status}}
        result=repair.prepare(base,'{{SOURCE_QUESTION}}',base_path=Path('fresh.json'),
                              expected_indices=None,expected_bank_count=None,
                              protocol='prospective-V')
        self.assertEqual(list(result['metadata']['repair_inputs']),['0'])
        self.assertEqual(result['metadata']['original_source_denominator'],3)
        self.assertEqual(result['metadata']['protocol'],'prospective-V')

    def test_cosmetic_changes_cannot_get_a_new_audit(self):
        first={'clues':[{'id':'c1','sentence':'A fact','fragment':'A'},
                         {'id':'c2','sentence':'Another fact','fragment':'B'}]}
        second={'clues':[{'id':'new1','sentence':'Another fact','fragment':'changed'},
                          {'id':'new2','sentence':'A fact','fragment':'changed','hidden_support':'changed'}]}
        self.assertEqual(repair.public_content(first),repair.public_content(second))
        second['clues'][0]['sentence']='A different fact'
        self.assertNotEqual(repair.public_content(first),repair.public_content(second))

    def test_frozen_inputs_exclude_student_records_and_select_corroborated_rejections(self):
        base={'banks':{},'audits':{},'sources':{},'partitions':{'reserve':[]},
              'responses':{'private':'STUDENT_FEEDBACK_MUST_NOT_ENTER'},'evaluations':{'private':'QWEN_SCORE'}}
        for index in [8,27,33,77,86,112,122,123,136,141,143]:
            key=str(index)
            base['banks'][key]={'source_index':index,'prompt':'convert_p4','output':{'status':'OK','clues':[]}}
            base['sources'][key]={'question':'Question','final_answer':'Answer','checked_solution':'Solution'}
            for prompt in ['audit_support_p1','audit_public_p4','audit_source_disclosure_p2']:
                rejected=(prompt!='audit_support_p1' and index in [8,86,123]) or (prompt=='audit_public_p4' and index==122)
                base['audits'][key+prompt]={'bank_key':key,'prompt':prompt,'output':{'status':'REJECT' if rejected else 'ACCEPT'}}
        result=repair.prepare(base,'{{SOURCE_QUESTION}} {{ORIGINAL_BANK}} {{PUBLIC_REVIEW}} {{SOURCE_REVIEW}}')
        self.assertEqual(sorted(result['metadata']['repair_inputs']),['123','8','86'])
        self.assertEqual(result['responses'],{})
        self.assertNotIn('STUDENT_FEEDBACK_MUST_NOT_ENTER',str(result))
        self.assertNotIn('QWEN_SCORE',str(result))
        result['banks']['27']['output']['status']='changed'
        self.assertEqual(base['banks']['27']['output']['status'],'OK')


if __name__=='__main__':unittest.main()
