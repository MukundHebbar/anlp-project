"""Compare GPT-Luna Judge pilot outputs with independent blinded agent reviews."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from .storage import atomic_write_json, atomic_write_text, read_json


def load_blind_reviews(paths: list[Path]) -> dict[str, dict[str, Any]]:
    reviews: dict[str, dict[str, Any]] = {}
    for path in paths:
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, list):
            raise ValueError(f"{path} must contain a JSON array")
        for row in value:
            if not isinstance(row, dict) or not isinstance(row.get("review_id"), str):
                raise ValueError(f"{path} contains an invalid review")
            review_id = row["review_id"]
            if review_id in reviews:
                raise ValueError(f"Duplicate review_id {review_id}")
            reviews[review_id] = row
    return reviews


def compare(key_path: Path, review_paths: list[Path]) -> dict[str, Any]:
    key = read_json(key_path)
    key_items = key.get("items")
    if not isinstance(key_items, list):
        raise ValueError("Review key has no items list")
    reviews = load_blind_reviews(review_paths)
    by_prompt: dict[str, list[dict[str, Any]]] = defaultdict(list)
    discrepancies: list[dict[str, Any]] = []
    for row in key_items:
        review_id = row["review_id"]
        review = reviews.get(review_id)
        prompt = Path(row["artifact"]).stem
        private = row.get("private") or {}
        label = private.get("label")
        step = private.get("first_error_step_id")
        if review is None:
            verdict = {"reviewed": False, "label_match": None, "first_error_match": None}
        else:
            verdict = {
                "reviewed": True,
                "label_match": review.get("true_label") == label,
                "first_error_match": review.get("true_first_error_step_id") == step,
                "method_preserved": review.get("reference_method_preserved"),
                "all_prior_steps_valid": review.get("all_prior_steps_valid"),
            }
            if not verdict["label_match"] or not verdict["first_error_match"]:
                discrepancies.append(
                    {
                        "review_id": review_id,
                        "candidate": prompt,
                        "source_id": row.get("source_id"),
                        "target_label": row.get("target_label"),
                        "claimed_label": label,
                        "reviewed_label": review.get("true_label"),
                        "claimed_first_error_step_id": step,
                        "reviewed_first_error_step_id": review.get("true_first_error_step_id"),
                        "mathematical_comment": review.get("mathematical_comment"),
                    }
                )
        by_prompt[prompt].append(verdict)

    unknown_reviews = set(reviews) - {row["review_id"] for row in key_items}
    if unknown_reviews:
        raise ValueError(f"Review files contain unknown IDs: {sorted(unknown_reviews)}")
    summaries = []
    for prompt, verdicts in sorted(by_prompt.items()):
        reviewed = [verdict for verdict in verdicts if verdict["reviewed"]]
        summaries.append(
            {
                "candidate": prompt,
                "generated_items": len(verdicts),
                "reviewed_items": len(reviewed),
                "label_matches": sum(verdict["label_match"] for verdict in reviewed),
                "first_error_matches": sum(verdict["first_error_match"] for verdict in reviewed),
                "all_prior_steps_valid": dict(Counter(verdict.get("all_prior_steps_valid") for verdict in reviewed)),
                "method_preserved": dict(Counter(verdict.get("method_preserved") for verdict in reviewed)),
            }
        )
    return {
        "review_kind": "independent GPT-Luna agent review; not human adjudication",
        "key_file": str(key_path),
        "review_files": [str(path) for path in review_paths],
        "generated_items": len(key_items),
        "reviewed_items": len(reviews),
        "summaries": summaries,
        "discrepancies": discrepancies,
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# GPT-Luna Judge prompt smoke test",
        "",
        "These are exploratory GPT-Luna agent generations and independent agent reviews. The review is not a human audit, and four sources are too few to establish a prompt quality rate.",
        "",
        "| Candidate | Reviewed/generated | Label match | First-error match | Prior steps valid | Method preserved |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in report["summaries"]:
        lines.append(
            f"| `{row['candidate']}` | {row['reviewed_items']}/{row['generated_items']} | "
            f"{row['label_matches']} | {row['first_error_matches']} | "
            f"{row['all_prior_steps_valid'].get('yes', 0)} | {row['method_preserved'].get('yes', 0)} |"
        )
    lines.extend(["", "## Disagreements", ""])
    if report["discrepancies"]:
        for row in report["discrepancies"]:
            lines.append(
                f"- `{row['candidate']}` `{row['source_id']}`: claimed "
                f"{row['claimed_label']}/{row['claimed_first_error_step_id']}; reviewed "
                f"{row['reviewed_label']}/{row['reviewed_first_error_step_id']}. "
                f"{row['mathematical_comment']}"
            )
    else:
        lines.append("- None in completed reviews.")
    lines.extend(["", "Human review, the full 60-source comparison, and Qwen3-8B confirmation remain required before freezing a generator."])
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--key", required=True, type=Path)
    parser.add_argument("--reviews", required=True, nargs="+", type=Path)
    parser.add_argument("--json-output", required=True, type=Path)
    parser.add_argument("--markdown-output", required=True, type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = compare(args.key, args.reviews)
    atomic_write_json(args.json_output, report)
    atomic_write_text(args.markdown_output, render_markdown(report))
    print(f"Compared {report['reviewed_items']}/{report['generated_items']} blinded Judge items")


if __name__ == "__main__":
    main()
