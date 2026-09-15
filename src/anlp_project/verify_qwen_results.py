"""Apply the shared deterministic verifier to retrieved Qwen SOLVE outputs."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from .solution_verification import verify_record
from .storage import atomic_write_json, read_json


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


def verify_qwen_results(input_path: Path, output_path: Path) -> dict[str, Any]:
    raw = read_json(input_path)
    results = raw.get("results")
    if not isinstance(results, list) or not results:
        raise ValueError(f"{input_path} must contain a non-empty results list")
    verified: list[dict[str, Any]] = []
    for item in results:
        if not isinstance(item, dict):
            raise ValueError("Qwen results contain a non-object item")
        record = dict(item)
        if record.get("status") == "completed":
            record["solve_solution"] = record.get("response", "")
        else:
            record["solve_solution"] = ""
            record["solve_error"] = record.get("error", "generation_failed")
        detail = verify_record(record)
        record.update(detail)
        record["verification"] = (
            "missing_final_answer" if detail["answer_status"] == "missing" else detail["answer_status"]
        )
        verified.append(record)

    status_counts = Counter(record["answer_status"] for record in verified)
    method_counts = Counter(record["verification_method"] for record in verified)
    reason_counts = Counter(record["verification_reason"] for record in verified if record.get("verification_reason"))
    parseable = status_counts["correct"] + status_counts["incorrect"]
    metadata = {
        "schema": "qwen3_4b_solve_verification_v2",
        "raw_results": str(input_path),
        "record_count": len(verified),
        "status_counts": dict(sorted(status_counts.items())),
        "verification_method_counts": dict(sorted(method_counts.items())),
        "verification_reason_counts": dict(sorted(reason_counts.items())),
        "strict_accuracy": status_counts["correct"] / len(verified),
        "parseable_accuracy": status_counts["correct"] / parseable if parseable else None,
        "verification_coverage": parseable / len(verified),
        "generation_failure_count": sum(
            record.get("status") != "completed" for record in verified
        ),
        "raw_metadata": raw.get("metadata", {}),
    }
    output = {"metadata": metadata, "results": verified}
    atomic_write_json(output_path, output)
    return output


def render_report(output: dict[str, Any]) -> str:
    records = output["results"]
    metadata = output["metadata"]
    raw_metadata = metadata.get("raw_metadata", {})
    lines = [
        "Qwen3-4B local deterministic SOLVE verification",
        f"Records: {len(records)}",
        f"Model: {raw_metadata.get('model', 'unknown')}",
        f"Slurm job: {raw_metadata.get('slurm_job_id', raw_metadata.get('job_id', 'unknown'))}",
        f"Node: {raw_metadata.get('hostname', 'unknown')}",
        f"GPU: {raw_metadata.get('gpu_name', 'unknown')}",
        f"Generation failures: {metadata.get('generation_failure_count', 0)}",
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
    lines.extend(f"  {key}: {value}" for key, value in metadata["verification_method_counts"].items())
    lines.extend(["", "Verification reasons"])
    lines.extend(f"  {key}: {value}" for key, value in metadata["verification_reason_counts"].items())
    lines.extend(["", "By topic:"])
    topic_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        topic_groups[str(record.get("topic", "unknown"))].append(record)
    for topic in sorted(topic_groups):
        group = topic_groups[topic]
        correct = sum(record["answer_status"] == "correct" for record in group)
        lines.append(f"  {topic}: {correct}/{len(group)} strict={correct / len(group):.4f}")
    lines.append("By difficulty:")
    difficulty_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        difficulty_groups[_difficulty_band(record.get("difficulty"))].append(record)
    for difficulty in sorted(difficulty_groups):
        group = difficulty_groups[difficulty]
        correct = sum(record["answer_status"] == "correct" for record in group)
        lines.append(f"  {difficulty}: {correct}/{len(group)} strict={correct / len(group):.4f}")
    lines.extend(["", "Per-problem results"])
    for record in records:
        lines.append(
            "{source_index}\t{source_id}\t{answer_status}\t{method}\t{reason}\tgold={gold!r}\textracted={extracted!r}".format(
                source_index=record.get("source_index"),
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
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    result = verify_qwen_results(args.input, args.output)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(render_report(result), encoding="utf-8")
    print(f"wrote local Qwen verification to {args.output}")
    print(f"wrote report to {args.report}")
