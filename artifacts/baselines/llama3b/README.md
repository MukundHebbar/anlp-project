# Completed Llama GRPO evidence

[Transfer matrix](grpo-matrix.md) · [Training and evaluation code](../../../phase2/llama_transfer/README.md) ·
[Validation results](validation.json) · [Source checksums](source-manifest.json)

Collected and verified on 2026-10-30. Selected adapters: SOLVE step 106, JUDGE step 78, RECONSTRUCT step 104.
The fixed JUDGE step-104 endpoint is retained separately. All training configs specify `method=grpo`.

| Directory/file | Evidence |
|---|---|
| `test/<model>/s0` | 400 SOLVE + 400 JUDGE + 400 RECONSTRUCT responses/scores; 800 final Qwen judging records and calibrated scores |
| `test/<model>/s1`, `s2`, `s3` | The other three SOLVE samples (400 questions each) |
| `training/<task>` | Saved configs, all per-update metrics, completion records, train UIDs and original code provenance |
| `training/<task>/dev` | Candidate dev responses/scores and checkpoint selection; SOLVE also has `dev-base` |
| `training/probes` | Both eight-update probes, their 200-question × four-sample dev evaluations and LR selection |
| `training/staged-source` | Separately labelled source snapshots collected from the staged node03/node08 repos, not a replacement for frozen run manifests |
| `selection.json` | Dev-selected steps, independent of final test scores |

All JSONL evidence is committed as deterministic gzip. The report and validator accept compressed records
directly. Full generated training rollouts and available operational records are retained in the original
checkout's ignored `local/project-consolidation-2026-10-30/turing/`, with independent SHA-256 verification
against Turing. Existing local outputs were not replaced. The master results archive matched all 68 overlapping
files exactly. SOLVE test outputs were cross-checked across node03, node08 and the prior local copy; raw Qwen
records are retained independently of the derived calibrated scores.

Adapter and optimizer binaries are deliberately not in Git. At collection, selected adapters were present at:

- node03: `/scratch/mukund.hebbar/llama-transfer/runs/llama3b-solve/adapters/step106/`
- node08: `/scratch/mukund.hebbar/llama-transfer/runs/llama3b-judge/adapters/step78/`
- node08: `/scratch/mukund.hebbar/llama-transfer/runs/llama3b-reconstruct/adapters/step104/`

The four inspected selected/fixed-endpoint adapter files were 389,074,464 bytes each. Their presence does not
imply a permanent external backup. The earlier Hugging Face archive concerns historical Qwen adapters; this
collection does not claim that the new Llama adapters were uploaded there.

Interpretation: single training seed; Llama's untrained SOLVE accuracy is 9.0%, substantially below Qwen's
52.625%; Gemma training/dev rewards replace Jev and have measured reconstruction weaknesses. SOLVE LR is
2e-5 rather than Qwen's 1e-5. See the code README for calibration caveats and the matrix for paired intervals.
