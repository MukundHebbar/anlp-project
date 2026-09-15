"""Recover safely parseable EXPLAIN responses without making API requests."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from anlp_project.explain_deepseek_flash import parse_and_validate_detailed, render_report
from anlp_project.storage import atomic_write_json, read_json


def repair_output(source_path: Path, input_path: Path, output_path: Path, report_path: Path) -> dict[str, Any]:
    source = read_json(source_path).get("problems")
    if not isinstance(source, list):
        raise ValueError(f"{source_path} must contain a problems list")
    source_by_index = {
        record["source_index"]: record
        for record in source
        if isinstance(record, dict) and isinstance(record.get("source_index"), int)
    }

    output = read_json(input_path)
    items = output.get("items")
    failures = output.get("failures")
    if not isinstance(items, list) or not isinstance(failures, list):
        raise ValueError(f"{input_path} must contain items and failures lists")

    existing_indices = {item.get("source_index") for item in items if isinstance(item, dict)}
    unresolved: list[dict[str, Any]] = []
    recovered: list[dict[str, Any]] = []
    generation_details = output.setdefault("metadata", {}).setdefault("generation_details", {})
    for failure in failures:
        source_index = failure.get("source_index") if isinstance(failure, dict) else None
        raw_response = failure.get("raw_response") if isinstance(failure, dict) else None
        if not isinstance(source_index, int) or source_index not in source_by_index or not isinstance(raw_response, str):
            unresolved.append(failure)
            continue
        try:
            parsed, method = parse_and_validate_detailed(raw_response, source_by_index[source_index])
        except ValueError:
            unresolved.append(failure)
            continue
        if source_index in existing_indices:
            unresolved.append(failure)
            continue
        items.append({"source_index": source_index, "output": parsed})
        existing_indices.add(source_index)
        recovered.append(
            {
                "source_index": source_index,
                "normalization_method": method,
                "original_failure": failure,
            }
        )
        generation_details[str(source_index)] = {
            "status": "recovered_local",
            "normalization_method": method,
            "usage": None,
        }

    items.sort(key=lambda item: item["source_index"])
    output["failures"] = unresolved
    output["recovered_failures"] = recovered
    metadata = output.setdefault("metadata", {})
    metadata["recovery"] = {
        "performed": True,
        "without_api_request": True,
        "recovered_count": len(recovered),
        "unresolved_count": len(unresolved),
    }
    metadata["counts"] = {
        "selected": len(source),
        "valid_tasks": sum(item.get("output") != "NOT_SUITABLE" for item in items),
        "not_suitable": sum(item.get("output") == "NOT_SUITABLE" for item in items),
        "recovered_locally": len(recovered),
        "rejected_or_failed": len(unresolved),
    }
    atomic_write_json(output_path, output)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    version = str(metadata.get("prompt_version", "v1"))
    report_path.write_text(render_report(output, len(source), version), encoding="utf-8")
    return output


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    result = repair_output(args.source, args.input, args.output, args.report)
    print(
        f"Recovered {result['metadata']['recovery']['recovered_count']} responses; "
        f"left {result['metadata']['recovery']['unresolved_count']} unresolved"
    )
