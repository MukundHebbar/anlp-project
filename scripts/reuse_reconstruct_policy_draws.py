#!/usr/bin/env python3
"""Reuse terminal draws for identical frozen requests across eligibility policies."""
import argparse
import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from anlp_project import reconstruct as r

p = argparse.ArgumentParser()
p.add_argument('--from-root', type=Path, required=True)
p.add_argument('--to-root', type=Path, required=True)
a = p.parse_args()
src = json.loads((a.from_root / 'student.json').read_text())
dst = json.loads((a.to_root / 'student.json').read_text())
sr = json.loads((a.from_root / 'student-requests.json').read_text())
dr = json.loads((a.to_root / 'student-requests.json').read_text())
assert r.stable_hash(sr) == src['metadata']['requests_hash']
assert r.stable_hash(dr) == dst['metadata']['requests_hash']
assert set(src['metadata']['jobs']) == set(src['metadata']['attempted_jobs'])
terminal = set(src['responses']) | {f['key'] for f in src['failures'] if f['stage'] == 'student'}
assert set(src['metadata']['jobs']) <= terminal
assert not dst['metadata']['attempted_jobs']
assert set(dr) <= set(sr)
assert src['metadata']['student_prompt_hash'] == dst['metadata']['student_prompt_hash']
srt = json.loads((a.from_root / 'local-runtime-provenance.json').read_text())
drt = json.loads((a.to_root / 'local-runtime-provenance.json').read_text())
assert srt['command_line'] == drt['command_line']
provenance = []
for key, request in dr.items():
    assert request == sr[key], key
    i = str(request['source_index'])
    assert src['sources'][i] == dst['sources'][i]
    if key in src['responses']:
        response = src['responses'][key]
        assert response['rendered_input_hash'] == request['rendered_input_hash']
        assert response['evidence_hash'] == request['evidence_hash']
        assert response['sampling'] == dict(temperature=.7, top_p=.8, top_k=20, max_tokens=8192, seed=0)
        dst['responses'][key] = copy.deepcopy(response)
    dst['failures'].extend(copy.deepcopy([f for f in src['failures'] if f['stage'] == 'student' and f['key'] == key]))
    dst['metadata']['attempted_jobs'].append(key)
    for stage in ['evaluations', 'source_recovery']:
        dst[stage].update(copy.deepcopy({k: v for k, v in src[stage].items() if v['response_key'] == key}))
    provenance.append(dict(response_key=key, from_root=str(a.from_root), rendered_input_hash=request['rendered_input_hash'], evidence_hash=request['evidence_hash'], response_hash=r.stable_hash(src['responses'].get(key)), reused_without_new_call=True))
dst['metadata']['draw_reuse'] = provenance
r.atomic_write_json(a.to_root / 'student.json', dst)
r.atomic_write_json(a.to_root / 'draw-reuse.json', provenance)
for name, field in [('response-math-review.json', 'rows')]:
    path = a.from_root / name
    if path.exists():
        obj = json.loads(path.read_text())
        obj[field] = [v for v in obj[field] if v['response_key'] in dr]
        if 'failed_attempt_reviews' in obj:
            indices = {v['source_index'] for v in dr.values()}
            obj['failed_attempt_reviews'] = [v for v in obj['failed_attempt_reviews'] if v['source_index'] in indices]
        obj['reused_from'] = str(path)
        r.atomic_write_json(a.to_root / name, obj)
print('Reused', len(dr), 'terminal draws; zero new model calls')
