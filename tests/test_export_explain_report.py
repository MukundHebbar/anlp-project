import json
import tempfile
import unittest
from pathlib import Path

from anlp_project.export_explain_report import completed_records, render_report


class ExportExplainReportTests(unittest.TestCase):
    def test_completed_records_render_reference_and_response(self):
        with tempfile.TemporaryDirectory() as directory_name:
            input_path = Path(directory_name) / "explain.json"
            input_path.write_text(
                json.dumps(
                    {
                        "problems": [
                            {
                                "source_index": 2,
                                "question": "Question two",
                                "solve_solution": "Reference solution two",
                                "explain_response": "NOT_SUITABLE",
                                "explain_response_kind": "not_suitable",
                                "explain_status": "completed",
                                "explain_model": "test-model",
                            },
                            {"source_index": 3, "explain_status": "failed"},
                        ]
                    }
                ),
                encoding="utf-8",
            )

            report = render_report(completed_records(input_path))

            self.assertIn("Completed problems: 1", report)
            self.assertIn("NOT_SUITABLE responses: 1", report)
            self.assertIn("Prior DeepSeek reference solution:\nReference solution two", report)
            self.assertIn("Generated EXPLAIN response:\nNOT_SUITABLE", report)


if __name__ == "__main__":
    unittest.main()
