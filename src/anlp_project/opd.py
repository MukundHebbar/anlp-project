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
    # e.g. {"data": "<sft.jsonl>", "per_step": 16, "weight": 1.0}: an SFT term on teacher answers each step (Stable-OPD)
    "sft_mix": None,
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


def warmup_manifest(task: str, n: int = 512) -> Path:
    """Seeded SFT warm-up questions from the train split, disjoint from the OPD trial slices.

    The order is the shuffled order, so a warm-up on the first k questions is well defined.
    """
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


def slice_rows(task: str, part: str) -> list[dict[str, Any]]:
    wanted = set(json.loads(slice_manifest(task).read_text())["uids"][part])
    rows = [r for r in load_rows(task, "train") if r["uid"] in wanted]
    return sorted(rows, key=lambda r: r["uid"])


def slice_prompts(task: str, part: str) -> list[dict[str, str]]:
    return [{"uid": r["uid"], "prompt": render_prompt(r)} for r in slice_rows(task, part)]
