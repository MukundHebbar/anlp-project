#!/usr/bin/env python3
"""Freeze and audit balanced display bands on saved development responses."""
import csv
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from anlp_project.reconstruct_partial_credit import (
    BALANCED_RATING_VERSION, BALANCED_RATING_BOUNDARIES, balanced_rating, relaxed_rating,
)

source = Path('artifacts/reconstruct/final-100-v1/questions-answers.jsonl')
root = Path('artifacts/reconstruct/balanced-ratings-v3')
root.mkdir(parents=True, exist_ok=True)
rows = [json.loads(line) for line in source.read_text().splitlines()]
for row in rows:
    row['rating_policy'] = BALANCED_RATING_VERSION
    row['balanced_rating_1_to_5'] = balanced_rating((row['score'] or {}).get('score_100'))
scored = [r for r in rows if r['balanced_rating_1_to_5'] is not None]
old = Counter(r['score']['rating_1_to_5'] for r in scored)
relaxed = Counter(relaxed_rating(r['score']['score_100']) for r in scored)
new = Counter(r['balanced_rating_1_to_5'] for r in scored)
summary = {
    'version': BALANCED_RATING_VERSION,
    'source_path': str(source),
    'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
    'boundaries': BALANCED_RATING_BOUNDARIES,
    'allocated': len(rows), 'scored': len(scored),
    'original_histogram': {i: old[i] for i in range(1, 6)},
    'relaxed_v2_histogram': {i: relaxed[i] for i in range(1, 6)},
    'balanced_v3_histogram': {i: new[i] for i in range(1, 6)},
    'new_model_calls': 0,
    'inspected_candidate_scales': [
        {'boundaries': cuts, 'histogram': {i: sum(1 + sum(r['score']['score_100'] >= c for c in cuts) == i for r in scored) for i in range(1, 6)}}
        for cuts in [(20, 40, 60, 75), (18.75, 37.5, 56.25, 75), (12.5, 31.25, 50, 68.75), (25, 37.5, 56.25, 70)]
    ],
    'selection_basis': 'Post-hoc development calibration after inspecting this cohort. Equal18.75-point spacing between adjacent cutoffs; no per-example rules or quantile assignment. Freeze before new evaluation.',
    'limitations': 'A middle-peaked ordinal histogram is not evidence of Gaussian scores or judge validity. Underlying numerical scores, source gates and success labels are unchanged. Future distribution is not guaranteed.',
}
(root / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
(root / 'questions-answers.jsonl').write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in rows))
with (root / 'questions-answers.csv').open('w', newline='') as handle:
    writer = csv.writer(handle)
    writer.writerow(['source_index', 'source_question', 'source_answer', 'input_status', 'clues', 'qwen_question', 'qwen_justification', 'score_100', 'original_rating', 'relaxed_v2_rating', 'balanced_v3_rating', 'semantic_equivalent', 'grounded_recovery'])
    for r in rows:
        s, q = r['score'] or {}, r['qwen'] or {}
        writer.writerow([r['source_index'], r['source_question'], r['source_final_answer'], r['input_status'], '\n'.join(r['clues']), q.get('question'), q.get('justification'), s.get('score_100'), s.get('rating_1_to_5'), relaxed_rating(s.get('score_100')), r['balanced_rating_1_to_5'], r.get('semantic_equivalent'), r['provisional_grounded_recovery']])
lines = ['# Balanced rating policy v3', '',
         'This supersedes the generous v2 display policy. It is a development-calibrated scale, selected after inspecting the same47 resolved scores, not a new model experiment or independently validated rubric.', '',
         '| Rating | Score range | Dimension sum, when fully scored | Original count | v2 count | v3 count |',
         '|---|---|---|---:|---:|---:|']
for i, interval, total in [(1, '[0,18.75)', '0–2'), (2, '[18.75,37.5)', '3–5'), (3, '[37.5,56.25)', '6–8'), (4, '[56.25,75)', '9–11'), (5, '[75,100]', '12–16')]:
    lines.append(f'| {i} | {interval} | {total} | {old[i]} | {relaxed[i]} | {new[i]} |')
lines += ['', 'The four cutoffs are equally spaced by18.75 score points (three raw dimension points). Rating3 captures moderate partial reconstruction;4 requires at least9/16 raw points;5 requires12/16. Scores are bounded, so the uppermost band includes the ceiling. A known shortcut remains score0/rating1 regardless of its raw dimensions.', '',
          'Selection rationale: v2 put too many moderate50-point responses in4. This policy puts50 in3,56.25 in4, and75 in5, using one global set of fixed thresholds. This calibration was informed by the current outcomes and must be described that way in a paper. It is not evidence of better model performance.', '',
          'Freeze these cutoffs for subsequent evaluation. Do not keep shifting them to preserve a desired histogram; report any future skew. Do not use ranks, quotas, item replacement or modified mathematical judgments to manufacture a Gaussian distribution. The current histogram is middle-peaked with sparse tails, not exactly symmetric or a demonstrated normal distribution.', '',
          'Numerical mean44.41/100, semantic recoveries2, and fully grounded recoveries0 remain unchanged. Grade5 remains high partial credit, not certified correctness. The original outputs, missingness and gate exclusions remain intact.', '',
          '- [Questions, answers and all three rating versions](questions-answers.csv)',
          '- [Annotated JSONL](questions-answers.jsonl)',
          '- [Policy provenance and counts](summary.json)']
(root / 'report.md').write_text('\n'.join(lines) + '\n')
print(json.dumps(summary, indent=2))
