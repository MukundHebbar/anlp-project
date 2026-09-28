#!/usr/bin/env python3
"""RECONSTRUCT dataset generation. Produces (final_answer, 4 clues) task inputs with
held-out source questions, split train/test.

Deferred: validated completions/SFT targets for the train split (see
docs/design/reconstruct/SKILL.md §8) — this script produces the input side only.

Two-step pipeline (current; resumable, run in order):
  prepare-pool      fetch/filter/dedup/split the 5000-source base dataset (no API cost)
  realtime-convert  step 1, generation: convert each source into a clue bank
                    (submit-convert + download-batches is the Batch API alternative)
  collect-convert   validate every round-1 result, write clue banks
  realtime-correct  step 2: one audit-and-correct call per source; its decision is final
  collect-correct   assemble the dataset from results on disk (no API calls)

v1 used a separate audit + copy gate instead of step 2; those stages remain to reproduce
it, and collect-correct keeps v1-accepted sources as-is:
  submit-gate / realtime-gate / collect-gate
"""
import argparse
import hashlib
import json
import random
import re
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from anlp_project import reconstruct as r
from anlp_project.reconstruct_sources import normalize_option_answer
from anlp_project.build_eval_manifest import difficulty_band
import importlib.util
spec = importlib.util.spec_from_file_location('frozen100', Path(__file__).with_name('run_reconstruct_final100.py'))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

ROOT = Path('data/manifests')
PREFIX = 'reconstruct-dataset-v1'
PROMPTS = Path('data/prompts/reconstruct/final_v1')
STATE_PATH = ROOT / f'{PREFIX}-batch-state.json'

TARGET_TRAIN = 4000
TARGET_TEST = 1000
TARGET_TOTAL = TARGET_TRAIN + TARGET_TEST
DIFFICULTY_BANDS = ('lower', 'upper')
FETCH_BLOCKS = 380
SEED = 20260922010


def normalize_question(s):
    return re.sub(r'\s+', '', s).casefold()


def fetch(url, attempts=7):
    last_exc = None
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(url, timeout=55) as response:
                raw = response.read()
            return json.loads(raw), hashlib.sha256(raw).hexdigest()
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
            last_exc = exc
            time.sleep(min(60, 2 ** attempt) + random.random())
    raise RuntimeError(f'Fetch failed after {attempts} attempts: {url}') from last_exc


def fetch_or_none(url):
    try:
        return fetch(url)
    except Exception as exc:
        print('permanently failed:', url, type(exc).__name__, str(exc)[:150], flush=True)
        return None


def fetch_blocks(block_numbers):
    """Fetch blocks, skipping any that permanently fail rather than aborting the whole batch."""
    urls = [f'https://datasets-server.huggingface.co/rows?dataset=zwhe99%2FDeepMath-103K&config=default&split=train&offset={b*100}&length=100' for b in block_numbers]
    with ThreadPoolExecutor(max_workers=3) as pool_exec:
        results = list(pool_exec.map(fetch_or_none, urls))
    pairs = [(u, d) for u, d in zip(urls, results) if d is not None]
    failed = len(urls) - len(pairs)
    return pairs, failed


def load_state():
    return json.loads(STATE_PATH.read_text()) if STATE_PATH.exists() else {}


def save_state(state):
    r.atomic_write_json(STATE_PATH, state)


def build_master_exclusion():
    exclude = set()
    for path in Path('artifacts/reconstruct').rglob('*.json'):
        try:
            obj = json.loads(path.read_text())
        except Exception:
            continue
        stack = [obj]
        while stack:
            item = stack.pop()
            if isinstance(item, dict):
                q = item.get('question') or item.get('source_question')
                if isinstance(q, str) and len(q) > 20:
                    exclude.add(normalize_question(q))
                stack.extend(item.values())
            elif isinstance(item, list):
                stack.extend(item)
    pool = json.loads(r.DEFAULT_SOURCE.read_text())['problems']
    for s in pool:
        exclude.add(normalize_question(s['question']))
    return exclude


def cmd_prepare_pool():
    assert not STATE_PATH.exists(), 'Already prepared; delete state file to redo (not recommended once submitted)'
    exclude = build_master_exclusion()
    (ROOT / f'{PREFIX}-exclusion-set.json').write_text(json.dumps(sorted(exclude), indent=1))
    print('master exclusion set:', len(exclude), 'previously-used questions')

    rng = random.Random(SEED)
    available_blocks = list(range(103022 // 100))
    rng.shuffle(available_blocks)
    blocks = available_blocks[:FETCH_BLOCKS]
    remaining_blocks = available_blocks[FETCH_BLOCKS:]
    meta, meta_hash = fetch('https://huggingface.co/api/datasets/zwhe99/DeepMath-103K')

    print('fetching', len(blocks), 'blocks...')
    pairs, failed = fetch_blocks(blocks)
    while failed and remaining_blocks:
        print(f'{failed} block(s) permanently failed; backfilling with {failed} replacement block(s)')
        backfill = remaining_blocks[:failed]
        remaining_blocks = remaining_blocks[failed:]
        extra_pairs, failed = fetch_blocks(backfill)
        pairs += extra_pairs
    downloads = [d for _, d in pairs]
    urls = [u for u, _ in pairs]
    print('successfully fetched', len(downloads), 'blocks')

    candidates = []
    seen = set(exclude)
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
            topic = r.broad_topic(row.get('topic', ''))
            if topic is None or difficulty_band(row['difficulty']) is None:
                discarded['topic_or_difficulty'] += 1
                continue
            if not row.get('final_answer') or not row.get('r1_solution_1'):
                discarded['missing_reference'] += 1
                continue
            if entry.get('truncated_cells'):
                discarded['truncated_cells'] += 1
                continue
            i = entry['row_idx']
            s = dict(
                source_index=3000000 + i, source_id=f'deepmath-row-{i}', dataset_row_index=i,
                question=q, final_answer=str(row['final_answer']), topic=row['topic'],
                broad_topic=topic, difficulty=row['difficulty'], difficulty_band=difficulty_band(row['difficulty']),
                checked_solution=row['r1_solution_1'],
                solution_origin='dataset_r1_solution_1_unverified_until_input_audit',
                download_url=url, download_sha256=digest,
                source_group_id=hashlib.sha256(key.encode()).hexdigest()[:16],
            )
            try:
                s = normalize_option_answer(s)
            except ValueError:
                discarded['ambiguous_option_answer'] += 1
                continue
            seen.add(key)
            candidates.append(s)

    # Stratify by topic (balanced, equal N per topic -- matches this project's own
    # precedent, SKILL.md: "six from each available topic") but NOT by difficulty band
    # within topic: an earlier equal-8-cell (topic x difficulty) design forced every
    # cell down to the scarcest one (Number Theory|upper, ~230 available in a 200-block
    # sample), capping the whole dataset far below target even though most cells had
    # abundant supply. Difficulty composition is left to each topic's natural mix and
    # reported per-topic/per-split for transparency, rather than forced to 50/50.
    topic_groups = {t: [s for s in candidates if s['broad_topic'] == t] for t in r.TOPIC_BUCKETS}
    for values in topic_groups.values():
        rng.shuffle(values)
    topic_supply = {t: len(v) for t, v in topic_groups.items()}
    target_per_topic = TARGET_TOTAL // len(r.TOPIC_BUCKETS)
    achievable_per_topic = min(target_per_topic, min(topic_supply.values()))
    if achievable_per_topic < target_per_topic:
        short = {t: n for t, n in topic_supply.items() if n < target_per_topic}
        print(f'WARNING: target {target_per_topic}/topic not achievable for all topics; '
              f'using {achievable_per_topic}/topic uniformly. Short topics: {short}')
    test_per_topic = round(achievable_per_topic * (TARGET_TEST / TARGET_TOTAL))
    train_per_topic = achievable_per_topic - test_per_topic

    train_pool, test_pool, reserve_pool = [], [], []
    for t, values in topic_groups.items():
        for s in values[:train_per_topic]:
            s['split'] = 'train'
            train_pool.append(s)
        for s in values[train_per_topic:train_per_topic + test_per_topic]:
            s['split'] = 'test'
            test_pool.append(s)
        reserve_pool.extend(values[train_per_topic + test_per_topic:])

    difficulty_composition = {
        split_name: {t: dict(Counter(s['difficulty_band'] for s in pool if s['broad_topic'] == t)) for t in r.TOPIC_BUCKETS}
        for split_name, pool in [('train', train_pool), ('test', test_pool)]
    }

    manifest = dict(
        version='RECONSTRUCT-DATASET-v1', protocol='docs/plans/reconstruct-final-v2-pilot.md',
        target_train=TARGET_TRAIN, target_test=TARGET_TEST,
        strata=dict(topics=list(r.TOPIC_BUCKETS), difficulty_bands=list(DIFFICULTY_BANDS),
                    target_per_topic=target_per_topic, achievable_per_topic=achievable_per_topic,
                    train_per_topic=train_per_topic, test_per_topic=test_per_topic, topic_supply=topic_supply,
                    difficulty_composition=difficulty_composition),
        actual_train=len(train_pool), actual_test=len(test_pool), reserve_unused=len(reserve_pool),
        source_selection_seed=SEED, sampled_blocks=blocks, fetched_urls=urls,
        dataset_acquisition=dict(
            dataset='zwhe99/DeepMath-103K', metadata_sha=meta.get('sha'), metadata_response_sha256=meta_hash,
            acquired_at=r.utc_now(), discarded=dict(discarded), excluded_prior_sources=len(exclude),
            raw_rows_fetched=len(urls) * 100, candidates_after_filter=len(candidates),
        ),
        runner_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    )
    r.atomic_write_json(ROOT / f'{PREFIX}-manifest.json', manifest)
    for name, pool in [('train', train_pool), ('test', test_pool)]:
        rows = [dict(split=s['split'], source_group_id=s['source_group_id'], source_id=s['source_id'],
                      source_index=s['source_index'], topic=s['topic'], broad_topic=s['broad_topic'],
                      difficulty=s['difficulty'], difficulty_band=s['difficulty_band'],
                      source_question=s['question'], final_answer=s['final_answer'],
                      checked_solution=s['checked_solution'],
                      provenance=dict(dataset_row_index=s['dataset_row_index'], download_url=s['download_url'],
                                       download_sha256=s['download_sha256']))
                 for s in pool]
        (ROOT / f'{PREFIX}-base-{name}.jsonl').write_text(''.join(json.dumps(x, ensure_ascii=False) + '\n' for x in rows))
    r.atomic_write_json(ROOT / f'{PREFIX}-pool.json', dict(train=train_pool, test=test_pool, reserve=reserve_pool))
    save_state(dict(stage='base_dataset_prepared', created_at=r.utc_now()))
    print('train:', len(train_pool), dict(Counter(s['broad_topic'] for s in train_pool)))
    print('test:', len(test_pool), dict(Counter(s['broad_topic'] for s in test_pool)))
    print('difficulty composition:', json.dumps(difficulty_composition, indent=1))
    print('reserve (unused surplus):', len(reserve_pool))
    print('discarded during filtering:', dict(discarded))


def all_pool_sources():
    """Reconstruct source dicts (as consumed by the convert/audit/copy stages) from
    the base-{train,test}.jsonl files -- the canonical output of prepare-pool."""
    sources = []
    for name in ['train', 'test']:
        for line in (ROOT / f'{PREFIX}-base-{name}.jsonl').read_text().splitlines():
            row = json.loads(line)
            sources.append(dict(
                source_index=row['source_index'], source_id=row['source_id'],
                question=row['source_question'], final_answer=row['final_answer'],
                checked_solution=row['checked_solution'], topic=row['topic'],
                broad_topic=row['broad_topic'], difficulty=row['difficulty'],
                difficulty_band=row['difficulty_band'], split=row['split'],
                source_group_id=row['source_group_id'], provenance=row['provenance'],
            ))
    return sources


def build_batch_lines(stage, requests):
    lines = []
    for custom_id, prompt in requests:
        cap = 16384 if stage == 'convert' else 8192
        body = dict(model=r.DEFAULT_TEACHER_MODEL, messages=[{'role': 'user', 'content': prompt}],
                    max_tokens=cap, temperature=0.0, reasoning_effort='low')
        lines.append(json.dumps({'custom_id': custom_id, 'method': 'POST', 'url': '/v1/chat/completions', 'body': body}))
    return lines


CHUNK_SIZE = 800  # ~15-20MB per chunk given full checked_solution text embedded in prompts;
                  # a single 5000-request (~110MB) file 502'd on upload, so submit in chunks.


def upload_and_create_with_retry(client, path, attempts=5):
    last_exc = None
    for attempt in range(attempts):
        try:
            f = client.files.create(file=open(path, 'rb'), purpose='batch')
            batch = client.batches.create(input_file_id=f.id, endpoint='/v1/chat/completions', completion_window='24h')
            return f, batch
        except Exception as exc:
            last_exc = exc
            print(f'upload/create failed (attempt {attempt + 1}/{attempts}):', type(exc).__name__, str(exc)[:200], flush=True)
            time.sleep(min(60, 2 ** attempt) + random.random())
    raise RuntimeError(f'Batch submission failed after {attempts} attempts for {path}') from last_exc


def submit_batch_chunked(client, lines, tag):
    chunks = [lines[i:i + CHUNK_SIZE] for i in range(0, len(lines), CHUNK_SIZE)]
    infos = []
    for idx, chunk in enumerate(chunks):
        chunk_tag = f'{tag}-chunk{idx}'
        path = ROOT / f'{PREFIX}-{chunk_tag}-input.jsonl'
        path.write_text('\n'.join(chunk) + '\n')
        f, batch = upload_and_create_with_retry(client, path)
        print(f'{chunk_tag}: submitted batch {batch.id} ({len(chunk)} requests), file {f.id}', flush=True)
        infos.append(dict(file_id=f.id, batch_id=batch.id, n_requests=len(chunk), submitted_at=r.utc_now(), chunk_index=idx))
    return infos


def cmd_submit_convert():
    state = load_state()
    assert state.get('stage') == 'base_dataset_prepared', f"Expected stage 'base_dataset_prepared', got {state.get('stage')!r}"
    convert_tpl = (PROMPTS / 'convert.md').read_text()
    requests = []
    for s in all_pool_sources():
        args = dict(SOURCE_QUESTION=s['question'], FINAL_ANSWER=s['final_answer'], CHECKED_SOLUTION=s['checked_solution'])
        prompt = r.render_template(convert_tpl, args)
        requests.append((f"convert:{s['source_index']}", prompt))
    client = r.deepinfra_client(300).client
    infos = submit_batch_chunked(client, build_batch_lines('convert', requests), 'round1-convert')
    state.update(stage='convert_submitted', round1=infos)
    save_state(state)


def retrying(fn, tag, attempts=6):
    last_exc = None
    for attempt in range(attempts):
        try:
            return fn()
        except Exception as exc:
            last_exc = exc
            print(f'{tag}: transient error (attempt {attempt + 1}/{attempts}):', type(exc).__name__, str(exc)[:150], flush=True)
            time.sleep(min(60, 2 ** attempt) + random.random())
    raise RuntimeError(f'{tag} failed after {attempts} attempts') from last_exc


def download_batch(client, output_file_id):
    def _get():
        content = client.files.content(output_file_id)
        raw = content.content if hasattr(content, 'content') else content.read()
        return [json.loads(line) for line in raw.decode().splitlines() if line.strip()]
    return retrying(_get, 'download_batch')


def poll_and_download_all(client, infos, tag, interval=60, max_wait_seconds=26 * 3600):
    """Poll every uncached chunk each round (not sequentially), caching each as it completes."""
    def cache_path(info):
        return ROOT / f"{PREFIX}-{tag}-chunk{info['chunk_index']}-output.json"

    terminal_failures = {}
    start = time.time()
    while time.time() - start < max_wait_seconds:
        pending = [i for i in infos if not cache_path(i).exists() and i['chunk_index'] not in terminal_failures]
        if not pending:
            break
        for info in pending:
            chunk_tag = f"{tag}-chunk{info['chunk_index']}"
            b = retrying(lambda: client.batches.retrieve(info['batch_id']), f'{chunk_tag} retrieve')
            print(time.strftime('%H:%M:%S'), chunk_tag, b.status, b.request_counts, flush=True)
            if b.status == 'completed':
                r.atomic_write_json(cache_path(info), download_batch(client, b.output_file_id))
                print(chunk_tag, 'downloaded and cached', flush=True)
            elif b.status in ('failed', 'expired', 'cancelled'):
                terminal_failures[info['chunk_index']] = dict(status=b.status, output_file_id=b.output_file_id,
                                                              error_file_id=b.error_file_id)
        if [i for i in infos if not cache_path(i).exists() and i['chunk_index'] not in terminal_failures]:
            time.sleep(interval)
    if terminal_failures:
        raise RuntimeError(f'{tag}: chunks ended without completing: {terminal_failures}')
    missing = [i['chunk_index'] for i in infos if not cache_path(i).exists()]
    if missing:
        raise TimeoutError(f'{tag}: chunks {missing} still pending after {max_wait_seconds}s')
    return [row for i in infos for row in json.loads(cache_path(i).read_text())]


REALTIME_CONVERT_PATH = ROOT / f'{PREFIX}-round1-convert-realtime.jsonl'
REALTIME_GATE_PATH = ROOT / f'{PREFIX}-round2-gate-realtime.jsonl'
TRANSPORT_ERRORS = ('APIConnectionError', 'APITimeoutError', 'InternalServerError', 'RateLimitError')


def read_jsonl(path):
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()] if path.exists() else []


def cached_round1_lines():
    """Every round-1 result on disk: completed batch chunks plus real-time fallback lines."""
    lines = []
    for path in sorted(ROOT.glob(f'{PREFIX}-round1-convert-chunk*-output.json')):
        lines += json.loads(path.read_text())
    return lines + read_jsonl(REALTIME_CONVERT_PATH)


def run_realtime(requests, out_path, workers):
    """Run (custom_id, prompt, max_tokens) requests through the real-time API, skipping any
    custom_id already in out_path, appending each result as it lands (resumable). Output lines
    use the Batch API's shape so the collect stages parse both paths identically. Transport
    errors are retried; content/schema failures are recorded, not retried."""
    import threading
    done = {line['custom_id'] for line in read_jsonl(out_path)}
    todo = [q for q in requests if q[0] not in done]
    print(f'{len(done)} results already in {out_path.name}; running {len(todo)} via real-time API', flush=True)
    client = r.deepinfra_client(900)
    lock = threading.Lock()
    counts = Counter()

    def run_one(request):
        custom_id, prompt, max_tokens = request
        line = None
        for attempt in range(4):
            try:
                raw = r.teacher_call(client, prompt, r.DEFAULT_TEACHER_MODEL, max_tokens, 'low')
                line = dict(custom_id=custom_id, source='realtime', response=dict(status_code=200, body=dict(
                    choices=[dict(message=dict(content=raw['content']), finish_reason=raw['finish_reason'])],
                    usage=raw['usage'], elapsed_seconds=raw['elapsed_seconds'])))
                break
            except Exception as exc:
                if type(exc).__name__ in TRANSPORT_ERRORS and attempt < 3:
                    time.sleep(min(60, 5 * 2 ** attempt) + random.random())
                    continue
                raw = getattr(exc, 'raw_response', None) or {}
                line = dict(custom_id=custom_id, source='realtime', response=dict(status_code=0, body=dict(
                    error=f'{type(exc).__name__}: {str(exc)[:300]}', usage=raw.get('usage'))))
                break
        with lock:
            with out_path.open('a') as f:
                f.write(json.dumps(line, ensure_ascii=False) + '\n')
            counts['ok' if line['response']['status_code'] == 200 else 'failed'] += 1
            n = sum(counts.values())
            if n % 100 == 0 or n == len(todo):
                print(time.strftime('%H:%M:%S'), f'{n}/{len(todo)}', dict(counts), flush=True)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        list(pool.map(run_one, todo))
    print(f'real-time run finished ({out_path.name}):', dict(counts), flush=True)


def cmd_realtime_convert():
    """Fallback for round 1: batch chunks 1-4 expired unprocessed in DeepInfra's queue."""
    state = load_state()
    assert state.get('stage') == 'convert_submitted', f"Expected stage 'convert_submitted', got {state.get('stage')!r}"
    done = {line['custom_id'] for line in cached_round1_lines()}
    convert_tpl = (PROMPTS / 'convert.md').read_text()
    requests = [(f"convert:{s['source_index']}",
                 r.render_template(convert_tpl, dict(SOURCE_QUESTION=s['question'], FINAL_ANSWER=s['final_answer'],
                                                     CHECKED_SOLUTION=s['checked_solution'])), 16384)
                for s in all_pool_sources() if f"convert:{s['source_index']}" not in done]
    run_realtime(requests, REALTIME_CONVERT_PATH, workers=30)


def cmd_download_batches():
    """Batch path: poll submitted chunks and cache each completed one for the collect stages."""
    state = load_state()
    client = r.deepinfra_client(300).client
    for key, tag in (('round1', 'round1-convert'), ('round2', 'round2-gate')):
        if state.get(key):
            poll_and_download_all(client, state[key], tag)


def cmd_collect_convert():
    state = load_state()
    assert state.get('stage') == 'convert_submitted', f"Expected stage 'convert_submitted', got {state.get('stage')!r}"
    results = cached_round1_lines()
    expected = {f"convert:{s['source_index']}" for s in all_pool_sources()}
    have = {line['custom_id'] for line in results}
    missing = expected - have
    assert not missing, f'{len(missing)} convert requests have no result yet; run realtime-convert first'
    assert len(results) == len(have), 'Duplicate convert results on disk'
    r.atomic_write_json(ROOT / f'{PREFIX}-round1-convert-output.json', results)

    ok = 0
    not_suitable = 0
    failed = 0
    banks = {}
    for line in results:
        custom_id = line['custom_id']
        i = int(custom_id.split(':')[1])
        try:
            assert line['response']['status_code'] == 200
            content = line['response']['body']['choices'][0]['message']['content']
            parsed = r.extract_json_object(content)
            m.validate_bank(parsed)
            if parsed['status'] == 'NOT_SUITABLE':
                not_suitable += 1
                continue
            banks[i] = parsed
            ok += 1
        except Exception as exc:
            failed += 1
            print('convert failed for', i, type(exc).__name__, str(exc)[:150])
    r.atomic_write_json(ROOT / f'{PREFIX}-round1-banks.json', {str(k): v for k, v in banks.items()})
    print(f'convert results: {ok} OK, {not_suitable} not_suitable, {failed} failed (of {len(results)})')

    state.update(stage='convert_collected', round1_summary=dict(ok=ok, not_suitable=not_suitable, failed=failed))
    save_state(state)


def load_banks():
    return json.loads((ROOT / f'{PREFIX}-round1-banks.json').read_text())


def public_evidence():
    """The public input (final answer + first four clues) for every source with a valid bank."""
    by_index = {s['source_index']: s for s in all_pool_sources()}
    evidence = {}
    for key, bank in load_banks().items():
        clues = [dict(id=c['id'], sentence=c['sentence']) for c in bank['clues'][:4]]
        evidence[key] = dict(final_answer=by_index[int(key)]['final_answer'], clues=clues,
                             rendered_clues='\n'.join(f'{n}. {c["sentence"]}' for n, c in enumerate(clues, 1)))
    return evidence


def convert_outcomes():
    """Round-1 outcome for sources that never got a valid bank (kept in the denominator)."""
    banks = load_banks()
    outcome = {}
    for line in json.loads((ROOT / f'{PREFIX}-round1-convert-output.json').read_text()):
        i = int(line['custom_id'].split(':')[1])
        if str(i) in banks:
            continue
        try:
            parsed = r.extract_json_object(line['response']['body']['choices'][0]['message']['content'])
            outcome[i] = ('not_suitable', parsed.get('reason')) if parsed.get('status') == 'NOT_SUITABLE' else ('conversion_failed', 'invalid clue bank')
        except Exception as exc:
            outcome[i] = ('conversion_failed', line['response']['body'].get('error') or f'{type(exc).__name__}: {str(exc)[:200]}')
    return outcome


def build_gate_requests():
    """Audit + copy prompts for every valid round-1 bank; writes the public evidence file."""
    audit_tpl = (PROMPTS / 'audit.md').read_text()
    copy_tpl = (PROMPTS / 'copy.md').read_text()
    by_index = {s['source_index']: s for s in all_pool_sources()}
    evidence = public_evidence()
    requests = []
    for key, ev in evidence.items():
        i = int(key)
        s = by_index[i]
        audit_args = dict(SOURCE_QUESTION=s['question'], FINAL_ANSWER=s['final_answer'],
                           CHECKED_SOLUTION=s['checked_solution'], RENDERED_CLUES=ev['rendered_clues'])
        requests.append((f'audit:{i}', r.render_template(audit_tpl, audit_args)))
        copy_args = dict(FINAL_ANSWER=ev['final_answer'], PUBLIC_BANK=ev['rendered_clues'])
        requests.append((f'copy:{i}', r.render_template(copy_tpl, copy_args)))
    r.atomic_write_json(ROOT / f'{PREFIX}-round2-evidence.json', evidence)
    return requests


def cmd_submit_gate():
    state = load_state()
    assert state.get('stage') == 'convert_collected', f"Expected stage 'convert_collected', got {state.get('stage')!r}"
    requests = build_gate_requests()
    client = r.deepinfra_client(300).client
    infos = submit_batch_chunked(client, build_batch_lines('audit', requests), 'round2-gate')
    state.update(stage='gate_submitted', round2=infos)
    save_state(state)


def cmd_realtime_gate():
    """Round 2 via the real-time API (batch queue proved unreliable in round 1). Resumable."""
    state = load_state()
    assert state.get('stage') in ('convert_collected', 'gate_submitted'), f"Unexpected stage {state.get('stage')!r}"
    requests = build_gate_requests()
    state.update(stage='gate_submitted', round2_mode='realtime')
    save_state(state)
    run_realtime([(cid, prompt, 8192) for cid, prompt in requests], REALTIME_GATE_PATH, workers=50)


def parse_gate_lines(results, evidence, audit_stage='audit', copy_stage='copy'):
    """Validate audit/copy result lines against their evidence. Returns parsed outputs by
    source index, per-call errors, and failure counts by stage."""
    audits, copies, call_errors, failed = {}, {}, {}, Counter()
    for line in results:
        stage, idx = line['custom_id'].split(':')
        i = int(idx)
        try:
            assert line['response']['status_code'] == 200, line['response']['body'].get('error', 'non-200 response')
            parsed = r.extract_json_object(line['response']['body']['choices'][0]['message']['content'])
            ev = evidence[str(i)]
            if stage == audit_stage:
                m.validate_audit(parsed, ev)
                audits[i] = parsed
            elif stage == copy_stage:
                m.validate_copy(parsed, ev)
                copies[i] = parsed
        except Exception as exc:
            failed[stage] += 1
            call_errors[(stage, i)] = f'{type(exc).__name__}: {str(exc)[:200]}'
    return audits, copies, call_errors, failed


def cmd_collect_gate():
    state = load_state()
    assert state.get('stage') == 'gate_submitted', f"Expected stage 'gate_submitted', got {state.get('stage')!r}"
    results = read_jsonl(REALTIME_GATE_PATH)
    for path in sorted(ROOT.glob(f'{PREFIX}-round2-gate-chunk*-output.json')):
        results += json.loads(path.read_text())
    expected = {f'{stage}:{k}' for k in json.loads((ROOT / f'{PREFIX}-round2-evidence.json').read_text()) for stage in ('audit', 'copy')}
    have = {line['custom_id'] for line in results}
    assert not expected - have, f'{len(expected - have)} gate requests have no result yet; run realtime-gate first'
    assert len(results) == len(have), 'Duplicate gate results on disk'
    r.atomic_write_json(ROOT / f'{PREFIX}-round2-output.json', results)

    evidence = json.loads((ROOT / f'{PREFIX}-round2-evidence.json').read_text())
    audits, copies, call_errors, failed = parse_gate_lines(results, evidence)

    convert_outcome = convert_outcomes()

    rows = []
    for s in all_pool_sources():
        i = s['source_index']
        ev = evidence.get(str(i))
        audit, copying = audits.get(i), copies.get(i)
        if ev is None:
            status, gate_record = convert_outcome[i][0], dict(convert_reason=convert_outcome[i][1])
        else:
            accepted = bool(audit and audit['status'] == 'ACCEPT' and copying and copying['status'] == 'no_direct_reconstruction')
            rejected = bool((audit and audit['status'] == 'REJECT') or (copying and copying['status'] == 'direct_candidate'))
            status = 'accepted' if accepted else 'rejected' if rejected else 'unresolved'
            gate_record = dict(audit_status=(audit or {}).get('status'), audit_reason=(audit or {}).get('reason'),
                               audit_call_error=call_errors.get(('audit', i)),
                               copy_status=(copying or {}).get('status'), copy_reason=(copying or {}).get('reason'),
                               copy_call_error=call_errors.get(('copy', i)))
        rows.append(dict(
            split=s['split'], source_group_id=s['source_group_id'], source_id=s['source_id'],
            source_index=i, topic=s['topic'], broad_topic=s['broad_topic'], difficulty=s['difficulty'],
            difficulty_band=s['difficulty_band'], input_status=status,
            public_input=dict(final_answer=ev['final_answer'], clues=[c['sentence'] for c in ev['clues']]) if ev else None,
            private=dict(source_question=s['question'], checked_solution=s['checked_solution']),
            gate_record=gate_record, provenance=s['provenance'],
        ))

    accepted_rows = [x for x in rows if x['input_status'] == 'accepted']
    train_rows = [x for x in accepted_rows if x['split'] == 'train'][:TARGET_TRAIN]
    test_rows = [x for x in accepted_rows if x['split'] == 'test'][:TARGET_TEST]
    used = {x['source_index'] for x in train_rows} | {x['source_index'] for x in test_rows}
    surplus = [x for x in accepted_rows if x['source_index'] not in used]

    (ROOT / f'{PREFIX}-train.jsonl').write_text(''.join(json.dumps(x, ensure_ascii=False) + '\n' for x in train_rows))
    (ROOT / f'{PREFIX}-test.jsonl').write_text(''.join(json.dumps(x, ensure_ascii=False) + '\n' for x in test_rows))
    (ROOT / f'{PREFIX}-surplus.jsonl').write_text(''.join(json.dumps(x, ensure_ascii=False) + '\n' for x in surplus))
    (ROOT / f'{PREFIX}-all-attempts.jsonl').write_text(''.join(json.dumps(x, ensure_ascii=False) + '\n' for x in rows))

    summary = dict(
        terminal=True, finished_at=r.utc_now(),
        train_target=TARGET_TRAIN, train_actual=len(train_rows),
        test_target=TARGET_TEST, test_actual=len(test_rows),
        train_target_met=len(train_rows) >= TARGET_TRAIN, test_target_met=len(test_rows) >= TARGET_TEST,
        total_candidates=len(rows), total_accepted=len(accepted_rows), surplus_accepted=len(surplus),
        input_status_counts=dict(Counter(x['input_status'] for x in rows)),
        input_status_by_split=dict(Counter(f"{x['split']}|{x['input_status']}" for x in rows)),
        accepted_by_split_topic=dict(Counter(f"{x['split']}|{x['broad_topic']}" for x in accepted_rows)),
        accepted_by_split_difficulty=dict(Counter(f"{x['split']}|{x['difficulty_band']}" for x in accepted_rows)),
        failed_gate_calls=dict(failed),
        limitations=[
            'Gate-only dataset: public_input + private source_question, no validated completion/SFT target for train (deferred per SKILL.md §8).',
            'Deduplication is exact/normalized-text only, not true paraphrase-level near-duplicate detection.',
            'No human audit of accepted rows yet.',
        ],
    )
    r.atomic_write_json(ROOT / f'{PREFIX}-summary.json', summary)
    state.update(stage='terminal', summary=summary)
    save_state(state)
    print(json.dumps(summary, indent=2))


# --- Audit + correct (v1.1) -------------------------------------------------------------
# Two-step pipeline: generation (convert), then ONE audit-and-correct call per source whose
# decision is final. ACCEPT_UNCHANGED keeps the four clues, CORRECTED replaces them with the
# agent's corrected four, UNREPAIRABLE rejects. No copy challenge and no re-verification.
# When earlier v1 gate results exist (audit + copy), sources they accepted are kept as-is and
# only the rest go to audit-and-correct; the v1 reviews are passed to the agent as evidence.

CORRECT_VERSION = 'audit_correct_p1'
CORRECT_PROMPT = Path(f'data/prompts/reconstruct/runtime/{CORRECT_VERSION}.md')
CORRECT_PATH = ROOT / f'{PREFIX}-round3-{CORRECT_VERSION}-realtime.jsonl'
V1_ATTEMPTS_PATH = ROOT / f'{PREFIX}-all-attempts.jsonl'
V1_GATE_OUTPUT_PATH = ROOT / f'{PREFIX}-round2-output.json'
# Advisory only: fresh audit/copy checks that ran on some corrected sets before the pipeline
# was simplified. Recorded on rows, never used to accept or reject.
ADVISORY_VERIFY_PATH = ROOT / f'{PREFIX}-round4-verify-{CORRECT_VERSION}-realtime.jsonl'
ADVISORY_EVIDENCE_PATH = ROOT / f'{PREFIX}-round3-{CORRECT_VERSION}-evidence.json'
OUT_PREFIX = 'reconstruct-dataset-v1.1'
CORRECT_DECISIONS = ('ACCEPT_UNCHANGED', 'CORRECTED', 'UNREPAIRABLE')
CORRECT_DEFECTS = ('none', 'question_disclosure', 'solution_disclosure', 'disguised_value', 'unsupported', 'padding')


def v1_accepted():
    return {x['source_index'] for x in read_jsonl(V1_ATTEMPTS_PATH) if x['input_status'] == 'accepted'}


def correction_candidates():
    """Sources with a valid bank that no earlier gate has accepted."""
    accepted, banks = v1_accepted(), load_banks()
    return [s for s in all_pool_sources() if str(s['source_index']) in banks and s['source_index'] not in accepted]


def validate_correction(out, ev, source_question):
    assert out.get('decision') in CORRECT_DECISIONS, 'Invalid decision'
    assert type(out.get('source_answer_correct')) is bool, 'source_answer_correct must be Boolean'
    findings = out.get('findings', [])
    assert sorted(f.get('id') for f in findings) == sorted(c['id'] for c in ev['clues']), 'Findings must cover each public clue once'
    for f in findings:
        assert f.get('verdict') in ('keep', 'rewrite', 'replace') and f.get('defect') in CORRECT_DEFECTS, 'Invalid finding'
        assert isinstance(f.get('reason'), str) and f['reason'].strip(), 'Finding without reason'
    assert isinstance(out.get('reason'), str) and out['reason'].strip(), 'Missing reason'
    corrected = out.get('corrected_clues')
    if out['decision'] != 'CORRECTED':
        assert corrected == [], f"{out['decision']} must not return corrected clues"
        if out['decision'] == 'ACCEPT_UNCHANGED':
            assert all(f['verdict'] == 'keep' and f['defect'] == 'none' for f in findings), 'ACCEPT_UNCHANGED with a defect'
        return out
    assert isinstance(corrected, list) and len(corrected) == 4, 'CORRECTED needs exactly four clues'
    assert [c.get('id') for c in corrected] == ['c1', 'c2', 'c3', 'c4'], 'Corrected ids must be c1-c4'
    sentences = [c.get('sentence') for c in corrected]
    assert all(isinstance(s, str) and s.strip() for s in sentences), 'Empty corrected clue'
    assert all(isinstance(c.get('hidden_support'), str) and c['hidden_support'].strip() for c in corrected), 'Missing hidden support'
    assert len(set(sentences)) == 4, 'Duplicate corrected clues'
    original = {c['id']: c['sentence'] for c in ev['clues']}
    assert all(original[f['id']] in sentences for f in findings if f['verdict'] == 'keep'), 'A kept clue was not preserved verbatim'
    assert any(f['verdict'] != 'keep' for f in findings), 'CORRECTED without any changed clue'
    assert set(sentences) != set(original.values()), 'CORRECTED set is identical to the original'
    assert isinstance(out.get('missing_essential_element'), str) and out['missing_essential_element'].strip(), 'Missing withheld element'
    q = normalize_question(source_question)
    assert not any(q in normalize_question(s) for s in sentences), 'A corrected clue contains the full source question'
    return out


def build_correct_requests(limit=None, split=None):
    evidence = public_evidence()
    banks = load_banks()
    if V1_GATE_OUTPUT_PATH.exists():
        audits, copies, call_errors, _ = parse_gate_lines(json.loads(V1_GATE_OUTPUT_PATH.read_text()), evidence)
    else:
        audits, copies, call_errors = {}, {}, {}
    candidates = sorted(correction_candidates(), key=lambda s: s['source_index'])
    if split:
        candidates = [s for s in candidates if s['split'] == split]
    if limit:
        random.Random(SEED).shuffle(candidates)
        candidates = candidates[:limit]
    template = CORRECT_PROMPT.read_text()
    requests = []
    for s in candidates:
        i = s['source_index']
        spare = '\n'.join(f"- {c['sentence']}" for c in banks[str(i)]['clues'][4:]) or '(none)'
        if V1_GATE_OUTPUT_PATH.exists():
            prior = json.dumps(dict(audit=audits.get(i) or {'unavailable': call_errors.get(('audit', i))},
                                    copy_challenge=copies.get(i) or {'unavailable': call_errors.get(('copy', i))}),
                               ensure_ascii=False, indent=1)
        else:
            prior = '(none; this is the first review)'
        prompt = r.render_template(template, dict(
            SOURCE_QUESTION=s['question'], CHECKED_SOLUTION=s['checked_solution'], FINAL_ANSWER=s['final_answer'],
            RENDERED_CLUES=evidence[str(i)]['rendered_clues'], SPARE_CLUES=spare, PRIOR_REVIEWS=prior))
        requests.append((f'correct:{i}', prompt, 16384))
    return requests, template


def cmd_realtime_correct(limit=None, split=None):
    """Step 2: audit + correct every source not already accepted (or a seeded pilot sample).
    Resumable: sources that already have a result are skipped, never rerun."""
    requests, template = build_correct_requests(limit, split)
    state = load_state()
    state['correction'] = dict(version=CORRECT_VERSION, prompt_sha256=hashlib.sha256(template.encode()).hexdigest())
    save_state(state)
    run_realtime(requests, CORRECT_PATH, workers=50)


def parsed_corrections():
    """Validated corrector outputs and per-source failure reasons."""
    evidence = public_evidence()
    by_index = {s['source_index']: s for s in all_pool_sources()}
    outputs, errors = {}, {}
    for line in read_jsonl(CORRECT_PATH):
        i = int(line['custom_id'].split(':')[1])
        try:
            assert line['response']['status_code'] == 200, line['response']['body'].get('error', 'non-200 response')
            parsed = r.extract_json_object(line['response']['body']['choices'][0]['message']['content'])
            outputs[i] = validate_correction(parsed, evidence[str(i)], by_index[i]['question'])
        except Exception as exc:
            errors[i] = f'{type(exc).__name__}: {str(exc)[:200]}'
    return outputs, errors


def advisory_checks():
    """Fresh audit/copy verdicts that exist for some corrected sets (advisory, not a gate)."""
    if not (ADVISORY_VERIFY_PATH.exists() and ADVISORY_EVIDENCE_PATH.exists()):
        return {}
    audits, copies, errors, _ = parse_gate_lines(read_jsonl(ADVISORY_VERIFY_PATH), json.loads(ADVISORY_EVIDENCE_PATH.read_text()),
                                                 'verify_audit', 'verify_copy')
    ran = {}
    for line in read_jsonl(ADVISORY_VERIFY_PATH):
        stage, i = line['custom_id'].split(':')
        ran.setdefault(int(i), set()).add(stage)
    return {i: dict(audit=(audits.get(i) or {}).get('status') or ('failed' if 'verify_audit' in stages else 'not_run'),
                    copy=(copies.get(i) or {}).get('status') or ('failed' if 'verify_copy' in stages else 'not_run'))
            for i, stages in ran.items()}


def cmd_collect_correct():
    """Assemble v1.1 from results already on disk; makes no API calls. Writes the dataset only
    when every candidate has an audit-and-correct result; otherwise writes a pilot summary."""
    v1_rows = {x['source_index']: x for x in read_jsonl(V1_ATTEMPTS_PATH)}
    evidence = public_evidence()
    banks = load_banks()
    no_bank = convert_outcomes()
    outputs, correct_errors = parsed_corrections()
    attempted = {int(l['custom_id'].split(':')[1]) for l in read_jsonl(CORRECT_PATH)}
    candidates = {s['source_index'] for s in correction_candidates()}
    advisory = advisory_checks()

    rows = []
    for s in all_pool_sources():
        i = s['source_index']
        v1 = v1_rows.get(i, {})
        ev = evidence.get(str(i))
        row = dict(split=s['split'], source_group_id=s['source_group_id'], source_id=s['source_id'], source_index=i,
                   topic=s['topic'], broad_topic=s['broad_topic'], difficulty=s['difficulty'], difficulty_band=s['difficulty_band'],
                   input_status=None, accepted_by=None,
                   public_input=dict(final_answer=ev['final_answer'], clues=[c['sentence'] for c in ev['clues']]) if ev else None,
                   original_public_input=None,
                   private=dict(source_question=s['question'], checked_solution=s['checked_solution']),
                   v1_status=v1.get('input_status'), v1_gate_record=v1.get('gate_record'),
                   audit_correct=None, advisory_fresh_check=advisory.get(i), provenance=s['provenance'])
        if str(i) not in banks:
            row['input_status'], row['conversion_reason'] = no_bank[i]
        elif i not in candidates:
            row['input_status'], row['accepted_by'] = 'accepted', 'v1_audit_and_copy'
        elif i not in attempted:
            row['input_status'] = 'pending'
        elif i not in outputs:
            row['input_status'] = 'unresolved'
            row['audit_correct'] = dict(error=correct_errors.get(i))
        else:
            out = outputs[i]
            row['audit_correct'] = dict(decision=out['decision'], findings=out['findings'], reason=out['reason'],
                                        missing_essential_element=out.get('missing_essential_element'),
                                        source_answer_correct=out['source_answer_correct'])
            if out['decision'] == 'UNREPAIRABLE':
                row['input_status'] = 'rejected'
            elif out['decision'] == 'ACCEPT_UNCHANGED':
                row['input_status'], row['accepted_by'] = 'accepted', 'audit_correct_unchanged'
            else:
                row['input_status'], row['accepted_by'] = 'accepted', 'audit_correct_corrected'
                row['original_public_input'] = row['public_input']
                row['public_input'] = dict(final_answer=ev['final_answer'], clues=[c['sentence'] for c in out['corrected_clues']])
                row['private']['corrected_hidden_support'] = [c['hidden_support'] for c in out['corrected_clues']]
        rows.append(row)

    accepted = [x for x in rows if x['input_status'] == 'accepted']
    corrected = [x for x in rows if x['accepted_by'] == 'audit_correct_corrected']
    complete = not any(x['input_status'] == 'pending' for x in rows)
    summary = dict(
        version='RECONSTRUCT-DATASET-v1.1', pipeline='convert -> audit_correct (decision final); v1-accepted kept',
        correction_prompt=CORRECT_VERSION, complete=complete, api_calls_made_by_collect=0,
        status_counts=dict(Counter(x['input_status'] for x in rows)),
        accepted_by=dict(Counter(x['accepted_by'] for x in accepted)),
        accepted_by_split=dict(Counter(x['split'] for x in accepted)),
        accepted_by_split_topic=dict(Counter(f"{x['split']}|{x['broad_topic']}" for x in accepted)),
        accepted_by_split_difficulty=dict(Counter(f"{x['split']}|{x['difficulty_band']}" for x in accepted)),
        audit_correct_decisions=dict(Counter(o['decision'] for o in outputs.values())),
        audit_correct_failures=len(correct_errors),
        advisory_fresh_check_on_corrected=dict(Counter(
            'both passed' if x['advisory_fresh_check'] and x['advisory_fresh_check']['audit'] == 'ACCEPT' and x['advisory_fresh_check']['copy'] == 'no_direct_reconstruction'
            else 'rejected by audit or copy' if x['advisory_fresh_check'] and ('REJECT' in x['advisory_fresh_check'].values() or 'direct_candidate' in x['advisory_fresh_check'].values())
            else 'no verdict' for x in corrected)),
    )
    if complete:
        for name in ('train', 'test'):
            (ROOT / f'{OUT_PREFIX}-{name}.jsonl').write_text(''.join(
                json.dumps(x, ensure_ascii=False) + '\n' for x in accepted if x['split'] == name))
        (ROOT / f'{OUT_PREFIX}-all-attempts.jsonl').write_text(''.join(json.dumps(x, ensure_ascii=False) + '\n' for x in rows))
        r.atomic_write_json(ROOT / f'{OUT_PREFIX}-summary.json', summary)
    else:
        r.atomic_write_json(ROOT / f'{OUT_PREFIX}-pilot-summary.json', summary)
    print(json.dumps(summary, indent=2))


COMMANDS = dict(
    **{'prepare-pool': cmd_prepare_pool},
    **{'submit-convert': cmd_submit_convert},
    **{'realtime-convert': cmd_realtime_convert},
    **{'download-batches': cmd_download_batches},
    **{'collect-convert': cmd_collect_convert},
    **{'submit-gate': cmd_submit_gate},
    **{'realtime-gate': cmd_realtime_gate},
    **{'collect-gate': cmd_collect_gate},
    **{'realtime-correct': cmd_realtime_correct},
    **{'collect-correct': cmd_collect_correct},
)

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('action', choices=list(COMMANDS))
    p.add_argument('--limit', type=int, help='realtime-correct only: seeded sample size (pilot)')
    p.add_argument('--split', choices=['train', 'test'], help='realtime-correct only: restrict candidates to one split')
    a = p.parse_args()
    if a.action == 'realtime-correct':
        cmd_realtime_correct(a.limit, a.split)
    else:
        COMMANDS[a.action]()
