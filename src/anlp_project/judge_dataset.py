"""Export private Judge generations and score the fixed response structure."""

from __future__ import annotations

import argparse
import hashlib
import re
from collections import Counter
from pathlib import Path
from typing import Any

from .judge_validation import public_export_record
from .paths import ARTIFACTS_DIR, PROJECT_ROOT
from .storage import atomic_write_json, read_json


DEFAULT_INPUT = ARTIFACTS_DIR / "qwen3-8b" / "judge" / "judge_generator_v1_rubric-dev-60.json"
DEFAULT_OUTPUT = ARTIFACTS_DIR / "qwen3-8b" / "judge" / "judge-generator-v1-dev-60-public.json"
DEFAULT_AUDIT = ARTIFACTS_DIR / "qwen3-8b" / "judge" / "judge-generator-v1-dev-60-audit.json"
DECISION_PATTERN = re.compile(r"^\s*Decision\s*:\s*(correct|incorrect)\s*$", re.IGNORECASE)
FIRST_ERROR_PATTERN = re.compile(r"^\s*First\s+wrong\s+step\s*:\s*(none|S[1-9][0-9]*)\s*$", re.IGNORECASE)
EXPLANATION_PATTERN = re.compile(r"^\s*Explanation\s*:\s*(.*)$", re.IGNORECASE)


def parse_student_response(response: str) -> tuple[dict[str, Any] | None, list[str]]:
    """Parse the fixed student format without attempting semantic grading."""

    if not isinstance(response, str) or not response.strip():
        return None, ["empty response"]
    lines = response.strip().splitlines()
    decision: str | None = None
    first_error: str | None = None
    explanation_lines: list[str] = []
    errors: list[str] = []
    explanation_started = False
    for line in lines:
        if explanation_started:
            explanation_lines.append(line)
            continue
        decision_match = DECISION_PATTERN.match(line)
        if decision_match:
            if decision is not None:
                errors.append("duplicate Decision field")
            decision = decision_match.group(1).lower()
            continue
        first_error_match = FIRST_ERROR_PATTERN.match(line)
        if first_error_match:
            if first_error is not None:
                errors.append("duplicate First wrong step field")
            first_error = first_error_match.group(1).lower()
            continue
        explanation_match = EXPLANATION_PATTERN.match(line)
        if explanation_match:
            explanation_started = True
            explanation_lines.append(explanation_match.group(1))
            continue
        if line.strip():
            errors.append(f"unexpected line: {line.strip()!r}")
    if decision is None:
        errors.append("missing Decision field")
    if first_error is None:
        errors.append("missing First wrong step field")
    explanation = "\n".join(explanation_lines).strip()
    if not explanation:
        errors.append("missing Explanation field")
    if errors:
        return None, errors
    normalized_first_error = None if first_error.lower() == "none" else first_error.upper()
    return {
        "decision": decision,
        "first_error_step_id": normalized_first_error,
        "explanation": explanation,
    }, []


def score_structural_response(response: str, private: dict[str, Any]) -> dict[str, Any]:
    """Score fields that can be compared exactly; explanation semantics stay external."""

    parsed, errors = parse_student_response(response)
    if errors or parsed is None:
        return {
            "parse_status": "invalid",
            "parse_errors": errors,
            "decision_correct": False,
            "first_error_correct": False,
            "explanation_present": False,
            "strict_structural_correct": False,
        }
    expected_label = private.get("label")
    expected_first_error = private.get("first_error_step_id")
    decision_correct = parsed["decision"] == expected_label
    first_error_correct = parsed["first_error_step_id"] == expected_first_error
    explanation_present = bool(parsed["explanation"])
    return {
        "parse_status": "valid",
        "parse_errors": [],
        "decision_correct": decision_correct,
        "first_error_correct": first_error_correct,
        "explanation_present": explanation_present,
        "strict_structural_correct": decision_correct and first_error_correct and explanation_present,
        "parsed": parsed,
    }


def _public_hash(public: dict[str, Any]) -> str:
    import json

    payload = json.dumps(public, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def export_public_dataset(
    input_path: Path,
    output_path: Path,
    audit_path: Path,
    *,
    split: str,
    require_valid: bool = True,
    require_one_per_source: bool = False,
) -> dict[str, Any]:
    """Export only public fields and write a rejection/audit ledger separately."""

    payload = read_json(input_path)
    items = payload.get("items")
    if not isinstance(items, list):
        raise ValueError(f"{input_path} must contain an items list")
    accepted: list[dict[str, Any]] = []
    audit: list[dict[str, Any]] = []
    seen_sources: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            audit.append({"item_id": None, "status": "rejected", "reasons": ["item is not an object"]})
            continue
        item_id = item.get("item_id")
        reasons: list[str] = []
        if item.get("status") != "completed":
            reasons.append(f"generation status is {item.get('status')!r}")
        if require_valid and item.get("validation_status") != "valid":
            reasons.extend(item.get("validation_errors") or ["generation validation did not pass"])
        generated = item.get("parsed_output")
        if not isinstance(generated, dict):
            reasons.append("parsed_output is missing")
        if reasons:
            audit.append({"item_id": item_id, "source_id": item.get("source_id"), "status": "rejected", "reasons": reasons})
            continue
        source_id = str(item.get("source_id"))
        if require_one_per_source and source_id in seen_sources:
            raise ValueError(f"More than one accepted Judge item for source_id {source_id}")
        seen_sources.add(source_id)
        public = public_export_record(item, generated)
        public["split"] = split
        public["public_sha256"] = _public_hash(public["public"])
        accepted.append(public)
        audit.append({"item_id": item_id, "source_id": source_id, "status": "accepted"})

    if require_one_per_source and len(seen_sources) != len(accepted):
        raise ValueError("Public export contains duplicate source IDs")
    if require_valid and not accepted:
        # A prepared or entirely failed batch is not a usable dataset export.
        raise ValueError("No valid generated Judge items are available for public export")

    source_metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
    output = {
        "manifest_name": f"judge-{split}-public",
        "task": "JUDGE",
        "split": split,
        "privacy": "public-only; no labels, reference solutions, or private explanations",
        "source_generation": {
            "model": source_metadata.get("model"),
            "prompt_file": source_metadata.get("prompt_file"),
            "prompt_sha256": source_metadata.get("prompt_sha256"),
            "input_artifact": str(input_path),
        },
        "item_count": len(accepted),
        "problems": accepted,
    }
    audit_output = {
        "manifest_name": f"judge-{split}-audit",
        "input_artifact": str(input_path),
        "accepted_count": len(accepted),
        "rejected_count": sum(record.get("status") == "rejected" for record in audit),
        "status_counts": dict(Counter(record.get("status") for record in audit)),
        "items": audit,
    }
    atomic_write_json(output_path, output)
    atomic_write_json(audit_path, audit_output)
    return output


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--audit", type=Path, default=DEFAULT_AUDIT)
    parser.add_argument("--split", default="development")
    parser.add_argument("--allow-invalid", action="store_true")
    parser.add_argument("--require-one-per-source", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output = export_public_dataset(
        args.input,
        args.output,
        args.audit,
        split=args.split,
        require_valid=not args.allow_invalid,
        require_one_per_source=args.require_one_per_source,
    )
    print(f"Exported {output['item_count']} public Judge items to {args.output}")


if __name__ == "__main__":
    main()
