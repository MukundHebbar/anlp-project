#!/usr/bin/env python3
"""Report amendment U without rewriting legacy rubric judgments."""
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from anlp_project.reconstruct import stable_hash, actual_cost, load_prompt


def main():
    root=Path('artifacts/reconstruct/inference-u')
    manifest=json.loads((root/'fixtures.json').read_text())
    results={}
    for prompt in ['evaluate_p2','evaluate_p3']:
        run=json.loads((root/f'{prompt}.json').read_text())
        assert run['metadata']['fixtures_hash']==stable_hash(manifest)
        assert stable_hash(Path(f'data/prompts/reconstruct/runtime/{prompt}.md').read_text())==manifest['prompt_hashes'][prompt]
        records=defaultdict(list)
        for record in run['judge_fixtures'].values():
            # The manifest freezes exact file bytes; the runner strips outer
            # whitespace. Verify both rather than rewriting the preregistration.
            assert record['prompt_hash']==stable_hash(load_prompt(prompt))
            records[record['fixture_id']].append(record)
        rows=[]
        for fixture in manifest['fixtures']:
            matches=records[fixture['id']]
            assert len(matches)<=1
            output=matches[0]['output'] if matches else {}
            passed=(output.get('status')=='scored' and output.get('score') in fixture['acceptable_scores']
                    and output.get('shortcut') is fixture['expected_shortcut'])
            if prompt=='evaluate_p3' and fixture['acceptable_scores']==[4]:
                passed=passed and output.get('inference',{}).get('status')=='substantive'
            rows.append(dict(id=fixture['id'],category=fixture['category'],expected=fixture['acceptable_scores'],
                observed=output.get('score'),shortcut=output.get('shortcut'),passed=passed,
                resolved=bool(matches),reason=output.get('reason')))
        results[prompt]=dict(rows=rows,authored_passed=sum(r['passed'] for r in rows if r['category'].startswith('authored_')),
            authored_total=16,diagnostics_passed=sum(r['passed'] for r in rows if r['category']=='production_diagnostic'),
            diagnostics_total=4,failures=len(run['failures']),resolved=len(run['judge_fixtures']),
            recorded_cost_usd=actual_cost(run))
    candidate=results['evaluate_p3']
    decision='passes_development_gate' if candidate['authored_passed']==16 and candidate['diagnostics_passed']==4 else 'not_passed'
    report=dict(protocol=manifest['protocol'],fixtures_hash=stable_hash(manifest),results=results,decision=decision,
        limitations=['Assistant-authored/reviewed references, not independent human gold.',
                     'Four authored families; multiple variants are correlated.',
                     'Production diagnostics were selected for known failure modes.',
                     'Expected labels use the proposed refinement; old-prompt differences need not violate its old specification.',
                     'No change to Qwen semantic recovery follows from changing a rubric.'])
    (root/'comparison.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
    lines=['# Amendment U: inference versus restatement','',f'Decision: **{decision}**.','',
           '| Evaluator | Authored controls | Production diagnostics | Resolved | Recorded cost |',
           '|---|---:|---:|---:|---:|']
    for prompt,r in results.items():
        lines.append(f"| {prompt} | {r['authored_passed']}/16 | {r['diagnostics_passed']}/4 | {r['resolved']}/20 | ${r['recorded_cost_usd']:.6f} |")
    lines+=['','Passes require both the registered score and shortcut flag, plus substantive inference for p3 positive controls.',
            '', '| Case | Expected | p2 | p3 | p3 passes |','|---|---:|---:|---:|---|']
    for a,b in zip(results['evaluate_p2']['rows'],candidate['rows']):
        lines.append(f"| {a['id']} | {a['expected']} | {a['observed']} | {b['observed']} | {b['passed']} |")
    lines+=['','Limitations:']+['- '+s for s in report['limitations']]
    (root/'comparison.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({p:{k:v for k,v in r.items() if k!='rows'} for p,r in results.items()},indent=2))


if __name__=='__main__': main()
