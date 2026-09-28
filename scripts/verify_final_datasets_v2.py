#!/usr/bin/env python3
"""Verify FINAL-v2 (data/manifests/final-v2). Exits non-zero on any failure."""
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import pyarrow.parquet as pq

D = Path(sys.argv[1] if len(sys.argv) > 1 else 'data/manifests/final-v2')
TASKS = ('solve', 'judge', 'reconstruct')
CORE = ['task', 'split', 'uid', 'dataset_row_index', 'source_group_id', 'topic', 'broad_topic',
        'difficulty', 'difficulty_band', 'question', 'final_answer', 'reference_solutions']


def norm(s):
    return re.sub(r'\s+', '', s or '').casefold()


def jl(path):
    return [json.loads(l) for l in open(path) if l.strip()]


def main():
    data = {t: [x for s in ('train', 'test') for x in jl(D / f'{t}-{s}.jsonl')] for t in TASKS}
    cell = lambda x: (x['broad_topic'], x['difficulty'])
    err = []

    for t, rows in data.items():
        tr = [x for x in rows if x['split'] == 'train']
        te = [x for x in rows if x['split'] == 'test']
        if (len(tr), len(te)) != (3600, 400):
            err.append(f'{t}: counts {len(tr)}/{len(te)}')
        if len({norm(x['question']) for x in rows}) != 4000 or len({x['dataset_row_index'] for x in rows}) != 4000:
            err.append(f'{t}: duplicate questions or rows inside the set')
        if {x['source_group_id'] for x in tr} & {x['source_group_id'] for x in te}:
            err.append(f'{t}: train/test overlap')
        if any(x['task'] != t or any(x.get(k) in (None, '') for k in CORE) for x in rows):
            err.append(f'{t}: missing core field')
        if any(len(x['reference_solutions']) != 3 or not all(s.strip() for s in x['reference_solutions']) for x in rows):
            err.append(f'{t}: reference solutions incomplete')
        full, test = Counter(map(cell, rows)), Counter(map(cell, te))
        dev = max(abs(test[c] / 400 - full[c] / 4000) for c in full)
        if dev > 0.005:
            err.append(f'{t}: test not proportional over cells ({dev:.4f})')
        print(f'{t:12s} {len(tr)} train / {len(te)} test | test cell-share deviation {dev*100:.2f} pts | '
              f'upper band {sum(x["difficulty_band"] == "upper" for x in rows) / 40:.1f}%')

    # Cross-task disjointness, counting every DeepMath row that carries the same question.
    files = sorted(Path('data/datasets/deepmath-103k').glob('train-*.parquet'))
    questions = [q for f in files for q in pq.read_table(f, columns=['question']).column('question').to_pylist()]
    groups = defaultdict(set)
    for i, q in enumerate(questions):
        groups[norm(q)].add(i)
    owner = {}
    for t, rows in data.items():
        for x in rows:
            if norm(questions[x['dataset_row_index']]) != norm(x['question']):
                err.append(f'{t}: row {x["dataset_row_index"]} question does not match DeepMath')
            for i in groups[norm(x['question'])] | {x['dataset_row_index']}:
                if owner.setdefault(i, t) != t:
                    err.append(f'{t} and {owner[i]} share DeepMath row {i}')
    for a in range(3):
        for b in range(a + 1, 3):
            n = len({norm(x['question']) for x in data[TASKS[a]]} & {norm(x['question']) for x in data[TASKS[b]]})
            print(f'{TASKS[a]} vs {TASKS[b]}: {n} shared questions')

    # JUDGE rules.
    j = data['judge']
    friend = {x['assignment_id']: x for x in jl('judge_data/judge-final-4604/judge-final-4604-private.jsonl')}
    if any(x['friend']['assignment_id'] not in friend for x in j):
        err.append('judge: item not from the friend file')
    if any(x['steps'] == 5 or x['steps'] != len(x['public']['proposed_solution']) for x in j):
        err.append('judge: 5-step item present or step count wrong')
    if any(x['public'] != friend[x['friend']['assignment_id']]['public'] or x['private'] != friend[x['friend']['assignment_id']]['private'] for x in j):
        err.append('judge: item content differs from the friend file')
    if any(norm(x['question']) != norm(x['public']['problem']) for x in j):
        err.append('judge: question differs from public.problem')
    if any(x['split'] == 'test' and x['friend']['split'] != 'test' for x in j):
        err.append('judge: test item from the friend train split')
    if any(not (x['private'].get('teacher_target_response') or '').strip() for x in j):
        err.append('judge: missing teacher target')
    labels = Counter(x['label'] for x in j)
    test_labels = Counter(x['label'] for x in j if x['split'] == 'test')
    if labels != Counter(correct=2000, incorrect=2000) or test_labels != Counter(correct=200, incorrect=200):
        err.append(f'judge: labels {dict(labels)}, test {dict(test_labels)}')
    print('judge labels', dict(labels), '| test', dict(test_labels), '| steps', dict(sorted(Counter(x['steps'] for x in j).items())))

    # SOLVE never uses a JUDGE or RECONSTRUCT candidate question, even ones dropped from those sets.
    used = {norm(x['question']) for x in jl('judge_data/deepmath-balanced-5000/deepmath-balanced-5000.jsonl')}
    used |= {norm(x['public']['problem']) for x in friend.values()}
    used |= {norm(x['source_question']) for s in ('train', 'test') for x in jl(f'data/manifests/reconstruct-dataset-v1-base-{s}.jsonl')}
    used |= set(json.load(open('data/manifests/reconstruct-dataset-v1-exclusion-set.json')))
    if any(norm(x['question']) in used for x in data['solve']):
        err.append('solve: uses an excluded question')
    js, rs, ss = (Counter(map(cell, data[t])) for t in ('judge', 'reconstruct', 'solve'))
    dev = max(abs(ss[c] / 4000 - (js[c] + rs[c]) / 8000) for c in set(js) | set(rs))
    if dev > 0.001:
        err.append(f'solve: cell shares not the JUDGE/RECONSTRUCT average ({dev:.4f})')
    print(f'solve cell shares vs JUDGE/RECONSTRUCT average: max deviation {dev*100:.3f} pts')

    # RECONSTRUCT rules.
    pool = {x['provenance']['dataset_row_index']: x for s in ('train', 'test', 'unused') for x in jl(f'data/manifests/reconstruct-dataset-v1.2-{s}.jsonl')}
    rc = data['reconstruct']
    if any(x['dataset_row_index'] not in pool for x in rc):
        err.append('reconstruct: row not from the accepted pool')
    if any(pool[x['dataset_row_index']]['split_v1_1'] != 'test' for x in rc if x['split'] == 'test'):
        err.append('reconstruct: test row from the original train pool')
    if any(len(x['public_input']['clues']) != 4 for x in rc):
        err.append('reconstruct: clue count')
    if any(norm(x['question']) in norm(c) for x in rc for c in x['public_input']['clues']):
        err.append('reconstruct: a clue contains the source question')

    print('ERRORS:', err or 'none')
    sys.exit(1 if err else 0)


if __name__ == '__main__':
    main()
