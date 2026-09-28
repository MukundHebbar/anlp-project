#!/usr/bin/env python3
"""Compare W and cached V on their own exact inputs; source-level paired estimates."""
import json
import random
import sys
from collections import defaultdict
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from anlp_project import reconstruct as r
from anlp_project.reconstruct_gates import verify_response_bindings
PROMPT='student_p10_recover_original'


def interval(values):
    if not values:return None
    rng=random.Random(20260921)
    samples=sorted(sum(rng.choices(values,k=len(values)))/len(values) for _ in range(10000))
    return [samples[249],samples[9749]]


def collect(root):
    run=json.loads((root/'student.json').read_text())
    review=json.loads((root/'response-math-review.json').read_text())
    refs={x['response_key']:x for x in review['rows']}
    rows=[]
    for key,response in run['responses'].items():
        if response['prompt']!=PROMPT:continue
        ref=refs[key]
        assert ref['response_output_hash']==r.stable_hash(response['output'])
        assert ref['evidence_hash']==response['evidence_hash']==r.stable_hash(response['public_evidence'])
        es=[e for e in run['evaluations'].values() if e['response_key']==key]
        ss=[s for s in run['source_recovery'].values() if s['response_key']==key]
        assert len(es)<=1 and len(ss)<=1
        e=es[0] if es else {};s=ss[0] if ss else {}
        for record,prompt in [(e,'evaluate_p3'),(s,'source_recovery_p2')]:
            if record:
                assert record['prompt']==prompt
                assert record['prompt_hash']==r.stable_hash(r.load_prompt(prompt))
        if e:
            assert e['response_output_hash']==ref['response_output_hash']
            assert e['evidence_hash']==ref['evidence_hash']
        eo=e.get('output',{});so=s.get('output',{})
        score=eo.get('score') if eo.get('status')=='scored' else None
        assert score is None or type(score) is int and 0<=score<=4
        bound=verify_response_bindings(key,response,e,s,run['sources'][str(response['source_index'])])
        rows.append(dict(source_index=response['source_index'],seed=response['sampling']['seed'],response_key=key,
            evidence_hash=response['evidence_hash'],score=score,raw_grounded=r.is_grounded_success(eo),
            raw_semantic=so.get('source_recovery'),semantic_status=so.get('status','missing'),exact_bindings=bound,
            independently_grounded=ref['mathematically_grounded_valid'],independently_original=ref['confirmed_original_recovery'],
            completion_tokens=response['request']['usage']['completion_tokens'],prompt_tokens=response['request']['usage']['prompt_tokens']))
    jobs=[j for j in run['metadata']['jobs'] if j['prompt']==PROMPT]
    assert len({(j['source_index'],j['seed']) for j in jobs})==len(jobs)
    scores=[x['score']*25 for x in rows if x['score'] is not None]
    total=sum(scores);n=len(jobs)
    bysource=defaultdict(list)
    for x in rows:
        if x['score'] is not None:bysource[x['source_index']].append(x['score']*25)
    complete=[sum(v)/2 for v in bysource.values() if len(v)==2]
    stats=dict(planned_draws=n,parsed=len(rows),scored=len(scores),raw_mean=sum(scores)/len(scores) if scores else None,
        planned_score_bounds=[total/n,(total+100*(n-len(scores)))/n],complete_family_ci95=interval(complete),
        primary_checked_original=sum(x['independently_original'] for x in rows if x['seed']==0),
        primary_checked_grounded=sum(x['independently_grounded'] for x in rows if x['seed']==0),
        accepted_source_count=len(run['partitions']['D1']),original_source_denominator=run['metadata']['original_source_denominator'],
        semantic_returned=sum(x['semantic_status']!='missing' for x in rows),
        semantic_resolved=sum(x['semantic_status']=='scored' for x in rows),
        mean_prompt_tokens=sum(x['prompt_tokens'] for x in rows)/len(rows),
        mean_completion_tokens=sum(x['completion_tokens'] for x in rows)/len(rows))
    return rows,stats


def main():
    root=Path('artifacts/reconstruct/target-example-w')
    old,oldstats=collect(Path('artifacts/reconstruct/verified-examples-v'))
    new,newstats=collect(root)
    population=json.loads((root/'comparison-population.json').read_text())
    common=population['paired_common_families'];deltas=[];pairs=[]
    for i in common:
        a=[x for x in old if x['source_index']==i];b=[x for x in new if x['source_index']==i]
        complete=len(a)==len(b)==2 and all(x['score'] is not None for x in a+b)
        delta=(sum(x['score'] for x in b)-sum(x['score'] for x in a))*25/2 if complete else None
        if complete:deltas.append(delta)
        pairs.append({'source_index':i,'score_delta':delta,
            'V_primary_original':any(x['seed']==0 and x['independently_original'] for x in a),
            'W_primary_original':any(x['seed']==0 and x['independently_original'] for x in b)})
    result={'protocol':'docs/plans/reconstruct-amendment-w.md','arms':{'V':oldstats,'W':newstats},'population':population,
       'paired_sources':pairs,'paired_complete_count':len(deltas),'paired_mean_score_delta':sum(deltas)/len(deltas) if deltas else None,
       'paired_score_ci95':interval(deltas),'W_rows':new,
       'decision':'Do not promote W: independent mathematical review finds no grounded original recoveries; coverage also fails80%.',
       'limitations':['Development comparison, not confirmation; only five shared accepted families.',
          'Policy changes content and clue count together; no isolated count or target-cue effect.',
          'One repair exhausted technical retries; retain its exclusion in coverage.',
          'p3 and semantic evaluators remain provisional; assistant analytic review is not human gold.',
          'Means on available scores and complete-family intervals are provisional if judgments remain unresolved.',
          'Zero observed improvement is not proof of equal population performance or a global optimum.']}
    r.atomic_write_json(root/'comparison.json',result)
    lines=['# W: target-retaining converter demonstration','',result['decision'],'',
      '| Evidence policy | Scores returned / planned | Raw mean /100 | Checked primary original recoveries / accepted | End-to-end / allocated |',
      '|---|---:|---:|---:|---:|']
    for name,s in result['arms'].items():
        mean='pending' if s['raw_mean'] is None else f"{s['raw_mean']:.2f}"
        lines.append(f"| {name} | {s['scored']}/{s['planned_draws']} | {mean} | {s['primary_checked_original']}/{s['accepted_source_count']} | {s['primary_checked_original']}/{s['original_source_denominator']} |")
    lines+=['',f"Matched accepted families: {common}. Newly eligible in W: {population['W_only_eligible']}; eligible only in V: {population['V_only_eligible']}.",
        f"Paired W−V mean-score difference: {result['paired_mean_score_delta']};95% source-bootstrap interval: {result['paired_score_ci95']}; complete pairs: {len(deltas)}.",
        f"W semantic records: {newstats['semantic_returned']}/16 returned, {newstats['semantic_resolved']} resolved. Missing-score bounds: {newstats['planned_score_bounds']}.",'',
        'Every W response has an explicit counterexample or mathematical contradiction in response-math-review.json. None is a valid grounded reconstruction. Raw scores remain separately archived; the review does not replace0-versus1 judgments.','',
        'Limitations:']+['- '+s for s in result['limitations']]
    (root/'comparison.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ['W_rows','population','limitations','paired_sources']},indent=2))


if __name__=='__main__':main()
