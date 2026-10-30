import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("eval_matrix_instruct", ROOT / "scripts/turing/eval_matrix.py")
evaluation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(evaluation)


class InstructEvaluationTests(unittest.TestCase):
    def test_native_instruct_and_qwen_preserve_sampling_and_continuation(self):
        for mode, model_format in (("instruct", "mistral"), ("nonthinking", "auto")):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                calls = {}

                class FakeLLM:
                    def __init__(self, **kwargs):
                        calls["loader"] = kwargs

                    def get_tokenizer(self):
                        return SimpleNamespace(decode=lambda ids, **_: str(ids))

                    def chat(self, messages, sampling, **kwargs):
                        calls["chat"] = (messages, sampling, kwargs)
                        outputs = [SimpleNamespace(token_ids=[i], finish_reason="stop") for i in (1, 2, 3)]
                        outputs.append(SimpleNamespace(token_ids=[7, 8], finish_reason="length"))
                        return [SimpleNamespace(prompt_token_ids=[101, 102], outputs=outputs)]

                    def generate(self, prompts, sampling, **kwargs):
                        calls["continuation"] = (prompts, sampling)
                        return [SimpleNamespace(outputs=[SimpleNamespace(token_ids=[9], finish_reason="stop")])]

                modules = {name: ModuleType(name) for name in (
                    "huggingface_hub", "vllm", "vllm.inputs", "vllm.lora", "vllm.lora.request")}
                modules["huggingface_hub"].snapshot_download = lambda *_, **__: self.fail("Pinned local model should be used")
                modules["vllm"].LLM = FakeLLM
                modules["vllm"].SamplingParams = lambda **kwargs: kwargs
                modules["vllm.inputs"].TokensPrompt = lambda **kwargs: kwargs
                modules["vllm.lora.request"].LoRARequest = lambda *_: None
                args = SimpleNamespace(split="test", limit=0, model="model-id", model_path="/pinned/model",
                                       model_format=model_format, chat_mode=mode, max_cap=32768, first_cap=16384,
                                       adapter="", samples=4, samples_tasks="solve")
                out = Path(directory)
                with patch.dict(sys.modules, modules), patch.object(evaluation, "rows_for", return_value=[{"uid": "solve-1"}]), \
                     patch.object(evaluation.baseline, "render_prompt", return_value="unchanged SOLVE prompt"):
                    evaluation.run_task(args, "solve", out)

                messages, sampling, chat_kwargs = calls["chat"]
                self.assertEqual(messages, [[{"role": "user", "content": "unchanged SOLVE prompt"}]])
                self.assertEqual(sampling, {"n": 4, "temperature": 1.0, "top_p": 1.0, "top_k": 0,
                                            "max_tokens": 16384, "seed": 0})
                if mode == "instruct":
                    self.assertNotIn("chat_template_kwargs", chat_kwargs)
                    self.assertEqual(calls["loader"]["tokenizer_mode"], "mistral")
                else:
                    self.assertEqual(chat_kwargs["chat_template_kwargs"], {"enable_thinking": False})
                    self.assertNotIn("tokenizer_mode", calls["loader"])
                prompts, continuation = calls["continuation"]
                self.assertEqual(prompts, [{"prompt_token_ids": [101, 102, 7, 8]}])
                self.assertEqual(continuation["max_tokens"], 16384)
                self.assertEqual(continuation["seed"], 1)
                records = [json.loads(line) for line in (out / "responses-solve.jsonl").read_text().splitlines()]
                self.assertEqual(len(records), 4)
                self.assertEqual(records[3]["text"], "[7, 8, 9]")
                self.assertTrue(records[3]["continued"])
                self.assertFalse(any(x["continued"] for x in records[:3]))


if __name__ == "__main__":
    unittest.main()
