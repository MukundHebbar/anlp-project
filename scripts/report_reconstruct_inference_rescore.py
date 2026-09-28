#!/usr/bin/env python3
"""Compare p2/p3 on frozen production responses with exact record bindings."""
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from anlp_project.reconstruct import stable_hash, load_prompt, actual_cost


def main():
    root=Path('artifacts/reconstruct/inference-u')
    run=json.loads((root/'production-rescore.json').read_text())
    by_response=defaultdict(list)
    for record in run['evaluations'].values():
        assert record['prompt_hash']==stable_hash(load_prompt('evaluate_p3'))
        by_response[record['response_key']].append(record)
    originals={}
    rows=[]
    for key,response in run['responses'].items():
        provenance=run['metadata']['response_provenance'][key]
        path=provenance['artifact']
        if path not in originals: originals[path]=json.loads(Path(path).read_text())
        original=originals[path]
        assert original['responses'][key]==response
        assert stable_hash(response)==provenance['response_hash']
        old=[r for r in original['evaluations'].values() if r['response_key']==key and r['prompt']=='evaluate_p2']
        assert len(old)==1
        new=by_response[key]
        assert len(new)<=1
        for record in old+new:
            assert record['response_output_hash']==stable_hash(response['output'])
            assert record['evidence_hash']==stable_hash(response['public_evidence'])
        output=new[0]['output'] if new else {}
        rows.append(dict(source=response['source_index'],model=response['model'],seed=response['sampling'].get('seed'),
            old_score=old[0]['output']['score'],new_score=output.get('score'),status=output.get('status','missing'),
            inference=output.get('inference'),reason=output.get('reason'),response_key=key))
    summaries={}
    for model in sorted({row['model'] for row in rows}):
        group=[row for row in rows if row['model']==model]
        resolved=[row for row in group if row['status']=='scored' and type(row['new_score']) is int]
        planned=18 if 'Qwen' in model else 9
        total=sum(row['new_score']*25 for row in resolved)
        summaries[model]=dict(saved_responses=len(group),planned_student_draws=planned,new_scored=len(resolved),
            old_saved_mean=sum(row['old_score']*25 for row in group)/len(group),
            new_scored_mean=total/len(resolved) if resolved else None,
            planned_mean_bounds=[total/planned,(total+100*(planned-len(resolved)))/planned],
            changed_responses=sum(row['old_score']!=row['new_score'] for row in resolved),
            zero_scores=sum(row['new_score']==0 for row in resolved))
    report=dict(summaries=summaries,rows=rows,failures=len(run['failures']),recorded_cost_usd=actual_cost(run),
        interpretation='Same saved outputs under different rubric versions; this measures an evaluator change, not improved student performance.',
        aggregation='Resolved response means; two Qwen draws per source except one missing. Planned bounds include failed student draws and unresolved judgments. Not a confirmation estimate.')
    review_path=root/'production-score-error-136.json'
    if review_path.exists():
        review=json.loads(review_path.read_text())
        response=run['responses'][review['response_key']]
        assert stable_hash(response)==review['response_hash']
        assert stable_hash(by_response[review['response_key']][0])==review['evaluation_hash']
        group=summaries[response['model']]
        correction=25*(review['proposed_reference_score']-review['raw_score'])
        report['independent_review_sensitivity']={
            'review':str(review_path),'raw_judgments_preserved':True,
            'Qwen_mean_with_one_reference_correction':group['new_scored_mean']+correction/group['new_scored'],
            'Qwen_planned_bounds_with_one_reference_correction':[x+correction/group['planned_student_draws'] for x in group['planned_mean_bounds']],
            'note':'A demonstrated scoring error: a new but mathematically invalid maximization target is substantive, not copy-only. Other raw judgments remain unmodified; not a fully independently relabeled test set.'}
    (root/'production-comparison.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
    lines=['# Frozen production outputs under the inference criterion','',report['interpretation'],'',
           '| Model | Saved outputs | p3 scored | p2 mean /100 | p3 resolved mean /100 | Planned-draw bounds |',
           '|---|---:|---:|---:|---:|---|']
    for model,s in summaries.items():
        new=f"{s['new_scored_mean']:.2f}" if s['new_scored_mean'] is not None else 'pending'
        lines.append(f"| {model} | {s['saved_responses']} | {s['new_scored']} | {s['old_saved_mean']:.2f} | {new} | {s['planned_mean_bounds']} |")
    lines+=['',report['aggregation'],'', '| Source | Model | Seed | p2 | p3 | Inference |', '|---|---|---:|---:|---:|---|']
    for row in rows:
        lines.append(f"| {row['source']} | {row['model']} | {row['seed']} | {row['old_score']} | {row['new_score']} | {(row['inference'] or {}).get('status')} |")
    if 'independent_review_sensitivity' in report:
        sensitivity=report['independent_review_sensitivity']
        lines+=['',f"Independent review found one demonstrated 0-versus-1 scoring error. Correcting that single reference case changes Qwen's resolved mean to {sensitivity['Qwen_mean_with_one_reference_correction']:.2f}/100; raw labels remain unchanged. See production-score-error-136.json.",
                'The revised evaluator remains provisional. Passing authored controls did not establish production accuracy; the unresolved stronger-model set-family judgment also remains in missingness accounting.']
    (root/'production-comparison.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({'summaries':summaries,'failures':len(run['failures'])},indent=2))


if __name__=='__main__': main()
