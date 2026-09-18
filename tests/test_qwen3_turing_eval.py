import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from anlp_project.qwen3_turing_eval import (
    build_explain_prompt,
    build_explain_v1_prompt,
    build_solve_prompt,
    build_solve_prompt_from_template,
    extract_final_answer,
    extract_student_task,
    load_explain_v1_records,
    load_records,
    load_witness_prompt,
    load_witness_records,
    build_witness_prompt,
    parse_witness_response,
    preflight_witness_prompts,
    load_student_explain_prompt,
    load_solve_prompt,
    normalize_answer,
    parse_args,
    student_explain_prompt_metadata,
    verify_final_answer,
)


class Qwen3TuringEvalTests(unittest.TestCase):
    def test_witness_loader_exposes_public_fields_only(self):
        with tempfile.TemporaryDirectory() as directory_name:
            path = Path(directory_name) / "witness.json"
            path.write_text(
                json.dumps({
                    "items": [{
                        "source_index": 8,
                        "output": {
                            "student_facing_task": {
                                "source_problem": "Original",
                                "relevant_context": ["Fact"],
                                "witness_request": "Give x.",
                                "response_instruction": "Verify.",
                            },
                            "reference_witness": {"object": "PRIVATE", "verification": "PRIVATE"},
                            "evaluation_rubric": {"required_conditions": ["PRIVATE"]},
                        },
                    }]
                }),
                encoding="utf-8",
            )
            record = load_witness_records(path)[0]
            self.assertEqual(set(record), {"source_index", "source_problem", "relevant_context", "witness_request", "response_instruction"})
            prompt = build_witness_prompt(record, "{source_problem}|{relevant_context}|{witness_request}|{response_instruction}")
            self.assertEqual(prompt, "Original|- Fact|Give x.|Verify.")
            self.assertNotIn("PRIVATE", prompt)

    def test_witness_prompt_loader_and_format_parser(self):
        template = load_witness_prompt()
        self.assertIn("{source_problem}", template)
        valid = parse_witness_response("Witness:\n{x = 1}\n\nVerification:\nIt satisfies the condition.")
        self.assertTrue(valid["format_valid"])
        self.assertEqual(valid["witness_text"], "{x = 1}")
        self.assertFalse(parse_witness_response("Verification: only")["format_valid"])
        self.assertFalse(parse_witness_response("Witness:\n\nVerification: text")["format_valid"])
        self.assertFalse(parse_witness_response("Witness: object\nVerification:")["format_valid"])

    def test_witness_preflight_checks_prompt_plus_completion_capacity(self):
        class FakeTokenizer:
            def apply_chat_template(self, messages, tokenize, add_generation_prompt):
                return [1, 2, 3]

        class FakeLLM:
            def get_tokenizer(self):
                return FakeTokenizer()

        record = {
            "source_index": 1,
            "source_problem": "P",
            "relevant_context": [],
            "witness_request": "W",
            "response_instruction": "R",
        }
        preflight_witness_prompts(FakeLLM(), [record], "{source_problem}{relevant_context}{witness_request}{response_instruction}", 4, 7)
        with self.assertRaises(ValueError):
            preflight_witness_prompts(FakeLLM(), [record], "{source_problem}{relevant_context}{witness_request}{response_instruction}", 5, 7)

    def test_load_explain_v1_filters_not_suitable_and_private_fields(self):
        with tempfile.TemporaryDirectory() as directory_name:
            path = Path(directory_name) / "input.json"
            path.write_text(
                json.dumps(
                    {
                        "items": [
                            {
                                "source_index": 2,
                                "output": {
                                    "student_facing_task": {
                                        "problem": "2+2",
                                        "established_context": ["Arithmetic applies."],
                                        "solution_skeleton": [
                                            {"id": "S1", "statement": "Write 2+2."},
                                            {"id": "S2", "statement": "Obtain 4."},
                                        ],
                                        "transition_to_explain": {
                                            "from": "S1",
                                            "to": "S2",
                                            "question": "Why?",
                                        },
                                    },
                                    "reference_explanation": "PRIVATE",
                                    "required_criteria": ["PRIVATE"],
                                },
                            },
                            {"source_index": 7, "output": "NOT_SUITABLE"},
                        ]
                    }
                ),
                encoding="utf-8",
            )
            records = load_explain_v1_records(path)
            self.assertEqual([item["source_index"] for item in records], [2])
            prompt = build_explain_v1_prompt(records[0])
            self.assertIn("<problem>\n2+2", prompt)
            self.assertIn("<established_context>\n- Arithmetic applies.", prompt)
            self.assertIn("<solution_step_1>\nWrite 2+2.", prompt)
            self.assertIn("<solution_step_2>\nObtain 4.", prompt)
            self.assertNotIn("PRIVATE", prompt)

    def test_student_prompt_loader_requires_all_placeholders_and_records_hash(self):
        with tempfile.TemporaryDirectory() as directory_name:
            path = Path(directory_name) / "student.md"
            path.write_text("{problem} {established_context}", encoding="utf-8")
            with self.assertRaises(ValueError):
                load_student_explain_prompt(path)
            path.write_text(
                "{problem}{established_context}{step_1}{step_2}{transition_question}",
                encoding="utf-8",
            )
            template = load_student_explain_prompt(path)
            metadata = student_explain_prompt_metadata(path, template)
            self.assertEqual(metadata["student_prompt_file"], str(path))
            self.assertEqual(len(metadata["student_prompt_sha256"]), 64)

    def test_attached_prompt_renders_all_public_fields(self):
        record = {
            "problem": "Solve x+1=2.",
            "established_context": ["x is real."],
            "solution_skeleton": [
                {"id": "S1", "statement": "Subtract 1 from both sides."},
                {"id": "S2", "statement": "Therefore x=1."},
            ],
            "transition_to_explain": {
                "from": "S1", "to": "S2", "question": "Why is this valid?"
            },
        }
        prompt = build_explain_v1_prompt(record, load_student_explain_prompt())
        for value in (
            "Solve x+1=2.",
            "x is real.",
            "Subtract 1 from both sides.",
            "Therefore x=1.",
            "Why is this valid?",
        ):
            self.assertIn(value, prompt)
        for private_name in ("reference_explanation", "required_criteria", "material_errors", "final_answer"):
            self.assertNotIn(private_name, prompt)

    def test_extract_student_task_hides_private_answer(self):
        response = """```text
<student_facing_task>
<question>Explain this step.</question>
</student_facing_task>
<private_reference_answer>secret</private_reference_answer>
```"""
        self.assertEqual(extract_student_task(response), "<question>Explain this step.</question>")
        with self.assertRaises(ValueError):
            extract_student_task(
                "<student_facing_task><private_reference_answer>secret</private_reference_answer></student_facing_task>"
            )

    def test_load_records_keeps_solve_records_and_filters_explain(self):
        with tempfile.TemporaryDirectory() as directory_name:
            path = Path(directory_name) / "input.json"
            path.write_text(
                json.dumps(
                    {
                        "problems": [
                            {
                                "source_index": 4,
                                "question": "Q",
                                "final_answer": "4",
                                "explain_response_kind": "task",
                                "explain_response": "<student_facing_task>Task</student_facing_task>",
                            },
                            {
                                "source_index": 5,
                                "question": "Q2",
                                "final_answer": "5",
                                "explain_response_kind": "not_suitable",
                                "explain_response": "NOT_SUITABLE",
                            },
                        ]
                    }
                ),
                encoding="utf-8",
            )
            records = load_records(path)
            self.assertEqual([record["source_index"] for record in records], [4, 5])
            self.assertEqual(records[0]["explain_task"], "Task")
            self.assertIsNone(records[1]["explain_task"])
            explain_records = load_records(path, explain_only=True)
            self.assertEqual([record["source_index"] for record in explain_records], [4])

    def test_prompt_builders_keep_task_boundaries(self):
        explain_prompt = build_explain_prompt("<student_facing_task>Task</student_facing_task>")
        solve_prompt = build_solve_prompt("x^2=4")
        self.assertIn("<task>\n<student_facing_task>Task", explain_prompt)
        self.assertIn("<problem>\nx^2=4", solve_prompt)
        self.assertIn("<final_answer>", solve_prompt)
        self.assertNotIn("private_reference", solve_prompt)

    def test_hardware_options_preserve_turing_defaults_and_accept_t4_values(self):
        with patch.object(sys, "argv", ["qwen3_turing_eval.py"]):
            defaults = parse_args()
        self.assertEqual(defaults.dtype, "auto")
        self.assertEqual(defaults.max_model_len, 16384)
        self.assertEqual(defaults.gpu_memory_utilization, 0.90)
        self.assertIsNone(defaults.max_num_seqs)
        with patch.object(sys, "argv", ["qwen3_turing_eval.py", "--dtype", "float16", "--max-model-len", "4096", "--gpu-memory-utilization", "0.85", "--max-num-seqs", "4"]):
            t4 = parse_args()
        self.assertEqual((t4.dtype, t4.max_model_len, t4.gpu_memory_utilization, t4.max_num_seqs), ("float16", 4096, 0.85, 4))

    def test_final_answer_tag_and_boxed_fallback(self):
        self.assertEqual(extract_final_answer("work\n<final_answer>\\dfrac{3}{2}</final_answer>"), ("\\dfrac{3}{2}", "tag"))
        self.assertEqual(extract_final_answer(r"work \(\boxed{4}\)"), ("4", "boxed_fallback"))
        self.assertEqual(extract_final_answer("no answer"), (None, "missing_final_answer"))

    def test_no_reference_solve_prompt_template(self):
        template = load_solve_prompt()
        prompt = build_solve_prompt_from_template("2+2?", template)
        self.assertIn("2+2?", prompt)
        self.assertNotIn("{{QUESTION}}", prompt)
        self.assertNotIn("verified final answer", prompt.lower())

    def test_deterministic_normalization_and_verification(self):
        self.assertEqual(normalize_answer(r"\dfrac{3}{2}"), "(3)/(2)")
        self.assertEqual(verify_final_answer(r"\dfrac{3}{2}", "3/2"), "correct")
        self.assertEqual(verify_final_answer(r"\infty", "infinity"), "correct")
        self.assertEqual(verify_final_answer(r"2^n - 1", "2^n-1"), "correct")
        self.assertEqual(verify_final_answer("Yes", "No"), "incorrect")

    def test_fake_vllm_shape_is_readable(self):
        completion = SimpleNamespace(text="<final_answer>4</final_answer>", finish_reason="stop", token_ids=[1, 2])
        request = SimpleNamespace(outputs=[completion], prompt_token_ids=[1, 2, 3])
        self.assertEqual(request.outputs[0].text, "<final_answer>4</final_answer>")


if __name__ == "__main__":
    unittest.main()
