#!/usr/bin/env python3
"""Complete check of the final dataset (data/manifests/final-v3). Needs only the final dataset and the
DeepMath parquet files. Exits non-zero on any failure.
  - every field of every row: presence, type, internal consistency, and agreement with DeepMath-103K
  - JUDGE annotations agree with labels and teacher targets; no answer-key or source-question leakage
  - the three tasks share no question, counting every DeepMath copy of it
  - dataset rules: 3,600 / 400 splits, proportional test, JUDGE labels 2,000 / 2,000 (test 200 / 200)
    from the friend's test split, SOLVE shares = the JUDGE/RECONSTRUCT average
"""
import gzip
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from anlp_project import reconstruct as r
from anlp_project.build_eval_manifest import difficulty_band

D = Path(sys.argv[1] if len(sys.argv) > 1 else 'data/manifests/final-v3')
PARQUET = Path('data/datasets/deepmath-103k')
TASKS = ('solve', 'judge', 'reconstruct')
LEVELS = {5.0, 5.5, 6.0, 6.5, 7.0, 7.5, 8.0}


def norm(s):
    return re.sub(r'\s+', '', s or '').casefold()


def open_split(task, split):
    """The raw .jsonl if present locally, else the .jsonl.gz that is tracked in git."""
    raw = D / f'{task}-{split}.jsonl'
    return raw.open() if raw.exists() else gzip.open(D / f'{task}-{split}.jsonl.gz', 'rt')


def main():
    files = sorted(PARQUET.glob('train-*-of-00010.parquet'))
    dm = [x for f in files for x in pq.read_table(f, columns=['question', 'final_answer', 'difficulty', 'topic']).to_pylist()]
    assert len(dm) == 103022
    groups = defaultdict(set)
    for i, x in enumerate(dm):
        groups[norm(x['question'])].add(i)

    problems = Counter()
    def bad(task, what, n=1):
        problems[f'{task}: {what}'] += n

    rows = {t: [json.loads(l) for s in ('train', 'test') for l in open_split(t, s)] for t in TASKS}
    needed_refs = {t: [x['dataset_row_index'] for x in rows[t]] for t in TASKS}

    for t in TASKS:
        seen_uid, seen_row, seen_q = set(), set(), set()
        for x in rows[t]:
            i = x.get('dataset_row_index')
            if type(i) is not int or not 0 <= i < len(dm):
                bad(t, 'invalid dataset_row_index')
                continue
            src = dm[i]
            # Presence, type and format of core fields.
            if x.get('task') != t: bad(t, 'task field wrong')
            if x.get('split') not in ('train', 'test'): bad(t, 'split invalid')
            if x.get('uid') != f'{t}-{i}': bad(t, 'uid not <task>-<row>')
            if x.get('source_group_id') != hashlib.sha256(norm(x['question']).encode()).hexdigest()[:16]: bad(t, 'source_group_id does not match question')
            if x['uid'] in seen_uid or i in seen_row or norm(x['question']) in seen_q: bad(t, 'duplicate uid/row/question')
            seen_uid.add(x['uid']); seen_row.add(i); seen_q.add(norm(x['question']))
            # Against the DeepMath record.
            if norm(x['question']) != norm(src['question']): bad(t, 'question differs from DeepMath')
            if x['topic'] != src['topic']: bad(t, 'topic differs from DeepMath')
            if x['broad_topic'] != r.broad_topic(src['topic']) or x['broad_topic'] not in r.TOPIC_BUCKETS: bad(t, 'broad_topic inconsistent')
            if type(x['difficulty']) is not float or x['difficulty'] != float(src['difficulty']) or x['difficulty'] not in LEVELS: bad(t, 'difficulty inconsistent')
            if x['difficulty_band'] != difficulty_band(x['difficulty']): bad(t, 'difficulty_band inconsistent')
            normalized = (x.get('answer_normalization') or {}).get('normalized_answer')
            if str(x['final_answer']).strip() != str(src['final_answer']).strip() and x['final_answer'] != normalized:
                bad(t, 'final_answer differs from DeepMath')
            if not isinstance(x.get('reference_solutions'), list) or len(x['reference_solutions']) != 3 or not all(isinstance(s, str) and s.strip() for s in x['reference_solutions']):
                bad(t, 'reference_solutions malformed')
            # Training block.
            tr = x.get('training') or {}
            if not isinstance(tr.get('input'), str) or not tr['input'].strip() or not isinstance(tr.get('final_answer'), str) or not tr['final_answer'].strip():
                bad(t, 'training input/final_answer missing')
            # Task-specific.
            if t == 'solve':
                if tr.get('chain_of_thought') != x['reference_solutions'][0] or tr.get('final_answer') != x['final_answer'] or tr.get('input') != x['question']:
                    bad(t, 'training block inconsistent')
            elif t == 'judge':
                pub, pri = x['public'], x['private']
                ids = [s['step_id'] for s in pub['proposed_solution']]
                if ids != [f'S{k}' for k in range(1, len(ids) + 1)] or x['steps'] != len(ids) or x['steps'] == 5: bad(t, 'steps inconsistent')
                if norm(pub['problem']) != norm(x['question']): bad(t, 'public.problem differs from question')
                if x['label'] != pri['label'] or x['label'] not in ('correct', 'incorrect'): bad(t, 'label inconsistent')
                if x['label'] == 'incorrect':
                    if pri['first_error_step_id'] not in ids or pri['error_position'] not in ('early', 'middle', 'late') or not (pri['first_error_explanation'] or '').strip():
                        bad(t, 'incorrect item: error annotation incomplete')
                elif pri['first_error_step_id'] is not None or pri['error_position'] is not None:
                    bad(t, 'correct item carries an error annotation')
                if x['error_position'] != pri['error_position']: bad(t, 'error_position inconsistent')
                target = pri['teacher_target_response'] or ''
                decision = re.search(r'Decision:\s*[*_`]*\s*(correct|incorrect)\b', target, re.I)
                step = re.search(r'First wrong step:\s*[*_`]*\s*(S\d+|none)\b', target, re.I)
                if not decision or decision.group(1).lower() != x['label']: bad(t, 'teacher target decision disagrees with label')
                want = (pri['first_error_step_id'] or 'none').lower()
                if not step or step.group(1).lower() != want: bad(t, 'teacher target step disagrees with annotation')
                if tr.get('final_answer') != target or tr.get('chain_of_thought') is not None: bad(t, 'training block inconsistent')
                if any(w in tr['input'] for w in (pri.get('first_error_explanation') or '\0',)) or 'first_error' in tr['input']:
                    bad(t, 'training input leaks the answer key')
            else:
                pi = x['public_input']
                if len(pi['clues']) != 4 or not all(isinstance(c, str) and c.strip() for c in pi['clues']): bad(t, 'clues malformed')
                if str(pi['final_answer']).strip() != str(x['final_answer']).strip(): bad(t, 'public answer differs from final_answer')
                if norm(x['question']) in norm(tr['input']) or any(norm(x['question']) in norm(c) for c in pi['clues']): bad(t, 'input contains the source question')
                if x['accepted_by'] not in ('v1_audit_and_copy', 'audit_correct_corrected', 'audit_correct_unchanged'): bad(t, 'accepted_by invalid')
                if (x['accepted_by'] == 'audit_correct_corrected') != (x.get('original_public_input') is not None): bad(t, 'correction record inconsistent')
                if tr.get('final_answer') != x['question'] or tr.get('chain_of_thought') != x['reference_solutions'][0]: bad(t, 'training block inconsistent')

    # Reference solutions against DeepMath, read file by file to keep memory low.
    start = 0
    wanted = {i: (t, k) for t in TASKS for k, i in enumerate(needed_refs[t])}
    for f in files:
        n = pq.read_metadata(f).num_rows
        local = sorted(i - start for i in wanted if start <= i < start + n)
        if local:
            table = pq.read_table(f, columns=['r1_solution_1', 'r1_solution_2', 'r1_solution_3']).take(local).to_pylist()
            for li, sol in zip(local, table):
                t, k = wanted[start + li]
                if rows[t][k]['reference_solutions'] != [sol['r1_solution_1'], sol['r1_solution_2'], sol['r1_solution_3']]:
                    bad(t, 'reference_solutions differ from DeepMath')
        start += n

    # Cross-task separation, counting every DeepMath copy of a question.
    owner = {}
    for t in TASKS:
        for x in rows[t]:
            for i in groups[norm(x['question'])]:
                if owner.setdefault(i, t) != t:
                    bad(t, f'shares a question with {owner[i]}')

    # Dataset rules.
    cell = lambda x: (x['broad_topic'], x['difficulty'])
    for t in TASKS:
        tr = [x for x in rows[t] if x['split'] == 'train']
        te = [x for x in rows[t] if x['split'] == 'test']
        if (len(tr), len(te)) != (3600, 400): bad(t, 'split sizes are not 3,600 / 400')
        if {x['source_group_id'] for x in tr} & {x['source_group_id'] for x in te}: bad(t, 'train/test overlap')
        full, test = Counter(map(cell, rows[t])), Counter(map(cell, te))
        if max(abs(test[c] / 400 - full[c] / 4000) for c in full) > 0.005: bad(t, 'test not proportional over topic x difficulty')
    j = rows['judge']
    if Counter(x['label'] for x in j) != Counter(correct=2000, incorrect=2000): bad('judge', 'labels not 2,000 / 2,000')
    if Counter(x['label'] for x in j if x['split'] == 'test') != Counter(correct=200, incorrect=200): bad('judge', 'test labels not 200 / 200')
    if any(x['split'] == 'test' and x['friend']['split'] != 'test' for x in j): bad('judge', "test item from the friend's train split")
    js, rs, ss = (Counter(map(cell, rows[t])) for t in ('judge', 'reconstruct', 'solve'))
    if max(abs(ss[c] / 4000 - (js[c] + rs[c]) / 8000) for c in set(js) | set(rs)) > 0.001:
        bad('solve', 'topic x difficulty shares are not the JUDGE/RECONSTRUCT average')

    # Summary file agrees with the data.
    summary = json.loads((D / 'summary.json').read_text())
    for t in TASKS:
        for s in ('train', 'test'):
            if summary[t][s] != sum(x['split'] == s for x in rows[t]): bad(t, f'summary {s} count wrong')
            if summary[t]['by_topic'][s] != dict(Counter(x['broad_topic'] for x in rows[t] if x['split'] == s)): bad(t, f'summary {s} topics wrong')

    for t in TASKS:
        tr = sum(x['split'] == 'train' for x in rows[t])
        print(f'{t:12s} {tr} train / {len(rows[t]) - tr} test | fields: {len(rows[t][0])} top-level, training block present on {sum("training" in x for x in rows[t])} rows')
    print('PROBLEMS:', dict(problems) or 'none')
    sys.exit(1 if problems else 0)


if __name__ == '__main__':
    main()
