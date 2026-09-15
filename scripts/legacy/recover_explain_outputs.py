"""Recover harmless JSON fences from a completed EXPLAIN generation artifact."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from anlp_project.explain_deepseek_flash import validate_v1_output
from anlp_project.storage import atomic_write_json, read_json


def _unwrap_json_fence(response: str) -> str:
    stripped = response.strip()
    if not stripped.startswith("```"):
        return stripped
    if not stripped.endswith("```"):
        raise ValueError("response is not one complete Markdown code fence")
    first_newline = stripped.find("\n")
    if first_newline < 0:
        raise ValueError("code fence has no body")
    language = stripped[3:first_newline].strip()
    if language not in {"", "json"}:
        raise ValueError(f"unsupported code-fence language: {language}")
    body = stripped[first_newline + 1 : -3].strip()
    if not body:
        raise ValueError("code fence body is empty")
    return body


def _escape_invalid_json_backslashes(text: str) -> str:
    """Repair only LaTeX-style backslashes that are invalid JSON escapes."""
    valid_simple = {'"', "\\", "/", "b", "f", "n", "r", "t"}
    result: list[str] = []
    in_string = False
    index = 0
    while index < len(text):
        character = text[index]
        if character == '"':
            result.append(character)
            escaped = index > 0 and text[index - 1] == "\\"
            if not escaped:
                in_string = not in_string
            index += 1
            continue
        if character == "\\" and in_string:
            next_character = text[index + 1] if index + 1 < len(text) else ""
            valid_unicode = (
                next_character == "u"
                and index + 5 < len(text)
                and all(char in "0123456789abcdefABCDEF" for char in text[index + 2 : index + 6])
            )
            if next_character not in valid_simple and not valid_unicode:
                result.append("\\\\")
                index += 1
                continue
        result.append(character)
        index += 1
    return "".join(result)


def _parse_response(response: str) -> tuple[Any, str]:
    body = _unwrap_json_fence(response)
    try:
        return json.loads(body), "strict_json"
    except json.JSONDecodeError:
        repaired = _escape_invalid_json_backslashes(body)
        return json.loads(repaired), "escaped_invalid_latex_backslashes"


def recover(raw_path: Path, input_path: Path, output_path: Path) -> dict[str, Any]:
    raw = read_json(raw_path)
    source = read_json(input_path)
    source_records = {
        record["source_index"]: record
        for record in source.get("problems", [])
        if isinstance(record, dict) and isinstance(record.get("source_index"), int)
    }
    items = [dict(item) for item in raw.get("items", []) if isinstance(item, dict)]
    item_indices = {item.get("source_index") for item in items}
    failures: list[dict[str, Any]] = []
    recovered_count = 0
    for failure in raw.get("failures", []):
        if not isinstance(failure, dict):
            failures.append({"error": "malformed_failure_record", "raw_record": failure})
            continue
        source_index = failure.get("source_index")
        response = failure.get("raw_response")
        try:
            if source_index not in source_records:
                raise ValueError("source_index is not present in the input manifest")
            if not isinstance(response, str):
                raise ValueError("failure has no raw response")
            value, recovery_method = _parse_response(response)
            value = validate_v1_output(value, source_records[source_index])
        except (TypeError, ValueError, json.JSONDecodeError) as error:
            failures.append(dict(failure))
            failures[-1]["recovery_error"] = f"{error.__class__.__name__}: {error}"
            continue
        if source_index in item_indices:
            failures.append({**failure, "recovery_error": "duplicate_source_index"})
            continue
        items.append({"source_index": source_index, "output": value})
        if recovery_method != "strict_json":
            items[-1]["recovery_method"] = recovery_method
        item_indices.add(source_index)
        recovered_count += 1

    expected_indices = set(source_records)
    missing_indices = sorted(expected_indices - item_indices - {failure.get("source_index") for failure in failures})
    for source_index in missing_indices:
        failures.append(
            {
                "source_index": source_index,
                "error": "GenerationInterrupted: request stopped before a response was returned",
                "raw_response": None,
            }
        )
    items.sort(key=lambda item: item["source_index"])
    failures.sort(key=lambda item: item.get("source_index", 10**9))
    metadata = dict(raw.get("metadata", {}))
    metadata.update(
        {
            "schema": "explain_v1_batch_recovered",
            "raw_artifact": str(raw_path),
            "recovery": "deterministically unwrap one complete json Markdown fence and revalidate v1 schema",
            "recovered_code_fence_count": recovered_count,
            "recovered_malformed_json_count": sum(
                item.get("recovery_method") == "escaped_invalid_latex_backslashes" for item in items
            ),
            "explicit_failure_count": len(failures),
            "expected_record_count": len(expected_indices),
        }
    )
    output = {"metadata": metadata, "items": items, "failures": failures}
    atomic_write_json(output_path, output)
    return output


def render_report(output: dict[str, Any]) -> str:
    metadata = output["metadata"]
    items = output["items"]
    failures = output["failures"]
    not_suitable = sum(item.get("output") == "NOT_SUITABLE" for item in items)
    return "\n".join(
        [
            "EXPLAIN-v1 DeepSeek generation (recovered)",
            f"Expected records: {metadata['expected_record_count']}",
            f"Valid EXPLAIN tasks: {len(items) - not_suitable}",
            f"NOT_SUITABLE: {not_suitable}",
            f"Fence-wrapped outputs recovered: {metadata['recovered_code_fence_count']}",
            f"Explicit failures: {len(failures)}",
            "Failures:",
            *[f"- source_index {item.get('source_index')}: {item.get('error')}" for item in failures],
            "",
        ]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, required=True)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    result = recover(args.raw, args.input, args.output)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(render_report(result), encoding="utf-8")
    print(f"wrote recovered EXPLAIN artifact to {args.output}")
    print(f"wrote report to {args.report}")
