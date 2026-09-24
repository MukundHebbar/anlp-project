#!/usr/bin/env python3
"""Load both proposal checkpoints and run one non-thinking chat smoke test."""

from __future__ import annotations

import argparse
import gc
import os
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--model-root",
        type=Path,
        default=Path("/share3") / os.environ.get("USER", "unknown") / "models",
    )
    parser.add_argument("--max-new-tokens", type=int, default=48)
    return parser.parse_args()


def main() -> None:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    args = parse_args()
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is unavailable; run this smoke test inside a GPU allocation")
    if args.max_new_tokens < 1:
        raise ValueError("max-new-tokens must be positive")

    messages = [
        {
            "role": "user",
            "content": "Decide whether the proposed solution is correct: 1+1=2. Answer briefly.",
        }
    ]
    for model_name in ("Qwen3-8B", "Qwen3-1.7B"):
        model_path = args.model_root / model_name
        print(f"Loading {model_name} from {model_path}")
        tokenizer = AutoTokenizer.from_pretrained(model_path, local_files_only=True)
        prompt = tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=False,
        )
        inputs = tokenizer(prompt, return_tensors="pt").to("cuda")
        model = AutoModelForCausalLM.from_pretrained(
            model_path,
            torch_dtype="auto",
            device_map="auto",
            local_files_only=True,
        )
        with torch.inference_mode():
            outputs = model.generate(**inputs, max_new_tokens=args.max_new_tokens, do_sample=False)
        generated = outputs[0][inputs.input_ids.shape[1] :]
        response = tokenizer.decode(generated, skip_special_tokens=True).strip()
        print(f"{model_name}: {response[:500]}")
        del outputs, generated, inputs, model, tokenizer
        gc.collect()
        torch.cuda.empty_cache()


if __name__ == "__main__":
    main()
