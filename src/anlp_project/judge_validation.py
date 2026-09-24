"""Schema and privacy checks for generated JUDGE examples."""

from __future__ import annotations

import json
import re
from typing import Any


ALLOWED_LABELS = {"correct", "incorrect"}
ALLOWED_ERROR_TYPES = {
    "arithmetic_algebra",
    "sign_inequality",
    "invalid_theorem_condition",
    "unjustified_implication",
    "missing_case",
    "domain_restriction",
    "counting_bijection",
    "other",
}
ALLOWED_ERROR_POSITIONS = {"early", "middle", "late"}
STEP_ID_PATTERN = re.compile(r"S([1-9][0-9]*)$")
ERROR_POSITIONS = ("early", "middle", "late")
PUBLIC_KEYS = {"problem", "proposed_solution", "instruction"}
PRIVATE_KEYS = {
    "label",
    "first_error_step_id",
    "first_error_explanation",
    "error_type",
    "error_position",
    "teacher_target_response",
}


def parse_json_response(response: str) -> dict[str, Any]:
    """Parse a JSON object, tolerating one surrounding markdown code fence."""

    text = response.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        decoder = json.JSONDecoder()
        for position, character in enumerate(text):
            if character != "{":
                continue
            try:
                value, _ = decoder.raw_decode(text[position:])
            except json.JSONDecodeError:
                continue
            break
        else:
            raise ValueError("response does not contain a JSON object")
    if not isinstance(value, dict):
        raise ValueError("generated response must be a JSON object")
    return value


def _nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def observed_error_position(step_id: str, step_count: int) -> str:
    """Assign a step to the first, middle, or final third of a proposal."""

    match = STEP_ID_PATTERN.fullmatch(step_id)
    if match is None or step_count < 3:
        raise ValueError("Position requires a valid step ID and at least three steps")
    step_number = int(match.group(1))
    if step_number > step_count:
        raise ValueError("Error step is outside the proposal")
    return ERROR_POSITIONS[min(2, (step_number - 1) * 3 // step_count)]


def validate_generated_output(
    output: Any,
    *,
    target_label: str | None = None,
    requested_error_type: str | None = None,
    requested_error_position: str | None = None,
    expected_problem: str | None = None,
    reference_solution: str | None = None,
) -> list[str]:
    """Return deterministic validation errors; an empty list means valid schema."""

    errors: list[str] = []
    if not isinstance(output, dict):
        return ["top-level output is not an object"]
    public = output.get("public")
    private = output.get("private")
    if not isinstance(public, dict):
        errors.append("missing public object")
    if not isinstance(private, dict):
        errors.append("missing private object")
    if errors:
        return errors

    if set(public) != PUBLIC_KEYS:
        errors.append("public object has unexpected or missing fields")
    if set(private) != PRIVATE_KEYS:
        errors.append("private object has unexpected or missing fields")
    if not _nonempty_string(public.get("problem")):
        errors.append("public.problem is empty")
    if expected_problem is not None and public.get("problem") != expected_problem:
        errors.append("public.problem does not exactly preserve the source problem")
    if not _nonempty_string(public.get("instruction")):
        errors.append("public.instruction is empty")
    steps = public.get("proposed_solution")
    if not isinstance(steps, list) or len(steps) < 2:
        errors.append("public.proposed_solution must contain at least two steps")
        steps = []
    step_ids: list[str] = []
    for step in steps:
        if not isinstance(step, dict):
            errors.append("every proposed step must be an object")
            continue
        if set(step) != {"step_id", "text"}:
            errors.append("proposed steps may contain only step_id and text")
        step_id = step.get("step_id")
        if not isinstance(step_id, str) or not STEP_ID_PATTERN.fullmatch(step_id):
            errors.append(f"invalid step ID: {step_id!r}")
        else:
            step_ids.append(step_id)
        if not _nonempty_string(step.get("text")):
            errors.append(f"empty text for step {step_id!r}")
    expected_ids = [f"S{index}" for index in range(1, len(step_ids) + 1)]
    if step_ids != expected_ids:
        errors.append("step IDs must be unique and consecutive from S1")

    label = private.get("label")
    if label not in ALLOWED_LABELS:
        errors.append(f"invalid private.label: {label!r}")
    if target_label is not None and label != target_label:
        errors.append(f"private.label does not match requested label {target_label!r}")

    first_error = private.get("first_error_step_id")
    explanation = private.get("first_error_explanation")
    error_type = private.get("error_type")
    error_position = private.get("error_position")
    if label == "correct":
        if first_error is not None or explanation is not None or error_type is not None or error_position is not None:
            errors.append("correct output must use null for all error metadata")
    elif label == "incorrect":
        if len(step_ids) < 3:
            errors.append("incorrect proposal needs at least three steps to locate early/middle/late errors")
        if first_error not in step_ids:
            errors.append("incorrect output has no first error step from the proposal")
        elif error_position in ALLOWED_ERROR_POSITIONS and len(step_ids) >= 3:
            observed_position = observed_error_position(first_error, len(step_ids))
            if observed_position != error_position:
                errors.append(
                    f"annotated error position {error_position!r} does not match "
                    f"step {first_error} in a {len(step_ids)}-step proposal "
                    f"({observed_position!r})"
                )
        if not _nonempty_string(explanation):
            errors.append("incorrect output has no first-error explanation")
        if error_type not in ALLOWED_ERROR_TYPES:
            errors.append(f"invalid error type: {error_type!r}")
        if error_position not in ALLOWED_ERROR_POSITIONS:
            errors.append(f"invalid error position: {error_position!r}")
    if target_label == "incorrect":
        if requested_error_type is not None and error_type != requested_error_type:
            errors.append(f"error type does not match requested {requested_error_type!r}")
        if requested_error_position is not None and error_position != requested_error_position:
            errors.append(f"error position does not match requested {requested_error_position!r}")

    target_response = private.get("teacher_target_response")
    if not _nonempty_string(target_response):
        errors.append("private.teacher_target_response is empty")
    elif "Decision:" not in target_response or "First wrong step:" not in target_response:
        errors.append("teacher_target_response does not use the fixed response format")

    public_text = json.dumps(public, ensure_ascii=False).lower()
    if reference_solution and reference_solution.strip() and reference_solution.strip().lower() in public_text:
        errors.append("reference solution leaked into public output")
    if _nonempty_string(explanation) and explanation.strip().lower() in public_text:
        errors.append("private first-error explanation leaked into public output")
    return errors


def public_export_record(source_record: dict[str, Any], generated: dict[str, Any]) -> dict[str, Any]:
    """Return the public-only JUDGE record used for student inference."""

    public = generated.get("public")
    if not isinstance(public, dict):
        raise ValueError("generated item has no public object")
    return {
        "source_id": source_record.get("source_id"),
        "source_index": source_record.get("source_index"),
        "source_dataset": "DeepMath-103K-pilot",
        "topic": source_record.get("topic"),
        "difficulty": source_record.get("difficulty"),
        "public": public,
    }
