#!/usr/bin/env python3
"""Score saved responses with versioned judges and fixed PC-v1 weights."""
import argparse,json,sys
from concurrent.futures import ThreadPoolExecutor,as_completed
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from anlp_project import reconstruct as r
from anlp_project.reconstruct_judge_validation import validate_judgment, validation_notes
ROOT=Path('artifacts/reconstruct/partial-credit-v4')
PROMPTS=Path('data/prompts/reconstruct/partial_credit_v4')
ROLES={'fidelity':'judge_fidelity.md','validity':'judge_validity.md'}
ARMS={'zero':'bridge-low-az','one':'bridge-midpoint-ay','two':'bridge-composition-ax'}

def validate(out,role,nclues):
 if out.get('status') not in ['scored','needs_review']:raise ValueError('Invalid status')
 fields=['premise_fidelity','target_fidelity'] if role=='fidelity' else ['evidence_integration','mathematical_validity']
 for f in fields:
  score=out.get(f,{}).get('score','missing')
  if score is not None and (type(score) is not int or not 0<=score<=4):raise ValueError('Invalid dimension '+f)
  if out['status']=='scored' and score is None:raise ValueError('Scored response has unresolved dimension')
 if role=='fidelity':
  if type(out.get('semantic_equivalent')) not in [bool,type(None)]:raise ValueError('Missing equivalence status')
  if out.get('semantic_equivalent') is True and any(out[f]['score']!=4 for f in fields):raise ValueError('Equivalence contradicts P/T')
 else:
  checks=out['evidence_integration'].get('clue_checks',[])
  if sorted(c.get('index',0) for c in checks)!=list(range(1,nclues+1)):raise ValueError('Incomplete clue coverage')
  if any(c.get('verdict') not in ['grounded','partial','unsupported','contradicted','uncertain'] for c in checks):raise ValueError('Invalid clue verdict')
  if type(out.get('shortcut',{}).get('present','missing')) not in [bool,type(None)]:raise ValueError('Missing shortcut assessment')
  m=out['mathematical_validity']
  for f in ['question_well_posed','supplied_answer_correct','verification_sound']:
   if type(m.get(f,'missing')) not in [bool,type(None)]:raise ValueError('Missing mathematical flag')
  if m['score'] in [3,4] and any(m[f] is not True for f in ['question_well_posed','supplied_answer_correct','verification_sound']):raise ValueError('High mathematical score contradicts flags')
 return out

def prepare():
 assert not (ROOT/'manifest.json').exists()
 prompts={role:(PROMPTS/name).read_text() for role,name in ROLES.items()};cases=[]
 for arm,directory in ARMS.items():
  path=Path('artifacts/reconstruct')/directory/'student.json';run=json.loads(path.read_text())
  assert len(run['responses'])==6
  for key,v in run['responses'].items():
   ev=v['public_evidence'];source=run['sources'][str(v['source_index'])]
   args=dict(SOURCE_QUESTION=source['question'],CANDIDATE_QUESTION=v['output']['question'],FINAL_ANSWER=ev['final_answer'],RENDERED_CLUES=ev['rendered_clues'],STUDENT_RESPONSE=v['output'])
   for role,prompt in prompts.items():cases.append(dict(id=arm+':'+str(v['source_index'])+':'+role,arm=arm,source_index=v['source_index'],role=role,source_file=str(path),response_key=key,response_hash=r.stable_hash(v['output']),evidence_hash=v['evidence_hash'],clue_count=ev['clue_count'],rendered_prompt=r.render_template(prompt,args)))
 manifest=dict(judge_version=PROMPTS.name,prompt_directory=str(PROMPTS),strict_certificates=PROMPTS.name in ['partial_credit_v2','partial_credit_v3','partial_credit_v4'],validator_hash=r.stable_hash(Path('src/anlp_project/reconstruct_judge_validation.py').read_text()),protocol='docs/plans/reconstruct-amendment-ba.md' if PROMPTS.name=='partial_credit_v1' else 'docs/design/reconstruct/JUDGE_VERIFICATION.md',cases=cases,prompts=prompts,prompt_hashes={k:r.stable_hash(v) for k,v in prompts.items()},weights=[.25]*4,rating_boundaries=[20,40,60,80],budget_usd=.30)
 r.atomic_write_json(ROOT/'manifest.json',manifest);r.atomic_write_json(ROOT/'run.json',dict(metadata=dict(manifest_hash=r.stable_hash(manifest)),records={},failures=[],attempted=[]));print('Frozen36 judging calls for18 saved responses.')

def main():
 manifest=json.loads((ROOT/'manifest.json').read_text());state=json.loads((ROOT/'run.json').read_text());assert state['metadata']['manifest_hash']==r.stable_hash(manifest)
 if manifest.get('strict_certificates'):assert manifest['validator_hash']==r.stable_hash(Path('src/anlp_project/reconstruct_judge_validation.py').read_text())
 for role,name in ROLES.items():assert r.stable_hash((PROMPTS/name).read_text())==manifest['prompt_hashes'][role]
 jobs=[c for c in manifest['cases'] if c['id'] not in state['attempted']];state['attempted'] += [c['id'] for c in jobs];r.atomic_write_json(ROOT/'run.json',state)
 def worker(c):
  raw=None;out=None;response={}
  try:
   raw=r.teacher_call(r.deepinfra_client(180),c['rendered_prompt'],r.DEFAULT_TEACHER_MODEL,8192,'low');out=r.extract_json_object(raw['content'])
   if manifest.get('strict_certificates'):
    source=json.loads(Path(c['source_file']).read_text());response=source['responses'][c['response_key']]['output']
    assert r.stable_hash(response)==c['response_hash']
    out=validate_judgment(out,c['role'],question=response['question'],response=response,clue_count=c['clue_count'])
   else:out=validate(out,c['role'],c['clue_count'])
   return c['id'],dict(output=out,validation_notes=validation_notes(out,response),raw=raw,rendered_prompt=c['rendered_prompt'],case_hash=r.stable_hash(c)),None
  except Exception as exc:return c['id'],None,dict(id=c['id'],error=str(exc),output=out,raw=raw or getattr(exc,'raw_response',None),case_hash=r.stable_hash(c))
 with ThreadPoolExecutor(max_workers=3) as pool:
  for future in as_completed([pool.submit(worker,c) for c in jobs]):
   key,record,error=future.result()
   if record:state['records'][key]=record
   else:state['failures'].append(error)
   r.atomic_write_json(ROOT/'run.json',state);print(key,record['output'] if record else 'FAILED '+error['error'],flush=True)
 print('Partial-credit scoring terminal; independent review remains required.')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--prepare-only',action='store_true');p.add_argument('--root',type=Path,default=ROOT);p.add_argument('--judge-prompts',type=Path,default=PROMPTS);a=p.parse_args();ROOT=a.root;PROMPTS=a.judge_prompts;ROOT.mkdir(parents=True,exist_ok=True);prepare() if a.prepare_only else main()
