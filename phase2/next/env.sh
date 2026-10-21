# Shared environment for phase2/next jobs (sourced by the sbatch files).
ENVROOT=${ENVROOT:-/scratch/$USER/anlp-env}
MINE=/scratch/$USER/phase2
mkdir -p "$MINE"
export PATH=$ENVROOT/venv/bin:$PATH HF_HOME=$MINE/hf_home HF_HUB_OFFLINE=1 TOKENIZERS_PARALLELISM=false PYTHONUNBUFFERED=1
export VLLM_CACHE_ROOT=$MINE/vllm_cache TRITON_CACHE_DIR=$MINE/triton_cache TORCHINDUCTOR_CACHE_DIR=$MINE/inductor_cache
export XDG_CACHE_HOME=$MINE/xdg_cache FLASHINFER_WORKSPACE_BASE=$MINE/flashinfer
BASE=$(ls -d $ENVROOT/hf_cache/hub/models--Qwen--Qwen3.5-2B/snapshots/*/ | head -1)
echo "job ${SLURM_JOB_ID:-none} on $(hostname) gpus ${CUDA_VISIBLE_DEVICES:-none} start $(date -u +%FT%TZ)"
