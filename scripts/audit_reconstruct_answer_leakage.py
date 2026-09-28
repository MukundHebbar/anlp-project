#!/usr/bin/env python3
"""Flag RECONSTRUCT rows where the literal final-answer value reappears inside the
Qwen-reconstructed question text (answer used as a smuggled premise/hypothesis
instead of being derived). Read-only diagnostic; makes no model calls and does
not gate or filter any pipeline output.

Usage: uv run scripts/audit_reconstruct_answer_leakage.py <questions-answers.jsonl> [...]
"""
import json
import re
import sys
from pathlib import Path


def normalize_number(text: str) -> str:
    return re.sub(r"[^0-9.\-]", "", text or "")


def has_answer_leakage(question: str, final_answer: str) -> bool:
    needle = normalize_number(final_answer)
    if len(needle) < 2:
        return False
    return needle in normalize_number(question)


def audit(path: Path) -> dict:
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    hits = []
    for row in rows:
        qwen = row.get("qwen") or {}
        question = qwen.get("question", "")
        answer = row.get("source_final_answer", "")
        if question and has_answer_leakage(question, answer):
            hits.append(
                {
                    "source_index": row.get("source_index"),
                    "rating_v4": row.get("rating_v4"),
                    "final_answer": answer,
                    "qwen_question": question,
                }
            )
    return {"path": str(path), "total_rows": len(rows), "leaked": len(hits), "examples": hits}


if __name__ == "__main__":
    paths = [Path(p) for p in sys.argv[1:]] or [Path("artifacts/reconstruct/valid-100-recovery-v1/questions-answers.jsonl")]
    for path in paths:
        report = audit(path)
        print(json.dumps({k: v for k, v in report.items() if k != "examples"}, indent=2))
        for example in report["examples"]:
            print(" -", example["source_index"], "rating", example["rating_v4"], "answer", repr(example["final_answer"]))
