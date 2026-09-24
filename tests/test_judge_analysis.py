import json
import tempfile
import unittest
from pathlib import Path

from anlp_project.judge_analysis import render_markdown, summarize_artifact


class JudgeAnalysisTests(unittest.TestCase):
    def test_summarizes_prepared_artifact_without_private_text(self):
        with tempfile.TemporaryDirectory() as directory_name:
            path = Path(directory_name) / "candidate.json"
            path.write_text(
                json.dumps(
                    {
                        "metadata": {"model": "test", "prompt_file": "candidate.md", "prompt_sha256": "abc"},
                        "items": [
                            {"status": "prepared", "target_label": "correct", "requested_error_type": "none", "requested_error_position": "none"},
                            {"status": "completed", "validation_status": "valid", "target_label": "incorrect", "requested_error_type": "sign_inequality", "requested_error_position": "middle", "prompt_tokens": 100, "completion_tokens": 20, "validation_errors": []},
                        ],
                    }
                ),
                encoding="utf-8",
            )
            summary = summarize_artifact(path)
            self.assertEqual(summary["item_count"], 2)
            self.assertEqual(summary["status_counts"]["prepared"], 1)
            self.assertEqual(summary["validation_counts"]["valid"], 1)
            report = render_markdown([summary])
            self.assertIn("candidate", report)
            self.assertNotIn("reference_solution", report)


if __name__ == "__main__":
    unittest.main()
