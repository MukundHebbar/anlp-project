import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('ledger', Path(__file__).resolve().parents[1] / 'scripts/reconstruct_cost_ledger.py')
ledger = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ledger)


class LedgerTests(unittest.TestCase):
    def test_calibration_raw_records_and_id_failures_are_included(self):
        raw = {'content': 'judge', 'usage': {'estimated_cost': .02}, 'elapsed_seconds': 3}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run = {'records': {'case': {'raw': raw}},
                   'failures': [{'id': 'same', 'raw': raw}, {'id': 'no-usage', 'raw': None}]}
            (root / 'calibration.json').write_text(json.dumps(run))
            (root / 'local.json').write_text(json.dumps({'responses': {'case': {'raw': {'content': 'local'}}}}))
            result = ledger.collect(root)
            self.assertEqual(result['unique_cost_bearing_records'], 1)
            self.assertAlmostEqual(result['all_recorded_estimated_cost_usd'], .02)
            self.assertEqual(result['unique_records_without_usage'], 1)

    def test_copies_and_recovered_failure_count_once_distinct_calls_count_twice(self):
        raw = {'content': 'x', 'reasoning': None, 'usage': {'estimated_cost': .1},
               'elapsed_seconds': 1, 'finish_reason': 'stop'}
        row = {'raw_content': 'x', 'request': {k: v for k, v in raw.items() if k != 'content'}}
        run = {'banks': {'a': row}, 'failures': [{'stage': 'audit', 'key': 'a', 'raw': raw}]}
        run['banks']['synthetic'] = {'model': 'mechanical_composition', 'output': {}}
        run['banks']['authored'] = {'model': 'authored_fixture', 'output': {}}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'pilot-v1').mkdir()
            (root / 'pilot-v1/run.json').write_text(json.dumps(run))
            (root / 'copy.json').write_text(json.dumps(run))
            result = ledger.collect(root)
            self.assertEqual(result['unique_cost_bearing_records'], 1)
            self.assertAlmostEqual(result['all_recorded_estimated_cost_usd'], .1)
            self.assertAlmostEqual(result['followup_only_estimated_cost_usd'], 0)
            run['banks']['b'] = {'raw_content': 'x', 'request': {**row['request'], 'elapsed_seconds': 2}}
            run['failures'].append({'stage': 'audit', 'key': 'missing', 'raw': None})
            (root / 'copy.json').write_text(json.dumps(run))
            result = ledger.collect(root)
            self.assertEqual(result['unique_cost_bearing_records'], 2)
            self.assertAlmostEqual(result['all_recorded_estimated_cost_usd'], .2)
            self.assertAlmostEqual(result['followup_only_estimated_cost_usd'], .1)
            self.assertEqual(result['unique_records_without_usage'], 1)
