#!/usr/bin/env python3
"""Frozen100-source partial-credit pipeline; resumes only unattempted calls."""
import argparse,copy,csv,json,random,statistics,sys,threading
from concurrent.futures import ThreadPoolExecutor,as_completed
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from anlp_project import reconstruct as r
from anlp_project.reconstruct_sources import normalize_option_answer
from anlp_project.reconstruct_judge_validation import validate_judgment,validation_notes
from anlp_project.reconstruct_partial_credit import aggregate
ROOT=Path('artifacts/reconstruct/final-100-v1')
PROMPTS=Path('data/prompts/reconstruct/final_v1')
ROLES=['convert','audit','copy','student','judge_fidelity','judge_validity']
LOCK=threading.RLock()
LEAKS=['direct_question_copy','premise_target_bundle_exposed','complete_solution_exposed']

def validate_bank(out):
 if out.get('status')=='NOT_SUITABLE':
  assert isinstance(out.get('reason'),str) and out['reason'].strip();return out
 assert out.get('status')=='OK' and len(out.get('clues',[]))==6,'Expected six-clue bank'
 ids=[]
 for c in out['clues']:
  assert all(isinstance(c.get(k),str) and c[k].strip() for k in ['id','sentence','hidden_support']),'Incomplete clue'
  ids.append(c['id'])
 assert len(set(ids))==6 and len({c['sentence'] for c in out['clues']})==6,'Duplicate clues'
 assert all(isinstance(out.get(k),str) and out[k].strip() for k in ['withheld','private_certificate'])
 return out

def validate_audit(out,evidence):
 assert out.get('status') in ['ACCEPT','REJECT','NEEDS_REVIEW']
 checks=out.get('checks',[])
 assert sorted(c.get('id','') for c in checks)==sorted(c['id'] for c in evidence['clues']),'Incomplete audit coverage'
 flags=[out.get('source_answer_correct','missing'),out.get('distinct_observations','missing')]
 flags += [c.get(f,'missing') for c in checks for f in ['supported','understandable']]
 leaks=[out.get(f,'missing') for f in LEAKS]
 assert all(type(v) in [bool,type(None)] for v in flags+leaks),'Invalid audit flags'
 public=evidence['final_answer']+'\n'+evidence['rendered_clues']
 quotes=out.get('public_quotes',[])
 assert quotes and all(isinstance(q,str) and q.strip() and q in public for q in quotes),'Nonpublic audit quote'
 assert all(isinstance(out.get(f),str) and out[f].strip() for f in ['reason','missing_essential_element','inference_required'])
 if out['status']=='ACCEPT':assert all(v is True for v in flags) and all(v is False for v in leaks),'Contradictory audit acceptance'
 if out['status']=='REJECT':assert any(v is False for v in flags) or any(v is True for v in leaks),'Rejection without explicit defect'
 return out

def validate_copy(out,evidence):
 assert out.get('status') in ['direct_candidate','no_direct_reconstruction','needs_review']
 assert isinstance(out.get('reason'),str) and out['reason'].strip()
 if out['status']=='direct_candidate':
  q=out.get('question');assert isinstance(q,str) and q.strip()
  matches=out.get('alignments',[]);assert matches,'Missing copy evidence'
  public=evidence['final_answer']+'\n'+evidence['rendered_clues']
  for a in matches:
   assert isinstance(a.get('question_span'),str) and a['question_span'] and a['question_span'] in q
   assert isinstance(a.get('public_quote'),str) and a['public_quote'] and a['public_quote'] in public
   assert a.get('operation') in ['copy','paraphrase','rename','reorder','grammatical_assembly']
 else:assert out.get('question') is None
 return out

def prepare():
 assert not (ROOT/'manifest.json').exists(),'Already frozen'
 sources=r.load_sources(r.DEFAULT_MANIFEST,r.DEFAULT_SOURCE,r.DEFAULT_SOLUTIONS)
 random.Random(20260921).shuffle(sources);sources=[normalize_option_answer(s) for s in sources[:100]]
 assert len(sources)==100 and len({s['source_index'] for s in sources})==100
 prompts={k:(PROMPTS/f'{k}.md').read_text() for k in ROLES}
 manifest=dict(version='RECONSTRUCT-FINAL-PC-v1',protocol='docs/plans/reconstruct-final-100-v1.md',sources=sources,prompts=prompts,source_selection_seed=20260921,public_clue_count=4,bank_clue_count=6,teacher=r.DEFAULT_TEACHER_MODEL,student=r.DEFAULT_MODEL,student_checkpoint_sha256='7485fe6f11af29433bc51cab58009521f205840f5b4ae3a32fa7f92e8534fdf5',sampling=dict(temperature=.7,top_p=.8,top_k=20,max_tokens=8192,seed=0),max_teacher_workers=3,cost_ceiling_usd=2.8,prior_recorded_cost_usd=1.9664399272,validator_hash=r.stable_hash(Path('src/anlp_project/reconstruct_judge_validation.py').read_text()),weights=[.25]*4,rating_boundaries=[20,40,60,80])
 state=dict(metadata={'manifest_hash':r.stable_hash(manifest),'created_at':r.utc_now()},records={},failures=[],attempted=[],items={str(s['source_index']):{'status':'allocated'} for s in sources})
 r.atomic_write_json(ROOT/'manifest.json',manifest);r.atomic_write_json(ROOT/'run.json',state)
 export(manifest,state);print('Frozen100 sources, four public clues, one Qwen draw per accepted input.',flush=True)

def export(manifest,state):
 rows=[];public=[];eligible=[]
 for source in manifest['sources']:
  i=source['source_index'];item=state['items'][str(i)];ev=item.get('evidence');records=state['records']
  f=records.get(f'judge_fidelity:{i}',{}).get('output');v=records.get(f'judge_validity:{i}',{}).get('output')
  student=records.get(f'student:{i}',{}).get('output')
  score=aggregate(f,v)
  valid=item.get('input_status')=='accepted'
  provisional=bool(valid and f and v and f.get('semantic_equivalent') is True and score['score_100'] is not None and score['shortcut'] is False and score['dimensions']['premise_fidelity']==4 and score['dimensions']['target_fidelity']==4 and score['dimensions']['evidence_integration']==4 and score['dimensions']['mathematical_validity'] in [3,4])
  row=dict(source_index=i,source_question=source['question'],source_final_answer=source['final_answer'],source_reference_solution=source['checked_solution'],status=item['status'],input_status=item.get('input_status','pending'),clues=[c['sentence'] for c in ev['clues']] if ev else [],qwen=student,score=score if valid else None,provisional_grounded_recovery=provisional,review_status='pending' if provisional else 'not_applicable')
  rows.append(row)
  if valid:
   eligible.append(row)
   public.append(dict(id=f'reconstruct-{i}',final_answer=ev['final_answer'],observations=[c['sentence'] for c in ev['clues']]))
 scores=[x['score']['score_100'] for x in eligible if x['score']['score_100'] is not None]
 histogram={str(j):sum(x['score']['rating_1_to_5']==j for x in eligible) for j in range(1,6)}
 summary=dict(version=manifest['version'],allocated=100,terminal_sources=sum(x['status'] in ['done','input_rejected','input_unresolved','not_suitable','conversion_failed','student_failed'] for x in rows),accepted_inputs=len(eligible),qwen_responses=sum(x['qwen'] is not None for x in rows),scored=len(scores),mean=statistics.mean(scores) if scores else None,sample_variance=statistics.variance(scores) if len(scores)>1 else None,histogram_1_to_5=histogram,provisional_grounded_recoveries=sum(x['provisional_grounded_recovery'] for x in rows),failures=len(state['failures']),missing_scores_on_accepted=len(eligible)-len(scores),limitations=['Reused development sources, not untouched test data.','100 allocated sources; accepted task count reported separately.','Provisional automatic recoveries require case review.','No judge scores or source exclusions adjusted for histogram shape.'])
 r.atomic_write_json(ROOT/'summary.json',summary)
 for name,values in [('questions-answers.jsonl',rows),('public-tasks.jsonl',public)]:
  (ROOT/name).write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in values))
 with (ROOT/'questions-answers.csv').open('w',newline='') as handle:
  writer=csv.writer(handle);writer.writerow(['source_index','source_question','source_answer','input_status','clues','qwen_question','qwen_justification','score_100','rating_1_to_5','provisional_grounded_recovery'])
  for x in rows:writer.writerow([x['source_index'],x['source_question'],x['source_final_answer'],x['input_status'],'\n'.join(x['clues']),(x['qwen'] or {}).get('question'),(x['qwen'] or {}).get('justification'),(x['score'] or {}).get('score_100'),(x['score'] or {}).get('rating_1_to_5'),x['provisional_grounded_recovery']])
 lines=['#100-source RECONSTRUCT questions and answers','','Private research/answer-key export. Public student inputs are in public-tasks.jsonl.','']
 for x in rows:
  lines += [f"## Source {x['source_index']} — {x['input_status']}",'', '**Original question:** '+x['source_question'],'','**Answer:** '+x['source_final_answer'],'','**Public clues:**']+[f"{n}. {c}" for n,c in enumerate(x['clues'],1)]
  if x['qwen']:lines += ['', '**Qwen reconstructed question:** '+x['qwen']['question'],'','**Qwen verification:** '+x['qwen']['justification'],'',f"**Score:** {(x['score'] or {}).get('score_100')} /100"]
  lines += ['']
 (ROOT/'questions-answers.md').write_text('\n'.join(lines)+'\n')
 return summary

class Run:
 def __init__(self):
  self.manifest=json.loads((ROOT/'manifest.json').read_text());self.state=json.loads((ROOT/'run.json').read_text());self.reserved=0
  assert self.state['metadata']['manifest_hash']==r.stable_hash(self.manifest)
  assert self.manifest['validator_hash']==r.stable_hash(Path('src/anlp_project/reconstruct_judge_validation.py').read_text())
  for role,text in self.manifest['prompts'].items():assert text==(PROMPTS/f'{role}.md').read_text()
 def save(self):r.atomic_write_json(ROOT/'run.json',self.state)
 def mark(self,i,**changes):
  with LOCK:self.state['items'][str(i)].update(changes);self.save()
 def cost(self):
  return sum(((x.get('raw') or {}).get('usage',{}).get('estimated_cost') if (x.get('raw') or {}).get('usage',{}).get('estimated_cost') is not None else x.get('reserved_cost_usd',0)) for x in list(self.state['records'].values())+self.state['failures'] if x.get('stage')!='student')
 def call(self,stage,source,args,validator,student=False):
  key=f'{stage}:{source["source_index"]}';prompt=r.render_template(self.manifest['prompts'][stage],args)
  cap=16384 if stage=='convert' else 8192
  reserve=0 if student else (len(prompt)*.20+cap*.60)/1e6
  with LOCK:
   if key in self.state['records']:return self.state['records'][key]['output']
   if key in self.state['attempted']:return None
   if self.cost()+self.reserved+reserve>self.manifest['cost_ceiling_usd']:
    raise RuntimeError('Run cost ceiling cannot reserve next call')
   self.reserved+=reserve;self.state['attempted'].append(key);self.save()
  raw=None;out=None
  try:
   if student:
    raw=r.student_call(r.local_client(timeout=600),prompt,self.manifest['student'],r.SamplingConfig(**self.manifest['sampling']))
    if r.has_generated_thinking(raw):raise ValueError('Unexpected thinking output')
   else:raw=r.teacher_call(r.deepinfra_client(180),prompt,self.manifest['teacher'],cap,'low')
   out=r.extract_json_object(raw['content']);validator(out)
   record=dict(reserved_cost_usd=reserve,stage=stage,source_index=source['source_index'],output=out,raw=raw,prompt=prompt,prompt_hash=r.stable_hash(prompt),input_hash=r.stable_hash(args),model=self.manifest['student'] if student else self.manifest['teacher'],validation_notes=validation_notes(out,args.get('STUDENT_RESPONSE',{})))
   with LOCK:self.state['records'][key]=record
   print(key,'completed',flush=True)
   return out
  except Exception as exc:
   with LOCK:self.state['failures'].append(dict(id=key,reserved_cost_usd=reserve,stage=stage,source_index=source['source_index'],error=str(exc),output=out,raw=raw or getattr(exc,'raw_response',None),prompt=prompt,input_hash=r.stable_hash(args)))
   print(key,'FAILED',str(exc),flush=True);return None
  finally:
   with LOCK:self.reserved-=reserve;self.save()
 def input(self,source):
  i=source['source_index'];args=dict(SOURCE_QUESTION=source['question'],FINAL_ANSWER=source['final_answer'],CHECKED_SOLUTION=source['checked_solution'])
  bank=self.call('convert',source,args,validate_bank)
  if bank is None:self.mark(i,status='conversion_failed');return False
  if bank['status']=='NOT_SUITABLE':self.mark(i,status='not_suitable',input_status='not_suitable');return False
  clues=[dict(id=c['id'],sentence=c['sentence']) for c in bank['clues'][:4]]
  ev=dict(final_answer=source['final_answer'],clues=clues,rendered_clues='\n'.join(f'{n}. {c["sentence"]}' for n,c in enumerate(clues,1)))
  self.mark(i,evidence=ev,evidence_hash=r.stable_hash(ev),status='auditing')
  audit=self.call('audit',source,{**args,'RENDERED_CLUES':ev['rendered_clues']},lambda out:validate_audit(out,ev))
  # Copy challenge is run even for audit rejections, retaining independent gate evidence.
  copying=self.call('copy',source,dict(FINAL_ANSWER=ev['final_answer'],PUBLIC_BANK=ev['rendered_clues']),lambda out:validate_copy(out,ev))
  rejected=(audit and audit['status']=='REJECT') or (copying and copying['status']=='direct_candidate')
  accepted=audit and audit['status']=='ACCEPT' and copying and copying['status']=='no_direct_reconstruction'
  status='accepted' if accepted else 'rejected' if rejected else 'unresolved'
  self.mark(i,input_status=status,status='ready_for_student' if accepted else 'input_'+status)
  return bool(accepted)
 def student(self,source):
  i=source['source_index'];ev=self.state['items'][str(i)]['evidence'];self.mark(i,status='student_running')
  out=self.call('student',source,dict(FINAL_ANSWER=ev['final_answer'],RENDERED_CLUES=ev['rendered_clues']),r.validate_student,student=True)
  self.mark(i,status='judging' if out else 'student_failed');return out
 def judge(self,source,role):
  i=source['source_index'];ev=self.state['items'][str(i)]['evidence'];response=self.state['records'][f'student:{i}']['output']
  args=dict(SOURCE_QUESTION=source['question'],CANDIDATE_QUESTION=response['question']) if role=='fidelity' else dict(FINAL_ANSWER=ev['final_answer'],RENDERED_CLUES=ev['rendered_clues'],STUDENT_RESPONSE=response)
  return self.call('judge_'+role,source,args,lambda out:validate_judgment(out,role,question=response['question'],response=response,clue_count=4))
 def run(self):
  import urllib.request
  with urllib.request.urlopen('http://127.0.0.1:8080/health',timeout=5) as response:assert json.load(response)['status']=='ok'
  local_futures=[];judge_futures=[]
  with ThreadPoolExecutor(max_workers=3) as teacher_pool,ThreadPoolExecutor(max_workers=1) as local_pool:
   def local_work(source):
    if self.student(source):
     with LOCK:
      for role in ['fidelity','validity']:judge_futures.append(teacher_pool.submit(self.judge,source,role))
   futures={teacher_pool.submit(self.input,s):s for s in self.manifest['sources']}
   for future in as_completed(futures):
    source=futures[future]
    try:
     if future.result():local_futures.append(local_pool.submit(local_work,source))
    except Exception as exc:self.mark(source['source_index'],status='input_unresolved',input_status='unresolved',orchestration_error=str(exc))
    with LOCK:export(self.manifest,self.state)
   for f in as_completed(local_futures):f.result()
   for f in as_completed(judge_futures):f.result()
  for source in self.manifest['sources']:
   i=source['source_index']
   if f'student:{i}' in self.state['records']:self.mark(i,status='done')
  with LOCK:
   self.state['metadata'].update(terminal=True,finished_at=r.utc_now(),recorded_cost_usd=self.cost());self.save();summary=export(self.manifest,self.state)
  print(json.dumps(summary,indent=2),flush=True)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','run','report']);a=p.parse_args();ROOT.mkdir(exist_ok=True)
 if a.action=='prepare':prepare()
 elif a.action=='run':Run().run()
 else:
  obj=Run();print(json.dumps(export(obj.manifest,obj.state),indent=2))
