"""Generate reference-guided PLAN outputs with DeepSeek V4 Flash on DeepInfra."""

from __future__ import annotations

import argparse
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from .paths import ARTIFACTS_DIR, PROMPTS_DIR, PROJECT_ROOT
from .solve_deepseek_flash import StreamInterruptedError, create_client, stream_solution
from .storage import atomic_write_json, read_json


ROOT_DIR = PROJECT_ROOT
DEFAULT_INPUTS = [
    ARTIFACTS_DIR / "deepseek-v4-flash" / "solve" / "146" / "solutions.json",
]
DEFAULT_PROMPT = PROMPTS_DIR / "plan" / "plan.md"
DEFAULT_OUTPUT = ARTIFACTS_DIR / "deepseek-v4-flash" / "plan" / "plans.json"
DEFAULT_MODEL = "deepseek-ai/DeepSeek-V4-Flash-0731"
DEFAULT_MAX_TOKENS = 16384
DEFAULT_TIMEOUT_SECONDS = 900.0
DEFAULT_CONCURRENCY = 20
REASONING_EFFORT = "medium"
OUTPUT_PRICE_PER_MILLION = 0.18


def render_prompt(template: str, question: str, solution: str) -> str:
    if "{question}" not in template or "{solution}" not in template:
        raise ValueError("Plan prompt must include both {question} and {solution}")
    return template.replace("{question}", question).replace("{solution}", solution)


def load_records(input_paths: list[Path], prompt_path: Path) -> tuple[list[dict[str, Any]], str]:
    try:
        template = prompt_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ValueError(f"Prompt file does not exist: {prompt_path}") from exc
    render_prompt(template, "validation question", "validation solution")

    records_by_index: dict[int, dict[str, Any]] = {}
    for input_path in input_paths:
        data = read_json(input_path)
        problems = data.get("problems")
        if not isinstance(problems, list):
            raise ValueError(f"{input_path} must contain a 'problems' list")
        for position, problem in enumerate(problems):
            if not isinstance(problem, dict) or problem.get("solve_status") != "completed":
                continue
            source_index = problem.get("source_index", position)
            if not isinstance(source_index, int):
                raise ValueError(f"Invalid source_index in {input_path}: {source_index!r}")
            if source_index in records_by_index:
                raise ValueError(f"Duplicate completed source index: {source_index}")
            if not problem.get("question") or not problem.get("solve_solution"):
                raise ValueError(f"Completed problem {source_index} lacks question or solve_solution")
            records_by_index[source_index] = {**problem, "source_index": source_index}

    if not records_by_index:
        raise ValueError("No completed solve records were found in the input files")
    return [records_by_index[index] for index in sorted(records_by_index)], template


def initialize_output(output_path: Path, selected: list[dict[str, Any]]) -> dict[str, Any]:
    if not output_path.exists():
        return {"metadata": {}, "problems": [dict(problem) for problem in selected]}

    output = read_json(output_path)
    saved = output.get("problems")
    if not isinstance(saved, list) or len(saved) != len(selected):
        raise ValueError("Existing plan output does not match the selected solve records")
    for source, existing in zip(selected, saved):
        if existing.get("source_index") != source["source_index"]:
            raise ValueError("Existing plan output order does not match the solve records")
    return output


def estimated_max_cost(problem_count: int, max_tokens: int) -> float:
    return problem_count * max_tokens * OUTPUT_PRICE_PER_MILLION / 1_000_000


def run_generation(args: argparse.Namespace, client: Any) -> dict[str, Any]:
    selected, template = load_records(args.inputs, args.prompt)
    output = initialize_output(args.output, selected)
    output.setdefault("metadata", {}).update(
        {
            "model": args.model,
            "reasoning_effort": REASONING_EFFORT,
            "prompt_file": str(args.prompt),
            "input_files": [str(path) for path in args.inputs],
            "max_tokens": args.max_tokens,
            "timeout_seconds": args.timeout,
            "concurrency": args.concurrency,
            "stream": True,
            "automatic_retries": False,
            "estimated_max_output_cost_usd": estimated_max_cost(len(selected), args.max_tokens),
        }
    )

    pending: dict[Any, tuple[int, dict[str, Any]]] = {}
    with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        for position, problem in enumerate(output["problems"], start=1):
            status = problem.get("plan_status")
            if status == "completed":
                print(f"[{position}/{len(selected)}] skipped (completed)")
                continue
            if status == "failed" and not args.retry_failed:
                print(f"[{position}/{len(selected)}] skipped (failed)")
                continue
            prompt = render_prompt(template, problem["question"], problem["solve_solution"])
            future = executor.submit(stream_solution, client, args.model, prompt, args.max_tokens)
            pending[future] = (position, problem)
            print(f"[{position}/{len(selected)}] queued")

        for future in as_completed(pending):
            position, problem = pending[future]
            try:
                plan, reasoning, finish_reason, usage = future.result()
                problem.update(
                    {
                        "plan_status": "completed",
                        "plan_model": args.model,
                        "plan_reasoning_effort": REASONING_EFFORT,
                        "plan_solution": plan,
                        "plan_reasoning": reasoning,
                        "plan_finish_reason": finish_reason,
                        "plan_usage": usage,
                    }
                )
                problem.pop("plan_error", None)
                problem.pop("plan_partial_solution", None)
                problem.pop("plan_partial_reasoning", None)
                print(f"[{position}/{len(selected)}] completed")
            except StreamInterruptedError as error:
                problem.update(
                    {
                        "plan_status": "failed",
                        "plan_model": args.model,
                        "plan_error": f"{error.__cause__.__class__.__name__}: {error}",
                        "plan_partial_solution": error.partial_solution or None,
                        "plan_partial_reasoning": error.partial_reasoning or None,
                    }
                )
                print(f"[{position}/{len(selected)}] stream interrupted: {problem['plan_error']}")
            except Exception as error:
                problem.update(
                    {
                        "plan_status": "failed",
                        "plan_model": args.model,
                        "plan_error": f"{error.__class__.__name__}: {error}",
                    }
                )
                print(f"[{position}/{len(selected)}] failed: {problem['plan_error']}")
            finally:
                atomic_write_json(args.output, output)

    completed = sum(problem.get("plan_status") == "completed" for problem in output["problems"])
    print(f"Finished: {completed}/{len(selected)} plans completed; output: {args.output}")
    return output


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", type=Path, nargs="+", default=DEFAULT_INPUTS)
    parser.add_argument("--prompt", type=Path, default=DEFAULT_PROMPT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY)
    parser.add_argument("--retry-failed", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.max_tokens < 1 or args.timeout <= 0 or args.concurrency < 1:
        raise ValueError("max-tokens, timeout, and concurrency must be positive")
    try:
        from dotenv import load_dotenv

        load_dotenv(ROOT_DIR / ".env")
    except ImportError as exc:
        raise RuntimeError("Install the 'python-dotenv' package before running this script") from exc

    selected, _ = load_records(args.inputs, args.prompt)
    if args.dry_run:
        print(f"Valid completed solve records: {len(selected)}")
        print(f"Model: {args.model}")
        print(f"Reasoning effort: {REASONING_EFFORT}")
        print(f"Streaming: True; concurrency: {args.concurrency}; timeout: {args.timeout:g}s")
        print(f"No automatic retries; maximum output-only cost: ${estimated_max_cost(len(selected), args.max_tokens):.4f}")
        return

    api_key = os.getenv("DEEPINFRA_API_KEY")
    if not api_key:
        raise RuntimeError("DEEPINFRA_API_KEY is not set in .env or the environment")
    run_generation(args, create_client(api_key, args.timeout))


if __name__ == "__main__":
    main()
