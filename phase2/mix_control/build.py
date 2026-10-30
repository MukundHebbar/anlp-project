#!/usr/bin/env python3
"""SOLVE-only control for the Phase-1 mixed-task run (mixed-lr2e-5, checkpoint step 75).

The mixed run (opd_run.py --task mixed: opd.mixed_prompts(1134), 30 prompts per step, every batch exactly 10 SOLVE +
10 JUDGE + 10 RECONSTRUCT) is re-run with its JUDGE and RECONSTRUCT prompts dropped: the same SOLVE questions, in the
same order and the same steps (10 per step), for 75 steps. Writes:
  data/prompts-solve75.jsonl   the control's 750 prompts (uid, prompt, task), step k = lines 10k..10k+9
  data/mixed_solve_uids.json   the same 750 uids (excluded from validation: 51 of them are in data/val_uids.json)

    python phase2/mix_control/build.py
"""
import collections
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "src"))
from anlp_project import opd  # noqa: E402

STEPS, PER_STEP, MIXED_PER_STEP = 75, 10, 30


def main() -> None:
    pool = opd.mixed_prompts(1134)
    solve = []
    for k in range(STEPS):
        batch = pool[MIXED_PER_STEP * k:MIXED_PER_STEP * (k + 1)]
        tasks = collections.Counter(p["task"] for p in batch)
        if tasks != {"solve": PER_STEP, "judge": PER_STEP, "reconstruct": PER_STEP}:
            raise SystemExit(f"mixed step {k + 1} is not 10/10/10: {dict(tasks)}")
        solve += [{"uid": p["uid"], "prompt": p["prompt"], "task": "solve"} for p in batch if p["task"] == "solve"]
    assert len({p["uid"] for p in solve}) == STEPS * PER_STEP
    out = HERE / "data"
    out.mkdir(exist_ok=True)
    with open(out / "prompts-solve75.jsonl", "w") as fh:
        for p in solve:
            fh.write(json.dumps(p, ensure_ascii=False) + "\n")
    (out / "mixed_solve_uids.json").write_text(json.dumps([p["uid"] for p in solve]))
    print(json.dumps({"prompts": len(solve), "steps": STEPS, "per_step": PER_STEP}))


if __name__ == "__main__":
    main()
