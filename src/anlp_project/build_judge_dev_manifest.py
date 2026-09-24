"""Build the private, verified-source development pool for Judge prompt tests.

The output intentionally contains the trusted reference solution because it is
an input to the Qwen teacher during generation.  It must not be used as a
student-facing manifest.
"""

from __future__ import annotations

import argparse
import random
from collections import Counter
from pathlib import Path
from typing import Any

from .paths import PROJECT_ROOT
from .storage import atomic_write_json, read_json


DEFAULT_SOURCE = PROJECT_ROOT / "artifacts" / "deepseek-v4-flash" / "solve" / "146" / "results.json"
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "manifests" / "deepmath" / "judge-dev-60-generator.json"
SEED = 20260921

# The current pilot contains these four broad topic groups.  The final proposal
# split still needs to be reconciled with the other task owners.
QUOTAS: dict[str, dict[str, int]] = {
    "Algebra": {"lower": 12, "upper": 3},
    "Calculus": {"lower": 12, "upper": 3},
    "Discrete Mathematics": {"lower": 12, "upper": 3},
    "Number Theory": {"lower": 12, "upper": 3},
}


def broad_topic(topic: str) -> str:
    parts = [part.strip() for part in topic.split(" -> ") if part.strip()]
    return parts[1] if len(parts) > 1 else (parts[0] if parts else "Unknown")


def difficulty_band(value: Any) -> str:
    difficulty = float(value)
    return "lower" if difficulty < 7 else "upper"


def load_verified_candidates(source_path: Path) -> list[dict[str, Any]]:
    payload = read_json(source_path)
    candidates: list[dict[str, Any]] = []
    for record in payload.get("problems", []):
        if record.get("answer_status") != "correct":
            continue
        reference_solution = record.get("solve_solution")
        if not isinstance(reference_solution, str) or not reference_solution.strip():
            continue
        question = record.get("question")
        topic = record.get("topic")
        if not isinstance(question, str) or not question.strip():
            continue
        if not isinstance(topic, str) or not topic.strip():
            continue
        candidates.append(
            {
                "source_id": record["source_id"],
                "source_index": record["source_index"],
                "question": question,
                "final_answer": record.get("final_answer"),
                "topic": topic,
                "broad_topic": broad_topic(topic),
                "difficulty": record.get("difficulty"),
                "difficulty_band": difficulty_band(record.get("difficulty")),
                "reference_solution": reference_solution,
                "question_hash": record.get("question_hash"),
                "verification_method": record.get("verification_method"),
            }
        )
    return candidates


def build_manifest(source_path: Path, seed: int = SEED) -> dict[str, Any]:
    candidates = load_verified_candidates(source_path)
    pools: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for candidate in candidates:
        key = (candidate["broad_topic"], candidate["difficulty_band"])
        pools.setdefault(key, []).append(candidate)

    rng = random.Random(seed)
    selected: list[dict[str, Any]] = []
    allocation: dict[str, dict[str, Any]] = {}
    for topic, band_quotas in QUOTAS.items():
        allocation[topic] = {}
        for band, quota in band_quotas.items():
            pool = sorted(pools.get((topic, band), []), key=lambda item: item["source_index"])
            rng.shuffle(pool)
            if len(pool) < quota:
                raise ValueError(
                    f"Not enough verified candidates for {topic}/{band}: "
                    f"need {quota}, found {len(pool)}"
                )
            chosen = sorted(pool[:quota], key=lambda item: item["source_index"])
            selected.extend(chosen)
            allocation[topic][band] = {
                "requested": quota,
                "available": len(pool),
                "source_indices": [item["source_index"] for item in chosen],
            }

    selected.sort(key=lambda item: item["source_index"])
    return {
        "manifest_name": "judge-dev-60-generator",
        "task": "JUDGE",
        "purpose": (
            "Private development input for comparing Judge-generation prompts. "
            "The reference_solution is teacher-only and must be removed from "
            "student-facing exports."
        ),
        "source_artifact": str(source_path.relative_to(PROJECT_ROOT)),
        "source_artifact_filter": {
            "answer_status": "correct",
            "reference_solution": "solve_solution",
            "verification": "existing DeepSeek solve verification; exploratory only",
        },
        "selection": {
            "seed": seed,
            "requested_size": sum(sum(bands.values()) for bands in QUOTAS.values()),
            "actual_size": len(selected),
            "allocation": allocation,
            "candidate_labels_for_prompt_comparison": ["correct", "incorrect"],
            "final_split_status": "not locked; exclude from final test until reassigned",
        },
        "problems": selected,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--seed", type=int, default=SEED)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    manifest = build_manifest(args.source.resolve(), seed=args.seed)
    atomic_write_json(args.output.resolve(), manifest)
    counts = Counter(
        (item["broad_topic"], item["difficulty_band"])
        for item in manifest["problems"]
    )
    print(f"Wrote {len(manifest['problems'])} private Judge development sources to {args.output}")
    for (topic, band), count in sorted(counts.items()):
        print(f"  {topic}/{band}: {count}")


if __name__ == "__main__":
    main()
