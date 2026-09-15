"""Generate versioned EXPLAIN tasks from completed DeepSeek SOLVE responses."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .paths import ARTIFACTS_DIR, MANIFESTS_DIR, PROMPTS_DIR, PROJECT_ROOT
from .solve_deepseek_flash import StreamInterruptedError, create_client, stream_solution
from .solution_verification import usage_cost
from .storage import atomic_write_json, read_json


ROOT_DIR = PROJECT_ROOT
DEFAULT_INPUT = MANIFESTS_DIR / "deepmath" / "deepmath-pilot-113-deepseek-v2-correct.json"
DEFAULT_PROMPT = PROMPTS_DIR / "explain" / "explain_v1.md"
DEFAULT_OUTPUT = ARTIFACTS_DIR / "deepseek-v4-flash" / "explain" / "v2-113" / "explanations.json"
DEFAULT_REPORT = ARTIFACTS_DIR / "deepseek-v4-flash" / "explain" / "v2-113" / "report.txt"
DEFAULT_MODEL = "deepseek-ai/DeepSeek-V4-Flash-0731"
REASONING_EFFORT = "medium"
DEFAULT_MAX_TOKENS = 16384
DEFAULT_TIMEOUT_SECONDS = 900.0
DEFAULT_CONCURRENCY = 20
OUTPUT_PRICE_PER_MILLION = 0.18
STUDENT_KEYS = {
    "problem",
    "established_context",
    "solution_skeleton",
    "transition_to_explain",
    "student_instruction",
}
OUTPUT_KEYS = {
    "main_step_skeleton",
    "student_facing_task",
    "reference_explanation",
    "required_criteria",
    "material_errors",
    "generation_notes",
}
RETRY_FORMAT_INSTRUCTIONS = """
FORMAT RETRY: Your previous response was rejected as invalid. Return exactly one
raw JSON object matching the required schema in this prompt, with no Markdown
code fences, no explanatory text before or after the JSON, and no trailing
commas. Escape every backslash inside JSON strings (for example, use \\frac
and \\( for LaTeX). Do not change the requested task design.
""".strip()


def render_prompt(template: str, problem: str, reference_solution: str) -> str:
    required = ("{problem}", "{reference_solution}")
    missing = [placeholder for placeholder in required if placeholder not in template]
    if missing:
        raise ValueError(f"EXPLAIN prompt is missing placeholders: {', '.join(missing)}")
    return template.replace("{problem}", problem).replace("{reference_solution}", reference_solution)


def load_records(input_path: Path, prompt_path: Path) -> tuple[list[dict[str, Any]], str]:
    try:
        template = prompt_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ValueError(f"Prompt file does not exist: {prompt_path}") from exc
    render_prompt(template, "validation problem", "validation reference solution")

    problems = read_json(input_path).get("problems")
    if not isinstance(problems, list):
        raise ValueError(f"{input_path} must contain a 'problems' list")

    selected: list[dict[str, Any]] = []
    seen: set[int] = set()
    for position, problem in enumerate(problems):
        if not isinstance(problem, dict) or problem.get("solve_status") != "completed":
            continue
        source_index = problem.get("source_index", position)
        if not isinstance(source_index, int) or source_index in seen:
            raise ValueError(f"Invalid or duplicate source_index in {input_path}: {source_index!r}")
        if not problem.get("question") or not problem.get("solve_solution"):
            raise ValueError(f"Completed problem {source_index} lacks question or solve_solution")
        seen.add(source_index)
        selected.append({**problem, "source_index": source_index})

    if not selected:
        raise ValueError("No completed DeepSeek SOLVE records were found")
    return selected, template


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def validate_output(value: Any, source_problem: dict[str, Any]) -> dict[str, Any] | str:
    if value == "NOT_SUITABLE":
        return value
    _require(isinstance(value, dict), "model output must be a JSON object or NOT_SUITABLE")
    _require(set(value) == OUTPUT_KEYS, "model output has the wrong top-level schema")

    task = value["student_facing_task"]
    _require(isinstance(task, dict), "student_facing_task must be an object")
    _require(set(task) == STUDENT_KEYS, "student_facing_task has the wrong schema")
    _require(isinstance(task["problem"], str) and task["problem"].strip(), "student problem must be non-empty")
    _require(isinstance(task["established_context"], list), "established_context must be a list")
    _require(all(isinstance(item, str) and item.strip() for item in task["established_context"]), "context entries must be non-empty strings")

    main_skeleton = value["main_step_skeleton"]
    _require(isinstance(main_skeleton, list) and len(main_skeleton) >= 2, "main_step_skeleton must contain at least 2 steps")
    main_ids = [step.get("id") if isinstance(step, dict) else None for step in main_skeleton]
    _require(main_ids == [f"S{i}" for i in range(1, len(main_skeleton) + 1)], "main step IDs must be ordered S1..Sn")
    _require(
        all(
            isinstance(step, dict)
            and set(step) == {"id", "statement"}
            and isinstance(step["statement"], str)
            and step["statement"].strip()
            for step in main_skeleton
        ),
        "invalid main step skeleton step",
    )

    skeleton = task["solution_skeleton"]
    _require(isinstance(skeleton, list) and len(skeleton) == 2, "solution_skeleton must contain exactly 2 steps")
    ids = [step.get("id") if isinstance(step, dict) else None for step in skeleton]
    _require(all(step_id in main_ids for step_id in ids), "solution skeleton refers to an unknown main step")
    _require(ids[1] == f"S{int(ids[0][1:]) + 1}" if all(isinstance(step_id, str) and step_id.startswith("S") and step_id[1:].isdigit() for step_id in ids) else False, "solution skeleton steps must be consecutive")
    _require(
        all(
            isinstance(step, dict)
            and set(step) == {"id", "statement"}
            and isinstance(step["statement"], str)
            and step["statement"].strip()
            for step in skeleton
        ),
        "invalid solution skeleton step",
    )

    transition = task["transition_to_explain"]
    _require(isinstance(transition, dict) and set(transition) == {"from", "to", "question"}, "invalid transition schema")
    _require(isinstance(transition["question"], str) and transition["question"].strip(), "transition question must be non-empty")
    _require(transition["from"] == ids[0] and transition["to"] == ids[1], "transition must connect the supplied consecutive steps")

    _require(isinstance(task["student_instruction"], str) and task["student_instruction"].strip(), "student_instruction must be non-empty")
    _require(isinstance(value["reference_explanation"], str) and value["reference_explanation"].strip(), "reference explanation must be non-empty")
    _require(isinstance(value["required_criteria"], list) and len(value["required_criteria"]) == 3, "required_criteria must contain exactly three items")
    _require(all(isinstance(item, str) and item.strip() for item in value["required_criteria"]), "criteria must be non-empty strings")
    _require(isinstance(value["material_errors"], list) and all(isinstance(item, str) and item.strip() for item in value["material_errors"]), "material_errors must be a list of strings")
    _require(isinstance(value["generation_notes"], str) and value["generation_notes"].strip(), "generation_notes must be non-empty")

    # The original problem is necessarily shown to the student and may contain
    # a word that is also the dataset's final answer (for example, a person's
    # name in a "who is correct?" question).  Check leakage only in generated
    # task fields other than the problem statement itself.
    student_text = json.dumps(
        {key: value for key, value in task.items() if key != "problem"},
        ensure_ascii=False,
    )
    _require(str(source_problem["solve_solution"]) not in student_text, "private full solution leaked into student-facing task")
    final_answer = str(source_problem.get("final_answer", "")).strip()
    if len(final_answer) >= 4:
        _require(final_answer not in student_text, "original final answer leaked into student-facing task")
    return value


def _json_payload(response: str) -> tuple[str, str]:
    text = response.strip()
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", text, flags=re.IGNORECASE | re.DOTALL)
    if fenced:
        return fenced.group(1).strip(), "stripped_outer_json_code_fence"
    if text.startswith("```") or text.endswith("```"):
        raise ValueError("malformed JSON code fence")
    return text, "raw_json"


def parse_and_validate_detailed(response: str, source_problem: dict[str, Any]) -> tuple[dict[str, Any] | str, str]:
    payload, normalization_method = _json_payload(response)
    if payload == "NOT_SUITABLE":
        return "NOT_SUITABLE", normalization_method
    try:
        value = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ValueError(f"malformed JSON: {exc.msg}") from exc
    return validate_output(value, source_problem), normalization_method


def parse_and_validate(response: str, source_problem: dict[str, Any]) -> dict[str, Any] | str:
    value, _ = parse_and_validate_detailed(response, source_problem)
    return value


# Backward-compatible name used by the existing v1 tests and callers.
validate_v1_output = validate_output


def estimated_max_cost(problem_count: int, max_tokens: int) -> float:
    return problem_count * max_tokens * OUTPUT_PRICE_PER_MILLION / 1_000_000


def load_project_environment(env_path: Path) -> None:
    """Load a simple project .env when python-dotenv is unavailable."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        if not env_path.exists():
            return
        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
                value = value[1:-1]
            os.environ.setdefault(key, value)
    else:
        load_dotenv(env_path)


def initialize_output(output_path: Path) -> dict[str, Any]:
    if not output_path.exists():
        return {"metadata": {}, "items": []}
    try:
        output = read_json(output_path)
    except ValueError:
        return {"metadata": {}, "items": []}
    if not isinstance(output, dict) or not isinstance(output.get("items"), list):
        return {"metadata": {}, "items": []}
    return output


def _usage_summary(output: dict[str, Any]) -> dict[str, Any]:
    prompt_tokens = 0
    completion_tokens = 0
    token_records = 0
    calculated_cost = 0.0
    provider_cost = 0.0
    provider_records = 0
    for detail in output.get("metadata", {}).get("generation_details", {}).values():
        usage = detail.get("usage") if isinstance(detail, dict) else None
        cost = usage_cost(usage)
        if cost["prompt_tokens"] is not None:
            prompt_tokens += cost["prompt_tokens"]
        if cost["completion_tokens"] is not None:
            completion_tokens += cost["completion_tokens"]
        if cost["total_tokens"] is not None:
            token_records += 1
        if cost["calculated_cost_usd"] is not None:
            calculated_cost += cost["calculated_cost_usd"]
        if cost["provider_estimated_cost_usd"] is not None:
            provider_cost += cost["provider_estimated_cost_usd"]
            provider_records += 1
    return {
        "records_with_usage": token_records,
        "prompt_tokens": prompt_tokens if token_records else None,
        "completion_tokens": completion_tokens if token_records else None,
        "total_tokens": (prompt_tokens + completion_tokens) if token_records else None,
        "calculated_cost_usd": calculated_cost if token_records else None,
        "provider_estimated_cost_usd": provider_cost if provider_records else None,
    }


def render_report(output: dict[str, Any], selected_count: int, version: str = "v1") -> str:
    items = output.get("items", [])
    suitable = sum(item.get("output") != "NOT_SUITABLE" for item in items)
    not_suitable = sum(item.get("output") == "NOT_SUITABLE" for item in items)
    failures = output.get("failures", [])
    recovered = len(output.get("recovered_failures", []))
    elapsed = output.get("metadata", {}).get("elapsed_seconds")
    usage = output.get("metadata", {}).get("usage_summary", {})
    lines = [
        f"EXPLAIN-{version} DeepSeek generation",
        f"Selected solutions: {selected_count}",
        f"Valid EXPLAIN tasks: {suitable}",
        f"Successful task rate: {suitable}/{selected_count} ({suitable / selected_count:.2%})" if selected_count else "Successful task rate: 0/0",
        f"NOT_SUITABLE: {not_suitable}",
        f"Recovered locally without API request: {recovered}",
        f"Rejected/failed generations: {len(failures)}",
        f"Rejection rate: {len(failures)}/{selected_count} ({len(failures) / selected_count:.2%})" if selected_count else "Rejection rate: 0/0",
        f"Elapsed seconds: {elapsed}",
        f"Prompt tokens: {usage.get('prompt_tokens')}",
        f"Completion tokens: {usage.get('completion_tokens')}",
        f"Total tokens: {usage.get('total_tokens')}",
        f"Calculated cost USD: {usage.get('calculated_cost_usd')}",
        f"Provider-reported cost USD: {usage.get('provider_estimated_cost_usd')}",
    ]
    if failures:
        lines.append("Failures:")
        lines.extend(f"- source_index {item['source_index']}: {item['error']}" for item in failures)
    return "\n".join(lines) + "\n"


def run_generation(args: argparse.Namespace, client: Any) -> dict[str, Any]:
    version = getattr(args, "version", "v1")
    started_at = datetime.now(timezone.utc)
    started_clock = time.perf_counter()
    selected, template = load_records(args.input, args.prompt)
    output = initialize_output(args.output)
    metadata = output.setdefault("metadata", {})
    metadata.update(
        {
            "schema": f"explain_{version}_batch",
            "prompt_version": version,
            "model": args.model,
            "reasoning_effort": REASONING_EFFORT,
            "prompt_file": str(args.prompt),
            "input_file": str(args.input),
            "reference_solution_field": "solve_solution",
            "prompt_sha256": hashlib.sha256(template.encode("utf-8")).hexdigest(),
            "selected_source_indices": [problem["source_index"] for problem in selected],
            "excluded_source_indices": [
                problem.get("source_index", position)
                for position, problem in enumerate(read_json(args.input).get("problems", []))
                if isinstance(problem, dict) and problem.get("solve_status") != "completed"
            ],
            "max_tokens": args.max_tokens,
            "timeout_seconds": args.timeout,
            "concurrency": args.concurrency,
            "stream": True,
            "automatic_retries": False,
            "estimated_max_output_cost_usd": estimated_max_cost(len(selected), args.max_tokens),
        }
    )
    output.setdefault("items", [])
    previous_failures = {
        item.get("source_index")
        for item in output.get("failures", [])
        if isinstance(item, dict) and isinstance(item.get("source_index"), int)
    }
    output["failures"] = []
    saved = {item["source_index"]: item for item in output["items"] if isinstance(item, dict) and "source_index" in item}
    pending: dict[Any, tuple[int, dict[str, Any]]] = {}
    with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        for position, problem in enumerate(selected, start=1):
            existing = saved.get(problem["source_index"])
            if existing is not None and "output" in existing:
                try:
                    existing_value = existing["output"]
                    parse_and_validate(existing_value if existing_value == "NOT_SUITABLE" else json.dumps(existing_value), problem)
                    print(f"[{position}/{len(selected)}] skipped (existing valid output)")
                    continue
                except ValueError:
                    output["items"] = [item for item in output["items"] if item.get("source_index") != problem["source_index"]]
            prompt = render_prompt(template, problem["question"], problem["solve_solution"])
            if args.retry_rejected and problem["source_index"] in previous_failures:
                prompt = f"{prompt}\n\n{RETRY_FORMAT_INSTRUCTIONS}"
            future = executor.submit(stream_solution, client, args.model, prompt, args.max_tokens)
            pending[future] = (position, problem)
            print(f"[{position}/{len(selected)}] queued")

        for future in as_completed(pending):
            position, problem = pending[future]
            source_index = problem["source_index"]
            response_text: str | None = None
            try:
                response, reasoning, finish_reason, usage = future.result()
                response_text = response
                parsed, normalization_method = parse_and_validate_detailed(response, problem)
                output["items"] = [old for old in output["items"] if old.get("source_index") != source_index]
                output["items"].append({"source_index": source_index, "output": parsed})
                output["items"].sort(key=lambda old: old["source_index"])
                metadata.setdefault("generation_details", {})[str(source_index)] = {
                    "status": "completed",
                    "finish_reason": finish_reason,
                    "usage": usage,
                    "reasoning": reasoning,
                    "normalization_method": normalization_method,
                }
                print(f"[{position}/{len(selected)}] completed ({'not_suitable' if parsed == 'NOT_SUITABLE' else 'task'})")
            except Exception as error:
                failure = {
                    "source_index": source_index,
                    "error": f"{error.__class__.__name__}: {error}",
                    "raw_response": response_text,
                }
                output["failures"].append(failure)
                print(f"[{position}/{len(selected)}] rejected: {failure['error']}")
            finally:
                atomic_write_json(args.output, output)

    metadata["started_at_utc"] = started_at.isoformat()
    metadata["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
    metadata["elapsed_seconds"] = round(time.perf_counter() - started_clock, 3)
    metadata["usage_summary"] = _usage_summary(output)
    metadata["counts"] = {
        "selected": len(selected),
        "valid_tasks": sum(item.get("output") != "NOT_SUITABLE" for item in output["items"]),
        "not_suitable": sum(item.get("output") == "NOT_SUITABLE" for item in output["items"]),
        "rejected_or_failed": len(output["failures"]),
    }
    atomic_write_json(args.output, output)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(render_report(output, len(selected), version), encoding="utf-8")
    print(f"Finished: {len(output['items'])}/{len(selected)} valid outputs; report: {args.report}")
    return output


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--prompt", type=Path, default=DEFAULT_PROMPT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY)
    parser.add_argument("--version", choices=("v1", "v2"), default="v1")
    parser.add_argument("--retry-failed", action="store_true")
    parser.add_argument("--retry-rejected", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.max_tokens < 1 or args.timeout <= 0 or args.concurrency < 1:
        raise ValueError("max-tokens, timeout, and concurrency must be positive")
    selected, _ = load_records(args.input, args.prompt)
    if args.dry_run:
        print(f"Valid completed DeepSeek SOLVE records: {len(selected)}")
        print(f"Excluded records: {len(read_json(args.input).get('problems', [])) - len(selected)}")
        print(f"Model: {args.model}")
        print(f"Prompt: {args.prompt}")
        print(f"Prompt version: {args.version}")
        print(f"Reasoning effort: {REASONING_EFFORT}")
        print(f"Streaming: True; concurrency: {args.concurrency}; timeout: {args.timeout:g}s")
        print(f"No automatic retries; maximum output-only cost: ${estimated_max_cost(len(selected), args.max_tokens):.4f}")
        return
    load_project_environment(ROOT_DIR / ".env")

    api_key = os.getenv("DEEPINFRA_API_KEY")
    if not api_key:
        raise RuntimeError("DEEPINFRA_API_KEY is not set in .env or the environment")
    run_generation(args, create_client(api_key, args.timeout))


if __name__ == "__main__":
    main()
