import json
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

from anlp_project.witness_deepseek_flash import (
    parse_and_validate,
    run_generation,
    validate_output,
)


def valid_output() -> dict:
    return {
        "transformation_type": "equality_case",
        "load_bearing_feature": "The bound in the source solution.",
        "connection_to_source": "The bound controls attainability.",
        "student_facing_task": {
            "source_problem": "Original problem.",
            "relevant_context": ["Established fact."],
            "witness_request": "Give one concrete witness and verify it.",
            "response_instruction": "Give a witness and verify each condition.",
        },
        "reference_witness": {
            "object": "x = 2",
            "verification": "Substitution gives the required equality.",
        },
        "evaluation_rubric": {
            "object_type": "An integer.",
            "required_conditions": ["It is an integer.", "It attains the bound."],
            "required_phenomenon": "The bound is attained.",
            "acceptable_variation": "Any equivalent witness is acceptable.",
            "material_errors": ["The proposed object does not attain the bound."],
        },
        "quality_checks": {
            "single_primary_change": True,
            "problem_anchored": True,
            "reference_verified": True,
            "not_trivial_copying": True,
            "verification_shorter_than_full_solution": True,
        },
    }


class WitnessDeepSeekFlashTests(unittest.TestCase):
    def test_schema_accepts_json_and_not_suitable(self):
        value = valid_output()
        self.assertEqual(validate_output(value), value)
        self.assertEqual(parse_and_validate("NOT_SUITABLE"), ("NOT_SUITABLE", "raw_json"))
        fenced = "```json\n" + json.dumps(value) + "\n```"
        self.assertEqual(parse_and_validate(fenced)[0], value)

    def test_schema_rejects_extra_or_missing_fields(self):
        value = valid_output()
        value["unexpected"] = True
        with self.assertRaises(ValueError):
            validate_output(value)
        value = valid_output()
        del value["quality_checks"]["problem_anchored"]
        with self.assertRaises(ValueError):
            validate_output(value)

    def test_generation_records_usage_and_elapsed_time(self):
        with tempfile.TemporaryDirectory() as directory_name:
            directory = Path(directory_name)
            input_path = directory / "input.json"
            prompt_path = directory / "prompt.txt"
            output_path = directory / "results.json"
            report_path = directory / "report.txt"
            input_path.write_text(
                json.dumps(
                    {
                        "problems": [
                            {
                                "source_index": 4,
                                "answer_status": "correct",
                                "solve_status": "completed",
                                "question": "Question",
                                "solve_solution": "Verified solution",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            prompt_path.write_text("P={problem}\nS={verified_solution}", encoding="utf-8")
            args = Namespace(
                input=input_path,
                prompt=prompt_path,
                output=output_path,
                report=report_path,
                model="test-model",
                max_tokens=100,
                timeout=10.0,
                concurrency=1,
                retry_failed=False,
            )
            with patch(
                "anlp_project.witness_deepseek_flash.stream_solution",
                return_value=(json.dumps(valid_output()), "private reasoning", "stop", {"prompt_tokens": 7, "completion_tokens": 11, "total_tokens": 18},),
            ):
                result = run_generation(args, object())
            self.assertEqual(result["metadata"]["reasoning_effort"], "high")
            self.assertEqual(result["metadata"]["usage_summary"]["total_tokens"], 18)
            self.assertGreaterEqual(result["metadata"]["elapsed_seconds"], 0)
            detail = result["metadata"]["generation_details"]["4"]
            self.assertEqual(detail["request_elapsed_seconds"] >= 0, True)
            self.assertIn("Elapsed seconds:", report_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
