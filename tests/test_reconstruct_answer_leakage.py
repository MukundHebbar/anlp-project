import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "audit_reconstruct_answer_leakage",
    Path(__file__).resolve().parents[1] / "scripts" / "audit_reconstruct_answer_leakage.py",
)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class TestAnswerLeakageDetection(unittest.TestCase):
    def test_detects_answer_given_as_premise(self):
        question = "Find the smallest prime p such that ... is less than p, given that the answer is 11."
        self.assertTrue(audit.has_answer_leakage(question, "11"))

    def test_detects_answer_used_as_hypothesis_variable(self):
        question = "Find the number of ordered triples (a,b,c) of positive integers such that a + b + c = 3540 and gcd(a,b,c) = 1."
        self.assertTrue(audit.has_answer_leakage(question, "3540"))

    def test_single_digit_answers_are_not_flagged_to_avoid_false_positives(self):
        # A single-digit answer (e.g. "5") is too likely to coincidentally appear
        # in an unrelated premise; the heuristic only checks 2+ digit numerals.
        question = "Let k be an odd integer. If k=5, what is the value of the expression?"
        self.assertFalse(audit.has_answer_leakage(question, "5"))

    def test_clean_reconstruction_not_flagged(self):
        question = "A rectangle has perimeter 20 and area 24. What is its longer side length?"
        self.assertFalse(audit.has_answer_leakage(question, "6"))

    def test_short_or_common_digit_answers_are_not_flagged(self):
        question = "Evaluate the definite integral of 1/(x + sqrt(1 - x^2)) from 0 to 1."
        self.assertFalse(audit.has_answer_leakage(question, "1"))

    def test_non_numeric_answer_is_not_flagged(self):
        question = "Determine who has the correct claim among the two players."
        self.assertFalse(audit.has_answer_leakage(question, "Jill"))


if __name__ == "__main__":
    unittest.main()
