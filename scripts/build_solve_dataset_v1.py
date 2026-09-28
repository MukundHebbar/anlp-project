#!/usr/bin/env python3
"""SOLVE-DATASET-v1: 5,000 DeepMath-103K questions disjoint from the JUDGE and RECONSTRUCT sets,
stratified exactly like the JUDGE set (1,250 per topic; per-topic counts over the 7 exact
difficulty levels 5.0-8.0), split 4,500 train / 500 test proportionally over those 28 cells.
No API calls: reads the full dataset from local parquet files verified against HuggingFace.

Excluded (by normalized question text, and by dataset row where known):
  - the JUDGE set (judge_data/deepmath-balanced-5000)
  - the RECONSTRUCT 5,000-source base allocation (train + test)
  - the 78-item JUDGE high-confidence test set
  - the 1,519 questions used by earlier RECONSTRUCT experiments (includes the 146 SOLVE pilot pool)
Duplicate questions inside DeepMath are collapsed to one group; a group is excluded if any
copy of it is excluded.
"""
import hashlib
import json
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import pyarrow.compute as pc
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from anlp_project import reconstruct as r
from anlp_project.build_eval_manifest import difficulty_band
from anlp_project.reconstruct_sources import normalize_option_answer

PARQUET_DIR = Path('data/datasets/deepmath-103k')
JUDGE = Path('judge_data/deepmath-balanced-5000/deepmath-balanced-5000.jsonl')
JUDGE_MANIFEST = Path('judge_data/deepmath-balanced-5000/deepmath-balanced-5000-manifest.json')
JUDGE_TEST = Path('judge_data/judge-high-confidence-public.jsonl')
RECON_BASE = [Path('data/manifests/reconstruct-dataset-v1-base-train.jsonl'),
              Path('data/manifests/reconstruct-dataset-v1-base-test.jsonl')]
PRIOR_EXCLUSION = Path('data/manifests/reconstruct-dataset-v1-exclusion-set.json')
OUT = Path('data/manifests')
PREFIX = 'solve-dataset-v1'
TEST_SIZE = 500
SEED = 20260925
LEVELS = (5.0, 5.5, 6.0, 6.5, 7.0, 7.5, 8.0)
COLUMNS = ['question', 'final_answer', 'difficulty', 'topic']
SOLUTION_COLUMNS = ['r1_solution_1', 'r1_solution_2', 'r1_solution_3']


def norm(s):
    return re.sub(r'\s+', '', s or '').casefold()


def read_jsonl(path):
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]


def sha256(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1 << 22), b''):
            h.update(chunk)
    return h.hexdigest()


def parquet_files():
    files = sorted(PARQUET_DIR.glob('train-*-of-00010.parquet'))
    assert len(files) == 10, f'expected 10 parquet files, found {len(files)}'
    return files


def load_deepmath():
    """Small columns only (the three reference solutions are several GB as Python strings).
    Also records which rows have all three solutions, reading them one column-chunk at a time."""
    rows, file_of = [], []
    for f in parquet_files():
        table = pq.read_table(f, columns=COLUMNS).to_pylist()
        solutions = pq.read_table(f, columns=SOLUTION_COLUMNS)
        present = None
        for c in SOLUTION_COLUMNS:
            nonempty = pc.fill_null(pc.greater(pc.utf8_length(pc.utf8_trim_whitespace(solutions.column(c))), 0), False)
            present = nonempty if present is None else pc.and_(present, nonempty)
        present = present.to_pylist()
        del solutions
        for row, ok in zip(table, present):
            row['has_three_solutions'] = ok
        rows += table
        file_of += [f.name] * len(table)
    assert len(rows) == 103022, f'expected 103,022 rows, got {len(rows)}'
    return rows, file_of, {f.name: sha256(f) for f in parquet_files()}


def load_solutions(indices):
    """Reference solutions for the given global row indices, one parquet file at a time."""
    wanted, out, start = set(indices), {}, 0
    for f in parquet_files():
        n = pq.read_metadata(f).num_rows
        local = [i - start for i in sorted(wanted) if start <= i < start + n]
        if local:
            table = pq.read_table(f, columns=SOLUTION_COLUMNS).take(local).to_pylist()
            for i, row in zip(local, table):
                out[start + i] = row
        start += n
    assert set(out) == wanted
    return out


def proportional_quotas(counts, total):
    n = sum(counts.values())
    exact = {c: total * k / n for c, k in counts.items()}
    quotas = {c: int(v) for c, v in exact.items()}
    for c in sorted(exact, key=lambda c: (exact[c] - quotas[c], c), reverse=True)[:total - sum(quotas.values())]:
        quotas[c] += 1
    return quotas


def main():
    rows, file_of, file_sha = load_deepmath()

    # Row numbering must match the JUDGE and RECONSTRUCT sets' dataset_row_index.
    judge = read_jsonl(JUDGE)
    recon = [x for p in RECON_BASE for x in read_jsonl(p)]
    misaligned = sum(norm(rows[int(x['dataset_row_index'])]['question']) != norm(x['question']) for x in judge)
    misaligned += sum(norm(rows[x['provenance']['dataset_row_index']]['question']) != norm(x['source_question']) for x in recon)
    assert misaligned == 0, f'{misaligned} JUDGE/RECONSTRUCT rows do not match the parquet row order'

    excluded_text = {norm(x['question']) for x in judge} | {norm(x['source_question']) for x in recon}
    excluded_text |= {norm(x['problem']) for x in read_jsonl(JUDGE_TEST)}
    excluded_text |= set(json.loads(PRIOR_EXCLUSION.read_text()))
    excluded_rows = {int(x['dataset_row_index']) for x in judge} | {x['provenance']['dataset_row_index'] for x in recon}

    # Group duplicate questions; keep the lowest row of each group as its representative.
    groups = defaultdict(list)
    for i, row in enumerate(rows):
        groups[norm(row['question'])].append(i)

    discarded, candidates = Counter(), defaultdict(list)
    for key, members in groups.items():
        i = members[0]
        row = rows[i]
        if not key:
            discarded['empty_question'] += 1
            continue
        if key in excluded_text or any(m in excluded_rows for m in members):
            discarded['in_judge_reconstruct_or_prior_sets'] += 1
            continue
        topic = r.broad_topic(row['topic'] or '')
        level = float(row['difficulty']) if row['difficulty'] is not None else None
        if topic not in r.TOPIC_BUCKETS or level not in LEVELS:
            discarded['topic_or_difficulty_outside_strata'] += 1
            continue
        if not str(row['final_answer'] or '').strip() or not row['has_three_solutions']:
            discarded['missing_answer_or_reference_solution'] += 1
            continue
        s = dict(question=row['question'], final_answer=str(row['final_answer']))
        try:
            s = normalize_option_answer(s)
        except ValueError:
            discarded['ambiguous_option_answer'] += 1
            continue
        candidates[f'{topic}::{level}'].append(dict(
            dataset_row_index=i, duplicate_rows=members[1:], question=row['question'], final_answer=s['final_answer'],
            answer_normalization=s.get('answer_normalization'), topic=row['topic'], broad_topic=topic,
            difficulty=level, difficulty_band=difficulty_band(level),
            source_group_id=hashlib.sha256(key.encode()).hexdigest()[:16], parquet_file=file_of[i]))

    target = {c: int(n) for c, n in json.loads(JUDGE_MANIFEST.read_text())['target_cells'].items()}
    short = {c: (n, len(candidates[c])) for c, n in target.items() if len(candidates[c]) < n}
    assert not short, f'cells with fewer candidates than the JUDGE target (target, available): {short}'

    rng = random.Random(SEED)
    selected = {}
    for c in sorted(target):
        pool = sorted(candidates[c], key=lambda x: x['dataset_row_index'])
        rng.shuffle(pool)
        selected[c] = pool[:target[c]]

    test_quota = proportional_quotas(target, TEST_SIZE)
    train, test = [], []
    for c in sorted(target):
        chosen = selected[c]
        for n, x in enumerate(chosen):
            x['split'] = 'test' if n < test_quota[c] else 'train'
            (test if x['split'] == 'test' else train).append(x)

    solutions = load_solutions([x['dataset_row_index'] for x in train + test])
    for x in train + test:
        x.update(solutions[x['dataset_row_index']])

    def finalize(x):
        i = x['dataset_row_index']
        return dict(split=x['split'], source_group_id=x['source_group_id'], source_id=f'deepmath-row-{i}',
                    source_index=4000000 + i, dataset_row_index=i, topic=x['topic'], broad_topic=x['broad_topic'],
                    difficulty=x['difficulty'], difficulty_band=x['difficulty_band'], question=x['question'],
                    final_answer=x['final_answer'], answer_normalization=x['answer_normalization'],
                    r1_solution_1=x['r1_solution_1'], r1_solution_2=x['r1_solution_2'], r1_solution_3=x['r1_solution_3'],
                    provenance=dict(dataset='zwhe99/DeepMath-103K', parquet_file=x['parquet_file'],
                                    parquet_sha256=file_sha[x['parquet_file']], duplicate_rows_in_deepmath=x['duplicate_rows']))

    for name, part in (('train', train), ('test', test)):
        part.sort(key=lambda x: x['dataset_row_index'])
        (OUT / f'{PREFIX}-{name}.jsonl').write_text(''.join(json.dumps(finalize(x), ensure_ascii=False) + '\n' for x in part))

    manifest = dict(
        version='SOLVE-DATASET-v1', dataset='zwhe99/DeepMath-103K', parquet_sha256=file_sha, seed=SEED,
        stratification='per (broad_topic, exact difficulty) cell, identical cell counts to the JUDGE set; test proportional over cells',
        target_cells=target, test_quota=test_quota,
        counts=dict(train=len(train), test=len(test), total=len(train) + len(test)),
        candidates_available_per_cell={c: len(candidates[c]) for c in sorted(target)},
        discarded_question_groups=dict(discarded), deepmath_question_groups=len(groups),
        excluded=dict(judge_rows=len(judge), reconstruct_rows=len(recon), judge_test_items=len(read_jsonl(JUDGE_TEST)),
                      prior_exclusion_set=len(json.loads(PRIOR_EXCLUSION.read_text())), excluded_question_texts=len(excluded_text)),
        runner_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    )
    (OUT / f'{PREFIX}-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps({k: manifest[k] for k in ('counts', 'discarded_question_groups', 'excluded')}, indent=2))
    print('tightest cells (available / target):',
          sorted(((round(len(candidates[c]) / target[c], 2), c) for c in target))[:4])


if __name__ == '__main__':
    main()
