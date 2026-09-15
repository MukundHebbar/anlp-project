import json
import tempfile
import unittest
from pathlib import Path

from anlp_project.build_explain_input import build_input


class BuildExplainInputTests(unittest.TestCase):
    def test_selects_exact_correct_completed_records(self):
        with tempfile.TemporaryDirectory() as directory_name:
            directory = Path(directory_name)
            source = directory / "source.json"
            output = directory / "output.json"
            records = []
            for index in range(113):
                records.append(
                    {
                        "source_index": index,
                        "source_id": f"source-{index}",
                        "question": f"Question {index}",
                        "answer_status": "correct",
                        "solve_status": "completed",
                        "solve_solution": f"Solution {index}",
                    }
                )
            records.extend(
                [
                    {"source_index": 200, "source_id": "wrong", "answer_status": "incorrect", "solve_status": "completed", "solve_solution": "x"},
                    {"source_index": 201, "source_id": "failed", "answer_status": "correct", "solve_status": "failed", "solve_solution": ""},
                ]
            )
            source.write_text(json.dumps({"dataset": "test", "problems": records}), encoding="utf-8")
            result = build_input(source, output)
            self.assertEqual(result["sample_size"], 113)
            self.assertEqual(len(result["problems"]), 113)
            self.assertEqual(result["problems"][0]["source_id"], "source-0")
            self.assertTrue(all(record["solve_solution"] for record in result["problems"]))

    def test_supports_versioned_prompt_metadata(self):
        with tempfile.TemporaryDirectory() as directory_name:
            directory = Path(directory_name)
            source = directory / "source.json"
            output = directory / "output.json"
            prompt = directory / "explain_v2_generator_prompt.md"
            prompt.write_text("{problem} {reference_solution}", encoding="utf-8")
            records = [
                {
                    "source_index": index,
                    "source_id": f"source-{index}",
                    "question": f"Question {index}",
                    "answer_status": "correct",
                    "solve_status": "completed",
                    "solve_solution": f"Solution {index}",
                }
                for index in range(113)
            ]
            source.write_text(json.dumps({"dataset": "test", "problems": records}), encoding="utf-8")
            result = build_input(source, output, prompt, "v2")
            self.assertEqual(result["metadata"]["prompt_version"], "v2")
            self.assertEqual(result["metadata"]["prompt_file"], str(prompt))
            self.assertEqual(result["metadata"]["purpose"], "deepseek_v4_flash_explain_v2_generation")


if __name__ == "__main__":
    unittest.main()
