"""Create a DeepSeek repair input for completed solutions without extractable answers."""

from __future__ import annotations

import argparse
from pathlib import Path

from .paths import PROJECT_ROOT
from .solution_verification import verify_record
from .storage import atomic_write_json, read_json


ROOT_DIR = PROJECT_ROOT


def build_repair_input(manifest_path: Path, solution_paths: list[Path], output_path: Path) -> None:
    manifest = read_json(manifest_path)
    problems = manifest.get("problems")
    if not isinstance(problems, list):
        raise ValueError(f"{manifest_path} must contain a problems list")
    solution_by_index = {}
    for path in solution_paths:
        data = read_json(path)
        for position, record in enumerate(data.get("problems", [])):
            if isinstance(record, dict) and record.get("solve_status") == "completed":
                solution_by_index[record.get("source_index", position)] = record

    selected = []
    for problem in problems:
        source_index = problem["source_index"]
        record = solution_by_index.get(source_index)
        if record is None:
            continue
        if verify_record(record)["answer_status"] == "missing":
            selected.append(problem)

    atomic_write_json(
        output_path,
        {
            "dataset": manifest.get("dataset"),
            "sample_size": len(selected),
            "metadata": {
                "purpose": "repair_missing_final_answers",
                "source_manifest": str(manifest_path),
                "source_solution_files": [str(path) for path in solution_paths],
            },
            "problems": selected,
        },
    )
    print(f"wrote {len(selected)} repair records to {output_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--solutions", type=Path, nargs="+", required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    build_repair_input(args.manifest, args.solutions, args.output)
