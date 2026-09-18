"""Judge Qwen WITNESS responses with DeepSeek V4 Flash on DeepInfra."""

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

from .paths import ARTIFACTS_DIR, ENV_FILE, MANIFESTS_DIR, PROMPTS_DIR, PROJECT_ROOT
from .solution_verification import usage_cost
from .solve_deepseek_flash import StreamInterruptedError, create_client, stream_solution
from .storage import atomic_write_json, read_json


ROOT_DIR = PROJECT_ROOT
DEFAULT_QWEN_INPUT = ARTIFACTS_DIR / "qwen3-4b" / "witness" / "v1-112" / "results.json"
DEFAULT_WITNESS_INPUT = ARTIFACTS_DIR / "deepseek-v4-flash" / "witness" / "v1-113" / "results.json"
DEFAULT_SOURCE_INPUT = MANIFESTS_DIR / "deepmath" / "deepmath-pilot-113-deepseek-v2-correct-explain-v2.json"
DEFAULT_PROMPT = PROMPTS_DIR / "witness" / "witness_eval.txt"
DEFAULT_OUTPUT = ARTIFACTS_DIR / "deepseek-v4-flash" / "witness-eval" / "v1-111" / "results.json"
DEFAULT_REPORT = ARTIFACTS_DIR / "deepseek-v4-flash" / "witness-eval" / "v1-111" / "report.txt"
DEFAULT_MODEL = "deepseek-ai/DeepSeek-V4-Flash-0731"
REASONING_EFFORT = "high"
DEFAULT_MAX_TOKENS = 16384
DEFAULT_TIMEOUT_SECONDS = 900.0
DEFAULT_CONCURRENCY = 20
INPUT_PRICE_PER_MILLION = 0.08
OUTPUT_PRICE_PER_MILLION = 0.18

JUDGE_KEYS = {
    "well_definedness",
    "constraint_satisfaction",
    "required_phenomenon",
    "verification_correct",
    "overall_witness",
    "brief_reason",
}
PASS_FAIL_KEYS = ("well_definedness", "constraint_satisfaction", "required_phenomenon", "verification_correct")
JUDGE_PLACEHOLDERS = (
    "{source_problem}",
    "{verified_source_solution}",
    "{relevant_context}",
    "{witness_request}",
    "{hidden_rubric}",
    "{reference_witness}",
    "{reference_verification}",
    "{student_response}",
)


def load_prompt(prompt_path: Path = DEFAULT_PROMPT) -> str:
    try:
        template = prompt_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ValueError(f"WITNESS evaluator prompt does not exist: {prompt_path}") from exc
    if not template.strip():
        raise ValueError(f"WITNESS evaluator prompt is empty: {prompt_path}")
    missing = [placeholder for placeholder in JUDGE_PLACEHOLDERS if placeholder not in template]
    if missing:
        raise ValueError(f"WITNESS evaluator prompt is missing placeholders: {', '.join(missing)}")
    return template


def _json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)


def load_records(
    qwen_path: Path,
    witness_path: Path,
    source_path: Path,
) -> tuple[list[dict[str, Any]], list[int]]:
    """Join Qwen, generated-task, and verified-source records by source_index."""
    qwen = read_json(qwen_path).get("results")
    witness = read_json(witness_path).get("items")
    source = read_json(source_path).get("problems")
    if not isinstance(qwen, list) or not isinstance(witness, list) or not isinstance(source, list):
        raise ValueError("Qwen, WITNESS, and source inputs must contain results/items/problems lists")

    witness_by_index: dict[int, dict[str, Any]] = {}
    for item in witness:
        if not isinstance(item, dict) or not isinstance(item.get("source_index"), int):
            raise ValueError("WITNESS artifact contains an invalid source_index")
        if item["source_index"] in witness_by_index:
            raise ValueError(f"WITNESS source_index is duplicated: {item['source_index']}")
        witness_by_index[item["source_index"]] = item
    source_by_index: dict[int, dict[str, Any]] = {}
    for item in source:
        if not isinstance(item, dict) or not isinstance(item.get("source_index"), int):
            raise ValueError("source manifest contains an invalid source_index")
        source_by_index[item["source_index"]] = item

    selected: list[dict[str, Any]] = []
    excluded: list[int] = []
    seen: set[int] = set()
    for item in qwen:
        if not isinstance(item, dict) or not isinstance(item.get("source_index"), int):
            raise ValueError("Qwen artifact contains an invalid source_index")
        index = item["source_index"]
        if index in seen:
            raise ValueError(f"Qwen source_index is duplicated: {index}")
        seen.add(index)
        if item.get("status") != "completed" or item.get("format_valid") is not True:
            excluded.append(index)
            continue
        generated = witness_by_index.get(index)
        source_record = source_by_index.get(index)
        if not isinstance(generated, dict) or not isinstance(source_record, dict):
            raise ValueError(f"source_index {index} is not aligned across all input artifacts")
        output = generated.get("output")
        task = output.get("student_facing_task") if isinstance(output, dict) else None
        if not isinstance(task, dict):
            raise ValueError(f"source_index {index} has no generated student task")
        required_task_fields = ("source_problem", "relevant_context", "witness_request", "response_instruction")
        if any(field not in task for field in required_task_fields):
            raise ValueError(f"source_index {index} has incomplete generated student task")
        if not isinstance(source_record.get("question"), str) or not source_record["question"].strip():
            raise ValueError(f"source_index {index} has no verified source problem")
        if not isinstance(source_record.get("solve_solution"), str) or not source_record["solve_solution"].strip():
            raise ValueError(f"source_index {index} has no verified source solution")
        response = item.get("response")
        if not isinstance(response, str) or not response.strip():
            raise ValueError(f"source_index {index} has no Qwen response")
        selected.append(
            {
                "source_index": index,
                "source_problem": source_record["question"],
                "verified_source_solution": source_record["solve_solution"],
                "relevant_context": task["relevant_context"],
                "witness_request": task["witness_request"],
                "hidden_rubric": output["evaluation_rubric"],
                "reference_witness": output["reference_witness"]["object"],
                "reference_verification": output["reference_witness"]["verification"],
                "student_response": response,
            }
        )
    selected.sort(key=lambda item: item["source_index"])
    if not selected:
        raise ValueError("No format-valid Qwen WITNESS responses are available")
    return selected, sorted(excluded)


def render_prompt(template: str, record: dict[str, Any]) -> str:
    values = {
        "source_problem": record["source_problem"],
        "verified_source_solution": record["verified_source_solution"],
        "relevant_context": "\n".join(f"- {fact}" for fact in record["relevant_context"]),
        "witness_request": record["witness_request"],
        "hidden_rubric": _json_text(record["hidden_rubric"]),
        "reference_witness": record["reference_witness"],
        "reference_verification": record["reference_verification"],
        "student_response": record["student_response"],
    }
    rendered = template
    for key, value in values.items():
        rendered = rendered.replace("{" + key + "}", value)
    return rendered


def _word_count(value: str) -> int:
    return len(re.findall(r"\S+", value))


def parse_judge_response(response: str) -> dict[str, str]:
    if not isinstance(response, str) or not response.strip():
        raise ValueError("judge response is empty")
    try:
        value = json.loads(response)
    except json.JSONDecodeError as exc:
        raise ValueError(f"judge response is not raw JSON: {exc.msg}") from exc
    if not isinstance(value, dict) or set(value) != JUDGE_KEYS:
        raise ValueError("judge response has the wrong exact schema")
    for field in PASS_FAIL_KEYS:
        if value[field] not in {"PASS", "FAIL"}:
            raise ValueError(f"{field} must be PASS or FAIL")
    if value["overall_witness"] not in {"VALID", "INVALID"}:
        raise ValueError("overall_witness must be VALID or INVALID")
    if not isinstance(value["brief_reason"], str) or not value["brief_reason"].strip():
        raise ValueError("brief_reason must be nonempty")
    if _word_count(value["brief_reason"]) > 80:
        raise ValueError("brief_reason must contain at most 80 words")
    expected = "VALID" if all(value[field] == "PASS" for field in PASS_FAIL_KEYS) else "INVALID"
    if value["overall_witness"] != expected:
        raise ValueError("overall_witness contradicts component decisions")
    return value


def initialize_output(output_path: Path, selected: list[dict[str, Any]]) -> dict[str, Any]:
    if not output_path.exists():
        return {"metadata": {}, "items": [], "failures": []}
    output = read_json(output_path)
    if not isinstance(output.get("items"), list) or not isinstance(output.get("failures"), list):
        raise ValueError("Existing evaluator output has invalid items/failures fields")
    saved_indices = {item.get("source_index") for item in output["items"] if isinstance(item, dict)}
    if not saved_indices.issubset({item["source_index"] for item in selected}):
        raise ValueError("Existing evaluator output contains an unexpected source_index")
    return output


def _usage_summary(output: dict[str, Any]) -> dict[str, Any]:
    prompt = completion = total = records = 0
    calculated = provider = 0.0
    provider_records = 0
    for detail in output.get("metadata", {}).get("generation_details", {}).values():
        cost = usage_cost(detail.get("usage") if isinstance(detail, dict) else None)
        if cost["total_tokens"] is not None:
            records += 1
            prompt += cost["prompt_tokens"] or 0
            completion += cost["completion_tokens"] or 0
            total += cost["total_tokens"] or 0
            calculated += cost["calculated_cost_usd"] or 0.0
        if cost["provider_estimated_cost_usd"] is not None:
            provider_records += 1
            provider += cost["provider_estimated_cost_usd"]
    return {
        "records_with_usage": records,
        "prompt_tokens": prompt if records else None,
        "completion_tokens": completion if records else None,
        "total_tokens": total if records else None,
        "calculated_cost_usd": calculated if records else None,
        "provider_estimated_cost_usd": provider if provider_records else None,
    }


def render_report(output: dict[str, Any], selected_count: int) -> str:
    items = output.get("items", [])
    failures = output.get("failures", [])
    parsed = [item for item in items if item.get("status") == "completed" and isinstance(item.get("judge_output"), dict)]
    overall_valid = sum(item["judge_output"]["overall_witness"] == "VALID" for item in parsed)
    lines = [
        "DeepSeek V4 Flash WITNESS judge",
        f"Selected format-valid Qwen responses: {selected_count}",
        f"Valid judge outputs: {len(parsed)}/{selected_count}",
        f"Overall VALID: {overall_valid}/{selected_count} ({overall_valid / selected_count:.2%})" if selected_count else "Overall VALID: 0/0",
    ]
    for field in (*PASS_FAIL_KEYS, "overall_witness"):
        if field == "overall_witness":
            continue
        passed = sum(item["judge_output"][field] == "PASS" for item in parsed)
        lines.append(f"{field} PASS: {passed}/{selected_count} ({passed / selected_count:.2%})" if selected_count else f"{field} PASS: 0/0")
    lines.extend(
        [
            f"Judge/API/schema failures: {len(failures)}",
            f"Elapsed seconds: {output.get('metadata', {}).get('elapsed_seconds')}",
            f"Prompt tokens: {output.get('metadata', {}).get('usage_summary', {}).get('prompt_tokens')}",
            f"Completion tokens: {output.get('metadata', {}).get('usage_summary', {}).get('completion_tokens')}",
            f"Total tokens: {output.get('metadata', {}).get('usage_summary', {}).get('total_tokens')}",
            f"Calculated cost USD: {output.get('metadata', {}).get('usage_summary', {}).get('calculated_cost_usd')}",
            f"Provider-reported cost USD: {output.get('metadata', {}).get('usage_summary', {}).get('provider_estimated_cost_usd')}",
            "",
            "Per-task verdicts",
        ]
    )
    for item in sorted(items, key=lambda value: value.get("source_index", -1)):
        verdict = item.get("judge_output", {}).get("overall_witness", item.get("status"))
        reason = item.get("judge_output", {}).get("brief_reason", item.get("error", ""))
        lines.append(f"source_index {item.get('source_index')}: {verdict} — {reason}")
    return "\n".join(lines) + "\n"


def run_generation(args: argparse.Namespace, client: Any) -> dict[str, Any]:
    started_at = datetime.now(timezone.utc)
    started_clock = time.perf_counter()
    template = load_prompt(args.prompt)
    selected, excluded = load_records(args.qwen_input, args.witness_input, args.source_input)
    output = initialize_output(args.output, selected)
    metadata = output.setdefault("metadata", {})
    metadata.update(
        {
            "schema": "witness_judge_v1_batch",
            "model": args.model,
            "reasoning_effort": REASONING_EFFORT,
            "prompt_file": str(args.prompt),
            "prompt_sha256": hashlib.sha256(template.encode("utf-8")).hexdigest(),
            "qwen_input": str(args.qwen_input),
            "witness_input": str(args.witness_input),
            "source_input": str(args.source_input),
            "selected_source_indices": [record["source_index"] for record in selected],
            "excluded_source_indices": excluded,
            "max_tokens": args.max_tokens,
            "timeout_seconds": args.timeout,
            "concurrency": args.concurrency,
            "stream": True,
            "judge_schema": sorted(JUDGE_KEYS),
            "automatic_retries": False,
        }
    )
    saved = {item["source_index"]: item for item in output["items"] if isinstance(item, dict) and isinstance(item.get("source_index"), int)}
    previous_failures = {item.get("source_index") for item in output["failures"] if isinstance(item, dict)}
    output["failures"] = []
    pending: dict[Any, tuple[int, dict[str, Any]]] = {}

    def request(record: dict[str, Any]) -> tuple[str, str | None, str | None, dict[str, Any] | None, float]:
        request_clock = time.perf_counter()
        result = stream_solution(client, args.model, render_prompt(template, record), args.max_tokens, REASONING_EFFORT)
        return (*result, round(time.perf_counter() - request_clock, 3))

    with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        for position, record in enumerate(selected, start=1):
            existing = saved.get(record["source_index"])
            if existing is not None and existing.get("status") == "completed":
                try:
                    parse_judge_response(existing["judge_response"])
                    print(f"[{position}/{len(selected)}] skipped (existing valid judge output)")
                    continue
                except (KeyError, ValueError):
                    output["items"] = [item for item in output["items"] if item.get("source_index") != record["source_index"]]
            if record["source_index"] in previous_failures and not args.retry_failed:
                print(f"[{position}/{len(selected)}] skipped (previous failure; use --retry-failed)")
                continue
            pending[executor.submit(request, record)] = (position, record)
            print(f"[{position}/{len(selected)}] queued")

        for future in as_completed(pending):
            position, record = pending[future]
            source_index = record["source_index"]
            response_text: str | None = None
            try:
                response, reasoning, finish_reason, usage, request_seconds = future.result()
                response_text = response
                parsed = parse_judge_response(response)
                output["items"] = [item for item in output["items"] if item.get("source_index") != source_index]
                output["items"].append(
                    {
                        "source_index": source_index,
                        "status": "completed",
                        "judge_response": response,
                        "judge_output": parsed,
                        "judge_reasoning": reasoning,
                        "finish_reason": finish_reason,
                        "usage": usage,
                        "request_elapsed_seconds": request_seconds,
                    }
                )
                output["items"].sort(key=lambda item: item["source_index"])
                metadata.setdefault("generation_details", {})[str(source_index)] = {
                    "status": "completed",
                    "request_elapsed_seconds": request_seconds,
                    "finish_reason": finish_reason,
                    "usage": usage,
                }
                print(f"[{position}/{len(selected)}] completed ({request_seconds}s)")
            except StreamInterruptedError as error:
                output["failures"].append(
                    {
                        "source_index": source_index,
                        "error": f"{error.__cause__.__class__.__name__}: {error}",
                        "raw_response": error.partial_solution or response_text,
                        "partial_reasoning": error.partial_reasoning or None,
                    }
                )
                print(f"[{position}/{len(selected)}] stream interrupted")
            except Exception as error:
                output["failures"].append(
                    {
                        "source_index": source_index,
                        "error": f"{error.__class__.__name__}: {error}",
                        "raw_response": response_text,
                    }
                )
                print(f"[{position}/{len(selected)}] rejected: {error}")
            finally:
                atomic_write_json(args.output, output)

    metadata["started_at_utc"] = started_at.isoformat()
    metadata["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
    metadata["elapsed_seconds"] = round(time.perf_counter() - started_clock, 3)
    metadata["usage_summary"] = _usage_summary(output)
    metadata["counts"] = {
        "selected": len(selected),
        "judge_valid": sum(item.get("status") == "completed" for item in output["items"]),
        "overall_valid": sum(item.get("judge_output", {}).get("overall_witness") == "VALID" for item in output["items"]),
        "failed": len(output["failures"]),
    }
    atomic_write_json(args.output, output)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(render_report(output, len(selected)), encoding="utf-8")
    print(f"Finished: {metadata['counts']['judge_valid']}/{len(selected)} valid judge outputs; report: {args.report}")
    return output


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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--qwen-input", type=Path, default=DEFAULT_QWEN_INPUT)
    parser.add_argument("--witness-input", type=Path, default=DEFAULT_WITNESS_INPUT)
    parser.add_argument("--source-input", type=Path, default=DEFAULT_SOURCE_INPUT)
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
    selected, excluded = load_records(args.qwen_input, args.witness_input, args.source_input)
    if args.dry_run:
        print(f"Format-valid Qwen WITNESS responses: {len(selected)}")
        print(f"Excluded Qwen responses: {excluded}")
        print(f"Model: {args.model}; reasoning effort: {REASONING_EFFORT}")
        print(f"Streaming: True; concurrency: {args.concurrency}; timeout: {args.timeout:g}s")
        return
    load_project_environment(ROOT_DIR / ".env")
    api_key = os.getenv("DEEPINFRA_API_KEY")
    if not api_key:
        raise RuntimeError("DEEPINFRA_API_KEY is not set in .env or the environment")
    run_generation(args, create_client(api_key, args.timeout))


if __name__ == "__main__":
    main()
