import unittest

from anlp_project import jev_judging as jj
from anlp_project import rewards as rw


def judge_row(label="incorrect"):
    return {"uid": "judge-1", "task": "judge", "public": {"problem": "p", "proposed_solution": [{"step_id": "S1", "text": "t"}]},
            "private": {"label": label, "first_error_step_id": "S2" if label == "incorrect" else None,
                        "first_error_explanation": "x", "error_type": "t", "teacher_target_response": "r"}}


def recon_row():
    return {"uid": "reconstruct-1", "task": "reconstruct", "question": "Find the longer side of a rectangle with perimeter 20 and area 24.",
            "public_input": {"final_answer": "6", "clues": ["a", "b", "c", "d"]}}


def score(level):
    return {"score": float(level), "probabilities": {str(level): 1.0}}


class FakeJev:
    """Returns fixed answers for every question asked; ``fail`` raises like a transport error."""

    def __init__(self, level=4, shortcut=False, fail=False):
        self.level, self.shortcut, self.fail = level, shortcut, fail

    def call(self, state, questions):
        if self.fail:
            raise RuntimeError("HTTP 503")
        out = {}
        for name, q in questions.items():
            if q["type"] == "score":
                out[name] = score(self.level)
            elif q["type"] == "noul":
                out[name] = {"noul": 0.9 if (self.shortcut and name in ("states_value",)) else 0.1}
            else:
                out[name] = {"choice": "not a shortcut", "probabilities": {"not a shortcut": 0.9}}
        return {"answers": out}


class SolveReward(unittest.TestCase):
    def test_values(self):
        row = {"final_answer": "6"}
        self.assertEqual(rw.solve_reward(row, "... <final_answer>6</final_answer>", "stop"), 1.0)
        self.assertEqual(rw.solve_reward(row, "... <final_answer>7</final_answer>", "stop"), 0.0)
        self.assertEqual(rw.solve_reward(row, "<final_answer>6</final_answer>", "length"), 0.0)  # truncated
        self.assertEqual(rw.solve_reward(row, "<final_answer>6</final_answer> or <final_answer>7</final_answer>", "stop"), 0.0)


class JudgeReward(unittest.TestCase):
    def test_gating_and_parts(self):
        row = judge_row()
        good = "Decision: incorrect\nFirst wrong step: S2\nExplanation: e"
        self.assertEqual(rw.judge_reward(row, good, "stop", None), 0.75)
        self.assertEqual(rw.judge_reward(row, good, "stop", FakeJev(level=4)), 1.0)
        self.assertEqual(rw.judge_reward(row, "Decision: incorrect\nFirst wrong step: S3", "stop", None), 0.5)
        self.assertEqual(rw.judge_reward(row, "Decision: correct\nFirst wrong step: none", "stop", FakeJev()), 0.0)
        hedge = good + "\nDecision: correct\nFirst wrong step: none"
        self.assertEqual(rw.judge_reward(row, hedge, "stop", FakeJev()), 0.0)
        self.assertEqual(rw.judge_reward(row, good, "length", FakeJev()), 0.0)

    def test_failed_jev_call_is_none(self):
        row = judge_row()
        self.assertIsNone(rw.judge_reward(row, "Decision: incorrect\nFirst wrong step: S2", "stop", FakeJev(fail=True)))

    def test_reward_range(self):
        r = rw.judge_reward(judge_row("correct"), "Decision: correct\nFirst wrong step: none", "stop", FakeJev(level=2))
        self.assertTrue(0.0 <= r <= 1.0)


class ReconstructReward(unittest.TestCase):
    def test_scored_gated_shortcut_failed(self):
        row = recon_row()
        ok = '{"assumptions":["a"],"question":"A rectangle has perimeter 20 and area 24. What is its longer side?","justification":"j"}'
        r = rw.reconstruct_reward(row, ok, "stop", FakeJev(level=4))
        self.assertAlmostEqual(r, 1.0)
        gated = '{"assumptions":[],"question":"Find the longer side. Answer: 6.","justification":"j"}'
        self.assertEqual(rw.reconstruct_reward(row, gated, "stop", FakeJev(level=4)), 0.0)
        self.assertEqual(rw.reconstruct_reward(row, ok, "stop", FakeJev(level=4, shortcut=True)), 0.0)
        self.assertEqual(rw.reconstruct_reward(row, ok, "length", FakeJev(level=4)), 0.0)
        self.assertIsNone(rw.reconstruct_reward(row, ok, "stop", FakeJev(fail=True)))
        drafts = '{"question":"Find x?","justification":"j"} then {"assumptions":[],"question":"A rectangle has perimeter 20 and area 24. What is its longer side?","justification":"j"}'
        self.assertAlmostEqual(rw.reconstruct_reward(row, drafts, "stop", FakeJev(level=4)), 0.9)


if __name__ == "__main__":
    unittest.main()
