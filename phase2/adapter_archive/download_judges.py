"""Pinned, checksum-verified judge downloads, without allocating GPUs."""
import hashlib
import json
import os
from pathlib import Path
import sys
import argparse
from huggingface_hub import HfApi, snapshot_download

token = sys.stdin.read().strip()
os.environ['HF_HOME'] = '/tmp/mukund-anlp-hf-cache'
api = HfApi(token=token)
root = Path('/tmp/mukund-anlp-local-judges')
root.mkdir(exist_ok=True)
p = argparse.ArgumentParser()
p.add_argument('--model', choices=['selene', 'gemma'], default='selene')
args = p.parse_args()
models = {'selene': 'AtlaAI/Selene-1-Mini-Llama-3.1-8B', 'gemma': 'google/gemma-4-12B-it'}
for name, model in [(args.model, models[args.model])]:
    info = api.model_info(model, files_metadata=True)
    dest = root / name
    print('Downloading', name, info.sha, flush=True)
    patterns = ['*.safetensors', '*.safetensors.index.json', 'config.json', 'generation_config.json',
                'tokenizer*', 'special_tokens_map.json', 'added_tokens.json', 'chat_template.jinja',
                'README.md', 'LICENSE*']
    patterns += ['processor_config.json', 'preprocessor_config.json']
    snapshot_download(model, revision=info.sha, local_dir=dest, allow_patterns=patterns,
                      max_workers=3, token=token)
    expected = {f.rfilename: f for f in info.siblings}
    files = {}
    for path in sorted(dest.iterdir()):
        if not path.is_file() or path.name == 'source.json':
            continue
        sha = hashlib.file_digest(path.open('rb'), 'sha256').hexdigest()
        e = expected[path.name]
        assert e.size == path.stat().st_size, path.name
        if e.lfs:
            assert sha == e.lfs.sha256, path.name
        files[path.name] = {'sha256': sha, 'bytes': path.stat().st_size}
    (dest / 'source.json').write_text(json.dumps({'model': model, 'revision': info.sha,
                                                 'files': files}, indent=2))
    print('Verified', name, sum(f['bytes'] for f in files.values()), flush=True)
print('ALL_DOWNLOADS_READY', flush=True)
