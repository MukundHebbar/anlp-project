#!/usr/bin/env python3
"""AE private-certificate audit; exact public inputs remain unchanged."""
import argparse,json,sys
from concurrent.futures import ThreadPoolExecutor,as_completed
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from anlp_project import reconstruct as r
from anlp_project.reconstruct_gates import public_disclosure_text,validate_strict_disclosure
ROOT=Path('artifacts/reconstruct/certificate-adjudication-ae')
def prepare():
    ROOT.mkdir(exist_ok=True);assert not (ROOT/'manifest.json').exists()
    parent=json.loads(Path('artifacts/reconstruct/richer-exposure-aa/run.json').read_text());graph=json.loads(Path('artifacts/reconstruct/richer-exposure-aa/source137-alternative-certificate.json').read_text())
    certs={96:{'missing':'gprime(0)=1','alternative_family':'g(x)=a*x on[-1,1], for arbitrary real a. Each is differentiable and g(0)=0. All six public observations hold for all a.','derivation':'H(t)=a*t^3/3; F(x)=a*(x^8-x^12)/12; since sin(F)/F tends to1, the requested limit is a/12. a=0 gives0, a=1 gives1/12. Therefore the public premises alone do not determine the question answer; using the supplied1/12 infers missing derivative a=1.','scope':'These computations are private and absent from the student clues.'},137:{'missing':'Exact degree triple3,4,5','derivation':'Let consecutive degrees be d-1,d,d+1 in equal groups. Mean degree d equals2e/n=6-12/n. Original supplied n6 implies d4, hence degrees3,4,5. Public premises before using answer do not determine d: the alternative n12 graph below has d5 and four vertices of each degree4,5,6.','alternative_certificate':graph,'scope':'The graph certificate and inverse computation are private and absent from public clues.'}}
    cases=[]
    for i in [96,137]:
        key,bank=r.latest_bank(parent,i,'convert_p6_rich');source=parent['sources'][str(i)]
        audits=[a for a in parent['audits'].values() if a['bank_key']==key]
        assert next(a for a in audits if a['prompt']=='audit_support_p1')['output']['status']=='ACCEPT'
        assert next(a for a in audits if a['prompt']=='audit_source_disclosure_p4')['output']['status']=='ACCEPT'
        cases.append({'source_index':i,'source':source,'bank_key':key,'bank':bank,'certificate':certs[i],'source_hash':r.stable_hash(source),'bank_hash':r.stable_hash(bank['output'])})
    m={'protocol':'docs/plans/reconstruct-amendment-ae.md','cases':cases,'prompt_hash':r.stable_hash(r.load_prompt('adjudicate_disclosure_p1')),'budget_usd':.15}
    r.atomic_write_json(ROOT/'manifest.json',m);r.atomic_write_json(ROOT/'run.json',{'metadata':{'manifest_hash':r.stable_hash(m)},'banks':{},'audits':{},'failures':[],'attempted':[]});print('AE frozen:2 private certificates, unchanged public inputs')
def run():
    m=json.loads((ROOT/'manifest.json').read_text());state=json.loads((ROOT/'run.json').read_text());assert r.stable_hash(m)==state['metadata']['manifest_hash']
    template=r.load_prompt('adjudicate_disclosure_p1');assert r.stable_hash(template)==m['prompt_hash']
    jobs=[c for c in m['cases'] if c['source_index'] not in state['attempted']];state['attempted'] += [c['source_index'] for c in jobs];r.atomic_write_json(ROOT/'run.json',state)
    def worker(c):
        raw=None;i=c['source_index'];public={'clues':[{'id':v['id'],'sentence':v['sentence']} for v in c['bank']['output']['clues']]}
        text=r.render_template(template,{'SOURCE_QUESTION':c['source']['question'],'FINAL_ANSWER':c['source']['final_answer'],'PUBLIC_BANK':public,'CERTIFICATE':c['certificate']})
        try:
            raw=r.teacher_call(r.deepinfra_client(180),text,r.DEFAULT_TEACHER_MODEL,8192,'low');out=r.extract_json_object(raw['content'])
            validate_strict_disclosure(out,public_disclosure_text(c['source']['final_answer'],c['bank']['output'],'source_disclosure'),'source_disclosure')
            if out['status']=='ACCEPT':assert out.get('certificate_valid') is True
            assert isinstance(out.get('certificate_check'),str) and out['certificate_check'].strip()
            return str(i),{'source_index':i,'bank_key':c['bank_key'],'bank_output_hash':c['bank_hash'],'source_record_hash':c['source_hash'],'certificate_hash':r.stable_hash(c['certificate']),'rendered_input':text,'prompt':'adjudicate_disclosure_p1','prompt_hash':m['prompt_hash'],'model':r.DEFAULT_TEACHER_MODEL,'output':out,'request':{k:v for k,v in raw.items() if k!='content'},'raw_content':raw['content']},None
        except Exception as exc:return str(i),None,{'stage':'certificate_adjudication','source_index':i,'key':str(i),'raw':raw or getattr(exc,'raw_response',None),'error':str(exc)}
    with ThreadPoolExecutor(max_workers=2) as pool:
        for future in as_completed([pool.submit(worker,c) for c in jobs]):
            key,record,error=future.result()
            if record:state['audits'][key]=record
            else:state['failures'].append(error)
            r.atomic_write_json(ROOT/'run.json',state);print(key,record['output']['status'] if record else error['error'],flush=True)
    print('AE adjudication terminal; no student inputs approved automatically',flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--prepare-only',action='store_true');a=p.parse_args();prepare() if a.prepare_only else run()
