import json
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

from anlp_project.explain_deepseek_flash import (
    StreamInterruptedError,
    load_records,
    parse_and_validate,
    render_prompt,
    run_generation,
    validate_v1_output,
)


def valid_output() -> dict:
    return {
        "main_step_skeleton": [
            {"id": "S1", "statement": "First main step."},
            {"id": "S2", "statement": "Second main step."},
            {"id": "S3", "statement": "Third main step."},
        ],
        "student_facing_task": {
            "problem": "Question",
            "established_context": ["Known context."],
            "solution_skeleton": [
                {"id": "S1", "statement": "First step."},
                {"id": "S2", "statement": "Second step."},
            ],
            "transition_to_explain": {"from": "S1", "to": "S2", "question": "Why does S2 follow?"},
            "student_instruction": "Explain the transition.",
        },
        "reference_explanation": "The relevant argument connects the two steps.",
        "required_criteria": ["Criterion 1", "Criterion 2", "Criterion 3"],
        "material_errors": ["A material error."],
        "generation_notes": "A local proof gap.",
    }


class ExplainDeepSeekFlashTests(unittest.TestCase):
    def write_inputs(self, directory: Path) -> tuple[Path, Path, Path, Path]:
        input_path = directory / "solved.json"
        prompt_path = directory / "explain_v1.md"
        output_path = directory / "explain.json"
        report_path = directory / "explain-report.txt"
        input_path.write_text(
            json.dumps(
                {
                    "problems": [
                        {
                            "source_index": 3,
                            "question": "Completed question",
                            "final_answer": "4",
                            "solve_solution": "Completed solution",
                            "solve_status": "completed",
                        },
                        {
                            "source_index": 4,
                            "question": "Failed question",
                            "solve_status": "failed",
                        },
                    ]
                }
            ),
            encoding="utf-8",
        )
        prompt_path.write_text(
            "P=<problem>{problem}</problem> R=<reference_solution>{reference_solution}</reference_solution>",
            encoding="utf-8",
        )
        return input_path, prompt_path, output_path, report_path

    @staticmethod
    def args(input_path: Path, prompt_path: Path, output_path: Path, report_path: Path) -> Namespace:
        return Namespace(
            input=input_path,
            prompt=prompt_path,
            output=output_path,
            report=report_path,
            model="test-model",
            max_tokens=123,
            timeout=10.0,
            concurrency=1,
            retry_rejected=False,
        )

    def test_render_and_load_only_completed_records(self):
        with tempfile.TemporaryDirectory() as directory_name:
            input_path, prompt_path, _, _ = self.write_inputs(Path(directory_name))
            records, template = load_records(input_path, prompt_path)
            self.assertEqual([record["source_index"] for record in records], [3])
            self.assertEqual(
                render_prompt(template, "Question", "Solution"),
                "P=<problem>Question</problem> R=<reference_solution>Solution</reference_solution>",
            )

    def test_render_rejects_missing_v2_placeholders(self):
        with self.assertRaises(ValueError):
            render_prompt("{problem}", "Question", "Solution")

    def test_validate_accepts_task_and_not_suitable(self):
        source = {"question": "Question", "solve_solution": "Solution", "final_answer": "4"}
        self.assertEqual(validate_v1_output(valid_output(), source), valid_output())
        self.assertEqual(parse_and_validate("NOT_SUITABLE", source), "NOT_SUITABLE")
        fenced = "```json\n" + json.dumps(valid_output()) + "\n```"
        self.assertEqual(parse_and_validate(fenced, source), valid_output())

    def test_validate_rejects_malformed_and_invalid_outputs(self):
        source = {"question": "Question", "solve_solution": "Solution", "final_answer": "4"}
        with self.assertRaises(ValueError):
            parse_and_validate("```json\n{}\n```", source)
        with self.assertRaises(ValueError):
            parse_and_validate("{bad", source)

        cases = []
        value = valid_output()
        value["student_facing_task"]["solution_skeleton"].append({"id": "S3", "statement": "Third."})
        cases.append(value)
        value = valid_output()
        value["student_facing_task"]["solution_skeleton"][1]["id"] = "S3"
        cases.append(value)
        value = valid_output()
        value["required_criteria"] = ["Only one"]
        cases.append(value)
        value = valid_output()
        value["student_facing_task"]["established_context"] = ["Solution"]
        cases.append(value)
        for case in cases:
            with self.subTest(case=case):
                with self.assertRaises(ValueError):
                    validate_v1_output(case, source)

    def test_generation_persists_v1_items_and_resumes(self):
        with tempfile.TemporaryDirectory() as directory_name:
            paths = self.write_inputs(Path(directory_name))
            args = self.args(*paths)
            with patch("anlp_project.explain_deepseek_flash.stream_solution", return_value=(json.dumps(valid_output()), None, "stop", {"completion_tokens": 1})) as stream:
                run_generation(args, client=object())
            saved = json.loads(args.output.read_text(encoding="utf-8"))
            self.assertEqual([item["source_index"] for item in saved["items"]], [3])
            self.assertEqual(saved["items"][0]["output"]["student_facing_task"]["problem"], "Question")
            self.assertEqual(stream.call_count, 1)
            self.assertIn("Valid EXPLAIN tasks: 1", args.report.read_text(encoding="utf-8"))

            with patch("anlp_project.explain_deepseek_flash.stream_solution") as stream:
                run_generation(args, client=object())
            self.assertEqual(stream.call_count, 0)

    def test_not_suitable_and_stream_failure_are_recorded(self):
        with tempfile.TemporaryDirectory() as directory_name:
            paths = self.write_inputs(Path(directory_name))
            args = self.args(*paths)
            with patch("anlp_project.explain_deepseek_flash.stream_solution", return_value=("NOT_SUITABLE", None, "stop", {})):
                run_generation(args, client=object())
            saved = json.loads(args.output.read_text(encoding="utf-8"))
            self.assertEqual(saved["items"][0]["output"], "NOT_SUITABLE")

            args.output.unlink()

            def interrupted(*_args):
                cause = RuntimeError("network")
                error = StreamInterruptedError(cause, "partial task", "partial reasoning")
                raise error from cause

            with patch("anlp_project.explain_deepseek_flash.stream_solution", side_effect=interrupted):
                run_generation(args, client=object())
            saved = json.loads(args.output.read_text(encoding="utf-8"))
            self.assertEqual(saved["items"], [])
            self.assertIn("network", saved["failures"][0]["error"])

    def test_retry_rejected_adds_format_instructions(self):
        with tempfile.TemporaryDirectory() as directory_name:
            paths = self.write_inputs(Path(directory_name))
            args = self.args(*paths)
            args.retry_rejected = True
            args.output.write_text(
                json.dumps({"metadata": {}, "items": [], "failures": [{"source_index": 3, "error": "bad format"}]}),
                encoding="utf-8",
            )
            with patch("anlp_project.explain_deepseek_flash.stream_solution", return_value=(json.dumps(valid_output()), None, "stop", {})) as stream:
                run_generation(args, client=object())
            prompt = stream.call_args.args[2]
            self.assertIn("FORMAT RETRY", prompt)
            self.assertIn("no Markdown", prompt)

    def test_v2_records_version_hash_timing_and_counts(self):
        with tempfile.TemporaryDirectory() as directory_name:
            input_path, prompt_path, output_path, report_path = self.write_inputs(Path(directory_name))
            args = self.args(input_path, prompt_path, output_path, report_path)
            args.version = "v2"
            with patch("anlp_project.explain_deepseek_flash.stream_solution", return_value=(json.dumps(valid_output()), None, "stop", {"prompt_tokens": 10, "completion_tokens": 20})):
                run_generation(args, client=object())
            saved = json.loads(output_path.read_text(encoding="utf-8"))
            metadata = saved["metadata"]
            self.assertEqual(metadata["schema"], "explain_v2_batch")
            self.assertEqual(metadata["prompt_version"], "v2")
            self.assertRegex(metadata["prompt_sha256"], r"^[0-9a-f]{64}$")
            self.assertGreaterEqual(metadata["elapsed_seconds"], 0)
            self.assertEqual(metadata["counts"]["valid_tasks"], 1)
            self.assertEqual(metadata["usage_summary"]["total_tokens"], 30)
            report = report_path.read_text(encoding="utf-8")
            self.assertIn("EXPLAIN-v2 DeepSeek generation", report)
            self.assertIn("Successful task rate: 1/1", report)
            self.assertIn("Elapsed seconds:", report)


if __name__ == "__main__":
    unittest.main()
