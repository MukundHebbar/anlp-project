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


def post(port: int, path: str, body: dict, timeout: float = 3600, host: str = "127.0.0.1") -> dict:
    req = urllib.request.Request(f"http://{host}:{port}{path}", data=json.dumps(body).encode(),
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


def serve_teacher(path: str, port: int, gpus: str, tp: int, mem: float, max_len: int, cfg: dict, log_dir: Path,
                  max_seqs: int = 64):
    # Batched tokens stay at 4096: prompt log-probs materialise [batched tokens x vocab] logits.
    return serve(path, "teacher", port, gpus,
                 ["--gpu-memory-utilization", str(mem), "--max-model-len", str(max_len),
                  "--max-num-seqs", str(max_seqs), "--max-num-batched-tokens", "4096",
                  "--tensor-parallel-size", str(tp), "--max-logprobs", str(max(20, cfg.get("topk_k", 20))),
                  "--host", "0.0.0.0"],  # reachable from runs on other nodes
                 log_dir, {})


def wait_teacher(port: int, proc, log_dir: Path, host: str = "127.0.0.1", timeout: float = 1800) -> float:
    """Wait for this run's teacher, or for an external one (``proc`` None) shared with other runs."""
    if proc is not None:
        return wait_ready(port, proc, "teacher", log_dir)
    start = time.time()
    while time.time() - start < timeout:
        try:
            with urllib.request.urlopen(f"http://{host}:{port}/health", timeout=5):
                return round(time.time() - start, 1)
        except Exception:
            time.sleep(5)
    raise RuntimeError(f"external teacher on port {port} not ready")


def per_task_stats(ros: list[dict], task_of: dict, mixed: set, g_mean: dict) -> dict:
    """Per-task reward, questions with a learning signal, mean |advantage|, length and truncation (task "mixed")."""
    out = {}
    for t in sorted(set(task_of[ro["uid"]] for ro in ros)):
        rs = [ro for ro in ros if task_of[ro["uid"]] == t]
        scored = [ro for ro in rs if ro["reward"] is not None]
        uids = {ro["uid"] for ro in rs}
        advs = [abs(ro["reward"] - g_mean[ro["uid"]]) for ro in scored if ro["uid"] in g_mean]
        out[t] = {"reward_mean": sum(ro["reward"] for ro in scored) / max(1, len(scored)),
                  "questions": len(uids), "groups_mixed": len(uids & mixed),
                  "adv_abs_mean": sum(advs) / max(1, len(advs)),
                  "mean_len": sum(len(ro["ids"]) for ro in rs) / max(1, len(rs)),
                  "truncation_rate": sum(ro["finish"] == "length" for ro in rs) / max(1, len(rs)),
                  "reward_failed": len(rs) - len(scored)}
    return out


def rolling_score(recs: list[dict], window: int) -> float | None:
    """Single task: the rolling mean reward of the last ``window`` steps. Mixed: the mean over tasks of each task's
    rolling reward minus its own first-``window``-steps average (the average gain, so no task's reward scale
    dominates)."""
    if len(recs) < window:
        return None
    if recs[-1].get("per_task"):
        tasks = sorted(recs[-1]["per_task"])
        mean = lambda rs, t: sum(r["per_task"][t]["reward_mean"] for r in rs) / len(rs)
        return sum(mean(recs[-window:], t) - mean(recs[:window], t) for t in tasks) / len(tasks)
    return sum(r["reward_mean"] for r in recs[-window:]) / window


def keep_best(out: Path, metrics_path: Path, adapter: Path, step: int, window: int, keep: int, log) -> None:
    """Keep the ``keep`` adapters with the highest rolling mean training reward (GRPO).

    The rolling mean covers the last ``window`` steps in metrics.jsonl, which spans resumed chunks. In a first
    pass over the data every step's questions are new, so this is the policy's accuracy on unseen training
    questions. The adapter saved at the end of the window is copied to adapters/best-step<k> (without optimizer
    state); out/best.json lists the kept ones, best first.
    """
    recs = [r for r in map(json.loads, metrics_path.open()) if r.get("reward_mean") is not None]
    score = rolling_score(recs, window)
    if score is None:
        return
    book_path = out / "best.json"
    book = json.loads(book_path.read_text()) if book_path.exists() else []
    book = [b for b in book if b["step"] != step]
    if len(book) >= keep and score <= min(b["rolling_reward"] for b in book):
        return
    dest = out / "adapters" / f"best-step{step}"
    shutil.copytree(adapter, dest, dirs_exist_ok=True, ignore=shutil.ignore_patterns("optimizer.pt"))
    book.append({"step": step, "rolling_reward": round(score, 5), "window": window, "path": str(dest)})
    book.sort(key=lambda b: -b["rolling_reward"])
    for b in book[keep:]:
        shutil.rmtree(b["path"], ignore_errors=True)
    book = book[:keep]
    book_path.write_text(json.dumps(book, indent=1) + "\n")
    log(f"best-by-reward: step {step} rolling {window}-step reward {score:.4f} (kept: {[b['step'] for b in book]})")


def run_opd(task: str, prompts: list[dict], cfg: dict, out: Path, student_path: str, teacher_path: str, *,
            steps: int, meta: dict | None = None, teacher_gpus: str = "1", teacher_tp: int = 1,
            student_gpu: str = "0", student_mem: float = 0.30, teacher_mem: float = 0.88,
            trainer_gpu: str | None = None,
            init_adapter: str | None = None, resume_from: str | None = None, start_step: int = 0,
            save_optimizer: bool = False, commit: Callable[[], None] = lambda: None,
            student_port: int = 8000, teacher_port: int = 8001, external_teacher: bool = False,
            teacher_host: str = "127.0.0.1",
            keep_steps: tuple[int, ...] = ()) -> dict[str, Any]:
    """Run ``steps`` OPD steps on ``prompts`` (B per step, in order).

    ``external_teacher``: use a teacher server already listening on ``teacher_port`` (shared by
    several runs on one node) instead of starting one. ``keep_steps``: adapters kept in addition
    to every ``keep_adapters_every``-th step and the last one.

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
    # task "mixed": every prompt carries its own task (opd.mixed_prompts); one cap for all of them.
    cap = max(cfg["rollout_max_tokens"].values()) if task == "mixed" else cfg["rollout_max_tokens"][task]
    task_of = {p_["uid"]: p_.get("task", task) for p_ in prompts}
    max_len = cap + cfg.get("prompt_max_tokens", 4096)  # self-judge prompts hold a whole own attempt (up to ~17k)
    r = cfg["lora"]["r"]
    procs = []
    try:
        grpo = cfg.get("method") == "grpo"  # GRPO: rewards instead of a teacher (anlp_project.rewards)
        teacher = None if (external_teacher or grpo) else serve_teacher(teacher_path, teacher_port, teacher_gpus, teacher_tp,
                                                                        teacher_mem, max_len, cfg, out, max_seqs=64)
        student = serve(student_path, "student", student_port, student_gpu,
                        ["--gpu-memory-utilization", str(student_mem), "--max-model-len", str(max_len),
                         "--max-num-seqs", str(max(64, cfg["prompts_per_step"] * cfg.get("samples_per_prompt", 1))),
                         "--enable-lora", "--max-lora-rank", str(r),
                         "--max-loras", "1", "--max-cpu-loras", "2"], out, {"VLLM_ALLOW_RUNTIME_LORA_UPDATING": "True"})
        procs = [p for p in (teacher, student) if p is not None]
        log(f"student server ready in {wait_ready(student_port, student, 'student', out)} s")

        # Load the trainer only after the student server has profiled its GPU's memory.
        import torch
        from peft import LoraConfig, PeftModel, get_peft_model
        from transformers import AutoTokenizer, Qwen3_5ForConditionalGeneration

        # The trainer shares the student's GPU, or gets its own (``trainer_gpu``): then vLLM keeps a whole GPU
        # for rollouts. Adapters reach vLLM through files either way, so the run stays strictly on-policy.
        os.environ["CUDA_VISIBLE_DEVICES"] = trainer_gpu or student_gpu
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
        log(f"trainer loaded: {sum(p.numel() for p in params) / 1e6:.1f}M LoRA parameters ({opt_note}); " +
            ("GRPO, no teacher" if grpo else
             f"teacher server ready in {wait_teacher(teacher_port, teacher, out, teacher_host, timeout=4 * 3600)} s"))
        if grpo:
            from . import rewards as rw
            from .baseline import load_rows
            from .jev_judging import Jev
            tasks_here = sorted(set(task_of.values()))
            reward_rows = {r_["uid"]: r_ for t_ in tasks_here if t_ != "selfjudge" for r_ in load_rows(t_, "train")}
            reward_rows.update({p_["uid"]: p_ for p_ in prompts if task_of[p_["uid"]] == "selfjudge"})  # label inside
            jev = Jev() if any(t_ not in ("solve", "selfjudge") for t_ in tasks_here) else None
            G = cfg["samples_per_prompt"]

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
            res = post(student_port, "/v1/completions", {
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
            res = post(teacher_port, "/v1/completions", {"model": "teacher", "prompt": p + ro["ids"], "max_tokens": 1,
                                                 "temperature": 0.0, "prompt_logprobs": K if topk else 0}, host=teacher_host)
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
            post(student_port, "/v1/load_lora_adapter", {"lora_name": f"s{start_step}", "lora_path": str(start_adapter)})
            current = f"s{start_step}"
            log(f"starting from adapter {start_adapter} at step {start_step}")
        loaded_names = {current} - {"student"}
        # Overlapped rollouts (GRPO, cfg["async_rollouts"]): step s+1's answers are generated with the adapter
        # of step s while step s trains, so rollouts lag the trained policy by one update. The token-level IS
        # ratio against vLLM's log-probs (capped at importance_sampling_cap) corrects for that lag.
        overlap = grpo and cfg.get("async_rollouts", False)

        def collect(local_i, model_name):
            """Rollouts (and rewards / teacher log-probs) for one step's prompts, sampled with ``model_name``."""
            batch_ = prompts[local_i * B:(local_i + 1) * B]
            if len(batch_) < B:
                return None
            step_ = start_step + local_i
            t0_, done_at = time.time(), []

            def rollout_and_score(i_p):
                # Each rollout is sent to the teacher (GRPO: the reward) as soon as it finishes, so scoring
                # overlaps with the slower rollouts instead of waiting for the whole batch.
                ro = rollout(i_p[1]["uid"], model_name, step_ * 1000 + i_p[0])
                done_at.append(time.time())
                if grpo:
                    text_ = tok.decode(ro["ids"], skip_special_tokens=True)
                    ro["reward"] = rw.reward(task_of[ro["uid"]], reward_rows[ro["uid"]], text_, ro["finish"], jev)
                    return ro, None
                return ro, teacher_lp(ro)

            jobs = list(enumerate(p_ for p_ in batch_ for _ in range(G))) if grpo else list(enumerate(batch_))
            with ThreadPoolExecutor(max_workers=len(jobs)) as pool:
                pairs = list(pool.map(rollout_and_score, jobs))
            return {"batch": batch_, "ros": [p_[0] for p_ in pairs], "t_lps": [p_[1] for p_ in pairs],
                    "t0": t0_, "t1": max(done_at), "sampled_with": model_name}

        prefetch_pool = ThreadPoolExecutor(max_workers=1) if overlap else None
        pending = prefetch_pool.submit(collect, 0, current) if overlap else None
        for local_step in range(steps):
            step = start_step + local_step  # global step index (0-based)
            t_wait = time.time()
            got = pending.result() if overlap else collect(local_step, current)
            if got is None:
                log("ran out of prompts")
                break
            batch, ros, t_lps, t0, t1 = got["batch"], got["ros"], got["t_lps"], got["t0"], got["t1"]
            sampled_with = got["sampled_with"]
            wait_s = time.time() - t_wait
            # Start the next step's rollouts now, with the adapter that is loaded (this step's starting policy).
            in_flight = current if overlap and local_step + 1 < steps else None
            pending = prefetch_pool.submit(collect, local_step + 1, current) if in_flight else None
            t2 = time.time()
            model.train()
            opt.zero_grad(set_to_none=True)
            stats = {"loss": 0.0, "rkl": [], "gap": [], "clipped": 0, "tokens": 0, "anchor": [],
                     "eos_adv": [], "eos_t": [], "eos_s": [], "tail_adv": [], "body_adv": []}
            drop = cfg.get("drop_truncated", False)
            beta = cfg.get("kl_anchor_beta", 0.0)
            # Overlong filtering: rollouts that hit the cap are left out of the loss.
            kept = [(ro, tlp) for ro, tlp in zip(ros, t_lps) if ro["ids"] and not (drop and ro["finish"] == "length")]
            if grpo:
                by_uid = {}
                for ro in ros:
                    if ro["reward"] is not None and not (drop and ro["finish"] == "length"):
                        by_uid.setdefault(ro["uid"], []).append(ro["reward"])
                g_mean = {u: sum(v) / len(v) for u, v in by_uid.items()}
                mixed = {u for u, v in by_uid.items() if len(set(v)) > 1}
                kept = [(ro, None) for ro, _ in kept if ro["reward"] is not None and ro["uid"] in mixed]
            # Optional verdict reward (JUDGE): 1 for a correct verdict and first wrong step, 0.5 for a correct
            # verdict only, 0 otherwise; the batch-mean-centred reward times `weight` is added to every token's
            # advantage (a REINFORCE term next to the teacher signal).
            vr = cfg.get("verdict_reward")
            if vr:
                from .baseline import extract_solve_answer, parse_judge_response
                from .solution_verification import compare_answer_detailed
                from .strict_gates import judge_gate, solve_gate  # hedged or contradictory answers earn 0
                key = {p_["uid"]: p_ for p_ in batch}
                for ro in ros:
                    text_ = tok.decode(ro["ids"], skip_special_tokens=True)
                    k_ = key[ro["uid"]]
                    if task == "solve":  # SOLVE: 1 if verifier v2 says correct (truncated answers score 0)
                        ans = extract_solve_answer(text_)[0] if ro["finish"] == "stop" and not solve_gate(text_) else None
                        ro["reward"] = float(ans is not None and
                                             compare_answer_detailed(k_["final_answer"], ans)["answer_status"] == "correct")
                        continue
                    d, st = parse_judge_response(text_)
                    if judge_gate(text_):
                        d = st = None
                    ro["reward"] = (1.0 if d == k_["label"] and st == k_["first_error_step"] else
                                    0.5 if d == k_["label"] else 0.0)
                r_mean = sum(ro["reward"] for ro in ros) / len(ros)
            stats["topk_kl"] = []
            # Micro-batches: rollouts sorted by length and right-padded to the longest in the group, up to
            # `train_micro_tokens` padded tokens. Exact under causal attention (real tokens never see the
            # padding). The top-K loss keeps one rollout per forward pass.
            budget = 0 if topk else cfg.get("train_micro_tokens", 0)
            order = sorted(range(len(kept)), key=lambda i: len(prompt_ids[kept[i][0]["uid"]]) + len(kept[i][0]["ids"]))
            groups, cur = [], []
            for i in order:
                n_i = len(prompt_ids[kept[i][0]["uid"]]) + len(kept[i][0]["ids"])
                if cur and (len(cur) + 1) * n_i > budget:
                    groups.append(cur)
                    cur = []
                cur.append(i)
            if cur:
                groups.append(cur)
            for group in groups:
              seqs = [prompt_ids[kept[i][0]["uid"]] + kept[i][0]["ids"] for i in group]
              width = max(map(len, seqs))
              ids_b = torch.tensor([q + [im_end] * (width - len(q)) for q in seqs], device="cuda:0")
              H = backbone(input_ids=ids_b, use_cache=False).last_hidden_state
              H_ref = None
              if beta > 0 and not topk:
                  with torch.no_grad():
                      if ref_adapter:
                          model.base_model.set_adapter(ref_adapter)
                          try:
                              H_ref = backbone(input_ids=ids_b, use_cache=False).last_hidden_state
                          finally:
                              model.base_model.set_adapter("default")
                      else:
                          with model.disable_adapter():
                              H_ref = backbone(input_ids=ids_b, use_cache=False).last_hidden_state
              group_losses = []
              for j, gi in enumerate(group):
                ro, tinfo = kept[gi]
                tlp = None if grpo else tinfo["lp"]
                if not grpo and len(tlp) != len(ro["ids"]):
                    raise RuntimeError(f"teacher returned {len(tlp)} log-probs for {len(ro['ids'])} tokens")
                p = prompt_ids[ro["uid"]]
                ids = ids_b[j:j + 1, :len(p) + len(ro["ids"])]
                targets = torch.tensor(ro["ids"], device="cuda:0")
                h = H[j, len(p) - 1:len(p) - 1 + len(ro["ids"])]
                lpk = None
                if topk:
                    top = torch.tensor(tinfo["top_ids"], device="cuda:0")
                    lp, lpk = token_logprobs(h, targets, cfg["logprob_chunk_tokens"], top)
                else:
                    lp = token_logprobs(h, targets, cfg["logprob_chunk_tokens"])
                t_ = lp.detach() if grpo else torch.tensor(tlp, device="cuda:0", dtype=torch.float32)
                v_ = torch.tensor([float("nan") if x is None else x for x in ro["vllm_lp"]], device="cuda:0",
                                  dtype=torch.float32)
                v_ = torch.where(torch.isnan(v_), lp.detach(), v_)
                ref = None
                ref_k = None
                if H_ref is not None:  # KL anchor from the group's reference forward pass
                    with torch.no_grad():
                        h_r = H_ref[j, len(p) - 1:len(p) - 1 + len(ro["ids"])]
                        c = cfg["logprob_chunk_tokens"]
                        ref = torch.cat([torch.log_softmax(lm_head(h_r[i:i + c]).float(), -1).gather(-1, targets[i:i + c, None])[:, 0]
                                         for i in range(0, len(targets), c)])
                elif beta > 0:  # KL anchor to the run's starting point (see ref_adapter above)
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
                    if grpo:  # group-relative reward, the same for every token of the rollout
                        adv = torch.full_like(t_, ro["reward"] - g_mean[ro["uid"]])
                    if vr:
                        adv = adv + vr["weight"] * (ro["reward"] - r_mean)
                    if ref is not None and not topk:  # with the top-K loss the anchor is a top-K KL below
                        adv = adv - beta * (lp.detach() - ref)
                    if ro["finish"] == "length" and cfg.get("overlong_penalty", 0.0):
                        adv = adv - cfg["overlong_penalty"]  # DAPO-style: pushes away from running to the cap
                    soft = cfg.get("soft_length_penalty")
                    if soft and len(ro["ids"]) > soft["start"]:  # DAPO soft overlong: linear from start to the cap
                        adv = adv - soft["max"] * min(1.0, (len(ro["ids"]) - soft["start"]) / (cap - soft["start"]))
                    raw_ratio = torch.exp(lp.detach() - v_)
                    ratio = raw_ratio.clamp(max=cfg["importance_sampling_cap"])
                if grpo and cfg.get("norm_tokens"):
                    # Dr. GRPO: token sum over a fixed constant (the generation cap), not the rollout's own
                    # length, so long wrong answers are not penalised less per token than short ones.
                    loss = -(ratio * adv * lp).sum() / cfg["norm_tokens"] / len(kept)
                else:
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
                group_losses.append(loss)
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
              torch.stack(group_losses).sum().backward()
              del H, H_ref, group_losses
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
            # Unload the adapter this step's rollouts were sampled with, unless the prefetch is still using it
            # (overlap: it is then unloaded one step later, when the next prefetch has moved on). Unloading first
            # keeps vLLM's CPU LoRA cache (2 slots) from evicting the adapter the prefetch is using.
            for name in [n for n in (sampled_with, current) if n != "student" and n != in_flight and n != f"s{step + 1}"]:
                if name in loaded_names:
                    post(student_port, "/v1/unload_lora_adapter", {"lora_name": name})
                    loaded_names.discard(name)
                    k_ = int(name[1:])
                    prev = out / "adapters" / f"step{k_}"
                    every = cfg.get("keep_adapters_every", 8)
                    if k_ % every != 0 and k_ not in keep_steps and k_ != start_step and prev.exists():
                        shutil.rmtree(prev)  # keep every Nth, the kept steps and the final one
            post(student_port, "/v1/load_lora_adapter", {"lora_name": f"s{step + 1}", "lora_path": str(path)})
            loaded_names.add(f"s{step + 1}")
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
                   "verdict_reward": (sum(ro["reward"] for ro in ros) / len(ros)) if vr else None,
                   "reward_mean": (sum(ro["reward"] for ro in ros if ro["reward"] is not None) /
                                   max(1, sum(ro["reward"] is not None for ro in ros))) if grpo else None,
                   "reward_failed": sum(ro["reward"] is None for ro in ros) if grpo else None,
                   "groups_mixed": len(mixed) if grpo else None,
                   "per_task": per_task_stats(ros, task_of, mixed, g_mean) if grpo and task == "mixed" else None,
                   "tokens": stats["tokens"], "grad_norm": gnorm, "lr": lr_now, "mean_len": sum(lens) / len(lens), "max_len": max(lens),
                   "truncation_rate": sum(ro["finish"] == "length" for ro in ros) / len(ros),
                   "stopped": sum(ro["finish"] == "stop" for ro in ros),
                   "eos_appended": sum(ro["eos_added"] for ro in ros),
                   "repetition": sum(repetition_score(ro["ids"]) for ro in ros) / len(ros),
                   "seconds": {"rollout": round(t1 - t0, 1), "teacher": round(t2 - t1, 1), "train": round(t3 - t2, 1),
                               "sync": round(t4 - t3, 1), "wait": round(wait_s, 1)},
                   "policy_lag": 1 if overlap and sampled_with != f"s{step}" and step > start_step else 0,
                   "trainer_peak_gib": round(torch.cuda.max_memory_allocated(0) / 2**30, 1),
                   "gpu_memory": subprocess.run(["nvidia-smi", "--query-gpu=memory.used,memory.total", "--format=csv,noheader"],
                                                capture_output=True, text=True).stdout.strip().splitlines()}
            history.append(rec)
            (out / "rollouts").mkdir(exist_ok=True)
            with (out / "rollouts" / f"step{step + 1}.jsonl").open("w") as fh:
                for ro in ros:
                    fh.write(json.dumps({"uid": ro["uid"], "task": task_of[ro["uid"]], "finish": ro["finish"], "tokens": len(ro["ids"]),
                                         "repetition": round(repetition_score(ro["ids"]), 4),
                                         "adv_mean": ro.get("adv_mean"), "eos_adv": ro.get("eos_adv"),
                                         "reward": ro.get("reward"),
                                         "text": tok.decode(ro["ids"])}, ensure_ascii=False) + "\n")
            with metrics_path.open("a") as fh:
                fh.write(json.dumps(rec) + "\n")
            if grpo and cfg.get("best_window"):
                keep_best(out, metrics_path, path, step + 1, cfg["best_window"], cfg.get("best_keep", 3), log)
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
