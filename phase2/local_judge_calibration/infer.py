"""Score the frozen historical calibration requests using the original one-token label recipe."""
import argparse
import json
import math
from pathlib import Path
import statistics
import sys
import time
import random

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
from anlp_project.qwen_judging import SYSTEM, render_question, label_probs


def find_label_tokens(tokenizer, labels):
    """All single-token spellings accepted by the historical label reader."""
    wanted = {label.lower() for label in labels}
    found = {label: [] for label in wanted}
    for token_id in tokenizer.get_vocab().values():
        text = tokenizer.decode([token_id]).strip().lower()
        if text in wanted:
            found[text].append(token_id)
    if any(not ids for ids in found.values()):
        raise ValueError(f'Labels without a single-token spelling: {found}')
    return found


def explicit_label_probs(scores, labels, token_ids):
    masses = [sum(math.exp(scores[i].logprob) for i in token_ids[label.lower()] if i in scores)
              for label in labels]
    if any(i not in scores for label in labels for i in token_ids[label.lower()]):
        raise ValueError('Engine omitted explicitly requested label token probabilities')
    total = sum(masses)
    return ([m / total for m in masses] if total else [1/len(labels)]*len(labels)), total


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--model-path', required=True)
    parser.add_argument('--name', choices=['selene', 'gemma'], required=True)
    parser.add_argument('--out', required=True)
    parser.add_argument('--limit', type=int, default=0)
    parser.add_argument('--label-protocol', choices=['top20', 'explicit'], default='top20')
    parser.add_argument('--requests', type=Path, default=ROOT/'artifacts/qwen-judge-calibration/requests.jsonl')
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    source = args.requests
    requests = [json.loads(line) for line in source.open()][:args.limit or None]
    # Interleave complete response groups for useful intermediate checks; fit/held-out assignment is unchanged.
    groups = {}
    for request in requests:
        groups.setdefault(request['key'].rsplit('|', 1)[0], []).append(request)
    ordered = list(groups.values())
    random.Random(0).shuffle(ordered)
    requests = [r for group in ordered for r in group]
    from vllm import LLM, SamplingParams
    from vllm.inputs import TokensPrompt
    llm = LLM(model=args.model_path, dtype='bfloat16', language_model_only=True,
              max_model_len=40960, max_num_seqs=32, gpu_memory_utilization=.90,
              seed=0, enable_prefix_caching=True, max_logprobs=256)
    tokenizer = llm.get_tokenizer()
    all_labels = sorted({label for request in requests for q in request['questions'].values()
                         for label in render_question(request['state'], q)[1]})
    label_ids = find_label_tokens(tokenizer, all_labels) if args.label_protocol == 'explicit' else None
    prompts, mapping, lengths = [], [], []
    for request in requests:
        for name, q in request['questions'].items():
            user, labels, meaning = render_question(request['state'], q)
            prompt = tokenizer.apply_chat_template([
                {'role': 'system', 'content': SYSTEM}, {'role': 'user', 'content': user}],
                tokenize=False, add_generation_prompt=True, enable_thinking=False) + 'Answer: '
            ids = tokenizer.encode(prompt, add_special_tokens=False)
            n = len(ids)
            assert n < 40960, (request['key'], name, n)
            prompts.append(TokensPrompt(prompt_token_ids=ids))
            lengths.append(n)
            mapping.append((request['key'], name, q, labels, meaning))
    t0 = time.monotonic()
    records, masses = {}, []
    for request in requests:
        records[request['key']] = {'key': request['key'], 'ok': True,
                                   'response': {'model': args.name, 'answers': {}}}
    raw = []
    def consume(item, output):
        key, name, q, labels, meaning = item
        scores = output.outputs[0].logprobs[0] if output.outputs[0].logprobs else {}
        top = {(token.decoded_token if token.decoded_token is not None else tokenizer.decode([token_id])):
               token.logprob for token_id, token in scores.items()}
        probs, mass = (explicit_label_probs(scores, labels, label_ids) if label_ids is not None
                       else label_probs(top, labels))
        masses.append(mass)
        if mass == 0:
            records[key]['ok'] = False
            records[key]['error'] = 'Zero allowed-label probability mass'
        if q['type'] == 'score':
            answer = {'type': 'score', 'score': sum(i*p for i, p in enumerate(probs)),
                      'probabilities': dict(zip(labels, probs)), 'mass': mass}
        elif q['type'] == 'noul':
            answer = {'type': 'noul', 'noul': probs[0], 'mass': mass}
        else:
            answer = {'type': 'choice', 'choice': meaning[max(range(len(probs)), key=probs.__getitem__)],
                      'probabilities': dict(zip(meaning, probs)), 'mass': mass}
        records[key]['response']['answers'][name] = answer
        raw.append({'key': key, 'question': name, 'generated': output.outputs[0].text,
                    'top_logprobs': top, 'label_mass': mass})
    expected = {r['key']: set(r['questions']) for r in requests}
    for start in range(0, len(prompts), 512):
        params = [SamplingParams(max_tokens=1, temperature=0, seed=0,
                    **({'logprob_token_ids': sorted({i for label in item[3] for i in label_ids[label.lower()]})}
                       if label_ids is not None else {'logprobs': 20}))
                  for item in mapping[start:start+512]]
        outputs = llm.generate(prompts[start:start+512], params, use_tqdm=True)
        for item, output in zip(mapping[start:start+512], outputs, strict=True):
            consume(item, output)
        complete = [r for k,r in records.items() if set(r['response']['answers']) == expected[k]]
        for filename, rows in [('answers.jsonl', complete), ('label-logprobs.jsonl', raw)]:
            temporary = out / (filename+'.tmp')
            with temporary.open('w') as f:
                for row in rows:
                    f.write(json.dumps(row, ensure_ascii=False)+'\n')
            temporary.replace(out/filename)
        progress = {'questions_done':len(raw),'questions_total':len(prompts),'complete_requests':len(complete),
                    'label_mass_median':statistics.median(masses), 'zero_mass':sum(m==0 for m in masses)}
        (out/'progress.json').write_text(json.dumps(progress,indent=2))
        print('CALIBRATION_PROGRESS',json.dumps(progress),flush=True)
    meta = {'name': args.name, 'model_source': json.loads((Path(args.model_path)/'source.json').read_text()),
            'requests_path':str(source),
            'recipe': 'original rubric/state, native chat, Answer prefix, one token, T=0',
            'label_protocol': args.label_protocol,
            'label_token_ids': label_ids,
            'requests': len(requests), 'questions': len(prompts), 'ok': sum(r['ok'] for r in records.values()),
            'label_mass_median': statistics.median(masses),
            'label_mass_below_half': sum(m < .5 for m in masses), 'zero_label_mass': sum(m == 0 for m in masses),
            'prompt_tokens': sum(lengths), 'max_prompt_tokens': max(lengths),
            'inference_seconds': time.monotonic()-t0}
    (out / 'metadata.json').write_text(json.dumps(meta, indent=2))
    (out / 'done').write_text('ok\n')
    print(json.dumps({k:v for k,v in meta.items() if k!='model_source'}, indent=2), flush=True)


if __name__ == '__main__':
    main()
