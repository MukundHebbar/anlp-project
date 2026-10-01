#!/usr/bin/env python3
"""SFT warm-up of the student on filtered teacher answers (LoRA, the same adapter shape as OPD).

    python scripts/turing/sft.py --data <gen dir>/sft.jsonl --out <run dir> [--n 256]

Loss: cross-entropy on the answer tokens only (the prompt is masked), token mean over each
optimiser batch. The saved adapter (<out>/adapter) is the starting point of OPD.
"""

import argparse
import json
import math
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from anlp_project import opd  # noqa: E402

SFT_CONFIG = {
    "examples": 256,          # the first N filtered teacher answers, in warm-up manifest order
    "epochs": 1,
    "batch_size": 16,         # examples per optimiser step (micro-batch 1, gradient accumulation)
    "lr": 1e-4,
    "min_lr": 1e-5,           # cosine decay target
    "warmup_steps": 3,
    "weight_decay": 0.0,
    "betas": [0.9, 0.999],
    "grad_clip": 1.0,
    "shuffle_seed": 20261001,
    "logprob_chunk_tokens": 1024,
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--n", type=int, default=SFT_CONFIG["examples"])
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    cfg = {**SFT_CONFIG, "examples": a.n, "lora": opd.TRIAL_CONFIG["lora"], "student": opd.TRIAL_CONFIG["student"],
           "data": a.data}
    rows = [json.loads(l) for l in open(a.data)][: a.n]
    if len(rows) < a.n:
        raise SystemExit(f"only {len(rows)} filtered examples, need {a.n}")
    (out / "config.json").write_text(json.dumps(cfg, indent=1))

    import torch
    from huggingface_hub import snapshot_download
    from peft import LoraConfig, get_peft_model
    from torch.utils.checkpoint import checkpoint
    from transformers import AutoTokenizer, Qwen3_5ForConditionalGeneration

    torch.manual_seed(0)
    path = snapshot_download(cfg["student"], local_files_only=True)
    tok = AutoTokenizer.from_pretrained(path)
    model = Qwen3_5ForConditionalGeneration.from_pretrained(path, dtype=torch.bfloat16, attn_implementation="sdpa").to("cuda:0")
    lc = cfg["lora"]
    model = get_peft_model(model, LoraConfig(r=lc["r"], lora_alpha=lc["alpha"], lora_dropout=lc["dropout"],
                                             target_modules=list(lc["target_modules"]), exclude_modules=r".*visual.*",
                                             bias="none"))
    model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
    model.enable_input_require_grads()
    params = [p for p in model.parameters() if p.requires_grad]
    opt = torch.optim.AdamW(params, lr=cfg["lr"], betas=tuple(cfg["betas"]), weight_decay=cfg["weight_decay"])
    backbone, lm_head = model.base_model.model.model, model.base_model.model.lm_head

    examples = []
    for r in rows:
        text = tok.apply_chat_template([{"role": "user", "content": r["prompt"]}], tokenize=False,
                                       add_generation_prompt=True, enable_thinking=False)
        examples.append((tok(text, add_special_tokens=False)["input_ids"], r["response_ids"]))
    order = []
    for e in range(cfg["epochs"]):
        idx = list(range(len(examples)))
        random.Random(f"{cfg['shuffle_seed']}:{e}").shuffle(idx)
        order += idx
    B = cfg["batch_size"]
    total = math.ceil(len(order) / B)

    def lr_at(step):  # step is 0-based
        if step < cfg["warmup_steps"]:
            return cfg["lr"] * (step + 1) / cfg["warmup_steps"]
        t = (step - cfg["warmup_steps"]) / max(1, total - cfg["warmup_steps"] - 1)
        return cfg["min_lr"] + 0.5 * (cfg["lr"] - cfg["min_lr"]) * (1 + math.cos(math.pi * min(1.0, t)))

    def token_logprobs(h, targets, chunk):
        def f(hc, tc):
            return torch.log_softmax(lm_head(hc).float(), -1).gather(-1, tc[:, None])[:, 0]
        return torch.cat([checkpoint(f, h[i:i + chunk], targets[i:i + chunk], use_reentrant=False)
                          for i in range(0, len(targets), chunk)])

    log = (out / "metrics.jsonl").open("a")
    model.train()
    for step in range(total):
        t0 = time.time()
        batch = [examples[i] for i in order[step * B:(step + 1) * B]]
        n_tok = sum(len(resp) for _, resp in batch)
        for g in opt.param_groups:
            g["lr"] = lr_at(step)
        opt.zero_grad(set_to_none=True)
        loss_sum = 0.0
        for prompt, resp in batch:
            ids = torch.tensor([prompt + resp], device="cuda:0")
            h = backbone(input_ids=ids, use_cache=False).last_hidden_state[0, len(prompt) - 1:len(prompt) - 1 + len(resp)]
            lp = token_logprobs(h, torch.tensor(resp, device="cuda:0"), cfg["logprob_chunk_tokens"])
            loss = -lp.sum() / n_tok
            loss.backward()
            loss_sum += loss.item()
            del h, lp, loss
        gnorm = torch.nn.utils.clip_grad_norm_(params, cfg["grad_clip"]).item()
        opt.step()
        rec = {"step": step + 1, "of": total, "loss": loss_sum, "grad_norm": gnorm, "lr": lr_at(step),
               "tokens": n_tok, "seconds": round(time.time() - t0, 1),
               "peak_gib": round(torch.cuda.max_memory_allocated(0) / 2**30, 1)}
        log.write(json.dumps(rec) + "\n")
        log.flush()
        print(json.dumps(rec), flush=True)
    model.save_pretrained(str(out / "adapter"))
    print(f"saved {out / 'adapter'}", flush=True)


if __name__ == "__main__":
    main()
