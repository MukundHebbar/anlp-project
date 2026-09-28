#!/usr/bin/env python3
"""Revalidate all frozen raw judge outputs without any provider calls."""
import copy
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from anlp_project import reconstruct as r
from anlp_project.reconstruct_judge_validation import validate_judgment,validation_notes
SOURCE=Path('artifacts/reconstruct/judge-calibration-bd')
ROOT=Path('artifacts/reconstruct/judge-calibration-be')
source_manifest=json.loads((SOURCE/'manifest.json').read_text())
source_run=json.loads((SOURCE/'run.json').read_text())
assert source_run['metadata']['manifest_hash']==r.stable_hash(source_manifest)
assert source_manifest['validator_hash']==r.stable_hash((SOURCE/'validator-original.py').read_text())
failures={x['id']:x for x in source_run['failures']}
assert set(source_run['records'])|set(failures)=={c['id'] for c in source_manifest['cases']}, 'Source run still pending'
assert not (ROOT/'manifest.json').exists(), 'Replay already frozen'
ROOT.mkdir(exist_ok=True)
manifest=copy.deepcopy(source_manifest)
manifest.update(version='partial_credit_v4/BE-validator-replay',protocol='docs/plans/reconstruct-amendment-be.md',source_manifest_hash=r.stable_hash(source_manifest),source_run_hash=r.stable_hash(source_run),validator_hash=r.stable_hash(Path('src/anlp_project/reconstruct_judge_validation.py').read_text()),provider_calls=0)
state=dict(metadata={'manifest_hash':r.stable_hash(manifest),'provenance':'Deterministic replay of BD raw outputs, not independent model calls'},records={},failures=[],attempted=[])
for c in manifest['cases']:
 key=c['id'];state['attempted'].append(key)
 original=source_run['records'].get(key) or failures[key]
 out=original.get('output');raw=original.get('raw')
 try:
  if out is None:raise ValueError('No original parsed response; not repaired')
  validate_judgment(out,c['role'],question=c['question'],response=c.get('response'),clue_count=c['clue_count'])
  state['records'][key]=dict(output=out,raw=raw,case_hash=r.stable_hash(c),validation_notes=validation_notes(out,c.get('response',{})),source_id=key,source_was_structurally_accepted=key in source_run['records'])
 except Exception as exc:state['failures'].append(dict(id=key,error=str(exc),output=out,raw=raw))
r.atomic_write_json(ROOT/'manifest.json',manifest);r.atomic_write_json(ROOT/'run.json',state)
print('Replayed',len(state['attempted']),'outputs;',len(state['records']),'accepted;',len(state['failures']),'rejected. No model calls.')
