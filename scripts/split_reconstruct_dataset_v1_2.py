#!/usr/bin/env python3
"""RECONSTRUCT-DATASET-v1.2: re-split v1.1's accepted examples into 3,500 train / 500 test,
proportionally stratified by topic x difficulty band. No API calls.

Test is drawn only from sources in v1.1's original test split, so nothing touched during
prompt development (the audit+correct pilot ran on train sources) can reach test. Examples
left over after the 4,000 target go to an unused file.
"""
import hashlib
import json
import random
from collections import Counter
from pathlib import Path

ROOT = Path('data/manifests')
SRC = 'reconstruct-dataset-v1.1'
OUT = 'reconstruct-dataset-v1.2'
TARGET_TRAIN, TARGET_TEST = 3500, 500
SEED = 20260924


def cell(x):
    return (x['broad_topic'], x['difficulty_band'])


def proportional_quotas(counts, total):
    """Largest-remainder allocation of `total` across cells in proportion to `counts`."""
    n = sum(counts.values())
    exact = {c: total * k / n for c, k in counts.items()}
    quotas = {c: int(v) for c, v in exact.items()}
    for c in sorted(exact, key=lambda c: (exact[c] - quotas[c], c), reverse=True)[:total - sum(quotas.values())]:
        quotas[c] += 1
    return quotas


def main():
    rows = [json.loads(l) for name in ('train', 'test') for l in (ROOT / f'{SRC}-{name}.jsonl').read_text().splitlines()]
    assert len({x['source_index'] for x in rows}) == len(rows)
    pool = Counter(map(cell, rows))
    test_quota = proportional_quotas(pool, TARGET_TEST)
    train_quota = proportional_quotas(pool, TARGET_TRAIN)
    rng = random.Random(SEED)
    train, test, unused = [], [], []
    for c in sorted(pool):
        members = sorted((x for x in rows if cell(x) == c), key=lambda x: x['source_index'])
        test_eligible = [x for x in members if x['split'] == 'test']
        rng.shuffle(test_eligible)
        assert len(test_eligible) >= test_quota[c], f'{c}: {len(test_eligible)} original-test rows < quota {test_quota[c]}'
        chosen = {x['source_index'] for x in test_eligible[:test_quota[c]]}
        rest = [x for x in members if x['source_index'] not in chosen]
        rng.shuffle(rest)
        assert len(rest) >= train_quota[c], f'{c}: {len(rest)} rows < train quota {train_quota[c]}'
        test += [x for x in members if x['source_index'] in chosen]
        train += rest[:train_quota[c]]
        unused += rest[train_quota[c]:]

    for split, split_rows in (('train', train), ('test', test), ('unused', unused)):
        for x in split_rows:
            x['split_v1_1'] = x['split']
            x['split'] = split
        split_rows.sort(key=lambda x: x['source_index'])
        (ROOT / f'{OUT}-{split}.jsonl').write_text(''.join(json.dumps(x, ensure_ascii=False) + '\n' for x in split_rows))

    summary = dict(
        version='RECONSTRUCT-DATASET-v1.2', derived_from=SRC, seed=SEED,
        stratification='proportional by (broad_topic, difficulty_band); test drawn only from v1.1 test sources',
        counts=dict(train=len(train), test=len(test), unused=len(unused)),
        cells={f'{t}|{d}': dict(pool=pool[(t, d)], train=train_quota[(t, d)], test=test_quota[(t, d)]) for t, d in sorted(pool)},
        by_topic={s: dict(Counter(x['broad_topic'] for x in rs)) for s, rs in (('train', train), ('test', test))},
        by_difficulty={s: dict(Counter(x['difficulty_band'] for x in rs)) for s, rs in (('train', train), ('test', test))},
        by_accepted_by={s: dict(Counter(x['accepted_by'] for x in rs)) for s, rs in (('train', train), ('test', test))},
        moved_test_to_train=sum(x['split_v1_1'] == 'test' for x in train),
        runner_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    )
    (ROOT / f'{OUT}-summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
