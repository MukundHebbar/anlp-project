#!/usr/bin/env python3
"""Frozen once-only versioned PC judge calibration, with labels hidden from the model."""
import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from anlp_project import reconstruct as r
from anlp_project.reconstruct_judge_validation import validate_judgment, validation_notes
ROOT = Path('artifacts/reconstruct/judge-calibration-bb')
PROMPTS = Path('data/prompts/reconstruct/partial_credit_v2')

def fixtures():
    cases = []
    def fidelity(name, source, candidate, p, t, equivalent):
        cases.append(dict(id=name, role='fidelity', source=source, question=candidate,
                          expected={'premise_fidelity.score':p, 'target_fidelity.score':t,
                                    'semantic_equivalent':equivalent}))
    fidelity('long_cycles_equivalent', 'How many permutations of100 elements contain at least one cycle of length at least51?', 'How many permutations of100 elements contain exactly one cycle of length at least51?', 4,4,True)
    fidelity('long_cycles_not_equivalent', 'How many permutations of100 elements contain at least one cycle of length at least40?', 'How many permutations of100 elements contain exactly one cycle of length at least40?', 4, [2,3],False)
    fidelity('missing_parameter_same_target', 'Find the remainder of51! modulo61.', 'Find the remainder of n! modulo61, where n is a positive integer.',2,4,False)
    fidelity('wrong_parameter_same_target', 'How many integer points satisfy x^2-y^2=2000^2?', 'How many integer points satisfy x^2-y^2=400^2?', [2,3],4,False)
    fidelity('equivalent_algebra', 'A rectangle has perimeter30 and area54. Find its longer side.', 'For positive x,y with x+y=15 and xy=54, find max(x,y).',4,4,True)
    fidelity('different_target', 'A rectangle has perimeter30 and area54. Find its longer side.', 'A rectangle has perimeter30 and area54. Find its shorter side.',4,2,False)
    def validity(name, question, proof, m, shortcut, answer='9', clues=None):
        response={'question':question,'assumptions':[], 'justification':proof}
        cases.append(dict(id=name,role='validity',question=question,response=response,
                          answer=answer,clues=clues or ['The two positive sides sum to15.', 'The product of the sides is54.'],
                          expected={'mathematical_validity.score':m,'shortcut.present':shortcut}))
    validity('correct_short_proof', 'A rectangle has perimeter30 and area54. Find its longer side.', 'The sides are roots of t^2-15t+54=(t-6)(t-9), so the longer side is9.',4,False)
    validity('false_proof_correct_answer', 'A rectangle has perimeter30 and area54. Find its longer side.', 'The sides are5 and9 because5+9=15 and5*9=54. The longer side is9.',1,False)
    validity('circular_proof_not_tautological_question', 'A rectangle has perimeter30 and area54. Find its longer side.', 'The supplied answer is9, therefore the answer is9.',0,False)
    validity('missing_premise_not_tautology', 'A rectangle has perimeter30. Find its longer side.', 'Assume its area is54. Then the side equation t^2-15t+54=0 gives9.',1,False)
    validity('inverse_target_not_tautology', 'A rectangle has perimeter30 and longer side9. Find its area.', 'The other side is15-9=6, so the area is54.',1,False)
    validity('actual_tautology', 'A rectangle has longer side9. What is its longer side?', 'Its longer side is9 by the premise.',[0,1],True)
    validity('valid_inverse_inference', 'For a positive integer m=3, find the number of subsets of a set with m elements.', 'A set with m elements has2^m subsets. The supplied answer8 implies m=3; for the reconstructed question the count is2^3=8.',4,False,answer='8',clues=['A subset count is requested.', 'Each element has two independent inclusion choices.'])
    validity('wrong_answer_sound_calculation', 'A rectangle has perimeter30 and area54. Find its shorter side.', 'The side equation factors as(t-6)(t-9)=0; the shorter side is6, not the supplied9.',1,False)
    # Real regression cases: judge outputs are NOT included in the prompt.
    manifest=json.loads(Path('artifacts/reconstruct/partial-credit-ba/manifest.json').read_text())
    for key,expected in [('zero:5:fidelity',{'premise_fidelity.score':4,'target_fidelity.score':4,'semantic_equivalent':True}),('zero:16:validity',{'shortcut.present':False,'mathematical_validity.score':1}),('one:10:validity',{'shortcut.present':False,'mathematical_validity.score':[0,1]}),('two:54:validity',{'shortcut.present':False,'mathematical_validity.score':[3,4]}),('two:113:validity',{'shortcut.present':False,'mathematical_validity.score':[3,4]})]:
        c=next(c for c in manifest['cases'] if c['id']==key)
        saved=json.loads(Path(c['source_file']).read_text());v=saved['responses'][c['response_key']]
        ev=v['public_evidence']
        cases.append(dict(id='regression:'+key,role=c['role'],question=v['output']['question'],response=v['output'],source=saved['sources'][str(v['source_index'])]['question'],answer=ev['final_answer'],rendered_clues=ev['rendered_clues'],clue_count=ev['clue_count'],expected=expected))
    return cases

def prepare():
    assert not (ROOT/'manifest.json').exists(), 'Manifest already frozen'
    prompts={role:(PROMPTS/f'judge_{role}.md').read_text() for role in ['fidelity','validity']}
    cases=fixtures()
    for c in cases:
        c['clue_count']=c.get('clue_count',len(c.get('clues',[])))
        args=dict(SOURCE_QUESTION=c.get('source',''),CANDIDATE_QUESTION=c['question'],FINAL_ANSWER=c.get('answer',''),STUDENT_RESPONSE=c.get('response',{}),RENDERED_CLUES=c.get('rendered_clues','\n'.join(f'{i}. {x}' for i,x in enumerate(c.get('clues',[]),1))))
        c['rendered_prompt']=r.render_template(prompts[c['role']],args)
    manifest=dict(validator_hash=r.stable_hash(Path('src/anlp_project/reconstruct_judge_validation.py').read_text()),version=PROMPTS.name+'/'+ROOT.name,cases=cases,prompts=prompts,model=r.DEFAULT_TEACHER_MODEL,max_tokens=8192,reasoning_effort='low',temperature=0,workers=3,retries=0,labels='Authored development and transfer controls plus known real regressions; not independent human gold or held-out benchmark.',acceptance='All required labels match, all certificates pass structural checks; failures/missing labels block promotion. No claim of universal correctness.')
    r.atomic_write_json(ROOT/'manifest.json',manifest)
    r.atomic_write_json(ROOT/'run.json',dict(metadata={'manifest_hash':r.stable_hash(manifest)},records={},failures=[],attempted=[]))
    print('Frozen',len(cases),'cases')

def run():
    manifest=json.loads((ROOT/'manifest.json').read_text());state=json.loads((ROOT/'run.json').read_text())
    assert state['metadata']['manifest_hash']==r.stable_hash(manifest)
    if 'validator_hash' in manifest:assert manifest['validator_hash']==r.stable_hash(Path('src/anlp_project/reconstruct_judge_validation.py').read_text())
    for role,prompt in manifest['prompts'].items():assert (PROMPTS/f'judge_{role}.md').read_text()==prompt
    cases=[c for c in manifest['cases'] if c['id'] not in state['attempted']]
    state['attempted'] += [c['id'] for c in cases];r.atomic_write_json(ROOT/'run.json',state)
    def worker(c):
        raw=None;out=None
        try:
            raw=r.teacher_call(r.deepinfra_client(180),c['rendered_prompt'],manifest['model'],8192,'low')
            out=r.extract_json_object(raw['content'])
            validate_judgment(out,c['role'],question=c['question'],response=c.get('response'),clue_count=c['clue_count'])
            return c,dict(output=out,raw=raw,case_hash=r.stable_hash(c),validation_notes=validation_notes(out,c.get('response',{}))),None
        except Exception as exc:return c,None,dict(id=c['id'],error=str(exc),output=out,raw=raw or getattr(exc,'raw_response',None))
    with ThreadPoolExecutor(max_workers=3) as pool:
        for f in as_completed([pool.submit(worker,c) for c in cases]):
            c,record,error=f.result()
            if record:state['records'][c['id']]=record
            else:state['failures'].append(error)
            r.atomic_write_json(ROOT/'run.json',state);print(c['id'],'returned' if record else 'FAILED '+error['error'],flush=True)
    report()

def report():
    m=json.loads((ROOT/'manifest.json').read_text());s=json.loads((ROOT/'run.json').read_text())
    assert s['metadata']['manifest_hash']==r.stable_hash(m)
    rows=[]
    for c in m['cases']:
        rec=s['records'].get(c['id']);checks=[]
        if rec:
            checks.append(dict(field='status',expected='scored',actual=rec['output'].get('status'),match=rec['output'].get('status')=='scored'))
            assert rec['case_hash']==r.stable_hash(c)
            for path,wanted in c['expected'].items():
                value=rec['output']
                for key in path.split('.'):value=value.get(key,{}) if isinstance(value,dict) else None
                match=value in wanted if isinstance(wanted,list) else type(value)==type(wanted) and value==wanted
                checks.append(dict(field=path,expected=wanted,actual=value,match=match))
        rows.append(dict(id=c['id'],returned=rec is not None,passed=bool(checks) and all(x['match'] for x in checks),checks=checks))
    terminal_ids=set(s['records'])|{f['id'] for f in s['failures']}
    result=dict(terminal=len(terminal_ids)==len(rows),pending=len(rows)-len(terminal_ids),planned=len(rows),returned=len(s['records']),failed=len(s['failures']),passed=sum(x['passed'] for x in rows),rows=rows,limitation=m['labels'])
    r.atomic_write_json(ROOT/'report.json',result);print(json.dumps(result,indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['prepare','run','report']);parser.add_argument('--root',type=Path,default=ROOT);parser.add_argument('--prompts',type=Path,default=PROMPTS);args=parser.parse_args()
    ROOT=args.root;PROMPTS=args.prompts;ROOT.mkdir(parents=True,exist_ok=True)
    {'prepare':prepare,'run':run,'report':report}[args.action]()
