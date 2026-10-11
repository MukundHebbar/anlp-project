# Phase-2 results

Curated outputs of the Phase-2 experiments; the write-up is
[docs/research/phase2/experiments-summary.md](../../docs/research/phase2/experiments-summary.md).
Generated texts (full solutions, agent reasoning) are removed; the complete runs are on Turing under
`/home/yashas.kotre/anlp-project-phase2/runs-out/`.

| Folder | Experiment | Code | Jobs |
|---|---|---|---|
| `hint-pilot/` | Census of the mixed model's seen SOLVE pool; specialist hints for always-wrong problems | `scripts/phase2/hint_pilot.py` | 43854, 43879 |
| `functional/` | Tutor (`tutor-*`) and self-checking solver with drift detection (`drift-*`) | `scripts/phase2/functional.py` | 43914, 43921 |
| `processbench/` | JUDGE on ProcessBench (natural errors) vs the synthetic JUDGE test set, six models | `scripts/phase2/processbench_eval.py` | 43937 |

Each folder has `summary.json` and the generated report(s). Records are gzipped JSONL:

- `hint-pilot/census.jsonl.gz`: 750 problems x 8 answers with checker results.
- `hint-pilot/agents.jsonl.gz`: the 39 always-wrong problems, JUDGE and RECONSTRUCT outputs and hints.
- `hint-pilot/test*.jsonl.gz`: retries per hint arm.
- `functional/tutor-items.jsonl.gz`: the 502 test solutions (200 correct, 200 false step, 102 wrong question).
- `functional/tutor-agents.jsonl.gz`, `tutor-compare.jsonl.gz`: verdicts, rebuilt questions, 27B comparisons.
- `functional/drift-*.jsonl.gz`: per-attempt critic outputs, per-checkpoint comparisons, repairs.
- `processbench/pred-<model>.jsonl.gz`: predicted first wrong step per solution (3,400 ProcessBench + 400 synthetic).
