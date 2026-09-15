import json
import tempfile
import unittest
from pathlib import Path

from anlp_project.explain_deepseek_flash import validate_v1_output
from scripts.legacy.repair_explain_output import repair_output


def valid_task() -> dict:
    return {
        "main_step_skeleton": [
            {"id": "S1", "statement": "First main step."},
            {"id": "S2", "statement": "Second main step."},
        ],
        "student_facing_task": {
            "problem": "Question",
            "established_context": ["Known context."],
            "solution_skeleton": [
                {"id": "S1", "statement": "First step."},
                {"id": "S2", "statement": "Second step."},
            ],
            "transition_to_explain": {"from": "S1", "to": "S2", "question": "Why?"},
            "student_instruction": "Explain the transition.",
        },
        "reference_explanation": "The relevant argument connects the two steps.",
        "required_criteria": ["Criterion 1", "Criterion 2", "Criterion 3"],
        "material_errors": ["A material error."],
        "generation_notes": "A local proof gap.",
    }


class RepairExplainOutputTests(unittest.TestCase):
    def test_recovers_fenced_json_without_api_request(self):
        with tempfile.TemporaryDirectory() as directory_name:
            directory = Path(directory_name)
            source = directory / "source.json"
            input_path = directory / "input.json"
            output = directory / "output.json"
            report = directory / "report.txt"
            source.write_text(
                json.dumps(
                    {
                        "problems": [
                            {"source_index": 1, "question": "Question", "solve_solution": "Solution", "final_answer": "4"},
                            {"source_index": 2, "question": "Question 2", "solve_solution": "Solution 2", "final_answer": "5"},
                        ]
                    }
                ),
                encoding="utf-8",
            )
            fenced = "```json\n" + json.dumps(valid_task()) + "\n```"
            input_path.write_text(
                json.dumps(
                    {
                        "metadata": {"prompt_version": "v2", "generation_details": {}},
                        "items": [],
                        "failures": [
                            {"source_index": 1, "raw_response": fenced, "error": "code fence"},
                            {"source_index": 2, "raw_response": "{bad", "error": "malformed"},
                        ],
                    }
                ),
                encoding="utf-8",
            )
            result = repair_output(source, input_path, output, report)
            self.assertEqual([item["source_index"] for item in result["items"]], [1])
            self.assertEqual([item["source_index"] for item in result["failures"]], [2])
            self.assertEqual(result["metadata"]["recovery"]["recovered_count"], 1)
            self.assertEqual(result["metadata"]["counts"]["valid_tasks"], 1)
            self.assertIn("Recovered locally without API request: 1", report.read_text(encoding="utf-8"))
            validate_v1_output(result["items"][0]["output"], {"question": "Question", "solve_solution": "Solution", "final_answer": "4"})


if __name__ == "__main__":
    unittest.main()
