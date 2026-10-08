"""Deterministic final-answer extraction, comparison, and cost accounting."""

from __future__ import annotations

import json
import logging
import multiprocessing
import os
import re
import signal
import threading
from concurrent.futures import ProcessPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeout
from concurrent.futures.process import BrokenProcessPool
from fractions import Fraction
from typing import Any

import sympy as sp
from tokenize import TokenError
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


def _replace_roots(text: str) -> str:
    """``\\sqrt[n]{x}`` -> ``(x)^(1/(n))``; plain ``\\sqrt{x}`` is left for the sympy ``sqrt``."""
    pattern = re.compile(r"\\sqrt\s*\[([^\[\]]+)\]\s*\{")
    while True:
        match = pattern.search(text)
        if not match:
            return text
        radicand = _balanced_brace(text, match.end() - 1)
        if radicand is None:
            return text
        text = text[: match.start()] + f"({radicand[0]})^(1/({match.group(1)}))" + text[radicand[1] :]


def normalize_answer(value: str) -> str:
    """Normalize harmless formatting without claiming symbolic equivalence."""
    text = str(value).strip().strip("`")
    text = re.sub(r"(?:\\\\|\\)+\s*$", "", text).strip()  # a stray trailing "\\" or "\"
    text = text.replace("$$", "")
    text = re.sub(r"\\\(|\\\)|\\\[|\\\]", "", text)
    text = text.replace("\\dfrac", "\\frac").replace("\\tfrac", "\\frac")
    text = _replace_fractions(text)
    text = _replace_roots(text)
    text = re.sub(r"\^\s*\{?\\circ\}?|°", "", text)  # degrees: 150^\circ == 150
    text = re.sub(r"\\(?:geqslant|geq|ge)(?![a-zA-Z])|≥", ">=", text)
    text = re.sub(r"\\(?:leqslant|leq|le)(?![a-zA-Z])|≤", "<=", text)
    text = re.sub(r"\\(?:neq|ne)(?![a-zA-Z])|≠", "!=", text)
    text = re.sub(r"\\bmod(?![a-zA-Z])", " mod ", text)
    # "\ln 2", "\cos 2": a function applied to one bare token keeps its argument once spaces go.
    text = re.sub(r"(?<![A-Za-z])\\?(ln|log|sin|cos|tan|exp)\s+([0-9]+(?:\.[0-9]+)?|[a-zA-Z])(?![a-zA-Z0-9])",
                  r"\\\1(\2)", text)  # with or without the backslash
    text = re.sub(r"\\ln(?![a-zA-Z])", r"\\log", text)
    text = re.sub(r"\|([^|]+)\|", r"abs(\1)", text)  # |x| -> abs(x), unnested only
    text = re.sub(r"^\s*\+\s*(?=\\infty|∞|infinity)", "", text)  # "+\infty" == "\infty"
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
    if text in {"infinite", "+infinity", "positiveinfinity"}:
        text = "infinity"
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
    # A plain "=" only: "a!=3" or "n>=28" must not turn into "3" / "28".
    plain = re.findall(r"(?<![!<>=])=(?!=)", candidate_normalized)
    if len(plain) == 1 and not re.search(r"!=|<=|>=", candidate_normalized):
        variants.append(re.split(r"(?<![!<>=])=(?!=)", candidate_normalized)[1].strip(". ,;:"))
    return list(dict.fromkeys(variants))


def _is_simple_text(text: str) -> bool:
    return bool(re.fullmatch(r"[a-z][a-z0-9 _-]*", text))


def _leading_boolean(candidate: str) -> str | None:
    """"yes"/"no", or "true"/"false" (the statement holds / does not), at the start of the answer."""
    match = re.match(r"^(?:[(:\[]\s*)?(yes|no|true|false)\b", candidate)
    if not match:
        return None
    return {"true": "yes", "false": "no"}.get(match.group(1), match.group(1))


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
    except (AttributeError, IndexError, NameError, TypeError, SyntaxError, ValueError, sp.SympifyError, TokenError):
        # IndexError: sympy's implicit-multiplication pass on some collapsed sentences.
        # TokenError: Python's tokenizer on text such as "2nd" (invalid decimal literal).
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


def _compare_rules(expected: str, candidate: str | None) -> dict[str, Any]:
    """The rule layer: normalised exact match, booleans, choices, exact arithmetic, sympy."""
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

    expected_boolean = _leading_boolean(expected_normalized) if expected_normalized in {"yes", "no", "true", "false"} else None
    if expected_boolean is not None:
        candidate_boolean = _leading_boolean(candidate_normalized)
        if candidate_boolean is not None:
            status = "correct" if candidate_boolean == expected_boolean else "incorrect"
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


# --- Layers on top of the rules (verifier v3) -----------------------------------------------------------
#
# Every layer can only turn a non-correct decision into "correct" on evidence that cannot be gamed by
# hedging: a cleaned answer must not drop words such as "or"/"not", numeric closeness needs the gold's
# precision, and math-verify only sees answers that are pure mathematics (no prose, where it would pick
# any number out of "It does not converge to 0").

HEDGE_WORDS = re.compile(
    r"\b(?:or|either|maybe|possibly|perhaps|probably|otherwise|unless|not|except|alternatively|also|"
    r"approximately|approx|roughly|about|guess)\b",
    re.I,
)
_QUALIFIER = re.compile(
    r"(?:\\(?:quad|qquad|,|;|:)|,|\s)\s*(?:\\text\s*\{\s*|\(\s*(?:\\text\s*\{\s*)?)"
    r"(?:for|where|when|whenever|if|with|i\.e\.|since|as|in|because|so|which|that|is|are|the)\b.*$",
    re.S,
)
_TRAILING_TEXT = re.compile(r"\s*\\text\s*\{[^{}]*\}\s*[.]?\s*$")
_VARIABLE = r"(?:[A-Za-z](?:_\{?[A-Za-z0-9]+\}?)?|\\[A-Za-z]+(?:_\{?[A-Za-z0-9]+\}?)?)"
_ASSIGN = re.compile(rf"^\s*(?:{_VARIABLE}|\(\s*{_VARIABLE}(?:\s*,\s*{_VARIABLE})+\s*\))\s*(?:=|\\in)\s*(.+)$", re.S)
_ASSIGN_LIST = re.compile(rf"^\s*{_VARIABLE}\s*=\s*([^,=]+?)(?:\s*,\s*{_VARIABLE}\s*=\s*([^,=]+?))+\s*$", re.S)
_MATH_WORDS = {
    "sin", "cos", "tan", "cot", "sec", "csc", "arcsin", "arccos", "arctan", "sinh", "cosh", "tanh", "log",
    "ln", "exp", "sqrt", "lim", "max", "min", "sup", "inf", "mod", "bmod", "pmod", "gcd", "lcm", "det",
    "frac", "dfrac", "tfrac", "cdot", "times", "infty", "pi", "left", "right", "mathbb", "mathcal",
    "mathrm", "operatorname", "binom", "choose", "sum", "prod", "int", "cup", "cap", "emptyset",
    "varnothing", "leq", "geq", "neq", "le", "ge", "ne", "pm", "mp", "alpha", "beta", "gamma", "delta",
    "epsilon", "varepsilon", "theta", "lambda", "mu", "sigma", "omega", "phi", "varphi", "psi", "rho",
    "tau", "zeta", "eta", "kappa", "nu", "xi", "chi", "circ", "displaystyle", "boxed", "mathbf", "vec",
    "overline", "hat", "dots", "ldots", "cdots", "quad", "qquad", "begin", "end", "pmatrix", "bmatrix",
    "matrix", "Gamma", "Delta", "Theta", "Lambda", "Sigma", "Omega", "Phi", "Psi", "to", "rightarrow",
}


def _is_clean_math(text: str) -> bool:
    """Pure mathematics: no \\text, no English words, short. math-verify is only trusted on these."""
    text = str(text or "")
    if not text.strip() or len(text) > 200 or "\\text" in text or "\n" in text.strip():
        return False
    if re.search(r"\\(?:aleph|beth|mathfrak)", text):  # cardinals: math-verify equates 2^{2^{a}} with 2^{a}
        return False
    for word in re.findall(r"\\?[A-Za-z]{2,}", text):
        if word.lstrip("\\") not in _MATH_WORDS:
            return False
    return True


def _top_level_commas(text: str) -> int:
    """Commas outside (), [], {}: "n = 0, 2" lists two values; "(1, 2)" is one tuple."""
    depth, count = 0, 0
    for character in re.sub(r"\\[{}]", "", str(text)):
        if character in "([{":
            depth += 1
        elif character in ")]}":
            depth = max(0, depth - 1)
        elif character == "," and depth == 0:
            count += 1
    return count


def _several_values(form: str, gold: str) -> bool:
    """The answer lists more values than the key: never accepted by the lenient layers.

    Also a key with no comma at all against a tuple-like answer ("(2)" vs "(4, 2+2\\sqrt{-5})"), except an
    interval reaching infinity ("(-\\infty, \\infty)" for \\mathbb{R}).
    """
    if _top_level_commas(form) > _top_level_commas(gold):
        return True
    commas = lambda t: len(re.findall(r"(?<!\\!),(?!\d{3}\b)", re.sub(r"\{,\}", "", str(t))))
    if commas(gold) == 0 and commas(form) > 0:
        return not re.fullmatch(r"\s*\$?\s*(?:\\left)?\s*[(\[].*(?:\\infty|∞).*[)\]]\s*\$?\s*", str(form), re.S)
    return False


def _cleaned_variants(candidate: str) -> list[tuple[str, str]]:
    """Answer forms the model meant, with what was removed. Hedged removals are refused."""
    raw = re.sub(r"(?:\\\\|\\)+\s*$", "", str(candidate)).strip().strip("$").strip()
    out: list[tuple[str, str]] = []

    def add(value: str, removed: str, how: str) -> None:
        value = value.strip().rstrip(".,;:").strip()
        if value and value != raw and not HEDGE_WORDS.search(re.sub(r"\\[A-Za-z]+", " ", removed)):
            out.append((value, how))

    # "2^k \text{ for } k \ge 1", "13^m \quad (\text{for some } m)", "n! \text{ is larger.}"
    # What is left must be pure mathematics, so a sentence is never cut down to a fragment that matches.
    match = _QUALIFIER.search(raw)
    if match and match.start() > 0 and _is_clean_math(raw[: match.start()]):
        add(raw[: match.start()], raw[match.start() :], "qualifier_removed")
    match = _TRAILING_TEXT.search(raw)
    if match and match.start() > 0 and _is_clean_math(raw[: match.start()]):
        add(raw[: match.start()], match.group(0), "trailing_text_removed")
    stems = [raw] + [value for value, _ in out]
    for stem in stems:
        # "n = 2^k", "(p, q) = (2, 2)", "a \in [-4, 4]": the value after a variable.
        match = _ASSIGN.match(stem)
        if match and "=" not in match.group(1):
            add(match.group(1), "", "assignment_value")
        # "x=0, y=0, z=0" -> "(0, 0, 0)"
        if _ASSIGN_LIST.match(stem):
            values = [part.split("=", 1)[1].strip() for part in stem.split(",")]
            add("(" + ", ".join(values) + ")", "", "assignment_tuple")
    return list(dict.fromkeys(out))


def _gold_variants(expected: str) -> list[str]:
    """The key itself, and its value when written as "(a, b) = (1, 1)" (a constant after variables)."""
    out = [expected]
    match = _ASSIGN.match(str(expected))
    if match and not re.search(r"[A-Za-z]", re.sub(r"\\(?:frac|dfrac|sqrt|pi|infty)", "", match.group(1))):
        out.append(match.group(1).strip())
    return out


def _equation_chain(candidate: str) -> list[str]:
    """"\\mathbb{F}_{2^6} = \\mathbb{F}_{64}": the sides of an equation chain without prose."""
    raw = str(candidate).strip().strip("$")
    if not _is_clean_math(raw) or raw.count("=") < 1 or re.search(r"[<>]|\\[lgn]e", raw) or _top_level_commas(raw):
        return []
    sides = [side.strip() for side in raw.split("=")]
    return sides if all(sides) else []


def _decimal_places(text: str) -> int | None:
    match = re.fullmatch(r"-?\d+\.(\d+)", text)
    return len(match.group(1)) if match else None


def _numeric_close(expected_normalized: str, candidate_normalized: str) -> bool | None:
    """Equal values written differently: e^{4.5} vs e^{9/2}, \\pi vs 3.141592653, 0.832293673 vs 2|cos 2|.

    A decimal key fixes the precision: the answer must agree to the key's last place and give at least
    all but one of its decimals. Otherwise the two values must agree to 1e-9 (relative), and a decimal
    answer needs 6 significant digits.
    """
    left = _sympy_expression(expected_normalized)
    right = _sympy_expression(candidate_normalized)
    if left is None or right is None or left.free_symbols or right.free_symbols:
        return None
    if any(e.has(sp.oo, -sp.oo, sp.zoo, sp.nan) for e in (left, right)):
        return None  # infinities are compared exactly by the rules, never numerically (oo - 1 == oo)
    if not left.has(sp.Float) and not right.has(sp.Float):
        # Exact on both sides: 10^{101} + 1 and 100 * 10^{99} differ by 1, which no relative tolerance sees.
        if left.is_Rational and right.is_Rational:
            return left == right
        try:
            difference = sp.N(left - right, 60)
            return bool(difference.is_number and abs(complex(difference)) <= 1e-40 * max(1.0, abs(complex(sp.N(left, 60)))))
        except (TypeError, ValueError, OverflowError):
            return None
    try:
        a = complex(sp.N(left, 30))
        b = complex(sp.N(right, 30))
    except (TypeError, ValueError, OverflowError):
        return None
    if any(map(lambda z: z != z or abs(z) == float("inf"), (a, b))):
        return None
    gold_places = _decimal_places(expected_normalized)
    cand_places = _decimal_places(candidate_normalized)
    if gold_places is not None and gold_places >= 4:  # a rounded numeric key; "0.5" stays exact
        if cand_places is not None and cand_places < gold_places - 1:
            return False
        places = gold_places if cand_places is None else min(gold_places, cand_places)
        return abs(a - b) <= 0.5 * 10 ** (-places) * (1 + 1e-9)
    if cand_places is not None and len(re.sub(r"\D", "", candidate_normalized).lstrip("0")) < 6:
        return False
    return abs(a - b) <= 1e-9 * max(1.0, abs(a))


def _math_verify_equal(expected: str, candidate: str) -> bool | None:
    try:
        from math_verify import ExprExtractionConfig, LatexExtractionConfig, parse, verify
    except ImportError as error:  # a hard dependency: fail loudly rather than silently weaken the checker
        raise RuntimeError("math-verify is required by the SOLVE checker (uv sync)") from error
    # Its own timeouts are off (they would cancel ours); it warns about that on every call.
    logging.getLogger("math_verify").setLevel(logging.ERROR)
    config = [LatexExtractionConfig(boxed_match_priority=0), ExprExtractionConfig()]

    def wrap(text: str) -> str:
        text = str(text).strip()
        return text if "$" in text else f"${text}$"

    gold = parse(wrap(expected), extraction_config=config, parsing_timeout=None)
    answer = parse(wrap(candidate), extraction_config=config, parsing_timeout=None)
    if not gold or not answer:
        return None
    return bool(verify(gold, answer, timeout_seconds=None))


def _compare_full(expected: str, candidate: str | None) -> dict[str, Any]:
    base = _compare_rules(expected, candidate)
    if base["answer_status"] in ("correct", "missing"):
        return base
    candidate = str(candidate)

    def upgraded(method: str, used: str) -> dict[str, Any]:
        return {**base, "answer_status": "correct", "verification_method": method,
                "verification_reason": None, "canonical_candidate": used}

    golds = _gold_variants(expected)
    # 1. The rules on cleaned forms of the answer (and of a "(a, b) = (1, 1)" key).
    forms = [(candidate, "as_written")] + _cleaned_variants(candidate)
    for gold in golds:
        for form, how in forms:
            if (gold, form) == (expected, candidate) or (how != "as_written" and _several_values(form, gold)):
                continue
            result = _compare_rules(gold, form)
            if result["answer_status"] == "correct":
                return upgraded(f"{how}+{result['verification_method']}", form)
    # 2. An equation chain "A = B = value": the last side is the answer; the first side counts only when
    #    every other side is a plain number ("2^6 = 64"), never "\tau(n) = <some formula>".
    sides = _equation_chain(candidate)
    if len(sides) >= 2:
        for gold in golds:
            verdicts = [_compare_rules(gold, side)["answer_status"] for side in sides]
            if "incorrect" in verdicts:
                continue
            numbers = all(_numeric_value(normalize_answer(side)) is not None for side in sides[1:])
            if verdicts[-1] == "correct" or (verdicts[0] == "correct" and numbers):
                return upgraded("equation_chain", candidate)
    # 3. Numeric closeness.
    for gold in golds:
        for form, how in forms:
            if _numeric_close(normalize_answer(gold), normalize_answer(form)):
                return upgraded(f"{how}+numeric_close", form)
    # 4. DeepMath's official checker pair (their reward accepts if either says equal): OpenMathInstruct's
    #    math_equal, then math-verify. math_equal strips \text{...}, so it never sees a hedged answer
    #    ("3 \text{ or } 5" would become "3"); its percentage rule (50 == 0.5) is off.
    if not HEDGE_WORDS.search(re.sub(r"\\[A-Za-z]+", " ", candidate)):
        from .third_party.omi_math_equal import math_equal

        for gold in golds:
            for form, how in forms:
                if not _is_clean_math(form) or _several_values(form, gold):
                    continue
                if normalize_answer(form) in {"true", "false", "yes", "no"}:  # Python: True == 1
                    continue
                try:
                    # tolerance 1e-9, not DeepMath's 1e-4: that accepts 88327 for 88329 (relative 2e-5).
                    same = math_equal(form, gold, include_percentage=False, tolerance=1e-9, check_antlr_version=False)
                except _CheckTimeout:
                    raise
                except Exception:
                    same = False
                if same:
                    return upgraded(f"{how}+omi_math_equal", form)
    # 5. math-verify, on pure mathematics only, and only where the rules could not decide.
    if base["answer_status"] == "unverified":
        for gold in golds:
            for form, how in forms:
                if (_is_clean_math(gold) and _is_clean_math(form) and not _several_values(form, gold)
                        and _math_verify_equal(gold, form)):
                    return upgraded(f"{how}+math_verify", form)
    return base


# --- Time limit ---------------------------------------------------------------------------------------
#
# sympy can run for minutes on adversarial input, and rewards are scored from trainer threads, where a
# SIGALRM cannot be used. The main thread uses an alarm directly; other threads hand the check to a small
# process pool whose workers run it in their own main thread under the same alarm.

CHECK_SECONDS = 10
_POOL: Any = None
_POOL_LOCK = threading.Lock()


class _CheckTimeout(Exception):
    pass


def _timed_out(expected: str, candidate: str | None, why: str) -> dict[str, Any]:
    return {
        "answer_status": "unverified",
        "verification_method": "timeout",
        "verification_reason": why,
        "normalized_expected": normalize_answer(expected),
        "normalized_candidate": None if candidate is None else normalize_answer(candidate),
        "canonical_candidate": None,
    }


def _compare_with_alarm(expected: str, candidate: str | None) -> dict[str, Any]:
    def handler(signum: int, frame: Any) -> None:
        raise _CheckTimeout

    previous = signal.signal(signal.SIGALRM, handler)
    signal.setitimer(signal.ITIMER_REAL, CHECK_SECONDS)
    try:
        return _compare_full(expected, candidate)
    except _CheckTimeout:
        return _timed_out(expected, candidate, f"check_exceeded_{CHECK_SECONDS}s")
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


def _pool() -> Any:
    global _POOL
    with _POOL_LOCK:
        if _POOL is None:
            _POOL = ProcessPoolExecutor(max_workers=min(8, os.cpu_count() or 1),
                                        mp_context=multiprocessing.get_context("spawn"))
        return _POOL


def _reset_pool() -> None:
    global _POOL
    with _POOL_LOCK:
        if _POOL is not None:
            _POOL.shutdown(wait=False, cancel_futures=True)
        _POOL = None


def compare_answer_detailed(expected: str, candidate: str | None) -> dict[str, Any]:
    """Compare answers and return an auditable deterministic decision (time-limited, thread-safe)."""
    if threading.current_thread() is threading.main_thread():
        return _compare_with_alarm(expected, candidate)
    future = _pool().submit(_compare_with_alarm, expected, candidate)
    try:
        return future.result(timeout=6 * CHECK_SECONDS)
    except FuturesTimeout:
        return _timed_out(expected, candidate, "worker_unresponsive")
    except BrokenProcessPool:
        _reset_pool()
        return _timed_out(expected, candidate, "worker_crashed")


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
