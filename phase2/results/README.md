# Phase-2 results

Curated outputs of the Phase-2 experiments; the write-up is
[../docs/experiments-summary.md](../docs/experiments-summary.md).
Generated texts (full solutions, agent reasoning) are removed; the complete runs are on Turing under
`/home/yashas.kotre/anlp-project-phase2/runs-out/` (generated texts, about 140 MB compressed).

| Folder | Experiment | Code | Jobs |
|---|---|---|---|
| `hint-pilot/` | Census of the mixed model's seen SOLVE pool; specialist hints for always-wrong problems | `../scripts/hint_pilot.py` | 43854, 43879 |
| `functional/` | Tutor (`tutor-*`) and self-checking solver with drift detection (`drift-*`) | `../scripts/functional.py` | 43914, 43921 |
| `processbench/` | JUDGE on ProcessBench (natural errors) vs the synthetic JUDGE test set, six models | `../scripts/processbench_eval.py` | 43937 |
| `failure-driven/` | Failure-driven GRPO pilot: SOLVE-only (A) vs failures converted to JUDGE/RECONSTRUCT (B) vs failures replayed as SOLVE (D) | `../failure_driven/` | 45538, 45540, 45808, 45851, 45888, 45943 |

Each folder has `summary.json` and the generated report(s). Records are gzipped JSONL:

- `hint-pilot/census.jsonl.gz`: 750 problems x 8 answers with checker results.
- `hint-pilot/agents.jsonl.gz`: the 39 always-wrong problems, JUDGE and RECONSTRUCT outputs and hints.
- `hint-pilot/test*.jsonl.gz`: retries per hint arm.
- `functional/tutor-items.jsonl.gz`: the 502 test solutions (200 correct, 200 false step, 102 wrong question).
- `functional/tutor-agents.jsonl.gz`, `tutor-compare.jsonl.gz`: verdicts, rebuilt questions, 27B comparisons.
- `functional/drift-*.jsonl.gz`: per-attempt critic outputs, per-checkpoint comparisons, repairs.
- `processbench/pred-<model>.jsonl.gz`: predicted first wrong step per solution (3,400 ProcessBench + 400 synthetic).
- `failure-driven/dev-scores.jsonl.gz`, `recheck-scores.jsonl.gz`: per-sample SOLVE checker results (dev evals; rechecks of the buffered failures).
- `failure-driven/buffers.jsonl.gz`, `conversion.jsonl.gz`: buffered failures (attempt texts removed), diagnoses and RECONSTRUCT clues.
- `failure-driven/train-metrics.jsonl.gz`: per-step training metrics of every run. Rollouts and adapters stay on Turing scratch (node07, node06).
