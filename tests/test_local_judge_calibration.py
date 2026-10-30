import importlib.util
import itertools
from pathlib import Path
import random
import unittest

spec = importlib.util.spec_from_file_location('calibration_fit',
    Path(__file__).resolve().parents[1] / 'phase2/local_judge_calibration/fit.py')
fit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fit)


class CalibrationTests(unittest.TestCase):
    def test_explicit_label_reader_sums_spellings_and_rejects_missing_logits(self):
        import math
        from types import SimpleNamespace
        spec = importlib.util.spec_from_file_location('calibration_infer',
            fit.ROOT / 'phase2/local_judge_calibration/infer.py')
        infer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(infer)
        ids = {'yes': [1, 2], 'no': [3]}
        scores = {i: SimpleNamespace(logprob=math.log(p))
                  for i,p in [(1,.01),(2,.02),(3,.07),(4,.9)]}
        probs, mass = infer.explicit_label_probs(scores, ['Yes', 'No'], ids)
        self.assertAlmostEqual(mass, .1)
        self.assertAlmostEqual(probs[0], .3)
        self.assertAlmostEqual(probs[1], .7)
        del scores[2]
        with self.assertRaises(ValueError):
            infer.explicit_label_probs(scores, ['Yes','No'], ids)

    def test_optimized_search_matches_original_kappa_objective(self):
        grid = [i / 2 for i in range(9)]
        for seed in range(6):
            rng = random.Random(seed)
            weights = [rng.random()*4 for _ in range(30)]
            truth = [rng.randrange(5) for _ in weights]
            score = lambda cut: fit.cj.qwk(truth, [sum(w>=t for t in cut) for w in weights])
            original = max(itertools.combinations(grid, 4), key=score)
            actual = fit.fit_cutoffs(weights, truth, grid)
            self.assertAlmostEqual(score(original), score(actual), places=12)

    def test_reproduces_historical_qwen_cutoffs(self):
        import json
        reference = fit.ROOT / 'phase2/results/local-judge-calibration/qwen27b-reference/summary.json'
        self.assertTrue(reference.exists())
        expected = json.loads((fit.ROOT / 'data/jev-eval/calibration-qwen27b-v1.json').read_text())['cutoffs']
        self.assertEqual(expected, json.loads(reference.read_text())['cutoffs'])
