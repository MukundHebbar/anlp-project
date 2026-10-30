#!/usr/bin/env python3
"""OPD on one Turing node with three GPUs: teacher on two (tensor parallel), student + trainer on one.

    python scripts/turing/opd_run.py --task reconstruct --out <run dir> --steps 16 --init-adapter <sft>/adapter
    python scripts/turing/opd_run.py --task reconstruct --out <run dir> --steps 8 \
        --resume-from <run dir>/adapters/step8 --start-step 8        # continue after a time limit

Same loop and configuration as the Modal trials (src/anlp_project/opd_train.py, TRIAL_CONFIG).
--config matrix uses opd.MATRIX_CONFIG and the transfer-matrix prompt order (opd.matrix_prompts).
With --teacher-port P --external-teacher, the run uses a teacher already serving on port P and
needs only one GPU (scripts/turing/opd_shared.py starts that teacher for several runs).
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
    ap.add_argument("--task", default="reconstruct", help="solve, judge, reconstruct, or mixed (equal thirds)")
    ap.add_argument("--mixed-per-task", type=int, default=1134, help="questions per task in the mixed pool")
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
    ap.add_argument("--config", default="trial", choices=["trial", "matrix", "opd9b", "grpo"],
                    help="opd9b: OPD from Qwen3.5-9B; grpo: GRPO with anlp_project.rewards (no teacher, 1 GPU)")
    ap.add_argument("--cap", type=int, default=0, help="rollout cap for every task (overrides the config)")
    ap.add_argument("--keep-steps", default="", help="comma-separated steps whose adapters are kept, e.g. 52,104")
    ap.add_argument("--student-port", type=int, default=8000)
    ap.add_argument("--teacher-port", type=int, default=8001)
    ap.add_argument("--external-teacher", action="store_true")
    ap.add_argument("--teacher-host", default="127.0.0.1", help="host of an external teacher (another node)")
    ap.add_argument("--prompts", default="trial", choices=["trial", "warmup", "matrix"],
                    help="OPD training questions: the trial slice, or the SFT warm-up questions (paired demonstrations)")
    ap.add_argument("--prompts-file", default="",
                    help="JSONL of {uid, prompt, label} training prompts (task selfjudge, phase3/build_selfjudge.py)")
    ap.add_argument("--gate", type=int, default=0, help="teacher signal only for rollouts up to this many tokens")
    ap.add_argument("--soft-length", default="", metavar="START:MAX",
                    help="soft length penalty, e.g. 4096:1.0 (rises linearly from START tokens to the cap)")
    ap.add_argument("--set", action="append", default=[], metavar="KEY=VALUE",
                    help="override TRIAL_CONFIG, e.g. optimizer.lr=1e-5 or overlong_penalty=0.3 (JSON values)")
    a = ap.parse_args()

    from huggingface_hub import snapshot_download

    gpus = os.environ.get("CUDA_VISIBLE_DEVICES", "0,1,2").split(",")
    configs = {"trial": opd.TRIAL_CONFIG, "matrix": opd.MATRIX_CONFIG, "opd9b": opd.OPD9B_CONFIG, "grpo": opd.GRPO_CONFIG}
    cfg = json.loads(json.dumps(configs[a.config]))
    need = 1 if (a.external_teacher or a.config == "grpo") else (2 if a.config == "opd9b" else 3)
    # GRPO with 2 visible GPUs: vLLM rollouts on the first, the trainer on the second. The trainer's GPU is
    # set here, before anything imports torch: transformers/peft initialise CUDA on import, after which a
    # change to CUDA_VISIBLE_DEVICES is ignored (the first try put the trainer next to vLLM and ran out of
    # memory). The vLLM server always gets its GPU explicitly (opd_train.serve).
    split = a.config == "grpo" and len(gpus) >= 2
    if split:
        os.environ["CUDA_VISIBLE_DEVICES"] = gpus[1]
    if len(gpus) < need:
        raise SystemExit(f"need {need} GPUs, have {gpus}")
    if a.config != "trial":
        a.prompts = "matrix"
    for item in a.set:
        key, value = item.split("=", 1)
        *parents, leaf = key.split(".")
        node = cfg
        for k in parents:
            node = node[k]
        if leaf not in node:
            raise SystemExit(f"unknown config key {key}")
        node[leaf] = json.loads(value)
    if a.cap:
        cfg["rollout_max_tokens"] = {t: a.cap for t in cfg["rollout_max_tokens"]}
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
    if a.task == "selfjudge":
        cfg["rollout_max_tokens"]["selfjudge"] = a.cap or 8192
        cfg["prompt_max_tokens"] = 17408  # judge prompts carry a whole own attempt (16k cap)
    if a.prompts_file:  # self-judge prompts carry their own label; order as written
        pool = [{**json.loads(line), "task": a.task} for line in open(a.prompts_file)]
    elif a.task == "mixed":  # equal thirds of the three tasks, interleaved (opd.mixed_prompts)
        pool = opd.mixed_prompts(a.mixed_per_task)
    elif a.prompts == "matrix":
        pool = opd.matrix_prompts(a.task, (a.start_step + a.steps) * B)
    else:
        base_pool = opd.warmup_prompts(a.task) if a.prompts == "warmup" else opd.slice_prompts(a.task, "train")
        pool = base_pool + (opd.extra_prompts(a.task) if a.extra_prompts else [])
    prompts = pool[a.start_step * B:(a.start_step + a.steps) * B]
    res = run_opd(a.task, prompts, cfg, Path(a.out), snapshot_download(cfg["student"], local_files_only=True),
                  snapshot_download(cfg["teacher"], local_files_only=True) if cfg.get("teacher") else None, steps=a.steps,
                  meta={"platform": "turing-l40s", "gpus": gpus, "overrides": a.set, "prompts": a.prompts,
                        "config_name": a.config, "external_teacher": a.external_teacher},
                  teacher_gpus=("" if a.external_teacher or a.config == "grpo" else
                                gpus[1] if a.config == "opd9b" else f"{gpus[1]},{gpus[2]}"),
                  teacher_tp=1 if a.config == "opd9b" else 2,
                  student_gpu=gpus[0], student_mem=0.88 if split else 0.35, teacher_mem=0.90,
                  trainer_gpu=gpus[1] if split else None,
                  init_adapter=a.init_adapter or None, resume_from=a.resume_from or None,
                  start_step=a.start_step, save_optimizer=True, student_port=a.student_port,
                  teacher_port=a.teacher_port, external_teacher=a.external_teacher,
                  teacher_host=a.teacher_host,
                  keep_steps=tuple(int(x) for x in a.keep_steps.split(",") if x))
    (Path(a.out) / f"result-{a.start_step}.json").write_text(json.dumps(res, indent=1))
    print("\n".join(res.get("events", [])))
    if not res["ok"]:
        print(res["error"][-3000:])
        raise SystemExit(1)


if __name__ == "__main__":
    main()
