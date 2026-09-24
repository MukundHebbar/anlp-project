#!/usr/bin/env bash
set -euo pipefail

# Run this from a node where the user-owned persistent share is mounted.
# Override JUDGE_SHARE_ROOT if this cluster uses /share1/$USER instead.
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
JUDGE_SHARE_ROOT="${JUDGE_SHARE_ROOT:-/share3/${USER:?USER is not set}}"
JUDGE_PYTHON_BIN="${JUDGE_PYTHON_BIN:-/home2/${USER}/CausalRepLearning/.venv/bin/python}"
MODEL_REVISION="${JUDGE_MODEL_REVISION:-main}"
MODEL_ROOT="${JUDGE_SHARE_ROOT}/models"
HF_HOME="${JUDGE_SHARE_ROOT}/huggingface"
INVENTORY="${MODEL_ROOT}/judge-model-inventory.json"

if [[ ! -d "$JUDGE_SHARE_ROOT" ]]; then
    echo "Persistent share is not mounted: $JUDGE_SHARE_ROOT" >&2
    echo "Set JUDGE_SHARE_ROOT to the user-owned share path on the allocated node." >&2
    exit 2
fi
if [[ ! -w "$JUDGE_SHARE_ROOT" ]]; then
    echo "Persistent share is not writable by $USER: $JUDGE_SHARE_ROOT" >&2
    exit 2
fi
if [[ ! -x "$JUDGE_PYTHON_BIN" ]]; then
    JUDGE_PYTHON_BIN="$(command -v python3)"
fi

mkdir -p "$MODEL_ROOT" "$HF_HOME"
export HF_HOME
export HUGGINGFACE_HUB_CACHE="$HF_HOME/hub"

"$JUDGE_PYTHON_BIN" -m pip install --upgrade \
    "transformers>=4.55,<5" accelerate "huggingface_hub>=0.34" safetensors

PROJECT_ROOT="$PROJECT_ROOT" MODEL_ROOT="$MODEL_ROOT" INVENTORY="$INVENTORY" MODEL_REVISION="$MODEL_REVISION" \
    "$JUDGE_PYTHON_BIN" - <<'PY'
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from huggingface_hub import HfApi, snapshot_download

models = (
    ("Qwen/Qwen3-8B", "Qwen3-8B"),
    ("Qwen/Qwen3-1.7B", "Qwen3-1.7B"),
)
requested_revision = os.environ["MODEL_REVISION"]
model_root = Path(os.environ["MODEL_ROOT"])
token = os.environ.get("HF_TOKEN")
api = HfApi(token=token)
inventory = []
for model_id, directory_name in models:
    info = api.model_info(model_id, revision=requested_revision)
    resolved_revision = getattr(info, "sha", None) or requested_revision
    local_dir = model_root / directory_name
    snapshot_download(
        repo_id=model_id,
        revision=resolved_revision,
        local_dir=str(local_dir),
        token=token,
    )
    inventory.append(
        {
            "model_id": model_id,
            "requested_revision": requested_revision,
            "resolved_revision": resolved_revision,
            "local_dir": str(local_dir),
            "downloaded_at_utc": datetime.now(timezone.utc).isoformat(),
        }
    )

output = {
    "purpose": "JUDGE teacher/student checkpoints",
    "models": inventory,
    "hf_home": os.environ["HF_HOME"],
}
Path(os.environ["INVENTORY"]).write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
print(json.dumps(output, indent=2))
PY

echo "Model inventory written to $INVENTORY"
