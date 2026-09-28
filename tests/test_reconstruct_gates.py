import copy
import unittest
from anlp_project.reconstruct_gates import validate_strict_disclosure, recovery_gate, public_disclosure_text, validate_copy_challenge, verify_response_bindings, check_student_readiness
from anlp_project.reconstruct import stable_hash, choose_clues


class StrictDisclosureTests(unittest.TestCase):
    def test_frozen_readiness_requires_review_and_exact_input(self):
        evidence={'clues':['a fact']}
        gate={'status':'pending','approved_evidence_hashes':{'8':stable_hash(evidence)}}
        run={'metadata':{'student_readiness':gate}}
        with self.assertRaises(ValueError):check_student_readiness(run,8,evidence)
        gate['status']='ready'
        check_student_readiness(run,8,evidence)
        with self.assertRaises(ValueError):check_student_readiness(run,8,{'clues':['changed fact']})
        with self.assertRaises(ValueError):check_student_readiness(run,9,evidence)

    def test_bank_order_preserves_audited_order_and_cannot_select_unaudited_subset(self):
        bank={'clues':[{'id':'c2','sentence':'second'},{'id':'c1','sentence':'first'}]}
        self.assertEqual(choose_clues(bank,2,42,'bank_order'),bank['clues'])
        with self.assertRaises(ValueError):choose_clues(bank,1,42,'bank_order')
        fixed={**bank,'fixed_order_ids':['c1','c2'],'fixed_order_seed':9}
        with self.assertRaises(ValueError):choose_clues(fixed,2,42,'bank_order')

    def test_stale_question_clue_or_reference_cannot_reuse_a_judgment(self):
        source={'question':'Find x.'}
        response={'source_index':7,'public_evidence':{'clues':['x+1=2']},
                  'output':{'question':'Find x.','justification':'x=1'}}
        response['evidence_hash']=stable_hash(response['public_evidence'])
        evaluation={'response_key':'r','source_index':7,'evidence_hash':response['evidence_hash'],
                    'response_output_hash':stable_hash(response['output'])}
        semantic={'response_key':'r','source_index':7,'candidate_question_hash':stable_hash('Find x.'),
                  'source_question_hash':stable_hash(source['question'])}
        self.assertTrue(verify_response_bindings('r',response,evaluation,semantic,source))
        for field,change in [('output',{'question':'Find y.'}),('public_evidence',{'clues':['different clue']})]:
            altered=copy.deepcopy(response);altered[field]=change
            self.assertFalse(verify_response_bindings('r',altered,evaluation,semantic,source))
        self.assertFalse(verify_response_bindings('r',response,evaluation,semantic,{'question':'Different original'}))
        del evaluation['response_output_hash']
        self.assertFalse(verify_response_bindings('r',response,evaluation,semantic,source))

    def setUp(self):
        self.audit={'status':'ACCEPT','scope':'public_disclosure','direct_question_copy':False,
          'premise_target_bundle_exposed':False,'complete_solution_exposed':False,
          'public_quotes':['x+y=10'],'missing_essential_element':'Area is missing',
          'inference_required':'Construct a compatible area constraint','reason':'Incomplete setup'}

    def test_hidden_quote_cannot_support_public_decision(self):
        self.audit['public_quotes']=['area24']
        with self.assertRaises(ValueError): validate_strict_disclosure(self.audit,'x+y=10','public_disclosure')

    def test_actual_public_labels_allowed_but_private_support_excluded(self):
        bank={'clues':[{'id':'c1','sentence':'x+y=10','hidden_support':'area24'}]}
        text=public_disclosure_text('6',bank,'public_disclosure')
        self.audit['public_quotes']=['FINAL ANSWER: 6','x+y=10']
        validate_strict_disclosure(self.audit,text,'public_disclosure')
        self.assertNotIn('area24',text)

    def test_conflicting_decision_and_flags_rejected(self):
        self.audit['complete_solution_exposed']=True
        with self.assertRaises(ValueError): validate_strict_disclosure(self.audit,'x+y=10','public_disclosure')
        self.audit['status']='REJECT'
        validate_strict_disclosure(self.audit,'x+y=10','public_disclosure')
        self.audit['complete_solution_exposed']=False
        with self.assertRaises(ValueError): validate_strict_disclosure(self.audit,'x+y=10','public_disclosure')

    def test_acceptance_cannot_hide_missing_or_uncertain_flags(self):
        self.audit['direct_question_copy']=None
        with self.assertRaises(ValueError): validate_strict_disclosure(self.audit,'x+y=10','public_disclosure')
        del self.audit['direct_question_copy']
        with self.assertRaises(ValueError): validate_strict_disclosure(self.audit,'x+y=10','public_disclosure')

    def test_same_answer_or_missing_evidence_never_counts(self):
        semantic={'status':'scored','source_recovery':0,'checks':dict.fromkeys(
          ['objects','premises','domains_parameters','target'],'different'),
          'correspondence':'Same answer only','reason':'Different problem'}
        result=recovery_gate({},semantic,{})
        self.assertFalse(result['confirmed_grounded_semantic_recovery'])
        self.assertIn('not_same_source_question',result['reasons'])
        self.assertIn('source_disclosure_passed_unverified',result['reasons'])

    def test_complete_joint_success_and_each_gate_is_necessary(self):
        semantic={'status':'scored','source_recovery':2,'checks':dict.fromkeys(
          ['objects','premises','domains_parameters','target'],'same'),
          'correspondence':'Variable renaming only','reason':'Same problem'}
        grounding={'status':'scored','score':4,'well_posed':True,'answer_correct':True,
                   'shortcut':False,'justification':'sufficient','clue_checks':[
                       {'index':1,'compatible':True,'grounding':'explicit'},
                       {'index':2,'compatible':True,'grounding':'implicit'}]}
        evidence=dict.fromkeys(['source_supported','public_disclosure_passed','source_disclosure_passed',
              'copy_challenge_reviewed_no_direct_recovery','independent_math_review_passed',
              'independent_semantic_review_passed','exact_record_binding_verified'],True)
        evidence['displayed_clue_count']=2
        self.assertTrue(recovery_gate(grounding,semantic,evidence)['confirmed_grounded_semantic_recovery'])
        for key in evidence:
            changed=copy.deepcopy(evidence);changed[key]=None
            self.assertFalse(recovery_gate(grounding,semantic,changed)['confirmed_grounded_semantic_recovery'])
        grounding['clue_checks'][1]['index']=1
        self.assertIn('complete_clue_coverage_unverified',recovery_gate(grounding,semantic,evidence)['reasons'])

    def test_copy_challenge_rejects_invented_evidence_and_forbidden_inference(self):
        value={'status':'direct_candidate','question':'Find the area of a unit square.',
               'alignments':[{'question_span':'unit square','public_quote':'unit square','operation':'copy'}],
               'reason':'Premises supplied'}
        validate_copy_challenge(value,'unit square')
        with self.assertRaises(ValueError):validate_copy_challenge(value,'rectangle')
        value['alignments'][0]['operation']='infer_missing_parameter'
        with self.assertRaises(ValueError):validate_copy_challenge(value,'unit square')

    def test_failed_copy_attack_is_a_structured_non_candidate(self):
        value={'status':'no_direct_reconstruction','question':None,'alignments':[],'reason':'Missing premise'}
        validate_copy_challenge(value,'some clue')
        value['question']='What is the supplied answer?'
        with self.assertRaises(ValueError):validate_copy_challenge(value,'some clue')


if __name__=='__main__': unittest.main()
