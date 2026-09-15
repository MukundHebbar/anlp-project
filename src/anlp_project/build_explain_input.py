"""Build a private versioned EXPLAIN input from verifier-v2-correct solutions."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from .paths import PROMPTS_DIR
from .storage import atomic_write_json, read_json


REQUIRED_COUNT = 113
DEFAULT_PROMPT = PROMPTS_DIR / "explain" / "explain_v1.md"


def build_input(
    source_path: Path,
    output_path: Path,
    prompt_path: Path = DEFAULT_PROMPT,
    version: str = "v1",
) -> dict[str, Any]:
    source = read_json(source_path)
    records = source.get("problems")
    if not isinstance(records, list):
        raise ValueError(f"{source_path} must contain a problems list")

    selected = [
        dict(record)
        for record in records
        if isinstance(record, dict)
        and record.get("answer_status") == "correct"
        and record.get("solve_status") == "completed"
        and isinstance(record.get("solve_solution"), str)
        and record["solve_solution"].strip()
    ]
    if len(selected) != REQUIRED_COUNT:
        raise ValueError(f"expected {REQUIRED_COUNT} correct completed solutions, found {len(selected)}")
    source_ids = [record.get("source_id") for record in selected]
    if any(not isinstance(source_id, str) for source_id in source_ids):
        raise ValueError("all selected records must have source IDs")
    if len(set(source_ids)) != len(source_ids):
        raise ValueError("selected records must have unique source IDs")
    source_indices = [record.get("source_index") for record in selected]
    if any(not isinstance(index, int) for index in source_indices):
        raise ValueError("all selected records must have integer source indices")
    if len(set(source_indices)) != len(source_indices):
        raise ValueError("selected records must have unique source indices")

    selected.sort(key=lambda record: record["source_index"])
    output = {
        "dataset": source.get("dataset"),
        "sample_size": REQUIRED_COUNT,
        "metadata": {
            "purpose": f"deepseek_v4_flash_explain_{version}_generation",
            "selection": "answer_status=correct from deterministic verifier v2",
            "source_verification": str(source_path),
            "prompt_file": str(prompt_path),
            "prompt_version": version,
            "private_reference_solution_included_for_generation": True,
            "student_facing_task_must_exclude_reference_solution": True,
        },
        "problems": selected,
    }
    atomic_write_json(output_path, output)
    print(f"wrote {len(selected)} EXPLAIN input records to {output_path}")
    return output


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--prompt", type=Path, default=DEFAULT_PROMPT)
    parser.add_argument("--version", choices=("v1", "v2"), default="v1")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    build_input(args.source, args.output, args.prompt, args.version)
