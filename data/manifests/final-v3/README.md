# FINAL-v3: SOLVE, JUDGE and RECONSTRUCT

The final dataset for training and testing. Three tasks, **4,000 questions each: 3,600 train /
400 test**. The tasks use completely separate DeepMath-103K questions: no question appears in two
tasks, counting every DeepMath copy of a question. Every row carries a `training` block with
input, chain of thought and final answer.

**Check:** `.venv/bin/python scripts/audit_final_dataset.py` → `PROBLEMS: none`. It needs only this
folder and the DeepMath parquet files in the git-ignored `data/datasets/deepmath-103k/`
(re-downloadable from HuggingFace `zwhe99/DeepMath-103K`).

## The three tasks

| Task | Model sees | Model produces |
|---|---|---|
| SOLVE | a math question | a solution and the final answer |
| JUDGE | a question plus a step-by-step proposed solution | correct/incorrect, the first wrong step, and why |
| RECONSTRUCT | a final answer plus 4 clues; the question is hidden | the original question |

## How each set was built

A **cell** is (topic, exact difficulty), with topics Algebra, Calculus, Discrete Mathematics
and Number Theory, and difficulty 5.0–8.0 in steps of 0.5. In every task the 400 test questions
are allocated to cells in proportion to cell size.

**JUDGE**: from the friend's 4,604 verified items:
1. Remove the 4 whose question is also in RECONSTRUCT, and 1 copy of a question that appeared
   twice → 4,599.
2. Remove **all 343 five-step items** → 4,256.
3. Remove **256 six-step items** from the friend's train split, spread over cells: 184 correct +
   72 incorrect. This ends at exactly **2,000 correct / 2,000 incorrect**. The 5-step items were
   79% incorrect, so removing them alone would have left 2,184 / 2,072.
4. Test: 200 correct + 200 incorrect, taken only from the friend's test split.

Item content (problem, proposed solution, label, error annotation, teacher response) is exactly
the friend's.

**RECONSTRUCT**: 4,000 of the 4,017 examples accepted by this project's two-step pipeline. Each
example is 4 clues generated from a DeepMath question with DeepSeek V4.1 Flash, then audited and,
if needed, corrected so the clues don't give the question away. Test comes only from sources that
no prompt development touched.

**SOLVE**: drawn from the full DeepMath-103K, with each cell's share set to the average of the
JUDGE and RECONSTRUCT shares (within 0.013 points). It excludes every question used for JUDGE
(all 5,000 originally assigned) or RECONSTRUCT (all 5,000 sources), plus earlier-used sets,
including duplicate copies.

All three were filtered the same way: topic in the four buckets, difficulty 5.0–8.0, a non-empty
answer, and three reference solutions present.

## Composition

| | SOLVE | JUDGE | RECONSTRUCT |
|---|---:|---:|---:|
| Algebra (train / test) | 893 / 99 | 870 / 97 | 919 / 101 |
| Calculus | 908 / 101 | 899 / 99 | 922 / 102 |
| Discrete Mathematics | 844 / 94 | 820 / 91 | 865 / 97 |
| Number Theory | 955 / 106 | 1,011 / 113 | 894 / 100 |
| Difficulty 5.0 | 746 / 82 | 726 / 81 | 765 / 85 |
| Difficulty 5.5 | 656 / 73 | 660 / 74 | 652 / 73 |
| Difficulty 6.0 | 771 / 86 | 775 / 87 | 767 / 84 |
| Difficulty 6.5 | 334 / 37 | 347 / 38 | 323 / 36 |
| Difficulty 7.0 | 372 / 42 | 376 / 40 | 370 / 41 |
| Difficulty 7.5 | 252 / 28 | 252 / 28 | 250 / 28 |
| Difficulty 8.0 | 469 / 52 | 464 / 52 | 473 / 53 |
| Upper band (7.0–8.0) | 30.4% | 30.3% | 30.4% |

**JUDGE:**

| | Train | Test |
|---|---:|---:|
| Correct / incorrect | 1,800 / 1,800 | 200 / 200 |
| 6 / 7 / 8 steps | 2,219 / 1,295 / 86 | 316 / 76 / 8 |
| Error early / middle / late (incorrect only) | 493 / 639 / 668 | 62 / 65 / 73 |

**RECONSTRUCT acceptance route:** 1,981 passed the original audit + copy check; 1,271 were
corrected by the audit-and-correct step; 748 were accepted unchanged by it.

Two properties of JUDGE come from the friend's data and the removal rules; they were not
stratified:
- **Topics are less even:** Number Theory 1,124 vs Discrete Mathematics 911.
- **Test is 79% six-step, train 62%**, because the friend's test split was mostly 6-step. If step
  count is an analysis variable, report results per step count.

## Row schema

Core fields, identical in every task:

| Field | Meaning |
|---|---|
| `task` | `solve`, `judge` or `reconstruct` |
| `split` | `train` or `test` |
| `uid` | `<task>-<dataset_row_index>` |
| `dataset_row_index` | row in DeepMath-103K |
| `source_group_id` | 16-hex hash of the whitespace/case-normalized question (dedup key) |
| `topic` | DeepMath's detailed topic, e.g. `Mathematics -> Number Theory -> Congruences` |
| `broad_topic` | Algebra, Calculus, Discrete Mathematics, or Number Theory |
| `difficulty` | DeepMath difficulty, 5.0–8.0 (float) |
| `difficulty_band` | `lower` (5.0–6.5) or `upper` (7.0–8.0) |
| `question` | the full question |
| `final_answer` | the answer |
| `answer_normalization` | `null`, or a record when a bare multiple-choice label (e.g. `C`) was replaced by its option text (11 SOLVE, 9 RECONSTRUCT rows) |
| `reference_solutions` | DeepMath's three DeepSeek-R1 solutions (long chain of thought; not verified by this project) |
| `source` | provenance |
| `training` | `{input, chain_of_thought, final_answer}`, see below |

Task-specific fields:

- **judge:**
  - `steps`, `label`, `error_position`.
  - `public` (the model's input): `problem`, `proposed_solution` (S1..Sn), `instruction`.
  - `private` (the answer key): `label`, `first_error_step_id`, `first_error_explanation`, `error_type`, `error_position`, `teacher_target_response`.
  - `friend`: the friend's `assignment_id`, original split, `source_id`, `replacement_generation`, `generation_record_sha256`.
- **reconstruct:**
  - `public_input` (the model's input): `final_answer` plus 4 `clues`.
  - `accepted_by`, `v1_status`, `audit_correct` (decision, per-clue findings, reason).
  - `original_public_input` and `corrected_hidden_support`: set on corrected rows.
  - `advisory_fresh_check`: an extra audit/copy verdict on some corrected rows. It was not used to accept or reject.

## Training layout

| Task | `training.input` | `training.chain_of_thought` | `training.final_answer` |
|---|---|---|---|
| SOLVE | the question | `reference_solutions[0]` | the final answer |
| JUDGE | problem + numbered proposed solution + instruction | `null` (the items have no separate reasoning trace) | the friend's `teacher_target_response` (decision, first wrong step, explanation) |
| RECONSTRUCT | final answer + the 4 numbered clues | `reference_solutions[0]` for the original problem | **the original question, in full** |

Notes on the RECONSTRUCT target:
- The input never contains the original question; this is checked on every row.
- The chain of thought was written while solving the original problem. It usually restates the
  question in its first line, so the target shows the question before giving it as the final
  answer.
- `docs/design/reconstruct/SKILL.md` §8 cautions that the source question as target can reward
  guessing the original rather than inferring a problem the clues support. Evaluate trained
  models with the source-blind validity judge as well as source recovery.

## Verification

`scripts/audit_final_dataset.py` checks, on all 12,000 rows:
- every field against DeepMath (question, topic, difficulty, answer, all three reference solutions)
- internal consistency (IDs, hashes, bands, topic mapping, JUDGE step IDs and annotations
  agreeing with labels and teacher targets, RECONSTRUCT correction records)
- no answer-key or source-question leakage into any training input
- no question shared across tasks
- the split, stratification, label and SOLVE-profile rules above

Two rules were verified before intermediate files were removed, since they need files outside
this folder. RECONSTRUCT test comes only from untouched sources, and SOLVE excludes every
question ever assigned to JUDGE or RECONSTRUCT, even ones later dropped.

## Provenance

- Build method: `scripts/build_final_datasets_v2.py` (selection) → `scripts/build_final_datasets_v3.py` (training block).
- These scripts read intermediate dataset versions that have since been deleted, so they document
  the method but can no longer be re-run end to end.
- Build records are archived in the git-ignored `local/archive/legacy/`:
  - `reconstruct-dataset-v1-build/`: RECONSTRUCT's raw API outputs from all rounds, clue banks,
    evidence, per-source outcome logs, the base allocation, and the exclusion set.
  - `judge_data/`: the friend's JUDGE files.

## Files

In git: `{solve,judge,reconstruct}-{train,test}.jsonl.gz`, `summary.json`, `CHECKSUMS.txt`,
this README. The files are gzipped because the raw train files (200–265 MB) exceed GitHub's
100 MB limit. Each `.gz` decompresses to exactly the raw `.jsonl`, and `CHECKSUMS.txt` lists both.
The audit script reads either form.

```python
import gzip, json
rows = [json.loads(line) for line in gzip.open('data/manifests/final-v3/solve-train.jsonl.gz', 'rt')]
```

```bash
gunzip -k data/manifests/final-v3/*.jsonl.gz   # optional: restore the raw .jsonl files
```
