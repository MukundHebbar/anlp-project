import json
import tempfile
import unittest
from pathlib import Path

from scripts.legacy.recover_explain_outputs import recover


class RecoverExplainOutputsTests(unittest.TestCase):
    def test_recovers_json_fence_and_records_missing_request(self):
        with tempfile.TemporaryDirectory() as directory_name:
            directory = Path(directory_name)
            source = directory / "input.json"
            raw = directory / "raw.json"
            output = directory / "output.json"
            valid = {
                "main_step_skeleton": [
                    {"id": "S1", "statement": "First."},
                    {"id": "S2", "statement": "Second."},
                ],
                "student_facing_task": {
                    "problem": "Question",
                    "established_context": [],
                    "solution_skeleton": [
                        {"id": "S1", "statement": "First."},
                        {"id": "S2", "statement": "Second."},
                    ],
                    "transition_to_explain": {"from": "S1", "to": "S2", "question": "Why?"},
                    "student_instruction": "Explain the transition.",
                },
                "reference_explanation": "Because.",
                "required_criteria": ["One.", "Two.", "Three."],
                "material_errors": ["Wrong."],
                "generation_notes": "Local.",
            }
            source.write_text(
                json.dumps(
                    {
                        "problems": [
                            {"source_index": 1, "question": "Question", "solve_solution": "Private", "final_answer": "4"},
                            {"source_index": 2, "question": "Question 2", "solve_solution": "Private", "final_answer": "5"},
                        ]
                    }
                ),
                encoding="utf-8",
            )
            raw.write_text(
                json.dumps(
                    {
                        "metadata": {},
                        "items": [],
                        "failures": [{"source_index": 1, "error": "fenced", "raw_response": "```json\n" + json.dumps(valid) + "\n```"}],
                    }
                ),
                encoding="utf-8",
            )
            result = recover(raw, source, output)
            self.assertEqual(len(result["items"]), 1)
            self.assertEqual(result["metadata"]["recovered_code_fence_count"], 1)
            self.assertEqual(result["failures"][0]["source_index"], 2)


if __name__ == "__main__":
    unittest.main()
