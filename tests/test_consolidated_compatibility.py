"""Protect upstream self-judge behavior and compressed evidence after consolidating experiments."""
import gzip
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from anlp_project import opd, rewards
from anlp_project.opd_train import make_reward_judge

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('matrix_report', ROOT/'scripts/report_grpo_matrix.py')
report = importlib.util.module_from_spec(spec)
spec.loader.exec_module(report)


class ConsolidatedCompatibility(unittest.TestCase):
    def test_selfjudge_never_instantiates_a_remote_judge(self):
        with patch('anlp_project.jev_judging.Jev', side_effect=AssertionError('unexpected API client')):
            self.assertIsNone(make_reward_judge(['judge'], {'reward_judge':'none'}))
            self.assertIsNone(make_reward_judge(['solve','repair'], {'reward_judge':'jev'}))

    def test_gemma_backend_preserves_the_configured_calibration(self):
        with patch('anlp_project.gemma_judging.GemmaJudge') as client:
            cfg={'reward_judge':'gemma','reward_judge_path':'model','reward_calibration_dir':'calibration',
                 'reward_judge_port':8123}
            self.assertIs(make_reward_judge(['reconstruct'],cfg),client.return_value)
            client.assert_called_once_with('model','calibration',port=8123)

    def test_verdict_only_reward_does_not_require_a_step_or_an_explanation(self):
        row={'private':{'label':'incorrect','verdict_only':True}}
        self.assertEqual(rewards.judge_reward(row,'Decision: incorrect', 'stop',None),1.0)
        self.assertEqual(rewards.judge_reward(row,'Decision: correct', 'stop',None),0.0)
        self.assertEqual(rewards.judge_reward(row,'Decision: incorrect', 'length',None),0.0)
        self.assertEqual(opd.TRIAL_CONFIG['prompt_max_tokens'],4096)

    def test_matrix_loader_handles_compressed_records_and_missing_records(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'scores.jsonl'
            self.assertEqual(report.load(path),[])
            with gzip.open(str(path)+'.gz','wt') as output:
                output.write(json.dumps({'correct_strict':True})+'\n')
            self.assertEqual(report.load(path),[{'correct_strict':True}])
            path.write_text(json.dumps({'correct_strict':False})+'\n')
            self.assertEqual(report.load(path),[{'correct_strict':False}])


if __name__=='__main__':unittest.main()
