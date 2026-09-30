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


# ----------------------------------------------------------------------------- servers

def _post(port: int, path: str, body: dict, timeout: float = 3600) -> dict:
    import urllib.request

    req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read()
    return json.loads(raw) if raw.strip().startswith(b"{") else {"text": raw.decode()}


def _serve(path: str, name: str, port: int, gpu: str, args: list[str], log_dir: Path, env_extra: dict):
    import os
    import subprocess

    env = {**os.environ, "CUDA_VISIBLE_DEVICES": gpu, **env_extra}
    log = open(log_dir / f"{name}-server.log", "w")
    cmd = ["vllm", "serve", path, "--served-model-name", name, "--port", str(port), "--dtype", "bfloat16",
           "--language-model-only", "--generation-config", "vllm", "--seed", "0", *args]
    return subprocess.Popen(cmd, env=env, stdout=log, stderr=subprocess.STDOUT)


def _wait_ready(port: int, proc, name: str, log_dir: Path, timeout: float = 1200):
    import urllib.request

    start = time.time()
    while time.time() - start < timeout:
        if proc.poll() is not None:
            tail = (log_dir / f"{name}-server.log").read_text()[-3000:]
            raise RuntimeError(f"{name} server exited:\n{tail}")
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=5):
                return round(time.time() - start, 1)
        except Exception:
            time.sleep(5)
    raise RuntimeError(f"{name} server not ready after {timeout}s")


# ----------------------------------------------------------------------------- training

def _train(task: str, prompts: list[dict], cfg: dict, run_name: str, steps: int, probe: bool,
           resume_from: str | None = None, start_step: int = 0) -> dict:
    """``resume_from``: an adapter path under /hf/opd to continue from; steps are numbered from
    ``start_step + 1``. The optimizer state was not saved, so AdamW restarts from zero moments."""
    import subprocess
    import traceback
    from concurrent.futures import ThreadPoolExecutor

    out = Path(HF_DIR) / "opd" / run_name
    (out / "adapters").mkdir(parents=True, exist_ok=True)
    metrics_path = out / "metrics.jsonl"
    events = []

    def log(msg):
        events.append(f"{time.strftime('%H:%M:%S')} {msg}")
        (out / "events.log").write_text("\n".join(events) + "\n")
        volume.commit()

    (out / "config.json").write_text(json.dumps({"task": task, "steps": steps, "probe": probe, "resume_from": resume_from,
                                                "start_step": start_step, **cfg}, indent=1))
    cap = cfg["rollout_max_tokens"][task]
    max_len = cap + 4096
    r = cfg["lora"]["r"]
    student_path, teacher_path = _snapshot(STUDENT), _snapshot(TEACHER)
    procs = []
    try:
        teacher = _serve(teacher_path, "teacher", 8001, "1",
                         ["--gpu-memory-utilization", "0.88", "--max-model-len", str(max_len), "--max-num-seqs", "32",
                          "--max-num-batched-tokens", "4096"], out, {})
        student = _serve(student_path, "student", 8000, "0",
                         ["--gpu-memory-utilization", "0.30", "--max-model-len", str(max_len), "--max-num-seqs", "64",
                          "--enable-lora", "--max-lora-rank", str(r), "--max-loras", "1", "--max-cpu-loras", "2"],
                         out, {"VLLM_ALLOW_RUNTIME_LORA_UPDATING": "True"})
        procs = [teacher, student]
        log(f"student server ready in {_wait_ready(8000, student, 'student', out)} s")

        # Load the trainer only after the student server has profiled GPU 0 memory.
        import torch
        from peft import LoraConfig, get_peft_model
        from transformers import AutoTokenizer, Qwen3_5ForConditionalGeneration

        tok = AutoTokenizer.from_pretrained(student_path)
        model = Qwen3_5ForConditionalGeneration.from_pretrained(student_path, dtype=torch.bfloat16,
                                                                attn_implementation="sdpa").to("cuda:0")
        if resume_from:
            from peft import PeftModel
            model = PeftModel.from_pretrained(model, str(Path(HF_DIR) / "opd" / resume_from), is_trainable=True)
        else:
            # A plain module list (vLLM reads it from adapter_config.json); the vision tower is excluded.
            model = get_peft_model(model, LoraConfig(r=r, lora_alpha=cfg["lora"]["alpha"], lora_dropout=cfg["lora"]["dropout"],
                                                     target_modules=list(cfg["lora"]["target_modules"]),
                                                     exclude_modules=r".*visual.*", bias="none"))
        model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
        model.enable_input_require_grads()
        trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
        o = cfg["optimizer"]
        opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=o["lr"],
                                betas=tuple(o["betas"]), weight_decay=o["weight_decay"])
        backbone, lm_head = model.base_model.model.model, model.base_model.model.lm_head
        log(f"trainer loaded: {trainable / 1e6:.1f}M LoRA parameters; "
            f"teacher server ready in {_wait_ready(8001, teacher, 'teacher', out)} s")

        eos_ids = {tok.convert_tokens_to_ids(t) for t in ("<|im_end|>", "<|endoftext|>")}
        im_end = tok.convert_tokens_to_ids("<|im_end|>")
        prompt_ids = {}
        for p in prompts:
            text = tok.apply_chat_template([{"role": "user", "content": p["prompt"]}], tokenize=False,
                                           add_generation_prompt=True, enable_thinking=False)
            prompt_ids[p["uid"]] = tok(text, add_special_tokens=False)["input_ids"]

        def rollout(uid, model_name, seed):
            res = _post(8000, "/v1/completions", {
                "model": model_name, "prompt": prompt_ids[uid], "max_tokens": cap, "temperature": cfg["rollout"]["temperature"],
                "top_p": cfg["rollout"]["top_p"], "logprobs": 1, "return_tokens_as_token_ids": True,
                "skip_special_tokens": False, "seed": seed})
            ch = res["choices"][0]
            ids = [int(t.split(":", 1)[1]) for t in ch["logprobs"]["tokens"]]
            lps = list(ch["logprobs"]["token_logprobs"])
            eos_added = False
            if ch["finish_reason"] == "stop" and (not ids or ids[-1] not in eos_ids):
                # Train on the stop token too, so the student learns when to end. No vLLM
                # log-prob exists for it; the IS ratio for that token is then 1.
                ids.append(im_end)
                lps.append(None)
                eos_added = True
            return {"uid": uid, "ids": ids, "vllm_lp": lps, "finish": ch["finish_reason"], "eos_added": eos_added}

        def teacher_lp(ro):
            p = prompt_ids[ro["uid"]]
            res = _post(8001, "/v1/completions", {"model": "teacher", "prompt": p + ro["ids"], "max_tokens": 1,
                                                  "temperature": 0.0, "prompt_logprobs": 0})
            plp = res["choices"][0]["prompt_logprobs"][len(p):]
            out = []
            for entry, t in zip(plp, ro["ids"]):
                e = entry.get(str(t)) or entry.get(f"token_id:{t}")
                if e is None:
                    raise KeyError(f"teacher log-prob missing for token {t}; keys {list(entry)[:3]}")
                out.append(e["logprob"])
            return out

        def token_logprobs(h, targets, chunk):
            from torch.utils.checkpoint import checkpoint

            def f(hc, tc):
                return torch.log_softmax(lm_head(hc).float(), -1).gather(-1, tc[:, None])[:, 0]
            return torch.cat([checkpoint(f, h[i:i + chunk], targets[i:i + chunk], use_reentrant=False)
                              for i in range(0, len(targets), chunk)])

        from opd_monitor import repetition_score, should_stop  # shipped into the image (see opd_image)
        history, current = [], "student"
        B = cfg["prompts_per_step"]
        if resume_from:  # rollouts of the first resumed step must come from the resumed adapter
            _post(8000, "/v1/load_lora_adapter", {"lora_name": f"s{start_step}", "lora_path": str(Path(HF_DIR) / "opd" / resume_from)})
            current = f"s{start_step}"
            log(f"resumed from {resume_from} at step {start_step}; optimizer state restarts")
        for local_step in range(steps):
            step = start_step + local_step  # global step index (0-based)
            batch = prompts[local_step * B:(local_step + 1) * B]
            if len(batch) < B:
                log("ran out of prompts")
                break
            t0 = time.time()
            with ThreadPoolExecutor(max_workers=B) as pool:
                ros = list(pool.map(lambda i_p: rollout(i_p[1]["uid"], current, step * 1000 + i_p[0]), enumerate(batch)))
            t1 = time.time()
            with ThreadPoolExecutor(max_workers=8) as pool:
                t_lps = list(pool.map(teacher_lp, ros))
            t2 = time.time()
            model.train()
            opt.zero_grad(set_to_none=True)
            stats = {"loss": 0.0, "rkl": [], "gap": [], "clipped": 0, "tokens": 0, "anchor": []}
            drop = cfg.get("drop_truncated", False)
            beta = cfg.get("kl_anchor_beta", 0.0)
            # Overlong filtering: rollouts that hit the cap are left out of the loss.
            kept = [(ro, tlp) for ro, tlp in zip(ros, t_lps) if ro["ids"] and not (drop and ro["finish"] == "length")]
            for ro, tlp in kept:
                if len(tlp) != len(ro["ids"]):
                    raise RuntimeError(f"teacher returned {len(tlp)} log-probs for {len(ro['ids'])} tokens")
                p = prompt_ids[ro["uid"]]
                ids = torch.tensor([p + ro["ids"]], device="cuda:0")
                targets = torch.tensor(ro["ids"], device="cuda:0")
                h = backbone(input_ids=ids, use_cache=False).last_hidden_state[0, len(p) - 1:len(p) - 1 + len(ro["ids"])]
                lp = token_logprobs(h, targets, cfg["logprob_chunk_tokens"])
                t_ = torch.tensor(tlp, device="cuda:0", dtype=torch.float32)
                v_ = torch.tensor([float("nan") if x is None else x for x in ro["vllm_lp"]], device="cuda:0",
                                  dtype=torch.float32)
                v_ = torch.where(torch.isnan(v_), lp.detach(), v_)
                ref = None
                if beta > 0:  # KL anchor to the initial student = the base model with the adapter off
                    with torch.no_grad(), model.disable_adapter():
                        h_ref = backbone(input_ids=ids, use_cache=False).last_hidden_state[
                            0, len(p) - 1:len(p) - 1 + len(ro["ids"])]
                        c = cfg["logprob_chunk_tokens"]
                        ref = torch.cat([torch.log_softmax(lm_head(h_ref[i:i + c]).float(), -1)
                                         .gather(-1, targets[i:i + c, None])[:, 0] for i in range(0, len(targets), c)])
                        del h_ref
                with torch.no_grad():
                    adv = t_ - lp.detach()
                    if ref is not None:
                        adv = adv - beta * (lp.detach() - ref)
                    raw_ratio = torch.exp(lp.detach() - v_)
                    ratio = raw_ratio.clamp(max=cfg["importance_sampling_cap"])
                loss = -(ratio * adv * lp).mean() / len(kept)
                loss.backward()
                stats["loss"] += loss.item()
                stats["rkl"].append((lp.detach() - t_).mean().item())
                stats["gap"].append((lp.detach() - v_).abs().mean().item())
                stats["clipped"] += int((raw_ratio > cfg["importance_sampling_cap"]).sum())
                stats["tokens"] += len(ro["ids"])
                if ref is not None:
                    stats["anchor"].append((lp.detach() - ref).mean().item())
                del h, lp, loss
            skipped = not kept  # every rollout truncated (with filtering): no update this step
            gnorm = 0.0
            if not skipped:
                gnorm = torch.nn.utils.clip_grad_norm_([p for p in model.parameters() if p.requires_grad],
                                                       cfg["optimizer"]["grad_clip"]).item()
                opt.step()
            t3 = time.time()
            path = out / "adapters" / f"step{step + 1}"
            model.save_pretrained(str(path))
            volume.commit()
            _post(8000, "/v1/load_lora_adapter", {"lora_name": f"s{step + 1}", "lora_path": str(path)})
            if current != "student":
                _post(8000, "/v1/unload_lora_adapter", {"lora_name": current})
                prev = out / "adapters" / f"step{step}"
                if step % 8 != 0 and prev.exists():  # keep every 8th adapter and the final one
                    import shutil
                    shutil.rmtree(prev)
            current = f"s{step + 1}"
            t4 = time.time()
            lens = [len(ro["ids"]) for ro in ros]
            n_used = max(1, len(stats["rkl"]))
            rec = {"step": step + 1, "loss": stats["loss"], "reverse_kl": sum(stats["rkl"]) / n_used,
                   "mean_abs_logprob_gap": sum(stats["gap"]) / n_used, "is_clipped_tokens": stats["clipped"],
                   "rollouts_used": len(kept), "rollouts_dropped": len(ros) - len(kept), "update_skipped": skipped,
                   "anchor_kl": (sum(stats["anchor"]) / len(stats["anchor"])) if stats["anchor"] else None,
                   "tokens": stats["tokens"], "grad_norm": gnorm, "mean_len": sum(lens) / len(lens), "max_len": max(lens),
                   "truncation_rate": sum(ro["finish"] == "length" for ro in ros) / len(ros),
                   "stopped": sum(ro["finish"] == "stop" for ro in ros),
                   "eos_appended": sum(ro["eos_added"] for ro in ros),
                   "repetition": sum(repetition_score(ro["ids"]) for ro in ros) / len(ros),
                   "seconds": {"rollout": round(t1 - t0, 1), "teacher": round(t2 - t1, 1), "train": round(t3 - t2, 1),
                               "sync": round(t4 - t3, 1)},
                   "trainer_peak_gib": round(torch.cuda.max_memory_allocated(0) / 2**30, 1),
                   "gpu_memory": subprocess.run(["nvidia-smi", "--query-gpu=memory.used,memory.total", "--format=csv,noheader"],
                                                capture_output=True, text=True).stdout.strip().splitlines()}
            history.append(rec)
            with metrics_path.open("a") as fh:
                fh.write(json.dumps(rec) + "\n")
            log(f"step {step + 1}: loss {rec['loss']:.4f} rkl {rec['reverse_kl']:.3f} gap {rec['mean_abs_logprob_gap']:.3f} "
                f"len {rec['mean_len']:.0f} trunc {rec['truncation_rate']:.2f} rep {rec['repetition']:.2f} "
                f"used {rec['rollouts_used']} anchor {rec['anchor_kl']} {'SKIPPED ' if skipped else ''}{rec['seconds']}")
            reason = should_stop(history, cfg)
            if reason:
                log(f"AUTO-STOP: {reason}")
                break
        return {"ok": True, "run": run_name, "steps_done": len(history), "history": history, "events": events}
    except Exception:
        log("ERROR\n" + traceback.format_exc())
        return {"ok": False, "run": run_name, "error": traceback.format_exc(), "events": events}
    finally:
        for p in procs:
            p.terminate()
        volume.commit()


opd_image = gpu_image.add_local_file(
    Path(__file__).resolve().parents[1] / "src" / "anlp_project" / "opd_monitor.py", "/root/opd_monitor.py")


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
