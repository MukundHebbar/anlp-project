#!/usr/bin/env python3
"""Generate zero-training baseline responses on Modal with vLLM.

Prompts are rendered locally by ``anlp_project.baseline`` and sent to one GPU
container; the container only runs vLLM and returns raw text, so what was sent is
exactly what is stored. Weights live in a Modal Volume so GPU time is never spent
downloading.

    # once, CPU only: cache both models' weights in the volume
    modal run scripts/modal_baseline.py::download
    # train pilot (100 per task), then the test baseline
    modal run scripts/modal_baseline.py::main --model qwen3.5-4b --split pilot
    modal run scripts/modal_baseline.py::main --model qwen3.8-27b --split test

Each run writes artifacts/baselines/final-v3/<split>/<model>/{responses.jsonl,
metadata.json} and then the deterministic scores.jsonl and summary.json.
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import modal

APP_NAME = "anlp-final-v3-baseline"
import os

# The weight cache; another workspace can point at its own copy (same Hugging Face layout).
VOLUME_NAME = os.environ.get("BASELINE_VOLUME", "anlp-final-v3-hf-cache")
HF_DIR = "/hf"
GPU = "H100"
GPU_TIMEOUT = 75 * 60  # hard stop per run (27B at 32k measured ~40 min), also a cost ceiling
# The 27B hybrid-attention model has one recurrent-state block per running sequence;
# with bf16 weights on 80 GB there are ~325, so vLLM's default of 1024 fails to start.
MAX_NUM_SEQS = 256

volume = modal.Volume.from_name(VOLUME_NAME, create_if_missing=True)
cpu_image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install("huggingface_hub[hf_transfer]")
    .env({"HF_HOME": HF_DIR, "HF_HUB_ENABLE_HF_TRANSFER": "1", "BASELINE_VOLUME": VOLUME_NAME})
)
gpu_image = (
    modal.Image.from_registry("nvidia/cuda:12.8.1-devel-ubuntu22.04", add_python="3.12")
    .entrypoint([])
    # Pinned so every workspace builds the same stack (the versions used by all 32k runs and the OPD trial).
    .uv_pip_install("vllm==0.30.0", "transformers==5.17.0", "huggingface_hub[hf_transfer]")
    .env({"HF_HOME": HF_DIR, "HF_HUB_ENABLE_HF_TRANSFER": "1", "BASELINE_VOLUME": VOLUME_NAME})
)
app = modal.App(APP_NAME)

WEIGHT_PATTERNS = ["*.json", "*.safetensors", "*.jinja", "*.txt", "*.model", "*.py"]


@app.function(image=cpu_image, volumes={HF_DIR: volume}, cpu=4, memory=8192, timeout=3 * 60 * 60)
def download_weights(repos: list[str]) -> dict:
    from huggingface_hub import snapshot_download

    out = {}
    for repo in repos:
        path = snapshot_download(repo, allow_patterns=WEIGHT_PATTERNS)
        size = sum(f.stat().st_size for f in Path(path).rglob("*") if f.is_file())
        if not Path(path).resolve().is_relative_to(Path(HF_DIR).resolve()):
            raise RuntimeError(f"weights landed outside the volume: {path}")
        out[repo] = {"path": path, "gib": round(size / 2**30, 2)}
        volume.commit()
    return out


@app.function(image=gpu_image, gpu=GPU, volumes={HF_DIR: volume}, cpu=8, memory=65536, timeout=GPU_TIMEOUT)
def generate(repo: str, prompts: list[str], sampling: dict, max_model_len: int, run_name: str) -> dict:
    """Run vLLM and return plain-Python results. Results are also saved to the volume
    before returning, and errors come back as text rather than unpicklable objects."""
    import traceback

    try:
        out = _generate(repo, prompts, sampling, max_model_len)
    except Exception:
        return {"error": traceback.format_exc()}
    path = Path(HF_DIR) / "outputs" / f"{run_name}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, ensure_ascii=False))
    volume.commit()
    out["runtime"]["volume_copy"] = f"outputs/{run_name}.json"
    return out


def _generate(repo: str, prompts: list[str], sampling: dict, max_model_len: int) -> dict:
    import os
    import subprocess
    import vllm
    from huggingface_hub import snapshot_download
    from vllm import LLM, SamplingParams

    os.environ["HF_HUB_OFFLINE"] = "1"
    started = time.time()
    local = snapshot_download(repo, allow_patterns=WEIGHT_PATTERNS, local_files_only=True)
    if not Path(local).resolve().is_relative_to(Path(HF_DIR).resolve()):
        raise RuntimeError(f"weights not found in the volume: {local}")
    engine = dict(model=local, tokenizer=local, dtype="bfloat16", max_model_len=max_model_len,
                  gpu_memory_utilization=0.90, max_num_seqs=MAX_NUM_SEQS, seed=sampling["seed"],
                  enable_prefix_caching=True)
    try:  # text-only serving: skip the vision encoder
        llm = LLM(**engine, language_model_only=True)
        text_only = "language_model_only"
    except TypeError:
        llm = LLM(**engine, limit_mm_per_prompt={"image": 0, "video": 0})
        text_only = "limit_mm_per_prompt=0"
    loaded = time.time()
    params = SamplingParams(temperature=sampling["temperature"], top_p=sampling["top_p"],
                            top_k=sampling["top_k"], max_tokens=sampling["max_tokens"],
                            seed=sampling["seed"])
    conversations = [[{"role": "user", "content": p}] for p in prompts]
    outputs = llm.chat(conversations, params, use_tqdm=False,
                       chat_template_kwargs={"enable_thinking": False})
    done = time.time()
    results = []
    for out in outputs:
        c = out.outputs[0]
        results.append({"text": str(c.text), "finish_reason": str(c.finish_reason),
                        "prompt_tokens": len(out.prompt_token_ids), "completion_tokens": len(c.token_ids)})
    gpu = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.used,memory.total", "--format=csv,noheader"],
                         capture_output=True, text=True).stdout.strip()
    return {
        "results": results,
        "runtime": {"vllm": str(vllm.__version__), "text_only_mode": text_only, "gpu": gpu,
                    "load_seconds": round(loaded - started, 1),
                    "generate_seconds": round(done - loaded, 1)},
    }


@app.local_entrypoint()
def download():
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    from anlp_project.baseline import MODELS

    print(json.dumps(download_weights.remote(list(MODELS.values())), indent=1))


@app.local_entrypoint()
def main(model: str, split: str = "pilot", tasks: str = "solve,judge,reconstruct", limit: int = 0,
         max_tokens: int = 8192, max_model_len: int = 0, protocol: str = "v2"):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    from anlp_project import baseline as b

    repo = b.MODELS[model]
    if protocol == "v2":  # the final protocol fixes its own cap; folders are named <model>-final
        sampling = dict(b.EVAL_SAMPLING)
        max_tokens, key = sampling["max_tokens"], f"{model}-final"
    else:
        key = b.run_key(model, max_tokens)
        sampling = {**b.SAMPLING, "max_tokens": max_tokens}
    max_model_len = max_model_len or max_tokens + 8192  # prompts are at most ~1k tokens
    directory = b.output_dir(split, key)
    if (directory / "responses.jsonl").exists():
        raise SystemExit(f"{directory} already has responses; move them aside to regenerate.")
    requests = b.build_requests(b.rows_for(split, tasks.split(","), limit))
    print(f"{model} {split}: {len(requests)} prompts -> {GPU}")
    run_name = f"{split}-{key}-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}"
    metadata = {
        "model": repo, "model_key": model, "split": split, "tasks": tasks.split(","),
        "run_key": key, "protocol": protocol, "n_prompts": len(requests), "limit": limit, "sampling": sampling,
        "chat_template_kwargs": {"enable_thinking": False}, "max_model_len": max_model_len, "max_num_seqs": MAX_NUM_SEQS,
        "prompt_files": {t: str(p.relative_to(b.PROMPTS_DIR.parent.parent)) for t, p in b.PROMPT_FILES.items()},
        "prompt_file_sha256": b.prompt_hashes(), "modal": {"app": APP_NAME, "gpu": GPU, "volume": VOLUME_NAME},
        "run_name": run_name, "started_utc": datetime.now(timezone.utc).isoformat(),
    }
    # Written before the GPU call so `collect` can finish the job from the volume copy
    # if this client disconnects (run with `modal run --detach`).
    directory.mkdir(parents=True, exist_ok=True)
    pending = directory / "pending.json"
    pending.write_text(json.dumps({"metadata": metadata, "requests": requests}, ensure_ascii=False))
    out = generate.remote(repo, [r["prompt"] for r in requests], sampling, max_model_len, run_name)
    if "error" in out:
        raise SystemExit(f"remote generation failed:\n{out['error']}")
    _write_outputs(b, split, key, out)


def _write_outputs(b, split: str, model: str, out: dict) -> None:
    directory = b.output_dir(split, model)
    pending = json.loads((directory / "pending.json").read_text())
    with (directory / "responses.jsonl").open("w", encoding="utf-8") as handle:
        for req, res in zip(pending["requests"], out["results"], strict=True):
            handle.write(json.dumps({**req, **res}, ensure_ascii=False) + "\n")
    metadata = {**pending["metadata"], "finished_utc": datetime.now(timezone.utc).isoformat(), **out["runtime"]}
    (directory / "metadata.json").write_text(json.dumps(metadata, indent=1) + "\n")
    (directory / "pending.json").unlink()
    summary = b.score_dir(split, model)
    print(json.dumps({"runtime": out["runtime"], "summary": summary}, indent=1))


@app.local_entrypoint()
def collect(model: str, split: str = "pilot", max_tokens: int = 8192, protocol: str = "v2"):
    """Finish a run from its volume copy (after a disconnect or a detached run)."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    from anlp_project import baseline as b

    key = f"{model}-final" if protocol == "v2" else b.run_key(model, max_tokens)
    directory = b.output_dir(split, key)
    run_name = json.loads((directory / "pending.json").read_text())["metadata"]["run_name"]
    data = b"".join(volume.read_file(f"outputs/{run_name}.json"))
    out = json.loads(data)
    out["runtime"]["volume_copy"] = f"outputs/{run_name}.json"
    _write_outputs(b, split, key, out)
