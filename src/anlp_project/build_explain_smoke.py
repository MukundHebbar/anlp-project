"""Build a one-record EXPLAIN-v1 smoke manifest from a recovered artifact."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from .storage import atomic_write_json, read_json


def build_smoke(source_path: Path, output_path: Path) -> dict[str, Any]:
    source = read_json(source_path)
    items = source.get("items")
    if not isinstance(items, list):
        raise ValueError(f"{source_path} must contain an items list")
    runnable = [
        item for item in items
        if isinstance(item, dict) and isinstance(item.get("source_index"), int)
        and item.get("output") != "NOT_SUITABLE"
    ]
    if not runnable:
        raise ValueError(f"{source_path} has no runnable EXPLAIN-v1 item")
    selected = runnable[0]
    output = {
        "dataset": source.get("dataset"),
        "sample_size": 1,
        "metadata": {
            "purpose": "qwen3_4b_explain_v1_smoke",
            "source_explain_artifact": str(source_path),
            "selected_source_index": selected["source_index"],
        },
        "items": [selected],
    }
    atomic_write_json(output_path, output)
    print(f"wrote 1 EXPLAIN-v1 smoke item to {output_path}")
    return output


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    build_smoke(args.source, args.output)
