import copy
import unittest
import importlib.util
from pathlib import Path
from anlp_project.reconstruct import validate_source_recovery


class SemanticValidationTests(unittest.TestCase):
    def setUp(self):
        self.valid={'status':'scored','source_recovery':2,
                    'checks':dict.fromkeys(['objects','premises','domains_parameters','target'],'same'),
                    'correspondence':'Explicit mathematical correspondence','reason':'Equivalent'}

    def test_rejects_boolean_score(self):
        self.valid['source_recovery']=True
        with self.assertRaises(ValueError): validate_source_recovery(self.valid)

    def test_rejects_missing_or_contradictory_checks(self):
        for field in self.valid['checks']:
            item=copy.deepcopy(self.valid)
            item['checks'][field]='different'
            with self.assertRaises(ValueError): validate_source_recovery(item,strict=True)
        self.valid['checks'].pop('target')
        with self.assertRaises(ValueError): validate_source_recovery(self.valid,strict=True)

    def test_allows_explicit_uncertainty_but_not_scored_uncertainty(self):
        self.valid['status']='needs_review'
        self.valid['source_recovery']=None
        self.valid['checks']['target']='uncertain'
        validate_source_recovery(self.valid,strict=True)
        self.valid['status']='scored'
        with self.assertRaises(ValueError): validate_source_recovery(self.valid,strict=True)

    def test_old_schema_retained_only_in_nonstrict_mode(self):
        old={'status':'scored','source_recovery':2,'reason':'Same'}
        validate_source_recovery(old)
        with self.assertRaises(ValueError): validate_source_recovery(old,strict=True)

    def test_calibration_request_excludes_reference_labels_and_reasons(self):
        path=Path(__file__).resolve().parents[1]/'scripts/calibrate_reconstruct_semantics.py'
        spec=importlib.util.spec_from_file_location('semantic_calibration',path)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        case={'source_question':'original','candidate_question':'candidate',
              'expected':'SECRET_REFERENCE','reference_reason':'SECRET_PROOF','family':'SECRET_FAMILY'}
        prompt=module.render_case('{{SOURCE_QUESTION}}\n{{CANDIDATE_QUESTION}}',case)
        self.assertEqual(prompt,'original\ncandidate')


if __name__=='__main__': unittest.main()
