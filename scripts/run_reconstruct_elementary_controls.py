#!/usr/bin/env python3
"""Frozen elementary diagnostics, explicitly outside benchmark performance."""
import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from anlp_project import reconstruct as r
root=Path('artifacts/reconstruct/elementary-controls-ar');root.mkdir(exist_ok=True);target=root/'run.json'
if not target.exists():
 families=[
 ('distance','A train travels at a constant15 kilometres per hour for4 hours without stopping. How many kilometres does it travel?','60',
  ['A train travels at15 kilometres per hour.','Its speed remains constant throughout an unreported positive number of hours.','The requested quantity is the distance travelled in kilometres.'],
  ['A train initially travels at15 kilometres per hour.','The journey lasts4 hours.','Its speed remains unchanged throughout the journey.']),
 ('urn','An urn contains only6 red balls and4 blue balls. One ball is drawn uniformly at random. What is the probability it is red?','3/5',
  ['An urn contains4 blue balls and an unreported positive integer number of red balls, with no other colors.','One ball is drawn and every individual ball is equally likely.','The requested quantity is the probability of drawing a red ball.'],
  ['An urn contains6 red balls and4 blue balls.','There are no balls of other colors.','One ball is drawn, with every individual ball equally likely.']),
 ('discount','An item originally costs80 dollars. Its price is reduced once by25 percent. What is the reduced price in dollars?','60',
  ['An item has an unreported positive original price in dollars.','A single25 percent discount is applied to that original price.','The requested quantity is the reduced price in dollars.'],
  ['An item originally costs80 dollars.','Its price is reduced by25 percent.','The reduction is applied exactly once to the original price.'])]
 template=r.load_prompt('student_p13_infer_missing');jobs={}
 for family,q,answer,pm,tm in families:
  for condition,clues in [('solve',None),('missing_premise',pm),('missing_target',tm)]:
   evidence=None
   if clues is None:prompt='Solve the mathematical problem. Give a concise mathematical justification and the final answer. Return JSON only with keys "justification" and "final_answer".\n\nQUESTION:\n'+q
   else:
    evidence=r.public_evidence(answer,[{'id':f'c{i+1}','sentence':v} for i,v in enumerate(clues)],'sentence')
    prompt=r.render_template(template,{'FINAL_ANSWER':answer,'RENDERED_CLUES':evidence['rendered_clues']})
   jobs[family+':'+condition]={'source_question':q,'source_answer':answer,'condition':condition,'evidence':evidence,'prompt':prompt,'prompt_hash':r.stable_hash(prompt)}
 state={'metadata':{'protocol':'docs/plans/reconstruct-amendment-ar.md','diagnostic_only':True,'created_at':r.utc_now(),'jobs_hash':r.stable_hash(jobs)},'jobs':jobs,'attempted':[],'responses':{},'failures':[]};r.atomic_write_json(target,state)
state=json.loads(target.read_text());assert r.stable_hash(state['jobs'])==state['metadata']['jobs_hash'];client=r.local_client(r.DEFAULT_LOCAL_URL,300);config=r.SamplingConfig(.7,.8,20,8192,0)
for key,job in state['jobs'].items():
 if key in state['attempted']:continue
 state['attempted'].append(key);r.atomic_write_json(target,state);raw=None
 try:
  raw=r.student_call(client,job['prompt'],r.DEFAULT_MODEL,config)
  assert not r.has_generated_thinking(raw)
  if job['condition']=='solve':out=r.extract_json_object(raw['content']);assert 'final_answer' in out and isinstance(out.get('justification'),str)
  else:out,_=r.parse_student_response(raw['content'])
  state['responses'][key]={'output':out,'raw':raw,'prompt_hash':job['prompt_hash']};print(key,'completed',flush=True)
 except Exception as exc:state['failures'].append({'key':key,'error':repr(exc),'raw':raw});print(key,'FAILED',flush=True)
 r.atomic_write_json(target,state)
print('Nine elementary diagnostic slots terminal; not benchmark successes',flush=True)
