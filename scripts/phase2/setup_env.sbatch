#!/bin/bash
# CPU-only: our own vLLM environment and model cache on node07's local scratch, with the same pins as
# scripts/turing/setup_env.sbatch (the shared copy under /scratch/mukund.hebbar was purged on 2026-10-11).
#   sbatch scripts/phase2/setup_env.sbatch
#SBATCH --job-name=p2-setup
#SBATCH --account=priyesh.shukla
#SBATCH --partition=u22
#SBATCH --nodelist=node07
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2   # >2 CPUs on a CPU-only job adds gpu:1 billing
#SBATCH --mem=16G
#SBATCH --time=03:00:00
#SBATCH --output=runs-out/slurm-%x-%j.out

set -euo pipefail
ROOT="/scratch/$USER/anlp-env"
export HF_HOME="$ROOT/hf_cache" UV_CACHE_DIR="$ROOT/uv_cache" UV_LINK_MODE=copy HF_HUB_ENABLE_HF_TRANSFER=1
export UV_PYTHON_INSTALL_DIR="$ROOT/python"
UV="$HOME/.local/bin/uv"
mkdir -p "$ROOT"
echo "host $(hostname) root $ROOT job ${SLURM_JOB_ID:-none} $(date -u +%FT%TZ)"
timeout 15 curl -sI https://huggingface.co | head -1 || { echo "no internet on this node"; exit 3; }

CHECK='import torch, vllm, transformers, peft, fla, sys; sys.exit(0 if torch.version.cuda.startswith("12.") and vllm.__version__.startswith("0.30.0") and transformers.__version__ == "5.17.0" else 1)'
if "$ROOT/venv/bin/python" -c "$CHECK" 2>/dev/null; then
    echo "venv already complete; skipping install"
else
    timeout 900 "$UV" venv --clear --python 3.12 "$ROOT/venv"
    # Turing's driver (CUDA 12.8) cannot run the default CUDA 13 wheels: vLLM's cu129 build and cu129 torch.
    timeout 3600 "$UV" pip install --python "$ROOT/venv/bin/python" \
        --extra-index-url https://wheels.vllm.ai/0.30.0/cu129 --torch-backend=cu129 \
        --index-strategy unsafe-best-match \
        "vllm==0.30.0+cu129" "transformers==5.17.0" "peft==0.21.1" "flash-linear-attention==0.5.2" \
        "huggingface_hub[hf_transfer]" "math-verify[antlr4-13-2]>=0.9.0" "sympy>=1.14.0"
fi
"$ROOT/venv/bin/python" -c "$CHECK" && echo "venv ok"

for repo in ${REPOS:-Qwen/Qwen3.5-2B Qwen/Qwen3.8-27B}; do  # e.g. REPOS=Qwen/Qwen3.5-9B sbatch ...
    timeout 5400 "$ROOT/venv/bin/hf" download "$repo" --exclude "*.pth" --exclude "original/*" >/dev/null
    echo "cached $repo"
done
du -sh "$HF_HOME"/hub/* 2>/dev/null
echo "done $(date -u +%FT%TZ)"
