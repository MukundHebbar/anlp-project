"""Run batched Qwen3-4B EXPLAIN and SOLVE evaluation with vLLM."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import socket
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .paths import ARTIFACTS_DIR, MANIFESTS_DIR, PROMPTS_DIR, PROJECT_ROOT
from .solution_verification import compare_answer_detailed, compare_answers, extract_final_answer, normalize_answer
from .storage import atomic_write_json, read_json


ROOT_DIR = PROJECT_ROOT
DEFAULT_INPUT = MANIFESTS_DIR / "deepmath" / "deepmath-pilot-113-deepseek-v2-correct.json"
DEFAULT_EXPLAIN_OUTPUT = ARTIFACTS_DIR / "qwen3-4b" / "explain" / "v1-colab-111" / "results.json"
DEFAULT_SOLVE_OUTPUT = ARTIFACTS_DIR / "qwen3-4b" / "solve" / "113" / "results.json"
DEFAULT_REPORT = ARTIFACTS_DIR / "qwen3-4b" / "evaluation-report.txt"
DEFAULT_MODEL = "Qwen/Qwen3-4B"
DEFAULT_BATCH_SIZE = 4
DEFAULT_MAX_TOKENS = 8192
DEFAULT_TEMPERATURE = 0.7
DEFAULT_TOP_P = 0.8
DEFAULT_TOP_K = 20
DEFAULT_DTYPE = "auto"
DEFAULT_MAX_MODEL_LEN = 16384
DEFAULT_GPU_MEMORY_UTILIZATION = 0.90
DEFAULT_EXPLAIN_V1_INPUT = ARTIFACTS_DIR / "deepseek-v4-flash" / "explain" / "v1-111" / "results.json"
DEFAULT_STUDENT_EXPLAIN_PROMPT = PROMPTS_DIR / "explain" / "student_explain.md"

EXPLAIN_SYSTEM = """You are answering a mathematics EXPLAIN task. Read the supplied task carefully and explain only why the selected step is valid. Identify the relevant mathematical principle, verify its conditions, and connect it to the supplied result. Do not choose a different strategy, continue solving the original problem, or state the original problem's final answer. Output only your explanation, without XML tags or a private reference answer."""
SOLVE_SYSTEM = """You are solving a mathematics problem. Give a complete, rigorous derivation with no exploratory commentary. End your response with exactly one tag of the form <final_answer>...</final_answer>, containing only the final answer expression or text. Do not put the tag inside a code fence."""

STUDENT_EXPLAIN_PLACEHOLDERS = (
    "{problem}",
    "{established_context}",
    "{step_1}",
    "{step_2}",
    "{transition_question}",
)


def extract_student_task(response: str) -> str:
    match = re.search(r"<student_facing_task>\s*(.*?)\s*</student_facing_task>", response, re.DOTALL)
    if not match:
        raise ValueError("EXPLAIN response has no student_facing_task block")
    task = match.group(1).strip()
    if "<private_reference_answer>" in task:
        raise ValueError("EXPLAIN task unexpectedly exposes private_reference_answer")
    return task


def load_records(input_path: Path, *, explain_only: bool = False) -> list[dict[str, Any]]:
    problems = read_json(input_path).get("problems")
    if not isinstance(problems, list):
        raise ValueError(f"{input_path} must contain a 'problems' list")

    records = []
    for position, problem in enumerate(problems):
        if not isinstance(problem, dict):
            continue
        source_index = problem.get("source_index", position)
        if not isinstance(source_index, int):
            raise ValueError(f"Invalid source_index: {source_index!r}")
        if not problem.get("question") or not problem.get("final_answer"):
            raise ValueError(f"Source index {source_index} lacks question or final_answer")
        task = None
        if problem.get("explain_response_kind") == "task":
            task = extract_student_task(problem.get("explain_response", ""))
        if explain_only and task is None:
            continue
        records.append(
            {
                "source_index": source_index,
                "source_id": problem.get("source_id", f"source-{source_index}"),
                "question": problem["question"],
                "final_answer": problem["final_answer"],
                "topic": problem.get("topic", "unknown"),
                "difficulty": problem.get("difficulty"),
                "explain_task": task,
            }
        )
    if not records:
        scope = "EXPLAIN tasks" if explain_only else "solved records"
        raise ValueError(f"No suitable {scope} were found")
    return records


def load_explain_v1_records(input_path: Path) -> list[dict[str, Any]]:
    """Load only public student-facing fields from the EXPLAIN-v1 batch."""
    batch = read_json(input_path)
    items = batch.get("items")
    if not isinstance(items, list):
        raise ValueError(f"{input_path} must contain an 'items' list")

    records: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get("source_index"), int):
            raise ValueError("EXPLAIN-v1 item has an invalid source_index")
        output = item.get("output")
        if output == "NOT_SUITABLE":
            continue
        if not isinstance(output, dict):
            raise ValueError(f"Source index {item['source_index']} has no EXPLAIN-v1 task")
        task = output.get("student_facing_task")
        if not isinstance(task, dict):
            raise ValueError(f"Source index {item['source_index']} has an invalid student task")
        required = ("problem", "established_context", "solution_skeleton", "transition_to_explain")
        if any(field not in task for field in required):
            raise ValueError(f"Source index {item['source_index']} has incomplete student task")
        if not isinstance(task["problem"], str) or not task["problem"].strip():
            raise ValueError(f"Source index {item['source_index']} has an invalid problem")
        if not isinstance(task["established_context"], list):
            raise ValueError(f"Source index {item['source_index']} has invalid established_context")
        if not isinstance(task["solution_skeleton"], list) or len(task["solution_skeleton"]) != 2:
            raise ValueError(f"Source index {item['source_index']} must have two solution steps")
        if any(
            not isinstance(step, dict)
            or not isinstance(step.get("id"), str)
            or not isinstance(step.get("statement"), str)
            for step in task["solution_skeleton"]
        ):
            raise ValueError(f"Source index {item['source_index']} has invalid solution steps")
        transition = task["transition_to_explain"]
        if not isinstance(transition, dict) or not all(
            isinstance(transition.get(key), str) for key in ("from", "to", "question")
        ):
            raise ValueError(f"Source index {item['source_index']} has an invalid transition")
        records.append(
            {
                "source_index": item["source_index"],
                "problem": task["problem"],
                "established_context": task["established_context"],
                "solution_skeleton": task["solution_skeleton"],
                "transition_to_explain": transition,
            }
        )
    if not records:
        raise ValueError("No suitable EXPLAIN-v1 tasks were found")
    if len({item["source_index"] for item in records}) != len(records):
        raise ValueError("EXPLAIN-v1 source indices are duplicated")
    return records


def build_explain_prompt(task: str) -> str:
    return f"{EXPLAIN_SYSTEM}\n\n<task>\n{task}\n</task>"


def load_student_explain_prompt(prompt_path: Path = DEFAULT_STUDENT_EXPLAIN_PROMPT) -> str:
    """Load and validate the versioned student-facing EXPLAIN prompt."""
    try:
        template = prompt_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ValueError(f"Student EXPLAIN prompt does not exist: {prompt_path}") from exc
    missing = [placeholder for placeholder in STUDENT_EXPLAIN_PLACEHOLDERS if placeholder not in template]
    if missing:
        raise ValueError(f"Student EXPLAIN prompt is missing placeholders: {', '.join(missing)}")
    return template


def student_explain_prompt_metadata(prompt_path: Path, template: str) -> dict[str, Any]:
    return {
        "student_prompt_file": str(prompt_path),
        "student_prompt_sha256": hashlib.sha256(template.encode("utf-8")).hexdigest(),
        "student_prompt_placeholders": list(STUDENT_EXPLAIN_PLACEHOLDERS),
    }


def build_explain_v1_prompt(record: dict[str, Any], prompt_template: str | None = None) -> str:
    """Render the public EXPLAIN-v1 task using the supplied prompt file."""
    template = prompt_template if prompt_template is not None else load_student_explain_prompt()
    context = "\n".join(f"- {fact}" for fact in record["established_context"])
    steps = record["solution_skeleton"]
    if len(steps) != 2:
        raise ValueError("EXPLAIN-v1 requires exactly two public solution steps")
    transition = record["transition_to_explain"]
    return template.format(
        problem=record["problem"],
        established_context=context or "(No additional established facts.)",
        step_1=steps[0]["statement"],
        step_2=steps[1]["statement"],
        transition_question=(
            f"From {transition['from']} to {transition['to']}: {transition['question']}"
        ),
    )


def build_solve_prompt(question: str) -> str:
    return f"{SOLVE_SYSTEM}\n\n<problem>\n{question}\n</problem>"


def verify_final_answer(expected: str, candidate: str | None) -> str:
    status = compare_answers(expected, candidate)
    return "missing_final_answer" if status == "missing" else status


def initialize_output(path: Path, records: list[dict[str, Any]], kind: str, metadata: dict[str, Any]) -> dict[str, Any]:
    if path.exists():
        output = read_json(path)
        saved = output.get("results")
        if not isinstance(saved, list) or [item.get("source_index") for item in saved] != [item["source_index"] for item in records]:
            raise ValueError(f"Existing {kind} output does not match source records")
        output.setdefault("metadata", {}).update(metadata)
        return output
    return {"metadata": metadata, "results": [dict(record) for record in records]}


def _result_from_output(result: Any) -> tuple[str, str | None, int | None, int | None]:
    choices = getattr(result, "outputs", None) or []
    if not choices:
        raise ValueError("vLLM returned no completion")
    choice = choices[0]
    text = getattr(choice, "text", "")
    if not isinstance(text, str):
        raise ValueError("vLLM completion text was not a string")
    completion_tokens = len(getattr(choice, "token_ids", ()) or ()) or None
    prompt_tokens = len(getattr(result, "prompt_token_ids", ()) or ()) or None
    return text.strip(), getattr(choice, "finish_reason", None), prompt_tokens, completion_tokens


def run_suite(
    llm: Any,
    output: dict[str, Any],
    kind: str,
    batch_size: int,
    sampling_params: Any,
    retry_failed: bool,
    prompt_template: str | None = None,
) -> None:
    results = output["results"]
    pending = [
        item
        for item in results
        if item.get("status") != "completed" and not (item.get("status") == "failed" and not retry_failed)
    ]
    for batch_number, start in enumerate(range(0, len(pending), batch_size), start=1):
        batch = pending[start : start + batch_size]
        if kind == "explain_v1":
            prompts = [build_explain_v1_prompt(item, prompt_template) for item in batch]
        else:
            prompts = [
                build_explain_prompt(item["explain_task"])
                if kind == "explain"
                else build_solve_prompt(item["question"])
                for item in batch
            ]
        for item, prompt in zip(batch, prompts):
            item["prompt"] = prompt
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
            per_item = elapsed / len(batch)
            for item, generated_item in zip(batch, generated):
                text, finish_reason, prompt_tokens, completion_tokens = _result_from_output(generated_item)
                item.update(
                    {
                        "status": "completed",
                        "response": text,
                        "response_nonempty": bool(text),
                        "finish_reason": finish_reason,
                        "prompt_tokens": prompt_tokens,
                        "completion_tokens": completion_tokens,
                        "batch_latency_seconds": elapsed,
                        "latency_seconds_approx": per_item,
                    }
                )
                if kind == "solve":
                    extracted, extraction_method = extract_final_answer(text)
                    verification_detail = compare_answer_detailed(item["final_answer"], extracted)
                    item.update(
                        {
                            "extracted_final_answer": extracted,
                            "final_answer_extraction": extraction_method,
                            "verification": verify_final_answer(item["final_answer"], extracted),
                            "verification_detail": verification_detail,
                            "answer_status": verification_detail["answer_status"],
                            "verification_method": verification_detail["verification_method"],
                            "verification_reason": verification_detail.get("verification_reason"),
                            "explain_eligible": verification_detail["answer_status"] == "correct",
                        }
                    )
            print(f"{kind} batch {batch_number}: {len(batch)} completed")
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
            print(f"{kind} batch {batch_number}: failed: {error}")
        finally:
            atomic_write_json(output["_path"], {key: value for key, value in output.items() if key != "_path"})


def build_report(explain: dict[str, Any], solve: dict[str, Any]) -> str:
    explain_results = explain["results"]
    solve_results = solve["results"]
    explain_completed = sum(item.get("status") == "completed" for item in explain_results)
    explain_nonempty = sum(item.get("response_nonempty") for item in explain_results)
    solve_counts = {status: sum(item.get("verification") == status for item in solve_results) for status in ("correct", "incorrect", "missing_final_answer")}
    solve_counts["failed_generation"] = sum(item.get("status") == "failed" for item in solve_results)
    lines = [
        "Qwen3-4B Turing evaluation",
        f"Model: {explain['metadata'].get('model')}",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "EXPLAIN evaluation",
        f"Tasks: {len(explain_results)}",
        f"Generation completed: {explain_completed}/{len(explain_results)}",
        f"Nonempty responses: {explain_nonempty}/{len(explain_results)}",
        "Semantic correctness: not deterministically scored; inspect saved responses against each task's private reference answer.",
        "",
        "SOLVE evaluation",
        f"Questions: {len(solve_results)}",
        f"Correct deterministic final answers: {solve_counts['correct']}/{len(solve_results)}",
        f"Incorrect final answers: {solve_counts['incorrect']}",
        f"Missing/unparseable final answers: {solve_counts['missing_final_answer']}",
        f"Failed generations: {solve_counts['failed_generation']}",
        "",
        "Per-problem results",
    ]
    for item in solve_results:
        lines.append(
            f"SOLVE index {item['source_index']}: expected={item['final_answer']!r}; extracted={item.get('extracted_final_answer')!r}; verification={item.get('verification', item.get('status'))}"
        )
    lines.append("")
    for item in explain_results:
        response = item.get("response", "")
        lines.extend(
            [
                f"EXPLAIN index {item['source_index']} ({item.get('status')}):",
                response if response else f"[no response: {item.get('error', 'empty')}]",
                "",
            ]
        )
    return "\n".join(lines)


def build_explain_v1_report(output: dict[str, Any]) -> str:
    results = output["results"]
    completed = sum(item.get("status") == "completed" for item in results)
    failed = sum(item.get("status") == "failed" for item in results)
    nonempty = sum(bool(item.get("response_nonempty")) for item in results)
    lines = [
        "Qwen3-4B EXPLAIN-v1 evaluation",
        f"Model: {output['metadata'].get('model')}",
        f"Tasks: {len(results)}",
        f"Generation completed: {completed}/{len(results)}",
        f"Nonempty responses: {nonempty}/{len(results)}",
        f"Failed generations: {failed}",
        "Semantic correctness: not automatically scored; inspect saved responses against private references.",
        "",
        "Per-task responses",
    ]
    for item in results:
        lines.extend(
            [
                f"EXPLAIN-v1 index {item['source_index']} ({item.get('status')}):",
                item.get("response", "")
                if item.get("response")
                else f"[no response: {item.get('error', 'empty')}]",
                "",
            ]
        )
    return "\n".join(lines)


def build_solve_report(output: dict[str, Any]) -> str:
    results = output["results"]
    counts = {status: sum(item.get("verification") == status for item in results) for status in ("correct", "incorrect", "unverified", "missing_final_answer")}
    lines = [
        "Qwen3-4B SOLVE evaluation",
        f"Model: {output['metadata'].get('model')}",
        f"Questions: {len(results)}",
        f"Correct deterministic final answers: {counts['correct']}/{len(results)}",
        f"Incorrect final answers: {counts['incorrect']}",
        f"Unverified symbolic answers: {counts['unverified']}",
        f"Missing/unparseable final answers: {counts['missing_final_answer']}",
        f"Failed generations: {sum(item.get('status') == 'failed' for item in results)}",
        f"Strict accuracy: {counts['correct'] / len(results) if results else 0.0:.4f}",
        "",
        "Per-problem results",
    ]
    for item in results:
        lines.append(
            f"SOLVE index {item['source_index']}: expected={item['final_answer']!r}; "
            f"extracted={item.get('extracted_final_answer')!r}; "
            f"verification={item.get('verification', item.get('status'))}"
        )
    return "\n".join(lines) + "\n"


def _metadata(args: argparse.Namespace, kind: str) -> dict[str, Any]:
    return {
        "model": args.model,
        "task_kind": kind,
        "input_file": str(args.input),
        "batch_size": args.batch_size,
        "max_tokens": args.max_tokens,
        "temperature": args.temperature,
        "top_p": args.top_p,
        "top_k": args.top_k,
        "enable_thinking": False,
        "backend": "vllm",
        "hostname": socket.gethostname(),
        "slurm_job_id": os.getenv("SLURM_JOB_ID"),
        "cuda_visible_devices": os.getenv("CUDA_VISIBLE_DEVICES"),
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
    }


def _runtime_metadata() -> dict[str, Any]:
    import sys

    import torch

    cuda_available = bool(torch.cuda.is_available())
    return {
        "python_version": sys.version,
        "torch_version": torch.__version__,
        "torch_cuda_version": getattr(torch.version, "cuda", None),
        "cuda_available": cuda_available,
        "gpu_name": torch.cuda.get_device_name(0) if cuda_available else None,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--explain-output", type=Path, default=DEFAULT_EXPLAIN_OUTPUT)
    parser.add_argument("--solve-output", type=Path, default=DEFAULT_SOLVE_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)
    parser.add_argument("--temperature", type=float, default=DEFAULT_TEMPERATURE)
    parser.add_argument("--top-p", type=float, default=DEFAULT_TOP_P)
    parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K)
    parser.add_argument("--dtype", default=DEFAULT_DTYPE)
    parser.add_argument("--max-model-len", type=int, default=DEFAULT_MAX_MODEL_LEN)
    parser.add_argument("--gpu-memory-utilization", type=float, default=DEFAULT_GPU_MEMORY_UTILIZATION)
    parser.add_argument("--max-num-seqs", type=int, default=None)
    parser.add_argument("--student-prompt", type=Path, default=DEFAULT_STUDENT_EXPLAIN_PROMPT)
    parser.add_argument("--retry-failed", action="store_true")
    parser.add_argument("--mode", choices=("suite", "explain-v1", "solve-only"), default="suite")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.batch_size < 1 or args.max_tokens < 1 or args.top_k < 1 or args.max_model_len < 1:
        raise ValueError("batch-size, max-tokens, top-k, and max-model-len must be positive")
    if args.max_num_seqs is not None and args.max_num_seqs < 1:
        raise ValueError("max-num-seqs must be positive when supplied")
    if not 0 < args.gpu_memory_utilization <= 1:
        raise ValueError("gpu-memory-utilization must be in (0, 1]")
    metadata = {
        "model": args.model,
        "batch_size": args.batch_size,
        "max_tokens": args.max_tokens,
        "temperature": args.temperature,
        "top_p": args.top_p,
        "top_k": args.top_k,
        "dtype": args.dtype,
        "max_model_len": args.max_model_len,
        "gpu_memory_utilization": args.gpu_memory_utilization,
        "max_num_seqs": args.max_num_seqs,
        "enable_thinking": False,
        "backend": "vllm",
    }
    if args.mode == "explain-v1":
        records = load_explain_v1_records(args.input)
        student_prompt = load_student_explain_prompt(args.student_prompt)
        explain = initialize_output(
            args.explain_output,
            records,
            "EXPLAIN-v1",
            {
                **metadata,
                **_metadata(args, "explain-v1"),
                **student_explain_prompt_metadata(args.student_prompt, student_prompt),
                "source_explain_artifact": str(args.input),
                "expected_task_count": len(records),
            },
        )
        explain["_path"] = args.explain_output
    elif args.mode == "solve-only":
        records = load_records(args.input)
        solve = initialize_output(args.solve_output, records, "SOLVE", {**metadata, **_metadata(args, "solve")})
        solve["_path"] = args.solve_output
    else:
        records = load_records(args.input)
        explain_records = [record for record in records if record["explain_task"] is not None]
        explain = initialize_output(args.explain_output, explain_records, "EXPLAIN", {**metadata, **_metadata(args, "explain")})
        solve = initialize_output(args.solve_output, records, "SOLVE", {**metadata, **_metadata(args, "solve")})
        explain["_path"] = args.explain_output
        solve["_path"] = args.solve_output

    try:
        from vllm import LLM, SamplingParams
    except ImportError as exc:
        raise RuntimeError("vLLM is required; install it in the Turing evaluation environment") from exc

    print(f"Loading {args.model} with vLLM")
    llm = LLM(
        model=args.model,
        trust_remote_code=True,
        dtype=args.dtype,
        max_model_len=args.max_model_len,
        gpu_memory_utilization=args.gpu_memory_utilization,
        tensor_parallel_size=1,
        **({"max_num_seqs": args.max_num_seqs} if args.max_num_seqs is not None else {}),
    )
    runtime = _runtime_metadata()
    if args.mode == "explain-v1":
        explain["metadata"].update(runtime)
    elif args.mode == "solve-only":
        solve["metadata"].update(runtime)
    else:
        explain["metadata"].update(runtime)
        solve["metadata"].update(runtime)
    sampling_params = SamplingParams(
        temperature=args.temperature,
        top_p=args.top_p,
        top_k=args.top_k,
        max_tokens=args.max_tokens,
    )
    if args.mode == "explain-v1":
        run_suite(
            llm,
            explain,
            "explain_v1",
            args.batch_size,
            sampling_params,
            args.retry_failed,
            prompt_template=student_prompt,
        )
        explain.pop("_path", None)
        atomic_write_json(args.explain_output, explain)
    elif args.mode == "solve-only":
        run_suite(llm, solve, "solve", args.batch_size, sampling_params, args.retry_failed)
        solve.pop("_path", None)
        atomic_write_json(args.solve_output, solve)
    else:
        run_suite(llm, explain, "explain", args.batch_size, sampling_params, args.retry_failed)
        run_suite(llm, solve, "solve", args.batch_size, sampling_params, args.retry_failed)
        explain.pop("_path", None)
        solve.pop("_path", None)
        atomic_write_json(args.explain_output, explain)
        atomic_write_json(args.solve_output, solve)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        build_explain_v1_report(explain)
        if args.mode == "explain-v1"
        else build_solve_report(solve)
        if args.mode == "solve-only"
        else build_report(explain, solve),
        encoding="utf-8",
    )
    print(f"Wrote report to {args.report}")


if __name__ == "__main__":
    main()
