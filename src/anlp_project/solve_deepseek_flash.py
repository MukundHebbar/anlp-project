"""Generate no-reference SOLVE answers with DeepSeek V4 Flash on DeepInfra."""

from __future__ import annotations

import argparse
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from .export_solve_report import completed_records, render_report
from .paths import ARTIFACTS_DIR, ENV_FILE, MANIFESTS_DIR, PROMPTS_DIR, PROJECT_ROOT
from .solution_verification import usage_cost
from .storage import atomic_write_json, atomic_write_text, read_json


ROOT_DIR = PROJECT_ROOT
DEFAULT_INPUT = MANIFESTS_DIR / "deepmath" / "deepmath-pilot-146.json"
DEFAULT_PROMPT = PROMPTS_DIR / "solve" / "solve_no_reference.md"
DEFAULT_OUTPUT = ARTIFACTS_DIR / "deepseek-v4-flash" / "solve" / "146" / "solutions.json"
DEFAULT_REPORT = ARTIFACTS_DIR / "deepseek-v4-flash" / "solve" / "146" / "report.txt"
DEFAULT_ENV = ENV_FILE
DEFAULT_MODEL = "deepseek-ai/DeepSeek-V4-Flash-0731"
DEFAULT_REASONING_EFFORT = "medium"
DEFAULT_MAX_TOKENS = 16384
DEFAULT_TIMEOUT_SECONDS = 900.0
DEFAULT_CONCURRENCY = 10
INPUT_PRICE_PER_MILLION = 0.08
OUTPUT_PRICE_PER_MILLION = 0.18
DEFAULT_INDICES = (
    0, 1, 2, 3, 5, 6, 7, 8, 9, 11, 15, 18, 20, 23, 25, 27, 33,
    36, 38, 40, 41, 45, 46, 47, 49,
)


def render_prompt(template: str, question: str) -> str:
    if "{{QUESTION}}" in template:
        return template.replace("{{QUESTION}}", question)
    if "{question}" in template:
        return template.replace("{question}", question)
    raise ValueError("Prompt must include {{QUESTION}} or {question}")


def validate_and_select(input_path: Path, prompt_path: Path, indices: list[int]) -> tuple[list[dict[str, Any]], str]:
    input_data = read_json(input_path)
    problems = input_data.get("problems")
    if not isinstance(problems, list):
        raise ValueError(f"{input_path} must contain a 'problems' list")
    if len(indices) != len(set(indices)):
        raise ValueError("Problem indices must be unique")
    invalid = [index for index in indices if index < 0 or index >= len(problems)]
    if invalid:
        raise ValueError(f"Problem indices are out of range: {invalid}")

    try:
        template = prompt_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ValueError(f"Prompt file does not exist: {prompt_path}") from exc
    render_prompt(template, "validation question")

    selected = []
    for index in indices:
        problem = problems[index]
        if not isinstance(problem, dict) or not problem.get("question"):
            raise ValueError(f"Problem {index} is missing a question")
        selected.append({**problem, "source_index": problem.get("source_index", index)})
    return selected, template


def create_client(api_key: str, timeout_seconds: float) -> Any:
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("Install the 'openai' package before running this script") from exc
    return OpenAI(
        api_key=api_key,
        base_url="https://api.deepinfra.com/v1/openai",
        timeout=timeout_seconds,
        max_retries=0,
    )


def response_data(response: Any) -> tuple[str, str | None, str | None, dict[str, Any] | None]:
    choices = getattr(response, "choices", None) or []
    if not choices:
        raise ValueError("API response did not contain any choices")
    message = getattr(choices[0], "message", None)
    content = getattr(message, "content", None)
    if not isinstance(content, str) or not content.strip():
        raise ValueError("API response contained an empty visible solution")

    reasoning = getattr(message, "reasoning_content", None)
    if not isinstance(reasoning, str):
        reasoning = None
    usage = getattr(response, "usage", None)
    if usage is not None and hasattr(usage, "model_dump"):
        usage = usage.model_dump()
    elif usage is not None and hasattr(usage, "to_dict"):
        usage = usage.to_dict()
    elif not isinstance(usage, dict):
        usage = None

    return content.strip(), reasoning, getattr(choices[0], "finish_reason", None), usage


class StreamInterruptedError(RuntimeError):
    """Preserves visible text received before a streaming request fails."""

    def __init__(self, cause: Exception, partial_solution: str, partial_reasoning: str) -> None:
        super().__init__(str(cause))
        self.partial_solution = partial_solution
        self.partial_reasoning = partial_reasoning


def stream_solution(
    client: Any,
    model: str,
    prompt: str,
    max_tokens: int,
) -> tuple[str, str | None, str | None, dict[str, Any] | None]:
    visible_parts: list[str] = []
    reasoning_parts: list[str] = []
    finish_reason: str | None = None
    usage: dict[str, Any] | None = None
    try:
        stream = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=max_tokens,
            stream=True,
            stream_options={"include_usage": True},
            extra_body={"reasoning_effort": DEFAULT_REASONING_EFFORT},
        )
        for chunk in stream:
            choices = getattr(chunk, "choices", None) or []
            if choices:
                choice = choices[0]
                delta = getattr(choice, "delta", None)
                content = getattr(delta, "content", None)
                reasoning = getattr(delta, "reasoning_content", None)
                if isinstance(content, str):
                    visible_parts.append(content)
                if isinstance(reasoning, str):
                    reasoning_parts.append(reasoning)
                if getattr(choice, "finish_reason", None):
                    finish_reason = choice.finish_reason
            chunk_usage = getattr(chunk, "usage", None)
            if chunk_usage is not None:
                if hasattr(chunk_usage, "model_dump"):
                    usage = chunk_usage.model_dump()
                elif hasattr(chunk_usage, "to_dict"):
                    usage = chunk_usage.to_dict()
                elif isinstance(chunk_usage, dict):
                    usage = chunk_usage
    except Exception as error:
        raise StreamInterruptedError(
            error,
            "".join(visible_parts).strip(),
            "".join(reasoning_parts).strip(),
        ) from error

    solution = "".join(visible_parts).strip()
    if not solution:
        raise ValueError("API stream completed without a visible solution")
    reasoning = "".join(reasoning_parts).strip() or None
    return solution, reasoning, finish_reason, usage


def initialize_output(output_path: Path, selected: list[dict[str, Any]]) -> dict[str, Any]:
    if not output_path.exists():
        return {"metadata": {}, "problems": [dict(problem) for problem in selected]}

    output = read_json(output_path)
    saved = output.get("problems")
    if not isinstance(saved, list) or len(saved) != len(selected):
        raise ValueError("Existing output does not match the requested experiment")
    for source, existing in zip(selected, saved):
        if existing.get("source_index") != source["source_index"]:
            raise ValueError("Existing output problem order does not match this experiment")
    return output


def estimated_max_cost(problem_count: int, max_tokens: int) -> float:
    """Output-only ceiling; prompt-token cost is small and input-dependent."""
    return problem_count * max_tokens * OUTPUT_PRICE_PER_MILLION / 1_000_000


def run_generation(args: argparse.Namespace, client: Any) -> dict[str, Any]:
    selected, template = validate_and_select(args.input, args.prompt, args.indices)
    output = initialize_output(args.output, selected)
    metadata = output.setdefault("metadata", {})
    metadata.update(
        {
            "model": args.model,
            "reasoning_effort": DEFAULT_REASONING_EFFORT,
            "prompt_file": str(args.prompt),
            "source_indices": args.indices,
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
            status = problem.get("solve_status")
            if status == "completed" or (status == "failed" and not args.retry_failed):
                print(f"[{position}/{len(selected)}] skipped ({status})")
                continue
            prompt = render_prompt(template, problem["question"])
            future = executor.submit(stream_solution, client, args.model, prompt, args.max_tokens)
            pending[future] = (position, problem)
            print(f"[{position}/{len(selected)}] queued")

        for future in as_completed(pending):
            position, problem = pending[future]
            try:
                solution, reasoning, finish_reason, usage = future.result()
                problem.update(
                    {
                        "solve_status": "completed",
                        "solve_model": args.model,
                        "solve_reasoning_effort": DEFAULT_REASONING_EFFORT,
                        "solve_solution": solution,
                        "solve_reasoning": reasoning,
                        "solve_finish_reason": finish_reason,
                        "solve_usage": usage,
                        "solve_usage_cost": usage_cost(usage),
                    }
                )
                problem.pop("solve_error", None)
                problem.pop("solve_partial_solution", None)
                problem.pop("solve_partial_reasoning", None)
                print(f"[{position}/{len(selected)}] completed")
            except StreamInterruptedError as error:
                problem.update(
                    {
                        "solve_status": "failed",
                        "solve_model": args.model,
                        "solve_error": f"{error.__cause__.__class__.__name__}: {error}",
                        "solve_partial_solution": error.partial_solution or None,
                        "solve_partial_reasoning": error.partial_reasoning or None,
                        "solve_usage_cost": usage_cost(None),
                    }
                )
                print(f"[{position}/{len(selected)}] stream interrupted: {problem['solve_error']}")
            except Exception as error:
                problem.update(
                    {
                        "solve_status": "failed",
                        "solve_model": args.model,
                        "solve_error": f"{error.__class__.__name__}: {error}",
                        "solve_usage_cost": usage_cost(None),
                    }
                )
                print(f"[{position}/{len(selected)}] failed: {problem['solve_error']}")
            finally:
                atomic_write_json(args.output, output)

    records = completed_records([args.output])
    atomic_write_text(args.report, render_report(records))
    print(f"Finished: {len(records)}/{len(selected)} completed; report: {args.report}")
    return output


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--prompt", type=Path, default=DEFAULT_PROMPT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--indices", type=int, nargs="+", default=list(DEFAULT_INDICES))
    parser.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY)
    parser.add_argument("--retry-failed", action="store_true", help="Explicitly retry failed records on rerun.")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.max_tokens < 1 or args.timeout <= 0 or args.concurrency < 1:
        raise ValueError("max-tokens, timeout, and concurrency must be positive")
    try:
        from dotenv import load_dotenv

        load_dotenv(DEFAULT_ENV)
    except ImportError as exc:
        raise RuntimeError("Install the 'python-dotenv' package before running this script") from exc

    selected, _ = validate_and_select(args.input, args.prompt, args.indices)
    if args.dry_run:
        print(f"Valid problems: {len(selected)}")
        print(f"Model: {args.model}")
        print(f"Reasoning effort: {DEFAULT_REASONING_EFFORT}")
        print(f"No automatic retries; timeout: {args.timeout:g}s")
        print(f"Maximum output-only cost: ${estimated_max_cost(len(selected), args.max_tokens):.4f}")
        return

    api_key = os.getenv("DEEPINFRA_API_KEY")
    if not api_key:
        raise RuntimeError("DEEPINFRA_API_KEY is not set in .env or the environment")
    run_generation(args, create_client(api_key, args.timeout))


if __name__ == "__main__":
    main()
