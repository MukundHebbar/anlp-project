#!/usr/bin/env python3
"""Choose the mixed-task GRPO checkpoint on the three dev slices.

    python3 scripts/select_checkpoint_mixed.py <dev dir> artifacts/opd/evals/v3-pass4-2b-dev

<dev dir>/step<k>/ are eval_matrix dev folders with all three tasks (SOLVE 4 samples in s0..s3; JUDGE and
RECONSTRUCT in s0). Per step:
- SOLVE: strict accuracy (mean over samples);
- JUDGE: Youden's J = verdict accuracy on incorrect keys + on correct keys - 1;
- RECONSTRUCT: Jev score /100 on s0 (scored here, about $0.06 per step, if judged-scores.jev.jsonl is missing).
The composite is the mean over tasks of the Δ against the untrained model, in points; best composite wins, ties go to
the later step. Writes <dev dir>/selection.json.
"""

import json
import statistics as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from select_dev_checkpoint import reconstruct_metric  # noqa: E402


def rows(d: Path, task: str, samples: str = "s*") -> list[dict]:
    return [x for f in sorted(d.glob(f"{samples}/scores.jsonl")) for x in map(json.loads, f.open()) if x["task"] == task]


def metrics(d: Path) -> dict[str, float]:
    solve = rows(d, "solve")
    judge = rows(d, "judge")
    by_label = {lab: [x["verdict_correct_strict"] for x in judge if x["label"] == lab] for lab in ("correct", "incorrect")}
    return {"solve_acc": 100 * st.mean(x["correct_strict"] for x in solve),
            "judge_j": 100 * (st.mean(by_label["incorrect"]) + st.mean(by_label["correct"]) - 1),
            "judge_step": 100 * st.mean(x["step_correct_strict"] for x in judge if x["label"] == "incorrect"),
            "recon_jev": reconstruct_metric(d)[0]}


def main():
    dev, base_dir = Path(sys.argv[1]), Path(sys.argv[2])
    base = metrics(base_dir)
    print("untrained:", {k: round(v, 1) for k, v in base.items()})
    out = {}
    for d in sorted(dev.glob("step*"), key=lambda p: int(p.name[4:])):
        if not (d / "s0" / "scores.jsonl").exists():
            continue
        m = metrics(d)
        delta = {"solve_acc": m["solve_acc"] - base["solve_acc"], "judge_j": m["judge_j"] - base["judge_j"],
                 "recon_jev": m["recon_jev"] - base["recon_jev"]}
        out[int(d.name[4:])] = {**m, "delta": delta, "composite": st.mean(delta.values())}
        print(f"step {d.name[4:]}: " + ", ".join(f"{k} {v:.1f} (Δ {delta.get(k, 0):+.1f})" for k, v in m.items()
                                                 if k in delta) + f"  composite {out[int(d.name[4:])]['composite']:+.2f}")
    best = max(out, key=lambda k: (round(out[k]["composite"], 6), k))
    (dev / "selection.json").write_text(json.dumps({
        "rule": "best mean dev Δ over SOLVE acc, JUDGE Youden J, RECONSTRUCT Jev score; ties -> later step",
        "selected_step": best, "base": base, "steps": out}, indent=1) + "\n")
    print(f"selected step {best}")


if __name__ == "__main__":
    main()
