import unittest

from anlp_project.solution_verification import (
    compare_answer_detailed,
    compare_answers,
    extract_final_answer,
    normalize_answer,
    split_reasoning_response,
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

    def test_sentence_that_breaks_sympy_is_unverified_not_a_crash(self):
        # Qwen3.8-27B test answer; sympy raised IndexError while parsing it.
        answer = "Yes, the prime number 2 can be expressed as the sum of two sixth powers of integers (e.g., $1^6 + 1^6 = 2$)."
        self.assertIn(compare_answers("2", answer), ("unverified", "incorrect", "correct"))

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

    def test_reasoning_response_split_supports_qwen_markers(self):
        paired = split_reasoning_response(
            "<think><final_answer>wrong</final_answer> check work</think>\n"
            "Full derivation. <final_answer>4</final_answer>"
        )
        self.assertEqual(paired["reasoning_parse_status"], "paired")
        self.assertIn("wrong", paired["reasoning_text"])
        self.assertNotIn("wrong", paired["solution_text"])
        self.assertIn("<final_answer>4</final_answer>", paired["solution_text"])

        implicit = split_reasoning_response("thinking\n</think>\nsolution")
        self.assertEqual(implicit["reasoning_parse_status"], "implicit_closed")
        self.assertEqual(implicit["solution_text"], "solution")

        unclosed = split_reasoning_response("<thinking>unfinished reasoning")
        self.assertEqual(unclosed["reasoning_parse_status"], "unclosed")
        self.assertEqual(unclosed["solution_text"], "")


if __name__ == "__main__":
    unittest.main()


class CheckerV3Tests(unittest.TestCase):
    """Cases from the 2026-10-07 audit of 7,465 (key, answer) pairs: recovered forms and the false positives
    each guard exists for."""

    def test_recovered_equivalent_forms(self):
        for key, answer in [
            ("2^k", r"n = 2^k \text{ for } k \ge 1"), (r"\infty", "+\\infty"), (r"\infty", "Infinite"),
            ("Yes", "True"), ("No", "False"), (r"\ln 2", r"\ln(2)"), (r"\ln 3", "ln 3"), ("(2, 2)", "(p, q) = (2, 2)"),
            ("(0, 0, 0)", "x=0, y=0, z=0"), (r"e^{\frac{9}{2}}", "e^{4.5}"), ("3.141592653", "3.14159265"),
            (r"2|\cos 2|", r"-2\cos(2)"), (r"\mathbb{R}", r"(-\infty, \infty)"), (r"m \bmod p", r"m \pmod p"),
            (r"n \geq 2", r"n \geqslant 2"), (r"e^{\frac{1}{3}}", r"\sqrt[3]{e}"), ("1{,}008{,}016", "1008016"),
        ]:
            self.assertEqual(compare_answers(key, answer), "correct", (key, answer))

    def test_audit_false_positives_stay_rejected(self):
        for key, answer in [
            ("88329", "88327"), ("501500", "501501"),            # DeepMath math_equal's 1e-4 tolerance
            (r"10^{101} + 1", r"100 \times 10^{99}"),            # exact numbers differ by 1
            (r"\infty", "1"), (r"-\infty", "+\\infty"),         # oo - 1 == oo
            ("3", r"a \neq 3"), ("1", "True"), ("0", "False"),  # "!=" split; Python True == 1
            ("2", "n = 0, 2"), ("2", "2, 2"),                    # several values
            ("(2)", r"(4, 2+2\sqrt{-5})"),                       # a tuple for a single-value key
            ("0", "It does not converge to 0"), ("0", "Does not converge to 0"),  # prose
            ("3", r"3 \text{ or } 5"),                           # hedge
            (r"2^{\aleph_0}", r"2^{2^{\aleph_0}}"),              # math-verify on cardinals
        ]:
            self.assertNotEqual(compare_answers(key, answer), "correct", (key, answer))

    def test_checks_from_threads_use_the_process_pool(self):
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(4) as pool:
            out = list(pool.map(lambda pair: compare_answers(*pair), [("2^k", "n = 2^k"), ("4", "5")] * 4))
        self.assertEqual(out, ["correct", "incorrect"] * 4)
