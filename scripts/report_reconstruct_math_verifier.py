#!/usr/bin/env python3
"""Report AD and export standard deduplicated usage records, without rescoring Qwen."""
import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from anlp_project import reconstruct as r
ROOT=Path('artifacts/reconstruct/math-verifier-ad')
m=json.loads((ROOT/'manifest.json').read_text());run=json.loads((ROOT/'run.json').read_text());assert r.stable_hash(m)==run['metadata']['manifest_hash']
rows=[];usage={'banks':{},'judge_fixtures':{},'failures':[],'metadata':{'purpose':'Accounting adapter for independent mathematical verification calls; these are not primary rubric scores.'}}
for case in m['cases']:
    rec=run['records'].get(case['id']);out=rec['output'] if rec else {}
    if rec:
        assert rec['case_hash']==r.stable_hash(case)
        raw=rec['raw'];usage['judge_fixtures'][case['id']]={'prompt':'verify_math_p1','model':r.DEFAULT_TEACHER_MODEL,'request':{k:v for k,v in raw.items() if k!='content'},'raw_content':raw['content']}
    rows.append({'id':case['id'],'population':case['population'],'expected':case['expected'],'observed':out.get('status'),'passed':out.get('status')==case['expected'],'reason':out.get('reason'),'checks':out.get('checks')})
for f in run['failures']:usage['failures'].append({'stage':'math_verification','key':f['id'],'raw':f['raw'],'error':f['error']})
r.atomic_write_json(ROOT/'accounting.json',usage)
result={'rows':rows,'planned':len(rows),'returned':len(run['records']),'failures':len(run['failures']),'passed':sum(x['passed'] for x in rows),'false_acceptances':[x['id'] for x in rows if x['expected']=='invalid' and x['observed']=='valid'],'false_rejections':[x['id'] for x in rows if x['expected']=='valid' and x['observed']=='invalid'],'decision':'advance_to_validation_only' if all(x['passed'] for x in rows) else 'do_not_adopt','recorded_cost_usd':r.actual_cost(usage),'limitation':'Twelve correlated assistant-authored/development controls; no independent human gold, no representative accuracy estimate, no change to student correctness.'}
r.atomic_write_json(ROOT/'comparison.json',result)
lines=['# AD: separate mathematical verifier','',result['decision'],'',f"Matched {result['passed']}/{result['planned']} development references; returned {result['returned']}; failures {result['failures']}.",'','| Case | Expected | Observed |','|---|---|---|']
lines += [f"| {x['id']} | {x['expected']} | {x['observed']} |" for x in rows]
lines += ['',result['limitation'],'','Raw scores and Qwen outputs in AA/AB/AC remain unchanged. Corrected proof controls are authored references, never successful Qwen generations.']
(ROOT/'comparison.md').write_text('\n'.join(lines)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='rows'},indent=2))
