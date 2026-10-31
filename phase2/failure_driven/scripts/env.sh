#!/bin/bash
# Run a command in the failure-driven experiment's environment on a Turing node (inside a Slurm job):
#   bash phase2/failure_driven/scripts/env.sh python scripts/turing/opd_run.py ...
#
# Packages: Yashas's node07 environment, used read-only. His venv's interpreter links into his private home, so a
# small venv on our scratch, built with our own Python 3.12.13 (the same version), adds his site-packages through one
# .pth line. Nothing is installed or written in his folders.
# Models: an HF cache of symlinks to his Qwen3.5-2B and Qwen3.8-27B folders, so snapshot_download(local_files_only)
# finds them; anything the hub writes lands in our cache folder.
# Caches (vLLM, Triton, Inductor, FlashInfer) go to our scratch.
# On another node (no node07 scratch), mirror_node07.sh first copies his venv and the two model folders to
# /scratch/$USER/yashas-anlp-env, and that copy is used instead.
set -euo pipefail
# Our own copy (mirror_node07.sh / push_env.sh) wherever this node has one; his node07 copy lost its models on
# 2026-10-22 and node14 has an incomplete one of his, so his is used only where ours is missing.
YENV=/scratch/$USER/yashas-anlp-env
[ -d "$YENV/venv" ] || YENV=/scratch/yashas.kotre/anlp-env
YSP=$YENV/venv/lib/python3.12/site-packages
ROOT=/scratch/$USER/failure-driven
VENV=$ROOT/venv
PY=${ANLP_PYTHON:-$HOME/.local/share/uv/python/cpython-3.12.13-linux-x86_64-gnu/bin/python3.12}
mkdir -p "$ROOT"
# Scratch cleanup may leave the directory and .pth file but remove its interpreter.
# Populate an existing directory without deleting its surviving files or packages.
[ -x "$VENV/bin/python" ] || "$PY" -m venv --without-pip "$VENV"
echo "import site; site.addsitedir('$YSP')" > "$VENV/lib/python3.12/site-packages/yashas_env.pth"  # follows YENV
# The trainer and judge runner start servers with the `vllm` command. The main guard is required: vLLM starts its
# engine with multiprocessing spawn, which re-imports this file in the child.
printf '#!%s\nimport sys\nfrom vllm.entrypoints.cli.main import main\nif __name__ == "__main__":\n    sys.exit(main())\n' \
    "$VENV/bin/python" > "$VENV/bin/vllm"
chmod +x "$VENV/bin/vllm"
mkdir -p "$ROOT/hf_home/hub"
for m in Qwen--Qwen3.5-2B Qwen--Qwen3.8-27B; do
    ln -sfn "$YENV/hf_cache/hub/models--$m" "$ROOT/hf_home/hub/models--$m"  # follows YENV
done
export PATH=$VENV/bin:$PATH HF_HOME=$ROOT/hf_home HF_HUB_OFFLINE=1 TOKENIZERS_PARALLELISM=false PYTHONUNBUFFERED=1
export VLLM_CACHE_ROOT=$ROOT/vllm_cache TRITON_CACHE_DIR=$ROOT/triton_cache TORCHINDUCTOR_CACHE_DIR=$ROOT/inductor_cache
export XDG_CACHE_HOME=$ROOT/xdg_cache FLASHINFER_WORKSPACE_BASE=$ROOT/flashinfer
"$VENV/bin/python" -c "import vllm, transformers, peft, torch; print('env: vllm', vllm.__version__, '| transformers', transformers.__version__, '| peft', peft.__version__, '| torch', torch.__version__)"
exec "$@"
