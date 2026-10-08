import unittest

from anlp_project.strict_gates import judge_gate, reconstruct_format_flags, reconstruct_gate, solve_gate


class ReconstructGate(unittest.TestCase):
    def test_clean_questions_pass(self):
        for answer, q in [("6", "A rectangle has perimeter 20 and area 24. Find its longer side."),
                          ("Alice", "Alice and Bob alternate picking digits. Who has a winning strategy?"),
                          ("C", "Let I be the 4x4 identity matrix and A have eigenvalues 2 and 5. Which of (a) 6 (b) 7 is an eigenvalue?"),
                          ("Yes", "Is every group of prime order cyclic?"),
                          ("13", "The witness's observation of the trial is recorded. How many days pass before day 13 ends?")]:
            self.assertEqual(reconstruct_gate(answer, q), [], q)

    def test_answer_in_question(self):
        self.assertIn("answer_in_question", reconstruct_gate("13", "Find the remainder of 2^100 mod 17.\nAnswer: 13."))
        self.assertIn("answer_in_question", reconstruct_gate("0", "Find the integral of 1/(z^2-1). (Note: The answer is -2)"))
        self.assertIn("answer_in_question", reconstruct_gate("\\dfrac{1}{n}", "Given that the probability is $\\frac{1}{n}$, what is the probability?"))
        self.assertIn("answer_in_question", reconstruct_gate("4^n", "Given that S <= 4^n, what is the value of this upper bound?"))

    def test_monologue(self):
        self.assertIn("monologue", reconstruct_gate("2", "Maybe it is an integral? No. Perhaps a sum. What gives 2?"))
        self.assertIn("monologue", reconstruct_gate("5", "Find x such that 3^x = 5 mod 7. Wait, let me re-read the clues."))
        self.assertIn("monologue", reconstruct_gate("5", "Find the area of the triangle.\n\nObservations:\n1. The triangle is right."))
        self.assertIn("monologue", reconstruct_gate("5", "Find n. Justification: n = 5 because ..."))

    def test_no_question(self):
        self.assertIn("no_question", reconstruct_gate("13", "..."))
        self.assertIn("no_question", reconstruct_gate("13", "Some numbers 1, 2, 3 and a graph G here."))

    def test_several_drafts_is_a_format_flag(self):
        text = '{"question": "Find x."} ... {"question": "Find y such that y = 2x."}'
        self.assertEqual(reconstruct_format_flags(text), ["several_drafts"])
        self.assertEqual(reconstruct_format_flags('{"question": "Find x."}'), [])


class JudgeGate(unittest.TestCase):
    def test_single_consistent_verdict_passes(self):
        self.assertEqual(judge_gate("Decision: incorrect\nFirst wrong step: S3\nExplanation: ..."), [])
        self.assertEqual(judge_gate("Decision: correct\nFirst wrong step: none"), [])
        self.assertEqual(judge_gate("Decision: incorrect\nFirst wrong step: S3\n...\nDecision: incorrect\nFirst wrong step: S3"), [])

    def test_hedging_fails(self):
        text = "Decision: incorrect\nFirst wrong step: S2\n...\nDecision: correct\nFirst wrong step: none"
        self.assertEqual(set(judge_gate(text)), {"several_decisions", "several_steps"})
        self.assertIn("several_steps", judge_gate("Decision: incorrect\nFirst wrong step: S3\nDecision: incorrect\nFirst wrong step: S5"))

    def test_mismatch_fails(self):
        self.assertEqual(judge_gate("Decision: incorrect\nFirst wrong step: none"), ["decision_step_mismatch"])
        self.assertEqual(judge_gate("Decision: correct\nFirst wrong step: S4"), ["decision_step_mismatch"])


class SolveGate(unittest.TestCase):
    def test_equivalent_repeats_pass(self):
        self.assertEqual(solve_gate("<final_answer>1/2</final_answer> ... <final_answer>0.5</final_answer>"), [])
        self.assertEqual(solve_gate("<final_answer>7</final_answer>"), [])

    def test_different_answers_fail(self):
        self.assertEqual(solve_gate("<final_answer>50</final_answer> or <final_answer>65</final_answer>"), ["several_answers"])


if __name__ == "__main__":
    unittest.main()
