import json
import tempfile
import unittest
from pathlib import Path

from anlp_project.judge_dataset import parse_student_response, score_structural_response
from anlp_project.judge_dataset import export_public_dataset


class JudgeDatasetTests(unittest.TestCase):
    def setUp(self):
        self.correct = {
            "public": {
                "problem": "Solve x + 1 = 2.",
                "proposed_solution": [
                    {"step_id": "S1", "text": "x + 1 = 2."},
                    {"step_id": "S2", "text": "Subtract 1: x = 1."},
                ],
                "instruction": "Judge the solution.",
            },
            "private": {
                "label": "correct",
                "first_error_step_id": None,
                "first_error_explanation": None,
                "error_type": None,
                "error_position": None,
                "teacher_target_response": "Decision: correct\nFirst wrong step: none\nExplanation: valid.",
            },
        }

    def test_parses_fixed_student_response(self):
        parsed, errors = parse_student_response(
            "Decision: incorrect\nFirst wrong step: S2\nExplanation: The sign changes incorrectly."
        )
        self.assertEqual(errors, [])
        self.assertEqual(parsed["decision"], "incorrect")
        self.assertEqual(parsed["first_error_step_id"], "S2")

    def test_rejects_unexpected_student_fields(self):
        parsed, errors = parse_student_response("I think it is correct.")
        self.assertIsNone(parsed)
        self.assertIn("missing Decision field", errors)

    def test_structural_score_requires_correct_first_step(self):
        private = {"label": "incorrect", "first_error_step_id": "S2"}
        result = score_structural_response(
            "Decision: incorrect\nFirst wrong step: S1\nExplanation: There is an error.",
            private,
        )
        self.assertTrue(result["decision_correct"])
        self.assertFalse(result["first_error_correct"])
        self.assertFalse(result["strict_structural_correct"])

    def test_public_export_excludes_private_fields(self):
        with tempfile.TemporaryDirectory() as directory_name:
            directory = Path(directory_name)
            private_input = directory / "input.json"
            public_output = directory / "public.json"
            audit_output = directory / "audit.json"
            item = {
                "item_id": "source-1::correct",
                "source_id": "source-1",
                "source_index": 1,
                "question": "Solve x + 1 = 2.",
                "topic": "Algebra",
                "difficulty": 5,
                "reference_solution": "Subtract 1 from both sides.",
                "status": "completed",
                "validation_status": "valid",
                "validation_errors": [],
                "parsed_output": self.correct,
            }
            private_input.write_text(json.dumps({"metadata": {}, "items": [item]}), encoding="utf-8")
            output = export_public_dataset(
                private_input,
                public_output,
                audit_output,
                split="development",
                require_one_per_source=True,
            )
            serialized = json.dumps(output)
            self.assertEqual(output["item_count"], 1)
            self.assertNotIn("reference_solution", serialized)
            self.assertNotIn('"label"', serialized)
            self.assertEqual(json.loads(public_output.read_text(encoding="utf-8"))["item_count"], 1)


if __name__ == "__main__":
    unittest.main()
