#!/usr/bin/env python3
"""Render the completed matched prompt screen from machine-readable analysis."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
directory=ROOT/'artifacts/reconstruct/followup-v2'
data=json.loads((directory/'prompt-comparison.json').read_text())
assert all(v['resolved']==v['planned']==24 for v in data['arms'].values())
names={'student_p1':'Compact one-shot baseline','student_p5':'Verification-first field order',
       'student_p6':'Order plus explicit consistency instruction','student_p7':'Two inverse-construction examples'}
lines=['# Matched prompt screen: completed development result','',
       'Twelve D2 sources, two decoding seeds per source, identical full-bank sentence evidence, '
       'local non-thinking Qwen3-4B Q4_K_M, fixed evaluate_p2. All 96 outputs have judgments. '
       'One malformed JSON output was recovered from saved raw text without new generation.','',
       'Subsequent validity review rejected source131 for exposing essentially the full solution. '
       'Both baseline successes came from that source. Preserve this historical comparison, but consult '
       '[the validity sensitivity analysis](baseline-validity-sensitivity.md) before making a task-quality claim.','',
       '| Arm | Mean /100 | Source-bootstrap 95% interval | Grounded successes | Mean completion tokens |',
       '|---|---:|---|---:|---:|']
for arm,x in data['arms'].items():
    ci=x['normalized_score_complete_sources']['source_bootstrap_95_interval']
    lines.append(f"| {names[arm]} | {x['mean_normalized_score_resolved']:.2f} | [{ci[0]:.2f}, {ci[1]:.2f}] | {x['successes']}/24 | {x['mean_completion_tokens']:.1f} |")
lines+=['','Two samples of one source are not independent sources; intervals resample 12 source means. '
        'All four development means satisfy the requested 20–75 band. This does not make all four useful or equally good.','',
        '| Candidate versus baseline | Paired mean difference /100 | Source-bootstrap 95% interval |',
        '|---|---:|---|']
for arm,x in data['comparisons'].items():
    stat=x['normalized_score_source_averaged'];ci=stat['source_bootstrap_95_interval']
    lines.append(f"| {names[arm]} | {stat['mean_difference']:+.2f} | [{ci[0]:.2f}, {ci[1]:.2f}] |")
lines+=['','## Decision','',
        'Retain student_p1 as the provisional single-call incumbent. None of the three prompt-only '
        'changes demonstrates a reliable gain. This is a simplicity decision under uncertainty, '
        'not proof that student_p1 is superior or that the alternatives are equivalent. The intervals '
        'remain wide and the same sources motivated some adaptations. Fresh confirmation is still required.','',
        'The supplied answer is often ignored even after the response derives a conflicting result. '
        'For source 30, the baseline asks for Log\'(1), derives 1, and fails to match the supplied answer 2. '
        'For source 95, it computes a parameter-dependent integral but omits the limiting operation '
        'needed for the supplied zero. These cases motivate testing additional orientation and explicit '
        'self-revision, but do not establish that those interventions work.','',
        '## Reproducibility and limits','',
        '- Analysis: [prompt-comparison.json](prompt-comparison.json). Raw records: [run.json](run.json). '
        'Full case export: [cases.md](cases.md).',
        '- Regenerate with `scripts/analyze_reconstruct_followup.py --run artifacts/reconstruct/followup-v2/run.json '
        '--output artifacts/reconstruct/followup-v2/prompt-comparison.json --arms student_p1 student_p5 student_p6 student_p7`, '
        'then this report script.',
        '- Runtime defaults: [server-props.json](server-props.json), [runtime-notes.json](runtime-notes.json). '
        'Requests omit min-p and inherit approximately 0.05. Do not pool with historical vLLM results.',
        '- Labels are DeepSeek evaluate_p2 judgments. Independent gold calibration and mathematical '
        'adjudication are separate, incomplete validation steps; no near-perfect accuracy claim follows from this table.',
        '- C is untouched. No training-transfer result has been measured.',
        '- Bootstrap intervals are descriptive development estimates; adaptive search and small source '
        'count limit inference. No global optimality or exact equivalence is claimed.','']
(directory/'prompt-screen.md').write_text('\n'.join(lines))
print('Wrote',directory/'prompt-screen.md')
