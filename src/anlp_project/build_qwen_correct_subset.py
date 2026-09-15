"""Build the Qwen input subset from deterministic DeepSeek-v2 results."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from .storage import atomic_write_json, read_json


def _public_record(record: dict[str, Any]) -> dict[str, Any]:
    fields = ("source_index", "source_id", "question", "final_answer", "topic", "difficulty")
    return {field: record[field] for field in fields if field in record}


def build_subset(input_path: Path, output_path: Path, smoke_path: Path) -> None:
    source = read_json(input_path)
    records = source.get("problems")
    if not isinstance(records, list):
        raise ValueError(f"{input_path} must contain a problems list")
    selected = [_public_record(record) for record in records if record.get("answer_status") == "correct"]
    if len(selected) != 113:
        raise ValueError(f"expected 113 correct records, found {len(selected)}")
    source_ids = [record.get("source_id") for record in selected]
    if any(not isinstance(source_id, str) for source_id in source_ids) or len(set(source_ids)) != len(source_ids):
        raise ValueError("selected records must have unique source IDs")
    metadata = {
        "purpose": "qwen3_4b_solve_evaluation",
        "selection": "answer_status=correct from DeepSeek verifier v2",
        "source_verification": str(input_path),
        "gold_answers_used_only_for_local_post_generation_scoring": True,
        "deepseek_solution_text_included": False,
    }
    atomic_write_json(output_path, {"dataset": source.get("dataset"), "sample_size": 113, "metadata": metadata, "problems": selected})
    atomic_write_json(
        smoke_path,
        {"dataset": source.get("dataset"), "sample_size": 1, "metadata": {**metadata, "purpose": "qwen3_4b_solve_smoke"}, "problems": selected[:1]},
    )
    print(f"wrote {len(selected)} records to {output_path}")
    print(f"wrote 1 smoke record to {smoke_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--smoke-output", type=Path, required=True)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    build_subset(args.input, args.output, args.smoke_output)
