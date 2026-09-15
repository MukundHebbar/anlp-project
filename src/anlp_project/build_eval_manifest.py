"""Build the reproducible 146-problem DeepMath evaluation manifest."""

from __future__ import annotations

import argparse
import hashlib
import random
from pathlib import Path
from typing import Any

from .paths import MANIFESTS_DIR, PROJECT_ROOT
from .storage import atomic_write_json, read_json


ROOT_DIR = PROJECT_ROOT
DEFAULT_DATASET = ROOT_DIR / "data" / "datasets" / "deepmath-60k"
DEFAULT_PILOT = ROOT_DIR / "data" / "legacy-inputs" / "deepmath-pilot-50.json"
DEFAULT_OUTPUT = MANIFESTS_DIR / "deepmath" / "deepmath-pilot-146.json"
DEFAULT_NEW_OUTPUT = MANIFESTS_DIR / "deepmath" / "deepmath-pilot-100-new.json"
SEED = 42
LOWER_BAND = (5.0, 6.5)
UPPER_BAND = (7.0, 8.0)
QUOTAS = {
    "Algebra": {"lower": 20, "upper": 6},
    "Calculus": {"lower": 20, "upper": 6},
    "Number Theory": {"lower": 20, "upper": 4},
    "Discrete Mathematics / Combinatorics": {"lower": 20, "upper": 4},
}
BROAD_PREFIXES = {
    "Algebra": (
        "Mathematics -> Algebra -> Algebra ->",
        "Mathematics -> Algebra -> Intermediate Algebra ->",
        "Mathematics -> Algebra -> Linear Algebra ->",
        "Mathematics -> Algebra -> Other",
    ),
    "Calculus": ("Mathematics -> Calculus ->",),
    "Number Theory": ("Mathematics -> Number Theory ->",),
    "Discrete Mathematics / Combinatorics": (
        "Mathematics -> Discrete Mathematics ->",
    ),
}


def question_hash(question: str) -> str:
    return hashlib.sha256(question.encode("utf-8")).hexdigest()


def broad_topic(topic: str) -> str | None:
    for broad, prefixes in BROAD_PREFIXES.items():
        if any(topic.startswith(prefix) for prefix in prefixes):
            return broad
    return None


def difficulty_band(value: Any) -> str | None:
    difficulty = float(value)
    if LOWER_BAND[0] <= difficulty <= LOWER_BAND[1]:
        return "lower"
    if UPPER_BAND[0] <= difficulty <= UPPER_BAND[1]:
        return "upper"
    return None


def load_existing_pilot(path: Path) -> tuple[dict[int, dict[str, Any]], set[str]]:
    data = read_json(path)
    problems = data.get("problems")
    if not isinstance(problems, list):
        raise ValueError(f"{path} must contain a problems list")
    by_index: dict[int, dict[str, Any]] = {}
    hashes: set[str] = set()
    for position, problem in enumerate(problems):
        if not isinstance(problem, dict) or not problem.get("question"):
            raise ValueError(f"pilot record {position} is invalid")
        by_index[position] = problem
        hashes.add(question_hash(problem["question"]))
    return by_index, hashes


def load_completed_indices(paths: list[Path]) -> set[int]:
    completed: set[int] = set()
    for path in paths:
        data = read_json(path)
        for position, problem in enumerate(data.get("problems", [])):
            if isinstance(problem, dict) and problem.get("solve_status") == "completed":
                completed.add(problem.get("source_index", position))
    return completed


def sample_new_rows(dataset_path: Path, excluded_hashes: set[str]) -> list[dict[str, Any]]:
    try:
        from datasets import load_from_disk
    except ImportError as exc:
        raise RuntimeError("Install datasets before building the local manifest") from exc

    dataset = load_from_disk(str(dataset_path))
    pools: dict[tuple[str, str], list[dict[str, Any]]] = {
        (broad, band): []
        for broad in QUOTAS
        for band in ("lower", "upper")
    }
    seen_hashes = set(excluded_hashes)
    for row_index, row in enumerate(dataset):
        question = row.get("question")
        topic = row.get("topic")
        if not isinstance(question, str) or not question.strip() or not isinstance(topic, str):
            continue
        digest = question_hash(question)
        if digest in seen_hashes:
            continue
        broad = broad_topic(topic)
        band = difficulty_band(row.get("difficulty"))
        if broad is None or band is None:
            continue
        pools[(broad, band)].append(
            {
                "dataset_row_index": row_index,
                "question": question,
                "final_answer": str(row.get("final_answer", "")),
                "topic": topic,
                "difficulty": float(row["difficulty"]),
                "question_hash": digest,
            }
        )

    rng = random.Random(SEED)
    selected: list[dict[str, Any]] = []
    selected_hashes = set(excluded_hashes)
    for broad, bands in QUOTAS.items():
        for band, quota in bands.items():
            candidates = pools[(broad, band)]
            rng.shuffle(candidates)
            chosen = []
            for candidate in candidates:
                if candidate["question_hash"] in selected_hashes:
                    continue
                chosen.append(candidate)
                selected_hashes.add(candidate["question_hash"])
                if len(chosen) == quota:
                    break
            if len(chosen) != quota:
                raise ValueError(
                    f"Insufficient unseen {broad}/{band} rows: "
                    f"needed {quota}, found {len(chosen)}"
                )
            selected.extend(chosen)
    return selected


def build_manifests(
    dataset_path: Path,
    pilot_path: Path,
    output_path: Path,
    new_output_path: Path,
    completed_solution_paths: list[Path],
) -> None:
    pilot, pilot_hashes = load_existing_pilot(pilot_path)
    completed_indices = load_completed_indices(completed_solution_paths)
    old_records: list[dict[str, Any]] = []
    for source_index in sorted(completed_indices):
        if source_index not in pilot:
            raise ValueError(f"completed source index {source_index} is not in the pilot")
        old_records.append(
            {
                **pilot[source_index],
                "source_index": source_index,
                "source_id": f"pilot-{source_index}",
                "question_hash": question_hash(pilot[source_index]["question"]),
            }
        )

    new_rows = sample_new_rows(dataset_path, pilot_hashes)
    new_records: list[dict[str, Any]] = []
    for ordinal, row in enumerate(new_rows, start=50):
        new_records.append(
            {
                **row,
                "source_index": ordinal,
                "source_id": f"deepmath-row-{row['dataset_row_index']}-{row['question_hash'][:12]}",
            }
        )

    if len(old_records) != 46:
        raise ValueError(f"expected 46 completed existing records, found {len(old_records)}")
    if len(new_records) != 100:
        raise ValueError(f"expected 100 new records, found {len(new_records)}")

    metadata = {
        "dataset_path": str(dataset_path),
        "pilot_path": str(pilot_path),
        "seed": SEED,
        "difficulty_bands": {"lower": list(LOWER_BAND), "upper": list(UPPER_BAND)},
        "new_topic_quotas": QUOTAS,
        "existing_completed_count": len(old_records),
        "new_count": len(new_records),
        "total_count": len(old_records) + len(new_records),
        "excluded_pilot_count": len(pilot),
        "completed_solution_paths": [str(path) for path in completed_solution_paths],
    }
    atomic_write_json(
        output_path,
        {
            "dataset": "zwhe99/DeepMath-103K",
            "sample_size": 146,
            "seed": SEED,
            "difficulty_buckets": {"lower": "5.0-6.5", "upper": "7.0-8.0"},
            "metadata": metadata,
            "problems": old_records + new_records,
        },
    )
    atomic_write_json(
        new_output_path,
        {
            "dataset": "zwhe99/DeepMath-103K",
            "sample_size": 100,
            "seed": SEED,
            "metadata": metadata,
            "problems": new_records,
        },
    )
    print(f"wrote {len(old_records) + len(new_records)} records to {output_path}")
    print(f"wrote {len(new_records)} new records to {new_output_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--pilot", type=Path, default=DEFAULT_PILOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--new-output", type=Path, default=DEFAULT_NEW_OUTPUT)
    parser.add_argument(
        "--completed-solutions",
        type=Path,
        nargs="+",
        default=[
            ROOT_DIR / "data" / "legacy-generated-solutions" / "deepmath-pilot-25-attempts-24-completed-deepseek-v4-flash-medium.json",
            ROOT_DIR / "data" / "legacy-generated-solutions" / "deepmath-pilot-26-attempts-22-completed-deepseek-v4-flash-medium.json",
        ],
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    build_manifests(
        args.dataset,
        args.pilot,
        args.output,
        args.new_output,
        args.completed_solutions,
    )
