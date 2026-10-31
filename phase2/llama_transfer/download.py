"""Download the official pinned student once; token comes from stdin, never logs or argv."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

from huggingface_hub import HfApi, hf_hub_download, snapshot_download

MODEL = 'meta-llama/Llama-3.2-3B-Instruct'
REVISION = '0cb88a4f764b7a12671c53f0838cd831a0843b95'


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--out',required=True)
    args=parser.parse_args()
    token=sys.stdin.read().strip()
    dest=Path(args.out)
    # Fail before a large transfer when the token has no gated-model access; do not repeatedly retry access.
    hf_hub_download(MODEL,'config.json',revision=REVISION,token=token)
    info=HfApi(token=token).model_info(MODEL,revision=REVISION,files_metadata=True)
    snapshot_download(MODEL,revision=REVISION,local_dir=dest,token=token,max_workers=3,
                      allow_patterns=['*.safetensors','*.safetensors.index.json','config.json',
                                      'generation_config.json','tokenizer*','special_tokens_map.json',
                                      'chat_template.jinja','README.md','LICENSE*'])
    expected={item.rfilename:item for item in info.siblings}
    files={}
    for path in sorted(dest.iterdir()):
        if not path.is_file() or path.name=='source.json':continue
        item=expected[path.name]
        digest=hashlib.file_digest(path.open('rb'),'sha256').hexdigest()
        if path.stat().st_size != item.size or (item.lfs and digest != item.lfs.sha256):
            raise ValueError(f'Model checksum/size mismatch: {path.name}')
        files[path.name]={'sha256':digest,'bytes':path.stat().st_size}
    (dest/'source.json').write_text(json.dumps({'model':MODEL,'revision':REVISION,'files':files},indent=2))
    print('LLAMA_DOWNLOAD_VERIFIED',sum(v['bytes'] for v in files.values()),flush=True)


if __name__=='__main__':main()
