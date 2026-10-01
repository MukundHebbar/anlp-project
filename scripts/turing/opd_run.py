#!/usr/bin/env python3
"""OPD on one Turing node with three GPUs: teacher on two (tensor parallel), student + trainer on one.

    python scripts/turing/opd_run.py --task reconstruct --out <run dir> --steps 16 --init-adapter <sft>/adapter
    python scripts/turing/opd_run.py --task reconstruct --out <run dir> --steps 8 \
        --resume-from <run dir>/adapters/step8 --start-step 8        # continue after a time limit

Same loop and configuration as the Modal trials (src/anlp_project/opd_train.py, TRIAL_CONFIG).
"""

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from anlp_project import opd  # noqa: E402
from anlp_project.opd_train import run_opd  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", default="reconstruct")
    ap.add_argument("--out", required=True)
    ap.add_argument("--steps", type=int, default=16)
    ap.add_argument("--init-adapter", default="")
    ap.add_argument("--resume-from", default="")
    ap.add_argument("--start-step", type=int, default=0)
    ap.add_argument("--teacher-instruction", default="", choices=["", *opd.TEACHER_INSTRUCTIONS],
                    help="a teacher-only system instruction from opd.TEACHER_INSTRUCTIONS")
    ap.add_argument("--loss", default="sampled", choices=["sampled", "topk"],
                    help="sampled-token reverse KL, or reverse KL on the teacher's renormalised top-K support")
    ap.add_argument("--divergence", default="reverse", choices=["reverse", "jsd", "forward"],
                    help="divergence on the renormalised top-K support (with --loss topk)")
    ap.add_argument("--extra-prompts", action="store_true",
                    help="append opd-extra-<task>.json (512 more train prompts) after the trial slice")
    ap.add_argument("--sft-mix", default="", help="teacher-answer jsonl for an SFT term during OPD (Stable-OPD)")
    ap.add_argument("--sft-per-step", type=int, default=16)
    ap.add_argument("--sft-weight", type=float, default=1.0)
    ap.add_argument("--sft-paired", action="store_true",
                    help="Stable-OPD pairing: each step's SFT term uses the demonstrations for that step's questions")
    ap.add_argument("--sft-keep", default="", help="JSON list of uids whose demonstrations are kept (judge filter)")
    ap.add_argument("--prompts", default="trial", choices=["trial", "warmup"],
                    help="OPD training questions: the trial slice, or the SFT warm-up questions (paired demonstrations)")
    ap.add_argument("--gate", type=int, default=0, help="teacher signal only for rollouts up to this many tokens")
    ap.add_argument("--soft-length", default="", metavar="START:MAX",
                    help="soft length penalty, e.g. 4096:1.0 (rises linearly from START tokens to the cap)")
    ap.add_argument("--set", action="append", default=[], metavar="KEY=VALUE",
                    help="override TRIAL_CONFIG, e.g. optimizer.lr=1e-5 or overlong_penalty=0.3 (JSON values)")
    a = ap.parse_args()

    from huggingface_hub import snapshot_download

    gpus = os.environ.get("CUDA_VISIBLE_DEVICES", "0,1,2").split(",")
    if len(gpus) < 3:
        raise SystemExit(f"need 3 GPUs, have {gpus}")
    cfg = json.loads(json.dumps(opd.TRIAL_CONFIG))
    for item in a.set:
        key, value = item.split("=", 1)
        *parents, leaf = key.split(".")
        node = cfg
        for k in parents:
            node = node[k]
        if leaf not in node:
            raise SystemExit(f"unknown config key {key}")
        node[leaf] = json.loads(value)
    cfg["loss"] = a.loss
    if a.sft_mix:
        cfg["sft_mix"] = {"data": a.sft_mix, "per_step": a.sft_per_step, "weight": a.sft_weight,
                          "paired": a.sft_paired, "keep_uids": a.sft_keep or None}
    cfg["topk_divergence"] = a.divergence
    if a.gate:
        cfg["teacher_signal_max_len"] = a.gate
    if a.soft_length:
        start, peak = a.soft_length.split(":")
        cfg["soft_length_penalty"] = {"start": int(start), "max": float(peak)}
    if a.teacher_instruction:
        cfg["teacher_system_prompt"] = opd.TEACHER_INSTRUCTIONS[a.teacher_instruction]
    B = cfg["prompts_per_step"]
    base_pool = opd.warmup_prompts(a.task) if a.prompts == "warmup" else opd.slice_prompts(a.task, "train")
    pool = base_pool + (opd.extra_prompts(a.task) if a.extra_prompts else [])
    prompts = pool[a.start_step * B:(a.start_step + a.steps) * B]
    res = run_opd(a.task, prompts, cfg, Path(a.out), snapshot_download(cfg["student"], local_files_only=True),
                  snapshot_download(cfg["teacher"], local_files_only=True), steps=a.steps,
                  meta={"platform": "turing-l40s", "gpus": gpus, "overrides": a.set, "prompts": a.prompts}, teacher_gpus=f"{gpus[1]},{gpus[2]}", teacher_tp=2,
                  student_gpu=gpus[0], student_mem=0.35, teacher_mem=0.90,
                  init_adapter=a.init_adapter or None, resume_from=a.resume_from or None,
                  start_step=a.start_step, save_optimizer=True)
    (Path(a.out) / f"result-{a.start_step}.json").write_text(json.dumps(res, indent=1))
    print("\n".join(res.get("events", [])))
    if not res["ok"]:
        print(res["error"][-3000:])
        raise SystemExit(1)


if __name__ == "__main__":
    main()
