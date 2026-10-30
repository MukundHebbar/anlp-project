"""Read-only inventory of this user's surviving PEFT adapters on Turing."""
import json
import os
from pathlib import Path

ROOTS = [Path('/home/mukund.hebbar')] + [Path('/scratch') / f'node{i:02d}' / 'mukund.hebbar'
                                         for i in range(1, 15)]
ROOTS += [Path('/scratch/node07/yashas.kotre/phase2')]
SKIP = {'.cache', '.local', 'venv', 'site-packages', 'hf_cache', 'hf_home', 'vllm_cache',
        'triton_cache', 'inductor_cache', 'python', '.git', 'models', 'model', 'xdg_cache', 'flashinfer'}
records = []
errors = []
for root in ROOTS:
    if not root.is_dir():
        continue
    for parent, dirs, files in os.walk(root, onerror=lambda e: errors.append(str(e))):
        dirs[:] = [d for d in dirs if d not in SKIP and not d.startswith('models--')]
        if 'adapter_config.json' not in files:
            continue
        p = Path(parent)
        weights = [f for f in files if f in ('adapter_model.safetensors', 'adapter_model.bin')]
        try:
            cfg = json.loads((p / 'adapter_config.json').read_text())
        except Exception as error:
            errors.append(f'{p}: {error}')
            cfg = {}
        records.append({'path': str(p), 'weights': weights,
                        'bytes': sum((p / f).stat().st_size for f in weights),
                        'base': cfg.get('base_model_name_or_path'),
                        'config': cfg})
print(json.dumps({'adapters': records, 'errors': errors}, indent=2))
