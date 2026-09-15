import unittest

from anlp_project.solution_verification import (
    compare_answer_detailed,
    compare_answers,
    extract_final_answer,
    normalize_answer,
    usage_cost,
    verify_record,
)


class SolutionVerificationTests(unittest.TestCase):
    def test_tag_and_legacy_boxed_extraction(self):
        self.assertEqual(
            extract_final_answer("work\n<final_answer>\\frac{1}{2}</final_answer>"),
            ("\\frac{1}{2}", "tag"),
        )
        self.assertEqual(extract_final_answer(r"work \(\boxed{4}\)"), ("4", "boxed_fallback"))
        self.assertEqual(extract_final_answer("no answer"), (None, "missing_final_answer"))

    def test_numeric_and_text_comparison(self):
        self.assertEqual(compare_answers(r"\\dfrac{3}{2}", "1.5"), "correct")
        self.assertEqual(compare_answers("Yes", "yes"), "correct")
        self.assertEqual(compare_answers("Yes", "Yes, with justification."), "correct")
        self.assertEqual(compare_answers("Yes", "No"), "incorrect")
        self.assertEqual(compare_answers("D", "(d) Both an essential singularity and poles."), "correct")
        self.assertEqual(compare_answers("Jill", "Jill is correct; the bound is attainable."), "correct")
        self.assertEqual(compare_answers("4", "5"), "incorrect")

    def test_formatting_and_symbolic_equivalence(self):
        self.assertEqual(normalize_answer(r"\(\sqrt{3}\)"), "sqrt(3)")
        self.assertEqual(compare_answers(r"\sqrt{3}", r"\(\sqrt{3}\)"), "correct")
        self.assertEqual(compare_answers(r"\dfrac{\pi}{4}", r"\frac{\pi}{4}"), "correct")
        self.assertEqual(compare_answers(r"l^2(\mathbb{N})", r"\ell^2(\mathbb N)"), "correct")
        self.assertEqual(compare_answers("1", "n=1"), "correct")
        self.assertEqual(compare_answers(r"(9e^2, \infty)", r"\boxed{a>9e^2}"), "correct")
        self.assertEqual(compare_answers("101", r"x \equiv 101 \pmod{2016}"), "correct")
        self.assertEqual(compare_answers(r"(x+1)^2", r"x^2+2*x+1"), "correct")
        self.assertEqual(compare_answers(r"2^n-1", r"2^n+1"), "incorrect")
        self.assertEqual(compare_answers(r"\\infty", "infinity"), "correct")

    def test_ambiguous_symbolic_and_proof_forms_remain_unverified(self):
        self.assertEqual(compare_answers("1", r"1/R (so none of the listed options)"), "unverified")
        self.assertEqual(compare_answers(r"\tau(n)", r"\tau(n)=\prod_{p^\alpha\parallel n}(\alpha+1)"), "unverified")
        self.assertEqual(compare_answers(r"C_3", "For every n >= 3, take G=C_n."), "unverified")

    def test_unsafe_expression_is_not_evaluated(self):
        result = compare_answer_detailed("x", "__import__('os').system('id')")
        self.assertEqual(result["answer_status"], "unverified")
        self.assertEqual(result["verification_method"], "no_safe_equivalence_rule")

    def test_cost_and_record_gate(self):
        record = {
            "final_answer": "4",
            "solve_solution": "proof <final_answer>4</final_answer>",
            "solve_usage": {"prompt_tokens": 100, "completion_tokens": 200},
        }
        result = verify_record(record)
        self.assertEqual(result["answer_status"], "correct")
        self.assertEqual(result["verification_method"], "normalized_exact")
        self.assertTrue(result["explain_eligible"])
        self.assertEqual(result["verification_cost"]["total_tokens"], 300)
        self.assertAlmostEqual(result["verification_cost"]["calculated_cost_usd"], 0.000044)

    def test_missing_answer_is_not_eligible(self):
        result = verify_record({"final_answer": "4", "solve_solution": "unfinished"})
        self.assertEqual(result["answer_status"], "missing")
        self.assertEqual(result["verification_reason"], "no_extractable_answer")
        self.assertFalse(result["explain_eligible"])


if __name__ == "__main__":
    unittest.main()
