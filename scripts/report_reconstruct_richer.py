#!/usr/bin/env python3
"""Report AA raw model metrics with exact bindings; manual review remains separate."""
import argparse,json,math,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from anlp_project import reconstruct as r
from anlp_project.reconstruct_gates import verify_response_bindings
ROOT=Path('artifacts/reconstruct/richer-exposure-aa')
def wilson(k,n):
    if not n:return None
    z=1.95996398454;p=k/n;d=1+z*z/n
    center=(p+z*z/(2*n))/d;radius=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d
    return [max(0,center-radius),min(1,center+radius)]
def main():
    global ROOT
    parser=argparse.ArgumentParser();parser.add_argument('--study-root',type=Path,default=ROOT);args=parser.parse_args();ROOT=args.study_root
    run=json.loads((ROOT/'student.json').read_text());rows=[]
    denominator=run['metadata']['original_denominator']
    if type(denominator) is not int or denominator<=0:raise ValueError('Allocation denominator must be a positive integer')
    review_path=ROOT/'response-math-review.json'
    reviews={x['response_key']:x for x in json.loads(review_path.read_text())['rows']} if review_path.exists() else {}
    for key in run['metadata']['jobs']:
        response=run['responses'].get(key);index,arm,_=key.split(':');index=int(index)
        if response is None:rows.append(dict(response_key=key,source_index=index,arm=arm,missing_response=True));continue
        es=[v for v in run['evaluations'].values() if v['response_key']==key];ss=[v for v in run['source_recovery'].values() if v['response_key']==key]
        assert len(es)<=1 and len(ss)<=1
        e=es[0] if es else {};s=ss[0] if ss else {};eo=e.get('output',{});so=s.get('output',{})
        binding=verify_response_bindings(key,response,e,s,run['sources'][str(index)])
        ref=reviews.get(key)
        if ref:assert ref['response_output_hash']==r.stable_hash(response['output']) and ref['evidence_hash']==response['evidence_hash']
        rows.append(dict(response_key=key,source_index=index,arm=arm,score_100=25*eo['score'] if eo.get('status')=='scored' else None,
            raw_grounded=r.is_grounded_success(eo),raw_semantic=so.get('source_recovery'),exact_bindings=binding,
            raw_joint=bool(binding and r.is_grounded_success(eo) and so.get('source_recovery')==2),
            reviewed_joint=ref.get('grounded_semantic_success') if ref else None,
            reviewed_semantic=ref.get('semantic_equivalent') if ref else None,
            word_count=len(response['public_evidence']['rendered_clues'].split()),clue_count=response['public_evidence']['clue_count'],
            finish_reason=response['request'].get('finish_reason')))
    stats={}
    for arm in run['metadata']['arms']:
        a=[x for x in rows if x['arm']==arm];scores=[x['score_100'] for x in a if x.get('score_100') is not None];n=len(a)
        joint=sum(x.get('raw_joint',False) for x in a);reviewed=sum(x.get('reviewed_joint') is True for x in a)
        stats[arm]={'planned':n,'scores_returned':len(scores),'mean_score_100':sum(scores)/len(scores) if scores else None,'raw_grounded':sum(x.get('raw_grounded',False) for x in a),'raw_semantic':sum(x.get('raw_semantic')==2 for x in a),'raw_joint':joint,'reviewed_joint':reviewed,'reviews_returned':sum(x.get('reviewed_joint') is not None for x in a),'reviewed_conditional_rate':reviewed/n if n else None,'reviewed_end_to_end_rate':reviewed/denominator,'reviewed_conditional_wilson95':wilson(reviewed,n),'denominator_all_sources':denominator}
        stats[arm].update(reviewed_semantic=sum(x.get('reviewed_semantic') is True for x in a),planned_score_bounds=[sum(scores)/n,(sum(scores)+100*(n-len(scores)))/n] if n else None)
        counts={str(level):sum(score==25*(level-1) for score in scores) for level in range(1,6)}
        stats[arm].update(rating_counts_1_to_5=counts,rating_missing=n-len(scores),rating_scale='display=stored0to4+1; normalized=25*(display-1)',
            middle_heavy_observed=(counts['3']>max(counts[k] for k in ['1','2','4','5']) and counts['2']>counts['1'] and counts['4']>counts['5']) if n and len(scores)==n else None)
    result={'arms':stats,'rows':rows,'limitations':['Development screen, one seed; cohort provenance and adaptive reuse must be checked in its protocol; not final confirmation.','Wilson intervals are descriptive and do not correct for adaptive development or policy selection.','Auditors and assistant review are fallible; raw and reviewed outcomes retained separately.']}
    r.atomic_write_json(ROOT/'comparison.json',result)
    lines=['# '+ROOT.name+': reconstruction screen','',f'| Arm | Scored/planned | Mean /100 | Reviewed semantic | Raw grounded + semantic | Reviewed joint / eligible | Reviewed joint /{denominator} |','|---|---:|---:|---:|---:|---:|---:|']
    for arm,s in stats.items():
        lines.append(f"| {arm} | {s['scores_returned']}/{s['planned']} | {s['mean_score_100']} | {s['reviewed_semantic']} | {s['raw_joint']} | {s['reviewed_joint']}/{s['planned']} | {s['reviewed_joint']}/{denominator} |")
    lines+=['','Manual reviews returned: '+str({k:v['reviews_returned'] for k,v in stats.items()}), '']+result['limitations']
    lines+=['','Five-level ratings are display labels for the unchanged0–4 rubric. Missing judgments are not rating1. The shape indicator is descriptive, not a confirmation gate or a Gaussian test.','','| Arm | Rating1 | Rating2 | Rating3 | Rating4 | Rating5 | Missing |','|---|---:|---:|---:|---:|---:|---:|']
    for arm,s in stats.items():
        lines.append('| '+arm+' | '+' | '.join(str(s['rating_counts_1_to_5'][str(k)]) for k in range(1,6))+' | '+str(s['rating_missing'])+' |')
    (ROOT/'comparison.md').write_text('\n'.join(lines)+'\n');print(json.dumps(stats,indent=2))
if __name__=='__main__':main()
