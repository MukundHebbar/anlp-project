"""Local-first RECONSTRUCT generation, inference, evaluation, and reporting."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import random
import re
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .paths import ARTIFACTS_DIR, ENV_FILE, MANIFESTS_DIR, PROJECT_ROOT
from .storage import atomic_write_json, atomic_write_text, read_json


DEFAULT_MODEL = "Qwen/Qwen3-4B"
DEFAULT_TEACHER_MODEL = "deepseek-ai/DeepSeek-V4.1-Flash"
DEFAULT_LOCAL_URL = "http://127.0.0.1:8080/v1"
DEFAULT_DEEPINFRA_URL = "https://api.deepinfra.com/v1/openai"
DEFAULT_MANIFEST = MANIFESTS_DIR / "deepmath" / "deepmath-pilot-113-deepseek-v2-correct.json"
DEFAULT_SOURCE = MANIFESTS_DIR / "deepmath" / "deepmath-pilot-146.json"
DEFAULT_SOLUTIONS = ARTIFACTS_DIR / "deepseek-v4-flash" / "solve" / "146" / "results.json"
DEFAULT_RUN = ARTIFACTS_DIR / "reconstruct" / "pilot-v1" / "run.json"
DEFAULT_REPORT = ARTIFACTS_DIR / "reconstruct" / "pilot-v1" / "report.md"
DEFAULT_PROMPT_DIR = PROJECT_ROOT / "data" / "prompts" / "reconstruct" / "runtime"
DEFAULT_JUDGE_FIXTURES = PROJECT_ROOT / "data" / "manifests" / "reconstruct-judge-fixtures.json"

TOPIC_BUCKETS = ("Algebra", "Number Theory", "Discrete Mathematics", "Calculus")


@dataclass(frozen=True)
class SamplingConfig:
    temperature: float = 0.7
    top_p: float = 0.8
    top_k: int = 20
    max_tokens: int = 16384
    seed: int = 0


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def stable_hash(value: Any) -> str:
    text = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def repair_json_backslashes(text: str) -> str:
    """Escape model-emitted LaTeX backslashes without reprocessing inserted escapes."""

    pieces: list[str] = []
    index = 0
    valid_json_escapes = set('"\\/bfnrtu')
    while index < len(text):
        if text[index] != "\\":
            pieces.append(text[index])
            index += 1
            continue
        tail = text[index + 1 :]
        if tail.startswith("\\"):
            pieces.append("\\\\")
            index += 2
            continue
        latex_command = re.match(r"[A-Za-z]{2,}", tail)
        next_character = tail[:1]
        pieces.append("\\\\" if latex_command or next_character not in valid_json_escapes else "\\")
        index += 1
    return "".join(pieces)


def extract_json_object(text: str) -> dict[str, Any]:
    """Parse a JSON object from plain or fenced output without evaluating text."""

    stripped = text.strip()
    candidates = [stripped]
    fenced = re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", stripped, re.DOTALL | re.IGNORECASE)
    candidates.extend(fenced)
    start, end = stripped.find("{"), stripped.rfind("}")
    if start >= 0 and end > start:
        candidates.append(stripped[start : end + 1])
    errors: list[str] = []
    for candidate in candidates:
        repaired = repair_json_backslashes(candidate)
        versions = (repaired, candidate) if repaired != candidate else (candidate,)
        for version in versions:
            try:
                parsed = json.loads(version)
            except json.JSONDecodeError as exc:
                errors.append(str(exc))
                continue
            if isinstance(parsed, dict):
                return parsed
    raise ValueError(f"No JSON object found ({'; '.join(errors[-2:])})")


def broad_topic(topic: str) -> str:
    for bucket in TOPIC_BUCKETS:
        if bucket.lower() in topic.lower():
            return bucket
    return topic.split(" -> ")[1] if " -> " in topic else topic


def load_sources(manifest_path: Path, source_path: Path, solutions_path: Path) -> list[dict[str, Any]]:
    manifest = read_json(manifest_path).get("problems")
    source = read_json(source_path).get("problems")
    solutions = read_json(solutions_path).get("problems")
    if not all(isinstance(rows, list) for rows in (manifest, source, solutions)):
        raise ValueError("All inputs must contain a problems list")
    by_index = {row.get("source_index", index): row for index, row in enumerate(source) if isinstance(row, dict)}
    solved = {row.get("source_index", index): row for index, row in enumerate(solutions) if isinstance(row, dict)}
    records: list[dict[str, Any]] = []
    for position, item in enumerate(manifest):
        if not isinstance(item, dict):
            continue
        index = item.get("source_index", position)
        original = by_index.get(index)
        solve = solved.get(index, {})
        if not original:
            raise ValueError(f"Missing source record {index}")
        checked_solution = solve.get("solve_solution") if solve.get("answer_status") == "correct" else None
        solution_origin = "deepseek_verified_answer" if checked_solution else "dataset_r1_solution_1"
        checked_solution = checked_solution or original.get("r1_solution_1")
        if not isinstance(checked_solution, str) or not checked_solution.strip():
            raise ValueError(f"Missing worked solution for source {index}")
        records.append(
            {
                "source_index": index,
                "source_id": item.get("source_id", f"source-{index}"),
                "question": item["question"],
                "final_answer": item["final_answer"],
                "topic": item.get("topic", original.get("topic", "unknown")),
                "broad_topic": broad_topic(item.get("topic", original.get("topic", "unknown"))),
                "difficulty": item.get("difficulty", original.get("difficulty")),
                "checked_solution": checked_solution.strip(),
                "solution_origin": solution_origin,
            }
        )
    return records


def partition_sources(records: list[dict[str, Any]], seed: int = 20260920) -> dict[str, list[int]]:
    """Create fixed topic-balanced D1/D2/C partitions; keep the remainder reserved."""

    rng = random.Random(seed)
    grouped: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        grouped.setdefault(record["broad_topic"], []).append(record)
    for rows in grouped.values():
        rows.sort(key=lambda row: (float(row.get("difficulty") or 0), row["source_index"]))
        rng.shuffle(rows)
    selected: dict[str, list[int]] = {"D1": [], "D2": [], "C": [], "reserve": []}
    targets = {"D1": 3, "D2": 3, "C": 6}
    for topic in TOPIC_BUCKETS:
        rows = grouped.pop(topic, [])
        offset = 0
        for split, count in targets.items():
            selected[split].extend(row["source_index"] for row in rows[offset : offset + count])
            offset += count
        selected["reserve"].extend(row["source_index"] for row in rows[offset:])
    for rows in grouped.values():
        selected["reserve"].extend(row["source_index"] for row in rows)
    for values in selected.values():
        values.sort()
    assigned = [index for values in selected.values() for index in values]
    if len(assigned) != len(set(assigned)) or set(assigned) != {row["source_index"] for row in records}:
        raise ValueError("Partition is not a one-to-one cover of sources")
    return selected


def load_prompt(name: str, prompt_dir: Path = DEFAULT_PROMPT_DIR) -> str:
    path = prompt_dir / f"{name}.md"
    try:
        return path.read_text(encoding="utf-8").strip()
    except FileNotFoundError as exc:
        raise ValueError(f"Prompt does not exist: {path}") from exc


def render_template(template: str, values: dict[str, Any]) -> str:
    rendered = template
    for key, value in values.items():
        replacement = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2)
        rendered = rendered.replace("{{" + key + "}}", replacement)
    missing = sorted(set(re.findall(r"\{\{([A-Z0-9_]+)\}\}", rendered)))
    if missing:
        raise ValueError(f"Missing template values: {missing}")
    return rendered


def validate_bank(value: dict[str, Any], *, max_clues: int = 4) -> dict[str, Any]:
    if max_clues not in (4, 6):
        raise ValueError("Supported bank caps are four or six clues")
    if value.get("status") == "NOT_SUITABLE":
        if not isinstance(value.get("reason"), str):
            raise ValueError("NOT_SUITABLE bank lacks reason")
        return value
    clues = value.get("clues")
    if value.get("status") != "OK" or not isinstance(clues, list) or not 1 <= len(clues) <= max_clues:
        raise ValueError(f"Bank must contain status OK and one to {'four' if max_clues == 4 else 'six'} clues")
    ids: set[str] = set()
    for clue in clues:
        if not isinstance(clue, dict) or set(clue) != {"id", "sentence", "fragment", "hidden_support"}:
            raise ValueError("Each clue needs id, sentence, fragment, and hidden_support")
        if not all(isinstance(clue[key], str) and clue[key].strip() for key in clue):
            raise ValueError("Clue fields must be nonempty strings")
        if clue["id"] in ids:
            raise ValueError("Duplicate clue ID")
        ids.add(clue["id"])
    return value


def validate_audit(value: dict[str, Any]) -> dict[str, Any]:
    if value.get("status") not in {"ACCEPT", "REJECT", "NEEDS_REVIEW"}:
        raise ValueError("Invalid audit status")
    if not isinstance(value.get("reason"), str):
        raise ValueError("Audit lacks reason")
    return value


def validate_disclosure(value: dict[str, Any]) -> dict[str, Any]:
    if value.get("status") == "NOT_SUITABLE":
        if not isinstance(value.get("reason"), str):
            raise ValueError("NOT_SUITABLE disclosure lacks reason")
        return value
    clues = value.get("clues")
    if value.get("status") != "OK" or not isinstance(clues, list) or not clues:
        raise ValueError("Disclosure must contain status OK and clues")
    for clue in clues:
        if not isinstance(clue, dict) or not isinstance(clue.get("id"), str):
            raise ValueError("Each disclosure clue needs an ID")
        for level in ("low", "medium", "high"):
            rendering = clue.get(level)
            if not isinstance(rendering, dict) or set(rendering) != {"sentence", "fragment"}:
                raise ValueError(f"Disclosure clue needs sentence and fragment at {level}")
            if not all(isinstance(text, str) and text.strip() for text in rendering.values()):
                raise ValueError("Disclosure renderings must be nonempty")
        if not isinstance(clue.get("hidden_support"), str) or not clue["hidden_support"].strip():
            raise ValueError("Disclosure clue lacks hidden support")
        for tie in ("low_equals_medium", "medium_equals_high"):
            if not isinstance(clue.get(tie), bool):
                raise ValueError(f"Disclosure clue lacks Boolean {tie}")
    return value


def materialize_disclosure(value: dict[str, Any], level: str) -> dict[str, Any]:
    if level not in {"low", "medium", "high"}:
        raise ValueError(f"Unsupported disclosure level: {level}")
    return {
        "status": "OK",
        "clues": [
            {
                "id": clue["id"],
                "sentence": clue[level]["sentence"],
                "fragment": clue[level]["fragment"],
                "hidden_support": clue["hidden_support"],
            }
            for clue in value["clues"]
        ],
    }


def validate_student(value: dict[str, Any]) -> dict[str, Any]:
    expected = {"question", "justification", "assumptions"}
    if set(value) != expected:
        raise ValueError(f"Student output keys must be {sorted(expected)}")
    if not isinstance(value["question"], str) or not value["question"].strip():
        raise ValueError("Student question is empty")
    if not isinstance(value["justification"], str) or not value["justification"].strip():
        raise ValueError("Student justification is empty")
    if not isinstance(value["assumptions"], list) or not all(isinstance(x, str) for x in value["assumptions"]):
        raise ValueError("Student assumptions must be a string list")
    return value


def parse_student_response(text: str) -> tuple[dict[str, Any], bool]:
    """Parse exact JSON when possible and preserve readable off-schema output."""

    try:
        value = extract_json_object(text)
        try:
            return validate_student(value), False
        except ValueError:
            if isinstance(value.get("question"), str) and isinstance(value.get("justification"), str):
                assumptions = value.get("assumptions", [])
                if not isinstance(assumptions, list):
                    assumptions = [str(assumptions)]
                normalized = {
                    "question": value["question"].strip(),
                    "justification": value["justification"].strip(),
                    "assumptions": [str(item) for item in assumptions],
                }
                return validate_student(normalized), True
    except ValueError:
        pass

    # Recover a missing closing bracket before the next named object field.
    # Only complete JSON strings in assumptions are allowed; no mathematics or
    # field contents are rewritten. Keep the raw response and format-error flag.
    repaired = re.sub(
        r'("assumptions"\s*:\s*\[(?:\s*"(?:\\.|[^"\\])*"\s*,)*\s*"(?:\\.|[^"\\])*"\s*),(\s*"(?:question|justification)"\s*:)',
        r'\1],\2',
        text,
    )
    if repaired != text:
        try:
            return validate_student(extract_json_object(repaired)), True
        except ValueError:
            pass

    question_match = re.search(
        r"(?:^|\n)\s*(?:question|reconstructed question)\s*:\s*(.+?)(?=\n\s*(?:justification|verification|assumptions)\s*:|\Z)",
        text,
        re.I | re.S,
    )
    justification_match = re.search(
        r"(?:^|\n)\s*(?:justification|verification)\s*:\s*(.+?)(?=\n\s*assumptions\s*:|\Z)",
        text,
        re.I | re.S,
    )
    if question_match and justification_match:
        return (
            {
                "question": question_match.group(1).strip(),
                "justification": justification_match.group(1).strip(),
                "assumptions": [],
            },
            True,
        )
    raise ValueError("Student response is neither valid JSON nor a readable question/justification response")


def has_generated_thinking(raw: dict[str, Any]) -> bool:
    reasoning = raw.get("reasoning")
    if isinstance(reasoning, str) and reasoning.strip():
        return True
    for match in re.findall(r"<think>(.*?)</think>", str(raw.get("content", "")), re.I | re.S):
        if match.strip():
            return True
    return False


def validate_evaluation(value: dict[str, Any], *, strict_inference: bool = False) -> dict[str, Any]:
    if value.get("status") not in {"scored", "needs_review"}:
        raise ValueError("Invalid evaluation status")
    score = value.get("score")
    if value["status"] == "scored" and (not isinstance(score, int) or not 0 <= score <= 4):
        raise ValueError("Scored evaluation requires integer score 0..4")
    if value["status"] == "needs_review" and score is not None:
        raise ValueError("needs_review score must be null")
    if not isinstance(value.get("reason"), str):
        raise ValueError("Evaluation lacks reason")
    if strict_inference:
        inference = value.get('inference')
        if not isinstance(inference, dict) or inference.get('status') not in {'substantive','copy_only','uncertain'}:
            raise ValueError('Evaluation lacks a valid reconstruction-inference assessment')
        for field in ('essential_content','reason'):
            if not isinstance(inference.get(field),str) or not inference[field].strip():
                raise ValueError('Inference assessment lacks an explanation')
        if value['status']=='scored' and type(score) is not int:
            raise ValueError('Boolean is not a rubric score')
        if inference['status']=='copy_only' and (score!=0 or value.get('shortcut') is not True):
            raise ValueError('Copy-only reconstruction must be scored0 with shortcut=true')
        if score is not None and score>=3 and (inference['status']!='substantive' or value.get('shortcut') is not False):
            raise ValueError('High score requires substantive reconstruction without a shortcut')
    return value


def is_scored_success(value: dict[str, Any]) -> bool:
    return bool(
        value.get("status") == "scored"
        and isinstance(value.get("score"), int)
        and value["score"] >= 3
        and value.get("well_posed") is True
        and value.get("answer_correct") is True
        and value.get("shortcut") is False
    )


def is_grounded_success(value: dict[str, Any]) -> bool:
    checks = value.get("clue_checks")
    return bool(
        is_scored_success(value)
        and isinstance(checks, list)
        and all(
            isinstance(check, dict)
            and check.get("compatible") is True
            and check.get("grounding") in {"explicit", "implicit"}
            for check in checks
        )
        and len(checks) > 0
    )


def choose_clues(
    bank: dict[str, Any], count: int, seed: int, selection_policy: str = "random"
) -> list[dict[str, Any]]:
    clues = list(bank.get("clues", []))
    if not clues:
        raise ValueError("Cannot select from empty bank")
    if count < 1 or count > len(clues):
        raise ValueError(f"Requested {count} clues from bank of {len(clues)}")
    if 'fixed_order_ids' in bank:
        ids = bank['fixed_order_ids']
        if (count != len(clues) or seed != bank.get('fixed_order_seed')
            or selection_policy != 'random'):
            raise ValueError('Materialized input requires its complete audited prefix and original order seed')
        if len(ids) != len(clues) or len(set(ids)) != len(ids) or set(ids) != {c['id'] for c in clues}:
            raise ValueError('Invalid fixed clue order')
        by_id = {c['id']:c for c in clues}
        return [by_id[i] for i in ids]
    if selection_policy == 'bank_order':
        if count != len(clues):
            raise ValueError('bank_order requires the complete audited bank; materialize subsets separately')
        return clues
    if bank.get("role_cue_id"):
        if count != len(clues):
            raise ValueError("Role-augmented experiment requires its complete bank")
        role = [clue for clue in clues if clue["id"] == bank["role_cue_id"]]
        base = [clue for clue in clues if clue["id"] != bank["role_cue_id"]]
        if len(role) != 1 or not base:
            raise ValueError("Role-augmented bank requires exactly one role cue and base clues")
        # Hold the historical clue order fixed; the only additional evidence is
        # the role sentence appended to the unchanged seeded base evidence.
        return choose_clues({"clues": base}, len(base), seed, selection_policy) + role
    if selection_policy not in {"random", "anchor_first"}:
        raise ValueError(f"Unsupported clue selection policy: {selection_policy}")
    if selection_policy == "anchor_first":
        rng = random.Random(f"{seed}:{stable_hash(clues)}:anchor_first")
        anchor, remainder = clues[0], clues[1:]
        rng.shuffle(remainder)
        return [anchor, *remainder[: count - 1]]
    rng = random.Random(f"{seed}:{stable_hash(clues)}")
    rng.shuffle(clues)
    return clues[:count]


def public_evidence(answer: str, clues: list[dict[str, Any]], style: str = "sentence") -> dict[str, Any]:
    if style not in {"sentence", "fragment", "paragraph"}:
        raise ValueError(f"Unsupported style: {style}")
    key = "fragment" if style == "fragment" else "sentence"
    texts = [clue[key].strip() for clue in clues]
    rendered = " ".join(texts) if style == "paragraph" else "\n".join(f"- {text}" for text in texts)
    return {
        "condition": "bank",
        "final_answer": answer,
        "clues": texts,
        "rendered_clues": rendered,
        "style": style,
        "clue_count": len(texts),
    }


def solution_sentences(solution: str, question: str) -> list[str]:
    """Return useful sentence-like excerpts while filtering obvious question copies."""

    chunks = re.split(r"(?<=[.!?])\s+|\n+", solution.strip())
    question_tokens = set(re.findall(r"[a-z0-9]+", question.lower()))
    candidates: list[str] = []
    for chunk in chunks:
        text = chunk.strip().lstrip("-* ")
        if len(text) < 20:
            continue
        tokens = set(re.findall(r"[a-z0-9]+", text.lower()))
        overlap = len(tokens & question_tokens) / max(1, len(tokens | question_tokens))
        looks_like_target = bool(re.match(r"^(find|determine|compute|evaluate|prove|show)\b", text, re.I))
        if overlap >= 0.72 or looks_like_target:
            continue
        candidates.append(text)
    return candidates


def condition_evidence(
    source: dict[str, Any],
    condition: str,
    *,
    bank: dict[str, Any] | None,
    clue_count: int,
    clue_seed: int,
    style: str,
    selection_policy: str = "random",
) -> dict[str, Any]:
    """Build one public input condition without exposing private support metadata."""

    answer = source["final_answer"]
    if condition == "bank":
        if bank is None:
            raise ValueError("The bank condition requires an accepted bank")
        evidence = public_evidence(
            answer,
            choose_clues(bank["output"], clue_count, clue_seed, selection_policy),
            style,
        )
        evidence["selection_policy"] = selection_policy
        return evidence
    if condition == "answer_only":
        return {
            "condition": condition,
            "final_answer": answer,
            "clues": [],
            "rendered_clues": "(No observations are provided.)",
            "style": "none",
            "clue_count": 0,
        }
    if condition == "full_solution":
        solution = source["checked_solution"]
        return {
            "condition": condition,
            "final_answer": answer,
            "clues": [solution],
            "rendered_clues": solution,
            "style": "worked_solution",
            "clue_count": None,
        }
    if condition == "random_excerpt":
        candidates = solution_sentences(source["checked_solution"], source["question"])
        if len(candidates) < clue_count:
            raise ValueError(f"Only {len(candidates)} non-restating solution excerpts are available")
        rng = random.Random(f"excerpt:{clue_seed}:{source['source_index']}")
        selected = rng.sample(candidates, clue_count)
        rendered = "\n".join(f"- {text}" for text in selected)
        return {
            "condition": condition,
            "final_answer": answer,
            "clues": selected,
            "rendered_clues": rendered,
            "style": "sentence",
            "clue_count": clue_count,
            "screening": "question-overlap heuristic; requires later audit",
        }
    raise ValueError(f"Unsupported evidence condition: {condition}")


class IncompleteCompletionError(ValueError):
    def __init__(self, message: str, raw_response: dict[str, Any]) -> None:
        super().__init__(message)
        self.raw_response = raw_response


class ChatClient:
    def __init__(self, base_url: str, api_key: str, timeout: float = 900.0) -> None:
        from openai import OpenAI

        self.client = OpenAI(api_key=api_key, base_url=base_url, timeout=timeout, max_retries=0)

    def complete(
        self,
        *,
        model: str,
        prompt: str,
        max_tokens: int,
        temperature: float,
        top_p: float = 1.0,
        seed: int | None = None,
        extra_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        started = time.perf_counter()
        request: dict[str, Any] = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
        }
        if seed is not None:
            request["seed"] = seed
        if extra_body:
            request["extra_body"] = extra_body
        response = self.client.chat.completions.create(**request)
        usage = response.usage.model_dump() if response.usage else None
        elapsed = round(time.perf_counter() - started, 3)
        if not response.choices:
            raise IncompleteCompletionError("Completion has no choices", {
                'content': '', 'reasoning': None, 'finish_reason': None,
                'usage': usage, 'elapsed_seconds': elapsed})
        message = response.choices[0].message
        content = message.content
        reasoning = getattr(message, "reasoning_content", None)
        raw = {
            "content": content.strip() if isinstance(content, str) else '',
            "reasoning": reasoning if isinstance(reasoning, str) else None,
            "finish_reason": response.choices[0].finish_reason,
            "usage": usage,
            "elapsed_seconds": elapsed,
        }
        if not raw['content']:
            raise IncompleteCompletionError("Completion has no visible content", raw)
        return raw


def deepinfra_client(timeout: float = 900.0) -> ChatClient:
    from dotenv import load_dotenv

    load_dotenv(ENV_FILE)
    key = os.getenv("DEEPINFRA_API_KEY")
    if not key:
        raise RuntimeError("DEEPINFRA_API_KEY is not set")
    return ChatClient(DEFAULT_DEEPINFRA_URL, key, timeout)


def local_client(base_url: str = DEFAULT_LOCAL_URL, timeout: float = 900.0) -> ChatClient:
    return ChatClient(base_url, "local", timeout)


def teacher_call(client: ChatClient, prompt: str, model: str, max_tokens: int, reasoning_effort: str) -> dict[str, Any]:
    return client.complete(
        model=model,
        prompt=prompt,
        max_tokens=max_tokens,
        temperature=0.0,
        extra_body={"reasoning_effort": reasoning_effort},
    )


def student_call(client: ChatClient, prompt: str, model: str, config: SamplingConfig) -> dict[str, Any]:
    return client.complete(
        model=model,
        prompt=prompt,
        max_tokens=config.max_tokens,
        temperature=config.temperature,
        top_p=config.top_p,
        seed=config.seed,
        extra_body={
            "top_k": config.top_k,
            "chat_template_kwargs": {"enable_thinking": False},
        },
    )


def new_run(records: list[dict[str, Any]], partitions: dict[str, list[int]], metadata: dict[str, Any]) -> dict[str, Any]:
    return {
        "metadata": {"schema": "reconstruct_pilot_v1", "created_at": utc_now(), **metadata},
        "partitions": partitions,
        "sources": {str(row["source_index"]): row for row in records},
        "banks": {},
        "audits": {},
        "disclosures": {},
        "disclosure_audits": {},
        "responses": {},
        "evaluations": {},
        "source_recovery": {},
        "judge_fixtures": {},
        "failures": [],
    }


def load_or_create_run(args: argparse.Namespace) -> dict[str, Any]:
    if args.output.exists():
        return read_json(args.output)
    records = load_sources(args.manifest, args.source, args.solutions)
    partitions = partition_sources(records, args.split_seed)
    run = new_run(
        records,
        partitions,
        {
            "manifest": str(args.manifest),
            "source": str(args.source),
            "solutions": str(args.solutions),
            "split_seed": args.split_seed,
            "teacher_model": args.teacher_model,
            "student_model": args.student_model,
        },
    )
    atomic_write_json(args.output, run)
    return run


def selected_indices(run: dict[str, Any], split: str, limit: int | None, explicit: list[int] | None) -> list[int]:
    if explicit:
        return explicit
    values = list(run["partitions"][split])
    return values[:limit] if limit else values


def failure(run: dict[str, Any], stage: str, source_index: int, key: str, error: Exception, raw: Any = None) -> None:
    if raw is None:
        raw = getattr(error, 'raw_response', None)
    run["failures"].append(
        {
            "time": utc_now(),
            "stage": stage,
            "source_index": source_index,
            "key": key,
            "error": f"{type(error).__name__}: {error}",
            "raw": raw,
        }
    )


def convert_sources(args: argparse.Namespace, run: dict[str, Any], indices: list[int]) -> None:
    bounds = run.get("metadata", {}).get("conversion_clue_bounds", {}).get(args.convert_prompt)
    if bounds is not None:
        lower, upper = bounds
        if not (type(lower) is int and type(upper) is int and 1 <= lower <= upper <= args.max_bank_clues):
            raise ValueError("Registered clue bounds exceed the configured --max-bank-clues; fix configuration before provider calls")
    client = deepinfra_client(args.timeout)
    template = load_prompt(args.convert_prompt, args.prompt_dir)
    prompt_hash = stable_hash(template)
    for position, index in enumerate(indices, 1):
        key = f"{index}:{prompt_hash}:{args.teacher_model}:{args.reasoning_effort}"
        if key in run["banks"] and not args.force:
            print(f"convert [{position}/{len(indices)}] {index}: cached")
            continue
        source = run["sources"][str(index)]
        prompt = render_template(
            template,
            {
                "SOURCE_QUESTION": source["question"],
                "FINAL_ANSWER": source["final_answer"],
                "CHECKED_SOLUTION": source["checked_solution"],
            },
        )
        raw: dict[str, Any] | None = None
        try:
            reserve_teacher_request(run, prompt, args.teacher_max_tokens, args.max_cost_usd)
            raw = teacher_call(client, prompt, args.teacher_model, args.teacher_max_tokens, args.reasoning_effort)
            parsed = validate_bank(extract_json_object(raw["content"]), max_clues=args.max_bank_clues)
            if bounds is not None and parsed["status"] == "OK" and not lower <= len(parsed["clues"]) <= upper:
                raise ValueError("Conversion violates registered clue-count bounds")
            run["banks"][key] = {
                "source_index": index,
                "prompt": args.convert_prompt,
                "prompt_hash": prompt_hash,
                "model": args.teacher_model,
                "reasoning_effort": args.reasoning_effort,
                "output": parsed,
                "request": {k: v for k, v in raw.items() if k != "content"},
                "raw_content": raw["content"],
            }
            print(f"convert [{position}/{len(indices)}] {index}: {parsed['status']}")
        except Exception as exc:
            failure(run, "convert", index, key, exc, raw)
            print(f"convert [{position}/{len(indices)}] {index}: FAILED {exc}")
        atomic_write_json(args.output, run)


def latest_bank(run: dict[str, Any], index: int, prompt_name: str | None = None) -> tuple[str, dict[str, Any]]:
    matches = [
        (key, item)
        for key, item in run["banks"].items()
        if item["source_index"] == index and (prompt_name is None or item.get("prompt") == prompt_name)
    ]
    if not matches:
        raise ValueError(f"No bank for source {index}")
    key, item = matches[-1]
    if item["output"].get("status") != "OK":
        raise ValueError(f"Source {index} is not suitable")
    return key, item


def accepted_bank(
    run: dict[str, Any], index: int, prompt_name: str | None = None
) -> tuple[str, dict[str, Any]]:
    latest = {
        item.get("bank_key"): item.get("output", {}).get("status")
        for item in run.get("audits", {}).values()
        if item.get("source_index") == index
    }
    # A subsequent rejection/uncertainty revokes earlier acceptance. Otherwise
    # revised leakage audits could be silently bypassed during generation.
    accepted = {key for key, status in latest.items() if status == "ACCEPT"}
    required = run.get('metadata', {}).get('required_bank_audits', {})
    by_prompt = {
        (item.get('bank_key'), item.get('prompt')): item.get('output', {}).get('status')
        for item in run.get('audits', {}).values() if item.get('source_index') == index
    }
    matches = [
        (key, item)
        for key, item in run["banks"].items()
        if key in accepted and (prompt_name is None or item.get("prompt") == prompt_name)
        and all(by_prompt.get((key, name)) == 'ACCEPT'
                for name in required.get(item.get('prompt'), []))
    ]
    if not matches:
        raise ValueError(f"No accepted audited bank for source {index}")
    return matches[-1]


def actual_cost(run: dict[str, Any]) -> float:
    total = 0.0
    for section in (
        "banks",
        "audits",
        "disclosures",
        "disclosure_audits",
        "evaluations",
        "source_recovery",
        "judge_fixtures",
        "teacher_reconstructions",
        "copy_challenges",
    ):
        for item in run.get(section, {}).values():
            usage = item.get("request", {}).get("usage")
            if isinstance(usage, dict):
                total += float(usage.get("estimated_cost") or 0.0)
    for item in run.get('failures', []):
        raw = item.get('raw')
        usage = raw.get('usage') if isinstance(raw, dict) else None
        if isinstance(usage, dict):
            total += float(usage.get('estimated_cost') or 0.0)
    return total


def reserve_teacher_request(run: dict[str, Any], prompt: str, max_tokens: int, cap: float) -> None:
    reserve = (len(prompt) / 4 * 0.20 + max_tokens * 0.60) / 1_000_000
    if actual_cost(run) + reserve > cap:
        raise RuntimeError(
            f"DeepInfra cost cap would be exceeded: spent=${actual_cost(run):.4f}, "
            f"reserve=${reserve:.4f}, cap=${cap:.2f}"
        )


def audit_sources(args: argparse.Namespace, run: dict[str, Any], indices: list[int]) -> None:
    client = deepinfra_client(args.timeout)
    template = load_prompt(args.audit_prompt, args.prompt_dir)
    prompt_hash = stable_hash(template)
    for position, index in enumerate(indices, 1):
        try:
            bank_key, bank = latest_bank(run, index, args.bank_prompt)
        except Exception as exc:
            failure(run, "audit", index, "missing-bank", exc)
            continue
        key = f"{index}:{stable_hash(bank['output'])}:{prompt_hash}:{args.teacher_model}:{args.reasoning_effort}"
        if key in run["audits"] and not args.force:
            print(f"audit [{position}/{len(indices)}] {index}: cached")
            continue
        source = run["sources"][str(index)]
        prompt = render_template(
            template,
            {
                "SOURCE_QUESTION": source["question"],
                "FINAL_ANSWER": source["final_answer"],
                "CHECKED_SOLUTION": source["checked_solution"],
                "CLUE_BANK": bank["output"],
                "PUBLIC_BANK": {
                    "role_cue_id": bank["output"].get("role_cue_id"),
                    "clues": [{"id": clue["id"], "sentence": clue["sentence"]}
                              for clue in bank["output"]["clues"]],
                },
            },
        )
        raw: dict[str, Any] | None = None
        try:
            reserve_teacher_request(run, prompt, args.teacher_max_tokens, args.max_cost_usd)
            raw = teacher_call(client, prompt, args.teacher_model, args.teacher_max_tokens, args.reasoning_effort)
            parsed = validate_audit(extract_json_object(raw["content"]))
            if args.audit_prompt in {'audit_public_p4', 'audit_public_p5', 'audit_source_disclosure_p1', 'audit_source_disclosure_p2', 'audit_source_disclosure_p3', 'audit_source_disclosure_p4'}:
                from .reconstruct_gates import validate_strict_disclosure, public_disclosure_text
                scope = ('public_disclosure' if args.audit_prompt in {'audit_public_p4', 'audit_public_p5'}
                         else 'source_disclosure')
                public_text = public_disclosure_text(source['final_answer'], bank['output'], scope)
                validate_strict_disclosure(parsed, public_text, scope)
            if args.audit_prompt == 'audit_support_p1':
                if parsed.get('scope') != 'source_support':
                    raise ValueError('Source-support audit returned the wrong scope')
                if parsed['status'] == 'ACCEPT':
                    checks = parsed.get('checks', [])
                    expected_ids = sorted(clue['id'] for clue in bank['output']['clues'])
                    if (sorted(check.get('id', '') for check in checks) != expected_ids
                        or not all(check.get('supported') is True and check.get('self_contained') is True for check in checks)
                        or parsed.get('distinct_observations') is not True):
                        raise ValueError('Source-support acceptance lacks complete positive checks')
            run["audits"][key] = {
                "source_index": index,
                "bank_key": bank_key,
                "bank_output_hash": stable_hash(bank['output']),
                "source_record_hash": stable_hash(source),
                "rendered_input_hash": stable_hash(prompt),
                "prompt": args.audit_prompt,
                "prompt_hash": prompt_hash,
                "model": args.teacher_model,
                "reasoning_effort": args.reasoning_effort,
                "output": parsed,
                "request": {k: v for k, v in raw.items() if k != "content"},
                "raw_content": raw["content"],
            }
            print(f"audit [{position}/{len(indices)}] {index}: {parsed['status']}")
        except Exception as exc:
            failure(run, "audit", index, key, exc, raw)
            print(f"audit [{position}/{len(indices)}] {index}: FAILED {exc}")
        atomic_write_json(args.output, run)


def copy_challenge_sources(args: argparse.Namespace, run: dict[str, Any], indices: list[int]) -> None:
    from .reconstruct_gates import public_disclosure_text, validate_copy_challenge
    client = deepinfra_client(args.timeout)
    template = load_prompt(args.copy_prompt, args.prompt_dir)
    prompt_hash = stable_hash(template)
    run.setdefault('copy_challenges', {})
    for index in indices:
        bank_key, bank = latest_bank(run, index, args.bank_prompt)
        answer = run['sources'][str(index)]['final_answer']
        public_bank = {'role_cue_id': bank['output'].get('role_cue_id'),
                       'clues': [{'id': c['id'], 'sentence': c['sentence']}
                                 for c in bank['output']['clues']]}
        public = {'FINAL_ANSWER': answer, 'PUBLIC_BANK': public_bank}
        prompt = render_template(template, public)
        key = f'{index}:{stable_hash(public)}:{prompt_hash}:{args.teacher_model}:{args.reasoning_effort}'
        if key in run['copy_challenges'] and not args.force:
            continue
        raw = None
        try:
            reserve_teacher_request(run, prompt, args.teacher_max_tokens, args.max_cost_usd)
            raw = teacher_call(client, prompt, args.teacher_model, args.teacher_max_tokens, args.reasoning_effort)
            value = validate_copy_challenge(extract_json_object(raw['content']),
                public_disclosure_text(answer, bank['output'], 'public_disclosure'))
            run['copy_challenges'][key] = {'source_index': index, 'bank_key': bank_key,
                'public_input': public, 'public_input_hash': stable_hash(public),
                'rendered_prompt': prompt, 'prompt': args.copy_prompt, 'prompt_hash': prompt_hash,
                'model': args.teacher_model, 'reasoning_effort': args.reasoning_effort,
                'output': value, 'raw_content': raw['content'],
                'request': {k: v for k, v in raw.items() if k != 'content'}}
            print(f'copy-challenge {index}: {value["status"]}', flush=True)
        except Exception as exc:
            failure(run, 'copy_challenge', index, key, exc, raw)
            print(f'copy-challenge {index}: FAILED {exc}', flush=True)
        atomic_write_json(args.output, run)


def generate_disclosures(args: argparse.Namespace, run: dict[str, Any], indices: list[int]) -> None:
    client = deepinfra_client(args.timeout)
    template = load_prompt(args.disclosure_prompt, args.prompt_dir)
    prompt_hash = stable_hash(template)
    run.setdefault("disclosures", {})
    for position, index in enumerate(indices, 1):
        try:
            bank_key, bank = accepted_bank(run, index, args.bank_prompt)
        except Exception as exc:
            failure(run, "disclose", index, "missing-accepted-bank", exc)
            continue
        key = f"{index}:{stable_hash(bank['output'])}:{prompt_hash}:{args.teacher_model}:{args.reasoning_effort}"
        if key in run["disclosures"] and not args.force:
            print(f"disclose [{position}/{len(indices)}] {index}: cached")
            continue
        source = run["sources"][str(index)]
        prompt = render_template(
            template,
            {
                "SOURCE_QUESTION": source["question"],
                "FINAL_ANSWER": source["final_answer"],
                "CHECKED_SOLUTION": source["checked_solution"],
                "CLUE_BANK": bank["output"],
            },
        )
        raw: dict[str, Any] | None = None
        try:
            reserve_teacher_request(run, prompt, args.teacher_max_tokens, args.max_cost_usd)
            raw = teacher_call(client, prompt, args.teacher_model, args.teacher_max_tokens, args.reasoning_effort)
            parsed = validate_disclosure(extract_json_object(raw["content"]))
            run["disclosures"][key] = {
                "source_index": index,
                "bank_key": bank_key,
                "prompt": args.disclosure_prompt,
                "prompt_hash": prompt_hash,
                "model": args.teacher_model,
                "reasoning_effort": args.reasoning_effort,
                "output": parsed,
                "request": {k: v for k, v in raw.items() if k != "content"},
                "raw_content": raw["content"],
            }
            print(f"disclose [{position}/{len(indices)}] {index}: {parsed['status']}")
        except Exception as exc:
            failure(run, "disclose", index, key, exc, raw)
            print(f"disclose [{position}/{len(indices)}] {index}: FAILED {exc}")
        atomic_write_json(args.output, run)


def latest_disclosure(run: dict[str, Any], index: int, bank_key: str) -> tuple[str, dict[str, Any]]:
    matches = [
        (key, item)
        for key, item in run.get("disclosures", {}).items()
        if item.get("source_index") == index
        and item.get("bank_key") == bank_key
        and item.get("output", {}).get("status") == "OK"
    ]
    if not matches:
        raise ValueError(f"No disclosure variants for source {index} and selected bank")
    return matches[-1]


def audit_disclosures(args: argparse.Namespace, run: dict[str, Any], indices: list[int]) -> None:
    client = deepinfra_client(args.timeout)
    template = load_prompt(args.disclosure_audit_prompt, args.prompt_dir)
    prompt_hash = stable_hash(template)
    run.setdefault("disclosure_audits", {})
    for position, index in enumerate(indices, 1):
        try:
            bank_key, _ = accepted_bank(run, index, args.bank_prompt)
            disclosure_key, disclosure = latest_disclosure(run, index, bank_key)
        except Exception as exc:
            failure(run, "audit_disclosure", index, "missing-disclosure", exc)
            continue
        key = f"{index}:{stable_hash(disclosure['output'])}:{prompt_hash}:{args.teacher_model}:{args.reasoning_effort}"
        if key in run["disclosure_audits"] and not args.force:
            print(f"audit-disclosure [{position}/{len(indices)}] {index}: cached")
            continue
        source = run["sources"][str(index)]
        prompt = render_template(
            template,
            {
                "SOURCE_QUESTION": source["question"],
                "FINAL_ANSWER": source["final_answer"],
                "CHECKED_SOLUTION": source["checked_solution"],
                "DISCLOSURE_BANK": disclosure["output"],
            },
        )
        raw: dict[str, Any] | None = None
        try:
            reserve_teacher_request(run, prompt, args.teacher_max_tokens, args.max_cost_usd)
            raw = teacher_call(client, prompt, args.teacher_model, args.teacher_max_tokens, args.reasoning_effort)
            parsed = validate_audit(extract_json_object(raw["content"]))
            run["disclosure_audits"][key] = {
                "source_index": index,
                "disclosure_key": disclosure_key,
                "prompt": args.disclosure_audit_prompt,
                "prompt_hash": prompt_hash,
                "model": args.teacher_model,
                "reasoning_effort": args.reasoning_effort,
                "output": parsed,
                "request": {k: v for k, v in raw.items() if k != "content"},
                "raw_content": raw["content"],
            }
            print(f"audit-disclosure [{position}/{len(indices)}] {index}: {parsed['status']}")
        except Exception as exc:
            failure(run, "audit_disclosure", index, key, exc, raw)
            print(f"audit-disclosure [{position}/{len(indices)}] {index}: FAILED {exc}")
        atomic_write_json(args.output, run)


def accepted_disclosure(run: dict[str, Any], index: int, bank_key: str) -> dict[str, Any]:
    latest = {
        item.get("disclosure_key"): item.get("output", {}).get("status")
        for item in run.get("disclosure_audits", {}).values()
        if item.get("source_index") == index
    }
    accepted = {key for key, status in latest.items() if status == "ACCEPT"}
    matches = [
        item
        for key, item in run.get("disclosures", {}).items()
        if key in accepted and item.get("bank_key") == bank_key
    ]
    if not matches:
        raise ValueError(f"No accepted disclosure variants for source {index}")
    return matches[-1]


def student_sources(args: argparse.Namespace, run: dict[str, Any], indices: list[int]) -> None:
    client = local_client(args.local_url, args.timeout)
    template = load_prompt(args.student_prompt, args.prompt_dir)
    prompt_hash = stable_hash(template)
    config = SamplingConfig(args.temperature, args.top_p, args.top_k, args.max_tokens, args.seed)
    for position, index in enumerate(indices, 1):
        source = run["sources"][str(index)]
        bank_key: str | None = None
        bank: dict[str, Any] | None = None
        try:
            if args.condition == "bank":
                bank_key, bank = accepted_bank(run, index, args.bank_prompt)
                if args.disclosure != "medium":
                    disclosure = accepted_disclosure(run, index, bank_key)
                    bank = {**bank, "output": materialize_disclosure(disclosure["output"], args.disclosure)}
            selected_clue_count = (
                len(bank["output"]["clues"])
                if args.condition == "bank" and args.all_clues and bank is not None
                else args.clue_count
            )
            evidence = condition_evidence(
                source,
                args.condition,
                bank=bank,
                clue_count=selected_clue_count,
                clue_seed=args.clue_seed,
                style=args.style,
                selection_policy=args.selection_policy,
            )
            evidence["disclosure"] = args.disclosure if args.condition == "bank" else None
            from .reconstruct_gates import check_student_readiness
            check_student_readiness(run, index, evidence)
        except Exception as exc:
            failure(run, "student", index, "evidence", exc)
            continue
        evidence_hash = stable_hash(evidence)
        key = f"{index}:{evidence_hash}:{prompt_hash}:{args.student_model}:{stable_hash(asdict(config))}"
        if key in run["responses"] and not args.force:
            print(f"student [{position}/{len(indices)}] {index}: cached")
            continue
        prompt = render_template(
            template,
            {"FINAL_ANSWER": evidence["final_answer"], "RENDERED_CLUES": evidence["rendered_clues"]},
        )
        raw: dict[str, Any] | None = None
        try:
            raw = student_call(client, prompt, args.student_model, config)
            if has_generated_thinking(raw):
                raise RuntimeError("Qwen generated a thinking channel although non-thinking mode was requested")
            parsed, format_error = parse_student_response(raw["content"])
            run["responses"][key] = {
                "source_index": index,
                "bank_key": bank_key,
                "condition": args.condition,
                "public_evidence": evidence,
                "evidence_hash": evidence_hash,
                "prompt": args.student_prompt,
                "prompt_hash": prompt_hash,
                "model": args.student_model,
                "sampling": asdict(config),
                "output": parsed,
                "format_error": format_error,
                "request": {k: v for k, v in raw.items() if k != "content"},
                "raw_content": raw["content"],
            }
            print(f"student [{position}/{len(indices)}] {index}: completed ({raw['elapsed_seconds']}s)")
        except Exception as exc:
            failure(run, "student", index, key, exc, raw)
            print(f"student [{position}/{len(indices)}] {index}: FAILED {exc}")
        atomic_write_json(args.output, run)


def evaluate_responses(args: argparse.Namespace, run: dict[str, Any], indices: list[int]) -> None:
    client = deepinfra_client(args.timeout)
    template = load_prompt(args.evaluate_prompt, args.prompt_dir)
    prompt_hash = stable_hash(template)
    for response in run.get("responses", {}).values():
        if response.get("source_index") in indices and isinstance(response.get("raw_content"), str):
            parsed, format_error = parse_student_response(response["raw_content"])
            response["output"] = parsed
            response["format_error"] = format_error
    eligible = [
        (key, item)
        for key, item in run["responses"].items()
        if item["source_index"] in indices
        and (args.response_prompt is None or item.get("prompt") == args.response_prompt)
        and (
            args.response_style is None
            or item.get("public_evidence", {}).get("style") == args.response_style
        )
        and (
            args.response_disclosure is None
            or item.get("public_evidence", {}).get("disclosure") == args.response_disclosure
        )
        and (
            args.response_selection_policy is None
            or item.get("public_evidence", {}).get("selection_policy", "random")
            == args.response_selection_policy
        )
        and (
            args.response_bank_prompt is None
            or run.get("banks", {}).get(item.get("bank_key"), {}).get("prompt")
            == args.response_bank_prompt
        )
        and (
            args.response_clue_count is None
            or item.get("public_evidence", {}).get("clue_count") == args.response_clue_count
        )
    ]
    for position, (response_key, response) in enumerate(eligible, 1):
        index = response["source_index"]
        key = f"{response_key}:{prompt_hash}:{args.teacher_model}:{args.reasoning_effort}"
        if key in run["evaluations"] and not args.force:
            print(f"evaluate [{position}/{len(eligible)}] {index}: cached")
            continue
        prompt = render_template(
            template,
            {
                "FINAL_ANSWER": response["public_evidence"]["final_answer"],
                "RENDERED_CLUES": response["public_evidence"]["rendered_clues"],
                "STUDENT_RESPONSE": {
                    field: response["output"][field]
                    for field in ("question", "justification", "assumptions")
                },
            },
        )
        raw: dict[str, Any] | None = None
        try:
            reserve_teacher_request(run, prompt, args.teacher_max_tokens, args.max_cost_usd)
            raw = teacher_call(client, prompt, args.teacher_model, args.teacher_max_tokens, args.reasoning_effort)
            parsed = validate_evaluation(extract_json_object(raw["content"]), strict_inference=args.evaluate_prompt=='evaluate_p3')
            run["evaluations"][key] = {
                "source_index": index,
                "response_key": response_key,
                "response_output_hash": stable_hash(response['output']),
                "evidence_hash": stable_hash(response['public_evidence']),
                "rendered_input_hash": stable_hash(prompt),
                "prompt": args.evaluate_prompt,
                "prompt_hash": prompt_hash,
                "model": args.teacher_model,
                "reasoning_effort": args.reasoning_effort,
                "output": parsed,
                "request": {k: v for k, v in raw.items() if k != "content"},
                "raw_content": raw["content"],
            }
            print(f"evaluate [{position}/{len(eligible)}] {index}: {parsed.get('score')}")
        except Exception as exc:
            failure(run, "evaluate", index, key, exc, raw)
            print(f"evaluate [{position}/{len(eligible)}] {index}: FAILED {exc}")
        atomic_write_json(args.output, run)


def validate_source_recovery(value: dict[str, Any], *, strict: bool = False) -> dict[str, Any]:
    if value.get('status') not in {'scored', 'needs_review'}:
        raise ValueError('Invalid source-recovery status')
    score = value.get('source_recovery')
    if value['status'] == 'scored' and (type(score) is not int or score not in {0, 1, 2}):
        raise ValueError('source_recovery must be integer 0, 1, or 2')
    if value['status'] == 'needs_review' and score is not None:
        raise ValueError('needs_review source_recovery must be null')
    if not isinstance(value.get('reason'), str) or not value['reason'].strip():
        raise ValueError('Source recovery needs a reason')
    if strict:
        checks = value.get('checks')
        fields = {'objects', 'premises', 'domains_parameters', 'target'}
        if not isinstance(checks, dict) or set(checks) != fields:
            raise ValueError('Source recovery needs all semantic checks')
        if any(v not in {'same', 'different', 'uncertain'} for v in checks.values()):
            raise ValueError('Invalid semantic check')
        if score == 2 and any(v != 'same' for v in checks.values()):
            raise ValueError('Exact recovery contradicts semantic checks')
        if not isinstance(value.get('correspondence'), str) or not value['correspondence'].strip():
            raise ValueError('Semantic recovery lacks correspondence')
    return value


def source_recovery_responses(args: argparse.Namespace, run: dict[str, Any], indices: list[int]) -> None:
    client = deepinfra_client(args.timeout)
    template = load_prompt(args.recovery_prompt, args.prompt_dir)
    prompt_hash = stable_hash(template)
    run.setdefault("source_recovery", {})
    eligible = [
        (key, item)
        for key, item in run["responses"].items()
        if item["source_index"] in indices
        and (args.response_prompt is None or item.get("prompt") == args.response_prompt)
        and (
            args.response_style is None
            or item.get("public_evidence", {}).get("style") == args.response_style
        )
        and (
            args.response_disclosure is None
            or item.get("public_evidence", {}).get("disclosure") == args.response_disclosure
        )
        and (
            args.response_selection_policy is None
            or item.get("public_evidence", {}).get("selection_policy", "random")
            == args.response_selection_policy
        )
        and (
            args.response_bank_prompt is None
            or run.get("banks", {}).get(item.get("bank_key"), {}).get("prompt")
            == args.response_bank_prompt
        )
        and (
            args.response_clue_count is None
            or item.get("public_evidence", {}).get("clue_count") == args.response_clue_count
        )
    ]
    for position, (response_key, response) in enumerate(eligible, 1):
        index = response["source_index"]
        key = f"{response_key}:{prompt_hash}:{args.teacher_model}:{args.reasoning_effort}"
        if key in run["source_recovery"] and not args.force:
            print(f"recover [{position}/{len(eligible)}] {index}: cached")
            continue
        source = run["sources"][str(index)]
        prompt = render_template(
            template,
            {"SOURCE_QUESTION": source["question"], "CANDIDATE_QUESTION": response["output"]["question"]},
        )
        raw: dict[str, Any] | None = None
        try:
            reserve_teacher_request(run, prompt, args.teacher_max_tokens, args.max_cost_usd)
            raw = teacher_call(client, prompt, args.teacher_model, args.teacher_max_tokens, args.reasoning_effort)
            parsed = validate_source_recovery(extract_json_object(raw['content']),
                                              strict=args.recovery_prompt == 'source_recovery_p2')
            value = parsed.get('source_recovery')
            run["source_recovery"][key] = {
                "source_index": index,
                "response_key": response_key,
                "candidate_question_hash": stable_hash(response['output']['question']),
                "source_question_hash": stable_hash(source['question']),
                "rendered_input_hash": stable_hash(prompt),
                "prompt": args.recovery_prompt,
                "prompt_hash": prompt_hash,
                "model": args.teacher_model,
                "reasoning_effort": args.reasoning_effort,
                "output": parsed,
                "request": {k: v for k, v in raw.items() if k != "content"},
                "raw_content": raw["content"],
            }
            print(f"recover [{position}/{len(eligible)}] {index}: {value}")
        except Exception as exc:
            failure(run, "source_recovery", index, key, exc, raw)
            print(f"recover [{position}/{len(eligible)}] {index}: FAILED {exc}")
        atomic_write_json(args.output, run)


def validate_judge_fixtures(args: argparse.Namespace, run: dict[str, Any]) -> None:
    """Run authored controls through the same source-blind primary evaluator."""

    client = deepinfra_client(args.timeout)
    template = load_prompt(args.evaluate_prompt, args.prompt_dir)
    prompt_hash = stable_hash(template)
    payload = read_json(args.fixtures)
    fixtures = payload.get("fixtures")
    if not isinstance(fixtures, list):
        raise ValueError("Judge fixture file must contain a fixtures list")
    run.setdefault("judge_fixtures", {})
    for position, fixture in enumerate(fixtures, 1):
        fixture_id = fixture["id"]
        key = f"{fixture_id}:{stable_hash(fixture)}:{prompt_hash}:{args.teacher_model}:{args.reasoning_effort}"
        if key in run["judge_fixtures"] and not args.force:
            print(f"judge-fixture [{position}/{len(fixtures)}] {fixture_id}: cached")
            continue
        prompt = render_template(
            template,
            {
                "FINAL_ANSWER": fixture["final_answer"],
                "RENDERED_CLUES": "\n".join(f"- {clue}" for clue in fixture["clues"]),
                "STUDENT_RESPONSE": fixture["student_response"],
            },
        )
        raw: dict[str, Any] | None = None
        try:
            reserve_teacher_request(run, prompt, args.teacher_max_tokens, args.max_cost_usd)
            raw = teacher_call(client, prompt, args.teacher_model, args.teacher_max_tokens, args.reasoning_effort)
            parsed = validate_evaluation(extract_json_object(raw["content"]), strict_inference=args.evaluate_prompt=='evaluate_p3')
            score = parsed.get("score")
            passed = parsed.get("status") == "scored" and score in fixture["acceptable_scores"]
            run["judge_fixtures"][key] = {
                "fixture_id": fixture_id,
                "category": fixture["category"],
                "expected": fixture["acceptable_scores"],
                "passed": passed,
                "prompt": args.evaluate_prompt,
                "prompt_hash": prompt_hash,
                "model": args.teacher_model,
                "reasoning_effort": args.reasoning_effort,
                "output": parsed,
                "request": {k: v for k, v in raw.items() if k != "content"},
                "raw_content": raw["content"],
            }
            print(f"judge-fixture [{position}/{len(fixtures)}] {fixture_id}: score={score} pass={passed}")
        except Exception as exc:
            failure(run, "judge_fixture", -1, key, exc, raw)
            print(f"judge-fixture [{position}/{len(fixtures)}] {fixture_id}: FAILED {exc}")
        atomic_write_json(args.output, run)


def summarize(run: dict[str, Any]) -> dict[str, Any]:
    # A response can be rescored after an evaluator revision.  Report its latest
    # judgment once so exploratory rescoring does not inflate aggregate counts.
    latest_evaluations: dict[str, dict[str, Any]] = {}
    for record in run.get("evaluations", {}).values():
        latest_evaluations[record["response_key"]] = record
    evaluation_records = list(latest_evaluations.values())
    evaluations = [item["output"] for item in evaluation_records]
    scores = [item["score"] for item in evaluations if isinstance(item.get("score"), int)]
    accepted: list[dict[str, Any]] = []
    bank_evaluations: list[dict[str, Any]] = []
    bank_accepted: list[dict[str, Any]] = []
    for record in evaluation_records:
        response = run.get("responses", {}).get(record.get("response_key"), {})
        output = record["output"]
        if response.get("condition", response.get("public_evidence", {}).get("condition")) == "bank":
            bank_evaluations.append(output)
            if is_grounded_success(output):
                bank_accepted.append(output)
                accepted.append(output)
        elif is_scored_success(output):
            accepted.append(output)
    usages: list[dict[str, Any]] = []
    for section in (
        "banks",
        "audits",
        "disclosures",
        "disclosure_audits",
        "responses",
        "evaluations",
        "source_recovery",
        "judge_fixtures",
    ):
        for item in run.get(section, {}).values():
            usage = item.get("request", {}).get("usage")
            if isinstance(usage, dict):
                usages.append(usage)
    by_condition: dict[str, dict[str, Any]] = {}
    evaluations_by_response = {item["response_key"]: item["output"] for item in run.get("evaluations", {}).values()}
    recovery_by_response = {
        item["response_key"]: item["output"] for item in run.get("source_recovery", {}).values()
    }
    for response_key, response in run.get("responses", {}).items():
        bank_prompt = run.get("banks", {}).get(response.get("bank_key"), {}).get("prompt", "none")
        label = ":".join(
            [
                response.get("condition", response.get("public_evidence", {}).get("condition", "bank")),
                response.get("prompt", "unknown"),
                str(response.get("public_evidence", {}).get("clue_count")),
                response.get("public_evidence", {}).get("style", "unknown"),
                str(response.get("public_evidence", {}).get("disclosure")),
                response.get("public_evidence", {}).get("selection_policy", "random"),
                bank_prompt,
            ]
        )
        cell = by_condition.setdefault(
            label,
            {
                "responses": 0,
                "evaluations": 0,
                "successes": 0,
                "scores": [],
                "recovery_scores": [],
            },
        )
        cell["responses"] += 1
        evaluation = evaluations_by_response.get(response_key)
        if evaluation and isinstance(evaluation.get("score"), int):
            cell["evaluations"] += 1
            cell["scores"].append(evaluation["score"])
            condition = response.get("condition", response.get("public_evidence", {}).get("condition", "bank"))
            success = is_grounded_success(evaluation) if condition == "bank" else is_scored_success(evaluation)
            cell["successes"] += int(success)
        recovery = recovery_by_response.get(response_key)
        if recovery and isinstance(recovery.get("source_recovery"), int):
            cell["recovery_scores"].append(recovery["source_recovery"])
    for cell in by_condition.values():
        cell["success_rate"] = cell["successes"] / cell["evaluations"] if cell["evaluations"] else None
        cell["mean_score"] = sum(cell["scores"]) / len(cell["scores"]) if cell["scores"] else None
        cell["source_recovery_count"] = len(cell["recovery_scores"])
        cell["exact_source_recovery_rate"] = (
            sum(score == 2 for score in cell["recovery_scores"]) / len(cell["recovery_scores"])
            if cell["recovery_scores"]
            else None
        )
        cell["mean_source_recovery"] = (
            sum(cell["recovery_scores"]) / len(cell["recovery_scores"])
            if cell["recovery_scores"]
            else None
        )
        del cell["scores"]
        del cell["recovery_scores"]
    latest_fixtures: dict[tuple[str, str], dict[str, Any]] = {}
    for item in run.get("judge_fixtures", {}).values():
        label = f"{item.get('model')}:{item.get('reasoning_effort')}:{item.get('prompt')}"
        latest_fixtures[(label, item.get("fixture_id", "unknown"))] = item
    fixtures = list(latest_fixtures.values())
    fixture_groups: dict[str, dict[str, int | float | None]] = {}
    for item in fixtures:
        label = f"{item.get('model')}:{item.get('reasoning_effort')}:{item.get('prompt')}"
        group = fixture_groups.setdefault(label, {"count": 0, "passed": 0, "accuracy": None})
        group["count"] = int(group["count"]) + 1
        group["passed"] = int(group["passed"]) + int(bool(item.get("passed")))
    for group in fixture_groups.values():
        group["accuracy"] = int(group["passed"]) / int(group["count"])
    recovery_scores = [
        item["output"].get("source_recovery")
        for item in run.get("source_recovery", {}).values()
        if isinstance(item.get("output", {}).get("source_recovery"), int)
    ]
    return {
        "sources": len(run.get("sources", {})),
        "banks": len(run.get("banks", {})),
        "audits": len(run.get("audits", {})),
        "disclosures": len(run.get("disclosures", {})),
        "disclosure_audits": len(run.get("disclosure_audits", {})),
        "responses": len(run.get("responses", {})),
        "evaluations": len(evaluations),
        "grounded_successes": len(accepted),
        "grounded_success_rate": len(accepted) / len(evaluations) if evaluations else None,
        "bank_grounded_successes": len(bank_accepted),
        "bank_grounded_success_rate": (
            len(bank_accepted) / len(bank_evaluations) if bank_evaluations else None
        ),
        "mean_score": sum(scores) / len(scores) if scores else None,
        "unresolved": sum(item.get("status") == "needs_review" for item in evaluations),
        "failures": len(run.get("failures", [])),
        "deepinfra_estimated_cost_usd": actual_cost(run),
        "judge_fixture_accuracy": (
            sum(bool(item.get("passed")) for item in fixtures) / len(fixtures) if fixtures else None
        ),
        "judge_fixture_count": len(fixtures),
        "judge_fixtures_by_config": fixture_groups,
        "source_recovery": {
            "count": len(recovery_scores),
            "score_0": sum(score == 0 for score in recovery_scores),
            "score_1": sum(score == 1 for score in recovery_scores),
            "score_2": sum(score == 2 for score in recovery_scores),
            "exact_rate": (
                sum(score == 2 for score in recovery_scores) / len(recovery_scores)
                if recovery_scores
                else None
            ),
        },
        "by_condition": by_condition,
        "usage": {
            key: sum(int(item.get(key) or 0) for item in usages)
            for key in ("prompt_tokens", "completion_tokens", "total_tokens")
        },
    }


def render_report(run: dict[str, Any]) -> str:
    summary = summarize(run)
    lines = [
        "# RECONSTRUCT pilot report",
        "",
        f"Generated: {utc_now()}",
        "",
        "## Summary",
        "",
        "```json",
        json.dumps(summary, indent=2),
        "```",
        "",
        "## Cases",
        "",
    ]
    by_response = {item["response_key"]: item for item in run.get("evaluations", {}).values()}
    recovery_by_response = {item["response_key"]: item for item in run.get("source_recovery", {}).values()}
    for response_key, response in sorted(run.get("responses", {}).items(), key=lambda pair: pair[1]["source_index"]):
        index = response["source_index"]
        source = run["sources"][str(index)]
        evaluation = by_response.get(response_key, {}).get("output")
        lines.extend(
            [
                f"### Source {index}: {source['broad_topic']}",
                "",
                f"**Source question (private):** {source['question']}",
                "",
                f"**Answer:** {source['final_answer']}",
                "",
                f"**Condition:** {response.get('condition', response['public_evidence'].get('condition', 'bank'))}; "
                f"prompt={response.get('prompt')}; seed={response.get('sampling', {}).get('seed')}",
                "",
                "**Public clues:**",
                "",
                response["public_evidence"]["rendered_clues"],
                "",
                f"**Reconstruction:** {response['output']['question']}",
                "",
                f"**Justification:** {response['output']['justification']}",
                "",
                f"**Evaluation:** {json.dumps(evaluation, ensure_ascii=False) if evaluation else 'not evaluated'}",
                "",
                f"**Source recovery:** {json.dumps(recovery_by_response.get(response_key, {}).get('output'), ensure_ascii=False) if response_key in recovery_by_response else 'not evaluated'}",
                "",
            ]
        )
    return "\n".join(lines) + "\n"


def add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--solutions", type=Path, default=DEFAULT_SOLUTIONS)
    parser.add_argument("--output", type=Path, default=DEFAULT_RUN)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--prompt-dir", type=Path, default=DEFAULT_PROMPT_DIR)
    parser.add_argument("--split", choices=("D1", "D2", "C", "reserve"), default="D1")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--indices", type=int, nargs="+")
    parser.add_argument("--split-seed", type=int, default=20260920)
    parser.add_argument("--teacher-model", default=DEFAULT_TEACHER_MODEL)
    parser.add_argument("--student-model", default=DEFAULT_MODEL)
    parser.add_argument("--teacher-max-tokens", type=int, default=16384)
    parser.add_argument("--max-cost-usd", type=float, default=5.0)
    parser.add_argument(
        "--reasoning-effort",
        choices=("minimal", "low", "medium", "high", "xhigh", "max"),
        default="high",
    )
    parser.add_argument("--timeout", type=float, default=900.0)
    parser.add_argument("--force", action="store_true")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for command in (
        "init",
        "convert",
        "audit",
        "disclose",
        "audit-disclosure",
        "copy-challenge",
        "student",
        "evaluate",
        "recover",
        "validate-judge",
        "smoke",
        "report",
    ):
        child = sub.add_parser(command)
        add_common_args(child)
        if command in {"convert", "smoke"}:
            child.add_argument("--convert-prompt", default="convert_p1")
            child.add_argument("--max-bank-clues", type=int, choices=(4, 6), default=4)
        if command in {"audit", "smoke"}:
            child.add_argument("--audit-prompt", default="audit_p1")
            child.add_argument("--bank-prompt")
        if command == "disclose":
            child.add_argument("--disclosure-prompt", default="disclosure_p1")
            child.add_argument("--bank-prompt")
        if command == 'copy-challenge':
            child.add_argument('--copy-prompt', default='copy_challenge_p1')
            child.add_argument('--bank-prompt')
        if command == "audit-disclosure":
            child.add_argument("--disclosure-audit-prompt", default="disclosure_audit_p1")
            child.add_argument("--bank-prompt")
        if command in {"student", "smoke"}:
            child.add_argument("--student-prompt", default="student_p1")
            child.add_argument("--local-url", default=DEFAULT_LOCAL_URL)
            child.add_argument("--clue-count", type=int, default=3)
            child.add_argument("--all-clues", action="store_true")
            child.add_argument("--clue-seed", type=int, default=20260920)
            child.add_argument(
                "--selection-policy", choices=("random", "anchor_first", "bank_order"), default="random"
            )
            child.add_argument("--style", choices=("sentence", "fragment", "paragraph"), default="sentence")
            child.add_argument(
                "--condition",
                choices=("bank", "answer_only", "full_solution", "random_excerpt"),
                default="bank",
            )
            child.add_argument("--temperature", type=float, default=0.7)
            child.add_argument("--top-p", type=float, default=0.8)
            child.add_argument("--top-k", type=int, default=20)
            child.add_argument("--max-tokens", type=int, default=16384)
            child.add_argument("--seed", type=int, default=0)
            child.add_argument("--disclosure", choices=("low", "medium", "high"), default="medium")
            if command == "student":
                child.add_argument("--bank-prompt")
        if command in {"evaluate", "smoke"}:
            child.add_argument("--evaluate-prompt", default="evaluate_p1")
            child.add_argument("--response-prompt")
            child.add_argument("--response-clue-count", type=int)
            child.add_argument("--response-style", choices=("sentence", "fragment", "paragraph"))
            child.add_argument("--response-disclosure", choices=("low", "medium", "high"))
            child.add_argument(
                "--response-selection-policy", choices=("random", "anchor_first", "bank_order")
            )
            child.add_argument("--response-bank-prompt")
        if command == "validate-judge":
            child.add_argument("--evaluate-prompt", default="evaluate_p1")
            child.add_argument("--fixtures", type=Path, default=DEFAULT_JUDGE_FIXTURES)
        if command in {"recover", "smoke"}:
            child.add_argument("--recovery-prompt", default="source_recovery_p1")
            if command == "recover":
                child.add_argument("--response-prompt")
                child.add_argument("--response-clue-count", type=int)
                child.add_argument("--response-style", choices=("sentence", "fragment", "paragraph"))
                child.add_argument("--response-disclosure", choices=("low", "medium", "high"))
                child.add_argument(
                    "--response-selection-policy", choices=("random", "anchor_first", "bank_order")
                )
                child.add_argument("--response-bank-prompt")
    return parser.parse_args(argv)


def execute(args: argparse.Namespace) -> None:
    if args.limit is not None and args.limit < 1:
        raise ValueError("limit must be positive")
    run = load_or_create_run(args)
    indices = selected_indices(run, args.split, args.limit, args.indices)
    if args.command == "init":
        print(json.dumps({key: len(value) for key, value in run["partitions"].items()}, indent=2))
        return
    if args.command in {"convert", "smoke"}:
        convert_sources(args, run, indices)
    if args.command in {"audit", "smoke"}:
        audit_sources(args, run, indices)
    if args.command == "disclose":
        generate_disclosures(args, run, indices)
    if args.command == "audit-disclosure":
        audit_disclosures(args, run, indices)
    if args.command == 'copy-challenge':
        copy_challenge_sources(args, run, indices)
    if args.command in {"student", "smoke"}:
        student_sources(args, run, indices)
    if args.command in {"evaluate", "smoke"}:
        evaluate_responses(args, run, indices)
    if args.command in {"recover", "smoke"}:
        source_recovery_responses(args, run, indices)
    if args.command == "validate-judge":
        validate_judge_fixtures(args, run)
    atomic_write_json(args.output, run)
    atomic_write_text(args.report, render_report(run))
    print(json.dumps(summarize(run), indent=2))


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    lock_path = args.output.with_suffix(args.output.suffix + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("w", encoding="utf-8") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        execute(args)


if __name__ == "__main__":
    main()
