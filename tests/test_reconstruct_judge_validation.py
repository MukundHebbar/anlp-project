import copy
import unittest

from anlp_project.reconstruct_judge_validation import validate_judgment, validation_notes


class JudgeCertificateTests(unittest.TestCase):
    def setUp(self):
        self.question = 'A rectangle has longer side9. What is its longer side?'
        self.response = {'question': self.question, 'justification': 'It is9.'}
        self.validity = {
            'status': 'scored',
            'evidence_integration': {'score': 2, 'clue_checks': [
                {'index': 1, 'verdict': 'partial', 'reason': 'Only side length given.'}]},
            'mathematical_validity': {'score': 0, 'question_well_posed': True,
                'supplied_answer_correct': True, 'verification_sound': False,
                'checks': [{'claim_quote': 'It is9.', 'reason': 'Simply restates the premise.'}]},
            'shortcut': {'present': True, 'type': 'answer-copy tautology',
                'premise_quote': 'longer side9', 'target_quote': 'What is its longer side?',
                'evidence': 'The same side is given and requested.'},
            'verification_certificate': {'requested_quantity': 'Longer side',
                'independent_check': 'The question gives9.', 'response_check': 'Restates9.'},
        }

    def check(self, out):
        return validate_judgment(out, 'validity', question=self.question,
                                 response=self.response, clue_count=1)

    def test_evidence_backed_override_passes(self):
        self.assertIs(self.check(self.validity), self.validity)

    def test_quote_in_justification_cannot_authorize_question_override(self):
        self.validity['shortcut']['premise_quote'] = 'It is9.'
        with self.assertRaisesRegex(ValueError, 'Shortcut quote not in question'):
            self.check(self.validity)

    def test_invented_math_quote_rejected(self):
        self.validity['mathematical_validity']['checks'][0]['claim_quote'] = 'The area is54.'
        with self.assertRaisesRegex(ValueError, 'claim quote not in response'):
            self.check(self.validity)

    def test_math_quote_spacing_is_logged_without_changing_output(self):
        self.validity['mathematical_validity']['checks'][0]['claim_quote'] = 'It is 9.'
        before = copy.deepcopy(self.validity)
        self.check(self.validity)
        self.assertEqual(self.validity, before)
        self.assertEqual(validation_notes(self.validity, self.response), [
            {'kind': 'math_quote_whitespace_only', 'claim_quote': 'It is 9.'}])

    def test_whitespace_fallback_cannot_change_a_number(self):
        self.validity['mathematical_validity']['checks'][0]['claim_quote'] = 'It is 8.'
        with self.assertRaisesRegex(ValueError, 'claim quote not in response'):
            self.check(self.validity)

    def test_shortcut_quotes_remain_exact(self):
        self.validity['shortcut']['premise_quote'] = 'longer side 9'
        with self.assertRaisesRegex(ValueError, 'Shortcut quote not in question'):
            self.check(self.validity)

    def test_duplicate_clue_coverage_rejected(self):
        self.validity['evidence_integration']['clue_checks'] *= 2
        with self.assertRaisesRegex(ValueError, 'clue checks'):
            self.check(self.validity)

    def test_unresolved_shortcut_cannot_be_scored(self):
        self.validity['shortcut']['present'] = None
        with self.assertRaisesRegex(ValueError, 'Unresolved label'):
            self.check(self.validity)

    def test_high_math_with_false_verification_rejected(self):
        self.validity['mathematical_validity']['score'] = 4
        with self.assertRaisesRegex(ValueError, 'High mathematical score'):
            self.check(self.validity)

    def test_absent_certificate_rejected(self):
        del self.validity['verification_certificate']
        with self.assertRaisesRegex(ValueError, 'Missing certificate'):
            self.check(self.validity)

    def test_equivalence_dimension_conflict_rejected(self):
        out = {'status': 'scored', 'premise_fidelity': {'score': 2},
               'target_fidelity': {'score': 4}, 'semantic_equivalent': True,
               'answer_in_premise': False,
               'verification_certificate': {k: 'A comparison' for k in
                   ['source_target', 'candidate_target', 'premise_comparison', 'target_comparison']}}
        with self.assertRaisesRegex(ValueError, 'Equivalence contradicts'):
            validate_judgment(out, 'fidelity', question='Find x.')

    def test_uncertainty_preserved_for_review(self):
        out = copy.deepcopy(self.validity)
        out['status'] = 'needs_review'
        out['shortcut'].update(present=None, type=None)
        self.assertIsNone(self.check(out)['shortcut']['present'])


if __name__ == '__main__':
    unittest.main()
