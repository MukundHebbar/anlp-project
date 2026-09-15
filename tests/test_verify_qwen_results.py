import json
import tempfile
import unittest
from pathlib import Path

from anlp_project.verify_qwen_results import render_report, verify_qwen_results


class VerifyQwenResultsTests(unittest.TestCase):
    def test_local_verification_preserves_failures_and_details(self):
        with tempfile.TemporaryDirectory() as directory_name:
            directory = Path(directory_name)
            raw = directory / "raw.json"
            verified = directory / "verified.json"
            raw.write_text(
                json.dumps(
                    {
                        "metadata": {"job_id": "123", "gpu_name": "L40S"},
                        "results": [
                            {
                                "source_index": 1,
                                "source_id": "one",
                                "question": "2+2?",
                                "final_answer": "4",
                                "topic": "Algebra",
                                "difficulty": 5.5,
                                "status": "completed",
                                "response": "<final_answer>4</final_answer>",
                            },
                            {
                                "source_index": 2,
                                "source_id": "two",
                                "question": "?",
                                "final_answer": "Yes",
                                "topic": "Calculus",
                                "difficulty": 7.0,
                                "status": "failed",
                                "error": "timeout",
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )
            output = verify_qwen_results(raw, verified)
            self.assertEqual(output["metadata"]["status_counts"], {"correct": 1, "missing": 1})
            self.assertEqual(output["metadata"]["raw_metadata"]["job_id"], "123")
            self.assertEqual(output["results"][0]["verification_method"], "normalized_exact")
            self.assertFalse(output["results"][1]["explain_eligible"])
            report = render_report(output)
            self.assertIn("Strict accuracy: 0.5000", report)
            self.assertIn("job_id", json.dumps(output["metadata"]))


if __name__ == "__main__":
    unittest.main()
