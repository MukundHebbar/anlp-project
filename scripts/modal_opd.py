#!/usr/bin/env python3
"""On-policy distillation (reverse KL) on Modal: one container, two H100s.

GPU 1: teacher vLLM server (Qwen3.8-27B bf16), used only to score tokens.
GPU 0: student vLLM server (Qwen3.5-2B + runtime LoRA) for rollouts, and the PEFT trainer.
Each step: rollouts -> teacher log-probs -> one LoRA update -> adapter loaded into vLLM.

    modal run scripts/modal_opd.py::download                       # CPU: cache weights
    modal run --detach scripts/modal_opd.py::probe --task solve    # 2 steps, reports memory/timing
    modal run --detach scripts/modal_opd.py::train --task solve --steps 16
    modal run --detach scripts/modal_opd.py::evaluate --task solve --adapter <run>/adapters/step16
    modal run scripts/modal_opd.py::collect --run <run>            # fetch metrics after a disconnect

Robust variant (survives a lost or killed client): deploy once, then spawn and fetch.

    modal deploy scripts/modal_opd.py
    modal run scripts/modal_opd.py::spawn_eval --task judge --adapter <run>/adapters/step14
    modal run scripts/modal_opd.py::fetch_eval --task judge --adapter <run>/adapters/step14
    modal run scripts/modal_opd.py::spawn_train --task reconstruct --steps 6 --kl-beta 0.1 --label kl0.1

OPD_VOLUME selects the workspace's Volume (default anlp-opd-cache). All results are written
to the Volume as they are produced, so a lost client loses nothing.
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import modal

import os

# Weight/output volume; a workspace can use its own copy (same Hugging Face layout).
VOLUME_NAME = os.environ.get("OPD_VOLUME", "anlp-opd-cache")
HF_DIR = "/hf"
STUDENT = "Qwen/Qwen3.5-2B"
TEACHER = "Qwen/Qwen3.8-27B"
WEIGHT_PATTERNS = ["*.json", "*.safetensors", "*.jinja", "*.txt", "*.model", "*.py"]
LOCAL_OUT = Path(__file__).resolve().parents[1] / "artifacts" / "opd"

volume = modal.Volume.from_name(VOLUME_NAME, create_if_missing=True)
cpu_image = (modal.Image.debian_slim(python_version="3.12").pip_install("huggingface_hub[hf_transfer]")
             .env({"HF_HOME": HF_DIR, "HF_HUB_ENABLE_HF_TRANSFER": "1"}))
gpu_image = (
    modal.Image.from_registry("nvidia/cuda:12.8.1-devel-ubuntu22.04", add_python="3.12")
    .entrypoint([])
    .uv_pip_install("vllm==0.30.0", "transformers==5.17.0", "peft==0.21.1", "flash-linear-attention==0.5.2",
                    "huggingface_hub[hf_transfer]")
    .env({"HF_HOME": HF_DIR, "HF_HUB_OFFLINE": "1", "TOKENIZERS_PARALLELISM": "false", "OPD_VOLUME": VOLUME_NAME})
)
app = modal.App("anlp-opd")


def _snapshot(repo: str) -> str:
    from huggingface_hub import snapshot_download

    path = snapshot_download(repo, allow_patterns=WEIGHT_PATTERNS, local_files_only=True)
    if not Path(path).resolve().is_relative_to(Path(HF_DIR).resolve()):
        raise RuntimeError(f"weights not in the volume: {path}")
    return path


@app.function(image=cpu_image, volumes={HF_DIR: volume}, cpu=4, memory=8192, timeout=3 * 3600)
def download_weights() -> dict:
    from huggingface_hub import snapshot_download

    out = {}
    for repo in (STUDENT, TEACHER):
        path = snapshot_download(repo, allow_patterns=WEIGHT_PATTERNS)
        if not Path(path).resolve().is_relative_to(Path(HF_DIR).resolve()):
            raise RuntimeError(f"weights landed outside the volume: {path}")
        out[repo] = round(sum(f.stat().st_size for f in Path(path).rglob("*") if f.is_file()) / 2**30, 2)
        volume.commit()
    return out


# ----------------------------------------------------------------------------- training

def _train(task: str, prompts: list[dict], cfg: dict, run_name: str, steps: int, probe: bool,
           resume_from: str | None = None, start_step: int = 0) -> dict:
    """The loop lives in src/anlp_project/opd_train.py (shared with the Turing runner).
    ``resume_from``: an adapter path under /hf/opd to continue from; steps are numbered from
    ``start_step + 1``. Modal runs do not save optimiser state, so AdamW restarts from zero moments."""
    from opd_train import run_opd  # shipped into the image (see opd_image)

    res = run_opd(task, prompts, cfg, Path(HF_DIR) / "opd" / run_name, _snapshot(STUDENT), _snapshot(TEACHER),
                  steps=steps, meta={"probe": probe}, teacher_gpus="1", student_gpu="0",
                  resume_from=str(Path(HF_DIR) / "opd" / resume_from) if resume_from else None,
                  start_step=start_step, commit=volume.commit)
    return {"run": run_name, **res}


_SRC = Path(__file__).resolve().parents[1] / "src" / "anlp_project"
opd_image = (gpu_image.add_local_file(_SRC / "opd_monitor.py", "/root/opd_monitor.py")
             .add_local_file(_SRC / "student_models.py", "/root/student_models.py")
             .add_local_file(_SRC / "opd_train.py", "/root/opd_train.py"))


@app.function(image=opd_image, gpu="H100:2", volumes={HF_DIR: volume}, cpu=8, memory=98304, timeout=40 * 60)
def probe_remote(task: str, prompts: list[dict], cfg: dict, run_name: str) -> dict:
    return _train(task, prompts, cfg, run_name, steps=2, probe=True)


@app.function(image=opd_image, gpu="H100:2", volumes={HF_DIR: volume}, cpu=8, memory=98304, timeout=110 * 60)
def train_remote(task: str, prompts: list[dict], cfg: dict, run_name: str, steps: int,
                 resume_from: str | None = None, start_step: int = 0) -> dict:
    return _train(task, prompts, cfg, run_name, steps=steps, probe=False, resume_from=resume_from, start_step=start_step)


# ----------------------------------------------------------------------------- evaluation

@app.function(image=opd_image, gpu="H100:2", volumes={HF_DIR: volume}, cpu=8, memory=98304, timeout=32 * 60)
def short_train_remote(task: str, prompts: list[dict], cfg: dict, run_name: str, steps: int) -> dict:
    """Short fix trials with a tight hard timeout (a cost ceiling on small free-tier budgets)."""
    return _train(task, prompts, cfg, run_name, steps=steps, probe=False)


@app.function(image=gpu_image, gpu="H100", volumes={HF_DIR: volume}, cpu=8, memory=65536, timeout=35 * 60)
def evaluate_remote(prompts: list[str], adapter: str | None, sampling: dict, run_name: str) -> dict:
    import traceback

    try:
        from vllm import LLM, SamplingParams
        from vllm.lora.request import LoRARequest

        llm = LLM(model=_snapshot(STUDENT), dtype="bfloat16", language_model_only=True, max_model_len=sampling["max_tokens"] + 8192,
                  gpu_memory_utilization=0.90, max_num_seqs=256, seed=sampling["seed"], enable_lora=adapter is not None,
                  max_lora_rank=64)
        lora = LoRARequest("trained", 1, str(Path(HF_DIR) / "opd" / adapter)) if adapter else None
        params = SamplingParams(temperature=sampling["temperature"], top_p=sampling["top_p"], top_k=sampling["top_k"],
                                max_tokens=sampling["max_tokens"], seed=sampling["seed"])
        outs = llm.chat([[{"role": "user", "content": p}] for p in prompts], params, lora_request=lora, use_tqdm=False,
                        chat_template_kwargs={"enable_thinking": False})
        res = [{"text": str(o.outputs[0].text), "finish_reason": str(o.outputs[0].finish_reason),
                "completion_tokens": len(o.outputs[0].token_ids)} for o in outs]
        path = Path(HF_DIR) / "opd" / "evals" / f"{run_name}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(res))
        volume.commit()
        return {"results": res}
    except Exception:
        return {"error": traceback.format_exc()}


# ----------------------------------------------------------------------------- local side

def _local():
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    from anlp_project import baseline, opd
    return baseline, opd


@app.local_entrypoint()
def download():
    print(download_weights.remote())


def _run_training(task: str, steps: int, probe_mode: bool):
    _, opd = _local()
    prompts = opd.slice_prompts(task, "train")
    need = (2 if probe_mode else steps) * opd.TRIAL_CONFIG["prompts_per_step"]
    run_name = f"{'probe' if probe_mode else 'trial'}-{task}-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}"
    print(f"{run_name}: {need} of {len(prompts)} training prompts")
    fn = probe_remote if probe_mode else train_remote
    args = (task, prompts[:need], opd.TRIAL_CONFIG, run_name) + (() if probe_mode else (steps,))
    res = fn.remote(*args)
    local = LOCAL_OUT / run_name
    local.mkdir(parents=True, exist_ok=True)
    (local / "result.json").write_text(json.dumps(res, indent=1))
    print("\n".join(res.get("events", [])))
    print(res.get("error", "")[-3000:])


@app.local_entrypoint()
def probe(task: str = "solve"):
    _run_training(task, 2, True)


@app.local_entrypoint()
def train(task: str = "solve", steps: int = 16):
    _run_training(task, steps, False)


@app.local_entrypoint()
def resume(task: str, parent: str, from_step: int, steps: int):
    """Continue a stopped run from <parent>/adapters/step<from_step> for ``steps`` more steps,
    on the prompts the original run would have used next."""
    _, opd = _local()
    B = opd.TRIAL_CONFIG["prompts_per_step"]
    prompts = opd.slice_prompts(task, "train")[from_step * B:(from_step + steps) * B]
    run_name = f"{parent}-resume{from_step}"
    print(f"{run_name}: steps {from_step + 1}-{from_step + steps} on {len(prompts)} prompts")
    res = train_remote.remote(task, prompts, opd.TRIAL_CONFIG, run_name, steps,
                              resume_from=f"{parent}/adapters/step{from_step}", start_step=from_step)
    local = LOCAL_OUT / run_name
    local.mkdir(parents=True, exist_ok=True)
    (local / "result.json").write_text(json.dumps(res, indent=1))
    print("\n".join(res.get("events", [])))
    print(res.get("error", "")[-3000:])


def _eval_request(task, adapter, label, temperature, top_p, top_k):
    baseline, opd = _local()
    tasks = task.split(",")  # several dev slices can share one container
    rows = [r for t in tasks for r in opd.slice_rows(t, "dev")]
    sampling = dict(baseline.EVAL_SAMPLING)  # final protocol v2
    if temperature >= 0:
        sampling["temperature"] = temperature
    if top_p >= 0:
        sampling["top_p"] = top_p
    if top_k != -2:
        sampling["top_k"] = top_k  # 0 disables top-k in vLLM
    label = label or ("base" if not adapter else adapter.replace("/", "_"))
    run_name = f"dev-{'+'.join(tasks)}-{label}"
    return rows, [baseline.render_prompt(r) for r in rows], sampling, run_name


def _write_eval(rows, results, adapter, sampling, run_name):
    baseline, _ = _local()
    d = LOCAL_OUT / "evals" / run_name
    d.mkdir(parents=True, exist_ok=True)
    scores = [baseline.score_response(r, x) for r, x in zip(rows, results, strict=True)]
    with (d / "responses.jsonl").open("w") as fh:
        for r, x in zip(rows, results):
            fh.write(json.dumps({"uid": r["uid"], **x}, ensure_ascii=False) + "\n")
    with (d / "scores.jsonl").open("w") as fh:
        for sc in scores:
            fh.write(json.dumps(sc, ensure_ascii=False) + "\n")
    summary = baseline.summarize(scores)
    (d / "summary.json").write_text(json.dumps({"adapter": adapter or None, "sampling": sampling, **summary}, indent=1))
    print(json.dumps(summary, indent=1))


@app.local_entrypoint()
def evaluate(task: str = "solve", adapter: str = "", label: str = "", temperature: float = -1.0,
             top_p: float = -1.0, top_k: int = -2):
    """Final protocol v2 by default (T 1.0, top_p 1.0, top_k off, 32k). Overrides are for diagnostics only.
    Runs attached to this client; prefer spawn_eval + fetch_eval, which survive a lost client."""
    rows, prompts, sampling, run_name = _eval_request(task, adapter, label, temperature, top_p, top_k)
    res = evaluate_remote.remote(prompts, adapter or None, sampling, run_name)
    if "error" in res:
        raise SystemExit(res["error"])
    _write_eval(rows, res["results"], adapter, sampling, run_name)


@app.local_entrypoint()
def spawn_train(task: str = "reconstruct", steps: int = 6, drop_truncated: bool = False, kl_beta: float = 0.0,
                label: str = ""):
    """Start a short fix trial on the deployed app and exit; progress is in the volume (opd/<run>/events.log)."""
    _, opd = _local()
    cfg = {**opd.TRIAL_CONFIG, "drop_truncated": drop_truncated, "kl_anchor_beta": kl_beta}
    prompts = opd.slice_prompts(task, "train")[:steps * cfg["prompts_per_step"]]
    run_name = f"fix-{task}-{label or 'x'}-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}"
    call = modal.Function.from_name("anlp-opd", "short_train_remote").spawn(task, prompts, cfg, run_name, steps)
    print(f"spawned {run_name}: call {call.object_id}; drop_truncated={drop_truncated} kl_beta={kl_beta}")


@app.local_entrypoint()
def spawn_eval(task: str = "solve", adapter: str = "", label: str = ""):
    """Start an evaluation on the *deployed* app (`modal deploy scripts/modal_opd.py`) and exit at once.
    The call runs on Modal regardless of this client; results land in the volume (see fetch_eval)."""
    rows, prompts, sampling, run_name = _eval_request(task, adapter, label, -1.0, -1.0, -2)
    fn = modal.Function.from_name("anlp-opd", "evaluate_remote")
    call = fn.spawn(prompts, adapter or None, sampling, run_name)
    print(f"spawned {run_name}: call {call.object_id}")


@app.local_entrypoint()
def fetch_eval(task: str = "solve", adapter: str = "", label: str = ""):
    """Score a finished evaluation from its volume copy (opd/evals/<run>.json)."""
    rows, _, sampling, run_name = _eval_request(task, adapter, label, -1.0, -1.0, -2)
    results = json.loads(b"".join(volume.read_file(f"opd/evals/{run_name}.json")))
    _write_eval(rows, results, adapter, sampling, run_name)


@app.local_entrypoint()
def collect(run: str):
    """Fetch a run's metrics and events from the volume."""
    local = LOCAL_OUT / run
    local.mkdir(parents=True, exist_ok=True)
    for name in ("metrics.jsonl", "events.log", "config.json", "student-server.log", "teacher-server.log"):
        try:
            (local / name).write_bytes(b"".join(volume.read_file(f"opd/{run}/{name}")))
            print("fetched", name)
        except Exception as e:
            print("missing", name, type(e).__name__)
