"""Deterministic final-answer extraction, comparison, and cost accounting."""

from __future__ import annotations

import json
import re
from fractions import Fraction
from typing import Any

import sympy as sp
from sympy.parsing.sympy_parser import (
    implicit_multiplication_application,
    parse_expr,
    standard_transformations,
)


INPUT_PRICE_PER_MILLION = 0.08
OUTPUT_PRICE_PER_MILLION = 0.18


def _balanced_brace(text: str, opening: int) -> tuple[str, int] | None:
    if opening >= len(text) or text[opening] != "{":
        return None
    depth = 0
    for index in range(opening, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[opening + 1 : index], index + 1
    return None


def extract_final_answer(response: str) -> tuple[str | None, str]:
    """Extract one explicit answer tag, then support legacy boxed answers."""
    matches = re.findall(
        r"<final_answer>\s*(.*?)\s*</final_answer>",
        response,
        re.DOTALL | re.IGNORECASE,
    )
    if len(matches) == 1 and matches[0].strip():
        return matches[0].strip(), "tag"
    boxed = re.search(r"\\boxed\s*\{", response)
    if boxed:
        content = _balanced_brace(response, boxed.end() - 1)
        if content and content[0].strip():
            return content[0].strip(), "boxed_fallback"
    if matches:
        return None, "invalid_final_tag"
    return None, "missing_final_answer"


def split_reasoning_response(response: str) -> dict[str, str]:
    """Separate Qwen reasoning markup from the visible solution.

    Qwen/vLLM may return either paired ``<think>``/``<thinking>`` blocks or
    the generated contents followed by only a closing ``</think>`` tag. A
    response with an unclosed reasoning block is intentionally not treated as
    a visible solution, so a final-answer tag inside it cannot be scored.
    """
    text = str(response or "")
    opening = re.search(r"<(think|thinking)\s*>", text, re.IGNORECASE)
    if opening:
        tag = opening.group(1)
        closing = re.search(rf"</{tag}\s*>", text[opening.end() :], re.IGNORECASE)
        if closing is None:
            return {
                "reasoning_text": text[opening.end() :].strip(),
                "solution_text": "",
                "reasoning_parse_status": "unclosed",
            }
        close_start = opening.end() + closing.start()
        close_end = opening.end() + closing.end()
        reasoning = text[opening.end() : close_start].strip()
        visible = (text[: opening.start()] + text[close_end:]).strip()
        return {
            "reasoning_text": reasoning,
            "solution_text": visible,
            "reasoning_parse_status": "paired",
        }

    closing = re.search(r"</(think|thinking)\s*>", text, re.IGNORECASE)
    if closing:
        return {
            "reasoning_text": text[: closing.start()].strip(),
            "solution_text": text[closing.end() :].strip(),
            "reasoning_parse_status": "implicit_closed",
        }

    return {
        "reasoning_text": "",
        "solution_text": text.strip(),
        "reasoning_parse_status": "none",
    }


def _replace_fractions(text: str) -> str:
    text = re.sub(r"\\(?:d?frac)\s*(\d+)\s*(\d+)", r"(\1)/(\2)", text)
    pattern = re.compile(r"\\(?:d?frac)\s*\{")
    while True:
        match = pattern.search(text)
        if not match:
            return text
        numerator = _balanced_brace(text, match.end() - 1)
        if numerator is None:
            return text
        denominator = _balanced_brace(text, numerator[1])
        if denominator is None:
            return text
        replacement = f"({numerator[0]})/({denominator[0]})"
        text = text[: match.start()] + replacement + text[denominator[1] :]


def _unwrap_command(text: str, command: str) -> str:
    marker = f"\\{command}{{"
    while marker in text:
        start = text.find(marker)
        content = _balanced_brace(text, start + len(marker) - 1)
        if content is None:
            return text
        text = text[:start] + content[0] + text[content[1] :]
    return text


def _strip_redundant_outer_parentheses(text: str) -> str:
    if text.startswith("(") and text.endswith(")") and "," in text:
        return text
    while text.startswith("(") and text.endswith(")"):
        depth = 0
        closes_at_end = True
        for index, character in enumerate(text):
            if character == "(":
                depth += 1
            elif character == ")":
                depth -= 1
                if depth == 0 and index != len(text) - 1:
                    closes_at_end = False
                    break
        if closes_at_end and depth == 0:
            text = text[1:-1]
        else:
            break
    return text


def normalize_answer(value: str) -> str:
    """Normalize harmless formatting without claiming symbolic equivalence."""
    text = str(value).strip().strip("`")
    text = text.replace("$$", "")
    text = re.sub(r"\\\(|\\\)|\\\[|\\\]", "", text)
    text = text.replace("\\dfrac", "\\frac")
    text = _replace_fractions(text)
    text = re.sub(r"\\(?:mathbb|mathcal|mathfrak)\s+([A-Za-z])", r"\1", text)
    for command in ("boxed", "text", "mathrm", "mathbb", "mathcal", "mathfrak"):
        text = _unwrap_command(text, command)
    text = re.sub(r"\\pmod\s*\{([^{}]*)\}", r" mod (\1)", text)
    text = text.replace("\\ell", "l")
    text = re.sub(r"\\(?:left|right|displaystyle|!|,|;|quad)", "", text)
    text = text.replace("\\infty", "infinity").replace("∞", "infinity")
    text = text.replace("\\cdot", "*").replace("\\times", "*")
    text = text.replace("\\equiv", "equiv").replace("\\pmod", "mod")
    text = text.replace("\\operatorname", "")
    text = text.replace("^", "**")
    text = re.sub(r"_\{([^{}]*)\}", r"_\1", text)
    text = text.replace("{", "(").replace("}", ")")
    text = text.replace("\\", "")
    text = text.replace("$", "")
    text = re.sub(r"\s+", "", text).casefold()
    text = text.strip(".,;:")
    return _strip_redundant_outer_parentheses(text)


def _numeric_value(text: str) -> Fraction | None:
    """Evaluate a deliberately small arithmetic grammar exactly."""
    if not re.fullmatch(r"(?:\d+(?:\.\d+)?|[()+*/-]|\*\*)+", text):
        return None
    tokens = re.findall(r"\d+(?:\.\d+)?|\*\*|[()+*/-]", text)
    position = 0

    def parse_expr() -> Fraction:
        nonlocal position
        value = parse_term()
        while position < len(tokens) and tokens[position] in ("+", "-"):
            operator = tokens[position]
            position += 1
            right = parse_term()
            value = value + right if operator == "+" else value - right
        return value

    def parse_term() -> Fraction:
        nonlocal position
        value = parse_power()
        while position < len(tokens) and tokens[position] in ("*", "/"):
            operator = tokens[position]
            position += 1
            right = parse_power()
            if operator == "/" and right == 0:
                raise ZeroDivisionError
            value = value * right if operator == "*" else value / right
        return value

    def parse_power() -> Fraction:
        nonlocal position
        value = parse_factor()
        if position < len(tokens) and tokens[position] == "**":
            position += 1
            exponent = parse_power()
            if exponent.denominator != 1 or abs(exponent.numerator) > 10000:
                raise ValueError
            value = value ** exponent.numerator
        return value

    def parse_factor() -> Fraction:
        nonlocal position
        if position >= len(tokens):
            raise ValueError
        token = tokens[position]
        if token in ("+", "-"):
            position += 1
            value = parse_factor()
            return value if token == "+" else -value
        if token == "(":
            position += 1
            value = parse_expr()
            if position >= len(tokens) or tokens[position] != ")":
                raise ValueError
            position += 1
            return value
        if re.fullmatch(r"\d+(?:\.\d+)?", token):
            position += 1
            return Fraction(token)
        raise ValueError

    try:
        result = parse_expr()
        return result if position == len(tokens) else None
    except (ValueError, ZeroDivisionError):
        return None


def _candidate_variants(candidate_normalized: str) -> list[str]:
    variants = [candidate_normalized]
    if "=" in candidate_normalized and candidate_normalized.count("=") == 1:
        variants.append(candidate_normalized.rsplit("=", 1)[1].strip(". ,;:"))
    return list(dict.fromkeys(variants))


def _is_simple_text(text: str) -> bool:
    return bool(re.fullmatch(r"[a-z][a-z0-9 _-]*", text))


def _leading_boolean(candidate: str) -> str | None:
    match = re.match(r"^(?:[(:\[]\s*)?(yes|no)\b", candidate)
    return match.group(1) if match else None


def _leading_choice(candidate: str) -> str | None:
    match = re.match(r"^(?:[(:\[]\s*)?([abcd])\s*[.):\-]", candidate)
    return match.group(1) if match else None


def _safe_text_claim(expected: str, candidate: str) -> bool:
    if not _is_simple_text(expected) or not candidate.startswith(expected):
        return False
    remainder = candidate[len(expected) :]
    return bool(re.match(r"(?:iscorrect|istheanswer|iscorrectanswer)(?:$|[,.;])", remainder))


def _congruence_residue(candidate: str) -> str | None:
    match = re.fullmatch(r".+equiv(.+?)mod\((.+)\)", candidate)
    return match.group(1).strip() if match else None


def _sympy_expression(text: str) -> sp.Expr | None:
    """Parse a restricted expression without evaluating arbitrary model text."""
    if len(text) > 300 or not re.fullmatch(r"[a-z0-9_+*/().,\-<> ]+", text):
        return None
    if "__" in text or any(word in text for word in ("import", "lambda", "exec", "eval")):
        return None
    identifiers = set(re.findall(r"[a-z][a-z0-9_]*", text))
    functions = {
        "sqrt": sp.sqrt,
        "sin": sp.sin,
        "cos": sp.cos,
        "tan": sp.tan,
        "asin": sp.asin,
        "acos": sp.acos,
        "atan": sp.atan,
        "log": sp.log,
        "exp": sp.exp,
        "abs": sp.Abs,
    }
    constants = {"pi": sp.pi, "e": sp.E, "infinity": sp.oo, "oo": sp.oo}
    for identifier in identifiers:
        if identifier in functions or identifier in constants:
            continue
        if re.search(rf"\b{re.escape(identifier)}\s*\(", text):
            return None
    local_dict: dict[str, Any] = {**functions, **constants}
    for identifier in identifiers:
        if identifier not in local_dict:
            local_dict[identifier] = sp.Symbol(identifier)
    try:
        transformations = standard_transformations + (implicit_multiplication_application,)
        expression = parse_expr(
            text,
            local_dict=local_dict,
            transformations=transformations,
            evaluate=True,
        )
        return expression if isinstance(expression, sp.Basic) else None
    except (AttributeError, IndexError, NameError, TypeError, SyntaxError, ValueError, sp.SympifyError):
        # IndexError: sympy's implicit-multiplication pass on some collapsed sentences.
        return None


def _interval_parts(text: str) -> tuple[str, str, bool, bool] | None:
    match = re.fullmatch(r"([([])(.+),(.+)([])])", text)
    if not match:
        return None
    return match.group(2), match.group(3), match.group(1) == "[", match.group(4) == "]"


def _inequality_parts(text: str) -> tuple[str, str, bool] | None:
    match = re.fullmatch(r"([a-z][a-z0-9_]*)\s*(>|>=|<|<=)(.+)", text)
    if not match:
        return None
    return match.group(1), match.group(3), ">=" in match.group(2) or "<=" in match.group(2)


def _same_expression(left: str, right: str) -> bool | None:
    left_expr = _sympy_expression(left)
    right_expr = _sympy_expression(right)
    if left_expr is None or right_expr is None:
        return None
    if left_expr.free_symbols != right_expr.free_symbols:
        return None
    try:
        return bool(sp.simplify(left_expr - right_expr) == 0)
    except (TypeError, ValueError, NotImplementedError):
        return None


def compare_answer_detailed(expected: str, candidate: str | None) -> dict[str, Any]:
    """Compare answers and return an auditable deterministic decision."""
    if candidate is None or not str(candidate).strip():
        return {
            "answer_status": "missing",
            "verification_method": "none",
            "verification_reason": "no_extractable_answer",
            "normalized_expected": normalize_answer(expected),
            "normalized_candidate": None,
            "canonical_candidate": None,
        }

    expected_normalized = normalize_answer(expected)
    candidate_normalized = normalize_answer(candidate)
    result_base = {
        "normalized_expected": expected_normalized,
        "normalized_candidate": candidate_normalized,
        "canonical_candidate": None,
    }

    if expected_normalized == candidate_normalized:
        return {**result_base, "answer_status": "correct", "verification_method": "normalized_exact"}

    if expected_normalized in {"yes", "no"}:
        candidate_boolean = _leading_boolean(candidate_normalized)
        if candidate_boolean is not None:
            status = "correct" if candidate_boolean == expected_normalized else "incorrect"
            return {
                **result_base,
                "answer_status": status,
                "verification_method": "leading_boolean",
                "verification_reason": None if status == "correct" else "conflicting_boolean",
            }

    if expected_normalized in {"a", "b", "c", "d"}:
        candidate_choice = _leading_choice(candidate_normalized)
        if candidate_choice is not None:
            status = "correct" if candidate_choice == expected_normalized else "incorrect"
            return {
                **result_base,
                "answer_status": status,
                "verification_method": "leading_choice",
                "verification_reason": None if status == "correct" else "conflicting_choice",
            }

    if _safe_text_claim(expected_normalized, candidate_normalized):
        return {**result_base, "answer_status": "correct", "verification_method": "safe_text_claim"}

    variants = _candidate_variants(candidate_normalized)
    expected_numeric = _numeric_value(expected_normalized)
    candidate_numerics = [_numeric_value(variant) for variant in variants]
    if expected_numeric is not None and any(value is not None for value in candidate_numerics):
        status = "correct" if any(value == expected_numeric for value in candidate_numerics) else "incorrect"
        return {
            **result_base,
            "answer_status": status,
            "verification_method": "rational_arithmetic",
            "verification_reason": None if status == "correct" else "unequal_numeric_values",
        }

    residue = _congruence_residue(candidate_normalized)
    if expected_numeric is not None and residue is not None:
        residue_numeric = _numeric_value(residue)
        if residue_numeric is not None:
            status = "correct" if residue_numeric == expected_numeric else "incorrect"
            return {
                **result_base,
                "answer_status": status,
                "verification_method": "congruence_residue",
                "verification_reason": None if status == "correct" else "unequal_congruence_residue",
            }

    expected_interval = _interval_parts(expected_normalized)
    candidate_inequality = _inequality_parts(candidate_normalized)
    if expected_interval and candidate_inequality:
        lower, upper, lower_closed, upper_closed = expected_interval
        variable, bound, bound_closed = candidate_inequality
        lower_match = _same_expression(lower, bound)
        if upper == "infinity":
            if lower_match is True and lower_closed == bound_closed:
                return {**result_base, "answer_status": "correct", "verification_method": "interval_inequality"}
            if lower_match is False:
                return {
                    **result_base,
                    "answer_status": "incorrect",
                    "verification_method": "interval_inequality",
                    "verification_reason": "unequal_interval_boundary",
                }

    for variant in variants:
        symbolic_match = _same_expression(expected_normalized, variant)
        if symbolic_match is True:
            return {
                **result_base,
                "answer_status": "correct",
                "verification_method": "sympy_symbolic_equivalence",
                "canonical_candidate": variant,
            }
        if symbolic_match is False:
            return {
                **result_base,
                "answer_status": "incorrect",
                "verification_method": "sympy_symbolic_non_equivalence",
                "verification_reason": "non_equal_supported_expressions",
                "canonical_candidate": variant,
            }

    reason = "unsupported_symbolic_or_semantic_form"
    if any(any(character.isalpha() for character in variant) for variant in variants):
        reason = "unsupported_symbolic_or_explanatory_text"
    return {
        **result_base,
        "answer_status": "unverified",
        "verification_method": "no_safe_equivalence_rule",
        "verification_reason": reason,
    }


def compare_answers(expected: str, candidate: str | None) -> str:
    """Compatibility wrapper returning only the four supported statuses."""
    return compare_answer_detailed(expected, candidate)["answer_status"]


def usage_cost(usage: Any) -> dict[str, Any]:
    usage = usage if isinstance(usage, dict) else {}
    prompt_tokens = usage.get("prompt_tokens")
    completion_tokens = usage.get("completion_tokens")
    prompt_tokens = int(prompt_tokens) if isinstance(prompt_tokens, (int, float)) else None
    completion_tokens = int(completion_tokens) if isinstance(completion_tokens, (int, float)) else None
    calculated = None
    if prompt_tokens is not None or completion_tokens is not None:
        calculated = (
            (prompt_tokens or 0) * INPUT_PRICE_PER_MILLION
            + (completion_tokens or 0) * OUTPUT_PRICE_PER_MILLION
        ) / 1_000_000
    provider = usage.get("estimated_cost")
    provider = float(provider) if isinstance(provider, (int, float)) else None
    return {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": (prompt_tokens or 0) + (completion_tokens or 0)
        if prompt_tokens is not None or completion_tokens is not None
        else None,
        "calculated_cost_usd": calculated,
        "provider_estimated_cost_usd": provider,
    }


def verify_record(record: dict[str, Any]) -> dict[str, Any]:
    candidate, method = extract_final_answer(str(record.get("solve_solution", "")))
    result = compare_answer_detailed(str(record.get("final_answer", "")), candidate)
    cost = usage_cost(record.get("solve_usage"))
    return {
        **result,
        "explain_eligible": result["answer_status"] == "correct",
        "extracted_final_answer": candidate,
        "final_answer_extraction": method,
        "verification_cost": cost,
    }


def dump_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)
