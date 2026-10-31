"""Wait for the no-OPD archive upload and save its verified public manifest locally."""
from pathlib import Path
import json
import subprocess
import time
import urllib.request

ROOT=Path(__file__).resolve().parents[2]
source='/tmp/mukund-anlp-adapter-archive/manifest.json'
host='mukund.hebbar@turing.iiit.ac.in'
deadline=time.monotonic()+12*3600
while True:
    r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15',host,'cat '+source],
                     capture_output=True,text=True)
    if r.returncode==0:
        data=json.loads(r.stdout)
        if data.get('remote_verified') and data['code_provenance'].get('excludes_opd_adapters'):
            break
    if time.monotonic()>deadline:
        raise SystemExit('Archive still incomplete; inspect local/adapter-archive/upload-grpo.log')
    time.sleep(45)

url='https://huggingface.co/api/models/ransom32/anlp-reasoning-transfer-adapters'
info=json.load(urllib.request.urlopen(url))
assert info.get('private') is False
files={f['rfilename'] for f in info['siblings']}
assert not any(p.startswith('adapters/phase1-opd/') for p in files)
for entry in data['unique_adapters']:
    assert entry['subfolder']+'/adapter_model.safetensors' in files
out=ROOT/'phase2/results/adapter-archive'
out.mkdir(parents=True,exist_ok=True)
(out/'manifest.json').write_text(json.dumps(data,indent=2)+'\n')
readme=('# Public adapter archive\n\n'
        '[ransom32/anlp-reasoning-transfer-adapters](https://huggingface.co/ransom32/anlp-reasoning-transfer-adapters)\n\n'
        f"Completed: {len(data['unique_adapters'])} distinct adapters, {len(data['aliases'])} duplicate aliases, "
        f"{len(data['failures'])} failures, from {data['source_count']} surviving project source copies. "
        'All uploaded weights were checked against the Hub file sizes and SHA-256 hashes. OPD-trained adapters '
        'are excluded. Sources remain untouched; configs normalize the base-model path to its public ID.\n\n'
        'The archive includes the four headline GRPO adapters, six control endpoints, surviving failure-driven '
        'runs, self-judge checkpoints and derived Phase-2 hybrids. Intermediate checkpoints deleted before this '
        'inventory are not claimed to have been recovered. See the manifest for every surviving source and alias.\n')
(out/'README.md').write_text(readme)
print(readme,flush=True)
