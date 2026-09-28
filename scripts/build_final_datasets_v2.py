#!/usr/bin/env python3
"""FINAL-v2: SOLVE, JUDGE and RECONSTRUCT, 4,000 each (3,600 train / 400 test), on completely separate
questions. No API calls.

JUDGE        friend's verified 4,604 items (judge_data/judge-final-4604): drop items whose question is in
             RECONSTRUCT, drop one copy of a duplicated question, drop every 5-step item, then drop 6-step
             items (from the friend's train split, spread over topic x difficulty) chosen to end at
             2,000 correct / 2,000 incorrect. Test: 400 items from the friend's test split, proportional
             over topic x difficulty x label.
RECONSTRUCT  unchanged from final-v1 (4,000 of the 4,017 accepted examples; test from untouched sources).
SOLVE        rebuilt from the full DeepMath-103K; per-cell counts = average of the final JUDGE and
             RECONSTRUCT cell shares; excludes every JUDGE, RECONSTRUCT and earlier-used question,
             including DeepMath duplicate copies.
A cell is (broad_topic, exact difficulty 5.0-8.0).
"""
import hashlib
import importlib.util
import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from anlp_project import reconstruct as r
from anlp_project.build_eval_manifest import difficulty_band
from anlp_project.reconstruct_sources import normalize_option_answer

spec = importlib.util.spec_from_file_location('solve_v1', Path(__file__).with_name('build_solve_dataset_v1.py'))
sv = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sv)
norm, proportional_quotas, load_deepmath, load_solutions = sv.norm, sv.proportional_quotas, sv.load_deepmath, sv.load_solutions

JUDGE_ITEMS = Path('judge_data/judge-final-4604/judge-final-4604-private.jsonl')
JUDGE_ORIGINAL = Path('judge_data/deepmath-balanced-5000/deepmath-balanced-5000.jsonl')
JUDGE_TEST_78 = Path('judge_data/judge-high-confidence-public.jsonl')
RECON_BASE = [Path('data/manifests/reconstruct-dataset-v1-base-train.jsonl'), Path('data/manifests/reconstruct-dataset-v1-base-test.jsonl')]
RECON_FINAL = [Path('data/manifests/final-v1/reconstruct-train.jsonl'), Path('data/manifests/final-v1/reconstruct-test.jsonl')]
PRIOR_EXCLUSION = Path('data/manifests/reconstruct-dataset-v1-exclusion-set.json')
OUT = Path('data/manifests/final-v2')
TOTAL, TEST = 4000, 400
SEED = 20260928
LEVELS = sv.LEVELS


def read_jsonl(path, drop=('r1_solution_1', 'r1_solution_2', 'r1_solution_3')):
    rows = []
    with path.open() as f:
        for line in f:
            if line.strip():
                x = json.loads(line)
                for k in drop:
                    x.pop(k, None)
                rows.append(x)
    return rows


def cell(x):
    return (x['broad_topic'], float(x['difficulty']))


def core(task, split, i, question, answer, topic, broad_topic, difficulty):
    return dict(task=task, split=split, uid=f'{task}-{i}', dataset_row_index=i,
                source_group_id=hashlib.sha256(norm(question).encode()).hexdigest()[:16],
                topic=topic, broad_topic=broad_topic, difficulty=float(difficulty),
                difficulty_band=difficulty_band(float(difficulty)), question=question, final_answer=answer)


def write(task, rows, summary):
    for name in ('train', 'test'):
        with (OUT / f'{task}-{name}.jsonl').open('w') as f:
            for x in sorted((x for x in rows if x['split'] == name), key=lambda x: x['dataset_row_index']):
                f.write(json.dumps(x, ensure_ascii=False) + '\n')
    summary[task] = dict(
        train=sum(x['split'] == 'train' for x in rows), test=sum(x['split'] == 'test' for x in rows),
        by_topic={s: dict(Counter(x['broad_topic'] for x in rows if x['split'] == s)) for s in ('train', 'test')},
        by_difficulty={s: {str(k): v for k, v in sorted(Counter(x['difficulty'] for x in rows if x['split'] == s).items())} for s in ('train', 'test')})
    print(task, summary[task]['train'], '/', summary[task]['test'], flush=True)


def main():
    rng = random.Random(SEED)
    OUT.mkdir(parents=True, exist_ok=True)
    rows, file_of, file_sha = load_deepmath()
    summary = dict(version='FINAL-v2', seed=SEED, total_per_task=TOTAL, test_per_task=TEST, parquet_sha256=file_sha)

    # ---------------- RECONSTRUCT (unchanged) ----------------
    recon = [x for p in RECON_FINAL for x in read_jsonl(p, drop=())]
    assert len(recon) == TOTAL
    recon_q = {norm(x['question']) for x in recon}

    # ---------------- JUDGE ----------------
    items = read_jsonl(JUDGE_ITEMS)
    for x in items:
        x['i'] = int(x['source_index'])
        x['steps'] = len(x['public']['proposed_solution'])
        x['label'] = x['private']['label']
        x['q'] = norm(x['public']['problem'])
        x['difficulty'] = float(x['difficulty'])
    mismatched = [x['i'] for x in items if norm(rows[x['i']]['question']) != x['q']]
    assert not mismatched, f'JUDGE source_index does not match the DeepMath row for {len(mismatched)} items'
    log = dict(start=len(items))
    shared = [x for x in items if x['q'] in recon_q]
    items = [x for x in items if x['q'] not in recon_q]
    log['removed_shared_with_reconstruct'] = sorted(x['i'] for x in shared)
    by_q = defaultdict(list)
    for x in items:
        by_q[x['q']].append(x)
    duplicates = {sorted(v, key=lambda y: y['i'])[k]['assignment_id'] for v in by_q.values() for k in range(1, len(v))}
    log['removed_internal_duplicates'] = sorted(x['i'] for x in items if x['assignment_id'] in duplicates)
    items = [x for x in items if x['assignment_id'] not in duplicates]
    log['removed_5_step'] = sum(x['steps'] == 5 for x in items)
    items = [x for x in items if x['steps'] != 5]

    need = len(items) - TOTAL
    labels = Counter(x['label'] for x in items)
    remove_correct = (labels['correct'] - labels['incorrect'] + need) // 2
    remove = {'correct': remove_correct, 'incorrect': need - remove_correct}
    assert all(v >= 0 for v in remove.values()), remove
    removed_6 = set()
    for label, k in remove.items():
        pool = [x for x in items if x['steps'] == 6 and x['label'] == label and x['split'] == 'train']
        quota = proportional_quotas(Counter(map(cell, pool)), k)
        for c in sorted(quota):
            members = sorted((x for x in pool if cell(x) == c), key=lambda x: x['i'])
            rng.shuffle(members)
            removed_6 |= {x['assignment_id'] for x in members[:quota[c]]}
    items = [x for x in items if x['assignment_id'] not in removed_6]
    log['removed_6_step'] = dict(correct=remove['correct'], incorrect=remove['incorrect'])
    assert len(items) == TOTAL
    log['final'] = len(items)
    log['final_labels'] = dict(Counter(x['label'] for x in items))

    # Exactly TEST/2 per label, each spread over topic x difficulty in proportion.
    test_quota = {}
    for label in ('correct', 'incorrect'):
        per_cell = proportional_quotas(Counter(cell(x) for x in items if x['label'] == label), TEST // 2)
        test_quota.update({(c, label): n for c, n in per_cell.items()})
    judge_test = set()
    for s in sorted(test_quota):
        eligible = sorted((x for x in items if (cell(x), x['label']) == s and x['split'] == 'test'), key=lambda x: x['i'])
        assert len(eligible) >= test_quota[s], f'JUDGE {s}: {len(eligible)} friend-test items < quota {test_quota[s]}'
        rng.shuffle(eligible)
        judge_test |= {x['assignment_id'] for x in eligible[:test_quota[s]]}

    judge_refs = load_solutions([x['i'] for x in items])
    judge_rows = []
    for x in items:
        row = rows[x['i']]
        judge_rows.append(dict(
            core('judge', 'test' if x['assignment_id'] in judge_test else 'train', x['i'], x['public']['problem'],
                 str(row['final_answer']), x['topic'], x['broad_topic'], x['difficulty']),
            reference_solutions=[judge_refs[x['i']][f'r1_solution_{k}'] for k in (1, 2, 3)],
            steps=x['steps'], label=x['label'], error_position=x['private']['error_position'],
            public=x['public'], private=x['private'],
            friend=dict(assignment_id=x['assignment_id'], split=x['split'], source_id=x['source_id'],
                        replacement_generation=x['replacement_generation'], generation_record_sha256=x['generation_record_sha256']),
            source=dict(dataset='zwhe99/DeepMath-103K', selection='judge_data/judge-final-4604')))
    del judge_refs
    summary['judge_reduction'] = log
    write('judge', judge_rows, summary)
    summary['judge']['labels'] = {s: dict(Counter(x['label'] for x in judge_rows if x['split'] == s)) for s in ('train', 'test')}
    summary['judge']['steps'] = {s: dict(sorted(Counter(x['steps'] for x in judge_rows if x['split'] == s).items())) for s in ('train', 'test')}
    summary['judge']['error_position_incorrect'] = {s: dict(Counter(x['error_position'] for x in judge_rows if x['split'] == s and x['label'] == 'incorrect')) for s in ('train', 'test')}
    judge_cells = Counter(map(cell, judge_rows))
    judge_q = {norm(x['question']) for x in judge_rows}
    del judge_rows
    write('reconstruct', recon, summary)
    recon_cells = Counter(map(cell, recon))
    del recon

    # ---------------- SOLVE ----------------
    excluded_q = {norm(x['question']) for x in read_jsonl(JUDGE_ORIGINAL)} | {norm(x['public']['problem']) for x in read_jsonl(JUDGE_ITEMS)}
    excluded_q |= {norm(x['source_question']) for p in RECON_BASE for x in read_jsonl(p, drop=('checked_solution',))}
    excluded_q |= {norm(x['problem']) for x in read_jsonl(JUDGE_TEST_78)} | set(json.loads(PRIOR_EXCLUSION.read_text()))
    excluded_q |= judge_q | recon_q
    groups = defaultdict(list)
    for i, row in enumerate(rows):
        groups[norm(row['question'])].append(i)
    candidates, discarded = defaultdict(list), Counter()
    for key, members in groups.items():
        i, row = members[0], rows[members[0]]
        if not key or key in excluded_q:
            discarded['excluded_or_empty'] += 1
            continue
        topic = r.broad_topic(row['topic'] or '')
        level = float(row['difficulty']) if row['difficulty'] is not None else None
        if topic not in r.TOPIC_BUCKETS or level not in LEVELS:
            discarded['outside_strata'] += 1
            continue
        if not str(row['final_answer'] or '').strip() or not row['has_three_solutions']:
            discarded['missing_answer_or_solution'] += 1
            continue
        try:
            s = normalize_option_answer(dict(question=row['question'], final_answer=str(row['final_answer'])))
        except ValueError:
            discarded['ambiguous_option_answer'] += 1
            continue
        candidates[(topic, level)].append(dict(i=i, duplicate_rows=members[1:], question=row['question'],
                                               final_answer=s['final_answer'], answer_normalization=s.get('answer_normalization'),
                                               topic=row['topic'], broad_topic=topic, difficulty=level, parquet_file=file_of[i]))

    cells = sorted(set(judge_cells) | set(recon_cells))
    share = {c: (judge_cells[c] + recon_cells[c]) / (2 * TOTAL) for c in cells}
    solve_target = proportional_quotas({c: share[c] * 10**6 for c in cells}, TOTAL)
    short = {c: (solve_target[c], len(candidates[c])) for c in cells if len(candidates[c]) < solve_target[c]}
    assert not short, f'SOLVE cells short (target, available): {short}'
    solve_test_quota = proportional_quotas(solve_target, TEST)
    selected = []
    for c in cells:
        pool = sorted(candidates[c], key=lambda x: x['i'])
        rng.shuffle(pool)
        for n, x in enumerate(pool[:solve_target[c]]):
            x['split'] = 'test' if n < solve_test_quota[c] else 'train'
            selected.append(x)
    solve_refs = load_solutions([x['i'] for x in selected])
    solve_rows = [dict(core('solve', x['split'], x['i'], x['question'], x['final_answer'], x['topic'], x['broad_topic'], x['difficulty']),
                       reference_solutions=[solve_refs[x['i']][f'r1_solution_{k}'] for k in (1, 2, 3)],
                       answer_normalization=x['answer_normalization'],
                       source=dict(dataset='zwhe99/DeepMath-103K', parquet_file=x['parquet_file'],
                                   parquet_sha256=file_sha[x['parquet_file']], duplicate_rows_in_deepmath=x['duplicate_rows']))
                  for x in selected]
    del solve_refs
    summary['solve_build'] = dict(target_cells={f'{t}|{d}': n for (t, d), n in solve_target.items()},
                                  tightest_supply=sorted((round(len(candidates[c]) / max(1, solve_target[c]), 2), f'{c[0]}|{c[1]}') for c in cells)[:3],
                                  discarded_question_groups=dict(discarded))
    write('solve', solve_rows, summary)

    summary['runner_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    (OUT / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(log, indent=2))
    print('SOLVE tightest supply:', summary['solve_build']['tightest_supply'])


if __name__ == '__main__':
    main()
