"""Combine validated EXPLAIN-v1 batch artifacts without losing provenance."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from anlp_project.storage import atomic_write_json, read_json


ROOT_DIR = Path(__file__).resolve().parents[2]
LEGACY_GENERATED_DIR = ROOT_DIR / "local" / "archive" / "legacy" / "generated"
DEFAULT_INPUTS = [
    LEGACY_GENERATED_DIR / "explanations" / "deepmath-pilot-24-completed-deepseek-v4-flash-medium-explain-23-valid.json",
    LEGACY_GENERATED_DIR / "explanations" / "deepmath-pilot-22-completed-deepseek-v4-flash-medium-explain-22-valid.json",
]
DEFAULT_OUTPUT = ROOT_DIR / "local" / "archive" / "deepmath-pilot-46-completed-deepseek-v4-flash-medium-explain-45-valid.json"


def load_batch(path: Path) -> dict[str, Any]:
    batch = read_json(path)
    if not isinstance(batch.get("metadata"), dict):
        raise ValueError(f"{path} must contain metadata as an object")
    items = batch.get("items")
    if not isinstance(items, list):
        raise ValueError(f"{path} must contain items as a list")
    failures = batch.get("failures", [])
    if not isinstance(failures, list):
        raise ValueError(f"{path} must contain failures as a list")
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get("source_index"), int):
            raise ValueError(f"{path} contains an item with an invalid source_index")
        output = item.get("output")
        if output != "NOT_SUITABLE" and not isinstance(output, dict):
            raise ValueError(f"{path} item {item['source_index']} has an invalid output")
    return batch


def combine_batches(input_paths: list[Path]) -> dict[str, Any]:
    if len(input_paths) < 2:
        raise ValueError("at least two EXPLAIN batch files are required")

    batches = [(path, load_batch(path)) for path in input_paths]
    items: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    seen: set[int] = set()
    for path, batch in batches:
        for item in batch["items"]:
            source_index = item["source_index"]
            if source_index in seen:
                raise ValueError(f"duplicate source_index across batches: {source_index}")
            seen.add(source_index)
            items.append(item)
        for failure in batch["failures"]:
            if not isinstance(failure, dict) or not isinstance(failure.get("source_index"), int):
                raise ValueError(f"{path} contains a failure with an invalid source_index")
            failures.append({**failure, "batch_file": str(path)})

    items.sort(key=lambda item: item["source_index"])
    failures.sort(key=lambda failure: failure["source_index"])
    suitable = sum(item["output"] != "NOT_SUITABLE" for item in items)
    not_suitable = len(items) - suitable
    models = {batch["metadata"].get("model") for _, batch in batches}
    reasoning = {batch["metadata"].get("reasoning_effort") for _, batch in batches}
    metadata = {
        "schema": "explain_v1_combined_batch",
        "model": next(iter(models)) if len(models) == 1 else sorted(str(model) for model in models),
        "reasoning_effort": next(iter(reasoning)) if len(reasoning) == 1 else sorted(str(value) for value in reasoning),
        "source_batches": [
            {
                "file": str(path),
                "schema": batch["metadata"].get("schema"),
                "selected_source_indices": batch["metadata"].get("selected_source_indices"),
                "item_count": len(batch["items"]),
                "failure_count": len(batch["failures"]),
            }
            for path, batch in batches
        ],
        "item_count": len(items),
        "valid_task_count": suitable,
        "not_suitable_count": not_suitable,
        "failure_count": len(failures),
        "source_indices": [item["source_index"] for item in items],
    }
    return {"metadata": metadata, "items": items, "failures": failures}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", dest="inputs", type=Path, action="append", default=None)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    inputs = args.inputs or DEFAULT_INPUTS
    combined = combine_batches(inputs)
    atomic_write_json(args.output, combined)
    print(f"Wrote {len(combined['items'])} items ({combined['metadata']['valid_task_count']} valid, {combined['metadata']['not_suitable_count']} NOT_SUITABLE) to {args.output}")


if __name__ == "__main__":
    main()
