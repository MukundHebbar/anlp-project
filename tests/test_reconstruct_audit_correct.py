import copy
import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    'gen_dataset', Path(__file__).resolve().parents[1] / 'scripts' / 'generate_reconstruct_dataset_v1.py')
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)

SOURCE = 'A rectangle has perimeter 20 and area 24. What is its longer side?'
EV = dict(final_answer='6', clues=[
    dict(id='c1', sentence='The sides x and y are positive.'),
    dict(id='c2', sentence='The side lengths satisfy x+y=10.'),
    dict(id='c3', sentence='The product of the sides is xy=24.'),
    dict(id='c4', sentence='The requested result is the larger side.'),
])
CORRECTED = dict(
    decision='CORRECTED', source_answer_correct=True,
    findings=[dict(id='c1', verdict='keep', defect='none', reason='Sound.'),
              dict(id='c2', verdict='keep', defect='none', reason='Sound.'),
              dict(id='c3', verdict='replace', defect='question_disclosure', reason='Exposes the area premise.'),
              dict(id='c4', verdict='keep', defect='none', reason='Sound.')],
    corrected_clues=[dict(id='c1', sentence='The sides x and y are positive.', hidden_support='s'),
                     dict(id='c2', sentence='The side lengths satisfy x+y=10.', hidden_support='s'),
                     dict(id='c3', sentence='Writing the unreported area as K gives x(10-x)=K.', hidden_support='s'),
                     dict(id='c4', sentence='The requested result is the larger side.', hidden_support='s')],
    missing_essential_element='The area 24.', inference_required='Infer K from the answer.', reason='Area withheld.')


def variant(**changes):
    out = copy.deepcopy(CORRECTED)
    out.update(changes)
    return out


class ValidateCorrectionTests(unittest.TestCase):
    def test_valid_correction_passes(self):
        self.assertEqual(g.validate_correction(copy.deepcopy(CORRECTED), EV, SOURCE)['decision'], 'CORRECTED')

    def test_kept_clue_must_survive_verbatim(self):
        out = copy.deepcopy(CORRECTED)
        out['corrected_clues'][0]['sentence'] = 'Both sides are positive numbers.'
        with self.assertRaises(AssertionError):
            g.validate_correction(out, EV, SOURCE)

    def test_needs_exactly_four_clues(self):
        out = copy.deepcopy(CORRECTED)
        out['corrected_clues'] = out['corrected_clues'][:3]
        with self.assertRaises(AssertionError):
            g.validate_correction(out, EV, SOURCE)

    def test_corrected_must_differ_from_original(self):
        out = copy.deepcopy(CORRECTED)
        out['corrected_clues'][2]['sentence'] = EV['clues'][2]['sentence']
        with self.assertRaises(AssertionError):
            g.validate_correction(out, EV, SOURCE)

    def test_corrected_clue_cannot_contain_source_question(self):
        out = copy.deepcopy(CORRECTED)
        out['corrected_clues'][2]['sentence'] = 'Consider: ' + SOURCE
        with self.assertRaises(AssertionError):
            g.validate_correction(out, EV, SOURCE)

    def test_findings_must_cover_each_clue_once(self):
        out = copy.deepcopy(CORRECTED)
        out['findings'] = out['findings'][:3]
        with self.assertRaises(AssertionError):
            g.validate_correction(out, EV, SOURCE)

    def test_accept_unchanged_cannot_report_a_defect(self):
        findings = copy.deepcopy(CORRECTED['findings'])
        with self.assertRaises(AssertionError):
            g.validate_correction(variant(decision='ACCEPT_UNCHANGED', corrected_clues=[], findings=findings), EV, SOURCE)

    def test_accept_unchanged_and_unrepairable_return_no_clues(self):
        clean = [dict(f, verdict='keep', defect='none') for f in CORRECTED['findings']]
        self.assertEqual(g.validate_correction(
            variant(decision='ACCEPT_UNCHANGED', corrected_clues=[], findings=clean), EV, SOURCE)['decision'], 'ACCEPT_UNCHANGED')
        with self.assertRaises(AssertionError):
            g.validate_correction(variant(decision='UNREPAIRABLE'), EV, SOURCE)


if __name__ == '__main__':
    unittest.main()
