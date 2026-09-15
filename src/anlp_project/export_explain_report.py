"""Export completed EXPLAIN results as a readable text report."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from .storage import atomic_write_text, read_json


def completed_records(input_path: Path) -> list[dict[str, Any]]:
    problems = read_json(input_path).get("problems")
    if not isinstance(problems, list):
        raise ValueError(f"{input_path} must contain a 'problems' list")

    records = []
    for position, problem in enumerate(problems):
        if not isinstance(problem, dict) or problem.get("explain_status") != "completed":
            continue
        source_index = problem.get("source_index", position)
        if not isinstance(source_index, int):
            raise ValueError(f"Invalid source_index in {input_path}: {source_index!r}")
        required_fields = ("question", "solve_solution", "explain_response")
        missing = [field for field in required_fields if not problem.get(field)]
        if missing:
            raise ValueError(
                f"Completed problem {source_index} in {input_path} is missing {missing}"
            )
        records.append(problem)
    return records


def render_report(records: list[dict[str, Any]]) -> str:
    models = sorted({str(record["explain_model"]) for record in records if record.get("explain_model")})
    model_label = ", ".join(models) if models else "unknown model"
    not_suitable_count = sum(
        record.get("explain_response_kind") == "not_suitable" for record in records
    )
    lines = [
        "DeepMath pilot EXPLAIN results",
        f"Model: {model_label}",
        f"Completed problems: {len(records)}",
        f"NOT_SUITABLE responses: {not_suitable_count}",
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
                "Prior DeepSeek reference solution:",
                str(problem["solve_solution"]).strip(),
                "",
                "Generated EXPLAIN response:",
                str(problem["explain_response"]).strip(),
                "",
            ]
        )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    records = completed_records(args.input)
    atomic_write_text(args.output, render_report(records))
    print(f"Wrote {len(records)} completed EXPLAIN records to {args.output}")


if __name__ == "__main__":
    main()
