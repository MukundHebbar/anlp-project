"""Summarize Judge generator pilot artifacts without exposing private text."""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
from statistics import mean
from typing import Any

from .storage import atomic_write_json, atomic_write_text, read_json


def _percentile(values: list[int], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = min(len(ordered) - 1, round((len(ordered) - 1) * fraction))
    return float(ordered[index])


def summarize_artifact(path: Path) -> dict[str, Any]:
    payload = read_json(path)
    items = payload.get("items")
    if not isinstance(items, list):
        raise ValueError(f"{path} must contain an items list")
    status_counts = Counter(item.get("status") for item in items if isinstance(item, dict))
    validation_counts = Counter(
        item.get("validation_status") for item in items if isinstance(item, dict) and item.get("status") == "completed"
    )
    labels = Counter(item.get("target_label") for item in items if isinstance(item, dict))
    requested_types = Counter(
        item.get("requested_error_type")
        for item in items
        if isinstance(item, dict) and item.get("target_label") == "incorrect"
    )
    requested_positions = Counter(
        item.get("requested_error_position")
        for item in items
        if isinstance(item, dict) and item.get("target_label") == "incorrect"
    )
    prompt_lengths = [item["prompt_tokens"] for item in items if isinstance(item, dict) and isinstance(item.get("prompt_tokens"), int)]
    completion_lengths = [item["completion_tokens"] for item in items if isinstance(item, dict) and isinstance(item.get("completion_tokens"), int)]
    validation_errors = Counter(
        error
        for item in items
        if isinstance(item, dict)
        for error in (item.get("validation_errors") or [])
        if isinstance(error, str)
    )
    return {
        "artifact": str(path),
        "model": (payload.get("metadata") or {}).get("model"),
        "prompt_file": (payload.get("metadata") or {}).get("prompt_file"),
        "prompt_sha256": (payload.get("metadata") or {}).get("prompt_sha256"),
        "item_count": len(items),
        "status_counts": dict(status_counts),
        "validation_counts": dict(validation_counts),
        "label_counts": dict(labels),
        "requested_error_type_counts": dict(requested_types),
        "requested_error_position_counts": dict(requested_positions),
        "prompt_tokens": {
            "count": len(prompt_lengths),
            "mean": mean(prompt_lengths) if prompt_lengths else None,
            "p95": _percentile(prompt_lengths, 0.95),
        },
        "completion_tokens": {
            "count": len(completion_lengths),
            "mean": mean(completion_lengths) if completion_lengths else None,
            "p95": _percentile(completion_lengths, 0.95),
        },
        "validation_error_counts": dict(validation_errors),
    }


def render_markdown(summaries: list[dict[str, Any]]) -> str:
    lines = [
        "# Judge generator prompt comparison",
        "",
        "This report contains structural generation metrics only. Mathematical validity, first-error correctness, and method preservation require a blinded human audit.",
        "",
        "| Candidate | Items | Completed | Valid schema | Correct targets | Incorrect targets | Prompt mean tokens | Completion mean tokens |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for summary in summaries:
        status = summary["status_counts"]
        validation = summary["validation_counts"]
        labels = summary["label_counts"]
        candidate = Path(summary["artifact"]).stem
        lines.append(
            f"| `{candidate}` | {summary['item_count']} | {status.get('completed', 0)} | "
            f"{validation.get('valid', 0)} | {labels.get('correct', 0)} | {labels.get('incorrect', 0)} | "
            f"{summary['prompt_tokens']['mean'] or '-'} | {summary['completion_tokens']['mean'] or '-'} |"
        )
    lines.extend(
        [
            "",
            "## Audit requirements",
            "",
            "- Confirm every correct proposal is mathematically valid.",
            "- Confirm every incorrect proposal has the requested first error and that all earlier steps are valid.",
            "- Confirm method preservation, error comprehensibility, and absence of label/length shortcuts.",
            "- Record disagreements and adjudications separately from raw generation artifacts.",
        ]
    )
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifacts", nargs="+", type=Path)
    parser.add_argument("--json-output", type=Path)
    parser.add_argument("--markdown-output", type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summaries = [summarize_artifact(path) for path in args.artifacts]
    if args.json_output:
        atomic_write_json(args.json_output, {"summaries": summaries})
    if args.markdown_output:
        atomic_write_text(args.markdown_output, render_markdown(summaries))
    if not args.json_output and not args.markdown_output:
        import json

        print(json.dumps({"summaries": summaries}, indent=2))


if __name__ == "__main__":
    main()
