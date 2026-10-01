import unittest
from unittest import mock

from anlp_project import opd
from anlp_project.opd_monitor import repetition_score, should_stop


def rows(n):
    return [{"uid": f"solve-{i}", "split": "train"} for i in range(n)]


class OpdTests(unittest.TestCase):
    def test_slices_are_disjoint_seeded_and_train_only(self):
        with mock.patch.object(opd, "load_rows", return_value=rows(1000)):
            a, b = opd.make_slices("solve", 64, 20), opd.make_slices("solve", 64, 20)
            self.assertEqual(a, b)
            self.assertEqual((len(a["train"]), len(a["dev"])), (64, 20))
            self.assertFalse(set(a["train"]) & set(a["dev"]))
        bad = rows(10)
        bad[0]["split"] = "test"
        with mock.patch.object(opd, "load_rows", return_value=bad):
            with self.assertRaises(ValueError):
                opd.make_slices("solve", 2, 2)

    def test_repetition_score(self):
        self.assertEqual(repetition_score(list(range(100))), 0.0)
        self.assertGreater(repetition_score([1, 2, 3, 4] * 200), 0.9)
        self.assertEqual(repetition_score([1, 2]), 0.0)

    def test_stop_rule(self):
        cfg = opd.TRIAL_CONFIG
        ok = {"loss": 0.1, "mean_abs_logprob_gap": 0.02, "truncation_rate": 0.1}
        self.assertIsNone(should_stop([ok, ok, ok], cfg))
        high = {**ok, "truncation_rate": 0.4}
        self.assertIsNone(should_stop([ok, high, high], cfg))  # needs 3 in a row
        self.assertIn("truncation", should_stop([ok, high, high, high], cfg))
        self.assertIn("gap", should_stop([ok, {**ok, "mean_abs_logprob_gap": 0.9}], cfg))
        self.assertIn("NaN", should_stop([ok, {**ok, "loss": float("nan")}], cfg))
        # a plateau near 20% truncation is not a collapse (ceiling 0.35)
        plateau = {**ok, "truncation_rate": 0.22}
        self.assertIsNone(should_stop([{**ok, "truncation_rate": 0.03}, plateau, plateau, plateau], cfg))

    def test_repetition_stop_matches_the_observed_runs(self):
        cfg = opd.TRIAL_CONFIG
        step = lambda rep, trunc=0.0: {"loss": 0.1, "mean_abs_logprob_gap": 0.01, "truncation_rate": trunc, "repetition": rep}
        # RECONSTRUCT collapse: 0.05, 0.08, 0.27, 0.53, 0.58 -> stop after the 5th step
        recon = [step(r) for r in (0.05, 0.08, 0.27, 0.53)]
        self.assertIsNone(should_stop(recon, cfg))
        self.assertIn("repetition", should_stop(recon + [step(0.58)], cfg))
        # healthy SOLVE had a single 0.48 spike; JUDGE peaked at 0.29 -> never stop
        self.assertIsNone(should_stop([step(r) for r in (0.16, 0.14, 0.48, 0.34, 0.2)], cfg))
        self.assertIsNone(should_stop([step(r) for r in (0.04, 0.13, 0.29, 0.2)], cfg))


if __name__ == "__main__":
    unittest.main()
