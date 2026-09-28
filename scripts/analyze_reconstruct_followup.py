#!/usr/bin/env python3
"""Matched source-level analysis of a RECONSTRUCT run; no provider requests."""
import argparse
import json
import math
import random
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from anlp_project.reconstruct import is_grounded_success, is_scored_success


def wilson(k, n):
    if not n:
        return None
    z = 1.959963984540054
    p = k / n
    d = 1 + z*z/n
    center = (p + z*z/(2*n)) / d
    half = z * math.sqrt(p*(1-p)/n + z*z/(4*n*n)) / d
    return [max(0, center-half), min(1, center+half)]


def paired(differences, bootstrap_seed=20260921):
    if not differences:
        return None
    rng = random.Random(bootstrap_seed)
    n = len(differences)
    draws = sorted(statistics.mean(rng.choices(differences, k=n)) for _ in range(10000))
    return {"sources": n, "mean_difference": statistics.mean(differences),
            "source_bootstrap_95_interval": [draws[249], draws[9749]]}


def mcnemar(b, c):
    n = b+c
    return min(1., 2*sum(math.comb(n, i) for i in range(min(b, c)+1))/2**n) if n else 1.


def arm_spec(label):
    base, separator, count = label.partition('#')
    prompt, bank_separator, bank = base.partition('@')
    if not separator or count == 'full':
        count = None
    elif count.startswith('k') and count[1:].isdigit() and int(count[1:]) > 0:
        count = int(count[1:])
    else:
        raise ValueError(f'Invalid clue-count arm: {label}')
    return prompt, bank if bank_separator else 'convert_p2', count


def analyze(run, split, arms, seeds, source_ids=None, selection_policy='random'):
    ids = run['partitions'][split] if source_ids is None else source_ids
    if not ids or len(ids) != len(set(ids)) or not set(ids) <= set(run['partitions'][split]):
        raise ValueError('Analysis sources must be a nonempty unique subset of the registered split')
    judgments = {v['response_key']: v['output'] for v in run['evaluations'].values()
                 if v['prompt'] == 'evaluate_p2'}
    recoveries = {v['response_key']: v['output']['source_recovery']
                  for v in run.get('source_recovery', {}).values()}
    cells = {}
    specs = {label:arm_spec(label) for label in arms}
    for key, response in run['responses'].items():
        e = response['public_evidence']
        bank = run['banks'].get(response.get('bank_key'), {})
        source, seed = response['source_index'], response['sampling']['seed']
        labels = [label for label,(prompt,bank_prompt,count) in specs.items()
                  if prompt == response['prompt'] and bank_prompt == bank.get('prompt')
                  and e['clue_count'] == (len(bank['output']['clues']) if count is None else count)]
        if (source not in ids or not labels or seed not in seeds or
            response.get('condition') != 'bank' or
            e.get('style') != 'sentence' or e.get('disclosure') != 'medium' or
            e.get('selection_policy', 'random') != selection_policy):
            continue
        judge = judgments.get(key)
        # A missing per-clue check cannot count as verified grounding.
        coverage = bool(judge) and sorted(c.get('index', -1) for c in judge.get('clue_checks', [])) == list(range(1, e['clue_count']+1))
        resolved = bool(judge and judge.get('status') == 'scored' and coverage)
        row = {'response_key': key, 'evidence_hash': response['evidence_hash'], 'bank_prompt':bank['prompt'],
                      'clue_count':e['clue_count'],
                      'lineage_key':bank.get('composition', {}).get('base_bank_key', response.get('bank_key')),
                      'clues':e.get('clues',[]),
                      'resolved': resolved, 'success': int(is_grounded_success(judge)) if resolved else None,
                      'answer_correct': judge.get('answer_correct') if judge else None,
                      'well_posed': judge.get('well_posed') if judge else None,
                      'score': judge.get('score') if resolved else None,
                      'source_recovery': recoveries.get(key),
                      'completion_tokens': response['request'].get('usage', {}).get('completion_tokens'),
                      'pipeline_completion_tokens': response.get('pipeline_completion_tokens', response['request'].get('usage', {}).get('completion_tokens')),
                      'pipeline_calls': response.get('pipeline_calls', 1),
                      'elapsed_seconds': response['request'].get('elapsed_seconds'),
                      'format_error': response.get('format_error'),
                      'length_stop': response['request'].get('finish_reason') == 'length'}
        for arm in labels:
            cell = (arm, source, seed)
            if cell in cells:
                raise ValueError(f'Duplicate experimental cell {cell}')
            cells[cell] = row.copy()
    # Fail loudly if evidence differs across the matched arms or decoding seeds.
    for source in ids:
        for lineage in {v['lineage_key'] for v in cells.values()}:
            lineage_rows = [v for (a,s,z),v in cells.items() if s==source and v['lineage_key']==lineage]
            ordered = sorted(lineage_rows, key=lambda v:v['clue_count'])
            if any(short['clues'] != long['clues'][:len(short['clues'])]
                   for short,long in zip(ordered,ordered[1:])):
                raise ValueError(f'Non-nested clue counts/order for source {source}, lineage {lineage}')
        for bank_prompt in {v['bank_prompt'] for v in cells.values()}:
            bank_rows = [v for (a,s,z),v in cells.items() if s==source and v['bank_prompt']==bank_prompt]
            by_count = {}
            for row in bank_rows:
                by_count.setdefault(row['clue_count'], []).append(row)
            for count, rows in by_count.items():
                if len({v['evidence_hash'] for v in rows}) > 1:
                    raise ValueError(f'Unmatched evidence for source {source}, bank {bank_prompt}, count {count}')
            ordered = [rows[0]['clues'] for count,rows in sorted(by_count.items())]
            if any(short != long[:len(short)] for short,long in zip(ordered,ordered[1:])):
                raise ValueError(f'Non-nested clue counts/order for source {source}, bank {bank_prompt}')
        for base_prompt, role_prompt in [('convert_p2', 'role_augmented'), ('base_sparse_2', 'role_sparse_2')]:
            base = next((v for (a,s,z),v in cells.items() if s==source and v['bank_prompt']==base_prompt),None)
            for (a,s,z),v in cells.items():
                if s==source and v['bank_prompt']==role_prompt and base:
                    if v['clues'][:-1] != base['clues']:
                        raise ValueError(f'Role condition changed base clues/order for source {source}')
    result = {'split':split, 'source_ids':ids, 'seeds':seeds, 'selection_policy':selection_policy,
              'judge':'evaluate_p2', 'arms':{}, 'comparisons':{}}
    for arm in arms:
        rows = [v for (a,s,z),v in cells.items() if a == arm]
        resolved = [v for v in rows if v['resolved']]
        expected = len(ids)*len(seeds)
        successes = sum(v['success'] for v in resolved)
        missing = expected-len(resolved)
        score_sum = sum(v['score']*25 for v in resolved)
        source_means = []
        for source in ids:
            source_rows = [cells.get((arm,source,z)) for z in seeds]
            if all(v and v['resolved'] for v in source_rows):
                source_means.append(statistics.mean(v['score']*25 for v in source_rows))
        score_bootstrap = paired(source_means)
        tokens = [v['completion_tokens'] for v in rows if v['completion_tokens'] is not None]
        pipeline_tokens = [v['pipeline_completion_tokens'] for v in rows if v['pipeline_completion_tokens'] is not None]
        result['arms'][arm] = {'planned':expected, 'generated':len(rows), 'resolved':len(resolved),
            'successes':successes, 'success_rate_lower_upper':[successes/expected,(successes+missing)/expected],
            'mean_score_resolved':statistics.mean(v['score'] for v in resolved) if resolved else None,
            'mean_normalized_score_resolved':score_sum/len(resolved) if resolved else None,
            'mean_normalized_score_all_planned_bounds':[score_sum/expected,(score_sum+100*missing)/expected],
            'normalized_score_complete_sources':{
                'sources':len(source_means),
                'mean':statistics.mean(source_means) if source_means else None,
                'source_bootstrap_95_interval':score_bootstrap['source_bootstrap_95_interval'] if score_bootstrap else None},
            'score_histogram_0_to_4':[sum(v['score']==i for v in resolved) for i in range(5)],
            'answer_correct_count':sum(v['answer_correct'] is True for v in resolved),
            'well_posed_and_answer_correct_count':sum(v['answer_correct'] is True and v['well_posed'] is True for v in resolved),
            'score4_count':sum(v['score'] == 4 for v in resolved),
            'mean_completion_tokens':statistics.mean(tokens) if tokens else None,
            'mean_pipeline_completion_tokens':statistics.mean(pipeline_tokens) if pipeline_tokens else None,
            'pipeline_calls_per_response':sorted({v['pipeline_calls'] for v in rows}),
            'format_errors':sum(bool(v['format_error']) for v in rows),
            'length_stops':sum(bool(v['length_stop']) for v in rows),
            'by_seed':{}}
        for seed in seeds:
            rr = [v for (a,s,z),v in cells.items() if a==arm and z==seed and v['resolved']]
            k = sum(v['success'] for v in rr)
            result['arms'][arm]['by_seed'][str(seed)] = {'resolved':len(rr),'successes':k,
                'wilson_95_resolved':wilson(k,len(rr))}
    baseline = arms[0]
    for arm in arms[1:]:
        diffs, score_diffs, wins, losses, paired_seed0 = [], [], 0, 0, 0
        for source in ids:
            aa = [cells.get((baseline,source,z)) for z in seeds]
            bb = [cells.get((arm,source,z)) for z in seeds]
            if all(v and v['resolved'] for v in aa+bb):
                diffs.append(statistics.mean(v['success'] for v in bb)-statistics.mean(v['success'] for v in aa))
                score_diffs.append(25*(statistics.mean(v['score'] for v in bb)-statistics.mean(v['score'] for v in aa)))
            a,b = cells.get((baseline,source,seeds[0])),cells.get((arm,source,seeds[0]))
            if a and b and a['resolved'] and b['resolved']:
                paired_seed0 += 1
                wins += b['success'] > a['success']
                losses += b['success'] < a['success']
        result['comparisons'][arm] = {'versus':baseline, 'source_averaged':paired(diffs),
            'normalized_score_source_averaged':paired(score_diffs),
            'first_seed':{'paired_sources':paired_seed0,'wins':wins,'losses':losses,
                          'exact_mcnemar_two_sided':mcnemar(wins, losses)}}
    result['cases'] = [{'arm':a,'source_index':s,'seed':z,**v} for (a,s,z),v in sorted(cells.items())]
    result['unique_student_responses_in_analysis'] = len({v['response_key'] for v in cells.values()})
    result['response_reuse_across_arms'] = {
        key: sorted({a for (a,s,z),v in cells.items() if v['response_key']==key})
        for key in {v['response_key'] for v in cells.values()}
        if len({a for (a,s,z),v in cells.items() if v['response_key']==key}) > 1}
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run',type=Path,required=True)
    p.add_argument('--split',default='D2')
    p.add_argument('--arms',nargs='+',default=['student_p1','student_p5','student_p6'])
    p.add_argument('--seeds',nargs='+',type=int,default=[0,1])
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--selection-policy',choices=['random','anchor_first','bank_order'],default='random')
    p.add_argument('--eligibility-manifest',type=Path,
                   help='Pre-inference eligibility record with common_sources; coverage remains a separate outcome')
    a=p.parse_args()
    eligibility = json.loads(a.eligibility_manifest.read_text()) if a.eligibility_manifest else None
    result=analyze(json.loads(a.run.read_text()),a.split,a.arms,a.seeds,
                   eligibility['common_sources'] if eligibility else None,a.selection_policy)
    if eligibility:
        result['eligibility_manifest'] = str(a.eligibility_manifest)
        result['eligibility_record'] = eligibility
        result['scope'] = 'Matched pre-inference eligible sources; report all-source conversion coverage separately'
    a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='cases'},indent=2))


if __name__=='__main__':
    main()
