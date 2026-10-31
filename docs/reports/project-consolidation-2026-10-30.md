# Results and code publication — 30 October 2026

Publication branch: `results/project-consolidation-2026-10-30`, based on `origin/phase2-experiments`
(`f7f419ac09212bb9202929effe0550e1a503be18`). The original dirty `phase2-failure-driven` checkout and both
user-supplied reports were preserved; the latter are byte-identical. Existing remote branches were not merged
or rewritten. Independent Phase 3 code remains on its own branch.

## Included work

- [Completed Llama GRPO transfer study](../../artifacts/baselines/llama3b/README.md): three single-seed arms,
  development selection, five full cross-task test evaluations, and final Qwen judging. Selected steps are
  SOLVE 106, JUDGE 78 and RECONSTRUCT 104; JUDGE 104 is also preserved as a fixed endpoint.
- [Task-mixture controls](../../phase2/results/mix-control/README.md): two seeds at each of three SOLVE-only
  learning rates, compared with the one-seed mixed checkpoint. Frozen inputs and the original decision rule
  are included, along with an offline reproduction wrapper.
- Supporting Gemma/Selene calibration records, Ministral baseline, and the existing non-OPD adapter archive
  inventory. Failed archive copies are documented by that original inventory, not claimed recovered here.
- The latest Phase 2 report and the separately named working report, with navigation from the root README.

Additional unpublished failure-driven experiments were omitted following the user's scope update. The base
branch's existing pilot remains. Two tiny frozen UID/exclusion lists and the portable runtime wrapper under
that directory are included because the mixture/Llama workflows require them. This collection adds no OPD
training or OPD adapter weights; shared training modules retain their historical `opd` filenames.

## Verification performed

- Independently hashed **900 collected files** on Turing and locally: zero mismatches. Retained all sources
  in the original checkout's ignored `local/project-consolidation-2026-10-30/turing/` archive.
- Existing local results matched all 68 overlapping files from the master results archive. Another 90 test
  files matched their node08 copies. Original JSONL bytes were preserved exactly through gzip compression.
- Verified 106 SOLVE updates and 104 JUDGE/RECONSTRUCT updates, training/dev/test separation, selection rules,
  400 test items per task, 1,600 SOLVE responses/model and 800 final Qwen scores/model.
- Regenerated the Llama matrix byte-for-byte: SHA-256
  `d591e1a53b78111f662a842ba974df05a666c0729cf9963a3f907eecc45244f6`.
- Reproduced the mixture controls from all 11,200 raw scores, the 348 filtered question outcomes and the
  unchanged bootstrap rule: saved decision output matched exactly.
- Passed 31 targeted regression tests covering reward compatibility, self-judge verdict-only/no-judge behavior,
  Llama/Gemma transport/configs, shutdown supervision, calibration, evaluation and existing mixed-GRPO behavior.
- Compiled relevant Python entry points and reviewed changes for whitespace, conflict markers, credentials,
  model binaries and large files. No training, GPU allocation or paid judging was used for this collection.

## Reproduce offline

```bash
python phase2/llama_transfer/validate_results.py
python phase2/llama_transfer/report.py
python phase2/mix_control/reproduce.py
```

Use the project's regular installed Python dependencies. Evidence readers support committed compressed JSONL;
no private runtime, model download or `.env` is required for these three commands.

## Limits

Adapter/optimizer binaries and full operational logs are intentionally outside Git. The selected Llama adapter
paths were checked, but no new Hugging Face weight upload was performed. The mixed model and each Llama arm
have one training seed; control seeds do not establish mixed-model seed uncertainty. Llama's starting SOLVE
accuracy is much weaker than Qwen's, and Gemma replaces Jev for Llama training/dev rewards. These differences
and the historical calibration's test-derived examples remain explicit in the experiment documentation.
