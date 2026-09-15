import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from anlp_project.solve_deepseek_flash import (
    estimated_max_cost,
    render_prompt,
    stream_solution,
    validate_and_select,
)


class SolveDeepSeekFlashTests(unittest.TestCase):
    def test_no_reference_prompt_and_selection(self):
        with tempfile.TemporaryDirectory() as directory_name:
            directory = Path(directory_name)
            input_path = directory / "pilot.json"
            prompt_path = directory / "solve_noref.txt"
            input_path.write_text(
                json.dumps(
                    {
                        "problems": [
                            {"question": "First question", "final_answer": "one"},
                            {"question": "Second question", "final_answer": "two"},
                        ]
                    }
                ),
                encoding="utf-8",
            )
            prompt_path.write_text("Solve: {{QUESTION}}", encoding="utf-8")

            selected, template = validate_and_select(input_path, prompt_path, [1, 0])

            self.assertEqual([problem["source_index"] for problem in selected], [1, 0])
            self.assertEqual(render_prompt(template, "x + 1 = 2"), "Solve: x + 1 = 2")

    def test_cost_ceiling_uses_output_price(self):
        self.assertAlmostEqual(estimated_max_cost(25, 8192), 0.036864)

    def test_streaming_collects_visible_and_reasoning_content(self):
        calls = []

        def create(**kwargs):
            calls.append(kwargs)
            return iter(
                [
                    SimpleNamespace(
                        choices=[SimpleNamespace(
                            delta=SimpleNamespace(content="First ", reasoning_content="Think "),
                            finish_reason=None,
                        )],
                        usage=None,
                    ),
                    SimpleNamespace(
                        choices=[SimpleNamespace(
                            delta=SimpleNamespace(content="answer", reasoning_content="step"),
                            finish_reason="stop",
                        )],
                        usage={"completion_tokens": 4},
                    ),
                ]
            )

        client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
        solution, reasoning, finish_reason, usage = stream_solution(client, "model", "prompt", 123)

        self.assertEqual(solution, "First answer")
        self.assertEqual(reasoning, "Think step")
        self.assertEqual(finish_reason, "stop")
        self.assertEqual(usage, {"completion_tokens": 4})
        self.assertTrue(calls[0]["stream"])
        self.assertEqual(calls[0]["extra_body"], {"reasoning_effort": "medium"})


if __name__ == "__main__":
    unittest.main()
