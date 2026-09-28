#!/usr/bin/env python3
"""Publish the completed100-valid-row extension, with separate cohort statistics."""
import csv
import importlib.util
import json
import statistics
import zipfile
from pathlib import Path

spec=importlib.util.spec_from_file_location('extension',Path(__file__).with_name('run_reconstruct_valid100.py'))
e=importlib.util.module_from_spec(spec);spec.loader.exec_module(e)
run=e.Run();root=e.ROOT
assert run.state['metadata'].get('terminal'),'Extension still running'
summary=e.report(run.manifest,run.state)
assert summary['target_met'],'Fewer than100 complete rows; do not publish as complete'
rows=[json.loads(x) for x in (root/'questions-answers.jsonl').read_text().splitlines()]
review_path=root/'manual-review.json'
reviews=json.loads(review_path.read_text()) if review_path.exists() else {'reviews':[]}
by_id={r['source_index']:r for r in reviews.get('reviews',[])}
for cohort in ['calibration','extension','combined']:
    subset=[r for r in rows if cohort=='combined' or r['cohort']==cohort]
    scores=[r['score']['score_100'] for r in subset]
    summary[cohort].update(median=statistics.median(scores),sample_stddev=statistics.stdev(scores),sample_variance=statistics.variance(scores),minimum=min(scores),maximum=max(scores))
    summary[cohort]['reviewed_grounded_successes']=sum(r['provisional_grounded_recovery'] and by_id.get(r['source_index'],{}).get('verdict')=='verified_grounded' for r in subset)
summary['failures_by_stage']=dict(e.Counter(r['stage'] for r in run.state['failures']))
e.m.r.atomic_write_json(root/'summary.json',summary)
lines=['#100 valid RECONSTRUCT questions and answers','','Validity means both automatic input gates passed and both judges returned complete validated scores. Qwen answers may be wrong. The47 calibration rows and53 added rows are labeled separately. Private answer-key material follows; use public-tasks.jsonl for student inputs.','']
for x in rows:
    lines += [f"## {x['source_index']} — {x['cohort']}",'', '**Original question:** '+x['source_question'],'','**Original final answer:** '+x['source_final_answer'],'','**Four public clues:**']+[f"{i}. {c}" for i,c in enumerate(x['clues'],1)]
    lines += ['', '**Qwen reconstructed question:** '+x['qwen']['question'],'','**Qwen verification:** '+x['qwen']['justification'],'',f"**Score:** {x['score']['score_100']}/100; **v4 rating:** {x['rating_v4']}/5; **semantic match:** {x.get('semantic_equivalent')}; **provisional grounded recovery:** {x['provisional_grounded_recovery']}."]
    if x['source_index'] in by_id:lines+=['','**Assistant case review:** '+json.dumps(by_id[x['source_index']],ensure_ascii=False)]
    lines+=['']
(root/'questions-answers.md').write_text('\n'.join(lines)+'\n')
report=['#100 completely scored, gate-passed RECONSTRUCT examples','','The extension retains47 calibration rows and adds53 previously unevaluated source questions. Prompts, four-clue exposure, model configuration and v4 display thresholds stayed fixed. This is a complete-case dataset, not100 successful reconstructions or an independently certified leak-free benchmark.','',f"Additional sources processed: {summary['extension_sources_attempted']}; input dispositions: {summary['extension_input_dispositions']}; fully scored additions: {summary['extension_complete']}; completed overflow: {summary['overflow']}. Selection uses frozen source order, not rating or completion speed. All rejected/unresolved attempts remain in extension-attempts.jsonl.",'','| Cohort | n | Mean /100 | Median | Sample SD | Semantic matches | Provisional grounded |','|---|---:|---:|---:|---:|---:|---:|']
for name in ['calibration','extension','combined']:
    s=summary[name];report.append(f"| {name} | {s['n']} | {s['mean']:.2f} | {s['median']:.2f} | {s['sample_stddev']:.2f} | {s['semantic_matches']} | {s['provisional_grounded']} |")
report+=['','| Rating | Calibration | Added | Combined |','|---|---:|---:|---:|']
for i in range(1,6):report.append(f"| {i} | {summary['calibration']['histogram'][i]} | {summary['extension']['histogram'][i]} | {summary['combined']['histogram'][i]} |")
report+=['',f"Recorded incremental cost estimate: ${summary['recorded_cost_usd']:.5f}. Failed calls by stage: {summary['failures_by_stage']}. Missing provider usage is not a reconciled bill.",'','## Interpretation','','The thresholds were calibrated on the original47 scored responses. The added53 were not used to retune them. However, they use a new DeepMath sampling frame and dataset reference solutions instead of the old prior-checked pool; no matched causal performance comparison is claimed. Completion/gating exclusions may be selective. The combined100 is not a held-out test set.','', 'Semantic matching, validity of the supplied answer for the reconstructed question, and the quality of Qwen verification remain distinct. High partial credit is not full recovery. Apparent recoveries require mathematical case review, recorded separately; assistant review is not independent human annotation. Automatic gates and LLM judgments remain fallible.','','## Files','','- [100 question/answer CSV](questions-answers.csv)','- [Readable questions and Qwen answers](questions-answers.md)','- [Full selected JSONL](questions-answers.jsonl)','- [Public inputs only](public-tasks.jsonl)','- [All extension attempts](extension-attempts.jsonl)','- [Frozen manifest and source provenance](manifest.json)','- [Raw model calls and failures](run.json)','- [Verification](verification.json)','- [Manual case review](manual-review.json)','- [Complete bundle](reconstruct-valid100.zip)']
(root/'report.md').write_text('\n'.join(report)+'\n')
with (root/'questions-answers.csv').open(newline='') as f:assert len(list(csv.DictReader(f)))==100
files=['questions-answers.csv','questions-answers.jsonl','questions-answers.md','public-tasks.jsonl','extension-attempts.jsonl','overflow-complete.jsonl','calibration-47.jsonl','summary.json','report.md','manifest.json','run.json','manual-review.json','verification.json','tests.log','runner-frozen.py','EXPORTS.md']
with zipfile.ZipFile(root/'reconstruct-valid100.zip','w',zipfile.ZIP_DEFLATED) as z:
    for name in files:
        if (root/name).exists():z.write(root/name,arcname=name)
    for role,prompt in run.manifest['prompts'].items():z.writestr(f'frozen-prompts/{role}.md',prompt)
    for name in ['run.json','manifest.json','verification.json','manual-review.json']:
        z.write(e.PARENT/name,arcname='calibration-parent/'+name)
    for name in ['docs/plans/reconstruct-valid-100-extension.md','scripts/verify_reconstruct_valid100.py','scripts/report_reconstruct_valid100.py','src/anlp_project/reconstruct_partial_credit.py','src/anlp_project/reconstruct_judge_validation.py']:
        z.write(name,arcname=name)
print(json.dumps(summary,indent=2))
