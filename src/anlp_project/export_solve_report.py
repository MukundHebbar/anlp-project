"""Export completed SOLVE results as a readable text report."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from .paths import PROJECT_ROOT
from .storage import atomic_write_text, read_json

ROOT_DIR = PROJECT_ROOT


def completed_records(input_paths: list[Path]) -> list[dict[str, Any]]:
    records_by_index: dict[int, dict[str, Any]] = {}

    for path in input_paths:
        problems = read_json(path).get("problems")
        if not isinstance(problems, list):
            raise ValueError(f"{path} must contain a 'problems' list")

        for position, problem in enumerate(problems):
            if not isinstance(problem, dict) or problem.get("solve_status") != "completed":
                continue
            source_index = problem.get("source_index", position)
            if not isinstance(source_index, int):
                raise ValueError(f"Invalid source_index in {path}: {source_index!r}")
            if source_index in records_by_index:
                raise ValueError(f"Duplicate completed source index: {source_index}")

            required_fields = ("question", "solve_solution", "final_answer")
            missing = [field for field in required_fields if not problem.get(field)]
            if missing:
                raise ValueError(
                    f"Completed problem {source_index} in {path} is missing {missing}"
                )
            records_by_index[source_index] = problem

    return [records_by_index[index] for index in sorted(records_by_index)]


def render_report(records: list[dict[str, Any]]) -> str:
    models = sorted({str(record["solve_model"]) for record in records if record.get("solve_model")})
    model_label = ", ".join(models) if models else "unknown model"
    lines = [
        "DeepMath pilot SOLVE results",
        f"Model: {model_label}",
        f"Completed problems: {len(records)}",
        "",
    ]

    for number, problem in enumerate(records, start=1):
        source_index = problem.get("source_index", number - 1)
        lines.extend(
            [
                "=" * 80,
                f"Problem {number} (pilot index {source_index})",
                f"Topic: {problem.get('topic', 'unknown')}",
                f"Difficulty: {problem.get('difficulty', 'unknown')}",
                "",
                "Question:",
                str(problem["question"]).strip(),
                "",
                "Generated answer:",
                str(problem["solve_solution"]).strip(),
                "",
                "Verified final answer:",
                str(problem["final_answer"]).strip(),
                "",
            ]
        )

    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", type=Path, nargs="+", required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    records = completed_records(args.inputs)
    atomic_write_text(args.output, render_report(records))
    print(f"Wrote {len(records)} completed problems to {args.output}")


if __name__ == "__main__":
    main()
