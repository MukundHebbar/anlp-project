import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location(
    'converter_report', Path(__file__).resolve().parents[1] / 'scripts/report_reconstruct_converter.py')
report = importlib.util.module_from_spec(spec)
spec.loader.exec_module(report)


class ConverterCoverageTests(unittest.TestCase):
    def test_missing_calls_remain_possible_without_dropping_denominator(self):
        result = report.summarize({'banks': {}, 'audits': {}}, 'convert_p4')
        self.assertEqual(result['accepted'], 0)
        self.assertEqual(result['original_sources'], 12)
        self.assertEqual(len(result['missing_conversions']), 11)
        self.assertAlmostEqual(result['coverage_upper_bound'], 11/12)
        self.assertNotIn(20, result['potential_additional_acceptances'])

    def test_rejections_and_unsuitable_banks_are_not_unresolved_successes(self):
        run = {'banks': {
            'a': {'source_index': 8, 'prompt': 'convert_p4', 'output': {'status': 'NOT_SUITABLE'}},
            'b': {'source_index': 27, 'prompt': 'convert_p4', 'output': {'status': 'OK', 'clues': []}},
        }, 'audits': {'b_reject': {'bank_key': 'b', 'prompt': 'audit_public_p4', 'output': {'status': 'REJECT'}}}}
        result = report.summarize(run, 'convert_p4')
        self.assertNotIn(8, result['potential_additional_acceptances'])
        self.assertNotIn(27, result['potential_additional_acceptances'])
        self.assertAlmostEqual(result['coverage_upper_bound'], 9/12)


if __name__ == '__main__':
    unittest.main()
