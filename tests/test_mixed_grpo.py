import collections
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from anlp_project import opd
from anlp_project.opd_train import keep_best, per_task_stats, rolling_score


class MixedPromptsTests(unittest.TestCase):
    def test_every_batch_of_30_holds_ten_of_each_task(self):
        prompts = opd.mixed_prompts(1134)
        self.assertEqual(len(prompts), 3402)
        for i in range(0, len(prompts) - 29, 30):
            counts = collections.Counter(p["task"] for p in prompts[i:i + 30])
            self.assertEqual(counts, {"solve": 10, "judge": 10, "reconstruct": 10})

    def test_no_repeats_and_no_dev_questions(self):
        prompts = opd.mixed_prompts(1134)
        uids = [p["uid"] for p in prompts]
        self.assertEqual(len(uids), len(set(uids)))
        dev = {r["uid"] for t in opd.MIXED_TASKS for r in opd.slice_rows(t, "dev")}
        self.assertFalse(dev & set(uids))
        self.assertTrue(all(p["uid"].startswith(p["task"]) for p in prompts))

    def test_same_order_as_the_single_task_arms(self):
        prompts = opd.mixed_prompts(1134)
        for t in opd.MIXED_TASKS:
            single = [p["uid"] for p in opd.matrix_prompts(t, 1134)]
            self.assertEqual([p["uid"] for p in prompts if p["task"] == t], single)


class PerTaskStatsTests(unittest.TestCase):
    def test_per_task_numbers(self):
        task_of = {"s1": "solve", "j1": "judge"}
        ros = ([{"uid": "s1", "reward": r, "ids": [0] * 10, "finish": "stop"} for r in (1.0, 0.0)] +
               [{"uid": "j1", "reward": 0.5, "ids": [0] * 4, "finish": "length"},
                {"uid": "j1", "reward": None, "ids": [0] * 4, "finish": "stop"}])
        out = per_task_stats(ros, task_of, mixed={"s1"}, g_mean={"s1": 0.5, "j1": 0.5})
        self.assertEqual(out["solve"]["groups_mixed"], 1)
        self.assertAlmostEqual(out["solve"]["adv_abs_mean"], 0.5)
        self.assertAlmostEqual(out["judge"]["reward_mean"], 0.5)
        self.assertEqual(out["judge"]["reward_failed"], 1)
        self.assertAlmostEqual(out["judge"]["truncation_rate"], 0.5)


class RollingScoreTests(unittest.TestCase):
    def rec(self, s, j):
        return {"reward_mean": (s + j) / 2, "per_task": {"solve": {"reward_mean": s}, "judge": {"reward_mean": j}}}

    def test_mixed_score_is_the_average_gain_per_task(self):
        recs = [self.rec(0.5, 0.2)] * 2 + [self.rec(0.7, 0.2)] * 2
        # window 2: solve gains 0.2, judge 0.0 -> 0.1
        self.assertAlmostEqual(rolling_score(recs, 2), 0.1)

    def test_single_task_score_is_the_rolling_mean(self):
        recs = [{"reward_mean": x} for x in (0.1, 0.2, 0.3, 0.5)]
        self.assertAlmostEqual(rolling_score(recs, 2), 0.4)
        self.assertIsNone(rolling_score(recs[:1], 2))

    def test_keep_best_uses_the_mixed_score(self):
        d = Path(tempfile.mkdtemp())
        try:
            (d / "adapters").mkdir()
            m = d / "metrics.jsonl"
            for k, (s, j) in enumerate([(0.5, 0.2), (0.5, 0.2), (0.9, 0.2), (0.5, 0.2)], 1):
                a = d / "adapters" / f"step{k}"
                a.mkdir()
                (a / "adapter_model.safetensors").write_text("x")
                with m.open("a") as fh:
                    fh.write(json.dumps(self.rec(s, j)) + "\n")
                keep_best(d, m, a, k, 2, 1, lambda _msg: None)
            self.assertEqual(json.loads((d / "best.json").read_text())[0]["step"], 3)
        finally:
            shutil.rmtree(d)


if __name__ == "__main__":
    unittest.main()
