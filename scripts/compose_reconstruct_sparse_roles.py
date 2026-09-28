#!/usr/bin/env python3
"""Mechanically compose preregistered two-observation +/- role banks; no calls."""
import argparse
import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from anlp_project.reconstruct import accepted_bank, latest_bank, choose_clues, stable_hash, utc_now
from anlp_project.storage import atomic_write_json


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--base', type=Path, required=True)
    p.add_argument('--roles', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    if a.output.exists():
        raise ValueError('Use a new artifact; existing research must not be overwritten')
    base = json.loads(a.base.read_text())
    roles = json.loads(a.roles.read_text())
    out = copy.deepcopy(base)
    for index in base['partitions']['D2']:
        key, bank = accepted_bank(base, index, 'convert_p2')
        role_key, role = latest_bank(roles, index, 'convert_role_p1')
        selected = copy.deepcopy(choose_clues(bank['output'], 2, 0))
        cue = copy.deepcopy(role['output']['clues'][0])
        cue['id'] = 'role'
        for name, clues in [('base_sparse_2', selected), ('role_sparse_2', selected + [cue])]:
            output = {'status': 'OK', 'clues': clues, 'withheld': 'Partial observations; requires public disclosure audit.'}
            if name == 'role_sparse_2':
                output['role_cue_id'] = 'role'
            digest = stable_hash(output)
            out['banks'][f'{index}:{name}:{digest}'] = {
                'source_index': index, 'prompt': name, 'prompt_hash': digest,
                'model': 'mechanical_composition', 'output': output, 'created_at': utc_now(),
                'composition': {'base_bank_key': key, 'role_bank_key': role_key,
                                'role_artifact': str(a.roles), 'selection_seed': 0,
                                'selected_clue_ids': [c['id'] for c in selected],
                                'registration': 'docs/plans/reconstruct-followup-controlled.md#adaptive-amendment-f-sparse-observations-with-answer-role-guidance'}}
        plain = {'clues': selected}
        augmented = {'clues': selected + [cue], 'role_cue_id': 'role'}
        assert choose_clues(plain, 2, 0) == choose_clues(augmented, 3, 0)[:-1]
    out['metadata']['sparse_role_composition'] = {'base': str(a.base), 'roles': str(a.roles), 'requires_joint_audit': True}
    atomic_write_json(a.output, out)
    print('Composed 24 unaudited banks; no source-specific edits or student calls')


if __name__ == '__main__':
    main()
