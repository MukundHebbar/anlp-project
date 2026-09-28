import copy
import unittest

from anlp_project.reconstruct import stable_hash
from anlp_project.reconstruct_gates import confirmation_recovery_count


def reviewed_row(index):
    source = {'question': 'Find the longer side of a rectangle of perimeter 20 and area 24.'}
    output = {'question': source['question'], 'justification': 'Sides 4 and 6.'}
    public = {'final_answer': '6', 'clues': ['The sides sum to 10.']}
    key = f'primary-{index}'
    response = {'source_index': index, 'sampling': {'seed': 0}, 'output': output,
                'public_evidence': public, 'evidence_hash': stable_hash(public)}
    evaluation = {'source_index': index, 'response_key': key,
                  'response_output_hash': stable_hash(output),
                  'evidence_hash': stable_hash(public), 'output': {
                      'status': 'scored', 'score': 4, 'well_posed': True,
                      'answer_correct': True, 'shortcut': False,
                      'justification': 'sufficient', 'clue_checks': [
                          {'index': 1, 'compatible': True, 'grounding': 'explicit'}]}}
    semantic = {'source_index': index, 'response_key': key,
                'candidate_question_hash': stable_hash(output['question']),
                'source_question_hash': stable_hash(source['question']), 'output': {
                    'status': 'scored', 'source_recovery': 2,
                    'checks': dict.fromkeys(['objects', 'premises', 'domains_parameters', 'target'], 'same'),
                    'correspondence': 'Identical mathematical question', 'reason': 'Same problem'}}
    evidence = dict.fromkeys([
        'source_supported', 'public_disclosure_passed', 'source_disclosure_passed',
        'copy_challenge_reviewed_no_direct_recovery', 'independent_math_review_passed',
        'independent_semantic_review_passed'], True)
    evidence['displayed_clue_count'] = 1
    return dict(source_index=index, response_key=key, source=source,
                response=response, evaluation=evaluation, semantic=semantic, evidence=evidence)


class ConfirmationTests(unittest.TestCase):
    def test_five_pass_but_do_not_authorize_release(self):
        result = confirmation_recovery_count(list(range(25)), [reviewed_row(i) for i in range(5)])
        self.assertEqual(result['confirmed_successes'], 5)
        self.assertTrue(result['recovery_count_gate_passed'])
        self.assertFalse(result['overall_release_assessed'])
        self.assertEqual(len(result['outcomes']), 25)

    def test_alternative_seed_leak_and_stale_binding_cannot_rescue_fifth(self):
        rows = [reviewed_row(i) for i in range(5)]
        changes = [
            ('response', 'sampling', {'seed': 1}),
            ('evidence', 'source_disclosure_passed', False),
            ('evaluation', 'response_output_hash', 'stale'),
            ('semantic', 'output', {**rows[4]['semantic']['output'], 'source_recovery': 1}),
        ]
        for section, field, value in changes:
            with self.subTest(field=field):
                changed = copy.deepcopy(rows)
                changed[4][section][field] = value
                changed[4]['evidence']['exact_record_binding_verified'] = True
                result = confirmation_recovery_count(list(range(25)), changed)
                self.assertEqual(result['confirmed_successes'], 4)
                self.assertFalse(result['recovery_count_gate_passed'])

    def test_duplicate_outside_and_short_manifests_rejected(self):
        for manifest, rows in [
            (list(range(24)), []),
            ([0] * 25, []),
            (list(range(25)), [reviewed_row(0), reviewed_row(0)]),
            (list(range(25)), [reviewed_row(25)]),
        ]:
            with self.assertRaises(ValueError):
                confirmation_recovery_count(manifest, rows)


if __name__ == '__main__':
    unittest.main()
