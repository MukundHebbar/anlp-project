#!/bin/bash
# CPU-only: build the Phase-3 inference environment (vLLM + math-verify) and cache Qwen3.5-2B on node scratch.
#   sbatch -w node08 phase3/turing/setup_env.sbatch   (from ~/anlp-project)
#SBATCH --job-name=p3-setup
#SBATCH --account=priyesh.shukla
#SBATCH --partition=u22
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2   # >2 CPUs on a CPU-only job adds gpu:1 billing
#SBATCH --mem=16G
#SBATCH --time=03:00:00
#SBATCH --output=logs/%x-%j.out

set -euo pipefail
ROOT="/scratch/$USER/anlp-p3"   # node-local NVMe scratch (read-only as /scratch/<node>/$USER from the login node)
export HF_HOME="$ROOT/hf_cache" UV_CACHE_DIR="$ROOT/uv_cache" UV_LINK_MODE=copy HF_HUB_ENABLE_HF_TRANSFER=1
UV="$HOME/.local/bin/uv"
mkdir -p "$ROOT"
echo "host $(hostname) root $ROOT job ${SLURM_JOB_ID:-none} $(date -u +%FT%TZ)"
cat /proc/driver/nvidia/version 2>/dev/null | head -1 || echo "no nvidia driver info"
timeout 15 curl -sI https://huggingface.co | head -1 || { echo "no internet on this node"; exit 3; }
df -h "$ROOT" | tail -1

# Same pins as the Modal image (scripts/modal_opd.py).
CHECK='import torch, vllm, transformers, peft, fla, math_verify, sys; sys.exit(0 if torch.version.cuda.startswith("12.") and vllm.__version__.startswith("0.30.0") and transformers.__version__ == "5.17.0" else 1)'
if "$ROOT/venv/bin/python" -c "$CHECK" 2>/dev/null; then
    echo "venv already complete; skipping install"
else
timeout 600 "$UV" venv --clear --python 3.12 "$ROOT/venv"
# Turing's driver (570, CUDA 12.8) cannot run the default CUDA 13 wheels, so use vLLM's cu129
# build and cu129 torch (CUDA 12.x minor-version compatibility).
timeout 3600 "$UV" pip install --python "$ROOT/venv/bin/python" \
    --extra-index-url https://wheels.vllm.ai/0.30.0/cu129 --torch-backend=cu129 \
    --index-strategy unsafe-best-match \
    "vllm==0.30.0+cu129" "transformers==5.17.0" "peft==0.21.1" "flash-linear-attention==0.5.2" \
    "huggingface_hub[hf_transfer]" sympy "math-verify[antlr4-13-2]"
"$ROOT/venv/bin/python" -c "import torch, sys; v=torch.version.cuda; print('torch', torch.__version__, 'cuda', v); sys.exit(0 if v and v.startswith('12.') else 4)"
fi
"$ROOT/venv/bin/python" - <<'EOF'
import importlib
for m in ("torch", "vllm", "transformers", "peft", "fla"):
    mod = importlib.import_module(m)
    print(m, getattr(mod, "__version__", "?"))
import torch; print("torch cuda build", torch.version.cuda)
EOF

for repo in Qwen/Qwen3.5-2B; do
    timeout 5400 "$ROOT/venv/bin/hf" download "$repo" --exclude "*.pth" --exclude "original/*" >/dev/null
    echo "cached $repo"
done
du -sh "$HF_HOME"/hub/* 2>/dev/null
echo "done $(date -u +%FT%TZ)"
