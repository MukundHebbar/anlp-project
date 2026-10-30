"""Read-only recovery of project adapters from the previously used Modal volumes."""
from pathlib import Path
import json
import modal

import os
account=os.environ['ANLP_ARCHIVE_ACCOUNT']
root=Path('local/adapter-archive/modal')/account
for name in ('anlp-opd-cache','anlp-final-v3-hf-cache'):
    try:
        volume=modal.Volume.from_name(name,create_if_missing=False)
        entries=list(volume.iterdir('/',recursive=True))
    except Exception as error:
        print(account,name,type(error).__name__,flush=True)
        continue
    wanted=[e for e in entries if e.path.endswith(('adapter_config.json','adapter_model.safetensors'))]
    for entry in wanted:
        target=root/name/entry.path.lstrip('/')
        target.parent.mkdir(parents=True,exist_ok=True)
        if target.exists() and target.stat().st_size==entry.size:
            continue
        temporary=target.with_suffix(target.suffix+'.partial')
        with temporary.open('wb') as f:
            for data in volume.read_file(entry.path):
                f.write(data)
        assert temporary.stat().st_size==entry.size
        temporary.replace(target)
        print('Recovered',account,name,entry.path,entry.size,flush=True)
