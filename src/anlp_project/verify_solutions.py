"""Verify DeepSeek SOLVE outputs against dataset gold final answers."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from .paths import ARTIFACTS_DIR, MANIFESTS_DIR, PROJECT_ROOT
from .solution_verification import verify_record, usage_cost
from .storage import atomic_write_json, read_json


ROOT_DIR = PROJECT_ROOT
DEFAULT_MANIFEST = MANIFESTS_DIR / "deepmath" / "deepmath-pilot-146.json"
DEFAULT_OUTPUT = ARTIFACTS_DIR / "deepseek-v4-flash" / "solve" / "146" / "results.json"
DEFAULT_REPORT = ARTIFACTS_DIR / "deepseek-v4-flash" / "solve" / "146" / "report.txt"


def load_manifest(path: Path) -> list[dict[str, Any]]:
    problems = read_json(path).get("problems")
    if not isinstance(problems, list) or not problems:
        raise ValueError(f"{path} must contain a non-empty problems list")
    indices = [problem.get("source_index") for problem in problems if isinstance(problem, dict)]
    if len(indices) != len(problems) or any(not isinstance(index, int) for index in indices):
        raise ValueError("manifest contains invalid source indices")
    if len(set(indices)) != len(indices):
        raise ValueError("manifest contains duplicate source indices")
    return problems


def load_solution_records(paths: list[Path]) -> dict[int, dict[str, Any]]:
    records: dict[int, dict[str, Any]] = {}
    for path in paths:
        data = read_json(path)
        problems = data.get("problems")
        if not isinstance(problems, list):
            raise ValueError(f"{path} must contain a problems list")
        for position, problem in enumerate(problems):
            if not isinstance(problem, dict):
                continue
            source_index = problem.get("source_index", position)
            if not isinstance(source_index, int):
                raise ValueError(f"invalid source index in {path}: {source_index!r}")
            if problem.get("solve_status") != "completed":
                continue
            # Files are processed in caller-specified order.  A later artifact
            # (for example, a one-time repair run) intentionally supersedes an
            # earlier solution for the same source index while raw artifacts
            # remain untouched on disk.
            records[source_index] = {**problem, "_solution_source": str(path)}
    return records


def _difficulty_band(value: Any) -> str:
    try:
        difficulty = float(value)
    except (TypeError, ValueError):
        return "unknown"
    if 5.0 <= difficulty <= 6.5:
        return "5.0-6.5"
    if 7.0 <= difficulty <= 8.0:
        return "7.0-8.0"
    return "other"


def verify_manifest(manifest_path: Path, solution_paths: list[Path], output_path: Path) -> dict[str, Any]:
    manifest = load_manifest(manifest_path)
    solutions = load_solution_records(solution_paths)
    merged: list[dict[str, Any]] = []
    for problem in manifest:
        source_index = problem["source_index"]
        solution = solutions.get(source_index)
        record = dict(problem)
        if solution is None:
            record.update({"solve_status": "failed", "solve_error": "no completed solution record"})
        else:
            record.update({key: value for key, value in solution.items() if key != "_solution_source"})
            record["solution_source"] = solution["_solution_source"]
        record.update(verify_record(record))
        record["solution_usage_cost"] = usage_cost(record.get("solve_usage"))
        merged.append(record)

    statuses = Counter(record["answer_status"] for record in merged)
    methods = Counter(record["verification_method"] for record in merged)
    reasons = Counter(
        record["verification_reason"]
        for record in merged
        if record.get("verification_reason")
    )
    costs = [record["solution_usage_cost"] for record in merged]
    prompt_tokens = sum(cost["prompt_tokens"] or 0 for cost in costs)
    completion_tokens = sum(cost["completion_tokens"] or 0 for cost in costs)
    calculated_cost = sum(cost["calculated_cost_usd"] or 0.0 for cost in costs)
    provider_costs = [cost["provider_estimated_cost_usd"] for cost in costs if cost["provider_estimated_cost_usd"] is not None]
    metadata = {
        "schema": "deepseek_solve_verification_v2",
        "manifest": str(manifest_path),
        "solution_files": [str(path) for path in solution_paths],
        "record_count": len(merged),
        "status_counts": dict(sorted(statuses.items())),
        "verification_method_counts": dict(sorted(methods.items())),
        "verification_reason_counts": dict(sorted(reasons.items())),
        "strict_accuracy": statuses["correct"] / len(merged) if merged else 0.0,
        "parseable_accuracy": statuses["correct"] / (statuses["correct"] + statuses["incorrect"])
        if statuses["correct"] + statuses["incorrect"]
        else None,
        "verification_coverage": (statuses["correct"] + statuses["incorrect"]) / len(merged)
        if merged
        else 0.0,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "calculated_cost_usd": calculated_cost,
        "provider_estimated_cost_usd": sum(provider_costs) if provider_costs else None,
    }
    output = {"metadata": metadata, "problems": merged}
    atomic_write_json(output_path, output)
    return output


def render_report(output: dict[str, Any]) -> str:
    records = output["problems"]
    metadata = output["metadata"]
    lines = [
        "DeepSeek SOLVE deterministic verification",
        f"Records: {len(records)}",
        f"Correct: {metadata['status_counts'].get('correct', 0)}",
        f"Incorrect: {metadata['status_counts'].get('incorrect', 0)}",
        f"Missing: {metadata['status_counts'].get('missing', 0)}",
        f"Unverified: {metadata['status_counts'].get('unverified', 0)}",
        f"Strict accuracy: {metadata['strict_accuracy']:.4f}",
        f"Parseable accuracy: {metadata['parseable_accuracy']!s}",
        f"Verification coverage: {metadata['verification_coverage']:.4f}",
        "",
        "Verification methods",
    ]
    for method, count in metadata.get("verification_method_counts", {}).items():
        lines.append(f"  {method}: {count}")
    lines.extend([
        "",
        "Verification reasons",
    ])
    for reason, count in metadata.get("verification_reason_counts", {}).items():
        lines.append(f"  {reason}: {count}")
    lines.extend([
        "",
        "Token and cost totals",
        f"Prompt tokens: {metadata['prompt_tokens']}",
        f"Completion tokens: {metadata['completion_tokens']}",
        f"Calculated cost USD: {metadata['calculated_cost_usd']:.8f}",
        f"Provider estimated cost USD: {metadata['provider_estimated_cost_usd']!s}",
        "",
        "Breakdowns",
    ])
    dimensions = {
        "topic": lambda record: record.get("topic", "unknown"),
        "difficulty": lambda record: _difficulty_band(record.get("difficulty")),
    }
    for name, key_fn in dimensions.items():
        lines.append(f"By {name}:")
        groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for record in records:
            groups[str(key_fn(record))].append(record)
        for key in sorted(groups):
            group = groups[key]
            correct = sum(record["answer_status"] == "correct" for record in group)
            lines.append(f"  {key}: {correct}/{len(group)} strict={correct / len(group):.4f}")
    lines.extend(["", "Per-problem results"])
    for record in records:
        lines.append(
            "{source_index}\t{source_id}\t{answer_status}\t{method}\t{reason}\tgold={gold!r}\textracted={extracted!r}".format(
                source_index=record["source_index"],
                source_id=record.get("source_id", ""),
                answer_status=record["answer_status"],
                method=record.get("verification_method", ""),
                reason=record.get("verification_reason", ""),
                gold=record.get("final_answer", ""),
                extracted=record.get("extracted_final_answer"),
            )
        )
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--solutions", type=Path, nargs="+", required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    result = verify_manifest(args.manifest, args.solutions, args.output)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(render_report(result), encoding="utf-8")
    print(f"wrote verification output to {args.output}")
    print(f"wrote verification report to {args.report}")
