#!/bin/bash
# One-time environment on a Jarvislabs GPU container. Everything lives under /home (kept across pause/resume).
#   bash phase3/setup_instance.sh [cu129]
# Pins match scripts/turing/setup_env.sbatch. Pass cu129 when the driver is older than CUDA 13.
set -euo pipefail
export HF_HOME=/home/hf UV_CACHE_DIR=/home/uv_cache HF_HUB_ENABLE_HF_TRANSFER=1
command -v uv >/dev/null || pip install -q uv
if ! /home/venv/bin/python -c 'import vllm, fla, math_verify' 2>/dev/null; then
    uv venv --clear --python 3.12 /home/venv
    extra=()
    if [ "${1:-}" = "cu129" ]; then
        extra=(--extra-index-url https://wheels.vllm.ai/0.30.0/cu129 --torch-backend=cu129 --index-strategy unsafe-best-match)
        vllm_pin="vllm==0.30.0+cu129"
    else
        vllm_pin="vllm==0.30.0"
    fi
    uv pip install --python /home/venv/bin/python "${extra[@]}" "$vllm_pin" "transformers==5.17.0" "peft==0.21.1" \
        "flash-linear-attention==0.5.2" "huggingface_hub[hf_transfer]" sympy "math-verify[antlr4-13-2]"
fi
/home/venv/bin/python -c 'import torch, vllm, transformers; print("torch", torch.__version__, torch.version.cuda, "vllm", vllm.__version__, "transformers", transformers.__version__, "gpu", torch.cuda.get_device_name(0))'
/home/venv/bin/hf download Qwen/Qwen3.5-2B --exclude "*.pth" --exclude "original/*" >/dev/null
echo "setup done"
