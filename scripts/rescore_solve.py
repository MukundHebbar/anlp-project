#!/usr/bin/env python3
"""Re-score the SOLVE rows of eval folders with the current answer checker (verifier v3).

    uv run python scripts/rescore_solve.py artifacts/baselines/final-v3/test/v3-pass4-2b [more eval dirs ...]

Each <dir>/s*/scores.jsonl gets its SOLVE rows recomputed from responses.jsonl with
baseline.score_response_strict; JUDGE and RECONSTRUCT rows are left as they are. The first time a file is
rewritten, the old one is kept as scores.v2.jsonl. Prints old and new strict accuracy per folder. CPU only.
"""

import json
import statistics as st
import sys
from multiprocessing import Pool
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from anlp_project.baseline import load_rows, score_response_strict  # noqa: E402

ROWS: dict = {}


def _init():
    global ROWS
    ROWS = {r["uid"]: r for split in ("train", "test") for r in load_rows("solve", split)}


def _score(response):
    return score_response_strict(ROWS[response["uid"]], response)


def main(dirs):
    with Pool(16, initializer=_init) as pool:
        for d in map(Path, dirs):
            samples = sorted(s for s in d.glob("s*") if (s / "responses.jsonl").exists())
            if not samples:
                raise SystemExit(f"{d}: no s*/responses.jsonl")
            old, new = [], []
            for s in samples:
                responses = [json.loads(l) for l in (s / "responses.jsonl").open()]
                solve = [r for r in responses if r.get("task") == "solve"]
                scores = [json.loads(l) for l in (s / "scores.jsonl").open()]
                fresh = {x["uid"]: x for x in pool.map(_score, solve, chunksize=8)}
                old += [x["correct_strict"] for x in scores if x["task"] == "solve"]
                new += [x["correct_strict"] for x in fresh.values()]
                backup = s / "scores.v2.jsonl"
                if not backup.exists():
                    backup.write_text((s / "scores.jsonl").read_text())
                out = [fresh.get(x["uid"], x) if x["task"] == "solve" else x for x in scores]
                (s / "scores.jsonl").write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in out))
            print(f"{d}: SOLVE strict accuracy {100 * st.mean(old):.1f} -> {100 * st.mean(new):.1f} "
                  f"({len(new)} answers)")


if __name__ == "__main__":
    main(sys.argv[1:])
