#!/usr/bin/env python3
"""One preregistered logical adjudication; never overwrites the original verifier."""
import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from anlp_project import reconstruct as r
root=Path('artifacts/reconstruct/bridge-composition-ax');manifest=root/'alpha-adjudication-manifest.json';target=root/'alpha-adjudication.json'
assert not manifest.exists() and not target.exists()
claims=[{'id':'forward_inverse','statement':'If L(alpha)=1/e, then alpha=1.','expected':True},{'id':'false_zero_inverse','statement':'If L(alpha)=0, then alpha=1.','expected':False},{'id':'forward_special_case','statement':'If alpha=1, then L(alpha)=1/e.','expected':True},{'id':'false_target','statement':'If L(alpha)=1/e, then alpha=2.','expected':False}]
text='For a fixed real alpha>0, define L(alpha)=lim as n tends to infinity of (n!)^(1/(alpha*n))/n, allowing an infinite limit. Assess each implication independently. Return JSON with checks, each containing id, valid (Boolean), and a mathematical proof or counterexample. Derive the limiting behavior from logarithms or Stirling. Do not confuse determining alpha from a specified limit with a forward problem where alpha is unspecified. Claims: '+json.dumps([{k:v for k,v in c.items() if k!='expected'} for c in claims])
r.atomic_write_json(manifest,{'purpose':'Resolve a verifier rationale that simultaneously says the specified limit only occurs at alpha1 and denies that the specified limit implies alpha1. Frozen before this once-only call.','cases':claims,'rendered_prompt':text,'analytic_reference':'log ratio=(1/alpha-1)log n-1/alpha+o(1). For alpha<1 ratio diverges; alpha1 gives1/e; alpha>1 ratio tends0. Thus the first and third implications are true; alpha2 andalpha1 give counterexamples for second/fourth.','budget_usd':.01})
raw=None
try:
 raw=r.teacher_call(r.deepinfra_client(180),text,r.DEFAULT_TEACHER_MODEL,8192,'low');out=r.extract_json_object(raw['content']);checks=out['checks'];assert {c['id'] for c in checks}=={c['id'] for c in claims};assert all(type(c['valid']) is bool for c in checks)
 state={'records':{'alpha_logic':{'output':out,'raw':raw,'rendered_prompt':text}},'failures':[]}
except Exception as exc:state={'records':{},'failures':[{'id':'alpha_logic','error':str(exc),'raw':raw or getattr(exc,'raw_response',None)}]}
r.atomic_write_json(target,state);print(json.dumps(state.get('records',{}).get('alpha_logic',{}).get('output',state['failures']),indent=2),flush=True)
