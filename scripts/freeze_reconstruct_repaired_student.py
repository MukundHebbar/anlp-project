#!/usr/bin/env python3
"""Freeze amendment S inputs only after exact-bank math and copying review."""
import copy
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from anlp_project.reconstruct import stable_hash,condition_evidence,atomic_write_json,utc_now


def main():
    root=Path('artifacts/reconstruct/d3-v2')
    target=root/'repaired-student.json'
    if target.exists():raise ValueError('Never overwrite frozen student data')
    parent=json.loads((root/'repair-study.json').read_text())
    copies=json.loads((root/'repair-copy-review.json').read_text())
    maths=json.loads((root/'repair-input-math-review.json').read_text())
    math_rows={r['source_index']:r for r in maths['rows']}
    selected=[r for r in copies['rows'] if r['development_eligible_after_review']]
    indices=sorted(r['source_index'] for r in selected)
    assert indices==[8,27,33,77,86,112,136,141,143]
    keys={r['bank_key'] for r in selected}
    run={'metadata':{'study':'amendment S: reviewed one-repair evidence policy',
            'frozen_at':utc_now(),'parent_snapshot_hash':stable_hash(parent),
            'diagnostic_source_indices':indices,'original_source_denominator':12,
            'release_coverage_passed':False,'teacher_reliability_established':False},
         'sources':{str(i):copy.deepcopy(parent['sources'][str(i)]) for i in indices},
         'partitions':copy.deepcopy(parent['partitions']),
         'banks':{k:copy.deepcopy(parent['banks'][k]) for k in keys},
         'audits':{k:copy.deepcopy(v) for k,v in parent['audits'].items() if v.get('bank_key') in keys},
         'copy_challenges':{k:copy.deepcopy(v) for k,v in parent['copy_challenges'].items() if v.get('bank_key') in keys},
         'responses':{},'evaluations':{},'source_recovery':{},'failures':[]}
    frozen={}
    for row in selected:
        i=row['source_index'];bank=run['banks'][row['bank_key']]
        assert stable_hash(bank['output'])==row['bank_output_hash']==math_rows[i]['bank_output_hash']
        assert stable_hash(run['sources'][str(i)])==row['source_record_hash']==math_rows[i]['source_record_hash']
        assert row['known_direct_source_disclosure'] is False
        assert math_rows[i]['mathematical_support_review']=='supported_under_stated_local_domain'
        status={v['prompt']:v['output']['status'] for v in run['audits'].values() if v['bank_key']==row['bank_key']}
        assert all(status.get(p)=='ACCEPT' for p in ['audit_support_p1','audit_public_p4','audit_source_disclosure_p2'])
        evidence=condition_evidence(run['sources'][str(i)],'bank',bank=bank,
                 clue_count=len(bank['output']['clues']),clue_seed=20260920,style='sentence',selection_policy='bank_order')
        evidence['disclosure']='medium'
        frozen[str(i)]={'bank_key':row['bank_key'],'evidence':evidence,'evidence_hash':stable_hash(evidence)}
    run['metadata']['frozen_public_inputs']=frozen
    run['metadata']['student_readiness']={'status':'ready',
        'approved_evidence_hashes':{i:r['evidence_hash'] for i,r in frozen.items()},
        'scope':'Development only: assistant mathematical/semantic reviews, not independent human release validation',
        'review_artifacts':{str(root/name):stable_hash(json.loads((root/name).read_text()))
            for name in ['repair-copy-review.json','repair-input-math-review.json']}}
    atomic_write_json(target,run)
    atomic_write_json(root/'repaired-student-inputs.json',frozen)
    print('Frozen nine reviewed development inputs; no student calls made')


if __name__=='__main__':main()
