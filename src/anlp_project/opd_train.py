"""Platform-neutral reverse-KL OPD loop (used by scripts/modal_opd.py and the Turing runner).

One node: a teacher vLLM server scores tokens, a student vLLM server (runtime LoRA) makes the
rollouts, and a PEFT trainer shares the student's GPU. Each step: rollouts -> teacher log-probs
-> one LoRA update -> the new adapter is loaded into the student server.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
import traceback
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Callable

try:  # package import locally and on Turing; flat file inside the Modal image
    from .opd_monitor import repetition_score, should_stop
except ImportError:  # pragma: no cover
    from opd_monitor import repetition_score, should_stop


def post(port: int, path: str, body: dict, timeout: float = 3600) -> dict:
    req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read()
    return json.loads(raw) if raw.strip().startswith(b"{") else {"text": raw.decode()}


def serve(path: str, name: str, port: int, gpus: str, args: list[str], log_dir: Path, env_extra: dict):
    env = {**os.environ, "CUDA_VISIBLE_DEVICES": gpus, **env_extra}
    log = open(log_dir / f"{name}-server.log", "w")
    cmd = ["vllm", "serve", path, "--served-model-name", name, "--port", str(port), "--dtype", "bfloat16",
           "--language-model-only", "--generation-config", "vllm", "--seed", "0", *args]
    return subprocess.Popen(cmd, env=env, stdout=log, stderr=subprocess.STDOUT)


def wait_ready(port: int, proc, name: str, log_dir: Path, timeout: float = 1800) -> float:
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


def run_opd(task: str, prompts: list[dict], cfg: dict, out: Path, student_path: str, teacher_path: str, *,
            steps: int, meta: dict | None = None, teacher_gpus: str = "1", teacher_tp: int = 1,
            student_gpu: str = "0", student_mem: float = 0.30, teacher_mem: float = 0.88,
            init_adapter: str | None = None, resume_from: str | None = None, start_step: int = 0,
            save_optimizer: bool = False, commit: Callable[[], None] = lambda: None) -> dict[str, Any]:
    """Run ``steps`` OPD steps on ``prompts`` (B per step, in order).

    ``init_adapter``: start from this LoRA adapter (e.g. an SFT warm-up) with a fresh optimiser.
    ``resume_from``: continue a stopped run from this adapter; steps are numbered from
    ``start_step + 1``, and ``optimizer.pt`` next to it is restored when present.
    """
    (out / "adapters").mkdir(parents=True, exist_ok=True)
    metrics_path = out / "metrics.jsonl"
    events: list[str] = []

    def log(msg):
        events.append(f"{time.strftime('%H:%M:%S')} {msg}")
        with (out / "events.log").open("a") as fh:
            fh.write(events[-1] + "\n")
        commit()

    (out / "config.json").write_text(json.dumps({"task": task, "steps": steps, **(meta or {}),
                                                "init_adapter": init_adapter, "resume_from": resume_from,
                                                "start_step": start_step, **cfg}, indent=1))
    cap = cfg["rollout_max_tokens"][task]
    max_len = cap + 4096
    r = cfg["lora"]["r"]
    procs = []
    try:
        teacher = serve(teacher_path, "teacher", 8001, teacher_gpus,
                        ["--gpu-memory-utilization", str(teacher_mem), "--max-model-len", str(max_len),
                         "--max-num-seqs", "32", "--max-num-batched-tokens", "4096",
                         "--tensor-parallel-size", str(teacher_tp), "--max-logprobs", str(max(20, cfg.get("topk_k", 20)))],
                        out, {})
        student = serve(student_path, "student", 8000, student_gpu,
                        ["--gpu-memory-utilization", str(student_mem), "--max-model-len", str(max_len),
                         "--max-num-seqs", "64", "--enable-lora", "--max-lora-rank", str(r), "--max-loras", "1",
                         "--max-cpu-loras", "2"], out, {"VLLM_ALLOW_RUNTIME_LORA_UPDATING": "True"})
        procs = [teacher, student]
        log(f"student server ready in {wait_ready(8000, student, 'student', out)} s")

        # Load the trainer only after the student server has profiled its GPU's memory.
        import torch
        from peft import LoraConfig, PeftModel, get_peft_model
        from transformers import AutoTokenizer, Qwen3_5ForConditionalGeneration

        os.environ["CUDA_VISIBLE_DEVICES"] = student_gpu  # the trainer shares the student's GPU
        tok = AutoTokenizer.from_pretrained(student_path)
        model = Qwen3_5ForConditionalGeneration.from_pretrained(student_path, dtype=torch.bfloat16,
                                                                attn_implementation="sdpa").to("cuda:0")
        start_adapter = resume_from or init_adapter
        if start_adapter:
            model = PeftModel.from_pretrained(model, start_adapter, is_trainable=True)
        else:
            # A plain module list (vLLM reads it from adapter_config.json); the vision tower is excluded.
            model = get_peft_model(model, LoraConfig(r=r, lora_alpha=cfg["lora"]["alpha"], lora_dropout=cfg["lora"]["dropout"],
                                                     target_modules=list(cfg["lora"]["target_modules"]),
                                                     exclude_modules=r".*visual.*", bias="none"))
        # KL anchor reference: the starting point of this run. With a starting adapter (e.g. the SFT
        # warm-up) that is a frozen copy of it; without one, the base model (adapter disabled).
        ref_adapter = None
        if cfg.get("kl_anchor_beta", 0.0) > 0 and init_adapter:
            model.load_adapter(init_adapter, adapter_name="ref", is_trainable=False)
            ref_adapter = "ref"
        model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
        model.enable_input_require_grads()
        params = [p for n, p in model.named_parameters() if p.requires_grad and ".ref." not in n]
        o = cfg["optimizer"]
        opt = torch.optim.AdamW(params, lr=o["lr"], betas=tuple(o["betas"]), weight_decay=o["weight_decay"])
        opt_note = "fresh optimiser"
        if resume_from and (Path(resume_from) / "optimizer.pt").exists():
            opt.load_state_dict(torch.load(Path(resume_from) / "optimizer.pt", map_location="cuda:0"))
            opt_note = "optimiser state restored"
        backbone, lm_head = model.base_model.model.model, model.base_model.model.lm_head
        log(f"trainer loaded: {sum(p.numel() for p in params) / 1e6:.1f}M LoRA parameters ({opt_note}); "
            f"teacher server ready in {wait_ready(8001, teacher, 'teacher', out)} s")

        eos_ids = {tok.convert_tokens_to_ids(t) for t in ("<|im_end|>", "<|endoftext|>")}
        im_end = tok.convert_tokens_to_ids("<|im_end|>")
        prompt_ids, teacher_prompt_ids = {}, {}
        system = cfg.get("teacher_system_prompt")  # teacher-only instruction (context distillation)
        for p in prompts:
            msgs = [{"role": "user", "content": p["prompt"]}]
            text = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True, enable_thinking=False)
            prompt_ids[p["uid"]] = tok(text, add_special_tokens=False)["input_ids"]
            if system:
                text = tok.apply_chat_template([{"role": "system", "content": system}] + msgs, tokenize=False,
                                               add_generation_prompt=True, enable_thinking=False)
                teacher_prompt_ids[p["uid"]] = tok(text, add_special_tokens=False)["input_ids"]
            else:
                teacher_prompt_ids[p["uid"]] = prompt_ids[p["uid"]]

        def rollout(uid, model_name, seed):
            res = post(8000, "/v1/completions", {
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

        topk = cfg.get("loss", "sampled") == "topk"
        K = cfg.get("topk_k", 20)

        def teacher_lp(ro):
            """Teacher log-prob of each sampled token; with the top-K loss also its top-K tokens per position."""
            p = teacher_prompt_ids[ro["uid"]]
            res = post(8001, "/v1/completions", {"model": "teacher", "prompt": p + ro["ids"], "max_tokens": 1,
                                                 "temperature": 0.0, "prompt_logprobs": K if topk else 0})
            plp = res["choices"][0]["prompt_logprobs"][len(p):]
            vals, top_ids, top_lps = [], [], []
            for entry, t in zip(plp, ro["ids"]):
                e = entry.get(str(t)) or entry.get(f"token_id:{t}")
                if e is None:
                    raise KeyError(f"teacher log-prob missing for token {t}; keys {list(entry)[:3]}")
                vals.append(e["logprob"])
                if topk:  # the entry holds the top-K tokens plus the sampled one; keep the K most likely
                    best = sorted(entry.items(), key=lambda kv: -kv[1]["logprob"])[:K]
                    top_ids.append([int(k.split(":")[-1]) for k, _ in best])
                    top_lps.append([v["logprob"] for _, v in best])
            return {"lp": vals, "top_ids": top_ids, "top_lp": top_lps}

        def token_logprobs(h, targets, chunk, top=None):
            """Student log-probs of the sampled tokens (and, given ``top`` [T, K], of those tokens too)."""
            from torch.utils.checkpoint import checkpoint

            def f(hc, tc):
                return torch.log_softmax(lm_head(hc).float(), -1).gather(-1, tc[:, None])[:, 0]

            def g(hc, tc, kc):
                ls = torch.log_softmax(lm_head(hc).float(), -1)
                return ls.gather(-1, tc[:, None])[:, 0], ls.gather(-1, kc)
            if top is None:
                return torch.cat([checkpoint(f, h[i:i + chunk], targets[i:i + chunk], use_reentrant=False)
                                  for i in range(0, len(targets), chunk)])
            parts = [checkpoint(g, h[i:i + chunk], targets[i:i + chunk], top[i:i + chunk], use_reentrant=False)
                     for i in range(0, len(targets), chunk)]
            return torch.cat([a for a, _ in parts]), torch.cat([b for _, b in parts])

        # Stable-OPD-style rollout mixture: an SFT term on fixed teacher answers each step.
        mix = cfg.get("sft_mix")
        mix_rows, mix_by_uid = [], {}
        if mix:
            import random as _random
            keep = set(json.loads(open(mix["keep_uids"]).read())) if mix.get("keep_uids") else None
            for line in open(mix["data"]):
                r = json.loads(line)
                if keep is not None and r["uid"] not in keep:
                    continue
                text = tok.apply_chat_template([{"role": "user", "content": r["prompt"]}], tokenize=False,
                                               add_generation_prompt=True, enable_thinking=False)
                item = (tok(text, add_special_tokens=False)["input_ids"], r["response_ids"])
                mix_rows.append(item)
                mix_by_uid[r["uid"]] = item
            _random.Random(mix.get("seed", 20261001)).shuffle(mix_rows)
            if mix.get("paired"):
                covered = sum(p["uid"] in mix_by_uid for p in prompts)
                log(f"SFT mix (paired, Stable-OPD): {len(mix_by_uid)} demonstrations; {covered} of {len(prompts)} "
                    f"OPD prompts have one; weight {mix['weight']}")
            else:
                log(f"SFT mix: {len(mix_rows)} teacher answers, {mix['per_step']} per step, weight {mix['weight']}")

        history, current = [], "student"
        B = cfg["prompts_per_step"]
        if start_adapter:  # rollouts of the first step must come from the starting adapter
            post(8000, "/v1/load_lora_adapter", {"lora_name": f"s{start_step}", "lora_path": str(start_adapter)})
            current = f"s{start_step}"
            log(f"starting from adapter {start_adapter} at step {start_step}")
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
            stats = {"loss": 0.0, "rkl": [], "gap": [], "clipped": 0, "tokens": 0, "anchor": [],
                     "eos_adv": [], "eos_t": [], "eos_s": [], "tail_adv": [], "body_adv": []}
            drop = cfg.get("drop_truncated", False)
            beta = cfg.get("kl_anchor_beta", 0.0)
            # Overlong filtering: rollouts that hit the cap are left out of the loss.
            kept = [(ro, tlp) for ro, tlp in zip(ros, t_lps) if ro["ids"] and not (drop and ro["finish"] == "length")]
            stats["topk_kl"] = []
            for ro, tinfo in kept:
                tlp = tinfo["lp"]
                if len(tlp) != len(ro["ids"]):
                    raise RuntimeError(f"teacher returned {len(tlp)} log-probs for {len(ro['ids'])} tokens")
                p = prompt_ids[ro["uid"]]
                ids = torch.tensor([p + ro["ids"]], device="cuda:0")
                targets = torch.tensor(ro["ids"], device="cuda:0")
                h = backbone(input_ids=ids, use_cache=False).last_hidden_state[0, len(p) - 1:len(p) - 1 + len(ro["ids"])]
                lpk = None
                if topk:
                    top = torch.tensor(tinfo["top_ids"], device="cuda:0")
                    lp, lpk = token_logprobs(h, targets, cfg["logprob_chunk_tokens"], top)
                else:
                    lp = token_logprobs(h, targets, cfg["logprob_chunk_tokens"])
                t_ = torch.tensor(tlp, device="cuda:0", dtype=torch.float32)
                v_ = torch.tensor([float("nan") if x is None else x for x in ro["vllm_lp"]], device="cuda:0",
                                  dtype=torch.float32)
                v_ = torch.where(torch.isnan(v_), lp.detach(), v_)
                ref = None
                ref_k = None
                if beta > 0:  # KL anchor to the run's starting point (see ref_adapter above)
                    def ref_logprobs():
                        nonlocal ref_k
                        h_ref = backbone(input_ids=ids, use_cache=False).last_hidden_state[
                            0, len(p) - 1:len(p) - 1 + len(ro["ids"])]
                        c = cfg["logprob_chunk_tokens"]
                        vals, ks = [], []
                        for i in range(0, len(targets), c):
                            ls = torch.log_softmax(lm_head(h_ref[i:i + c]).float(), -1)
                            vals.append(ls.gather(-1, targets[i:i + c, None])[:, 0])
                            if topk:
                                ks.append(ls.gather(-1, top[i:i + c]))
                        if topk:
                            ref_k = torch.cat(ks)
                        return torch.cat(vals)
                    with torch.no_grad():
                        if ref_adapter:
                            model.base_model.set_adapter(ref_adapter)
                            try:
                                ref = ref_logprobs()
                            finally:
                                model.base_model.set_adapter("default")
                        else:
                            with model.disable_adapter():
                                ref = ref_logprobs()
                with torch.no_grad():
                    # Sampled-token loss: the teacher term is the advantage. Top-K loss: the teacher
                    # term is the renormalised top-K KL below; only the penalties stay policy-gradient.
                    # Length gate: rollouts longer than `teacher_signal_max_len` get no teacher term,
                    # only the length penalties below, so long searches and loops are never reinforced.
                    gate = cfg.get("teacher_signal_max_len")
                    gated = gate is not None and len(ro["ids"]) > gate
                    adv = torch.zeros_like(t_) if (topk or gated) else t_ - lp.detach()
                    if ref is not None and not topk:  # with the top-K loss the anchor is a top-K KL below
                        adv = adv - beta * (lp.detach() - ref)
                    if ro["finish"] == "length" and cfg.get("overlong_penalty", 0.0):
                        adv = adv - cfg["overlong_penalty"]  # DAPO-style: pushes away from running to the cap
                    soft = cfg.get("soft_length_penalty")
                    if soft and len(ro["ids"]) > soft["start"]:  # DAPO soft overlong: linear from start to the cap
                        adv = adv - soft["max"] * min(1.0, (len(ro["ids"]) - soft["start"]) / (cap - soft["start"]))
                    raw_ratio = torch.exp(lp.detach() - v_)
                    ratio = raw_ratio.clamp(max=cfg["importance_sampling_cap"])
                loss = -(ratio * adv * lp).mean() / len(kept)
                ro["gated"] = gated
                if topk and not gated:  # Revisiting OPD: reverse KL between student and teacher renormalised on the teacher's top K
                    lt = torch.tensor(tinfo["top_lp"], device="cuda:0", dtype=torch.float32)
                    log_s = lpk - torch.logsumexp(lpk, -1, keepdim=True)
                    log_t = lt - torch.logsumexp(lt, -1, keepdim=True)
                    div = cfg.get("topk_divergence", "reverse")
                    if div == "jsd":  # GKD generalised JSD with mixing weight 0.5 on the renormalised support
                        log_m = torch.logsumexp(torch.stack([log_s, log_t]), 0) - torch.log(torch.tensor(2.0, device=log_s.device))
                        kl = 0.5 * (log_s.exp() * (log_s - log_m)).sum(-1) + 0.5 * (log_t.exp() * (log_t - log_m)).sum(-1)
                    elif div == "forward":
                        kl = (log_t.exp() * (log_t - log_s)).sum(-1)
                    else:
                        kl = (log_s.exp() * (log_s - log_t)).sum(-1)
                    loss = loss + kl.mean() / len(kept)
                    stats["topk_kl"].append(kl.mean().item())
                    if ref_k is not None:  # anchor on the same support: optimum ~ teacher^(1/(1+b)) * ref^(b/(1+b))
                        log_r = ref_k - torch.logsumexp(ref_k, -1, keepdim=True)
                        akl = (log_s.exp() * (log_s - log_r)).sum(-1)
                        loss = loss + beta * akl.mean() / len(kept)
                        stats.setdefault("topk_anchor", []).append(akl.mean().item())
                        del log_r, akl
                    del lpk, log_s, kl
                loss.backward()
                stats["loss"] += loss.item()
                stats["rkl"].append((lp.detach() - t_).mean().item())
                stats["gap"].append((lp.detach() - v_).abs().mean().item())
                stats["clipped"] += int((raw_ratio > cfg["importance_sampling_cap"]).sum())
                stats["tokens"] += len(ro["ids"])
                if ref is not None:
                    stats["anchor"].append((lp.detach() - ref).mean().item())
                ro["adv_mean"] = adv.mean().item()
                if ro["finish"] == "stop":  # the stop token: does the teacher agree with ending here?
                    stats["eos_adv"].append(adv[-1].item())
                    stats["eos_t"].append(t_[-1].item())
                    stats["eos_s"].append(lp[-1].item())
                    stats["tail_adv"].append(adv[-16:].mean().item())
                    ro["eos_adv"] = adv[-1].item()
                stats["body_adv"].append(adv.mean().item())
                del h, lp, loss
            sft_loss = None
            sft_n = 0
            if mix_rows:
                if mix.get("paired"):  # the demonstrations for this step's own questions
                    batch_sft = [mix_by_uid[p["uid"]] for p in batch if p["uid"] in mix_by_uid]
                else:
                    k = mix["per_step"]
                    batch_sft = [mix_rows[(step * k + i) % len(mix_rows)] for i in range(k)]
                sft_n = len(batch_sft)
                n_tok = max(1, sum(len(resp) for _, resp in batch_sft))
                sft_loss = 0.0
                for prompt_s, resp in batch_sft:
                    ids_s = torch.tensor([prompt_s + resp], device="cuda:0")
                    h_s = backbone(input_ids=ids_s, use_cache=False).last_hidden_state[
                        0, len(prompt_s) - 1:len(prompt_s) - 1 + len(resp)]
                    lp_s = token_logprobs(h_s, torch.tensor(resp, device="cuda:0"), cfg["logprob_chunk_tokens"])
                    loss_s = -mix["weight"] * lp_s.sum() / n_tok  # token mean over the SFT batch
                    loss_s.backward()
                    sft_loss += loss_s.item() / mix["weight"]
                    del h_s, lp_s, loss_s
            skipped = not kept and not sft_n  # nothing to learn from this step: no update
            gnorm = 0.0
            # Linear warm-up over the first `warmup_steps` global steps, then the constant LR.
            warm = cfg["optimizer"].get("warmup_steps", 0)
            lr_now = o["lr"] * min(1.0, (step + 1) / warm) if warm else o["lr"]
            for g in opt.param_groups:
                g["lr"] = lr_now
            if not skipped:
                gnorm = torch.nn.utils.clip_grad_norm_(params, cfg["optimizer"]["grad_clip"]).item()
                opt.step()
            t3 = time.time()
            path = out / "adapters" / f"step{step + 1}"
            model.save_pretrained(str(path), selected_adapters=["default"])
            if save_optimizer:  # only the latest step keeps optimiser state (about 0.5 GB)
                torch.save(opt.state_dict(), path / "optimizer.pt")
                prev_opt = out / "adapters" / f"step{step}" / "optimizer.pt"
                if prev_opt.exists():
                    prev_opt.unlink()
            commit()
            post(8000, "/v1/load_lora_adapter", {"lora_name": f"s{step + 1}", "lora_path": str(path)})
            if current != "student":
                post(8000, "/v1/unload_lora_adapter", {"lora_name": current})
                prev = out / "adapters" / f"step{step}"
                if step % 8 != 0 and prev.exists():  # keep every 8th adapter and the final one
                    shutil.rmtree(prev)
            current = f"s{step + 1}"
            t4 = time.time()
            lens = [len(ro["ids"]) for ro in ros]
            n_used = max(1, len(stats["rkl"]))
            rec = {"step": step + 1, "loss": stats["loss"], "reverse_kl": sum(stats["rkl"]) / n_used,
                   "mean_abs_logprob_gap": sum(stats["gap"]) / n_used, "is_clipped_tokens": stats["clipped"],
                   "rollouts_used": len(kept), "rollouts_dropped": len(ros) - len(kept), "update_skipped": skipped,
                   "rollouts_gated": sum(bool(ro.get("gated")) for ro in ros),
                   "anchor_kl": (sum(stats["anchor"]) / len(stats["anchor"])) if stats["anchor"] else None,
                   "stop_token": {k: (sum(v) / len(v) if v else None) for k, v in
                                  (("advantage", stats["eos_adv"]), ("teacher_lp", stats["eos_t"]),
                                   ("student_lp", stats["eos_s"]), ("last16_advantage", stats["tail_adv"]))},
                   "mean_advantage": sum(stats["body_adv"]) / max(1, len(stats["body_adv"])),
                   "topk_kl": (sum(stats["topk_kl"]) / len(stats["topk_kl"])) if stats["topk_kl"] else None,
                   "sft_loss": sft_loss, "sft_examples": sft_n,
                   "topk_anchor_kl": (sum(stats["topk_anchor"]) / len(stats["topk_anchor"])) if stats.get("topk_anchor") else None,
                   "tokens": stats["tokens"], "grad_norm": gnorm, "lr": lr_now, "mean_len": sum(lens) / len(lens), "max_len": max(lens),
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
            (out / "rollouts").mkdir(exist_ok=True)
            with (out / "rollouts" / f"step{step + 1}.jsonl").open("w") as fh:
                for ro in ros:
                    fh.write(json.dumps({"uid": ro["uid"], "finish": ro["finish"], "tokens": len(ro["ids"]),
                                         "repetition": round(repetition_score(ro["ids"]), 4),
                                         "adv_mean": ro.get("adv_mean"), "eos_adv": ro.get("eos_adv"),
                                         "text": tok.decode(ro["ids"])}, ensure_ascii=False) + "\n")
            with metrics_path.open("a") as fh:
                fh.write(json.dumps(rec) + "\n")
            log(f"step {step + 1}: loss {rec['loss']:.4f} rkl {rec['reverse_kl']:.3f} gap {rec['mean_abs_logprob_gap']:.3f} "
                f"len {rec['mean_len']:.0f} trunc {rec['truncation_rate']:.2f} rep {rec['repetition']:.2f} "
                f"used {rec['rollouts_used']} sft {rec['sft_loss']} anchor {rec['anchor_kl']} topk-kl {rec['topk_kl']} topk-anchor {rec['topk_anchor_kl']} stop-adv {rec['stop_token']['advantage']} "
                f"stop-teacher-lp {rec['stop_token']['teacher_lp']} {'SKIPPED ' if skipped else ''}{rec['seconds']}")
            reason = should_stop(history, cfg)
            if reason:
                log(f"AUTO-STOP: {reason}")
                break
        return {"ok": True, "steps_done": len(history), "history": history, "events": events}
    except Exception:
        log("ERROR\n" + traceback.format_exc())
        return {"ok": False, "error": traceback.format_exc(), "events": events}
    finally:
        for p in procs:
            p.terminate()
        commit()
