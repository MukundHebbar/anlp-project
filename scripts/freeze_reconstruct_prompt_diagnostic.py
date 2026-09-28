#!/usr/bin/env python3
"""Freeze amendment O's four exact inputs; leave inference blocked pending review."""
import copy
import json
from pathlib import Path
from anlp_project.reconstruct import accepted_bank, condition_evidence, stable_hash, utc_now
from anlp_project.storage import atomic_write_json


def main():
    parent=Path('artifacts/reconstruct/d3-v2/run.json')
    path=Path('artifacts/reconstruct/d3-v2/prompt-diagnostic.json')
    if path.exists():raise ValueError('Never overwrite a frozen diagnostic')
    base=json.loads(parent.read_text())
    indices=[8,27,33,77]
    selected={i:accepted_bank(base,i,'convert_p3') for i in indices}
    run=copy.deepcopy(base)
    keys={key for key,bank in selected.values()}
    run['banks']={k:v for k,v in run['banks'].items() if k in keys}
    run['sources']={str(i):base['sources'][str(i)] for i in indices}
    run['audits']={k:v for k,v in run['audits'].items() if v['bank_key'] in keys}
    for section in ['responses','evaluations','source_recovery','copy_challenges']:run[section]={}
    run['failures']=[]
    public={}
    for i,(key,bank) in selected.items():
        e=condition_evidence(run['sources'][str(i)],'bank',bank=bank,
                            clue_count=len(bank['output']['clues']),clue_seed=20260920,
                            style='sentence',selection_policy='bank_order')
        e['disclosure']='medium'
        public[str(i)]={'bank_key':key,'evidence':e,'evidence_hash':stable_hash(e)}
    run['metadata'].update(study='amendment O, fixed four-source prompt alignment diagnostic',
       parent_artifact=str(parent),parent_snapshot_hash=stable_hash(base),frozen_at=utc_now(),
       diagnostic_source_indices=indices,full_policy_coverage_passed=False,
       frozen_public_inputs=public,
       student_readiness={'status':'pending_copy_and_independent_review','approved_evidence_hashes':{}})
    atomic_write_json(path,run)
    atomic_write_json(path.with_name('prompt-diagnostic-inputs.json'),public)
    print('Frozen four accepted inputs; student inference remains blocked pending copy/domain reviews.')


if __name__=='__main__':main()
