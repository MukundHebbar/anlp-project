#!/usr/bin/env python3
"""Fail-closed Y diagnostic accounting; keep selected cases separate from accuracy."""
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from anlp_project.reconstruct import stable_hash,atomic_write_json
ROOT=Path('artifacts/reconstruct/production-boundary-y')


def main():
    run=json.loads((ROOT/'run.json').read_text());m=json.loads((ROOT/'manifest.json').read_text())
    assert run['metadata']['manifest_hash']==stable_hash(m)
    rows=[]
    for f in m['fixtures']:
        decisions={}
        for p in m['prompts']:
            aa=[a for a in run['audits'].values() if a['source_index']==f['source_index'] and a['prompt']==p]
            assert len(aa)<=1
            if aa:
                a=aa[0]
                assert a['bank_output_hash']==f['bank_output_hash'] and a['source_record_hash']==f['source_record_hash']
                assert a['prompt_hash']==stable_hash(Path(f'data/prompts/reconstruct/runtime/{p}.md').read_text().strip())
                assert a['model']==m['teacher_model'] and a['reasoning_effort']==m['reasoning_effort']
                decisions[p]=a['output']
            else:decisions[p]={'status':'missing'}
        rows.append({**f,'decisions':decisions})
    summaries={}
    for p in m['prompts']:
        summaries[p]={'returned':sum(x['decisions'][p]['status']!='missing' for x in rows),
            'matches':sum(x['decisions'][p]['status']==x['reference_status'] for x in rows),
            'hard_negatives_rejected':sum(x['reference_status']=='REJECT' and x['decisions'][p]['status']=='REJECT' for x in rows),
            'hard_negative_count':4,'planned':7}
    hard_misses=[{'case':x['source_index'],'prompt':p,'decision':x['decisions'][p]['status']} for x in rows for p in m['prompts']
                 if x['reference_status']=='REJECT' and x['decisions'][p]['status'] not in ['REJECT','missing']]
    result={'protocol':m['protocol'],'summaries':summaries,'rows':rows,'hard_negative_misses':hard_misses,
        'all_declared_references_matched':all(s['matches']==7 for s in summaries.values()),
        'adoption_blocked_by_hard_negative_miss':bool(hard_misses),
        'production_accuracy_established':False,'automatic_promotion_authorized':False,
        'provenance':'Seven selected archived cases across six families; assistant reference review, not independent human gold. Historical W/V/R records unchanged.'}
    atomic_write_json(ROOT/'comparison.json',result)
    lines=['# Y: archived production-boundary diagnostic','',result['provenance'],'',
       '| Archived case | Reference | Public candidate | Source-aware candidate |','|---|---|---|---|']
    for x in rows:lines.append('| '+x['condition']+' | '+x['reference_status']+' | '+' | '.join(x['decisions'][p]['status'] for p in m['prompts'])+' |')
    lines+=['',f"Hard-negative adoption block: {bool(hard_misses)}. Missing decisions cannot pass. No population accuracy claim or automatic promotion follows from this report."]
    (ROOT/'comparison.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({'summaries':summaries,'hard_negative_misses':hard_misses},indent=2))


if __name__=='__main__':main()
