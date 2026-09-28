#!/usr/bin/env python3
"""Report AT paired controls, preserving the frozen reference-label defect."""
import json
from pathlib import Path

root = Path('artifacts/reconstruct/judge-scope-at')
manifest = json.loads((root/'manifest.json').read_text())
run = json.loads((root/'run.json').read_text())
failures = {f['id']: f for f in run['failures']}
expected_jobs = {p+':'+c['id'] for p in manifest['prompt_hashes'] for c in manifest['cases']}
assert expected_jobs == set(run['records']) | set(failures), 'AT calls are not all terminal'
rows = []
for case in manifest['cases']:
    corrected = 0 if case['id'] == 'rectangle_scope-contrast' else case['expected_score']
    row = dict(case_id=case['id'], family=case['family'], frozen_expected=case['expected_score'],
               adjudicated_expected=corrected, predictions={}, failures={})
    for prompt in manifest['prompt_hashes']:
        key = prompt+':'+case['id']
        output = run['records'].get(key, {}).get('output', {})
        row['predictions'][prompt] = output.get('score') if output.get('status') == 'scored' else None
        if key in failures: row['failures'][prompt] = failures[key]['error']
    rows.append(row)
stats = {}
for prompt in manifest['prompt_hashes']:
    available = [x for x in rows if x['predictions'][prompt] is not None]
    stats[prompt] = dict(planned=len(rows), scored=len(available), missing=len(rows)-len(available),
        frozen_label_matches=sum(x['predictions'][prompt] == x['frozen_expected'] for x in available),
        adjudicated_matches=sum(x['predictions'][prompt] == x['adjudicated_expected'] for x in available),
        false_full_credit=sum(x['predictions'][prompt] == 4 and x['adjudicated_expected'] < 3 for x in available))
result = dict(stats=stats, rows=rows, adopted=False,
    limitations=['Authored, related development controls; no independent population accuracy estimate.',
                 'One frozen label corrected after observing judge output; raw and adjudicated agreement both shown.',
                 'Missing judgments stay in planned denominators; no retries or model-output edits.'])
(root/'comparison.json').write_text(json.dumps(result, indent=2)+'\n')
lines = ['# AT: judge scope and consistency', '',
         '| Judge | Scored/planned | Frozen-reference matches | Adjudicated matches | False full credit |',
         '|---|---:|---:|---:|---:|']
for prompt, s in stats.items():
    lines.append(f"| {prompt} | {s['scored']}/{s['planned']} | {s['frozen_label_matches']} | {s['adjudicated_matches']} | {s['false_full_credit']} |")
lines += ['', 'Counts refer to the same planned twelve controls. Adjudicated matches are development agreement, not independent accuracy.', '',
          '| Control | Frozen / corrected label | p3 | p4 |', '|---|---|---:|---:|']
for x in rows:
    lines.append(f"| {x['case_id']} | {x['frozen_expected']} / {x['adjudicated_expected']} | {x['predictions']['evaluate_p3']} | {x['predictions']['evaluate_p4_standalone']} |")
lines += ['', 'No evaluator is promoted.'] + result['limitations']
(root/'comparison.md').write_text('\n'.join(lines)+'\n')
print(json.dumps(stats, indent=2))
