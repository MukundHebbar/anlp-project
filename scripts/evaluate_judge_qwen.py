#!/usr/bin/env python3
"""Evaluate Qwen3-4B on the JUDGE high-confidence set, rated by DeepSeek against the key.

Two model steps, then assembly (resumable; finished items are never rerun):
  generate  Qwen3-4B (local llama.cpp, non-thinking) answers each item's qwen_prompt verbatim
  rate      DeepSeek V4.1 Flash scores each response against the private answer key
  collect   0-100 score and 1-5 rating (RECONSTRUCT rating v4), summary; no API calls

Score: four dimensions 0-4 (V verdict, L localization, E error explanation,
M mathematical soundness), total = 6.25 * (V+L+E+M), binned with the same v4 boundaries
as RECONSTRUCT. Verdict and step are also parsed from Qwen's text, to cross-check DeepSeek.
"""
import argparse
import csv
import hashlib
import json
import re
import statistics
import sys
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from anlp_project import reconstruct as r
from anlp_project.reconstruct_partial_credit import BALANCED_V4_BOUNDARIES, balanced_rating_v4

PUBLIC = Path('local/archive/legacy/judge_data/judge-high-confidence-public.jsonl')
KEY = Path('local/archive/legacy/judge_data/judge-high-confidence-private-key.jsonl')
RATE_PROMPT = Path('data/prompts/judge/judge_eval_p1.md')
OUT = Path('artifacts/qwen3-4b/judge/high-confidence-78')
RESPONSES = OUT / 'qwen-responses.jsonl'
RATINGS = OUT / 'deepseek-ratings.jsonl'
SAMPLING = r.SamplingConfig(temperature=0.7, top_p=0.8, top_k=20, max_tokens=8192, seed=0)
DIMENSIONS = ('V', 'L', 'E', 'M')
TRANSPORT_ERRORS = ('APIConnectionError', 'APITimeoutError', 'InternalServerError', 'RateLimitError')


def read_jsonl(path):
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()] if path.exists() else []


def append(path, row, lock):
    with lock, path.open('a') as f:
        f.write(json.dumps(row, ensure_ascii=False) + '\n')


def items():
    keys = {k['judge_id']: k for k in read_jsonl(KEY)}
    public = read_jsonl(PUBLIC)
    assert len(public) == len(keys) and all(p['judge_id'] in keys for p in public), 'public/key mismatch'
    return [dict(p, key=keys[p['judge_id']]) for p in public]


def parse_student(text):
    decision = re.search(r'Decision:\s*[*_`]*\s*(correct|incorrect)\b', text or '', re.I)
    step = re.search(r'First wrong step:\s*[*_`]*\s*(S\d+|none)\b', text or '', re.I)
    return (decision.group(1).lower() if decision else None,
            (step.group(1).upper() if step.group(1).lower() != 'none' else 'none') if step else None)


def cmd_generate():
    OUT.mkdir(parents=True, exist_ok=True)
    done = {x['judge_id'] for x in read_jsonl(RESPONSES)}
    todo = [x for x in items() if x['judge_id'] not in done]
    print(f'{len(done)} already generated; running {len(todo)} with {r.DEFAULT_MODEL}', flush=True)
    client, lock = r.local_client(timeout=900), threading.Lock()
    for n, x in enumerate(todo, 1):
        try:
            raw = r.student_call(client, x['qwen_prompt'], r.DEFAULT_MODEL, SAMPLING)
            if r.has_generated_thinking(raw):
                raise ValueError('Unexpected thinking output')
            row = dict(judge_id=x['judge_id'], ok=True, content=raw['content'], raw=raw)
        except Exception as exc:
            raw = getattr(exc, 'raw_response', None) or {}
            row = dict(judge_id=x['judge_id'], ok=False, content=raw.get('content', ''), raw=raw,
                       error=f'{type(exc).__name__}: {str(exc)[:300]}')
        append(RESPONSES, row, lock)
        print(time.strftime('%H:%M:%S'), f'{n}/{len(todo)}', x['judge_id'], 'ok' if row['ok'] else row['error'][:80], flush=True)


def render_rating_prompt(template, x, response):
    key = x['key']
    answer_key = dict(label=key['label'], first_wrong_step=key['first_error_step_id'] or 'none',
                      error_explanation=key['first_error_explanation'], error_type=key['error_type'],
                      reference_response=key['teacher_target_response'])
    return r.render_template(template, dict(
        PROBLEM=x['problem'],
        PROPOSED_SOLUTION='\n'.join(f"{s['step_id']}: {s['text']}" for s in x['proposed_solution']),
        ANSWER_KEY=json.dumps(answer_key, ensure_ascii=False, indent=1),
        STUDENT_RESPONSE=response or '(empty response)'))


def validate_rating(out, label):
    assert out.get('status') in ('scored', 'needs_review'), 'Invalid status'
    scores = {}
    for d in DIMENSIONS:
        s = (out.get(d) or {}).get('score', 'missing')
        assert s is None or (type(s) is int and 0 <= s <= 4), f'Invalid {d} score'
        assert isinstance((out.get(d) or {}).get('reason'), str), f'{d} missing reason'
        scores[d] = s
    if out['status'] == 'scored':
        assert all(s is not None for s in scores.values()), 'scored with an unresolved dimension'
    if scores['V'] is not None:
        assert scores['V'] in (0, 4), 'V must be 0 or 4'
    if scores['L'] is not None:
        assert scores['L'] in ((0, 2, 4) if label == 'incorrect' else (0, 4)), 'L outside the allowed values'
    if scores['V'] == 0:
        assert scores['L'] in (0, None) and scores['E'] in (0, None), 'Wrong verdict must score L=0 and E=0'
    return out


def cmd_rate():
    responses = {x['judge_id']: x for x in read_jsonl(RESPONSES)}
    by_id = {x['judge_id']: x for x in items()}
    assert set(responses) == set(by_id), 'Run generate first: some items have no Qwen response'
    done = {x['judge_id'] for x in read_jsonl(RATINGS)}
    template = RATE_PROMPT.read_text()
    todo = [i for i in by_id if i not in done]
    print(f'{len(done)} already rated; rating {len(todo)} with {r.DEFAULT_TEACHER_MODEL}', flush=True)
    client, lock = r.deepinfra_client(900), threading.Lock()

    def rate(judge_id):
        prompt = render_rating_prompt(template, by_id[judge_id], responses[judge_id]['content'])
        for attempt in range(4):
            try:
                raw = r.teacher_call(client, prompt, r.DEFAULT_TEACHER_MODEL, 8192, 'low')
                row = dict(judge_id=judge_id, ok=True, raw=raw, prompt_sha256=hashlib.sha256(prompt.encode()).hexdigest())
                break
            except Exception as exc:
                if type(exc).__name__ in TRANSPORT_ERRORS and attempt < 3:
                    time.sleep(5 * 2 ** attempt)
                    continue
                row = dict(judge_id=judge_id, ok=False, raw=getattr(exc, 'raw_response', None),
                           error=f'{type(exc).__name__}: {str(exc)[:300]}')
                break
        append(RATINGS, row, lock)

    with ThreadPoolExecutor(max_workers=16) as pool:
        list(pool.map(rate, todo))
    print('rating finished', flush=True)


def cmd_collect():
    by_id = {x['judge_id']: x for x in items()}
    responses = {x['judge_id']: x for x in read_jsonl(RESPONSES)}
    ratings = {x['judge_id']: x for x in read_jsonl(RATINGS)}
    rows = []
    for judge_id, x in by_id.items():
        key, resp, rating = x['key'], responses.get(judge_id), ratings.get(judge_id)
        decision, step = parse_student(resp['content'] if resp else '')
        truth_step = key['first_error_step_id'] or 'none'
        parsed, error = None, None
        try:
            assert rating and rating['ok'], (rating or {}).get('error', 'not rated')
            parsed = validate_rating(r.extract_json_object(rating['raw']['content']), key['label'])
        except Exception as exc:
            error = f'{type(exc).__name__}: {str(exc)[:200]}'
        dims = {d: (parsed or {}).get(d, {}).get('score') for d in DIMENSIONS}
        scored = parsed is not None and parsed['status'] == 'scored'
        score = 6.25 * sum(dims.values()) if scored else None
        rows.append(dict(
            judge_id=judge_id, problem=x['problem'], proposed_solution=x['proposed_solution'],
            key_label=key['label'], key_first_wrong_step=truth_step, key_error_type=key['error_type'],
            key_error_position=key['error_position'], key_explanation=key['first_error_explanation'],
            qwen_response=resp['content'] if resp else None, qwen_error=resp.get('error') if resp else 'no response',
            qwen_decision=decision, qwen_first_wrong_step=step,
            parsed_verdict_correct=decision == key['label'] if decision else None,
            parsed_step_correct=(step == truth_step) if step and decision == key['label'] else (False if decision else None),
            deepseek=parsed, deepseek_error=error, dimensions=dims,
            score_100=score, rating_1_to_5=balanced_rating_v4(score) if scored else None,
            provenance=key['provenance']))

    scored = [x for x in rows if x['score_100'] is not None]
    agree_v = [x for x in scored if x['qwen_decision'] and (x['dimensions']['V'] == 4) == x['parsed_verdict_correct']]
    cost = sum((((x.get('raw') or {}).get('usage')) or {}).get('estimated_cost') or 0 for x in ratings.values())

    def group(key_fn):
        out = {}
        for k in sorted({key_fn(x) for x in rows}, key=str):
            g = [x for x in rows if key_fn(x) == k]
            s = [x['score_100'] for x in g if x['score_100'] is not None]
            out[str(k)] = dict(n=len(g), verdict_accuracy=round(sum(bool(x['parsed_verdict_correct']) for x in g) / len(g), 3),
                               mean_score=round(statistics.mean(s), 2) if s else None)
        return out

    wrong_items = [x for x in rows if x['key_label'] == 'incorrect']
    summary = dict(
        dataset=str(PUBLIC), items=len(rows), qwen_model=r.DEFAULT_MODEL, sampling=vars(SAMPLING),
        rater_model=r.DEFAULT_TEACHER_MODEL, rater_prompt=str(RATE_PROMPT),
        rating_boundaries=list(BALANCED_V4_BOUNDARIES),
        qwen_failures=sum(1 for x in rows if x['qwen_error']), rater_failures=sum(1 for x in rows if x['deepseek_error']),
        scored=len(scored),
        mean_score=round(statistics.mean(x['score_100'] for x in scored), 2) if scored else None,
        median_score=statistics.median(x['score_100'] for x in scored) if scored else None,
        rating_histogram={str(k): sum(x['rating_1_to_5'] == k for x in scored) for k in range(1, 6)},
        dimension_means={d: round(statistics.mean(x['dimensions'][d] for x in scored), 2) for d in DIMENSIONS} if scored else None,
        parsed_verdict_accuracy=round(sum(bool(x['parsed_verdict_correct']) for x in rows) / len(rows), 3),
        parsed_first_step_accuracy_on_incorrect=round(sum(bool(x['parsed_step_correct']) for x in wrong_items) / len(wrong_items), 3),
        unparseable_qwen_responses=sum(x['qwen_decision'] is None for x in rows),
        deepseek_verdict_agrees_with_parse=f'{len(agree_v)}/{sum(1 for x in scored if x["qwen_decision"])}',
        by_key_label=group(lambda x: x['key_label']),
        by_error_position=group(lambda x: x['key_error_position']),
        rater_cost_usd=round(cost, 4),
    )
    with (OUT / 'results.jsonl').open('w') as f:
        for x in rows:
            f.write(json.dumps(x, ensure_ascii=False) + '\n')
    with (OUT / 'results.csv').open('w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['judge_id', 'key_label', 'key_first_wrong_step', 'key_error_position', 'qwen_decision',
                    'qwen_first_wrong_step', 'V', 'L', 'E', 'M', 'score_100', 'rating_1_to_5', 'deepseek_summary', 'qwen_response'])
        for x in rows:
            w.writerow([x['judge_id'], x['key_label'], x['key_first_wrong_step'], x['key_error_position'], x['qwen_decision'],
                        x['qwen_first_wrong_step'], *[x['dimensions'][d] for d in DIMENSIONS], x['score_100'],
                        x['rating_1_to_5'], (x['deepseek'] or {}).get('summary'), x['qwen_response']])
    (OUT / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('action', choices=['generate', 'rate', 'collect'])
    {'generate': cmd_generate, 'rate': cmd_rate, 'collect': cmd_collect}[p.parse_args().action]()
