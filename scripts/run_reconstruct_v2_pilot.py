#!/usr/bin/env python3
"""Small, cheap pilot for the final_v2 prompt set (no copy gate, no-few-shot
student, unmerged judges) before any scaled dataset generation.
See docs/plans/reconstruct-final-v2-pilot.md.
"""
import argparse
import copy
import hashlib
import importlib.util
import json
import random
import re
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

spec = importlib.util.spec_from_file_location('frozen100', Path(__file__).with_name('run_reconstruct_final100.py'))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
from anlp_project.reconstruct_partial_credit import BALANCED_V4_BOUNDARIES

ROOT = Path('artifacts/reconstruct/v2-pilot-bf')
PROMPTS = Path('data/prompts/reconstruct/final_v2')
m.ROOT = ROOT
m.PROMPTS = PROMPTS
PILOT_SIZE = 20
COST_CEILING_USD = 1.00


def normalize_question(s):
    return re.sub(r'\s+', '', s).casefold()


def fetch(url):
    with urllib.request.urlopen(url, timeout=55) as response:
        raw = response.read()
    return json.loads(raw), hashlib.sha256(raw).hexdigest()


def excluded_questions():
    pool_146 = json.loads(m.r.DEFAULT_SOURCE.read_text())['problems']
    excluded = {normalize_question(s['question']) for s in pool_146}
    for path in [Path('artifacts/reconstruct/valid-100-recovery-v1/manifest.json')]:
        if path.exists():
            for s in json.loads(path.read_text())['sources']:
                excluded.add(normalize_question(s['question']))
    return excluded


def prepare():
    ROOT.mkdir(parents=True, exist_ok=True)
    assert not (ROOT / 'manifest.json').exists(), 'Already prepared'
    excluded = excluded_questions()
    rng = random.Random(20260922003)
    blocks = rng.sample(range(103022 // 100), 4)
    urls = [f'https://datasets-server.huggingface.co/rows?dataset=zwhe99%2FDeepMath-103K&config=default&split=train&offset={b*100}&length=100' for b in blocks]
    meta, meta_hash = fetch('https://huggingface.co/api/datasets/zwhe99/DeepMath-103K')
    with ThreadPoolExecutor(max_workers=3) as pool:
        downloads = list(pool.map(fetch, urls))
    candidates = []
    seen = set(excluded)
    discarded = Counter()
    for (data, digest), url in zip(downloads, urls):
        assert data['num_rows_total'] == 103022
        for entry in data['rows']:
            row = entry['row']
            q = row.get('question', '')
            key = normalize_question(q)
            if not q or key in seen:
                discarded['duplicate_or_empty'] += 1
                continue
            topic = m.r.broad_topic(row.get('topic', ''))
            if topic is None:
                discarded['topic'] += 1
                continue
            if not row.get('final_answer') or not row.get('r1_solution_1'):
                discarded['missing_reference'] += 1
                continue
            if entry.get('truncated_cells'):
                discarded['truncated_cells'] += 1
                continue
            i = entry['row_idx']
            s = dict(
                source_index=2000000 + i, source_id=f'deepmath-row-{i}', dataset_row_index=i,
                question=q, final_answer=str(row['final_answer']), topic=row['topic'],
                broad_topic=topic, difficulty=row['difficulty'], checked_solution=row['r1_solution_1'],
                solution_origin='dataset_r1_solution_1_unverified_until_input_audit',
                download_url=url, download_sha256=digest,
            )
            try:
                s = m.normalize_option_answer(s)
            except ValueError:
                discarded['ambiguous_option_answer'] += 1
                continue
            seen.add(key)
            candidates.append(s)
    assert len(candidates) >= PILOT_SIZE, f'Insufficient candidate pool: {len(candidates)}'
    rng.shuffle(candidates)
    sources = candidates[:PILOT_SIZE]
    prompts = {role: (PROMPTS / f'{role}.md').read_text() for role in m.ROLES}
    manifest = dict(
        version='RECONSTRUCT-FINAL-V2-PILOT-v1', protocol='docs/plans/reconstruct-final-v2-pilot.md',
        sources=sources, prompts=prompts, source_selection_seed=20260922003, public_clue_count=4,
        bank_clue_count=6, teacher=m.r.DEFAULT_TEACHER_MODEL, student=m.r.DEFAULT_MODEL,
        student_checkpoint_sha256='7485fe6f11af29433bc51cab58009521f205840f5b4ae3a32fa7f92e8534fdf5',
        sampling=dict(temperature=.7, top_p=.8, top_k=20, max_tokens=8192, seed=0),
        max_teacher_workers=3, cost_ceiling_usd=COST_CEILING_USD, prior_recorded_cost_usd=0.0,
        validator_hash=m.r.stable_hash(Path('src/anlp_project/reconstruct_judge_validation.py').read_text()),
        weights=[.25] * 4, rating_boundaries=list(BALANCED_V4_BOUNDARIES),
        dataset_acquisition=dict(
            dataset='zwhe99/DeepMath-103K', metadata_sha=meta.get('sha'), metadata_response_sha256=meta_hash,
            acquired_at=m.r.utc_now(), blocks=blocks,
            responses=[dict(url=u, sha256=d[1]) for u, d in zip(urls, downloads)],
            discarded=dict(discarded), excluded_prior_sources=len(excluded),
        ),
        runner_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    )
    state = dict(
        metadata=dict(manifest_hash=m.r.stable_hash(manifest), created_at=m.r.utc_now()),
        records={}, failures=[], attempted=[],
        items={str(s['source_index']): {'status': 'allocated'} for s in sources},
    )
    m.r.atomic_write_json(ROOT / 'manifest.json', manifest)
    m.r.atomic_write_json(ROOT / 'run.json', state)
    (ROOT / 'runner-frozen.py').write_bytes(Path(__file__).read_bytes())
    print('Pilot sources:', len(sources), 'topics:', dict(Counter(s['broad_topic'] for s in sources)), flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('action', choices=['prepare', 'run', 'report'])
    a = p.parse_args()
    if a.action == 'prepare':
        prepare()
    elif a.action == 'run':
        m.Run().run()
    else:
        obj = m.Run()
        print(json.dumps(m.export(obj.manifest, obj.state), indent=2))
