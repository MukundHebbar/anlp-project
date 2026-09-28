#!/usr/bin/env python3
"""Independent mathematics veto for terminal student responses; no prior scores sent."""
import argparse,importlib.util,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from anlp_project import reconstruct as r
spec=importlib.util.spec_from_file_location('math_gate',Path(__file__).with_name('run_reconstruct_math_verifier.py'));module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
p=argparse.ArgumentParser();p.add_argument('--study-root',type=Path,required=True);args=p.parse_args();root=args.study_root
student=json.loads((root/'student.json').read_text());assert set(student['metadata']['jobs'])==set(student['metadata']['attempted_jobs'])
terminal=set(student['responses']) | {f['key'] for f in student['failures'] if f['stage']=='student'}
assert set(student['metadata']['jobs'])<=terminal, 'Student requests still in flight; attempted does not mean terminal'
target=root/'math-verification.json';state=json.loads(target.read_text()) if target.exists() else {'banks':{},'audits':{},'failures':[],'attempted':[],'metadata':{'purpose':'Independent mathematical veto; not a replacement rubric or source-equivalence judge'}}
template=r.load_prompt('verify_math_p1')
for key,response in student['responses'].items():
    jobid=key+':'+r.stable_hash(response['output'])+':'+r.stable_hash(template)
    if jobid in state['attempted']:continue
    state['attempted'].append(jobid);r.atomic_write_json(target,state)
    text=r.render_template(template,{'FINAL_ANSWER':response['public_evidence']['final_answer'],'RENDERED_CLUES':response['public_evidence']['rendered_clues'],'STUDENT_RESPONSE':response['output']});raw=None
    try:
        r.reserve_teacher_request(state,text,8192,.15)
        raw=r.teacher_call(r.deepinfra_client(180),text,r.DEFAULT_TEACHER_MODEL,8192,'low');out=module.validate(r.extract_json_object(raw['content']),response['output'])
        state['audits'][jobid]={'source_index':response['source_index'],'response_key':key,'response_output_hash':r.stable_hash(response['output']),'evidence_hash':response['evidence_hash'],'prompt':'verify_math_p1','prompt_hash':r.stable_hash(template),'rendered_prompt':text,'output':out,'model':r.DEFAULT_TEACHER_MODEL,'request':{k:v for k,v in raw.items() if k!='content'},'raw_content':raw['content']};print(key,out['status'],flush=True)
    except Exception as exc:r.failure(state,'math_verification',response['source_index'],jobid,exc,raw);print(key,'FAILED',str(exc),flush=True)
    r.atomic_write_json(target,state)
