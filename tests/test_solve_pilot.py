import json
import tempfile
import unittest
from pathlib import Path

from anlp_project.solve_pilot import run_generation


class FakeMessage:
    def __init__(self, content):
        self.content = content
        self.reasoning_content = "internal reasoning"


class FakeChoice:
    def __init__(self, content):
        self.message = FakeMessage(content)
        self.finish_reason = "stop"


class FakeResponse:
    def __init__(self, content):
        self.choices = [FakeChoice(content)]
        self.usage = {"prompt_tokens": 10, "completion_tokens": 20}


class FakeCompletions:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        response = next(self.responses)
        if isinstance(response, Exception):
            raise response
        return FakeResponse(response)


class FakeClient:
    def __init__(self, responses):
        self.chat = type("Chat", (), {})()
        self.chat.completions = FakeCompletions(responses)


def write_inputs(directory: Path):
    input_path = directory / "pilot.json"
    prompt_path = directory / "solve.txt"
    input_path.write_text(
        json.dumps(
            {
                "dataset": "test-dataset",
                "problems": [
                    {
                        "question": "What is 2 + 2?",
                        "final_answer": "4",
                        "r1_solution_1": "Add the two numbers in the usual way.",
                        "r1_solution_2": "Add.",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    prompt_path.write_text(
        "Q={question}\nA={final_answer}\nR={reasoning_trace}",
        encoding="utf-8",
    )
    return input_path, prompt_path


class SolvePilotTests(unittest.TestCase):
    def test_prompt_and_output(self):
        with tempfile.TemporaryDirectory() as directory_name:
            directory = Path(directory_name)
            input_path, prompt_path = write_inputs(directory)
            output_path = directory / "solved.json"
            client = FakeClient(["The complete solution is 2 + 2 = 4."])

            run_generation(
                input_path,
                prompt_path,
                output_path,
                "test-model",
                client,
                sleep=lambda _: None,
            )

            call = client.chat.completions.calls[0]
            self.assertIn("Q=What is 2 + 2?", call["messages"][0]["content"])
            self.assertIn("A=4", call["messages"][0]["content"])
            self.assertIn("R=Add.", call["messages"][0]["content"])
            saved = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(saved["problems"][0]["solve_status"], "completed")
            self.assertEqual(
                saved["problems"][0]["solve_solution"],
                "The complete solution is 2 + 2 = 4.",
            )
            self.assertEqual(saved["problems"][0]["solve_reasoning"], "internal reasoning")
            self.assertEqual(saved["problems"][0]["solve_reference_field"], "r1_solution_2")
            self.assertNotIn("<think>", saved["problems"][0]["solve_solution"])
            self.assertEqual(saved["problems"][0]["final_answer"], "4")
            self.assertFalse(call["extra_body"]["chat_template_kwargs"]["enable_thinking"])
            self.assertEqual(call["temperature"], 0.7)
            self.assertEqual(call["top_p"], 0.8)
            self.assertEqual(call["extra_body"]["top_k"], 20)

    def test_thinking_tag_is_recorded_as_failure(self):
        with tempfile.TemporaryDirectory() as directory_name:
            directory = Path(directory_name)
            input_path, prompt_path = write_inputs(directory)
            output_path = directory / "solved.json"
            client = FakeClient(["<think>reasoning without a reliable boundary"])

            run_generation(
                input_path,
                prompt_path,
                output_path,
                "test-model",
                client,
                sleep=lambda _: None,
            )

            saved = json.loads(output_path.read_text(encoding="utf-8"))
            problem = saved["problems"][0]
            self.assertEqual(problem["solve_status"], "failed")
            self.assertIn("thinking tag", problem["solve_error"])
            self.assertNotIn("solve_solution", problem)

    def test_no_reference_prompt_and_thinking_mode(self):
        with tempfile.TemporaryDirectory() as directory_name:
            directory = Path(directory_name)
            input_path, _ = write_inputs(directory)
            prompt_path = directory / "solve_noref.txt"
            prompt_path.write_text(
                "Solve this carefully:\n{{QUESTION}}",
                encoding="utf-8",
            )
            output_path = directory / "solved.json"
            client = FakeClient(["The complete solution is 2 + 2 = 4."])

            run_generation(
                input_path,
                prompt_path,
                output_path,
                "test-model",
                client,
                thinking_mode=True,
                source_indices=[0],
                sleep=lambda _: None,
            )

            call = client.chat.completions.calls[0]
            self.assertIn("What is 2 + 2?", call["messages"][0]["content"])
            self.assertNotIn("R=", call["messages"][0]["content"])
            self.assertTrue(call["extra_body"]["chat_template_kwargs"]["enable_thinking"])
            self.assertEqual(call["temperature"], 1.0)
            self.assertEqual(call["top_p"], 0.95)

            saved = json.loads(output_path.read_text(encoding="utf-8"))
            problem = saved["problems"][0]
            self.assertEqual(problem["source_index"], 0)
            self.assertIsNone(problem["solve_reference_field"])
            self.assertEqual(problem["solve_reference_strategy"], "not_used")

    def test_completed_problem_is_skipped_on_rerun(self):
        with tempfile.TemporaryDirectory() as directory_name:
            directory = Path(directory_name)
            input_path, prompt_path = write_inputs(directory)
            output_path = directory / "solved.json"

            first_client = FakeClient(["The answer is 4."])
            run_generation(
                input_path,
                prompt_path,
                output_path,
                "test-model",
                first_client,
                sleep=lambda _: None,
            )

            second_client = FakeClient([])
            run_generation(
                input_path,
                prompt_path,
                output_path,
                "test-model",
                second_client,
                sleep=lambda _: None,
            )
            self.assertEqual(len(second_client.chat.completions.calls), 0)

    def test_transient_failure_is_retried(self):
        transient_error = type("APIConnectionError", (Exception,), {})("temporary")
        client = FakeClient([transient_error, transient_error, "Recovered solution"])

        with tempfile.TemporaryDirectory() as directory_name:
            directory = Path(directory_name)
            input_path, prompt_path = write_inputs(directory)
            output_path = directory / "solved.json"
            run_generation(
                input_path,
                prompt_path,
                output_path,
                "test-model",
                client,
                sleep=lambda _: None,
            )

            self.assertEqual(len(client.chat.completions.calls), 3)
            saved = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(saved["problems"][0]["solve_status"], "completed")


if __name__ == "__main__":
    unittest.main()
