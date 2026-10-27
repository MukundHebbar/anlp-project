"""On-policy distillation (OPD) trial: data slices, configuration and step diagnostics.

The training loop itself runs on Modal (``scripts/modal_opd.py``); this module holds the
parts that are decided locally: which training questions are used, the frozen trial
configuration, and pure-Python helpers for monitoring. Only the FINAL-v3 *train* split is
used; the test split is never touched by a trial.
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

from .baseline import MANIFESTS_DIR, load_rows, render_prompt
from .opd_monitor import repetition_score, should_stop  # noqa: F401  (re-exported)

TRIAL_DIR = MANIFESTS_DIR / "final-v3"
SLICE_SEED = 20260930

# Frozen OPD v1 trial configuration (see docs/research/transfer-study/baselines-and-opd-method.md).
TRIAL_CONFIG: dict[str, Any] = {
    "student": "Qwen/Qwen3.5-2B",
    "teacher": "Qwen/Qwen3.8-27B",
    "objective": "per-token reverse KL, sampled-token estimator, discount 0",
    "loss_normalization": "token mean per rollout, then mean over rollouts",
    "importance_sampling_cap": 2.0,  # token-level truncated IS for vLLM-vs-trainer mismatch
    "lora": {"r": 64, "alpha": 64, "dropout": 0.0,
             "target_modules": ["q_proj", "k_proj", "v_proj", "o_proj", "in_proj_qkv", "in_proj_z",
                                "out_proj", "gate_proj", "up_proj", "down_proj"]},
    "optimizer": {"name": "adamw", "lr": 5e-5, "betas": [0.9, 0.999], "weight_decay": 0.0,
                  "warmup_steps": 0, "grad_clip": 1.0},
    "prompts_per_step": 32,
    "samples_per_prompt": 1,
    "updates_per_step": 1,  # sync the adapter into vLLM after every update (strictly on-policy)
    "rollout": {"temperature": 1.0, "top_p": 1.0},
    # One cap for all three arms: at T 1.0 the student's JUDGE/RECONSTRUCT answers exceed 8k in
    # 12-16% of cases but 16k in about 1% (protocol-v2 test baseline).
    "rollout_max_tokens": {"solve": 16384, "judge": 16384, "reconstruct": 16384},
    "logprob_chunk_tokens": 1024,
    # Repetition stop (added after the RECONSTRUCT collapse, where repetition went 0.05 -> 0.58;
    # healthy SOLVE/JUDGE runs peaked at 0.48 / 0.29 for single steps).
    # Truncation stop: above max(step-1 rate + rise, ceiling) for `patience` steps. The ceiling
    # (added 2026-10-01) keeps a run that plateaus near 20% from being stopped as a collapse.
    "auto_stop": {"truncation_rise": 0.15, "truncation_ceiling": 0.35, "patience": 3, "max_mean_abs_logprob_gap": 0.5,
                  "repetition_threshold": 0.5, "repetition_patience": 2},
    # Fixes for length/repetition collapse, off by default (see the RECONSTRUCT fix trials).
    "drop_truncated": False,
    "kl_anchor_beta": 0.0,
    "overlong_penalty": 0.0,  # subtracted from every token's advantage in rollouts that hit the cap
    # e.g. {"start": 4096, "max": 1.0}: a penalty rising linearly from `start` tokens to the cap
    "soft_length_penalty": None,
    "teacher_system_prompt": None,  # optional instruction in the teacher's context only
    # "sampled": sampled-token reverse KL (the advantage above). "topk": reverse KL between student and
    # teacher renormalised over the teacher's top-K tokens at each position (Revisiting OPD, 2603.25562).
    "loss": "sampled",
    "teacher_signal_max_len": None,  # e.g. 8192: longer rollouts get only the length penalties
    "prompt_max_tokens": 4096,  # vLLM context = rollout cap + this (judging the policy's own long attempts needs more)
    # e.g. {"data": "<sft.jsonl>", "per_step": 16, "weight": 1.0}: an SFT term on teacher answers each step (Stable-OPD)
    "sft_mix": None,
    "verdict_reward": None,  # JUDGE/SOLVE, e.g. {"weight": 0.5}: OPD plus a REINFORCE term on the checkable answer
    "topk_k": 20,
    "topk_divergence": "reverse",  # or "jsd" (GKD, weight 0.5) or "forward", on the renormalised top-K support
}


def make_slices(task: str, n_train: int, n_dev: int, seed: int = SLICE_SEED) -> dict[str, list[str]]:
    """Disjoint, seeded train and dev slices from the FINAL-v3 train split of one task."""
    rows = load_rows(task, "train")
    if any(r["split"] != "train" for r in rows):
        raise ValueError("OPD slices must come from the train split")
    uids = sorted(r["uid"] for r in rows)
    random.Random(f"{seed}:{task}").shuffle(uids)
    if n_train + n_dev > len(uids):
        raise ValueError("slices larger than the split")
    return {"train": sorted(uids[:n_train]), "dev": sorted(uids[n_train:n_train + n_dev])}


def slice_manifest(task: str, n_train: int = 512, n_dev: int = 200) -> Path:
    path = TRIAL_DIR / f"opd-trial-{task}.json"
    if path.exists():
        data = json.loads(path.read_text())
        if (len(data["uids"]["train"]), len(data["uids"]["dev"])) != (n_train, n_dev):
            raise ValueError(f"{path} exists with different slice sizes")
        return path
    uids = make_slices(task, n_train, n_dev)
    path.write_text(json.dumps({
        "description": "OPD trial slices from the FINAL-v3 train split: 'train' for rollouts, 'dev' (disjoint) for evaluation.",
        "task": task, "seed": SLICE_SEED, "uids": uids}, indent=1) + "\n")
    return path


# Teacher-only instructions (context distillation). "anti_repetition" was probed on the collapsed
# RECONSTRUCT answers: teacher log-prob on loop tokens -0.083 -> -0.215, other tokens within 0.02.
TEACHER_INSTRUCTIONS = {
    "anti_repetition": ("Be concise. Never repeat a sentence, calculation or list item you have already written. "
                        "If you notice that you are repeating yourself or going in circles, stop, commit to your best "
                        "answer and finish the required output format immediately."),
}

WARMUP_SEED = 20261001
# Warm-up questions per task. SOLVE and JUDGE draw more because their filter also requires a
# correct teacher answer within the 4k training cap (transfer matrix, 2026-10-01).
WARMUP_N = {"solve": 640, "judge": 640, "reconstruct": 512}


def warmup_manifest(task: str, n: int | None = None) -> Path:
    """Seeded SFT warm-up questions from the train split, disjoint from the OPD trial slices.

    The order is the shuffled order, so a warm-up on the first k questions is well defined.
    """
    n = n or WARMUP_N[task]
    path = TRIAL_DIR / f"sft-warmup-{task}.json"
    if path.exists():
        data = json.loads(path.read_text())
        if len(data["uids"]) != n:
            raise ValueError(f"{path} exists with a different size")
        return path
    trial = json.loads(slice_manifest(task).read_text())["uids"]
    taken = set(trial["train"]) | set(trial["dev"])
    rows = load_rows(task, "train")
    if any(r["split"] != "train" for r in rows):
        raise ValueError("warm-up questions must come from the train split")
    uids = sorted(r["uid"] for r in rows if r["uid"] not in taken)
    random.Random(f"{WARMUP_SEED}:{task}").shuffle(uids)
    path.write_text(json.dumps({
        "description": "SFT warm-up questions (teacher answers) from the FINAL-v3 train split, disjoint from "
                       "the OPD trial train and dev slices. Shuffled order; a warm-up on k questions uses the first k.",
        "task": task, "seed": WARMUP_SEED, "uids": uids[:n]}, indent=1) + "\n")
    return path


EXTRA_SEED = 20261002


def extra_manifest(task: str, n: int = 512) -> Path:
    """More OPD training prompts from the train split, disjoint from the trial slices and the SFT warm-up set."""
    path = TRIAL_DIR / f"opd-extra-{task}.json"
    if path.exists():
        data = json.loads(path.read_text())
        if len(data["uids"]) != n:
            raise ValueError(f"{path} exists with a different size")
        return path
    trial = json.loads(slice_manifest(task).read_text())["uids"]
    warm = json.loads(warmup_manifest(task).read_text())["uids"]
    taken = set(trial["train"]) | set(trial["dev"]) | set(warm)
    rows = load_rows(task, "train")
    uids = sorted(r["uid"] for r in rows if r["uid"] not in taken and r["split"] == "train")
    random.Random(f"{EXTRA_SEED}:{task}").shuffle(uids)
    path.write_text(json.dumps({
        "description": "Extra OPD training prompts from the FINAL-v3 train split, disjoint from the OPD trial train/dev "
                       "slices and the SFT warm-up questions. Used after the trial slice (steps 17+).",
        "task": task, "seed": EXTRA_SEED, "uids": uids[:n]}, indent=1) + "\n")
    return path


def extra_rows(task: str, n: int) -> list[dict[str, Any]]:
    """The first ``n`` extra questions as dataset rows (an additional held-out evaluation set)."""
    order = json.loads(extra_manifest(task).read_text())["uids"][:n]
    by_uid = {r["uid"]: r for r in load_rows(task, "train")}
    return [by_uid[u] for u in order]


def extra_prompts(task: str) -> list[dict[str, str]]:
    order = json.loads(extra_manifest(task).read_text())["uids"]
    by_uid = {r["uid"]: r for r in load_rows(task, "train")}
    return [{"uid": u, "prompt": render_prompt(by_uid[u])} for u in order]


def warmup_rows(task: str) -> list[dict[str, Any]]:
    order = json.loads(warmup_manifest(task).read_text())["uids"]
    by_uid = {r["uid"]: r for r in load_rows(task, "train")}
    return [by_uid[u] for u in order]


def warmup_prompts(task: str) -> list[dict[str, str]]:
    order = json.loads(warmup_manifest(task).read_text())["uids"]
    by_uid = {r["uid"]: r for r in load_rows(task, "train")}
    return [{"uid": u, "prompt": render_prompt(by_uid[u])} for u in order]


MATRIX_SEED = 20261003

# Transfer-matrix recipe (2026-10-01): the regularised SFT-470 recipe with a 4k rollout cap for all
# arms, 64 prompts per step, teacher scoring overlapped with rollouts and micro-batched training.
MATRIX_CONFIG: dict[str, Any] = {
    **json.loads(json.dumps(TRIAL_CONFIG)),
    "prompts_per_step": 64,
    "rollout_max_tokens": {"solve": 4096, "judge": 4096, "reconstruct": 4096},
    "kl_anchor_beta": 0.5,
    "overlong_penalty": 1.0,
    "teacher_system_prompt": TEACHER_INSTRUCTIONS["anti_repetition"],
    "train_micro_tokens": 16384,  # right-padded micro-batches up to this many tokens (0 = one rollout at a time)
    "keep_adapters_every": 8,
}


# Transfer study v3 (2026-10-06, docs/plans/2026-10-06-grpo-opd-transfer.md): the matrix recipe with the
# Qwen3.5-9B teacher (the 27B is now the final judge only) and student prompts v2. One cap for every arm.
TEACHER_9B = "Qwen/Qwen3.5-9B"
V3_CAP = 16384  # decided 2026-10-06: a third of v2 answers exceed 8k, almost none looping
OPD9B_CONFIG: dict[str, Any] = {
    **json.loads(json.dumps(MATRIX_CONFIG)),
    "teacher": TEACHER_9B,
    "rollout_max_tokens": {"solve": V3_CAP, "judge": V3_CAP, "reconstruct": V3_CAP},
}
# Dr. GRPO (Liu et al. 2025, "Understanding R1-Zero-Like Training"): no teacher. 8 prompts x 8 samples = 64
# rollouts per step, as OPD. Advantage = reward - mean reward of the prompt's group, with no std division, the
# same for every token; loss = token sum over a fixed constant (the generation cap), with no 1/|o| per-answer
# normalization. Both remove GRPO's length and difficulty biases. No KL anchor; truncated rollouts are
# filtered. Rewards: anlp_project.rewards.
GRPO_CONFIG: dict[str, Any] = {
    **json.loads(json.dumps(OPD9B_CONFIG)),
    "method": "grpo",
    "teacher": None,
    "prompts_per_step": 8,
    "samples_per_prompt": 8,
    "kl_anchor_beta": 0.0,       # standard for GRPO; OPD keeps 0.5
    "overlong_penalty": 0.0,     # truncated rollouts are filtered instead (DAPO overlong filtering)
    # Truncated rollouts stay in, with reward 0, inside their group (Dr. GRPO as published). Filtering them
    # (DAPO) removed every signal against running long: on 2026-10-06 JUDGE went from 2% to 67% truncation in
    # 12 steps and SOLVE was drifting the same way.
    "drop_truncated": False,
    "variant": "dr_grpo",
    "norm_tokens": V3_CAP,       # Dr. GRPO constant normalizer: the generation cap
    "teacher_system_prompt": None,
    "reward_timeout_s": 180,
    # Generate step s+1's rollouts while step s trains (one-update policy lag, corrected by the capped IS
    # ratio). About halves the step time when rollouts and training take similar time (SOLVE, 2026-10-07).
    "async_rollouts": False,
    # Keep the `best_keep` adapters with the highest `best_window`-step rolling mean training reward
    # (adapters/best-step<k>, out/best.json). 0 = off.
    "best_window": 0,
    "best_keep": 3,
    # Judge for the JUDGE explanation and RECONSTRUCT rewards: "jev" (the Jev API) or "qwen" (Qwen3.8-27B logit judge,
    # qwen_judging.QwenJudge, already serving on reward_judge_port; it answers Jev's questions in Jev's shape), or "none"
    # when every JUDGE row is verdict_only (no explanation score is needed).
    "reward_judge": "jev",
    "reward_judge_port": 8002,
    # Optional jsonl of extra answer-key rows (FINAL-v3 row format) for prompts outside the train split, such as
    # auxiliary items built during training (phase2/failure_driven).
    "extra_reward_rows": None,
}


def matrix_manifest(task: str) -> Path:
    """OPD training order for the transfer matrix: every train question except the dev slice, shuffled.

    The warm-up questions are included (their teacher answers are SFT data, not OPD targets).
    """
    path = TRIAL_DIR / f"opd-matrix-{task}.json"
    if path.exists():
        return path
    dev = set(json.loads(slice_manifest(task).read_text())["uids"]["dev"])
    rows = load_rows(task, "train")
    if any(r["split"] != "train" for r in rows):
        raise ValueError("OPD prompts must come from the train split")
    uids = sorted(r["uid"] for r in rows if r["uid"] not in dev)
    random.Random(f"{MATRIX_SEED}:{task}").shuffle(uids)
    path.write_text(json.dumps({
        "description": "Transfer-matrix OPD prompts: the FINAL-v3 train split minus the 200-question dev slice, "
                       "shuffled. Epoch k > 1 reshuffles with seed MATRIX_SEED:task:k.",
        "task": task, "seed": MATRIX_SEED, "uids": uids}, indent=1) + "\n")
    return path


def matrix_prompts(task: str, n: int) -> list[dict[str, str]]:
    """The first ``n`` OPD prompts, repeating the pool in a fresh shuffled order for each further epoch."""
    order = json.loads(matrix_manifest(task).read_text())["uids"]
    by_uid = {r["uid"]: r for r in load_rows(task, "train")}
    seq, epoch = list(order), 1
    while len(seq) < n:
        epoch += 1
        nxt = list(order)
        random.Random(f"{MATRIX_SEED}:{task}:{epoch}").shuffle(nxt)
        seq += nxt
    out = []
    for u in seq[:n]:
        item = {"uid": u, "prompt": render_prompt(by_uid[u])}
        if task == "solve":  # answer key, used only by the optional answer reward
            item["final_answer"] = by_uid[u]["final_answer"]
        if task == "judge":  # answer key, used only by the optional verdict reward
            key = by_uid[u]["private"]
            item["label"] = key["label"]
            item["first_error_step"] = key["first_error_step_id"] if key["label"] == "incorrect" else "none"
        out.append(item)
    return out


MIXED_TASKS = ("solve", "judge", "reconstruct")


def mixed_manifest(n_per_task: int = 1134) -> Path:
    """Equal-thirds GRPO mixture: the first ``n_per_task`` questions of each task's transfer-matrix order (train
    split minus the dev slice), interleaved solve, judge, reconstruct, solve, ... so that any batch whose size is a
    multiple of 3 and starts at a multiple of 3 holds equal numbers of each task."""
    path = TRIAL_DIR / f"grpo-mixed-{n_per_task}.json"
    if not path.exists():
        orders = {t: json.loads(matrix_manifest(t).read_text())["uids"][:n_per_task] for t in MIXED_TASKS}
        if any(len(o) < n_per_task for o in orders.values()):
            raise ValueError("n_per_task is larger than a task's training pool")
        uids = [orders[t][i] for i in range(n_per_task) for t in MIXED_TASKS]
        path.write_text(json.dumps({
            "description": "Mixed-task GRPO prompts: equal thirds of SOLVE, JUDGE and RECONSTRUCT from the FINAL-v3 "
                           "train splits minus each dev slice (the transfer-matrix orders), interleaved S, J, R.",
            "n_per_task": n_per_task, "tasks": list(MIXED_TASKS), "uids": uids}, indent=1) + "\n")
    return path


def mixed_prompts(n_per_task: int = 1134) -> list[dict[str, str]]:
    """The mixed manifest's prompts in order; each item carries its ``task``."""
    uids = json.loads(mixed_manifest(n_per_task).read_text())["uids"]
    items = {}
    for t in MIXED_TASKS:
        for item in matrix_prompts(t, n_per_task):
            items[item["uid"]] = {**item, "task": t}
    return [items[u] for u in uids]


def slice_rows(task: str, part: str) -> list[dict[str, Any]]:
    wanted = set(json.loads(slice_manifest(task).read_text())["uids"][part])
    rows = [r for r in load_rows(task, "train") if r["uid"] in wanted]
    return sorted(rows, key=lambda r: r["uid"])


def slice_prompts(task: str, part: str) -> list[dict[str, str]]:
    return [{"uid": r["uid"], "prompt": render_prompt(r)} for r in slice_rows(task, part)]
