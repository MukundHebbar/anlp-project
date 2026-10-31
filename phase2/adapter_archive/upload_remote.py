"""Archive only this project's validated PEFT files; token arrives on stdin and is never logged."""
import hashlib
import json
import re
import struct
import sys
from pathlib import Path
from huggingface_hub import HfApi, CommitOperationAdd

payload = json.load(sys.stdin)
api = HfApi(token=payload['token'])
assert api.whoami()['name'] == 'ransom32'
repo = 'ransom32/anlp-reasoning-transfer-adapters'
api.create_repo(repo, repo_type='model', private=False, exist_ok=True)
base = 'Qwen/Qwen3.5-2B'
revision = '15852e8c16360a2fea060d615a32b45270f8a8fc'
sft_names = {'SJ-sft470', 'SS2-sft470-nofilter', 'sft470-adapter', 'SS-sft470'}
rows = [r for r in payload['inventory']['adapters'] if 'Qwen3.5-2B' in (r.get('base') or '')
        and ('/anlp-opd-shared/' not in r['path'] or '/grpo/' in r['path']
             or r['path'].rsplit('/', 1)[1] in sft_names)]
root = Path('/tmp/mukund-anlp-adapter-archive')
root.mkdir(exist_ok=True)
manifest = {'base_model': base, 'base_revision': revision, 'source_count': len(rows),
            'unique_adapters': [], 'aliases': [], 'failures': [],
            'code_provenance': payload['code_provenance']}
known = {}
reserved = set()
pending = []

def flush():
    if not pending:
        return
    result = api.create_commit(repo_id=repo, operations=[op for _, operations in pending for op in operations],
                               num_threads=8, commit_message=f'Archive batch of {len(pending)} adapters')
    for entry, _ in pending:
        entry['commit'] = result.oid
        manifest['unique_adapters'].append(entry)
        print('archived', entry['name'], entry['weight_sha256'][:12], flush=True)
    pending.clear()
    (root / 'progress.json').write_text(json.dumps(manifest, indent=2))

def slug(row):
    p = row['path']
    if '/anlp-opd-shared/grpo/' in p:
        return 'phase1-grpo/' + p.rsplit('/', 1)[1]
    if '/anlp-opd-shared/' in p:
        return 'phase1-sft/' + p.rsplit('/', 1)[1]
    if '/mix-control/runs/' in p:
        return 'mix-control/' + p.split('/mix-control/runs/')[1].replace('/adapters/', '/')
    if '/failure-driven/runs/' in p:
        return 'failure-driven/' + p.split('/failure-driven/runs/')[1].replace('/adapters/', '/')
    if '/yashas.kotre/phase2/' in p:
        return 'phase2-shared/' + p.split('/yashas.kotre/phase2/')[1].replace('/adapters/', '/')
    raise ValueError('Unrecognized project adapter location: ' + p)

def priority(row):
    p = row['path']
    return (0 if '/anlp-opd-shared/grpo/' in p else
            1 if p.endswith('/step75') else 2 if '/anlp-opd-shared/' in p else
            3 if p.endswith(('/step40', '/step32')) else 4, p)

def inspect_weight(p):
    size = p.stat().st_size
    with p.open('rb') as f:
        n = struct.unpack('<Q', f.read(8))[0]
        assert 2 < n < min(size, 100_000_000)
        header = json.loads(f.read(n))
    tensors = {k: v for k, v in header.items() if k != '__metadata__'}
    assert tensors and all('lora_' in k for k in tensors)
    assert max(v['data_offsets'][1] for v in tensors.values()) == size - 8 - n
    for key, value in tensors.items():
        assert 0 <= value['data_offsets'][0] <= value['data_offsets'][1] <= size - 8 - n
        if 'lora_A' in key:
            assert key.replace('lora_A', 'lora_B') in tensors
    with p.open('rb') as f:
        sha = hashlib.file_digest(f, 'sha256').hexdigest()
    return sha, len(tensors)

for i, row in enumerate(sorted(rows, key=priority), 1):
    source = Path(row['path'])
    try:
        weight = source / 'adapter_model.safetensors'
        sha, tensors = inspect_weight(weight)
        cfg = dict(row['config'])
        cfg['base_model_name_or_path'] = base
        cfg['revision'] = revision
        raw_cfg = json.dumps(cfg, indent=2) + '\n'
        assert not re.search(r'hf_[A-Za-z0-9]{20,}', raw_cfg)
        identity = sha + ':' + hashlib.sha256(raw_cfg.encode()).hexdigest()
        name = slug(row)
        if identity in known:
            manifest['aliases'].append({'source': str(source), 'name': name,
                                        'subfolder': known[identity], 'weight_sha256': sha})
            continue
        if name in reserved:
            name += '-' + sha[:8]
        reserved.add(name)
        subfolder = 'adapters/' + name
        readme = ('---\nbase_model: Qwen/Qwen3.5-2B\nlibrary_name: peft\nlicense: apache-2.0\n'
                  'tags: [lora, anlp, mathematical-reasoning]\n---\n\n# ' + name + '\n\n'
                  'Unmerged research LoRA adapter. Load with the base model `Qwen/Qwen3.5-2B`, '
                  'revision `' + revision + '`.\n\nWeight SHA-256: `' + sha + '`.\n\n'
                  'Source adapter weights are unchanged. The configuration base path is normalized '
                  'from a cluster-local cache path to the public model ID. '
                  'This archive is a preservation copy, not a claim that every intermediate checkpoint improves performance.\n')
        ops = [CommitOperationAdd(path_in_repo=subfolder + '/adapter_model.safetensors', path_or_fileobj=weight),
               CommitOperationAdd(path_in_repo=subfolder + '/adapter_config.json', path_or_fileobj=raw_cfg.encode()),
               CommitOperationAdd(path_in_repo=subfolder + '/README.md', path_or_fileobj=readme.encode())]
        entry = {'name': name, 'subfolder': subfolder, 'source': str(source), 'weight_sha256': sha,
                 'bytes': weight.stat().st_size, 'tensor_count': tensors}
        pending.append((entry, ops))
        known[identity] = subfolder
        print(f'{i}/{len(rows)} prepared {name} {sha[:12]}', flush=True)
    except Exception as error:
        manifest['failures'].append({'source': str(source), 'error': f'{type(error).__name__}: {error}'})
        print(f'{i}/{len(rows)} FAILED {source}: {type(error).__name__}: {error}', flush=True)
    if len(pending) >= 8:
        flush()
    (root / 'progress.json').write_text(json.dumps(manifest, indent=2))

flush()
info = api.model_info(repo, files_metadata=True)
remote = {f.rfilename: f for f in info.siblings}
for entry in manifest['unique_adapters']:
    f = remote[entry['subfolder'] + '/adapter_model.safetensors']
    assert f.size == entry['bytes']
    if f.lfs:
        assert f.lfs.sha256 == entry['weight_sha256']
manifest['remote_verified'] = True
readme = ('---\nbase_model: Qwen/Qwen3.5-2B\nlibrary_name: peft\nlicense: apache-2.0\n'
          'tags: [lora, anlp, mathematical-reasoning, grpo]\n---\n\n'
          '# ANLP mathematical reasoning: adapter archive\n\n'
          f"Preservation of {len(manifest['unique_adapters'])} distinct adapters from {len(rows)} surviving source copies. "
          'Includes original GRPO specialists and mixed model, SFT warm-ups, matched SOLVE controls, '
          'and surviving Phase-2 checkpoints. OPD-trained adapters are excluded at the user\'s request. '
          'No base weights, optimizer states, credentials, or dataset examples are included.\n\n'
          '## Loading\n\n```python\nfrom transformers import Qwen3_5ForConditionalGeneration\n'
          'from peft import PeftModel\n'
          f'base = Qwen3_5ForConditionalGeneration.from_pretrained("{base}", revision="{revision}", dtype="bfloat16")\n'
          f'model = PeftModel.from_pretrained(base, "{repo}", subfolder="adapters/phase1-grpo/solve66")\n```\n\n'
          'Keep the original non-thinking template and task prompts when reproducing the study. '
          'See `archive-manifest.json` for checksums, source aliases and any failures. '
          'Adapter configs use public base IDs; their tensors are unmodified. '
          'Several historical intermediate checkpoints have been removed from scratch and are not recoverable from git.\n\n'
          '| Adapter | Size (MB) |\n|---|---:|\n')
readme += '\n'.join(f"| [{e['name']}]({e['subfolder']}) | {e['bytes']/1e6:.1f} |" for e in manifest['unique_adapters']) + '\n'
api.create_commit(repo_id=repo, operations=[
    CommitOperationAdd(path_in_repo='README.md', path_or_fileobj=readme.encode()),
    CommitOperationAdd(path_in_repo='archive-manifest.json', path_or_fileobj=(json.dumps(manifest, indent=2)+'\n').encode()),
], commit_message='Publish verified inventory and loading instructions')
(root / 'manifest.json').write_text(json.dumps(manifest, indent=2))
print('ARCHIVE_COMPLETE', repo, len(manifest['unique_adapters']), 'unique;', len(manifest['failures']), 'failures', flush=True)
