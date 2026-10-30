# SOLVE-only learning-rate controls for mixed GRPO

Completed 2026-10-27. The full method and results are in
[the experiment README](../../mix_control/README.md#completed-lower-learning-rate-validation-2026-10-27).

The formerly missing run, `ctrl-lr1e-5-s1`, scores **63.1% avg@4 and 84.2% pass@4** on the same 348 eligible
validation questions as the six other arms. The mixed checkpoint scores **71.0% avg@4 and 85.3% pass@4**.
Mixed minus the two-seed SOLVE-only mean is **+5.4 [3.0, 7.8]**, **+8.0 [5.6, 10.5]**, and **+9.3 [6.9, 11.8]**
avg@4 points at learning rates 2e-5, 1e-5, and 6.7e-6, respectively. Intervals are paired 95% question-bootstrap
intervals (10,000 resamples, seed 0). They do not cover training-run uncertainty; mixed has a single training seed.

| File | Contents |
|---|---|
| `lower-lr-decision.txt` | Output of the unchanged pre-set `phase2/mix_control/decide_lr.py` rule |
| `summary.json` | Pooled and per-split metrics, protocol and job identifiers |
| `paired-question-outcomes.jsonl.gz` | Four correctness indicators per arm for each of the 348 included questions |
| `validation-scores.jsonl.gz` | All 11,200 source scores: seven arms × two 200-question splits × four samples, including excluded rows |
| `evaluation-metadata.json` | Metadata for the 14 evaluations |
| `source-checksums.json` | SHA-256 of each of the 56 source score files |
| `recovery-provenance.json` | Saved training configuration, checkpoint and response checksums, job states, and environment repair provenance |

The 348-question set is 199 dev + 149 val200, using the existing exclusions in `decide.py`. Every arm has exactly
the same included questions and four samples per question. All evaluations use prompt v2, temperature 1, top-p 1,
top-k 0, evaluation seed 0, a 16k first pass and continuation to a 32k total cap. Only validation was recovered;
the lower-learning-rate test comparisons have not been run as part of this recovery.

Training job 51700 completed on node07. Earlier evaluation job 51980 failed before model loading because its
scratch Python environment was incomplete. Recovery attempt 52200 failed a stale check of the mirrored Python
symlink. After fixing the two wrapper checks, dev job 52201 and val200 job 52202 completed successfully on node07
under account `priyesh.shukla`. The two completed evaluations used 3,223 GPU-seconds (0.895 GPU-hours); the failed
recovery attempt used one additional GPU-second. Node14 was not used.

Full generated responses for the recovered run are retained, compressed, in the ignored local directories
`local/mix-control/evals/{dev,val200}-ctrl-lr1e-5-s1-step75/`. No checkpoint was retrained and no scoring rule,
exclusion, prompt, sampling setting, or pre-set decision rule was changed.

## Reproduce from the committed evidence

Run `python phase2/mix_control/reproduce.py` from the repository root. It reconstructs the 56 score files in
an isolated temporary directory, checks all 11,200 raw scores against the 348 filtered paired outcomes and
published means, and executes the unchanged pre-set LR decision rule. Its output must equal
`lower-lr-decision.txt`. No models, training, credentials or API calls are needed.

There are two training seeds **per SOLVE-only control learning rate** (six control runs). The mixed model
itself has **one** training seed. This collection does not claim two mixed-model seeds.
