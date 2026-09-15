"""Generate SOLVE responses for the DeepMath pilot set using DeepInfra."""

from __future__ import annotations

import argparse
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Callable

from .paths import ENV_FILE, MANIFESTS_DIR, PROMPTS_DIR, PROJECT_ROOT
from .storage import atomic_write_json, read_json

ROOT_DIR = PROJECT_ROOT
DEFAULT_INPUT = MANIFESTS_DIR / "deepmath" / "deepmath-pilot-146.json"
DEFAULT_PROMPT = PROMPTS_DIR / "solve" / "solve.md"
DEFAULT_OUTPUT = PROJECT_ROOT / "artifacts" / "qwen3-4b" / "solve" / "pilot-output.json"
DEFAULT_ENV = ENV_FILE
DEFAULT_MODEL = "Qwen/Qwen3.5-35B-A3B"
DEFAULT_MAX_TOKENS = 8192
DEFAULT_CONCURRENCY = 4
DEFAULT_TIMEOUT_SECONDS = 300.0
THINKING_MODE = False
REFERENCE_FIELDS = ("r1_solution_1", "r1_solution_2", "r1_solution_3")
REFERENCE_STRATEGY = "shortest_complete_r1_trace"
NO_REFERENCE_STRATEGY = "not_used"
RETRYABLE_EXCEPTION_NAMES = {
    "APIConnectionError",
    "APITimeoutError",
    "InternalServerError",
    "RateLimitError",
}
PROMPT_PLACEHOLDERS = {
    "question": ("{question}", "{{QUESTION}}"),
    "final_answer": ("{final_answer}",),
    "reasoning_trace": ("{reasoning_trace}",),
}


def validate_inputs(input_path: Path, prompt_path: Path) -> tuple[dict[str, Any], str]:
    input_data = read_json(input_path)
    problems = input_data.get("problems")
    if not isinstance(problems, list) or not problems:
        raise ValueError(f"{input_path} must contain a non-empty 'problems' list")

    try:
        prompt = prompt_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ValueError(f"Prompt file does not exist: {prompt_path}") from exc

    if not any(token in prompt for token in PROMPT_PLACEHOLDERS["question"]):
        raise ValueError("Prompt must include either {question} or {{QUESTION}}")

    uses_reference = prompt_uses_reference(prompt)

    for index, problem in enumerate(problems):
        if not isinstance(problem, dict):
            raise ValueError(f"Problem {index} is not a JSON object")
        required_fields = ["question"]
        if "{final_answer}" in prompt:
            required_fields.append("final_answer")
        missing = [field for field in required_fields if not problem.get(field)]
        if missing:
            raise ValueError(f"Problem {index} is missing required fields: {missing}")
        if uses_reference and not any(problem.get(field) for field in REFERENCE_FIELDS):
            raise ValueError(f"Problem {index} has no usable reference trace")

    return input_data, prompt


def prompt_uses_reference(prompt_template: str) -> bool:
    return "{reasoning_trace}" in prompt_template


def select_reference_trace(problem: dict[str, Any]) -> tuple[str, str]:
    candidates = [
        (field, problem[field])
        for field in REFERENCE_FIELDS
        if isinstance(problem.get(field), str) and problem[field].strip()
    ]
    if not candidates:
        raise ValueError("Problem has no usable reference trace")
    return min(candidates, key=lambda candidate: len(candidate[1]))


def build_prompt(prompt_template: str, problem: dict[str, Any]) -> tuple[str, str | None]:
    reference_field: str | None = None
    try:
        prompt = prompt_template.replace("{{QUESTION}}", problem["question"])
        prompt = prompt.replace("{question}", problem["question"])
        if "{final_answer}" in prompt:
            prompt = prompt.replace("{final_answer}", problem["final_answer"])
        if not prompt_uses_reference(prompt_template):
            return prompt, None

        reference_field, reasoning_trace = select_reference_trace(problem)
        prompt = prompt.replace("{reasoning_trace}", reasoning_trace)
        return prompt, reference_field
    except KeyError as exc:
        raise ValueError(f"Problem is missing prompt data: {exc.args[0]}") from exc


def response_content(
    response: Any,
    thinking_mode: bool,
) -> tuple[str, str | None, str | None, dict[str, Any] | None, str]:
    choices = getattr(response, "choices", None) or []
    if not choices:
        raise ValueError("API response did not contain any choices")

    message = getattr(choices[0], "message", None)
    content = getattr(message, "content", None)
    if not isinstance(content, str) or not content.strip():
        raise ValueError("API response contained an empty solution")

    reasoning_content = getattr(message, "reasoning_content", None)
    if not isinstance(reasoning_content, str):
        reasoning_content = None

    has_inline_thinking = "<think>" in content or "</think>" in content
    if not thinking_mode and has_inline_thinking:
        raise ValueError(
            "Non-thinking response unexpectedly contained a thinking tag"
        )
    if not content:
        raise ValueError("API response contained no solution after removing thinking")

    finish_reason = getattr(choices[0], "finish_reason", None)
    usage = getattr(response, "usage", None)
    if usage is not None and hasattr(usage, "model_dump"):
        usage = usage.model_dump()
    elif usage is not None and hasattr(usage, "to_dict"):
        usage = usage.to_dict()
    elif usage is not None and isinstance(usage, dict):
        usage = usage
    else:
        usage = None

    response_format = "inline_thinking" if has_inline_thinking else "content_only"
    if reasoning_content:
        response_format = "separate_reasoning"

    return content.strip(), reasoning_content, finish_reason, usage, response_format


def is_retryable(error: Exception) -> bool:
    if error.__class__.__name__ in RETRYABLE_EXCEPTION_NAMES:
        return True
    status_code = getattr(error, "status_code", None)
    return status_code == 429 or isinstance(status_code, int) and status_code >= 500


def request_solution(
    client: Any,
    model: str,
    prompt: str,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    max_attempts: int = 3,
    backoff_seconds: float = 2.0,
    thinking_mode: bool = THINKING_MODE,
    sleep: Callable[[float], None] = time.sleep,
) -> tuple[str, str | None, str | None, dict[str, Any] | None, str]:
    last_error: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=1.0 if thinking_mode else 0.7,
                top_p=0.95 if thinking_mode else 0.8,
                presence_penalty=1.5 if thinking_mode else 0.0,
                max_tokens=max_tokens,
                extra_body={
                    "chat_template_kwargs": {"enable_thinking": thinking_mode},
                    "top_k": 20,
                    "min_p": 0.0,
                },
            )
            return response_content(response, thinking_mode)
        except Exception as error:  # API and response-shape errors are recorded per problem.
            last_error = error
            if not is_retryable(error) or attempt == max_attempts:
                raise
            delay = backoff_seconds * (2 ** (attempt - 1))
            print(f"  transient error; retrying in {delay:g}s ({attempt}/{max_attempts})")
            sleep(delay)

    raise RuntimeError("Request failed without an error") from last_error


def load_or_initialize_output(
    output_path: Path,
    input_data: dict[str, Any],
    input_path: Path,
) -> dict[str, Any]:
    input_problems = input_data["problems"]
    if not output_path.exists():
        return {
            "metadata": {
                "source_dataset": input_data.get("dataset", "unknown"),
                "source_file": str(input_path),
                "model": None,
                "reference_strategy": REFERENCE_STRATEGY,
                "thinking_mode": THINKING_MODE,
                "max_tokens": DEFAULT_MAX_TOKENS,
            },
            "problems": [dict(problem) for problem in input_problems],
        }

    output_data = read_json(output_path)
    output_problems = output_data.get("problems")
    if not isinstance(output_problems, list) or len(output_problems) != len(input_problems):
        raise ValueError(
            f"Existing output must contain exactly {len(input_problems)} problems: {output_path}"
        )

    for index, (source, saved) in enumerate(zip(input_problems, output_problems)):
        if not isinstance(saved, dict):
            raise ValueError(f"Existing output problem {index} is not an object")
        for field, value in source.items():
            if field in saved and saved[field] != value:
                raise ValueError(
                    f"Existing output problem {index} does not match input field '{field}'"
                )
            saved.setdefault(field, value)
    return output_data


def run_generation(
    input_path: Path,
    prompt_path: Path,
    output_path: Path,
    model: str,
    client: Any,
    max_attempts: int = 3,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    concurrency: int = DEFAULT_CONCURRENCY,
    thinking_mode: bool = THINKING_MODE,
    source_indices: list[int] | None = None,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    sleep: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    if concurrency < 1:
        raise ValueError("concurrency must be at least 1")

    input_data, prompt_template = validate_inputs(input_path, prompt_path)
    if source_indices is not None:
        original_problems = input_data["problems"]
        invalid_indices = [
            index for index in source_indices if index < 0 or index >= len(original_problems)
        ]
        if invalid_indices:
            raise ValueError(f"Problem indices are out of range: {invalid_indices}")
        input_data = {
            **input_data,
            "problems": [
                {**original_problems[index], "source_index": index}
                for index in source_indices
            ],
        }

    output_data = load_or_initialize_output(output_path, input_data, input_path)
    output_data.setdefault("metadata", {})["model"] = model
    output_data["metadata"]["prompt_file"] = str(prompt_path)
    output_data["metadata"]["thinking_mode"] = thinking_mode
    output_data["metadata"]["max_tokens"] = max_tokens
    output_data["metadata"]["reference_strategy"] = (
        REFERENCE_STRATEGY if prompt_uses_reference(prompt_template) else NO_REFERENCE_STRATEGY
    )
    output_data["metadata"]["concurrency"] = concurrency
    output_data["metadata"]["timeout_seconds"] = timeout_seconds
    output_data["metadata"]["source_indices"] = source_indices

    problems = output_data["problems"]
    total = len(problems)
    pending = {}
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        for index, problem in enumerate(problems, start=1):
            if (
                problem.get("solve_status") == "completed"
                and problem.get("solve_model") == model
                and problem.get("solve_thinking_mode") is thinking_mode
            ):
                print(f"[{index}/{total}] skipped (already completed)")
                continue

            try:
                prompt, reference_field = build_prompt(prompt_template, problem)
            except Exception as error:
                problem.update(
                    {
                        "solve_status": "failed",
                        "solve_model": model,
                        "solve_error": f"{error.__class__.__name__}: {error}",
                    }
                )
                atomic_write_json(output_path, output_data)
                continue

            reference_label = reference_field or "no reference trace"
            print(f"[{index}/{total}] queued with {reference_label}")
            future = executor.submit(
                request_solution,
                client,
                model,
                prompt,
                max_tokens,
                max_attempts,
                2.0,
                thinking_mode,
                sleep,
            )
            pending[future] = (index, problem, reference_field)

        for future in as_completed(pending):
            index, problem, reference_field = pending[future]
            try:
                solution, reasoning_content, finish_reason, usage, response_format = future.result()
                problem.update(
                    {
                        "solve_solution": solution,
                        "solve_status": "completed",
                        "solve_model": model,
                        "solve_thinking_mode": thinking_mode,
                        "solve_max_tokens": max_tokens,
                        "solve_reference_field": reference_field,
                        "solve_reference_strategy": (
                            REFERENCE_STRATEGY
                            if reference_field
                            else NO_REFERENCE_STRATEGY
                        ),
                        "solve_reasoning": reasoning_content,
                        "solve_response_format": response_format,
                        "solve_finish_reason": finish_reason,
                        "solve_usage": usage,
                    }
                )
                problem.pop("solve_error", None)
                print(f"[{index}/{total}] completed")
            except Exception as error:
                problem.update(
                    {
                        "solve_status": "failed",
                        "solve_model": model,
                        "solve_error": f"{error.__class__.__name__}: {error}",
                    }
                )
                print(f"[{index}/{total}] failed: {problem['solve_error']}")
            finally:
                atomic_write_json(output_path, output_data)

    completed = sum(problem.get("solve_status") == "completed" for problem in problems)
    print(f"Finished: {completed}/{total} solutions completed")
    return output_data


def create_client(
    api_key: str,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> Any:
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--prompt", type=Path, default=DEFAULT_PROMPT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--model", default=None)
    parser.add_argument("--max-attempts", type=int, default=3)
    parser.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)
    parser.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY)
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT_SECONDS,
        help="Per-request API timeout in seconds.",
    )
    parser.add_argument(
        "--thinking-mode",
        choices=("thinking", "non-thinking"),
        default="non-thinking",
        help="Select Qwen's chat-template thinking mode.",
    )
    parser.add_argument(
        "--indices",
        help="Comma-separated zero-based problem indexes to generate.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="validate the input and prompt without making API requests",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        from dotenv import load_dotenv

        load_dotenv(DEFAULT_ENV)
        load_dotenv()
    except ImportError as exc:
        raise RuntimeError("Install the 'python-dotenv' package before running this script") from exc

    input_data, _ = validate_inputs(args.input, args.prompt)
    model = args.model or os.getenv("DEEPINFRA_MODEL", DEFAULT_MODEL)
    source_indices = None
    if args.indices:
        try:
            source_indices = [int(index.strip()) for index in args.indices.split(",")]
        except ValueError as exc:
            raise ValueError("--indices must be comma-separated integers") from exc
        if not source_indices:
            raise ValueError("--indices must not be empty")
    if args.dry_run:
        total = len(source_indices) if source_indices is not None else len(input_data["problems"])
        print(f"Valid input: {total} problems")
        print(f"Prompt: {args.prompt}")
        print(f"Model: {model}")
        print(f"Thinking mode: {args.thinking_mode}")
        print(f"Timeout: {args.timeout:g}s")
        return

    api_key = os.getenv("DEEPINFRA_API_KEY")
    if not api_key:
        raise RuntimeError("DEEPINFRA_API_KEY is not set in .env or the environment")

    client = create_client(api_key, timeout_seconds=args.timeout)
    run_generation(
        input_path=args.input,
        prompt_path=args.prompt,
        output_path=args.output,
        model=model,
        client=client,
        max_attempts=args.max_attempts,
        max_tokens=args.max_tokens,
        concurrency=args.concurrency,
        thinking_mode=args.thinking_mode == "thinking",
        source_indices=source_indices,
        timeout_seconds=args.timeout,
    )


if __name__ == "__main__":
    main()
