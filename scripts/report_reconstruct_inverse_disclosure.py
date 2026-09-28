#!/usr/bin/env python3
"""Source-family/condition disclosure diagnostics; missing judgments never pass."""
import json
import sys
from collections import Counter
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from anlp_project.reconstruct import stable_hash,atomic_write_json
ROOT=Path('artifacts/reconstruct/inverse-disclosure-x')


def main():
    run=json.loads((ROOT/'run.json').read_text());manifest=json.loads((ROOT/'manifest.json').read_text())
    assert run['metadata']['manifest_hash']==stable_hash(manifest)
    all_rows=[];summaries={}
    for prompt in manifest['prompts']:
        records={a['source_index']:a for a in run['audits'].values() if a['prompt']==prompt}
        assert len(records)==sum(a['prompt']==prompt for a in run['audits'].values())
        rows=[]
        for fixture in manifest['fixtures']:
            a=records.get(fixture['source_index'])
            if a:
                assert a['bank_output_hash']==fixture['bank_output_hash'] and a['source_record_hash']==fixture['source_record_hash']
                assert a['prompt_hash']==stable_hash(Path(f'data/prompts/reconstruct/runtime/{prompt}.md').read_text().strip())
                assert a['model']==manifest['teacher_model'] and a['reasoning_effort']==manifest['reasoning_effort']
            status=a['output']['status'] if a else 'missing'
            rows.append({**fixture,'prompt':prompt,'status':status,'matches_proposed_reference':status==fixture['reference_status'],
                         'review':a['output'] if a else None})
        all_rows.extend(rows)
        hard=[x for x in rows if x['condition']!='inverse']
        inverse=[x for x in rows if x['condition']=='inverse']
        summaries[prompt]={'returned':len(records),'planned':16,
            'reference_matches':sum(x['matches_proposed_reference'] for x in rows),
            'hard_negative_rejects':sum(x['status']=='REJECT' for x in hard),'hard_negative_count':12,
            'hard_negative_gate_passed':all(x['status']=='REJECT' for x in hard),
            'inverse_accepts':sum(x['status']=='ACCEPT' for x in inverse),'inverse_count':4,
            'all_authored_references_matched':all(x['matches_proposed_reference'] for x in rows),
            'by_condition':{c:dict(Counter(x['status'] for x in rows if x['condition']==c)) for c in ['full','cosmetic','inverse','proof']},
            'by_family':{f:sum(x['matches_proposed_reference'] for x in rows if x['family']==f) for f in ['rectangle','linear','urn','motion']}}
    paired=[]
    for old,new in [('audit_public_p4','audit_public_p5'),('audit_source_disclosure_p2','audit_source_disclosure_p3')]:
        for fixture in manifest['fixtures']:
            before=next(x for x in all_rows if x['source_index']==fixture['source_index'] and x['prompt']==old)
            after=next(x for x in all_rows if x['source_index']==fixture['source_index'] and x['prompt']==new)
            resolved=before['status']!='missing' and after['status']!='missing'
            paired.append({'family':fixture['family'],'condition':fixture['condition'],'incumbent':old,'candidate':new,
                'before':before['status'],'after':after['status'],'both_returned':resolved,
                'reference_agreement_gain':int(after['matches_proposed_reference'])-int(before['matches_proposed_reference']) if resolved else None})
    result={'protocol':manifest['protocol'],'summaries':summaries,'rows':all_rows,'paired_comparisons':paired,
            'candidate_production_validated':False,'promotion_authorized':False,
            'limitations':['Four authored mathematical families; transformations within a family are correlated.',
              'Rectangle intentionally overlaps an existing prompt demonstration, testing consistency rather than held-out generalization.',
              'Agreement is with a proposed operational definition, not independently measured near-perfect accuracy.',
              'No Qwen score or original-recovery result is produced by this diagnostic.',
              'Candidate acceptance of inversions cannot override a full-question or full-proof false acceptance.',
              'Historical W labels and results remain unchanged; these are separate development controls.']}
    atomic_write_json(ROOT/'comparison.json',result)
    lines=['# X: inverse inference versus direct disclosure','',
      '| Auditor | Returned /16 | Reference matches /16 | Hard negatives rejected /12 | Missing-premise inversions accepted /4 |',
      '|---|---:|---:|---:|---:|']
    for p,s in summaries.items():lines.append(f"| {p} | {s['returned']} | {s['reference_matches']} | {s['hard_negative_rejects']} | {s['inverse_accepts']} |")
    lines+=['','| Family / condition | '+' | '.join(manifest['prompts'])+' |', '|---|'+'---|'*4]
    for fixture in manifest['fixtures']:
        statuses=[next(x['status'] for x in all_rows if x['source_index']==fixture['source_index'] and x['prompt']==p) for p in manifest['prompts']]
        lines.append('| '+fixture['family']+' / '+fixture['condition']+' | '+' | '.join(statuses)+' |')
    lines+=['','No production adoption is authorized by this control report. Inspect exact reasons and validate separate production boundaries before considering a candidate.','']+['- '+s for s in result['limitations']]
    (ROOT/'comparison.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps(summaries,indent=2))


if __name__=='__main__':main()
