#!/usr/bin/env python3
"""Paired, source-level V report; preserve raw and independently reviewed endpoints."""
import json
import random
import sys
from collections import Counter,defaultdict
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from anlp_project import reconstruct as r
from anlp_project.reconstruct_gates import verify_response_bindings

PROMPTS=['student_p10_recover_original','student_p12_verified_examples']


def bootstrap(values):
    if not values:return None
    rng=random.Random(20260921);n=len(values)
    samples=sorted(sum(rng.choices(values,k=n))/n for _ in range(10000))
    return [samples[249],samples[9749]]


def main():
    root=Path('artifacts/reconstruct/verified-examples-v')
    run=json.loads((root/'student.json').read_text())
    review=json.loads((root/'response-math-review.json').read_text())
    references={row['response_key']:row for row in review['rows']}
    audits=defaultdict(list);semantics=defaultdict(list)
    for record in run['evaluations'].values():
        assert record['prompt']=='evaluate_p3' and record['prompt_hash']==r.stable_hash(r.load_prompt('evaluate_p3'))
        audits[record['response_key']].append(record)
    for record in run['source_recovery'].values():
        assert record['prompt']=='source_recovery_p2'
        assert record['prompt_hash']==r.stable_hash(r.load_prompt('source_recovery_p2'))
        semantics[record['response_key']].append(record)
    rows=[]
    for key,response in run['responses'].items():
        assert len(audits[key])<=1 and len(semantics[key])<=1
        reference=references[key]
        assert reference['response_output_hash']==r.stable_hash(response['output'])
        assert reference['evidence_hash']==r.stable_hash(response['public_evidence'])==response['evidence_hash']
        evaluation=audits[key][0] if audits[key] else {}
        semantic=semantics[key][0] if semantics[key] else {}
        if evaluation:
            assert evaluation['response_output_hash']==r.stable_hash(response['output'])
            assert evaluation['evidence_hash']==response['evidence_hash']
        bindings=verify_response_bindings(key,response,evaluation,semantic,run['sources'][str(response['source_index'])])
        score=evaluation.get('output',{}).get('score')
        scored=evaluation.get('output',{}).get('status')=='scored' and type(score) is int
        semantic_output=semantic.get('output',{})
        raw_g=r.is_grounded_success(evaluation.get('output',{})) if evaluation else False
        rows.append(dict(source_index=response['source_index'],prompt=response['prompt'],seed=response['sampling']['seed'],
            response_key=key,score=score if scored else None,raw_grounded=raw_g,
            raw_source_recovery=semantic_output.get('source_recovery'),semantic_status=semantic_output.get('status','missing'),
            exact_bindings=bindings,independently_grounded_valid=reference['mathematically_grounded_valid'],
            independently_confirmed_original=reference['confirmed_original_recovery'],
            raw_grounded_original=raw_g and semantic_output.get('source_recovery')==2 and bindings,
            completion_tokens=response['request']['usage']['completion_tokens'],
            prompt_tokens=response['request']['usage']['prompt_tokens'],finish_reason=response['request']['finish_reason']))
    arms={}
    for prompt in PROMPTS:
        group=[row for row in rows if row['prompt']==prompt]
        planned=sum(job['prompt']==prompt for job in run['metadata']['jobs'])
        scored=[row for row in group if row['score'] is not None]
        total=sum(row['score']*25 for row in scored)
        by_source=defaultdict(list)
        for row in scored:by_source[row['source_index']].append(row['score']*25)
        complete=[sum(v)/2 for v in by_source.values() if len(v)==2]
        arms[prompt]=dict(planned_draws=planned,parsed_responses=len(group),scored=len(scored),
            raw_mean=total/len(scored) if scored else None,
            complete_source_mean_ci95=bootstrap(complete),complete_sources=len(complete),
            planned_score_bounds=[total/planned,(total+100*(planned-len(scored)))/planned],
            score_counts=dict(Counter(row['score'] for row in scored)),
            primary_raw_grounded_original=sum(row['raw_grounded_original'] for row in group if row['seed']==0),
            primary_independently_confirmed_original=sum(row['independently_confirmed_original'] for row in group if row['seed']==0),
            primary_independently_grounded_valid=sum(row['independently_grounded_valid'] for row in group if row['seed']==0),
            total_completion_tokens=sum(row['completion_tokens'] for row in group),
            mean_prompt_tokens=sum(row['prompt_tokens'] for row in group)/len(group),
            mean_completion_tokens=sum(row['completion_tokens'] for row in group)/len(group),
            length_stops=sum(row['finish_reason']=='length' for row in group))
    deltas=[]
    for index in run['partitions']['D1']:
        values={p:[row['score'] for row in rows if row['source_index']==index and row['prompt']==p] for p in PROMPTS}
        if all(len(v)==2 and None not in v for v in values.values()):
            deltas.append(25*(sum(values[PROMPTS[1]])-sum(values[PROMPTS[0]]))/2)
    result=dict(protocol='docs/plans/reconstruct-amendment-v.md',arms=arms,rows=rows,
        allocated_sources=12,accepted_sources=8,coverage=8/12,
        paired_complete_sources=len(deltas),paired_candidate_minus_incumbent_mean=sum(deltas)/len(deltas) if deltas else None,
        paired_difference_ci95=bootstrap(deltas),semantic_records=len(run['source_recovery']),
        semantic_resolved=sum(row['semantic_status']=='scored' for row in rows),
        failures=len(run['failures']),
        decision='no independently verified original-recovery improvement; do not promote the demonstration package',
        limitations=['Eight accepted development families, selected by input validity rather than student success; four exclusions remain in end-to-end denominator.',
                     'Two draws are repeated measurements within a source, not independent source families.',
                     'Package changes demonstration count, content and input tokens together.',
                     'p3 remains provisional; assistant analytic references are not independent human gold.',
                     'Incomplete teacher judgments remain explicit; complete-source intervals exclude unresolved families and are not final if judgments remain pending.'])
    (root/'comparison.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
    lines=['# V: verified demonstrations versus the incumbent prompt','',
        'Independent mathematical review: no confirmed original recoveries for either arm. The candidate has one primary valid alternative, replicated at seed1; it changes the source target. This is not the required semantic recovery.','',
        '| Prompt | Scored / planned | Raw mean /100 | Primary checked original recoveries /8 | Primary checked valid reconstructions /8 | Mean completion tokens |',
        '|---|---:|---:|---:|---:|---:|']
    for p,s in arms.items():
        mean=f"{s['raw_mean']:.2f}" if s['raw_mean'] is not None else 'pending'
        lines.append(f"| {p} | {s['scored']}/{s['planned_draws']} | {mean} | {s['primary_independently_confirmed_original']} | {s['primary_independently_grounded_valid']} | {s['mean_completion_tokens']:.1f} |")
    lines+=['',f"End-to-end primary original recovery is0/12 allocated families for both arms. Reviewed input coverage is8/12, below the80% release threshold.",
            f"Paired score difference (candidate minus incumbent): {result['paired_candidate_minus_incumbent_mean']};95% source-bootstrap interval: {result['paired_difference_ci95']}; complete paired families: {len(deltas)}.",
            f"Semantic judgments: {result['semantic_records']}/32 returned, {result['semantic_resolved']} resolved. Mathematical references: response-math-review.json.",'',
            'Decision: '+result['decision']+'.','', 'Limitations:']+['- '+s for s in result['limitations']]
    (root/'comparison.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ['rows','limitations']},indent=2))


if __name__=='__main__':main()
