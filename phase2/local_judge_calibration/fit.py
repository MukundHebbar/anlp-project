"""Original split/rubrics/grid/kappa objective, evaluated without any new reference API calls."""
import argparse
import bisect
import gzip
import hashlib
import importlib.util
import itertools
import json
import math
from pathlib import Path
import statistics as st
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'scripts')]
import qwen_judge_calibration as old
import compare_jev_judges as cj
from anlp_project import jev_judging as jj


def fit_cutoffs(ws, ys, grid=None):
    """Exact quadratic-kappa grid search using prefix sufficient statistics, avoiding repeated item scans."""
    grid = grid or [i / 10 for i in range(41)]
    pairs = sorted(zip(ws, ys))
    xs = [w for w, _ in pairs]
    prefix = [(0, 0, 0)]
    for _, y in pairs:
        n, s, ss = prefix[-1]
        prefix.append((n+1, s+y, ss+y*y))
    boundaries = [prefix[bisect.bisect_left(xs, t)] for t in grid]
    n, sy, sy2 = prefix[-1]
    best, best_score = None, -float('inf')
    for indices in itertools.combinations(range(len(grid)), 4):
        ends = [boundaries[i] for i in indices] + [prefix[-1]]
        start = (0, 0, 0)
        obs = expected = 0
        for level, end in enumerate(ends):
            count, s, ss = (end[i]-start[i] for i in range(3))
            obs += ss - 2*level*s + level*level*count
            expected += count*(sy2 - 2*level*sy + level*level*n)
            start = end
        score = 1 - obs*n/expected if expected else -float('inf')
        if score > best_score + 1e-14:
            best_score, best = score, [grid[i] for i in indices]
    if best is None:
        raise ValueError('No non-degenerate calibration threshold candidate')
    return best


def read(path):
    with (gzip.open(path, 'rt') if str(path).endswith('.gz') else open(path)) as f:
        return [json.loads(line) for line in f]


def run(name, folder):
    records = read(folder / 'answers.jsonl')
    ans = {}
    for record in records:
        if record.get('ok'):
            arm, uid, part = record['key'].split('|')
            ans.setdefault((arm, uid), {})[part] = record['response']['answers']
    judge, recon = old.samples()
    arms = sorted({a for a, _ in judge+recon})
    fit_arms = set(arms[::2])
    ds = {a: old.load(a, 'judged-scores.jsonl') for a in arms}
    det = {a: old.load(a, 'scores.jsonl') for a in arms}
    jk = [k for k in judge if k in ans and 'M' in ans[k] and ds[k[0]].get(k[1], {}).get('score_100') is not None]
    ek = [k for k in jk if 'E' in ans[k] and ds[k[0]][k[1]]['dimensions']['V'] == 4]
    rk = [k for k in recon if k in ans and len(ans[k]) == 3 and
          ds[k[0]].get(k[1], {}).get('score_100') is not None]
    dims = [('judge.M', jk, lambda k: ans[k]['M']['M']['score'],
             lambda k: ds[k[0]][k[1]]['dimensions']['M']),
            ('judge.E', ek, lambda k: ans[k]['E']['E']['score'] *
             (2 if det[k[0]][k[1]]['label']=='correct' else 1),
             lambda k: ds[k[0]][k[1]]['dimensions']['E'])]
    for dim, part in [('P','fidelity'),('T','fidelity'),('E','validity'),('M','validity')]:
        dims.append(('reconstruct.'+dim, rk, lambda k,d=dim,p=part: ans[k][p][d]['score'],
                     lambda k,d=dim: ds[k[0]][k[1]]['dimensions'][old.NAMES[d]]))
    summary = {'model': name, 'fit_arms': sorted(fit_arms), 'heldout_arms': sorted(set(arms)-fit_arms),
               'requests': len(records), 'failed_requests': sum(not r.get('ok') for r in records),
               'dimensions': {}, 'cutoffs': {}, 'heldout_cutoffs': {}}
    lines = [f'# {name}: historical judge calibration', '',
             'Same saved requests, DeepSeek labels, four-checkpoint fit/four-checkpoint evaluation split, '
             '0.1-spaced threshold grid and quadratic-weighted kappa as the original calibration. '
             'No Jev or DeepSeek API calls. Native model chat formatting; otherwise the same one-token label protocol.', '',
             '| Dimension | Total n | Held-out n | Raw kappa | Calibrated kappa |', '|---|---:|---:|---:|---:|']
    held = {}
    for dim, keys, w, y in dims:
        tr = [k for k in keys if k[0] in fit_arms]
        te = [k for k in keys if k[0] not in fit_arms]
        assert tr and te, dim
        cut = fit_cutoffs([w(k) for k in tr], [y(k) for k in tr])
        summary['heldout_cutoffs'][dim] = cut
        summary['cutoffs'][dim] = fit_cutoffs([w(k) for k in keys], [y(k) for k in keys])
        pred = lambda value: sum(value>=c for c in cut)
        result = {'n':len(keys), 'heldout_n':len(te),
                  'raw_kappa':cj.qwk([y(k) for k in te], [min(4,round(w(k))) for k in te]),
                  'calibrated_kappa':cj.qwk([y(k) for k in te], [pred(w(k)) for k in te])}
        summary['dimensions'][dim] = result
        for k in te:
            held.setdefault(k, {})[dim] = pred(w(k))
        lines.append(f"| {dim} | {len(keys)} | {len(te)} | {result['raw_kappa']:.3f} | {result['calibrated_kappa']:.3f} |")
    totals = {}
    for task, keys in [('judge',jk),('reconstruct',rk)]:
        predicted, truth = [], []
        for k in keys:
            if k[0] in fit_arms:
                continue
            if task=='judge':
                item = det[k[0]][k[1]]
                v = 4*bool(item.get('verdict_correct_strict', item.get('verdict_correct')))
                l = 4 if v and (det[k[0]][k[1]]['label']=='correct' or
                                item.get('step_correct_strict', item.get('step_correct'))) else 0
                score = 6.25*(v+l+held[k].get('judge.E',0)+held[k]['judge.M'])
            else:
                score = 0 if jj.is_shortcut(ans[k]['shortcut']) else 6.25*sum(held[k]['reconstruct.'+d] for d in 'PTEM')
            predicted.append(score)
            truth.append(ds[k[0]][k[1]]['score_100'])
        correlation = cj.pearson(truth,predicted)
        totals[task] = {'n':len(truth),'pearson_r':correlation if math.isfinite(correlation) else None,
                        'mae':st.mean(abs(a-b) for a,b in zip(truth,predicted)),
                        'reference_mean':st.mean(truth),'model_mean':st.mean(predicted)}
    summary['heldout_total_scores'] = totals
    sc = [k for k in rk if k[0] not in fit_arms]
    truth = [bool(ds[k[0]][k[1]]['shortcut']) for k in sc]
    pred = [jj.is_shortcut(ans[k]['shortcut']) for k in sc]
    summary['heldout_shortcuts'] = {'n':len(sc),'reference_positive':sum(truth),
                                    'caught':sum(a and b for a,b in zip(truth,pred)),
                                    'false_positive':sum(b and not a for a,b in zip(truth,pred))}
    summary['eligible_for_both_training_tasks'] = bool(
        totals['judge']['pearson_r'] is not None and totals['judge']['pearson_r'] >= .90 and
        totals['reconstruct']['pearson_r'] is not None and totals['reconstruct']['pearson_r'] >= .80)
    lines += ['', '## Total scores on held-out checkpoints', '',
              '| Task | n | Pearson r | Mean absolute error /100 |', '|---|---:|---:|---:|']
    for task, value in totals.items():
        corr = f"{value['pearson_r']:.3f}" if value['pearson_r'] is not None else 'undefined (constant scores)'
        lines.append(f"| {task} | {value['n']} | {corr} | {value['mae']:.2f} |")
    shortcuts = summary['heldout_shortcuts']
    lines += ['', f"Held-out shortcut checks: {shortcuts['reference_positive']} reference positives, "
              f"{shortcuts['caught']} caught, {shortcuts['false_positive']} false positives.",
              'The candidate is '+('eligible' if summary['eligible_for_both_training_tasks'] else 'not eligible')+
              ' for both training tasks under the initial correlation screen (JUDGE >=0.90; RECONSTRUCT >=0.80).',
              'This tests compatibility with the original one-token recipe, not the model\'s best possible performance '
              'with its separately recommended critique-generation templates.']
    lines += ['', 'Historical calibration examples are test-derived, following the user-requested original recipe. '
              'This is checkpoint-held-out calibration, not an untouched-question test of judge generalization. '
              'Final Qwen27B calibration and evaluation remain unchanged.', '']
    dest = ROOT/'phase2/results/local-judge-calibration'/name
    dest.mkdir(parents=True, exist_ok=True)
    (dest/'summary.json').write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n')
    model_name = (json.loads((folder/'metadata.json').read_text())['model_source']['model']
                  if (folder/'metadata.json').exists() else name)
    (dest/'calibration.json').write_text(json.dumps({'version':name+'-historical-v1','model':model_name,
                'eligible_for_both_training_tasks':summary['eligible_for_both_training_tasks'],
                'cutoffs':summary['cutoffs']},indent=2)+'\n')
    (dest/'README.md').write_text('\n'.join(lines))
    for filename in ['answers.jsonl','label-logprobs.jsonl']:
        p=folder/filename
        if p.exists():
            with p.open('rb') as src,gzip.open(dest/(filename+'.gz'),'wb') as output:
                output.write(src.read())
    if (folder/'metadata.json').exists():
        (dest/'metadata.json').write_text((folder/'metadata.json').read_text())
    print('\n'.join(lines))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--name',required=True);p.add_argument('--folder',type=Path,required=True)
    a=p.parse_args();run(a.name,a.folder)
