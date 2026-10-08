import unittest

from anlp_project import jev_judging as jj

CUT = jj._cutoffs()


def score(level):  # a Jev Score answer whose expectation is `level`
    return {"score": float(level), "probabilities": {str(level): 1.0}}


def judge_row(label="incorrect"):
    return {"uid": "judge-1", "task": "judge",
            "private": {"label": label, "first_error_step_id": "S2" if label == "incorrect" else None,
                        "first_error_explanation": "x", "error_type": "t", "teacher_target_response": "r"}}


def recon_row():
    return {"uid": "reconstruct-1", "task": "reconstruct", "question": "Find the longer side of a rectangle with perimeter 20 and area 24.",
            "public_input": {"final_answer": "6", "clues": ["a", "b", "c", "d"]}}


NO_SHORTCUT = {"shortcut_type": {"probabilities": {"not a shortcut": 0.9}}, "states_value": {"noul": 0.1},
               "repeats_answer": {"noul": 0.1}}


class JudgeScoring(unittest.TestCase):
    def test_gated_answer_scores_zero(self):
        text = "Decision: incorrect\nFirst wrong step: S2\nDecision: correct\nFirst wrong step: none"
        out = jj.score_record(judge_row(), text, {"gate": ["several_decisions"], "calls": {}}, CUT)
        self.assertEqual((out["status"], out["score_100"], out["verdict_correct_strict"]), ("gated", 0.0, False))

    def test_full_marks(self):
        text = "Decision: incorrect\nFirst wrong step: S2\nExplanation: ..."
        rec = {"gate": [], "calls": {"M": {"answers": {"M": score(4)}}, "E": {"answers": {"E": score(4)}}}}
        out = jj.score_record(judge_row(), text, rec, CUT)
        self.assertEqual(out["dimensions"], {"V": 4, "L": 4, "E": 4, "M": 4})
        self.assertEqual(out["score_100"], 100.0)
        self.assertTrue(out["verdict_correct_strict"])

    def test_wrong_verdict_keeps_only_m(self):
        text = "Decision: correct\nFirst wrong step: none\nExplanation: ..."
        rec = {"gate": [], "calls": {"M": {"answers": {"M": score(4)}}}}
        out = jj.score_record(judge_row(), text, rec, CUT)
        self.assertEqual(out["dimensions"], {"V": 0, "L": 0, "E": 0, "M": 4})

    def test_correct_label_e_uses_three_levels(self):
        text = "Decision: correct\nFirst wrong step: none\nExplanation: ..."
        rec = {"gate": [], "calls": {"M": {"answers": {"M": score(4)}}, "E": {"answers": {"E": score(2)}}}}
        out = jj.score_record(judge_row("correct"), text, rec, CUT)
        self.assertEqual(out["dimensions"]["E"], 4)


class ReconstructScoring(unittest.TestCase):
    def test_statuses(self):
        row = recon_row()
        self.assertEqual(jj.score_record(row, "", {"gate": ["unusable_response"], "calls": {}}, CUT)["status"], "unusable_response")
        self.assertEqual(jj.score_record(row, "", {"gate": ["monologue"], "calls": {}}, CUT)["score_100"], 0.0)
        shortcut = {"shortcut_type": {"probabilities": {"not a shortcut": 0.2}}, "states_value": {"noul": 0.1},
                    "repeats_answer": {"noul": 0.1}}
        out = jj.score_record(row, "", {"gate": [], "calls": {"shortcut": {"answers": shortcut}}}, CUT)
        self.assertEqual((out["status"], out["score_100"]), ("shortcut", 0.0))

    def test_scored(self):
        rec = {"gate": [], "calls": {"shortcut": {"answers": NO_SHORTCUT},
                                     "fidelity": {"answers": {"P": score(4), "T": score(4), "equivalent": {"noul": 0.9}}},
                                     "validity": {"answers": {"E": score(4), "M": score(4)}}}}
        out = jj.score_record(recon_row(), "", rec, CUT)
        self.assertEqual((out["status"], out["score_100"], out["semantic_equivalent"]), ("scored", 100.0, True))


if __name__ == "__main__":
    unittest.main()
