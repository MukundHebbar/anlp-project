#!/usr/bin/env python3
"""User-requested 2/3-boundary revision on the frozen development cohort."""
import csv
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from anlp_project.reconstruct_partial_credit import BALANCED_V4_VERSION, BALANCED_V4_BOUNDARIES, balanced_rating, balanced_rating_v4

source = Path('artifacts/reconstruct/final-100-v1/questions-answers.jsonl')
root = Path('artifacts/reconstruct/balanced-ratings-v4')
root.mkdir(parents=True, exist_ok=True)
rows = [json.loads(line) for line in source.read_text().splitlines()]
for row in rows:
    score = (row['score'] or {}).get('score_100')
    row.update(rating_policy=BALANCED_V4_VERSION, previous_v3_rating=balanced_rating(score), balanced_v4_rating=balanced_rating_v4(score))
scored = [r for r in rows if r['balanced_v4_rating'] is not None]
old = Counter(r['previous_v3_rating'] for r in scored)
new = Counter(r['balanced_v4_rating'] for r in scored)
changed = [r['source_index'] for r in scored if r['previous_v3_rating'] != r['balanced_v4_rating']]
assert all(r['previous_v3_rating'] == 3 and r['balanced_v4_rating'] == 2 for r in scored if r['source_index'] in changed)
summary = dict(version=BALANCED_V4_VERSION, source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(), boundaries=BALANCED_V4_BOUNDARIES, allocated=len(rows), scored=len(scored), previous_histogram={i:old[i] for i in range(1,6)}, histogram={i:new[i] for i in range(1,6)}, changed_source_ids=changed, new_model_calls=0, selection_basis='User-requested post-hoc development calibration. Raise only the2/3 cutoff from37.5 to43.75. Six tied37.5-point responses move together; no per-example exceptions.', limitations='Numerical scores, judgments and success labels unchanged. A more symmetric ordinal histogram does not establish Gaussian scores or judge accuracy. No fresh-evaluation evidence.')
(root/'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
(root/'questions-answers.jsonl').write_text(''.join(json.dumps(r, ensure_ascii=False)+'\n' for r in rows))
with (root/'questions-answers.csv').open('w', newline='') as handle:
    writer = csv.writer(handle)
    writer.writerow(['source_index','source_question','source_answer','input_status','clues','qwen_question','qwen_justification','score_100','previous_v3_rating','balanced_v4_rating','semantic_equivalent','grounded_recovery'])
    for r in rows:
        s,q=r['score'] or {},r['qwen'] or {}
        writer.writerow([r['source_index'],r['source_question'],r['source_final_answer'],r['input_status'],'\n'.join(r['clues']),q.get('question'),q.get('justification'),s.get('score_100'),r['previous_v3_rating'],r['balanced_v4_rating'],r.get('semantic_equivalent'),r['provisional_grounded_recovery']])
lines=['# Rating policy v4: slightly more2s, fewer3s','','Only the2/3 boundary changes:37.5 becomes43.75. Rating3 now requires at least7/16 raw dimension points instead of6/16. All six responses at37.5 move from3 to2 together. Ratings1,4,5 are unchanged. Missing scores remain missing and shortcuts remain score0/rating1.','','| Rating | Score range | Previous count | Current count |','|---|---|---:|---:|']
for i,interval in [(1,'[0,18.75)'),(2,'[18.75,43.75)'),(3,'[43.75,56.25)'),(4,'[56.25,75)'),(5,'[75,100]')]:
    lines.append(f'| {i} | {interval} | {old[i]} | {new[i]} |')
lines+=['','This supersedes v3 as the current development display policy. It was chosen after inspecting these results at the user\'s request; it is not an independent experiment. The bins are no longer equally spaced. Keep all earlier versions and report the adaptation history in research. Freeze before fresh evaluation, with no promise of reproducing this distribution.','','Underlying mean44.41/100, two semantic recoveries and zero fully grounded recoveries are unchanged. Grade5 remains high partial credit rather than certified correctness. No new model calls were made.','','- [Updated questions, answers and paired ratings](questions-answers.csv)','- [Full JSONL](questions-answers.jsonl)','- [Counts, changed source IDs and provenance](summary.json)']
(root/'report.md').write_text('\n'.join(lines)+'\n')
print(json.dumps(summary,indent=2))
