#!/usr/bin/env python3
"""Offline schema recovery, preserving raw verdicts, errors and usage; no calls."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from anlp_project import reconstruct as r
from anlp_project.reconstruct_gates import public_disclosure_text,normalize_non_candidate_copy_annotations
p=argparse.ArgumentParser();p.add_argument('--artifact',type=Path,required=True);p.add_argument('--bank-prompt',required=True);a=p.parse_args();run=json.loads(a.artifact.read_text());template=r.load_prompt('copy_challenge_p1');changes=[]
for f in run['failures']:
 if f['stage']!='copy_challenge' or f['key'] in run.get('copy_challenges',{}):continue
 raw=f.get('raw')
 if not raw or not raw.get('content'):continue
 i=f['source_index'];bank_key,bank=r.latest_bank(run,i,a.bank_prompt);source=run['sources'][str(i)]
 public={'FINAL_ANSWER':source['final_answer'],'PUBLIC_BANK':{'role_cue_id':bank['output'].get('role_cue_id'),'clues':[{'id':c['id'],'sentence':c['sentence']} for c in bank['output']['clues']]}}
 key=f'{i}:{r.stable_hash(public)}:{r.stable_hash(template)}:{r.DEFAULT_TEACHER_MODEL}:low'
 if key!=f['key']:continue
 try:
  original=r.extract_json_object(raw['content']);normalized=normalize_non_candidate_copy_annotations(original,public_disclosure_text(source['final_answer'],bank['output'],'public_disclosure'))
 except ValueError:continue
 change={'rule':'null-question-exact-public-annotations-v1','removed_alignments':original['alignments'],'original_output_hash':r.stable_hash(original),'normalized_output_hash':r.stable_hash(normalized),'semantic_verdict_unchanged':True}
 run['copy_challenges'][key]={'source_index':i,'bank_key':bank_key,'public_input':public,'public_input_hash':r.stable_hash(public),'rendered_prompt':r.render_template(template,public),'prompt':'copy_challenge_p1','prompt_hash':r.stable_hash(template),'model':r.DEFAULT_TEACHER_MODEL,'reasoning_effort':'low','output':normalized,'raw_content':raw['content'],'request':{k:v for k,v in raw.items() if k!='content'},'normalization':change}
 changes.append({'source_index':i,'key':key,**change})
r.atomic_write_json(a.artifact,run);r.atomic_write_json(a.artifact.parent/'copy-annotation-recovery.json',{'changes':changes,'model_calls':0,'errors_and_raw_outputs_preserved':True});print('Recovered',len(changes),'non-candidate schemas; no judgments changed')
