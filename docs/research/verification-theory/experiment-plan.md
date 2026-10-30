# Experiments needed for the paper, end to end (2026-10-29)

Outline: `paper-outline.md`.

- **Already done:** the 2B mixed model on dev / test / extra, 16 attempts each, all judged; Stage-0 measurements;
  the primary CAV result; trace features; mechanism checks.
- **Costs:** Turing L40S GPU-hours at the measured rates. 2B: about 1,700 attempts per GPU-hour (16k cap); judging
  about 1,600 attempts per GPU-hour (1 chain + direct read).
- **Rule:** all methods share the cached pools, use dev-only tuning, and are compared at matched unit cost *and*
  decoded tokens with a paired bootstrap over questions. Before any new pool is judged, its predicted CAV gain is
  registered (`phase3/semisynth.py`).

## A. GPU experiments

| ID | Experiment | Paper section / claim | Design | GPU-h | Priority |
|---|---|---|---|---|---|
| **E1** | **Second model** | §4 Table 1, §6–§8 cross-condition points | A different size/family as solver *and* self-judge (Qwen3.5-4B, or a non-Qwen model of similar size). Dev 200 + test 400, 16 attempts each. Same judging (1 chain + direct; 4 chains on test attempts 0–3). Fit the model on its 4-attempt aggregates → register predictions → judge. | 18–22 | **Must** |
| **E2** | **Second benchmark** | §8 generality; §6 contested collapse on harder problems | Mixed 2B on MATH-500 (or an OlympiadBench subset): 100 questions for tuning + 400 for evaluation, **8 attempts**, same judging. Register predictions first. | 6–8 | **Must** |
| **E3** | **Seeds of the primary result** | §7 robustness | 2 new seeds of generation + judging (1 chain + direct) on the 400 test questions, 16 attempts. Seed-0 dev-tuned β reused, fixed in advance. Report per-seed and pooled gain. | ~24 | **Must** |
| **E4** | **Solver-confidence baselines**: DeepConf (offline), self-certainty, CISC response-probability | §7 baselines; §8 points | One prefill pass over the cached attempts saving top-20 token log-probs (main pools + E1/E2/E3 pools). No generation. | 6–9 | **Must** (the closest competitors) |
| **E6** | **Pairwise self-verification (V1-Infer)** | §7 strongest LLM-selector competitor | Our model judges pairs of representatives from the top answer groups on contested questions, with uncertainty-guided extra comparisons. Matched cost. | 4–6 | **Must** |
| E7 | Trained self-judge evaluation (Stage-2 adapters exist) | §6 direct test of the criterion shift; §9 judge training | Re-judge dev / test / extra with the `global` and `perq` step-32 adapters (1 chain + direct). | ~10 | Optional (strong add) |
| E8 | PairJudge RM and/or Universal Self-Consistency | §7 extra baselines | Contested questions only | 3–5 | Optional |

**Core total (E1–E4, E6): about 58–70 GPU-hours.** With E7–E8: about 71–85. The ledger has 216 GPU-hours left. At
4 GPUs, the core takes about 16–19 hours of wall time. (E5, the external reward model, was dropped on 2026-10-29 by
the user's decision.)

## B. CPU analyses (free, on cached data)

| ID | Analysis | Section |
|---|---|---|
| A1 | CISC with P(True) (= our direct read, softmax-weighted vote, temperature tuned on dev); early-stopping self-consistency; adaptive-consistency variants | §7 |
| A2 | Every signal (judge chain, direct, CISC, DeepConf, self-certainty, V1) **used natively vs inside CAV**, at matched cost and tokens | §7 wrapper claim |
| A3 | **Predicted vs observed gain** across all verifiers, models and benchmarks; correlation of gain with contested within-question AUROC vs pooled AUROC (bootstrap CIs) | §8 headline |
| A4 | Swapped tuning (tune on test ∪ extra, evaluate on dev); per-set breakdown; sensitivity over β and (N₁, m); chain cost 0.3 / 0.5 / 0.67 | §7–§8 robustness |
| A5 | Worst-case gap to majority vote for every rule across models, benchmarks, N and seeds | §5 guarantee |
| A6 | Refit the leniency model to this judge's own 1-verdict / 4-verdict data; report the noise split | §6 |
| A7 | Register the semi-synthetic predicted gain for each new pool (E1, E2, E3 seeds) before judging; hash it in the pre-registration | §8 |

## C. Order and dependencies

1. **Now, CPU:** A1, A4, A6. Extend the pre-registration with E1–E6 (models, benchmarks, seeds, baselines,
   primary comparisons).
2. **GPU wave 1** (4 GPUs in parallel): generation for E1 (2 GPUs), E2 (1 GPU), E3 (1 GPU).
3. **Before judging the new pools:** fit the model on each pool's first 4 attempts, then run A7 (register
   predictions).
4. **GPU wave 2:** judge the E1/E2/E3 pools, then the prefill pass E4, then E6 (and optionally E7).
5. **CPU:** A2, A3, A5 → paper tables and figures (`phase3/paper_tables.py`, `fig_prediction.py`).
6. **Write-up:** fill §7–§8, Table 1 rows, and the limitations; final pass.

## D. Explicitly not needed

- Larger N (32–64).
- More generation seeds beyond E3.
- Human error annotation.
- Base/SOLVE/JUDGE adapter scoring (cancelled).
- Retraining the judge (Stage-2 training done; only E7's evaluation is optional).
- An external reward model (dropped by the user's decision).
