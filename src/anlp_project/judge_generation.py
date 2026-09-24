"""Generate and resume Qwen-based JUDGE prompt-comparison batches."""

from __future__ import annotations

import argparse
import hashlib
import os
import socket
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .judge_validation import parse_json_response, validate_generated_output
from .paths import ARTIFACTS_DIR, MANIFESTS_DIR, PROMPTS_DIR, PROJECT_ROOT
from .storage import atomic_write_json, read_json


DEFAULT_MANIFEST = MANIFESTS_DIR / "deepmath" / "judge-dev-60-generator.json"
DEFAULT_PROMPT = PROMPTS_DIR / "judge" / "judge_generator_v1_rubric.md"
DEFAULT_OUTPUT = ARTIFACTS_DIR / "qwen3-8b" / "judge" / "prompt-v1-dev-60.json"
DEFAULT_MODEL = "Qwen/Qwen3-8B"
DEFAULT_BATCH_SIZE = 4
DEFAULT_MAX_TOKENS = 4096
DEFAULT_TEMPERATURE = 0.2
DEFAULT_TOP_P = 0.9
DEFAULT_TOP_K = 20
DEFAULT_MAX_MODEL_LEN = 16384
DEFAULT_GPU_MEMORY_UTILIZATION = 0.90

REQUIRED_PROMPT_PLACEHOLDERS = (
    "{problem}",
    "{reference_solution}",
    "{target_label}",
    "{error_type}",
    "{error_position}",
)
ERROR_TYPES_BY_TOPIC = {
    "Algebra": (
        "arithmetic_algebra",
        "sign_inequality",
        "invalid_theorem_condition",
        "unjustified_implication",
        "domain_restriction",
        "missing_case",
    ),
    "Calculus": (
        "arithmetic_algebra",
        "sign_inequality",
        "invalid_theorem_condition",
        "unjustified_implication",
        "domain_restriction",
    ),
    "Discrete Mathematics": (
        "arithmetic_algebra",
        "invalid_theorem_condition",
        "unjustified_implication",
        "missing_case",
        "counting_bijection",
    ),
    "Number Theory": (
        "arithmetic_algebra",
        "sign_inequality",
        "invalid_theorem_condition",
        "unjustified_implication",
        "missing_case",
        "counting_bijection",
    ),
}
ERROR_POSITIONS = ("early", "middle", "late")
ALGORITHM_ERROR_TYPES = ("arithmetic_algebra", "unjustified_implication")


def load_generator_prompt(prompt_path: Path) -> str:
    template = prompt_path.read_text(encoding="utf-8")
    missing = [placeholder for placeholder in REQUIRED_PROMPT_PLACEHOLDERS if placeholder not in template]
    if missing:
        raise ValueError(f"Generator prompt is missing placeholders: {', '.join(missing)}")
    return template


def render_generator_prompt(
    template: str,
    record: dict[str, Any],
    *,
    target_label: str,
    error_type: str,
    error_position: str,
) -> str:
    replacements = {
        "{problem}": str(record["question"]),
        "{reference_solution}": str(record["reference_solution"]),
        "{target_label}": target_label,
        "{error_type}": error_type,
        "{error_position}": error_position,
    }
    rendered = template
    for placeholder, value in replacements.items():
        rendered = rendered.replace(placeholder, value)
    return rendered


def _error_assignment(record: dict[str, Any], position: int) -> tuple[str, str]:
    topic = record.get("broad_topic", "")
    detailed_topic = record.get("topic", "")
    types = (
        ALGORITHM_ERROR_TYPES
        if topic == "Discrete Mathematics" and " -> Algorithms" in detailed_topic
        else ERROR_TYPES_BY_TOPIC.get(topic, ERROR_TYPES_BY_TOPIC["Algebra"])
    )
    return types[position % len(types)], ERROR_POSITIONS[position % len(ERROR_POSITIONS)]


def build_generation_items(records: Iterable[dict[str, Any]], labels: str = "both") -> list[dict[str, Any]]:
    if labels not in {"both", "correct", "incorrect"}:
        raise ValueError(f"Unsupported labels selection: {labels}")
    items: list[dict[str, Any]] = []
    for position, record in enumerate(records):
        selected_labels = ("correct", "incorrect") if labels == "both" else (labels,)
        for label in selected_labels:
            if label == "correct":
                error_type, error_position = "none", "none"
            else:
                error_type, error_position = _error_assignment(record, position)
            items.append(
                {
                    "item_id": f"{record['source_id']}::{label}",
                    "source_id": record["source_id"],
                    "source_index": record["source_index"],
                    "question": record["question"],
                    "final_answer": record.get("final_answer"),
                    "topic": record.get("topic"),
                    "broad_topic": record.get("broad_topic"),
                    "difficulty": record.get("difficulty"),
                    "reference_solution": record["reference_solution"],
                    "target_label": label,
                    "requested_error_type": error_type,
                    "requested_error_position": error_position,
                    "status": "pending",
                }
            )
    return items


def _item_key(item: dict[str, Any]) -> str:
    return str(item.get("item_id"))


def initialize_output(
    output_path: Path,
    items: list[dict[str, Any]],
    metadata: dict[str, Any],
) -> dict[str, Any]:
    if output_path.exists():
        output = read_json(output_path)
        saved_items = output.get("items")
        comparison_fields = (
            "item_id", "source_id", "source_index", "question", "target_label",
            "requested_error_type", "requested_error_position",
        )
        if not isinstance(saved_items, list) or len(saved_items) != len(items):
            raise ValueError("Existing Judge output does not match the requested items")
        for saved, requested in zip(saved_items, items):
            if any(saved.get(field) != requested.get(field) for field in comparison_fields):
                raise ValueError("Existing Judge output has different sources or label/error assignments")
        saved_metadata = output.get("metadata") or {}
        if saved_metadata.get("prompt_sha256") != metadata.get("prompt_sha256"):
            raise ValueError("Existing Judge output has a different prompt hash")
        if saved_metadata.get("model") != metadata.get("model"):
            raise ValueError("Existing Judge output has a different model")
        output.setdefault("metadata", {}).update(metadata)
        return output
    return {"metadata": metadata, "items": items}


def _completion(result: Any) -> tuple[str, str | None, int | None, int | None]:
    choices = getattr(result, "outputs", None) or []
    if not choices:
        raise ValueError("vLLM returned no completion")
    choice = choices[0]
    text = getattr(choice, "text", "")
    if not isinstance(text, str):
        raise ValueError("vLLM completion text was not a string")
    return (
        text.strip(),
        getattr(choice, "finish_reason", None),
        len(getattr(result, "prompt_token_ids", ()) or ()) or None,
        len(getattr(choice, "token_ids", ()) or ()) or None,
    )


def _write(output_path: Path, output: dict[str, Any]) -> None:
    atomic_write_json(output_path, output)


def run_generation(
    llm: Any,
    output: dict[str, Any],
    output_path: Path,
    prompt_template: str,
    *,
    batch_size: int,
    sampling_params: Any,
    retry_failed: bool,
    retry_invalid: bool,
) -> None:
    pending = []
    for item in output["items"]:
        status = item.get("status")
        if status == "completed":
            if retry_invalid and item.get("validation_status") == "invalid":
                pending.append(item)
            continue
        if status == "failed" and not retry_failed:
            continue
        pending.append(item)
    for batch_number, start in enumerate(range(0, len(pending), batch_size), start=1):
        batch = pending[start : start + batch_size]
        prompts = [
            render_generator_prompt(
                prompt_template,
                item,
                target_label=item["target_label"],
                error_type=item["requested_error_type"],
                error_position=item["requested_error_position"],
            )
            for item in batch
        ]
        for item, prompt in zip(batch, prompts):
            item["prompt"] = prompt
            item["prompt_sha256"] = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
            item["batch_number"] = batch_number
        started = time.perf_counter()
        try:
            generated = llm.chat(
                [[{"role": "user", "content": prompt}] for prompt in prompts],
                sampling_params,
                use_tqdm=False,
                chat_template_kwargs={"enable_thinking": False},
            )
            if len(generated) != len(batch):
                raise ValueError(f"vLLM returned {len(generated)} outputs for {len(batch)} prompts")
            elapsed = time.perf_counter() - started
            for item, generated_item in zip(batch, generated):
                response, finish_reason, prompt_tokens, completion_tokens = _completion(generated_item)
                try:
                    parsed = parse_json_response(response)
                    errors = validate_generated_output(
                        parsed,
                        target_label=item["target_label"],
                        requested_error_type=(
                            item["requested_error_type"] if item["target_label"] == "incorrect" else None
                        ),
                        requested_error_position=(
                            item["requested_error_position"] if item["target_label"] == "incorrect" else None
                        ),
                        expected_problem=item["question"],
                        reference_solution=item["reference_solution"],
                    )
                    validation_status = "valid" if not errors else "invalid"
                except (TypeError, ValueError) as error:
                    parsed = None
                    errors = [f"parse_error: {error}"]
                    validation_status = "invalid"
                item.update(
                    {
                        "status": "completed",
                        "response": response,
                        "parsed_output": parsed,
                        "validation_status": validation_status,
                        "validation_errors": errors,
                        "finish_reason": finish_reason,
                        "prompt_tokens": prompt_tokens,
                        "completion_tokens": completion_tokens,
                        "batch_latency_seconds": elapsed,
                        "latency_seconds_approx": elapsed / len(batch),
                    }
                )
            print(f"Judge batch {batch_number}: {len(batch)} completed")
        except Exception as error:
            elapsed = time.perf_counter() - started
            for item in batch:
                item.update(
                    {
                        "status": "failed",
                        "error": f"{error.__class__.__name__}: {error}",
                        "batch_latency_seconds": elapsed,
                    }
                )
            print(f"Judge batch {batch_number}: failed: {error}")
        finally:
            _write(output_path, output)


def _metadata(args: argparse.Namespace, prompt_template: str, item_count: int) -> dict[str, Any]:
    return {
        "model": args.model,
        "task": "JUDGE_GENERATOR",
        "manifest": str(args.manifest),
        "prompt_file": str(args.prompt),
        "prompt_sha256": hashlib.sha256(prompt_template.encode("utf-8")).hexdigest(),
        "item_count": item_count,
        "batch_size": args.batch_size,
        "max_tokens": args.max_tokens,
        "temperature": args.temperature,
        "top_p": args.top_p,
        "top_k": args.top_k,
        "dtype": args.dtype,
        "max_model_len": args.max_model_len,
        "gpu_memory_utilization": args.gpu_memory_utilization,
        "tensor_parallel_size": args.tensor_parallel_size,
        "enable_thinking": False,
        "backend": "vllm",
        "hostname": socket.gethostname(),
        "slurm_job_id": os.getenv("SLURM_JOB_ID"),
        "cuda_visible_devices": os.getenv("CUDA_VISIBLE_DEVICES"),
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--prompt", type=Path, default=DEFAULT_PROMPT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--labels", choices=("both", "correct", "incorrect"), default="both")
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)
    parser.add_argument("--temperature", type=float, default=DEFAULT_TEMPERATURE)
    parser.add_argument("--top-p", type=float, default=DEFAULT_TOP_P)
    parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K)
    parser.add_argument("--dtype", default="auto")
    parser.add_argument("--max-model-len", type=int, default=DEFAULT_MAX_MODEL_LEN)
    parser.add_argument("--gpu-memory-utilization", type=float, default=DEFAULT_GPU_MEMORY_UTILIZATION)
    parser.add_argument("--tensor-parallel-size", type=int, default=1)
    parser.add_argument("--retry-failed", action="store_true")
    parser.add_argument("--retry-invalid", action="store_true")
    parser.add_argument("--prepare-only", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.batch_size < 1 or args.max_tokens < 1 or args.max_model_len < 1 or args.top_k < 1 or args.tensor_parallel_size < 1:
        raise ValueError("batch-size, max-tokens, max-model-len, top-k, and tensor-parallel-size must be positive")
    if not 0 < args.gpu_memory_utilization <= 1:
        raise ValueError("gpu-memory-utilization must be in (0, 1]")
    prompt_template = load_generator_prompt(args.prompt)
    manifest = read_json(args.manifest)
    records = manifest.get("problems")
    if not isinstance(records, list) or not records:
        raise ValueError(f"{args.manifest} must contain a non-empty problems list")
    items = build_generation_items(records, labels=args.labels)
    output = initialize_output(args.output, items, _metadata(args, prompt_template, len(items)))
    if args.prepare_only:
        for item in output["items"]:
            item["prompt"] = render_generator_prompt(
                prompt_template,
                item,
                target_label=item["target_label"],
                error_type=item["requested_error_type"],
                error_position=item["requested_error_position"],
            )
            item["prompt_sha256"] = hashlib.sha256(item["prompt"].encode("utf-8")).hexdigest()
            item["status"] = "prepared"
        output["metadata"]["prepared_only"] = True
        _write(args.output, output)
        print(f"Prepared {len(items)} Judge prompts at {args.output}")
        return

    try:
        from vllm import LLM, SamplingParams
    except ImportError as exc:
        raise RuntimeError("vLLM is required for Judge generation") from exc

    print(f"Loading {args.model} with vLLM")
    llm = LLM(
        model=args.model,
        trust_remote_code=True,
        dtype=args.dtype,
        max_model_len=args.max_model_len,
        gpu_memory_utilization=args.gpu_memory_utilization,
        tensor_parallel_size=args.tensor_parallel_size,
    )
    sampling_params = SamplingParams(
        temperature=args.temperature,
        top_p=args.top_p,
        top_k=args.top_k,
        max_tokens=args.max_tokens,
    )
    run_generation(
        llm,
        output,
        args.output,
        prompt_template,
        batch_size=args.batch_size,
        sampling_params=sampling_params,
        retry_failed=args.retry_failed,
        retry_invalid=args.retry_invalid,
    )
    output["metadata"]["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
    _write(args.output, output)
    print(f"Wrote Judge generation artifact to {args.output}")


if __name__ == "__main__":
    main()
