#!/usr/bin/env python3
"""Extend the frozen47 scored development rows to100 complete gate-passed rows."""
import argparse
import copy
import csv
import hashlib
import importlib.util
import json
import random
import re
import threading
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

spec=importlib.util.spec_from_file_location('frozen100',Path(__file__).with_name('run_reconstruct_final100.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
from anlp_project.reconstruct_partial_credit import aggregate, balanced_rating_v4, BALANCED_V4_BOUNDARIES
from anlp_project.build_eval_manifest import broad_topic, difficulty_band

PARENT=Path('artifacts/reconstruct/final-100-v1')
ROOT=Path('artifacts/reconstruct/valid-100-v1')
m.ROOT=ROOT
TEACHER=threading.Semaphore(3)
LOCAL=threading.Semaphore(1)

def normalize_question(s):
    return re.sub(r'\s+','',s).casefold()

def fetch(url):
    with urllib.request.urlopen(url,timeout=55) as response:
        raw=response.read()
    return json.loads(raw),hashlib.sha256(raw).hexdigest()

def prepare():
    ROOT.mkdir(parents=True,exist_ok=True)
    assert not (ROOT/'manifest.json').exists(),'Already frozen'
    parent=json.loads((PARENT/'manifest.json').read_text())
    original=[json.loads(x) for x in (PARENT/'questions-answers.jsonl').read_text().splitlines()]
    baseline=[r for r in original if r['input_status']=='accepted' and r['qwen'] and r['score']['score_100'] is not None]
    assert len(baseline)==47
    (ROOT/'calibration-47.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in baseline))
    prior=json.loads(m.r.DEFAULT_SOURCE.read_text())['problems']
    excluded={normalize_question(s['question']) for s in prior}
    rng=random.Random(20260922)
    blocks=rng.sample(range(103022//100),12)
    urls=[f'https://datasets-server.huggingface.co/rows?dataset=zwhe99%2FDeepMath-103K&config=default&split=train&offset={b*100}&length=100' for b in blocks]
    meta,meta_hash=fetch('https://huggingface.co/api/datasets/zwhe99/DeepMath-103K')
    with ThreadPoolExecutor(max_workers=3) as pool:downloads=list(pool.map(fetch,urls))
    candidates=[];seen=set(excluded);discarded=Counter()
    for (data,digest),url in zip(downloads,urls):
        assert data['num_rows_total']==103022
        for entry in data['rows']:
            row=entry['row'];q=row.get('question','');key=normalize_question(q)
            if not q or key in seen:discarded['duplicate_or_empty']+=1;continue
            topic=broad_topic(row.get('topic',''))
            if topic is None or difficulty_band(row['difficulty']) is None:discarded['topic_or_difficulty']+=1;continue
            if not row.get('final_answer') or not row.get('r1_solution_1'):discarded['missing_reference']+=1;continue
            if entry.get('truncated_cells'):discarded['truncated_cells']+=1;continue
            i=entry['row_idx']
            s=dict(source_index=1000000+i,source_id=f'deepmath-row-{i}',dataset_row_index=i,question=q,final_answer=str(row['final_answer']),topic=row['topic'],broad_topic=m.r.broad_topic(row['topic']),difficulty=row['difficulty'],checked_solution=row['r1_solution_1'],solution_origin='dataset_r1_solution_1_unverified_until_input_audit',download_url=url,download_sha256=digest)
            try:s=m.normalize_option_answer(s)
            except ValueError:discarded['ambiguous_option_answer']+=1;continue
            seen.add(key);candidates.append(s)
    groups={t:[s for s in candidates if s['broad_topic']==t] for t in m.r.TOPIC_BUCKETS}
    for values in groups.values():rng.shuffle(values)
    ordered=[]
    while any(groups.values()):
        for t in m.r.TOPIC_BUCKETS:
            if groups[t]:ordered.append(groups[t].pop())
    assert len(ordered)>=150, f'Insufficient candidate pool: {len(ordered)}'
    manifest=copy.deepcopy(parent)
    manifest.update(version='RECONSTRUCT-VALID100-EXTENSION-v1',protocol='docs/plans/reconstruct-valid-100-extension.md',sources=ordered,source_selection_seed=20260922,cost_ceiling_usd=2.4,prior_recorded_cost_usd=2.4866524088,rating_boundaries=list(BALANCED_V4_BOUNDARIES),rating_version='RECONSTRUCT-RATING-v4',target_total=100,target_added=53,batch_size=6,parent_manifest_hash=m.r.stable_hash(parent),calibration_file_sha256=hashlib.sha256((ROOT/'calibration-47.jsonl').read_bytes()).hexdigest(),dataset_acquisition=dict(dataset='zwhe99/DeepMath-103K',metadata_sha=meta.get('sha'),metadata_response_sha256=meta_hash,acquired_at=m.r.utc_now(),blocks=blocks,responses=[dict(url=u,sha256=d[1]) for u,d in zip(urls,downloads)],discarded=dict(discarded),excluded_pilot_sources=len(prior)),runner_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    state=dict(metadata=dict(manifest_hash=m.r.stable_hash(manifest),created_at=m.r.utc_now(),completed_batches=0),records={},failures=[],attempted=[],items={str(s['source_index']):{'status':'allocated'} for s in ordered})
    m.r.atomic_write_json(ROOT/'manifest.json',manifest);m.r.atomic_write_json(ROOT/'run.json',state)
    (ROOT/'runner-frozen.py').write_bytes(Path(__file__).read_bytes())
    print('Frozen candidates:',len(ordered),'topics:',dict(Counter(s['broad_topic'] for s in ordered)),flush=True)

def complete(state,i):
    if state['items'][str(i)].get('input_status')!='accepted':return False
    records=state['records']
    if f'student:{i}' not in records:return False
    f=records.get(f'judge_fidelity:{i}',{}).get('output',{})
    v=records.get(f'judge_validity:{i}',{}).get('output',{})
    score=aggregate(f,v)
    return f.get('status')==v.get('status')=='scored' and all(x is not None for x in score['dimensions'].values()) and score['score_100'] is not None

class Run(m.Run):
    def call(self,stage,source,args,validator,student=False):
        with LOCAL if student else TEACHER:
            return super().call(stage,source,args,validator,student)

    def workflow(self,source):
        i=source['source_index']
        try:
            if self.input(source) and self.student(source):
                for role in ['fidelity','validity']:self.judge(source,role)
                self.mark(i,status='complete_valid' if complete(self.state,i) else 'judgment_unresolved')
        except Exception as exc:
            self.mark(i,status='orchestration_failed',orchestration_error=str(exc))

    def run(self):
        with urllib.request.urlopen('http://127.0.0.1:8080/health',timeout=5) as f:assert json.load(f)['status']=='ok'
        if self.state['metadata'].get('terminal'):
            return report(self.manifest,self.state)
        sources=self.manifest['sources'];start=self.state['metadata']['completed_batches']*6
        for pos in range(start,len(sources),6):
            with ThreadPoolExecutor(max_workers=6) as pool:list(pool.map(self.workflow,sources[pos:pos+6]))
            self.state['metadata'].update(completed_batches=pos//6+1,recorded_cost_usd=self.cost());self.save()
            total=sum(complete(self.state,s['source_index']) for s in sources)
            print(f'BATCH {pos//6+1}: sources processed={min(pos+6,len(sources))}; complete added={total}/53; cost=${self.cost():.5f}',flush=True)
            report(self.manifest,self.state)
            budget_failed=any('cost ceiling' in x.get('orchestration_error','') for x in self.state['items'].values())
            if total>=53 or budget_failed:break
        self.state['metadata'].update(terminal=True,finished_at=m.r.utc_now(),recorded_cost_usd=self.cost());self.save()
        return report(self.manifest,self.state)

def report(manifest,state):
    baseline=[json.loads(x) for x in (ROOT/'calibration-47.jsonl').read_text().splitlines()]
    for row in baseline:row.update(cohort='calibration',rating_v4=balanced_rating_v4(row['score']['score_100']))
    attempts=[];eligible=[]
    records=state['records']
    for source in manifest['sources']:
        i=source['source_index'];item=state['items'][str(i)]
        if item['status']=='allocated':continue
        ev=item.get('evidence',{})
        f=records.get(f'judge_fidelity:{i}',{}).get('output',{});v=records.get(f'judge_validity:{i}',{}).get('output',{})
        score=aggregate(f,v)
        ok=complete(state,i)
        row=dict(cohort='extension',source_index=i,source_question=source['question'],source_final_answer=source['final_answer'],source_reference_solution=source['checked_solution'],status=item['status'],input_status=item.get('input_status'),clues=[x['sentence'] for x in ev.get('clues',[])],qwen=records.get(f'student:{i}',{}).get('output'),score=score if item.get('input_status')=='accepted' else None,rating_v4=balanced_rating_v4(score['score_100']) if ok else None,complete_valid=ok,semantic_equivalent=f.get('semantic_equivalent'),provisional_grounded_recovery=bool(ok and f.get('semantic_equivalent') and list(score['dimensions'].values())[:3]==[4,4,4] and score['dimensions']['mathematical_validity']>=3 and score['shortcut'] is False),gate_audit=records.get(f'audit:{i}',{}).get('output'),gate_copy=records.get(f'copy:{i}',{}).get('output'))
        attempts.append(row)
        if ok:eligible.append(row)
    selected=baseline+eligible[:53]
    for name,rows in [('questions-answers.jsonl',selected),('extension-attempts.jsonl',attempts),('overflow-complete.jsonl',eligible[53:])]:
        (ROOT/name).write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in rows))
    public=[dict(id=f'reconstruct-{r["source_index"]}',final_answer=r['source_final_answer'],observations=r['clues']) for r in selected]
    (ROOT/'public-tasks.jsonl').write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in public))
    with (ROOT/'questions-answers.csv').open('w',newline='') as handle:
        writer=csv.writer(handle);writer.writerow(['source_index','cohort','source_question','source_answer','clues','qwen_question','qwen_justification','P','T','E','M','score_100','rating_v4','semantic_equivalent','provisional_grounded_recovery'])
        for x in selected:
            writer.writerow([x['source_index'],x['cohort'],x['source_question'],x['source_final_answer'],'\n'.join(x['clues']),x['qwen']['question'],x['qwen']['justification'],*x['score']['dimensions'].values(),x['score']['score_100'],x['rating_v4'],x.get('semantic_equivalent'),x['provisional_grounded_recovery']])
    def stats(rows):
        scores=[r['score']['score_100'] for r in rows]
        return dict(n=len(rows),mean=sum(scores)/len(scores) if scores else None,histogram={i:sum(r['rating_v4']==i for r in rows) for i in range(1,6)},semantic_matches=sum(r.get('semantic_equivalent') is True for r in rows),provisional_grounded=sum(r['provisional_grounded_recovery'] for r in rows))
    summary=dict(terminal=state['metadata'].get('terminal',False),target_met=len(selected)==100,selected=len(selected),calibration=stats(baseline),extension=stats(eligible[:53]),combined=stats(selected),extension_sources_attempted=len(attempts),extension_input_dispositions=dict(Counter(r['input_status'] for r in attempts)),extension_complete=len(eligible),overflow=len(eligible[53:]),failed_calls=len(state['failures']),recorded_cost_usd=state['metadata'].get('recorded_cost_usd'),limitations=['Automatic gate/completion validity is not answer correctness or independent certification.','47 rows calibrated the rating scale; added rows are a new source frame, not a matched confirmation of the original pool.','No rating thresholds or prompts changed for the extension.'])
    m.r.atomic_write_json(ROOT/'summary.json',summary)
    return summary

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','run','report']);args=p.parse_args()
    if args.action=='prepare':prepare()
    elif args.action=='run':print(json.dumps(Run().run(),indent=2))
    else:
        obj=Run();print(json.dumps(report(obj.manifest,obj.state),indent=2))
