"""Offline audit: production-scoring parity, shortcut errors and rubric-only correlations."""
import importlib.util
import json
import math
from pathlib import Path
import statistics
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
import qwen_judge_calibration as original
import compare_jev_judges as agreement
from anlp_project import baseline,jev_judging as jj


def corr(a,b):
    value=agreement.pearson(a,b)
    return value if math.isfinite(value) else None


def audit(name,answers_file):
    summary=json.loads((ROOT/'phase2/results/local-judge-calibration'/name/'summary.json').read_text())
    cuts=summary['heldout_cutoffs']
    records={}
    for line in answers_file.open():
        r=json.loads(line)
        if r.get('ok'):
            arm,uid,part=r['key'].split('|')
            records.setdefault((arm,uid),{})[part]=r['response']['answers']
    requests={}
    for line in (ROOT/'artifacts/qwen-judge-calibration/requests.jsonl').open():
        r=json.loads(line)
        arm,uid,part=r['key'].split('|')
        requests[(arm,uid,part)]=r
    _,sample=original.samples()
    rows={r['uid']:r for r in baseline.rows_for('test',['reconstruct'])}
    labels={arm:original.load(arm,'judged-scores.jsonl') for arm,_ in sample}
    values=[]
    max_discrepancy=0
    for arm,uid in sample:
        if arm not in summary['heldout_arms'] or (arm,uid) not in records:
            continue
        ans=records[(arm,uid)]
        if set(ans)!={'shortcut','fidelity','validity'}:
            continue
        label=labels[arm].get(uid,{})
        if label.get('score_100') is None:
            continue
        state=requests[(arm,uid,'validity')]['state']
        text=json.dumps(state['response'])
        rec={'gate':[],'calls':{part:{'answers':ans[part]} for part in ans}}
        production=jj.score_record(rows[uid],text,rec,cuts)
        expected={d:ans[part][d]['score'] for d,part in [('P','fidelity'),('T','fidelity'),('E','validity'),('M','validity')]}
        ordinal=6.25*sum(jj.level(expected[d],cuts['reconstruct.'+d]) for d in 'PTEM')
        weighted=6.25*sum(expected.values())
        shortcut=jj.is_shortcut(ans['shortcut'])
        manual=0 if shortcut else ordinal
        max_discrepancy=max(max_discrepancy,abs(manual-production['score_100']))
        assert manual==production['score_100'],(name,arm,uid)
        assert (0 if shortcut else weighted)==production['score_weighted'],(name,arm,uid)
        sc=ans['shortcut']
        values.append({'arm':arm,'uid':uid,'reference':label['score_100'],
                       'reference_shortcut':bool(label['shortcut']),
                       'calibrated_with_shortcut':production['score_100'],
                       'continuous_with_shortcut':production['score_weighted'],
                       'calibrated_rubric_only':ordinal,'continuous_rubric_only':weighted,
                       'shortcut_predicted':shortcut,
                       'class_probability_rule':sc['shortcut_type']['probabilities']['not a shortcut']<.5,
                       'class_argmax_rule':sc['shortcut_type']['choice']!='not a shortcut',
                       'states_value_rule':sc['states_value']['noul']>.5,
                       'repeats_answer_rule':sc['repeats_answer']['noul']>.5})
    result={'model':name,'n':len(values),'production_score_max_absolute_difference':max_discrepancy,
            'all_heldout':{},'reference_non_shortcuts':{},
            'shortcut_flags_by_rule':{k:sum(v[k] for v in values) for k in
                ['class_probability_rule','class_argmax_rule','states_value_rule','repeats_answer_rule']}}
    for group,items in [('all_heldout',values),('reference_non_shortcuts',[v for v in values if not v['reference_shortcut']])]:
        for metric in ['calibrated_with_shortcut','continuous_with_shortcut','calibrated_rubric_only','continuous_rubric_only']:
            result[group][metric]={'n':len(items),'pearson_r':corr([v['reference'] for v in items],[v[metric] for v in items]),
                                   'mean_prediction':statistics.mean(v[metric] for v in items)}
    out=ROOT/'phase2/results/local-judge-calibration'/name
    (out/'reconstruct-audit.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps(result,indent=2))
    return result


if __name__=='__main__':
    for name,path in [('selene',ROOT/'local/local-judge-calibration/selene/answers.jsonl'),
                      ('qwen27b-reference',ROOT/'artifacts/qwen-judge-calibration/answers.jsonl')]:
        audit(name,path)
