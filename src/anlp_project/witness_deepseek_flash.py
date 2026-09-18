"""Generate WITNESS construction tasks with DeepSeek V4 Flash on DeepInfra."""

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
DEFAULT_INPUT = MANIFESTS_DIR / "deepmath" / "deepmath-pilot-113-deepseek-v2-correct-explain-v2.json"
DEFAULT_PROMPT = PROMPTS_DIR / "witness" / "witness_generator_prompt.txt"
DEFAULT_OUTPUT = ARTIFACTS_DIR / "deepseek-v4-flash" / "witness" / "v1-113" / "results.json"
DEFAULT_REPORT = ARTIFACTS_DIR / "deepseek-v4-flash" / "witness" / "v1-113" / "report.txt"
DEFAULT_MODEL = "deepseek-ai/DeepSeek-V4-Flash-0731"
REASONING_EFFORT = "high"
DEFAULT_MAX_TOKENS = 16384
DEFAULT_TIMEOUT_SECONDS = 900.0
DEFAULT_CONCURRENCY = 20
OUTPUT_PRICE_PER_MILLION = 0.18

TOP_LEVEL_KEYS = {
    "transformation_type",
    "load_bearing_feature",
    "connection_to_source",
    "student_facing_task",
    "reference_witness",
    "evaluation_rubric",
    "quality_checks",
}
TASK_KEYS = {"source_problem", "relevant_context", "witness_request", "response_instruction"}
REFERENCE_KEYS = {"object", "verification"}
RUBRIC_KEYS = {
    "object_type",
    "required_conditions",
    "required_phenomenon",
    "acceptable_variation",
    "material_errors",
}
QUALITY_KEYS = {
    "single_primary_change",
    "problem_anchored",
    "reference_verified",
    "not_trivial_copying",
    "verification_shorter_than_full_solution",
}
TRANSFORMATION_TYPES = {
    "boundary_shift",
    "assumption_weakening",
    "domain_extension",
    "converse_failure",
    "equality_case",
    "structural_stress_test",
}
RETRY_FORMAT_INSTRUCTIONS = (
    "FORMAT RETRY: Return exactly one raw JSON object matching the WITNESS schema "
    "or exactly NOT_SUITABLE. Do not use Markdown or code fences. Do not add commentary. "
    "Escape every backslash inside JSON strings (for example, use \\\\frac or \\\\( for LaTeX); "
    "prefer plain-text notation with no backslashes when possible."
)


def render_prompt(template: str, problem: str, verified_solution: str) -> str:
    missing = [placeholder for placeholder in ("{problem}", "{verified_solution}") if placeholder not in template]
    if missing:
        raise ValueError(f"WITNESS prompt is missing placeholders: {', '.join(missing)}")
    return template.replace("{problem}", problem).replace("{verified_solution}", verified_solution)


def load_records(input_path: Path, prompt_path: Path) -> tuple[list[dict[str, Any]], str]:
    try:
        template = prompt_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ValueError(f"Prompt file does not exist: {prompt_path}") from exc
    render_prompt(template, "validation problem", "validation solution")
    records = read_json(input_path).get("problems")
    if not isinstance(records, list):
        raise ValueError(f"{input_path} must contain a 'problems' list")

    selected: list[dict[str, Any]] = []
    seen: set[int] = set()
    for position, record in enumerate(records):
        if not isinstance(record, dict):
            continue
        if record.get("answer_status") != "correct" or record.get("solve_status") != "completed":
            continue
        source_index = record.get("source_index", position)
        if not isinstance(source_index, int) or source_index in seen:
            raise ValueError(f"Invalid or duplicate source_index in {input_path}: {source_index!r}")
        if not isinstance(record.get("question"), str) or not record["question"].strip():
            raise ValueError(f"Completed problem {source_index} lacks question")
        if not isinstance(record.get("solve_solution"), str) or not record["solve_solution"].strip():
            raise ValueError(f"Completed problem {source_index} lacks solve_solution")
        seen.add(source_index)
        selected.append({**record, "source_index": source_index})
    if not selected:
        raise ValueError("No verified completed records were found")
    selected.sort(key=lambda record: record["source_index"])
    return selected, template


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _strings(value: Any, field: str) -> None:
    _require(isinstance(value, list), f"{field} must be a list")
    _require(all(isinstance(item, str) and item.strip() for item in value), f"{field} must contain non-empty strings")


def validate_output(value: Any) -> dict[str, Any] | str:
    if value == "NOT_SUITABLE":
        return value
    _require(isinstance(value, dict), "model output must be a JSON object or NOT_SUITABLE")
    _require(set(value) == TOP_LEVEL_KEYS, "model output has the wrong top-level schema")
    _require(value["transformation_type"] in TRANSFORMATION_TYPES, "invalid transformation_type")
    for field in ("load_bearing_feature", "connection_to_source"):
        _require(isinstance(value[field], str) and value[field].strip(), f"{field} must be non-empty")

    task = value["student_facing_task"]
    _require(isinstance(task, dict) and set(task) == TASK_KEYS, "student_facing_task has the wrong schema")
    for field in ("source_problem", "witness_request", "response_instruction"):
        _require(isinstance(task[field], str) and task[field].strip(), f"student_facing_task.{field} must be non-empty")
    _strings(task["relevant_context"], "student_facing_task.relevant_context")

    reference = value["reference_witness"]
    _require(isinstance(reference, dict) and set(reference) == REFERENCE_KEYS, "reference_witness has the wrong schema")
    for field in REFERENCE_KEYS:
        _require(isinstance(reference[field], str) and reference[field].strip(), f"reference_witness.{field} must be non-empty")

    rubric = value["evaluation_rubric"]
    _require(isinstance(rubric, dict) and set(rubric) == RUBRIC_KEYS, "evaluation_rubric has the wrong schema")
    for field in ("object_type", "required_phenomenon", "acceptable_variation"):
        _require(isinstance(rubric[field], str) and rubric[field].strip(), f"evaluation_rubric.{field} must be non-empty")
    _strings(rubric["required_conditions"], "evaluation_rubric.required_conditions")
    _strings(rubric["material_errors"], "evaluation_rubric.material_errors")

    checks = value["quality_checks"]
    _require(isinstance(checks, dict) and set(checks) == QUALITY_KEYS, "quality_checks has the wrong schema")
    _require(all(isinstance(checks[field], bool) for field in QUALITY_KEYS), "quality_checks values must be booleans")
    return value


def parse_and_validate(response: str) -> tuple[dict[str, Any] | str, str]:
    text = response.strip()
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", text, flags=re.IGNORECASE | re.DOTALL)
    if fenced:
        text = fenced.group(1).strip()
        method = "stripped_outer_json_code_fence"
    else:
        if text.startswith("```") or text.endswith("```"):
            raise ValueError("malformed JSON code fence")
        method = "raw_json"
    if text == "NOT_SUITABLE":
        return "NOT_SUITABLE", method
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"malformed JSON: {exc.msg}") from exc
    return validate_output(value), method


def load_project_environment(env_path: Path) -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        if env_path.exists():
            for raw_line in env_path.read_text(encoding="utf-8").splitlines():
                line = raw_line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ.setdefault(key.strip(), value.strip().strip("\"'"))
    else:
        load_dotenv(env_path)


def initialize_output(output_path: Path) -> dict[str, Any]:
    if not output_path.exists():
        return {"metadata": {}, "items": [], "failures": []}
    try:
        output = read_json(output_path)
    except ValueError:
        return {"metadata": {}, "items": [], "failures": []}
    if not isinstance(output.get("items"), list):
        return {"metadata": {}, "items": [], "failures": []}
    output.setdefault("failures", [])
    return output


def _usage_summary(output: dict[str, Any]) -> dict[str, Any]:
    prompt = completion = total = 0
    records = 0
    provider_cost = 0.0
    provider_records = 0
    for detail in output.get("metadata", {}).get("generation_details", {}).values():
        cost = usage_cost(detail.get("usage") if isinstance(detail, dict) else None)
        if cost["total_tokens"] is not None:
            records += 1
            prompt += cost["prompt_tokens"] or 0
            completion += cost["completion_tokens"] or 0
            total += cost["total_tokens"] or 0
        if cost["provider_estimated_cost_usd"] is not None:
            provider_records += 1
            provider_cost += cost["provider_estimated_cost_usd"]
    return {
        "records_with_usage": records,
        "prompt_tokens": prompt if records else None,
        "completion_tokens": completion if records else None,
        "total_tokens": total if records else None,
        "calculated_cost_usd": total * OUTPUT_PRICE_PER_MILLION / 1_000_000 if records else None,
        "provider_estimated_cost_usd": provider_cost if provider_records else None,
    }


def render_report(output: dict[str, Any], selected_count: int) -> str:
    items = output.get("items", [])
    suitable = sum(item.get("output") != "NOT_SUITABLE" for item in items)
    not_suitable = sum(item.get("output") == "NOT_SUITABLE" for item in items)
    failures = output.get("failures", [])
    usage = output.get("metadata", {}).get("usage_summary", {})
    lines = [
        "WITNESS-v1 DeepSeek generation",
        f"Selected verified solutions: {selected_count}",
        f"Schema-valid outputs: {len(items)}",
        f"Valid WITNESS tasks: {suitable}",
        f"NOT_SUITABLE: {not_suitable}",
        f"Schema/API failures: {len(failures)}",
        f"Elapsed seconds: {output.get('metadata', {}).get('elapsed_seconds')}",
        f"Prompt tokens: {usage.get('prompt_tokens')}",
        f"Completion tokens: {usage.get('completion_tokens')}",
        f"Total tokens: {usage.get('total_tokens')}",
        f"Calculated output cost USD: {usage.get('calculated_cost_usd')}",
        f"Provider-reported cost USD: {usage.get('provider_estimated_cost_usd')}",
    ]
    if failures:
        lines.append("Failures:")
        lines.extend(f"- source_index {item['source_index']}: {item['error']}" for item in failures)
    return "\n".join(lines) + "\n"


def run_generation(args: argparse.Namespace, client: Any) -> dict[str, Any]:
    started_at = datetime.now(timezone.utc)
    started_clock = time.perf_counter()
    selected, template = load_records(args.input, args.prompt)
    output = initialize_output(args.output)
    metadata = output.setdefault("metadata", {})
    metadata.update(
        {
            "schema": "witness_v1_batch",
            "prompt_version": "v1",
            "model": args.model,
            "reasoning_effort": REASONING_EFFORT,
            "prompt_file": str(args.prompt),
            "input_file": str(args.input),
            "prompt_sha256": hashlib.sha256(template.encode("utf-8")).hexdigest(),
            "selected_source_indices": [record["source_index"] for record in selected],
            "max_tokens": args.max_tokens,
            "timeout_seconds": args.timeout,
            "concurrency": args.concurrency,
            "stream": True,
            "schema_only_validation": True,
            "automatic_retries": False,
        }
    )
    saved = {item["source_index"]: item for item in output["items"] if isinstance(item, dict) and isinstance(item.get("source_index"), int)}
    previous_failures = {item.get("source_index") for item in output.get("failures", []) if isinstance(item, dict)}
    output["failures"] = []
    pending: dict[Any, tuple[int, dict[str, Any], int]] = {}

    def request(position: int, record: dict[str, Any], prompt: str) -> tuple[str, str | None, str | None, dict[str, Any] | None, float]:
        request_clock = time.perf_counter()
        result = stream_solution(client, args.model, prompt, args.max_tokens, REASONING_EFFORT)
        return (*result, round(time.perf_counter() - request_clock, 3))

    with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        for position, record in enumerate(selected, start=1):
            existing = saved.get(record["source_index"])
            if existing is not None and "output" in existing:
                try:
                    parse_and_validate(existing["output"] if existing["output"] == "NOT_SUITABLE" else json.dumps(existing["output"]))
                    print(f"[{position}/{len(selected)}] skipped (existing schema-valid output)")
                    continue
                except ValueError:
                    output["items"] = [item for item in output["items"] if item.get("source_index") != record["source_index"]]
            if record["source_index"] in previous_failures and not args.retry_failed:
                print(f"[{position}/{len(selected)}] skipped (previous failure; use --retry-failed)")
                continue
            prompt = render_prompt(template, record["question"], record["solve_solution"])
            if args.retry_failed and record["source_index"] in previous_failures:
                prompt = f"{prompt}\n\n{RETRY_FORMAT_INSTRUCTIONS}"
            batch_number = (position - 1) // args.concurrency + 1
            future = executor.submit(request, position, record, prompt)
            pending[future] = (position, record, batch_number)
            print(f"[{position}/{len(selected)}] queued (batch {batch_number})")

        for future in as_completed(pending):
            position, record, batch_number = pending[future]
            source_index = record["source_index"]
            response_text: str | None = None
            try:
                response, reasoning, finish_reason, usage, request_seconds = future.result()
                response_text = response
                parsed, normalization_method = parse_and_validate(response)
                output["items"] = [item for item in output["items"] if item.get("source_index") != source_index]
                output["items"].append({"source_index": source_index, "output": parsed})
                output["items"].sort(key=lambda item: item["source_index"])
                metadata.setdefault("generation_details", {})[str(source_index)] = {
                    "status": "completed",
                    "batch_number": batch_number,
                    "request_elapsed_seconds": request_seconds,
                    "finish_reason": finish_reason,
                    "usage": usage,
                    "reasoning": reasoning,
                    "normalization_method": normalization_method,
                }
                print(f"[{position}/{len(selected)}] completed ({'not_suitable' if parsed == 'NOT_SUITABLE' else 'task'}, {request_seconds}s)")
            except Exception as error:
                output["failures"].append(
                    {
                        "source_index": source_index,
                        "batch_number": batch_number,
                        "error": f"{error.__class__.__name__}: {error}",
                        "raw_response": response_text,
                    }
                )
                print(f"[{position}/{len(selected)}] failed: {error.__class__.__name__}: {error}")
            finally:
                atomic_write_json(args.output, output)

    metadata["started_at_utc"] = started_at.isoformat()
    metadata["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
    metadata["elapsed_seconds"] = round(time.perf_counter() - started_clock, 3)
    metadata["usage_summary"] = _usage_summary(output)
    metadata["counts"] = {
        "selected": len(selected),
        "schema_valid": len(output["items"]),
        "valid_tasks": sum(item.get("output") != "NOT_SUITABLE" for item in output["items"]),
        "not_suitable": sum(item.get("output") == "NOT_SUITABLE" for item in output["items"]),
        "failed": len(output["failures"]),
    }
    atomic_write_json(args.output, output)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(render_report(output, len(selected)), encoding="utf-8")
    print(f"Finished: {len(output['items'])}/{len(selected)} schema-valid outputs; report: {args.report}")
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
    parser.add_argument("--retry-failed", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.max_tokens < 1 or args.timeout <= 0 or args.concurrency < 1:
        raise ValueError("max-tokens, timeout, and concurrency must be positive")
    selected, _ = load_records(args.input, args.prompt)
    if args.dry_run:
        print(f"Verified completed records: {len(selected)}")
        print(f"Model: {args.model}")
        print(f"Reasoning effort: {REASONING_EFFORT}")
        print(f"Streaming: True; concurrency: {args.concurrency}; timeout: {args.timeout:g}s")
        print(f"Maximum output-only cost: ${len(selected) * args.max_tokens * OUTPUT_PRICE_PER_MILLION / 1_000_000:.4f}")
        return
    load_project_environment(ROOT_DIR / ".env")
    api_key = os.getenv("DEEPINFRA_API_KEY")
    if not api_key:
        raise RuntimeError("DEEPINFRA_API_KEY is not set in .env or the environment")
    run_generation(args, create_client(api_key, args.timeout))


if __name__ == "__main__":
    main()
