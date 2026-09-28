#!/usr/bin/env python3
"""Freeze or run AD independent mathematical verification controls."""
import argparse,json,sys
from concurrent.futures import ThreadPoolExecutor,as_completed
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from anlp_project import reconstruct as r
ROOT=Path('artifacts/reconstruct/math-verifier-ad')

def prepare():
    assert not (ROOT/'manifest.json').exists();ROOT.mkdir(exist_ok=True)
    families=[
      ('continuity','Yes',['The function is defined on the real line.','Its absolute value at x is |x|.'], 'Is the function f(x)=|x| continuous at0?',
       'For every epsilon>0 choose delta=epsilon. If |x|<delta, then |f(x)-f(0)|=|x|<epsilon. Thus f is continuous at0.',
       'The function |x| is differentiable at0 with derivative0, and differentiability implies continuity, so it is continuous at0.',
       'Right derivative is1, left derivative is-1, so differentiability at0 is false. The continuity conclusion is nevertheless true.'),
      ('probability','11/36',['Two fair six-sided dice are independent.','The desired event involves a six.'],'What is the probability that at least one of two independent fair six-sided dice shows6?',
       'The complement is no six on either die, with probability(5/6)^2=25/36; subtracting from1 gives11/36.',
       'Let A and B mean the first and second dice show6. A and B are mutually exclusive. Inclusion-exclusion gives P(A union B)=1/6+1/6-1/36=11/36.',
       'The claim of mutual exclusion is false: both show6 with probability1/36. A correct numerical formula does not validate that false claim.'),
      ('quadratic','2 and 3',['A monic quadratic has two real roots.','Their sum is5.'],'Find the real roots of x^2-5x+6=0.',
       'Factor x^2-5x+6=(x-2)(x-3), so the roots are2 and3.',
       'Factor x^2-5x+6=(x-2)(x+3). Setting each factor to zero gives roots2 and3.',
       '(x-2)(x+3)=x^2+x-6 and its second root is-3, so both factorization and stated inference are false.'),
      ('tree','5',['A finite simple graph has six vertices.','Connectedness is relevant to the edge count.'],'How many edges does a tree with six vertices have?',
       'A tree has n-1 edges, proved by removing a leaf inductively. For n=6 this gives5.',
       'Every connected simple graph with six vertices has exactly five edges. A tree is connected, so its edge count is5.',
       'The cycle C6 is connected with six edges, refuting the universal premise. Trees specifically have five edges.')]
    cases=[]
    for family,answer,clues,q,good,bad,reason in families:
        for kind,proof in [('valid',good),('invalid',bad)]:
            cases.append({'id':family+'-'+kind,'family':family,'population':'authored','expected':kind,'final_answer':answer,'clues':clues,'response':{'question':q,'justification':proof,'assumptions':[]},'reference':good if kind=='valid' else reason})
    for directory,index,q,proof,reason in [
       ('missing-premise-ab',62,None,'Writing w=z-pi gives sin(pi+w)=-sin(w), so f=-sin(w)/w^2=-1/w+w/6-... . The regular part is entire in w and the only negative-power term is -1/w. Hence the Laurent expansion about pi converges for every0<|w|<infinity and has outer radius infinity.','The raw response claims a double pole, but the numerator has a simple zero, so f has a simple pole. Its nearest-singularity explanation is also inconsistent.'),
       ('premises-first-ac',129,'How many length12 words over digits0,1,2,3,4,5,6 have neighboring digits differing by exactly1, reduced modulo2008?','Let f1(d)=1 for all seven digits. Iterate f(k+1,d)=f(k,d-1)+f(k,d+1), using zero only outside0..6. At length12 the vector is[396,792,956,1120,956,792,396], summing to5408. Thus the remainder is5408-2*2008=1392.','The raw question leaves the fixed length unspecified. Length1 gives7 and length2 gives12. Its claimed sum over all lengths1..19 actually gives1115 modulo2008, not1392.')]:
        path=Path('artifacts/reconstruct')/directory/'student.json';run=json.loads(path.read_text());key,response=next((k,v) for k,v in run['responses'].items() if v['source_index']==index)
        for kind in ['invalid','valid']:
            value=response['output'] if kind=='invalid' else {'question':q or response['output']['question'],'justification':proof,'assumptions':[]}
            cases.append({'id':f'production-{index}-{kind}','family':f'production-{index}','population':'production_diagnostic' if kind=='invalid' else 'authored_correction_NOT_QWEN','expected':kind,'final_answer':response['public_evidence']['final_answer'],'clues':response['public_evidence']['clues'],'response':value,'reference':reason if kind=='invalid' else proof,'parent':{'artifact':str(path),'response_key':key,'response_hash':r.stable_hash(response)}})
    assert len(cases)==12
    prompt=r.load_prompt('verify_math_p1');manifest={'protocol':'docs/plans/reconstruct-amendment-ad.md','prompt_hash':r.stable_hash(prompt),'cases':cases,'budget_usd':.15,'calls':12}
    r.atomic_write_json(ROOT/'manifest.json',manifest);r.atomic_write_json(ROOT/'run.json',{'metadata':{'manifest_hash':r.stable_hash(manifest)},'records':{},'failures':[]})
    print('Frozen12 cases, no model calls')

def validate(value,response):
    assert value.get('status') in ['valid','invalid','uncertain']
    assert isinstance(value.get('reason'),str) and value['reason'].strip()
    for field in ['question_answer_correct','verification_sound']:assert field in value and type(value[field]) in [bool,type(None)]
    checks=value.get('checks');assert isinstance(checks,list) and checks
    texts=[str(response.get(f,'')) for f in ['question','justification']]+response.get('assumptions',[])
    for check in checks:
        assert check.get('verdict') in ['supported','false','unresolved']
        assert isinstance(check.get('claim_quote'),str) and check['claim_quote'] and any(check['claim_quote'] in t for t in texts)
        assert isinstance(check.get('evidence'),str) and check['evidence'].strip()
    if value['status']=='valid':assert value['question_answer_correct'] is True and value['verification_sound'] is True and all(c['verdict']=='supported' for c in checks)
    if value['status']=='invalid':assert False in [value['question_answer_correct'],value['verification_sound']] and any(c['verdict']=='false' for c in checks)
    return value

def run():
    manifest=json.loads((ROOT/'manifest.json').read_text());state=json.loads((ROOT/'run.json').read_text());assert state['metadata']['manifest_hash']==r.stable_hash(manifest)
    template=r.load_prompt('verify_math_p1');assert r.stable_hash(template)==manifest['prompt_hash']
    attempted=set(state.get('attempted',[]))|set(state['records'])|{f['id'] for f in state['failures']};jobs=[c for c in manifest['cases'] if c['id'] not in attempted]
    assert len(jobs)*8192*.6/1e6 < manifest['budget_usd']
    state['attempted']=sorted(attempted|{c['id'] for c in jobs})
    r.atomic_write_json(ROOT/'run.json',state)
    def worker(case):
        prompt=r.render_template(template,{'FINAL_ANSWER':case['final_answer'],'RENDERED_CLUES':'\n'.join(case['clues']),'STUDENT_RESPONSE':case['response']});raw=None
        try:
            raw=r.teacher_call(r.deepinfra_client(180),prompt,r.DEFAULT_TEACHER_MODEL,8192,'low');out=validate(r.extract_json_object(raw['content']),case['response'])
            return case['id'],{'output':out,'raw':raw,'rendered_prompt':prompt,'prompt_hash':r.stable_hash(prompt),'case_hash':r.stable_hash(case)},None
        except Exception as exc:return case['id'],None,{'id':case['id'],'error':str(exc),'raw':raw or getattr(exc,'raw_response',None),'rendered_prompt':prompt}
    with ThreadPoolExecutor(max_workers=4) as pool:
        for future in as_completed([pool.submit(worker,c) for c in jobs]):
            key,record,error=future.result()
            if record:state['records'][key]=record
            else:state['failures'].append(error)
            r.atomic_write_json(ROOT/'run.json',state);print(key,record['output']['status'] if record else 'FAILED '+error['error'],flush=True)
    print('AD calls terminal; inspect all exact quotes and mathematical certificates before adoption',flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--prepare-only',action='store_true');a=p.parse_args();prepare() if a.prepare_only else run()
