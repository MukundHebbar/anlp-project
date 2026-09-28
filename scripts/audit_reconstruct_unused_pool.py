#!/usr/bin/env python3
"""Metadata-only exposure audit of proposed new development IDs; no API calls."""
import json,sys
from pathlib import Path
from collections import Counter
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from anlp_project import reconstruct as r
allocation=json.loads(Path('data/manifests/reconstruct-d4-allocation-v1.json').read_text())
canonical=json.loads(Path('artifacts/reconstruct/followup-v2/run.json').read_text())['sources']
pool=allocation['partitions']['contingency_remaining'];protected=set(allocation['partitions']['C25_proposed']+allocation['partitions']['R'])
assert not set(pool)&protected
hits=[];scanned=0
for path in Path('artifacts/reconstruct').rglob('*.json'):
    try:obj=json.loads(path.read_text())
    except (ValueError,OSError):continue
    if not isinstance(obj,dict) or not isinstance(obj.get('sources'),dict):continue
    scanned+=1;sources=obj['sources']
    for i in pool:
        s=sources.get(str(i));ref=canonical[str(i)]
        if not isinstance(s,dict):continue
        if s.get('question')!=ref['question'] and (not s.get('source_id') or s.get('source_id')!=ref.get('source_id')):continue
        for section in ('banks','responses','evaluations','source_recovery','audits','copy_challenges'):
            records=obj.get(section,{})
            if isinstance(records,dict) and any(isinstance(v,dict) and v.get('source_index')==i for v in records.values()):hits.append({'source_index':i,'artifact':str(path),'section':section})
result={'purpose':'Prospective development-pool exposure audit; no student outcome values used in selection','pool':pool,'pool_size':len(pool),'protected_partitions_disjoint':True,'allocation_hash':r.stable_hash(allocation),'source_identity_hashes':{str(i):r.stable_hash(canonical[str(i)]['question']) for i in pool},'topic_counts':dict(Counter(canonical[str(i)]['broad_topic'] for i in pool)),'source_artifacts_scanned':scanned,'prior_reconstruct_stage_hits':hits,'limitation':'Exact question or source_id identity check, not semantic near-duplicate adjudication. Historical SOLVE evaluations may exist; no their outcomes were inspected for this allocation. Absence of a saved stage record is not proof of no earlier human exposure.'}
r.atomic_write_json(Path('artifacts/reconstruct/followup-v2/unused-pool-exposure-audit.json'),result)
print(json.dumps({'pool_size':len(pool),'source_artifacts_scanned':scanned,'prior_reconstruct_stage_hits':len(hits)}))
