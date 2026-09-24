"""Build a blinded mathematical review packet for Judge prompt pilots."""

from __future__ import annotations

import argparse
import hashlib
import random
from pathlib import Path
from typing import Any

from .storage import atomic_write_json, read_json


def build_review_packet(paths: list[Path], seed: int = 20260924) -> tuple[dict[str, Any], dict[str, Any]]:
    if not paths:
        raise ValueError("At least one generator artifact is required")
    blinded: list[dict[str, Any]] = []
    key: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for path in paths:
        artifact = read_json(path)
        items = artifact.get("items")
        if not isinstance(items, list):
            raise ValueError(f"{path} has no items list")
        metadata = artifact.get("metadata") or {}
        for item in items:
            if not isinstance(item, dict):
                raise ValueError(f"{path} contains a non-object item")
            generated = item.get("parsed_output")
            if not isinstance(generated, dict) or not isinstance(generated.get("public"), dict):
                continue
            public = generated["public"]
            review_id = hashlib.sha256(
                f"{path}:{item.get('item_id')}:{seed}".encode("utf-8")
            ).hexdigest()[:16]
            if review_id in seen_ids:
                raise ValueError(f"Duplicate review ID {review_id}")
            seen_ids.add(review_id)
            blinded.append(
                {
                    "review_id": review_id,
                    "problem": public.get("problem"),
                    "proposed_solution": public.get("proposed_solution"),
                    "instruction": public.get("instruction"),
                    "review": {
                        "true_label": None,
                        "true_first_error_step_id": None,
                        "all_prior_steps_valid": None,
                        "reference_method_preserved": None,
                        "error_type_matches": None,
                        "error_position_matches": None,
                        "teacher_target_correct": None,
                        "label_shortcut": None,
                        "mathematical_comment": None,
                    },
                }
            )
            key.append(
                {
                    "review_id": review_id,
                    "artifact": str(path),
                    "item_id": item.get("item_id"),
                    "source_id": item.get("source_id"),
                    "source_index": item.get("source_index"),
                    "prompt_file": metadata.get("prompt_file"),
                    "prompt_sha256": metadata.get("prompt_sha256"),
                    "target_label": item.get("target_label"),
                    "requested_error_type": item.get("requested_error_type"),
                    "requested_error_position": item.get("requested_error_position"),
                    "private": generated.get("private"),
                }
            )
    random.Random(seed).shuffle(blinded)
    return (
        {"purpose": "blind mathematical audit of GPT-Luna Judge prompt pilot", "seed": seed, "item_count": len(blinded), "items": blinded},
        {"purpose": "private key for Judge blind review; do not give to reviewers before annotation", "seed": seed, "item_count": len(key), "items": key},
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifacts", nargs="+", type=Path)
    parser.add_argument("--blind-output", required=True, type=Path)
    parser.add_argument("--key-output", required=True, type=Path)
    parser.add_argument("--seed", type=int, default=20260924)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    blind, key = build_review_packet(args.artifacts, args.seed)
    if args.blind_output.resolve() == args.key_output.resolve():
        raise ValueError("Blind packet and private key must have different paths")
    atomic_write_json(args.blind_output, blind)
    atomic_write_json(args.key_output, key)
    print(f"Wrote {blind['item_count']} blinded Judge items to {args.blind_output}")


if __name__ == "__main__":
    main()
