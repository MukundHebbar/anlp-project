#!/usr/bin/env python3
"""Z case-level accounting with cached p3 comparators and fail-closed gates."""
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from anlp_project.reconstruct import stable_hash,atomic_write_json
ROOT=Path('artifacts/reconstruct/witness-boundary-z')


def record(run,index,prompt,bank_hash,source_hash):
    rows=[a for a in run['audits'].values() if a['source_index']==index and a['prompt']==prompt]
    assert len(rows)<=1
    if not rows:return {'status':'missing'}
    a=rows[0]
    assert a['bank_output_hash']==bank_hash and a['source_record_hash']==source_hash
    assert a['prompt_hash']==stable_hash(Path(f'data/prompts/reconstruct/runtime/{prompt}.md').read_text().strip())
    assert a['model']=='deepseek-ai/DeepSeek-V4.1-Flash' and a['reasoning_effort']=='low'
    return a['output']


def main():
    top=json.loads((ROOT/'manifest.json').read_text());rows=[]
    for pop in top['populations']:
        root=Path(pop['root']);m=json.loads((root/'manifest.json').read_text());run=json.loads((root/'run.json').read_text())
        assert stable_hash(m)==pop['manifest_hash']==run['metadata']['manifest_hash']
        for f in m['fixtures']:
            new=record(run,f['source_index'],'audit_source_disclosure_p4',f['bank_output_hash'],f['source_record_hash'])
            oldrun=json.loads(Path(f['origin_artifact']).read_text()) if 'origin_artifact' in f else run
            oldindex=f.get('origin_source_index',f['source_index'])
            old=record(oldrun,oldindex,'audit_source_disclosure_p3',f['bank_output_hash'],f['source_record_hash'])
            rows.append({**f,'population':root.name,'incumbent':old,'candidate':new,
                         'candidate_matches':new['status']==f['reference_status'],
                         'incumbent_matches':old['status']==f['reference_status'],
                         'comparator_reused':oldrun is not run})
    summaries={}
    for group in ['authored','x-regression','y-regression','all']:
        subset=[r for r in rows if group=='all' or r['population']==group]
        summaries[group]={'cases':len(subset),
            'incumbent_returned':sum(r['incumbent']['status']!='missing' for r in subset),
            'incumbent_matches':sum(r['incumbent_matches'] for r in subset),
            'candidate_returned':sum(r['candidate']['status']!='missing' for r in subset),
            'candidate_matches':sum(r['candidate_matches'] for r in subset),
            'hard_negatives':sum(r['reference_status']=='REJECT' for r in subset),
            'hard_negatives_rejected':sum(r['reference_status']=='REJECT' and r['candidate']['status']=='REJECT' for r in subset)}
    misses=[{'population':r['population'],'case':r['source_index'],'status':r['candidate']['status']} for r in rows
             if r['reference_status']=='REJECT' and r['candidate']['status'] not in ['REJECT','missing']]
    result={'protocol':top['protocol'],'summaries':summaries,'rows':rows,'hard_negative_misses':misses,
      'all_candidate_references_matched':all(r['candidate_matches'] for r in rows),
      'manual_reason_review_complete':False,'automatic_adoption_authorized':False,
      'limitation':'Selected and authored development cases, correlated transformations and reused comparator judgments. No independent population accuracy or Qwen recovery claim.'}
    atomic_write_json(ROOT/'comparison.json',result)
    lines=['# Z: question information versus solution information','',
      '| Population | Cases | Incumbent matches | Candidate returned | Candidate matches | Hard negatives rejected |',
      '|---|---:|---:|---:|---:|---:|']
    for group,s in summaries.items():lines.append(f"| {group} | {s['cases']} | {s['incumbent_matches']} | {s['candidate_returned']} | {s['candidate_matches']} | {s['hard_negatives_rejected']}/{s['hard_negatives']} |")
    lines+=['',result['limitation'],'','No automatic adoption. Inspect every positive missing-element rationale and the known source123 rejection before a decision.']
    (ROOT/'comparison.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps(summaries,indent=2))


if __name__=='__main__':main()
