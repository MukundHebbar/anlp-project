#!/usr/bin/env python3
"""Finalize the frozen cohort report and downloadable exports after completion."""
import collections,importlib.util,json,statistics,zipfile
from pathlib import Path
spec=importlib.util.spec_from_file_location('final100',Path(__file__).with_name('run_reconstruct_final100.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
run=m.Run();state=run.state;manifest=run.manifest;root=m.ROOT
assert state['metadata'].get('terminal') is True,'The100-source pipeline is still running'
summary=m.export(manifest,state)
rows=[json.loads(x) for x in (root/'questions-answers.jsonl').read_text().splitlines()]
assert len(rows)==100 and len({x['source_index'] for x in rows})==100
accepted=[x for x in rows if x['input_status']=='accepted'];scored=[x for x in accepted if x['score']['score_100'] is not None]
source_by_id={s['source_index']:s for s in manifest['sources']}
topic_counts={}
for topic in sorted({s['broad_topic'] for s in manifest['sources']}):
 subset=[x for x in rows if source_by_id[x['source_index']]['broad_topic']==topic]
 topic_counts[topic]={'allocated':len(subset),'accepted':sum(x['input_status']=='accepted' for x in subset),'scored':sum(x['score'] is not None and x['score']['score_100'] is not None for x in subset)}
semantic=sum(state['records'].get(f"judge_fidelity:{x['source_index']}",{}).get('output',{}).get('semantic_equivalent') is True for x in accepted)
checks=json.loads((root/'manual-review.json').read_text())
verified=[x['source_index'] for x in checks.get('success_reviews',[]) if x.get('verdict')=='verified' and any(r['source_index']==x['source_index'] and r['provisional_grounded_recovery'] for r in rows)]
reviewed_semantic=[x['source_index'] for x in checks.get('success_reviews',[]) if x.get('verdict') in ['verified','semantic_match_without_grounded_verification'] and any(r['source_index']==x['source_index'] and r['semantic_equivalent'] is True for r in accepted)]
summary['reviewed_semantic_recoveries']=len(reviewed_semantic)
summary['reviewed_semantic_source_ids']=reviewed_semantic
paid=[x for x in list(state['records'].values())+state['failures'] if x.get('stage')!='student']
usage_cost=sum((x.get('raw') or {}).get('usage',{}).get('estimated_cost',0) or 0 for x in paid)
usage_unknown=sum((x.get('raw') or {}).get('usage',{}).get('estimated_cost') is None for x in paid)
student_attempts=sum(k.startswith('student:') for k in state['attempted'])
student_records=[x for x in list(state['records'].values())+state['failures'] if x.get('stage')=='student']
student_token_caps=sum((x.get('raw') or {}).get('finish_reason')=='length' for x in student_records)
ratings=[x['score']['rating_1_to_5'] for x in scored]
fidelity_outputs=[r['output'] for r in state['records'].values() if r['stage']=='judge_fidelity']
validity_outputs=[r['output'] for r in state['records'].values() if r['stage']=='judge_validity']
failure_counts=dict(collections.Counter(r['stage'] for r in state['failures']))
dimensions={name:{'count':len(vals),'mean':statistics.mean(vals) if vals else None,'histogram':dict(sorted(collections.Counter(vals).items()))} for name,vals in ((name,[x['score']['dimensions'][name] for x in scored if x['score']['dimensions'][name] is not None]) for name in ['premise_fidelity','target_fidelity','evidence_integration','mathematical_validity'])}
diagnostics={'dimensions_on_scored_responses':dimensions,'failures_by_stage':failure_counts,'resolved_fidelity_calls':len(fidelity_outputs),'resolved_validity_calls':len(validity_outputs),'validity_answer_correct':sum(v['mathematical_validity']['supplied_answer_correct'] is True for v in validity_outputs),'validity_verification_sound':sum(v['mathematical_validity']['verification_sound'] is True for v in validity_outputs),'shortcut_flags':sum(v['shortcut']['present'] is True for v in validity_outputs)}
summary['diagnostics']=diagnostics
summary['target_checks']={'average_20_to_75':summary['mean'] is not None and 20<=summary['mean']<=75,'semantic_recovery_rate_on_accepted':semantic/len(accepted) if accepted else None,'grounded_recovery_rate_on_accepted':len(verified)/len(accepted) if accepted else None,'middle_rating_strictly_modal':summary['histogram_1_to_5']['3']>max(summary['histogram_1_to_5'][str(i)] for i in [1,2,4,5])}
summary['target_checks']['semantic_success_20_to_40_percent']=bool(accepted and .2<=len(reviewed_semantic)/len(accepted)<=.4)
summary['target_checks']['grounded_success_20_to_40_percent']=bool(accepted and .2<=len(verified)/len(accepted)<=.4)
summary.update(student_token_cap_completions=student_token_caps,topic_counts=topic_counts,automatic_semantic_recoveries=semantic,reviewed_grounded_recoveries=len(verified),reviewed_grounded_source_ids=verified,student_attempts=student_attempts,paid_calls=len(paid),returned_usage_cost_usd=usage_cost,paid_calls_without_usage=usage_unknown,ordinal_rating_sample_variance=statistics.variance(ratings) if len(ratings)>1 else None)
m.r.atomic_write_json(root/'summary.json',summary)
fmt=lambda v:'unavailable' if v is None else f'{v:.2f}'
lines=['# Final100-source run: results','','Frozen version: four sentence clues plus the final answer; local Qwen3-4B nonthinking; PC-v4 judges. This is reused development data, not untouched confirmation.','',f"- Allocated sources:100; accepted inputs:{len(accepted)}.",f"- Input dispositions:{summary['input_status_counts']}.",f"- Qwen attempts:{student_attempts}; parsed responses:{summary['qwen_responses']}; scored:{len(scored)}.",f"- Mean:{fmt(summary['mean'])}/100; median:{fmt(summary['median'])}; sample standard deviation:{fmt(summary['sample_stddev'])}; sample variance:{fmt(summary['sample_variance'])}.",f"- Automatic semantic recoveries:{semantic}; provisional grounded recoveries:{summary['provisional_grounded_recoveries']}; reviewed verified grounded recoveries:{len(verified)}.",'','| Rating | Count |','|---|---:|']
for rating in range(1,6):lines.append(f"|{rating}|{summary['histogram_1_to_5'][str(rating)]}|")
lines += ['', 'These rating counts cover accepted inputs with resolved scores. Rejected inputs and missing judgments are not imputed as zero. Grade5 is not automatically a strict recovery. Raw scores are not rewritten after manual review.','', '| Topic | Allocated | Accepted | Scored |','|---|---:|---:|---:|']
for topic,counts in topic_counts.items():lines.append(f"|{topic}|{counts['allocated']}|{counts['accepted']}|{counts['scored']}|")
lines += ['', '## Diagnostics', '', f"- Failures by stage: {failure_counts}.",f"- Resolved validity judgments: {len(validity_outputs)}; supplied answer judged correct: {diagnostics['validity_answer_correct']}; verification judged sound: {diagnostics['validity_verification_sound']}; shortcut flags: {diagnostics['shortcut_flags']}.",f"- Desired average20–75/100 met: {summary['target_checks']['average_20_to_75']}.",f"- Rating3 strictly most frequent: {summary['target_checks']['middle_rating_strictly_modal']}.",f"- Semantic recoveries / accepted inputs: {semantic}/{len(accepted)}. Reviewed grounded recoveries / accepted inputs: {len(verified)}/{len(accepted)}. These are separate from the mean partial-credit score.", '', 'These diagnostics are model judgments with explicit missingness, not independently established error rates. The100-source denominator includes gate exclusions; the scored denominator is selected by successful gates and resolved output validation. No score-distribution target was enforced by changing grades or replacing sources.']
lines += ['',f"Paid calls:{len(paid)}; returned usage estimates:${usage_cost:.5f}; missing-usage paid calls:{usage_unknown}. Local inference is separate. These are recorded estimates, not a billing reconciliation.",'','## Interpretation and review','', 'This run freezes a procedure and measures its yield; it does not establish an optimal clue count, a Gaussian distribution, universal judge accuracy, or training transfer. Rejected/uncertain conversions remain in the100-source denominator. Gate disputes and verified counterexamples are in [manual review](manual-review.json). The original dataset labels include invalid sources; use the status-bearing research export or accepted task subset.','', '## Downloads','', '- [Full100-source CSV](questions-answers.csv)','- [Full100-source JSONL with ratings and review](questions-answers.jsonl)','- [Readable questions and answers](questions-answers.md)','- [Accepted reconstruction question/answer pairs](reconstruct-qa.jsonl)','- [Accepted public tasks](public-tasks.jsonl)','- [Export guide](EXPORTS.md)','- [Frozen manifest](manifest.json)','- [Raw calls and failures](run.json)']
lines += ['', '## Concrete findings', '', '- Source28: a valid alternative function supports partial credit, but is not a reformulation of the original function.', '- Sources94 and65: the original mathematical question is recovered, but Qwen merely asserts the supplied answer instead of verifying it. Source65 also has an unresolved validity judgment due to a non-verbatim claim quotation.', '- Source123: Qwen reverses the required non-perfect-power condition, making the claimed existence false.', '- Source78: Qwen changes a constant term into a linear term inside an oscillatory phase, changing the limit from-1 to-sqrt(2)/2.', '- Sources49,39,5 and12: copying candidates leave an essential bound unspecified or invent a parameter/target. These are documented weaknesses of the copying gate; their frozen exclusions remain visible.', '- Source1: the source itself leaves a2 unconstrained. Two exact rational constructions give different final answers despite the source-aware audit accepting it. It remains excluded.', '', 'The automatic input subset is therefore gate-passed research material, not a certified leak-free or universally valid dataset. Assistant case reviews are separate from independent human annotation.']
(root/'report.md').write_text('\n'.join(lines)+'\n')
# Fixed categorical histogram, never a fitted Gaussian curve.
try:
 import matplotlib
 matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 fig,ax=plt.subplots(figsize=(6,3.5))
 ax.bar(range(1,6),[summary['histogram_1_to_5'][str(i)] for i in range(1,6)],color='#3564ad')
 ax.set(xticks=range(1,6),xlabel='Partial-credit rating',ylabel='Number of scored responses',title=f'Four-clue RECONSTRUCT: {len(scored)} scored / {len(accepted)} accepted /100 sources')
 fig.tight_layout();fig.savefig(root/'rating-distribution.png',dpi=180);plt.close(fig)
except ImportError:pass
files=['questions-answers.csv','questions-answers.jsonl','questions-answers.md','reconstruct-qa.jsonl','public-tasks.jsonl','source-question-answer-key.jsonl','EXPORTS.md','report.md','summary.json','manual-review.json','manifest.json','run.json','runner-frozen.py','tests.log','source-1-counterexample.json','rating-distribution.png','verification.json']
with zipfile.ZipFile(root/'reconstruct-final100-deliverables.zip','w',zipfile.ZIP_DEFLATED) as bundle:
 for name in files:
  if (root/name).exists():bundle.write(root/name,arcname=name)
 for role,prompt in manifest['prompts'].items():bundle.writestr(f'frozen-prompts/{role}.md',prompt)
 for path in ['docs/design/reconstruct/FINAL_V1.md','docs/plans/reconstruct-final-100-v1.md','scripts/report_reconstruct_final100.py','scripts/verify_reconstruct_final100.py','src/anlp_project/reconstruct_judge_validation.py','src/anlp_project/reconstruct_partial_credit.py']:
  bundle.write(path,arcname=path)
print(json.dumps(summary,indent=2))
