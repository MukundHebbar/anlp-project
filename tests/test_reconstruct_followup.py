import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    'followup', Path(__file__).resolve().parents[1]/'scripts/analyze_reconstruct_followup.py'
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class FollowupAnalysisTests(unittest.TestCase):
    def test_small_sample_intervals_do_not_claim_certainty(self):
        self.assertIsNone(module.wilson(0, 0))
        low, high = module.wilson(1, 12)
        self.assertLess(low, 1/12)
        self.assertGreater(high, .30)
        self.assertEqual(module.mcnemar(0, 0), 1.)
        self.assertEqual(module.mcnemar(3, 0), .25)

    def test_missing_clue_check_is_unresolved_not_success(self):
        run = {'partitions':{'D2':[1]}, 'banks':{'b':{'prompt':'convert_p2', 'output':{'clues':[{},{}]}}},
               'responses':{'r':{'source_index':1,'prompt':'student_p1','sampling':{'seed':0},
                 'condition':'bank','bank_key':'b','evidence_hash':'same','request':{},
                 'public_evidence':{'style':'sentence','disclosure':'medium','clue_count':2}}},
               'evaluations':{'e':{'response_key':'r','prompt':'evaluate_p2','output':{
                  'status':'scored','score':4,'well_posed':True,'answer_correct':True,'shortcut':False,
                  'clue_checks':[{'index':1,'compatible':True,'grounding':'explicit'}]}}}}
        result = module.analyze(run,'D2',['student_p1'],[0])['arms']['student_p1']
        self.assertEqual(result['resolved'],0)
        self.assertEqual(result['successes'],0)
        self.assertEqual(result['success_rate_lower_upper'],[0.,1.])
        self.assertEqual(result['mean_normalized_score_all_planned_bounds'],[0.,100.])
        run['evaluations']['e']['output']['clue_checks'].append(
            {'index':2,'compatible':True,'grounding':'explicit'})
        result=module.analyze(run,'D2',['student_p1'],[0])['arms']['student_p1']
        self.assertEqual(result['mean_normalized_score_resolved'],100.)
        self.assertEqual(result['normalized_score_complete_sources']['mean'],100.)
        run['responses']['r']['request'] = {'usage': {'completion_tokens': 90}}
        run['responses']['r']['pipeline_calls'] = 2
        run['responses']['r']['pipeline_completion_tokens'] = 240
        result=module.analyze(run,'D2',['student_p1'],[0])['arms']['student_p1']
        self.assertEqual(result['mean_completion_tokens'],90)
        self.assertEqual(result['mean_pipeline_completion_tokens'],240)
        self.assertEqual(result['pipeline_calls_per_response'],[2])
        run['responses']['r']['public_evidence']['selection_policy']='bank_order'
        self.assertEqual(module.analyze(run,'D2',['student_p1'],[0])['arms']['student_p1']['generated'],0)
        ordered=module.analyze(run,'D2',['student_p1'],[0],selection_policy='bank_order')
        self.assertEqual(ordered['arms']['student_p1']['generated'],1)
        self.assertEqual(ordered['selection_policy'],'bank_order')

    def test_source_bootstrap_uses_one_difference_per_source(self):
        result = module.paired([0., .5, 1.])
        self.assertEqual(result['sources'],3)
        self.assertEqual(result['mean_difference'],.5)

    def test_registered_eligible_set_defines_planned_student_denominator(self):
        run = {'partitions': {'D2': [1,2,3]}, 'responses': {}, 'evaluations': {}, 'banks': {}}
        result = module.analyze(run, 'D2', ['student_p1'], [0,1], [1,3])
        self.assertEqual(result['source_ids'], [1,3])
        self.assertEqual(result['arms']['student_p1']['planned'], 4)
        self.assertEqual(result['arms']['student_p1']['mean_normalized_score_all_planned_bounds'], [0,100])
        for ids in [[], [1,1], [4]]:
            with self.assertRaises(ValueError):
                module.analyze(run, 'D2', ['student_p1'], [0,1], ids)

    def test_count_arms_require_nesting_and_record_shared_full_input(self):
        run = {'partitions': {'D2': [1]}, 'banks': {'b': {'prompt':'convert_p2','output':{'clues':[{},{}]}}},
               'responses': {}, 'evaluations': {}}
        for k,clues in [(1,['a']), (2,['a','b'])]:
            run['responses'][str(k)] = {'source_index':1,'prompt':'student_p1','sampling':{'seed':0},
                'condition':'bank','bank_key':'b','evidence_hash':str(k),'request':{},
                'public_evidence':{'style':'sentence','disclosure':'medium','clue_count':k,'clues':clues}}
            run['evaluations'][str(k)] = {'response_key':str(k),'prompt':'evaluate_p2','output':{
                'status':'scored','score':k,'well_posed':True,'answer_correct':True,'shortcut':False,
                'clue_checks':[{'index':i,'compatible':True,'grounding':'explicit'} for i in range(1,k+1)]}}
        arms = ['student_p1#k1','student_p1#k2','student_p1#full']
        result = module.analyze(run,'D2',arms,[0])
        self.assertEqual(result['arms'][arms[0]]['mean_normalized_score_resolved'],25)
        self.assertEqual(result['arms'][arms[1]]['mean_normalized_score_resolved'],50)
        self.assertEqual(result['unique_student_responses_in_analysis'],2)
        self.assertEqual(result['response_reuse_across_arms']['2'],sorted(arms[1:]))
        run['responses']['1']['public_evidence']['clues'] = ['b']
        with self.assertRaisesRegex(ValueError,'Non-nested'):
            module.analyze(run,'D2',arms,[0])
        for label in ['student_p1#k0','student_p1#garbage']:
            with self.assertRaises(ValueError):
                module.arm_spec(label)


if __name__ == '__main__':
    unittest.main()
