# Phase 2: what can the trained task specialists do?

Phase 1 ([GRPO transfer report](../docs/reports/2026-10-08-grpo-transfer-report.md)) trained Qwen3.5-2B with
Dr. GRPO on three forms of the same mathematics (**SOLVE**: write a solution; **JUDGE**: find the first wrong step
in a solution; **RECONSTRUCT**: recover a question from its answer and partial clues). It produced one specialist
per task and one mixed model, and measured transfer between the tasks.

Phase 2 asks what these models are good for beyond their own test sets. Four experiments, with every result,
positive and negative:

| # | Experiment | Outcome |
|---|---|---|
| 1 | Specialists write hints for problems GRPO can no longer learn from | **Negative**: no hint beat a plain "answer X is wrong" control |
| 2 | Tutor: mark student solutions, including ones that answer the wrong question | **Positive**: RECONSTRUCT adds wrong-question detection on top of JUDGE |
| 3 | Self-checking solver: catch and repair wrong attempts, including "drift" to a different problem | **Negative**: checkers are near chance on the model's own long solutions |
| 4 | JUDGE on real errors (ProcessBench) instead of injected ones | **Mixed**: about half of the trained gain transfers |

The full write-up with all tables is [docs/experiments-summary.md](docs/experiments-summary.md); a one-page version
for slides is [docs/presentation-summary.md](docs/presentation-summary.md).

## Phase-1 recap (change vs the untrained 2B, test sets)

| Trained on | SOLVE accuracy | JUDGE error-finding | RECONSTRUCT score |
|---|---|---|---|
| SOLVE | **+16.6** | +8.8 | +3.8 |
| JUDGE | −1.1 | **+17.2** | +6.0 |
| RECONSTRUCT | −10.7 | +14.2 | **+21.4** |
| Mixed (1/3 each) | +17.1 | +32.2 | +18.3 |

## 1. Hints for always-wrong problems (negative)

After training, the mixed model answered the 750 SOLVE problems it trained on 8 times each. Problems it always gets
right or always gets wrong give GRPO no learning signal.

| Result over 8 tries | Problems |
|---|---|
| Always right | 291 (39%) |
| Sometimes right | 374 (50%) |
| Always wrong | 85 (11%), of which 39 genuinely wrong (the rest unreadable or cut off) |

For the 39, JUDGE was asked to find the first wrong step in a failed attempt and RECONSTRUCT to write the question the
wrong answer would be correct for; the mixed model then retried with each hint (23 non-Yes/No problems, 184 tries per
hint):

| Hint | Correct tries |
|---|---|
| None | 6 |
| RECONSTRUCT hint | 2 |
| "An earlier attempt got X, which is wrong" | 7 |
| JUDGE hint (only 5 problems had one) | 0 / 40 |

JUDGE found a usable wrong step in 0/39 attempts (5/39 with a 4× longer budget); RECONSTRUCT mostly rewrote the
original problem. Same-size specialists share the learner's blind spot.

## 2. Tutor (positive)

Students make two kinds of mistake: a **false step** (one line of maths is wrong; JUDGE finds it) and a **wrong
question** (every line is right but it solves a slightly different problem, e.g. divisors of k instead of k + 1).
For the second, RECONSTRUCT rebuilds the question the work actually answers and Qwen3.8-27B checks it against the
problem that was set. Test set: 200 correct and 200 false-step solutions from the JUDGE test set, plus 102
wrong-question solutions made by changing one detail of a correct solution's problem.

| Measure | Specialists | Mixed model |
|---|---|---|
| False-step solutions caught by JUDGE (exact step named) | 64.5% (55.5%) | 80.5% (72.5%) |
| Correct solutions wrongly flagged by JUDGE | 4.5% | 4.0% |
| Wrong-question solutions caught by JUDGE alone | 69.6% | 73.6% |
| … with RECONSTRUCT added, held-out threshold for 5% false alarms | 78.2% | 81.3% |
| … with RECONSTRUCT added, held-out threshold for 10% false alarms | 83.1% | 83.5% |
| Correct solutions flagged with RECONSTRUCT added (5% / 10% threshold) | 8.8% / 15.2% | 10.0% / 14.2% |

Thresholds are chosen on one half of the solutions and measured on the other (50 random splits, both directions).

## 3. Self-checking solver with drift detection (negative)

The mixed model made 4 attempts at each of 200 unseen problems (800 attempts, 242 wrong). JUDGE checked each attempt;
RECONSTRUCT rebuilt the question from the work so far at ¼, ½, ¾ and the end, and the 27B flagged drift from the real
problem. Flagged attempts were cut at the flag and regenerated.

| Checker | Flags wrong attempts | Flags correct attempts | AUROC |
|---|---|---|---|
| JUDGE (mixed) | 7.4% | 2.2% | 0.53 |
| Drift check (mixed) | 0.4% | 0.5% | 0.38 |

| Repair rule | Accuracy |
|---|---|
| None | 69.75% |
| Where JUDGE flagged | 70.13% |
| Random, same number | 69.75% |
| Perfect flags (every wrong attempt) | 76.75% |

Repair is worth about 7 points with perfect detection, but neither checker can find the wrong attempts. Only one wrong
attempt showed drift without a false step.

## 4. JUDGE on real errors: ProcessBench (mixed)

ProcessBench: 3,400 step-split solutions written by other models, with labelled first wrong steps. Same prompt and
sampling as on the synthetic JUDGE test set. Score: F1 of exact-first-error accuracy and correct-solution accuracy.

| Model | Injected errors (JUDGE test set) | Real errors (ProcessBench avg) |
|---|---|---|
| Untrained 2B | 44.7 | 41.1 |
| SOLVE-trained | 52.0 | 45.5 |
| JUDGE-trained | 68.9 | 54.6 |
| RECONSTRUCT-trained | 50.4 | 55.2 |
| Mixed | 79.5 | 59.8 |
| Qwen3.5-9B (reference) | 84.1 | 74.5 |

About half of the trained gain survives on real errors (mixed: +34.8 → +18.7). RECONSTRUCT training helps real
error-finding as much as JUDGE training. Not comparable with published ProcessBench numbers (different prompt and
sampling).

## Overall finding

| Input | Learned checking |
|---|---|
| Short step-numbered solutions, injected errors | Works |
| Short step-split solutions, real errors by other models | Partly (about half the gain) |
| Long unstructured solutions written by the checked model | Fails (near chance) |

## Layout

```
phase2/
  README.md            this file
  docs/                experiments-summary.md (full write-up), presentation-summary.md
  scripts/
    hint_pilot.py      experiment 1 (census, specialist hints, retries)
    functional.py      experiments 2 and 3 (tutor, drift solver); 27B comparator client
    tutor_calibrate.py held-out threshold for experiment 2 (CPU, reads results/)
    processbench_eval.py  experiment 4
    *.sbatch           Turing jobs; setup_env.sbatch builds the vLLM environment and model cache
  results/             curated outputs (no generated texts), see results/README.md
```

## Reproducing

Requirements: this repository's `src/anlp_project` (prompts, answer checker, strict gates) and
`data/manifests/final-v3`; the four Phase-1 LoRA adapters (`solve-step66`, `judge-step26`, `reconstruct-step104`,
`mixed-step75`; not in git, expected at `~/anlp-final-adapters`); a Turing allocation on node07. From the repository
root on Turing:

```bash
mkdir -p phase2/runs
sbatch phase2/scripts/setup_env.sbatch                                   # vLLM 0.30 env + Qwen3.5-2B, Qwen3.8-27B
REPOS=Qwen/Qwen3.5-9B sbatch phase2/scripts/setup_env.sbatch             # 9B for experiment 4
sbatch phase2/scripts/hint_pilot.sbatch                                  # experiment 1 (4 GPUs)
FOLLOWUP=1 sbatch --gres=gpu:2 phase2/scripts/hint_pilot.sbatch          # experiment 1 control arms
sbatch --gres=gpu:3 phase2/scripts/functional.sbatch                     # experiments 2 and 3
python phase2/scripts/tutor_calibrate.py --false-alarm 0.05              # experiment 2 held-out threshold
mkdir -p phase2/data/processbench && for f in gsm8k math olympiadbench omnimath; do \
  curl -sL -o phase2/data/processbench/$f.json https://huggingface.co/datasets/Qwen/ProcessBench/resolve/main/$f.json; done
sbatch phase2/scripts/processbench.sbatch                                # experiment 4 (3 GPUs)
```

Outputs go to `phase2/runs/` (ignored by git). The original runs, including full generated texts (about 140 MB
compressed), are on Turing under `/home/yashas.kotre/anlp-project-phase2/runs-out/`.

## Compute

| Job | Experiment | GPUs | GPU-hours |
|---|---|---|---|
| 43847 | Smoke test | 1 | 0.3 |
| 43854 | 1: census, specialists, hints | 4 | 5.3 |
| 43879 | 1: JUDGE 16k, control hint | 2 | 0.6 |
| 43908 | 2–3 smoke test | 3 | 1.1 |
| 43914 | 2–3 (stopped when the shared model cache was purged) | 3 | 12.2 |
| 43921 | 2–3 resumed | 3 | 1.0 |
| 43937 | 4: ProcessBench | 3 | 9.5 |
| | **Total** | | **30.0** |

## Caveats

- One seed and one sample per item in most measurements; the Phase-1 models themselves come from single runs with
  different recipes (see the Phase-1 report's limitations).
- Wrong-question solutions in experiment 2 were made by the 27B, not by real students; "closer to the solved problem"
  is the 27B's judgement.
- The 27B comparator's absolute probabilities are poorly calibrated; experiments 2 and 3 report threshold-free AUROC
  and held-out thresholds.
- ProcessBench scores use this project's JUDGE prompt and temperature-1 sampling.
