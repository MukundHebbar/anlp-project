#!/usr/bin/env python3
"""Freeze and run paired judge scope controls; never edits benchmark responses."""
import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from anlp_project import reconstruct as r

ROOT = Path('artifacts/reconstruct/judge-scope-at')
PROMPTS = ['evaluate_p3', 'evaluate_p4_standalone']


def prepare():
    assert not (ROOT / 'manifest.json').exists()
    old = r.load_prompt(PROMPTS[0])
    addition = '''Scope and decision priority (apply before assigning the score):
The question field must stand alone. Do not borrow necessary premises from the observations, justification or assumptions to repair it. Resolve ordinary bound symbols inside the question, but an undefined function or missing numerical condition makes it ill-posed. The other fields explain and verify the question; they do not change what it asks.
Check explicit mathematical assertions in the justification independently, including definitions and equalities, even when the final conclusion is true. A false essential mathematical assertion gives score1, not score3 or4.
Choose the verdict consistently: if copy_only, return score0 and shortcut=true. Otherwise a demonstrated wrong answer, ill-posed question or mathematical contradiction gives score1. Use score2 only for an unresolved substantive grounding gap without an established contradiction. Scores3 and4 require substantive inference, shortcut=false and a correct standalone question; distinguish incomplete from sufficient verification as specified below. Uncertain correctness requires needs_review with score null. Check that the JSON fields agree with this decision before returning.

'''
    path = Path('data/prompts/reconstruct/runtime/evaluate_p4_standalone.md')
    assert not path.exists()
    path.write_text(addition + old)
    cases = []

    def pair(family, answer, clues, goodq, goodj, badq, badj, badscore, reason):
        for kind, q, j, score, reference in [
            ('valid', goodq, goodj, 4, goodj),
            ('contrast', badq, badj, badscore, reason),
        ]:
            cases.append(dict(id=f'{family}-{kind}', family=family, final_answer=answer,
                clues=clues, response=dict(question=q, justification=j, assumptions=[]),
                expected_score=score, reference=reference, population='authored diagnostic'))

    pair('rectangle_scope', '6', ['The rectangle has perimeter20.', 'The target is its longer side.'],
         'A rectangle has perimeter20 and area24. What is its longer side?',
         'Sides sum to10 and multiply to24, so they are4 and6. The longer side is6.',
         'A rectangle has perimeter20. What is its longer side?',
         'I infer area24. The sides are4 and6, giving6.', 1,
         'The question omits area24. Sides3 and7 also satisfy it, so6 is not determined.')
    pair('continuity_scope', 'Yes', ['A real function is differentiable on R.', 'Its derivative has absolute value at most2.'],
         'If f:R->R is differentiable and |f\'(x)|<=2 for all x, is f uniformly continuous on R?',
         'The mean value theorem gives |f(x)-f(y)|<=2|x-y|. For epsilon>0 choose delta=epsilon/2.',
         'Is the function uniformly continuous on R?',
         'The mean value theorem and the given derivative bound give delta=epsilon/2.', 1,
         'The question does not specify a function or hypotheses. f(x)=x^2 on R is a counterexample to an unrestricted interpretation.')
    pair('continuity_proof', 'Yes', ['A real function is differentiable on R.', 'Its derivative has absolute value at most2.'],
         'If f:R->R is differentiable and |f\'(x)|<=2 for all x, is f uniformly continuous on R?',
         'By the mean value theorem, |f(x)-f(y)|<=2|x-y|, so delta=epsilon/2 suffices.',
         'If f:R->R is differentiable and |f\'(x)|<=2 for all x, is f uniformly continuous on R?',
         'The mean value theorem gives |f(x)-f(y)|<=2|x-y|. This Lipschitz inequality is the definition of uniform continuity.', 1,
         'A Lipschitz inequality is sufficient, not the definition of uniform continuity; sqrt(x) on [0,infinity) is uniformly continuous but not Lipschitz.')
    pair('distance_copy', '60', ['A vehicle moves at15 km/h for4 hours.'],
         'How many kilometres does a vehicle travel at a constant15 km/h for4 hours?',
         'Distance equals speed times time:15*4=60 km. I inferred distance as the requested quantity.',
         'What is15*4?', '15*4=60.', 0,
         'The bare arithmetic question drops the vehicle/distance meaning and merely restates the numerical operation; assess as a copy shortcut only if that operation is supplied.')
    # Make the copy contrast unambiguous by explicitly supplying its operation.
    cases[-1]['clues'] = ['The multiplication to be evaluated is15*4, which equals60.']
    cases[-1]['reference'] = 'Both requested multiplication and its result are explicit; no missing mathematical content is reconstructed.'
    pair('mean_target', '4', ['The three observations are2,3 and7.'],
         'What is the arithmetic mean of2,3 and7?',
         'Their sum is12 and there are3 observations, so their arithmetic mean is4.',
         'What is the median of2,3 and7?', 'Their sum is12; dividing by3 gives median4.', 1,
         'The sorted list is2,3,7, so its median is3. The response computes a different target.')
    pair('rectangle_proof', '6', ['A rectangle has perimeter20.', 'The requested quantity is its longer side.'],
         'A rectangle has perimeter20 and area24. Find its longer side.',
         'The side lengths are roots of t^2-10t+24=(t-4)(t-6), hence4 and6. Select6.',
         'A rectangle has perimeter20 and area24. Find its longer side.',
         'Its side lengths are3 and8, which sum to10 and multiply to24; the longer side is6.', 1,
         '3+8=11 and max(3,8)=8. A correct final answer does not validate these false assertions.')
    manifest = dict(protocol='docs/plans/reconstruct-amendment-at.md', cases=cases,
                    prompt_hashes={p:r.stable_hash(r.load_prompt(p)) for p in PROMPTS}, budget_usd=.20)
    ROOT.mkdir(parents=True, exist_ok=True)
    r.atomic_write_json(ROOT/'manifest.json', manifest)
    r.atomic_write_json(ROOT/'run.json', dict(metadata=dict(manifest_hash=r.stable_hash(manifest)), records={}, failures=[], attempted=[]))
    print('Frozen12 controls and2 judge prompts; no calls.')


def run():
    manifest = json.loads((ROOT/'manifest.json').read_text())
    state = json.loads((ROOT/'run.json').read_text())
    assert state['metadata']['manifest_hash'] == r.stable_hash(manifest)
    for p in PROMPTS:
        assert r.stable_hash(r.load_prompt(p)) == manifest['prompt_hashes'][p]
    jobs = [(p,c) for c in manifest['cases'] for p in PROMPTS if p+':'+c['id'] not in state['attempted']]
    state['attempted'] += [p+':'+c['id'] for p,c in jobs]
    r.atomic_write_json(ROOT/'run.json', state)
    def worker(p,c):
        text = r.render_template(r.load_prompt(p), dict(FINAL_ANSWER=c['final_answer'], RENDERED_CLUES='\n'.join(c['clues']), STUDENT_RESPONSE=c['response']))
        raw = None
        try:
            raw = r.teacher_call(r.deepinfra_client(180), text, r.DEFAULT_TEACHER_MODEL, 8192, 'low')
            output = r.validate_evaluation(r.extract_json_object(raw['content']), strict_inference=True)
            return p+':'+c['id'], dict(output=output,raw=raw,rendered_prompt=text,case_hash=r.stable_hash(c)), None
        except Exception as exc:
            return p+':'+c['id'], None, dict(error=str(exc),raw=raw or getattr(exc,'raw_response',None),rendered_prompt=text)
    with ThreadPoolExecutor(max_workers=2) as pool:
        for future in as_completed([pool.submit(worker,p,c) for p,c in jobs]):
            key, record, error = future.result()
            if record: state['records'][key] = record
            else: state['failures'].append(dict(id=key, **error))
            r.atomic_write_json(ROOT/'run.json', state)
            print(key, record['output']['score'] if record else 'FAILED '+error['error'], flush=True)
    print('AT terminal; development controls only.', flush=True)


if __name__ == '__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--prepare-only',action='store_true');args=parser.parse_args()
    prepare() if args.prepare_only else run()
