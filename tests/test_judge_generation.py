import json
import tempfile
import unittest
from pathlib import Path

from anlp_project.judge_generation import (
    build_generation_items,
    initialize_output,
    load_generator_prompt,
    render_generator_prompt,
)
from anlp_project.judge_validation import observed_error_position, parse_json_response, validate_generated_output


class JudgeGenerationTests(unittest.TestCase):
    def setUp(self):
        self.record = {
            "source_id": "source-1",
            "source_index": 1,
            "question": "Solve x + 1 = 2.",
            "final_answer": "1",
            "topic": "Mathematics -> Algebra -> Linear Equations",
            "broad_topic": "Algebra",
            "difficulty": 5,
            "reference_solution": "Subtract 1 from both sides to obtain x = 1.",
        }

    def test_builds_balanced_correct_and_incorrect_items(self):
        items = build_generation_items([self.record])
        self.assertEqual([item["target_label"] for item in items], ["correct", "incorrect"])
        self.assertEqual(items[0]["requested_error_type"], "none")
        self.assertIn(items[1]["requested_error_type"], {"arithmetic_algebra", "sign_inequality", "invalid_theorem_condition", "unjustified_implication", "domain_restriction", "missing_case"})

    def test_prompt_rendering_replaces_all_inputs(self):
        template = "{problem}|{reference_solution}|{target_label}|{error_type}|{error_position}"
        rendered = render_generator_prompt(
            template,
            self.record,
            target_label="incorrect",
            error_type="sign_inequality",
            error_position="middle",
        )
        self.assertEqual(
            rendered,
            "Solve x + 1 = 2.|Subtract 1 from both sides to obtain x = 1.|incorrect|sign_inequality|middle",
        )

    def test_validation_accepts_correct_output(self):
        output = {
            "public": {
                "problem": self.record["question"],
                "proposed_solution": [
                    {"step_id": "S1", "text": "x + 1 = 2."},
                    {"step_id": "S2", "text": "Subtracting 1 gives x = 1."},
                ],
                "instruction": "Judge the solution.",
            },
            "private": {
                "label": "correct",
                "first_error_step_id": None,
                "first_error_explanation": None,
                "error_type": None,
                "error_position": None,
                "teacher_target_response": "Decision: correct\nFirst wrong step: none\nExplanation: The algebra is valid.",
            },
        }
        self.assertEqual(
            validate_generated_output(
                output,
                target_label="correct",
                expected_problem=self.record["question"],
                reference_solution=self.record["reference_solution"],
            ),
            [],
        )

    def test_validation_rejects_private_leak(self):
        output = {
            "public": {
                "problem": self.record["question"],
                "proposed_solution": [
                    {"step_id": "S1", "text": "The answer is 1."},
                    {"step_id": "S2", "text": self.record["reference_solution"]},
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
        errors = validate_generated_output(
            output,
            target_label="correct",
            expected_problem=self.record["question"],
            reference_solution=self.record["reference_solution"],
        )
        self.assertIn("reference solution leaked into public output", errors)

    def test_validation_rejects_private_fields_added_to_public(self):
        output = {
            "public": {
                "problem": self.record["question"],
                "proposed_solution": [
                    {"step_id": "S1", "text": "x + 1 = 2."},
                    {"step_id": "S2", "text": "x = 1."},
                ],
                "instruction": "Judge the solution.",
                "label": "correct",
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
        errors = validate_generated_output(output, target_label="correct")
        self.assertIn("public object has unexpected or missing fields", errors)

    def test_json_parser_accepts_code_fence(self):
        value = parse_json_response("```json\n{" + '"ok": true' + "}\n```")
        self.assertEqual(value, {"ok": True})

    def test_requested_error_position_uses_step_location(self):
        self.assertEqual(observed_error_position("S2", 3), "middle")
        self.assertEqual(observed_error_position("S4", 4), "late")
        output = {
            "public": {
                "problem": self.record["question"],
                "proposed_solution": [
                    {"step_id": "S1", "text": "Write the original equation."},
                    {"step_id": "S2", "text": "Subtract 2 from both sides."},
                    {"step_id": "S3", "text": "Conclude x = 1."},
                ],
                "instruction": "Judge the solution.",
            },
            "private": {
                "label": "incorrect",
                "first_error_step_id": "S2",
                "first_error_explanation": "Subtracting 2 is invalid here.",
                "error_type": "arithmetic_algebra",
                "error_position": "early",
                "teacher_target_response": "Decision: incorrect\nFirst wrong step: S2\nExplanation: Subtract 1.",
            },
        }
        errors = validate_generated_output(output, target_label="incorrect")
        self.assertTrue(any("does not match step S2" in error for error in errors))

    def test_algorithm_source_avoids_forced_bijection_error(self):
        record = {**self.record, "topic": "Mathematics -> Discrete Mathematics -> Algorithms", "broad_topic": "Discrete Mathematics"}
        records = [{**record, "source_id": f"source-{index}", "source_index": index} for index in range(15)]
        items = build_generation_items(records)
        self.assertEqual(items[-1]["requested_error_type"], "arithmetic_algebra")

    def test_resume_rejects_changed_error_assignment(self):
        with tempfile.TemporaryDirectory() as directory_name:
            path = Path(directory_name) / "output.json"
            items = build_generation_items([self.record])
            metadata = {"prompt_sha256": "old", "model": "Qwen/Qwen3-8B"}
            path.write_text(json.dumps({"metadata": metadata, "items": items}), encoding="utf-8")
            changed = [dict(item) for item in items]
            changed[1]["requested_error_type"] = "missing_case"
            with self.assertRaisesRegex(ValueError, "different sources or label/error assignments"):
                initialize_output(path, changed, metadata)


if __name__ == "__main__":
    unittest.main()
