"""Download only the pinned BF16/native Mistral files and record their checksums."""
import hashlib
import json
from pathlib import Path
import sys

from huggingface_hub import HfApi, snapshot_download

MODEL = "mistralai/Ministral-3-3B-Instruct-2512-BF16"
REVISION = "b6d637bef2393152b3da2b2fde72eecdee30557e"
FILES = ["consolidated.safetensors", "params.json", "tekken.json", "config.json",
         "generation_config.json", "chat_template.jinja", "README.md"]


def main():
    destination = Path(sys.argv[1])
    info = HfApi().model_info(MODEL, revision=REVISION, files_metadata=True)
    assert info.sha == REVISION
    expected = {f.rfilename: f for f in info.siblings if f.rfilename in FILES}
    if set(expected) != set(FILES):
        raise RuntimeError("Pinned model is missing a required native-format file")
    snapshot_download(MODEL, revision=REVISION, local_dir=destination, allow_patterns=FILES, max_workers=2)
    hashes = {}
    for name in FILES:
        p = destination / name
        assert p.stat().st_size == expected[name].size, name
        h = hashlib.sha256()
        with p.open("rb") as f:
            for block in iter(lambda: f.read(1024 * 1024), b""):
                h.update(block)
        hashes[name] = {"bytes": p.stat().st_size, "sha256": h.hexdigest()}
        lfs = expected[name].lfs
        if lfs is not None and lfs.sha256 != h.hexdigest():
            raise RuntimeError(f"Checksum mismatch: {name}")
    (destination / "source.json").write_text(json.dumps({
        "model": MODEL, "revision": REVISION, "format": "mistral", "dtype": "bfloat16", "files": hashes,
    }, indent=2) + "\n")
    print(f"Verified {len(hashes)} files at {destination}", flush=True)


if __name__ == "__main__":
    main()
