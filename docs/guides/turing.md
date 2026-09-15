---
name: iiit-gpu-cluster
description: Use when working with IIIT Hyderabad HPC/GPU clusters such as Turing or Ada, including SSH login, Slurm jobs, GPU allocation, storage strategy, rsync, interactive sessions, batch jobs, monitoring, accounting, quotas, and cluster-safe experiment workflows.
---

# IIIT GPU Cluster Usage Guide

## Overview

Use this skill for operating IIIT GPU clusters safely and reproducibly. Treat login nodes as control planes, Slurm allocations as chargeable compute, `/home` as small persistent storage, and scratch as large temporary job storage.

Always fail fast with explicit errors. Do not use silent fallbacks, fake paths, random CUDA versions, hidden recovery, or unlogged behavior changes.

## First Check

Before giving current cluster policy advice, prefer the latest local docs or official docs if available:

- Turing local docs: `instructions/turing_instructions.md`
- Ada local docs: `instructions/ada_instructions.md`
- Turing host: `turing.iiit.ac.in`
- Ada host: `ada.iiit.ac.in`

If official docs are unavailable, say so and base advice on local docs plus observed commands.

## Canonical Turing Identity

For Mukund's Turing work, always use this exact SSH identity:

```bash
ssh mukund.hebbar@turing.iiit.ac.in
```

The local `turing` SSH alias must resolve to that same host and user. Verify before cluster work:

```bash
ssh -G turing | awk '/^(hostname|user) / {print}'
ssh -o BatchMode=yes turing 'printf "user=%s host=%s\n" "$USER" "$(hostname)"'
```

Expected remote identity: `user=mukund.hebbar host=turing.iiit.ac.in`.

Never infer the remote username from the workstation username. Never put a password in a skill,
repository, SSH config, shell command, process argument, log, or environment variable. Prefer the
existing SSH key. If key authentication must be bootstrapped, run
`ssh-copy-id -o BatchMode=no mukund.hebbar@turing.iiit.ac.in` interactively so the password is
entered only at the terminal prompt, then require `BatchMode=yes` to pass.

## Cluster Selection

Use the cluster specified by the user or the project docs. If the user has not specified a cluster, prefer the local instruction files before assuming.

Turing defaults:

```bash
ssh mukund.hebbar@turing.iiit.ac.in
sinteractive -c 16 -p u22 -A <slurm-account> -g 1
```

Turing facts from local docs:

- Login/master node has no GPU.
- Compute nodes include RTX 6000, L40S, and A100 GPUs.
- Partition: `u22`
- Slurm account depends on the project/group allocation. Verify the account from local docs or the professor/admin-provided instructions before submitting jobs.
- `/home/$USER` quota: 50 GB
- `/scratch/nodeXX` is temporary local NVMe on compute nodes.
- Observed on 2026-05-17: `u22/python/3.12.4` may point to missing `/usr/local/apps/python-3.12.4`; verify before relying on it.
- Observed on 2026-05-17: user-local `uv python install 3.12` works and created Python 3.12.13 under `$HOME/.local/share/uv/python`.

Ada is separate. Do not mix Ada commands with Turing commands. Ada uses different hosts, partitions, accounts, modules, limits, storage, and older GPUs.

## What Counts as GPU Usage or Charge

"Charged" means Slurm resource accounting against the specified Slurm account, not necessarily direct money charged to the user.

Usually accounted:

- Running interactive Slurm allocations after resources are granted.
- Running batch jobs after resources are granted.
- Requested CPUs, GPUs, memory, and elapsed wall-clock allocation time.
- Allocated GPU time even if Python accidentally runs on CPU.

Usually not accounted as GPU usage:

- Plain SSH login to the master/login node.
- Editing files, creating folders, checking queues, or syncing code.
- Waiting in the Slurm queue before allocation.
- Jobs that fail before allocation.

Always explain the difference:

- **GPU allocated**: Slurm granted `--gres=gpu:1` or `-g 1`.
- **GPU actually used**: `nvidia-smi` shows activity, or framework checks confirm CUDA usage.

Verification:

```bash
hostname
echo "$CUDA_VISIBLE_DEVICES"
nvidia-smi
uv run python -c "import torch; print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0))"
```

## Login Node Rules

Use login node for:

- SSH access
- `mkdir`, `ls`, `cd`, `vim`, `nano`
- Git clone/pull
- `rsync` / `scp`
- Checking jobs with `squeue`
- Submitting jobs with `sbatch`
- Reading logs

Avoid on login node:

- Training
- Inference loops
- Dataset preprocessing that uses high CPU/RAM
- Downloading or extracting very large files without checking storage
- Long-running Python scripts
- Repeated unconstrained `uv run` or `uv sync` when the login node is resource-limited.
- Treating login-node `torch` import failures as final GPU failures before testing inside Slurm allocation.

Observed login-node caveats:

- `uv` can fail with `failed to initialize global rayon pool`, `Resource temporarily unavailable`, or small memory allocation failures.
- `torch` may fail to import on the login node with `libtorch_cuda.so: failed to map segment from shared object`, while working on a compute node.
- Heavy module help commands can hang on the login node if they import large ML frameworks. Prefer unit tests, config-only validation, or a short Slurm allocation for import-heavy checks.
- If login-node checks hit these errors, retry with conservative `uv` settings or move checks into a short interactive allocation.

Conservative `uv` settings:

```bash
export UV_CONCURRENT_DOWNLOADS=1
export UV_CONCURRENT_BUILDS=1
export UV_CONCURRENT_INSTALLS=1
export UV_LINK_MODE=copy
```

Use these settings by default in Slurm scripts for Python ML projects on Turing.

## Python And uv On Turing

Do not assume the documented Python module works. Verify first:

```bash
module load u22/python/3.12.4
module show u22/python/3.12.4
ls -la /usr/local/apps/python-3.12.4/bin
python3 --version
```

If the module target path is missing or Python is still 3.9/3.10, use user-local `uv`:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"
uv --version
uv python install 3.12
uv python list
```

For projects with `pyproject.toml` and `uv.lock`:

```bash
cd <project>
export PATH="$HOME/.local/bin:$PATH"
export UV_CONCURRENT_DOWNLOADS=1
export UV_CONCURRENT_BUILDS=1
export UV_CONCURRENT_INSTALLS=1
export UV_LINK_MODE=copy
uv sync
uv run python -c "import sys; print(sys.executable); print(sys.version)"
```

If unconstrained `uv sync` fails on the login node with resource errors, retry with conservative `uv` settings or run setup/checks inside a short Slurm allocation.

## Storage Strategy

Use `/home` only for small persistent artifacts:

- Source code
- Slurm scripts
- Config files
- Small logs and summaries
- Final LoRA adapters if small
- Minimal reproducibility metadata

Avoid storing these in `/home`:

- Full model checkpoints
- Large datasets
- Hugging Face model cache
- Rollout dumps
- Large screenshot/video logs
- Repeated redundant checkpoints
- `.venv` if it grows too large

Use scratch for large temporary job data. On a Turing compute node, its own local NVMe is mounted
at `/scratch/$USER`. From the login node, a compute node's storage may be visible as
`/scratch/nodeXX/$USER`. Do not build a compute-node path as `/scratch/$(hostname)/$USER`.

```bash
SCRATCH_DIR="/scratch/$USER/<project-name>/$SLURM_JOB_ID"
mkdir -p "$SCRATCH_DIR"
export HF_HOME="$SCRATCH_DIR/hf_cache"
export TRANSFORMERS_CACHE="$SCRATCH_DIR/hf_cache"
export HF_DATASETS_CACHE="$SCRATCH_DIR/hf_datasets"
```

Important scratch rules:

- Scratch is temporary and not a backup.
- Copy important final artifacts back to `/home`.
- Delete unneeded scratch data at job end.
- Never assume scratch files will remain long-term.

End-of-job artifact pattern:

```bash
OUT_DIR="$HOME/<project-name>/outputs/${SLURM_JOB_NAME}-${SLURM_JOB_ID}"
mkdir -p "$OUT_DIR"
cp "$CONFIG_FILE" "$OUT_DIR/"
cp -r "$SCRATCH_DIR"/metrics "$OUT_DIR/" 2>/dev/null || true
cp -r "$SCRATCH_DIR"/adapters "$OUT_DIR/" 2>/dev/null || true
```

Use `|| true` only for optional artifact copies that are explicitly non-critical. Never use it to hide training, evaluation, CUDA, Slurm, or data failures.

## File Transfer

Prefer `rsync` because it resumes interrupted transfers:

```bash
rsync -avz --exclude '.venv' --exclude '__pycache__' local_dir/ turing:~/project-dir/
rsync -avz turing:~/project-dir/outputs/ ./outputs/
```

Do not sync caches, virtualenvs, huge checkpoints, or generated scratch data unless explicitly needed.

## Interactive Workflow

Use interactive sessions for smoke tests and debugging only:

```bash
ssh turing
cd ~/<project-dir>
sinteractive -c 16 -p u22 -A <slurm-account> -g 1
module load u22/cuda/12.4
module load u22/python/3.12.4
hostname
nvidia-smi
```

Exit when done:

```bash
exit
```

If inside both a Slurm session and SSH, one `exit` leaves compute allocation and another exits SSH.

Avoid leaving interactive sessions idle. They may continue accounting resources.

## Batch Workflow

Use `sbatch` for real runs and anything that should survive SSH disconnects.

Minimal Turing template:

```bash
#!/bin/bash
#SBATCH -A <slurm-account>
#SBATCH -p u22
#SBATCH -n 16
#SBATCH --gres=gpu:1
#SBATCH --mem-per-cpu=4096
#SBATCH --time=02:00:00
#SBATCH --output=logs/slurm-%x-%j.out
#SBATCH --error=logs/slurm-%x-%j.err
#SBATCH --job-name=job-name

set -euo pipefail

module load u22/cuda/12.4

cd "$HOME/<project-dir>"
export PATH="$HOME/.local/bin:$PATH"
export UV_CONCURRENT_DOWNLOADS=1
export UV_CONCURRENT_BUILDS=1
export UV_CONCURRENT_INSTALLS=1
export UV_LINK_MODE=copy
mkdir -p logs outputs

echo "job_id=${SLURM_JOB_ID}"
echo "job_name=${SLURM_JOB_NAME}"
echo "host=$(hostname)"
echo "cuda_visible_devices=${CUDA_VISIBLE_DEVICES:-unset}"
echo "start_time=$(date --iso-8601=seconds)"

nvidia-smi

SCRATCH_DIR="/scratch/$USER/${SLURM_JOB_NAME}/${SLURM_JOB_ID}"
mkdir -p "$SCRATCH_DIR"
export HF_HOME="$SCRATCH_DIR/hf_cache"
export TRANSFORMERS_CACHE="$SCRATCH_DIR/hf_cache"
export HF_DATASETS_CACHE="$SCRATCH_DIR/hf_datasets"

nvidia-smi --query-gpu=timestamp,index,name,utilization.gpu,memory.used,memory.total,power.draw,temperature.gpu \
  --format=csv -l 10 > "logs/gpu-${SLURM_JOB_ID}.csv" &
GPU_MONITOR_PID=$!

# Replace with the real command.
uv run python -m your_module

kill "$GPU_MONITOR_PID" || true
echo "end_time=$(date --iso-8601=seconds)"
```

Submit:

```bash
sbatch scripts/run_turing.sh
```

Parameterized submit:

```bash
sbatch --export=ALL,CONFIG=configs/experiment.yaml scripts/run_turing.sh
```

## Monitoring Commands

List jobs:

```bash
squeue -u mukund.hebbar
```

Detailed job info:

```bash
scontrol show job <jobid>
```

Completed job accounting:

```bash
sacct -j <jobid> --format=user,jobid,jobname,partition,state,time,start,end,elapsed,alloctres,ncpus,nodelist
```

Watch logs:

```bash
tail -f logs/slurm-<jobname>-<jobid>.out
tail -f logs/slurm-<jobname>-<jobid>.err
```

Cancel:

```bash
scancel <jobid>
scancel -u "$USER"
```

Only use `scancel -u "$USER"` when intentionally cancelling all of the user's jobs.

## Experiment Logging Requirements

For ML/RL/LoRA jobs, record at least:

- Git commit or source snapshot
- Config file path and full config copy
- Slurm job id
- Hostname and GPU model
- CUDA visible devices
- Start/end time
- Python, CUDA, torch, transformers, trl, peft versions
- Seed
- Dataset/task name
- Reward metrics
- Invalid action count
- No-op count
- Episode length
- Success rate
- Checkpoint/adapter path
- GPU utilization CSV

Why: cluster jobs are expensive and non-reproducible without config, code, environment, and metrics.

## ML / RL / LoRA Experiment Pattern

For ML experiments on the cluster:

1. Start with the smallest debug run that exercises model load, data load, reward/eval logic, logging, and artifact save.
2. Confirm CUDA is actually used inside a Slurm allocation.
3. Run one baseline config before sweeping.
4. Sweep one variable at a time: learning rate, LoRA rank, batch size, rollout length, reward setting, or dataset/task.
5. Use `sbatch` for real experiments and sweeps.
6. Keep final adapters, summaries, configs, and logs in `/home`; keep caches, rollouts, screenshots, and large temporary files in scratch.

For agentic/RL systems, never silently convert invalid actions, parser failures, missing tools, or failed environment steps into benign no-ops. If a fallback is intentional, log it explicitly with a reason such as `fallback_reason`.

Project-specific notes live in separate files next to this skill. For example, Liquid browser-control details are in `browser-control-liquid-notes.md`; do not copy those project-specific assumptions into this general guide.

When syncing local patches back to a cluster, run `rsync` from the laptop/workstation, not from inside the cluster SSH session:

```bash
rsync -avz \
  --exclude '.venv' \
  --exclude '__pycache__' \
  --exclude '.ruff_cache' \
  --exclude 'logs' \
  --exclude 'outputs' \
  --exclude 'runs' \
  --exclude 'reports' \
  /path/to/local/project/ \
  <user>@<cluster-host>:~/path/to/remote/project/
```

## Failure Handling

When anything fails:

1. Stop unsafe progression.
2. Capture the exact command, job id, node, config, and error.
3. Identify the layer: SSH/VPN, Slurm account, partition/QoS, modules, CUDA, Python env, storage quota, dataset, model cache, training code, remote service, or logging.
4. Fix the root cause explicitly.
5. Re-run the smallest failing command.
6. Resume only after verification succeeds.

Never solve cluster failures by random account changes, random partition changes, unverified CUDA downgrades, hidden defaults, fake data, or broad retries without root-cause evidence.

## Before Stopping Work Or Sleeping

Do not leave Slurm allocations running unattended unless intentionally running a batch experiment.

Check and cancel jobs:

```bash
squeue -u mukund.hebbar
scancel -u mukund.hebbar   # only when intentionally cancelling all of your jobs
squeue -u mukund.hebbar
```

Clean stopped shell jobs on the login node:

```bash
jobs
kill %1       # if exactly one stopped job is listed
kill $(jobs -p) 2>/dev/null || true
jobs
```

Then logout:

```bash
exit
```

Safe-to-sleep state: `squeue -u mukund.hebbar` is empty and `jobs` shows no stopped local
commands.

## Default Advice

For Turing:

- Use `mukund.hebbar@turing.iiit.ac.in`; do not substitute the workstation username.
- SSH is for access, not GPU compute.
- `sinteractive` is for quick debugging.
- `sbatch` is for real experiments.
- `/home` is permanent but small.
- Scratch is large but temporary.
- Requested Slurm resources are what matter for accounting.
- Always exit/cancel unused allocations.
- Always log enough to reproduce the run.
