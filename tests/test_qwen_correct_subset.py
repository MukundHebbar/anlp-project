import json
import tempfile
import unittest
from pathlib import Path

from anlp_project.build_qwen_correct_subset import build_subset


class QwenCorrectSubsetTests(unittest.TestCase):
    def test_builds_exact_public_subset_and_smoke_record(self):
        with tempfile.TemporaryDirectory() as directory_name:
            directory = Path(directory_name)
            records = []
            for index in range(114):
                records.append(
                    {
                        "source_index": index,
                        "source_id": f"source-{index}",
                        "question": f"question {index}",
                        "final_answer": str(index),
                        "topic": "Algebra",
                        "difficulty": 5.5,
                        "answer_status": "correct" if index < 113 else "unverified",
                        "solve_solution": "private trace",
                    }
                )
            source = directory / "verified.json"
            output = directory / "subset.json"
            smoke = directory / "smoke.json"
            source.write_text(json.dumps({"dataset": "test", "problems": records}), encoding="utf-8")
            build_subset(source, output, smoke)
            subset = json.loads(output.read_text(encoding="utf-8"))
            smoke_data = json.loads(smoke.read_text(encoding="utf-8"))
            self.assertEqual(len(subset["problems"]), 113)
            self.assertEqual(len(smoke_data["problems"]), 1)
            self.assertEqual(smoke_data["problems"][0]["source_index"], 0)
            self.assertNotIn("solve_solution", subset["problems"][0])
            self.assertNotIn("answer_status", subset["problems"][0])


if __name__ == "__main__":
    unittest.main()
