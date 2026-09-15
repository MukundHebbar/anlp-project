import json
import tempfile
import unittest
from pathlib import Path

from anlp_project.export_solve_report import completed_records, render_report


class ExportSolveReportTests(unittest.TestCase):
    def test_completed_records_are_sorted_and_rendered(self):
        with tempfile.TemporaryDirectory() as directory_name:
            directory = Path(directory_name)
            first = directory / "first.json"
            second = directory / "second.json"
            first.write_text(
                json.dumps(
                    {
                        "problems": [
                            {
                                "source_index": 5,
                                "question": "Question five",
                                "final_answer": "five",
                                "solve_solution": "Solution five",
                                "solve_status": "completed",
                            },
                            {"source_index": 6, "solve_status": "failed"},
                        ]
                    }
                ),
                encoding="utf-8",
            )
            second.write_text(
                json.dumps(
                    {
                        "problems": [
                            {
                                "source_index": 2,
                                "question": "Question two",
                                "final_answer": "two",
                                "solve_solution": "Solution two",
                                "solve_status": "completed",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            records = completed_records([first, second])
            report = render_report(records)

            self.assertEqual([record["source_index"] for record in records], [2, 5])
            self.assertIn("Completed problems: 2", report)
            self.assertLess(report.index("Question two"), report.index("Question five"))
            self.assertIn("Generated answer:\nSolution two", report)
            self.assertIn("Verified final answer:\ntwo", report)


if __name__ == "__main__":
    unittest.main()
