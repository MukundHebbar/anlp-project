import json
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

from anlp_project.witness_eval_deepseek_flash import (
    load_records,
    parse_judge_response,
    render_prompt,
    run_generation,
)


def judge_output(overall="VALID"):
    value = {
        "well_definedness": "PASS",
        "constraint_satisfaction": "PASS",
        "required_phenomenon": "PASS",
        "verification_correct": "PASS",
        "overall_witness": overall,
        "brief_reason": "The explicit witness satisfies every rubric condition and the verification is correct.",
    }
    return value


class WitnessEvalDeepSeekFlashTests(unittest.TestCase):
    def write_inputs(self, root: Path):
        qwen = root / "qwen.json"
        witness = root / "witness.json"
        source = root / "source.json"
        prompt = root / "eval.txt"
        output = root / "results.json"
        report = root / "report.txt"
        qwen.write_text(
            json.dumps({"results": [
                {"source_index": 4, "status": "completed", "format_valid": True, "response": "Witness: x\nVerification: okay"},
                {"source_index": 9, "status": "completed", "format_valid": False, "response": "bad"},
            ]}), encoding="utf-8"
        )
        witness.write_text(json.dumps({"items": [{
            "source_index": 4,
            "output": {
                "student_facing_task": {
                    "source_problem": "Public source",
                    "relevant_context": ["Public fact"],
                    "witness_request": "Give a witness",
                    "response_instruction": "Verify it",
                },
                "reference_witness": {"object": "x=1", "verification": "Substitution works"},
                "evaluation_rubric": {
                    "object_type": "number",
                    "required_conditions": ["x is real"],
                    "required_phenomenon": "shows it",
                    "acceptable_variation": "equivalent values",
                    "material_errors": ["wrong x"],
                },
            },
        }]}), encoding="utf-8")
        source.write_text(json.dumps({"problems": [{
            "source_index": 4, "question": "Original question", "solve_solution": "Verified source solution"
        }]}), encoding="utf-8")
        prompt.write_text(
            "P={source_problem}\nS={verified_source_solution}\nC={relevant_context}\nW={witness_request}\n"
            "R={hidden_rubric}\nO={reference_witness}\nV={reference_verification}\nU={student_response}",
            encoding="utf-8",
        )
        return qwen, witness, source, prompt, output, report

    def args(self, paths):
        qwen, witness, source, prompt, output, report = paths
        return Namespace(
            qwen_input=qwen, witness_input=witness, source_input=source, prompt=prompt,
            output=output, report=report, model="test-model", max_tokens=123,
            timeout=10.0, concurrency=1, retry_failed=False,
        )

    def test_alignment_excludes_only_format_invalid_response(self):
        with tempfile.TemporaryDirectory() as name:
            paths = self.write_inputs(Path(name))
            records, excluded = load_records(*paths[:3])
            self.assertEqual([record["source_index"] for record in records], [4])
            self.assertEqual(excluded, [9])

    def test_render_includes_judge_fields_and_not_student_only_fields(self):
        with tempfile.TemporaryDirectory() as name:
            paths = self.write_inputs(Path(name))
            records, _ = load_records(*paths[:3])
            rendered = render_prompt(paths[3].read_text(encoding="utf-8"), records[0])
            for value in ("Original question", "Verified source solution", "Public fact", "Give a witness", "x=1", "Witness: x"):
                self.assertIn(value, rendered)
            self.assertIn("required_conditions", rendered)

    def test_parser_enforces_exact_schema_and_aggregation(self):
        parsed = parse_judge_response(json.dumps(judge_output()))
        self.assertEqual(parsed["overall_witness"], "VALID")
        invalid = judge_output(overall="INVALID")
        with self.assertRaises(ValueError):
            parse_judge_response(json.dumps(invalid))
        invalid = judge_output()
        invalid["brief_reason"] = "word " * 81
        with self.assertRaises(ValueError):
            parse_judge_response(json.dumps(invalid))
        invalid = judge_output()
        invalid["extra"] = True
        with self.assertRaises(ValueError):
            parse_judge_response(json.dumps(invalid))

    def test_generation_saves_reasoning_metrics_and_resumes(self):
        with tempfile.TemporaryDirectory() as name:
            paths = self.write_inputs(Path(name))
            args = self.args(paths)
            response = json.dumps(judge_output())
            with patch(
                "anlp_project.witness_eval_deepseek_flash.stream_solution",
                return_value=(response, "private reasoning", "stop", {"prompt_tokens": 7, "completion_tokens": 11, "total_tokens": 18},),
            ) as stream:
                result = run_generation(args, object())
            self.assertEqual(stream.call_count, 1)
            self.assertEqual(result["metadata"]["reasoning_effort"], "high")
            self.assertEqual(result["metadata"]["usage_summary"]["total_tokens"], 18)
            self.assertEqual(result["metadata"]["counts"]["overall_valid"], 1)
            self.assertIn("Overall VALID: 1/1", paths[5].read_text(encoding="utf-8"))
            with patch("anlp_project.witness_eval_deepseek_flash.stream_solution") as resumed:
                run_generation(args, object())
            self.assertEqual(resumed.call_count, 0)

    def test_malformed_judge_response_is_recorded_as_failure(self):
        with tempfile.TemporaryDirectory() as name:
            paths = self.write_inputs(Path(name))
            args = self.args(paths)
            with patch(
                "anlp_project.witness_eval_deepseek_flash.stream_solution",
                return_value=("not json", None, "stop", {}),
            ):
                result = run_generation(args, object())
            self.assertEqual(result["items"], [])
            self.assertEqual(result["failures"][0]["source_index"], 4)
            self.assertIn("raw JSON", result["failures"][0]["error"])


if __name__ == "__main__":
    unittest.main()
