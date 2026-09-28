#!/usr/bin/env python3
"""Compare a versioned, more generous display policy on frozen responses. No API calls."""
import csv
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from anlp_project.reconstruct_partial_credit import (
    RELAXED_RATING_VERSION, RELAXED_RATING_BOUNDARIES, relaxed_rating,
)

source = Path('artifacts/reconstruct/final-100-v1/questions-answers.jsonl')
root = Path('artifacts/reconstruct/relaxed-ratings-v2')
root.mkdir(parents=True, exist_ok=True)
rows = [json.loads(line) for line in source.read_text().splitlines()]
for row in rows:
    row['rating_policy'] = RELAXED_RATING_VERSION
    row['relaxed_rating_1_to_5'] = relaxed_rating((row['score'] or {}).get('score_100'))
scored = [r for r in rows if r['relaxed_rating_1_to_5'] is not None]
old = Counter(r['score']['rating_1_to_5'] for r in scored)
new = Counter(r['relaxed_rating_1_to_5'] for r in scored)
summary = {
    'version': RELAXED_RATING_VERSION,
    'source_path': str(source),
    'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
    'new_boundaries': RELAXED_RATING_BOUNDARIES,
    'allocated': len(rows), 'scored': len(scored),
    'old_histogram': {i: old[i] for i in range(1, 6)},
    'new_histogram': {i: new[i] for i in range(1, 6)},
    'changed_ratings': sum(r['score']['rating_1_to_5'] != r['relaxed_rating_1_to_5'] for r in scored),
    'new_model_calls': 0,
    'interpretation': 'Post-hoc display-policy comparison on the same responses. Scores, judgments, gates and success labels unchanged. Not a performance improvement or independent validation.',
}
(root / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
(root / 'questions-answers.jsonl').write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in rows))
with (root / 'questions-answers.csv').open('w', newline='') as handle:
    writer = csv.writer(handle)
    writer.writerow(['source_index', 'source_question', 'source_answer', 'input_status', 'clues', 'qwen_question', 'qwen_justification', 'score_100', 'old_rating', 'relaxed_rating', 'semantic_equivalent', 'grounded_recovery'])
    for r in rows:
        s, q = r['score'] or {}, r['qwen'] or {}
        writer.writerow([r['source_index'], r['source_question'], r['source_final_answer'], r['input_status'], '\n'.join(r['clues']), q.get('question'), q.get('justification'), s.get('score_100'), s.get('rating_1_to_5'), r['relaxed_rating_1_to_5'], r.get('semantic_equivalent'), r['provisional_grounded_recovery']])
lines = ['# More generous ratings: v2', '',
         'Same frozen responses and quality scores; only the display thresholds change. This is an explicitly post-hoc policy choice, not a new model experiment.', '',
         '| Rating | Old score range | New score range | Old count | New count |',
         '|---|---|---|---:|---:|']
for i, previous, current in [(1, '[0,20)', '[0,20)'), (2, '[20,40)', '[20,40)'), (3, '[40,60)', '[40,50)'), (4, '[60,80)', '[50,70)'), (5, '[80,100]', '[70,100]')]:
    lines.append(f'| {i} | {previous} | {current} | {old[i]} | {new[i]} |')
lines += ['', f"Scored responses: {len(scored)}; changed labels: {summary['changed_ratings']}; new model calls: 0.", '',
          'A4 now denotes substantial partial reconstruction; a5 denotes strong aggregate reconstruction quality. Neither certifies semantic equivalence, a correct supplied answer, or a sufficient proof. Retain the source-equivalence and grounded-success flags alongside the rating. Missing scores remain missing, and known shortcuts remain score0/rating1.', '',
          'The underlying mean remains44.41/100. The two reviewed semantic matches and zero fully grounded successes are unchanged. The new histogram is an observed consequence of this policy; no Gaussian or middle-mode guarantee is made.', '',
          '- [Questions, answers and both ratings](questions-answers.csv)',
          '- [Full annotated JSONL](questions-answers.jsonl)',
          '- [Summary and input hash](summary.json)']
(root / 'report.md').write_text('\n'.join(lines) + '\n')
print(json.dumps(summary, indent=2))
