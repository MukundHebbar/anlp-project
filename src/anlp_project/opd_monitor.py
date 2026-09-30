"""Dependency-free OPD step monitors, shipped into the Modal training image as a single file."""

from __future__ import annotations

from typing import Any


def repetition_score(token_ids: list[int], n: int = 8, window: int = 4096) -> float:
    """Share of repeated n-grams in the last ``window`` tokens (0 = none, near 1 = looping)."""
    tail = token_ids[-window:]
    grams = [tuple(tail[i:i + n]) for i in range(len(tail) - n + 1)]
    return 1.0 - len(set(grams)) / len(grams) if grams else 0.0


def should_stop(history: list[dict[str, Any]], config: dict[str, Any]) -> str | None:
    """Automatic stop rule, applied after every step. Returns a reason or None."""
    rule = config["auto_stop"]
    if not history:
        return None
    last = history[-1]
    for key in ("loss", "mean_abs_logprob_gap"):
        value = last.get(key)
        if value is None or value != value:  # NaN
            return f"{key} is missing or NaN"
    if last["mean_abs_logprob_gap"] > rule["max_mean_abs_logprob_gap"]:
        return f"vLLM/trainer log-prob gap {last['mean_abs_logprob_gap']:.3f} is too large"
    threshold, patience = rule.get("repetition_threshold"), rule.get("repetition_patience", 2)
    tail = history[-patience:]
    if threshold is not None and len(tail) == patience and all(h.get("repetition", 0) > threshold for h in tail):
        return f"repetition above {threshold} for {patience} steps ({tail[-1]['repetition']:.2f})"
    base = history[0]["truncation_rate"]
    recent = history[-rule["patience"]:]
    if len(recent) == rule["patience"] and all(h["truncation_rate"] > base + rule["truncation_rise"] for h in recent):
        return f"truncation rose from {base:.2f} to {recent[-1]['truncation_rate']:.2f}"
    return None
