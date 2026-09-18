"""Shard and merge helpers for the four-worker Qwen3 WITNESS run."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import socket
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .qwen3_turing_eval import build_witness_report


def shard_witness_input(input_path: Path, shard_dir: Path, shard_count: int = 4) -> list[int]:
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    items = payload.get("items")
    if not isinstance(items, list) or not items:
        raise ValueError("WITNESS input must contain non-empty items")
    indices = [item.get("source_index") for item in items if isinstance(item, dict)]
    if len(indices) != len(items) or len(set(indices)) != len(indices):
        raise ValueError("WITNESS source indices must be unique")
    if shard_count < 1:
        raise ValueError("shard_count must be positive")
    shard_dir.mkdir(parents=True, exist_ok=True)
    for worker in range(shard_count):
        (shard_dir / f"shard-{worker:02d}.json").write_text(
            json.dumps({"metadata": payload.get("metadata", {}), "items": items[worker::shard_count]}, ensure_ascii=False),
            encoding="utf-8",
        )
    return indices


def merge_witness_results(
    input_path: Path,
    result_dir: Path,
    artifact_dir: Path,
    *,
    node: str = "node07",
    start_epoch: float | None = None,
) -> dict[str, Any]:
    source = json.loads(input_path.read_text(encoding="utf-8"))
    expected = [item["source_index"] for item in source["items"]]
    expected_set = set(expected)
    by_index: dict[int, dict[str, Any]] = {}
    for path in sorted(result_dir.glob("shard-*-results.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        for item in payload.get("results", []):
            index = item.get("source_index")
            if index in by_index:
                raise ValueError(f"duplicate source_index={index}")
            by_index[index] = item
    missing = expected_set - set(by_index)
    extra = set(by_index) - expected_set
    if missing or extra or len(by_index) != len(expected):
        raise ValueError(
            f"merge mismatch missing={sorted(missing)} extra={sorted(extra)} "
            f"count={len(by_index)} expected={len(expected)}"
        )
    elapsed = (time.time() - start_epoch) if start_epoch is not None else None
    merged: dict[str, Any] = {
        "metadata": {
            "model": "Qwen/Qwen3-4B",
            "task_kind": "witness",
            "backend": "vllm",
            "node": node,
            "hostname": socket.gethostname(),
            "slurm_job_id": os.getenv("SLURM_JOB_ID"),
            "cuda_visible_devices": os.getenv("CUDA_VISIBLE_DEVICES"),
            "parallel_workers": len(list(result_dir.glob("shard-*-results.json"))),
            "batch_size": 5,
            "max_tokens": 16384,
            "max_model_len": 32768,
            "max_num_seqs": 5,
            "temperature": 0.7,
            "top_p": 0.8,
            "top_k": 20,
            "enable_thinking": False,
            "reasoning_effort": None,
            "semantic_scoring": False,
            "expected_task_count": len(expected),
            "job_elapsed_seconds": elapsed,
            "elapsed_seconds": elapsed,
            "finished_at_utc": datetime.now(timezone.utc).isoformat(),
            "usage_summary": {
                "prompt_tokens": sum(item.get("prompt_tokens") or 0 for item in by_index.values()),
                "completion_tokens": sum(item.get("completion_tokens") or 0 for item in by_index.values()),
                "total_tokens": sum((item.get("prompt_tokens") or 0) + (item.get("completion_tokens") or 0) for item in by_index.values()),
            },
        },
        "results": [by_index[index] for index in expected],
    }
    artifact_dir.mkdir(parents=True, exist_ok=True)
    (artifact_dir / "results.json").write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (artifact_dir / "report.txt").write_text(build_witness_report(merged), encoding="utf-8")
    shutil.copy2(input_path, artifact_dir / "input.json")
    logs = result_dir.parent / "logs"
    if logs.exists():
        shutil.copytree(logs, artifact_dir / "worker-logs", dirs_exist_ok=True)
    return merged


def main() -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    shard = subparsers.add_parser("shard")
    shard.add_argument("input", type=Path)
    shard.add_argument("output", type=Path)
    shard.add_argument("--count", type=int, default=4)
    merge = subparsers.add_parser("merge")
    merge.add_argument("input", type=Path)
    merge.add_argument("results", type=Path)
    merge.add_argument("artifact", type=Path)
    merge.add_argument("--start-epoch", type=float, default=None)
    args = parser.parse_args()
    if args.command == "shard":
        print(f"input_items={len(shard_witness_input(args.input, args.output, args.count))} workers={args.count}")
    else:
        merged = merge_witness_results(args.input, args.results, args.artifact, start_epoch=args.start_epoch)
        print(f"merged_results={len(merged['results'])} format_valid={sum(item.get('format_valid') is True for item in merged['results'])}")


if __name__ == "__main__":
    main()
