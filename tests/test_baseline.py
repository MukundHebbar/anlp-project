import re
import unittest

from anlp_project import baseline as b


def row(task, **extra):
    base = {"uid": f"{task}-1", "task": task, "split": "train", "broad_topic": "Algebra",
            "difficulty": 5.0, "question": "What is 2+2?", "final_answer": "4"}
    return {**base, **extra}


class BaselineTests(unittest.TestCase):
    def test_prompts_render_without_placeholders_or_source_leak(self):
        rows = [
            row("solve"),
            row("judge", training={"input": "Problem...\nS1: ...\nDecide whether..."}),
            row("reconstruct", public_input={"final_answer": "4", "clues": ["A sum is taken.", "Two equal terms."]}),
        ]
        for request in b.build_requests(rows):
            self.assertNotRegex(request["prompt"], r"\{\{[A-Z_]+\}\}")
        recon = b.render_prompt(rows[2])
        self.assertIn("1. A sum is taken.\n2. Two equal terms.", recon)
        self.assertNotIn("What is 2+2?", recon)
        self.assertIn("Decision:", b.render_prompt(rows[1]))

    def test_pilot_selection_is_deterministic_and_train_only(self):
        rows = {t: [row(t, uid=f"{t}-{i}") for i in range(300)] for t in b.TASKS}
        first, second = b.select_pilot(rows, size=10), b.select_pilot(rows, size=10)
        self.assertEqual(first, second)
        self.assertEqual({len(v) for v in first.values()}, {10})
        rows["solve"][0]["split"] = "test"
        with self.assertRaises(ValueError):
            b.select_pilot(rows, size=10)

    def test_judge_scoring_uses_key_and_parser(self):
        judge = row("judge", private={"label": "incorrect", "first_error_step_id": "S3", "error_position": "middle"})
        s = b.score_response(judge, {"text": "Decision: **incorrect**\nFirst wrong step: S3\nExplanation: x",
                                     "finish_reason": "stop", "completion_tokens": 12})
        self.assertTrue(s["verdict_correct"] and s["step_correct"])
        s = b.score_response(judge, {"text": "Decision: incorrect\nFirst wrong step: S2", "finish_reason": "stop"})
        self.assertTrue(s["verdict_correct"])
        self.assertFalse(s["step_correct"])

    def test_solve_and_reconstruct_scoring(self):
        s = b.score_response(row("solve"), {"text": "so <final_answer>4</final_answer>", "finish_reason": "stop"})
        self.assertEqual(s["answer_status"], "correct")
        s = b.score_response(row("solve"), {"text": "<final_answer>3</final_answer>\n</think>\nagain <final_answer>4</final_answer>",
                                            "finish_reason": "stop"})
        self.assertEqual((s["answer_status"], s["extraction"]), ("correct", "last_of_multiple_tags"))
        s = b.score_response(row("solve"), {"text": "no tag", "finish_reason": "length"})
        self.assertEqual(s["answer_status"], "missing")
        self.assertTrue(s["hit_token_cap"])
        recon = row("reconstruct")
        ok = b.score_response(recon, {"text": '{"assumptions":[],"question":"Q?","justification":"J"}'})
        self.assertTrue(ok["parsed"])
        self.assertFalse(b.score_response(recon, {"text": "not json"})["parsed"])

    def test_lenient_extraction_recovers_broken_json_without_rewriting(self):
        # Unclosed assumptions array, invalid \' escape, stray ")}" ending: seen from Qwen3.5-4B.
        text = ('{"assumptions":["It\\\'s a guess.","question":"Find f(1) if f(x)=x+\\\\frac{1}{2}.",'
                '"justification":"Substituting gives 3/2.")}')
        value, method = b.extract_reconstruction(text)
        self.assertEqual(method, "lenient")
        self.assertEqual(value["question"], "Find f(1) if f(x)=x+\\frac{1}{2}.")
        self.assertEqual(value["justification"], "Substituting gives 3/2.")
        self.assertEqual(b.extract_reconstruction('{"assumptions":["only this"'), (None, None))


if __name__ == "__main__":
    unittest.main()
