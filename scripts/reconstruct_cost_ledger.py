#!/usr/bin/env python3
"""Deduplicate provider usage across copied research artifacts, including failures.

This is an observational ledger, not a provider billing reconciliation or a
cross-process reservation lock. Requests without returned usage remain unknown.
"""
import argparse
import hashlib
import json
from pathlib import Path


def fingerprint(raw):
    fields = {k: raw.get(k) for k in ('content', 'reasoning', 'finish_reason', 'usage', 'elapsed_seconds')}
    return hashlib.sha256(json.dumps(fields, sort_keys=True).encode()).hexdigest()


def collect(root):
    paid = {}
    unknown = set()
    for path in sorted(root.rglob('*.json')):
        try:
            run = json.loads(path.read_text())
        except (ValueError, OSError):
            continue
        if not isinstance(run, dict) or not any(isinstance(run.get(k), dict) for k in ('banks', 'records')):
            continue
        for section in ('banks', 'audits', 'disclosures', 'disclosure_audits', 'evaluations', 'source_recovery', 'judge_fixtures', 'teacher_reconstructions', 'copy_challenges', 'records'):
            for key, row in run.get(section, {}).items():
                if row.get('model') in {'mechanical_composition', 'authored_fixture'}:
                    continue
                if section == 'records':
                    if not isinstance(row.get('raw'), dict):
                        continue
                    raw = row['raw']
                else:
                    raw = dict(row.get('request', {}))
                    raw['content'] = row.get('raw_content')
                usage = raw.get('usage') or {}
                if usage.get('estimated_cost') is None:
                    unknown.add((section, key))
                    continue
                fid = fingerprint(raw)
                entry = paid.setdefault(fid, {'estimated_cost_usd': float(usage['estimated_cost']), 'locations': []})
                entry['locations'].append({'file': str(path), 'section': section, 'key': key})
        for row in run.get('failures', []):
            stage = row.get('stage', 'calibration')
            key = row.get('key', row.get('id'))
            if stage in ('student', 'student_revision'):
                continue
            raw = row.get('raw') or {}
            usage = raw.get('usage') or {}
            if usage.get('estimated_cost') is None:
                unknown.add((stage, key))
                continue
            fid = fingerprint(raw)
            entry = paid.setdefault(fid, {'estimated_cost_usd': float(usage['estimated_cost']), 'locations': []})
            entry['locations'].append({'file': str(path), 'section': 'failures', 'key': key})
    imported = {key for key, row in paid.items()
                if any('pilot-v1' in Path(loc['file']).parts for loc in row['locations'])}
    return {
        'scope': str(root),
        'deduplication': 'Exact raw response content, reasoning, usage, finish reason, and elapsed time; no provider request IDs available. Same-request copies collapse; identical distinct requests could theoretically collide.',
        'unique_cost_bearing_records': len(paid),
        'all_recorded_estimated_cost_usd': sum(v['estimated_cost_usd'] for v in paid.values()),
        'imported_pilot_estimated_cost_usd': sum(paid[k]['estimated_cost_usd'] for k in imported),
        'followup_only_estimated_cost_usd': sum(v['estimated_cost_usd'] for k, v in paid.items() if k not in imported),
        'unique_records_without_usage': len(unknown),
        'limitation': 'Recorded estimates only; missing-usage failures may incur additional cost. Historical means pilot-v1 artifact membership, not a time-derived billing boundary.',
        'records': paid,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, default=Path('artifacts/reconstruct'))
    p.add_argument('--output', type=Path, default=Path('artifacts/reconstruct/followup-v2/cost-ledger.json'))
    a = p.parse_args()
    result = collect(a.root)
    a.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'records'}, indent=2))


if __name__ == '__main__':
    main()
