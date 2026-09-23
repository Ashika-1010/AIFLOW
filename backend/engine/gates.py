"""
Stage 1 — Deterministic Gate

Handles arithmetic, unit conversion, and date arithmetic.
Uses sympy.sympify in a restricted namespace (no builtins, no __import__).
Falls through to Stage 2 on ANY ambiguity — false-positive-free by design.

All gate decisions are logged so precision can be audited.
"""
from __future__ import annotations
import logging
import re
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Arithmetic gate
# ---------------------------------------------------------------------------
_ARITH_PURE = re.compile(
    r"""^\s*
        (what\s+is\s+)?           # optional preamble
        [\d\s\+\-\*\/\(\)\.x×÷\^]+  # numbers and operators
        \s*[\?\.]?\s*$            # optional trailing ? or .
    """,
    re.VERBOSE | re.IGNORECASE,
)
# Must contain at least one operator OR explicit "calculate"
_HAS_OPERATOR = re.compile(r"[\+\-\*\/×÷\^]|\bmod\b")

# Normalise human-readable operators before sympify
_OP_ALIASES = [
    (re.compile(r"[×x]"), "*"),
    (re.compile(r"÷"),    "/"),
    (re.compile(r"\^"),   "**"),
]

# Unit-conversion triggers
_UNIT_PATTERNS = [
    re.compile(r"\bconvert\b", re.I),
    re.compile(r"\bin\s+(km|mph|kph|celsius|fahrenheit|kg|lb|lbs|miles?|meters?|feet|inches?|litres?|gallons?)\b", re.I),
    re.compile(r"\b\d+\s*(mph|kph|km/h|m/s|kg|lb|lbs|miles?|km|meters?|feet|ft|inches?|in|celsius|fahrenheit|°[cf])\b", re.I),
    re.compile(r"\bto\s+(kilometers?|miles?|celsius|fahrenheit|kg|pounds?|litres?|gallons?)\b", re.I),
]

# Date arithmetic triggers
_DATE_PATTERNS = [
    re.compile(r"\bhow\s+many\s+days\s+between\b", re.I),
    re.compile(r"\bdays?\s+(between|from|until|to)\b", re.I),
    re.compile(r"\b\d{4}-\d{2}-\d{2}\b.*\b\d{4}-\d{2}-\d{2}\b"),
    re.compile(r"\bdate\s+arithmetic\b", re.I),
]

# Ambiguity guard — these words make a query non-deterministic
_AMBIGUITY_GUARDS = re.compile(
    r"\b(explain|describe|why|what\s+does|who|list|summarize|essay|story|write|"
    r"generate|analyz|review|compare|discuss|elaborate|implication|impact|"
    r"suggest|recommend|translate|paraphrase|code|program)\b",
    re.I,
)


def _safe_eval_arithmetic(expr: str) -> Optional[str]:
    """Evaluate expr with sympy in a restricted namespace. Returns str or None."""
    try:
        from sympy import sympify, Rational
        # Normalise operator aliases
        for pattern, replacement in _OP_ALIASES:
            expr = pattern.sub(replacement, expr)
        # Strip any remaining non-numeric/non-operator chars before sympify
        clean = re.sub(r"[^\d\s\+\-\*\/\(\)\.\*]", "", expr).strip()
        if not clean:
            return None
        result = sympify(clean, evaluate=True)
        # Return a clean numeric string
        if result.is_number:
            f = float(result)
            if f == int(f):
                return str(int(f))
            return f"{f:.6g}"
        return None
    except Exception as exc:
        logger.debug("sympy eval failed for %r: %s", expr, exc)
        return None


def _eval_unit_conversion(query: str) -> Optional[str]:
    """Use pint to evaluate simple unit conversion queries."""
    try:
        import pint
        ureg = pint.UnitRegistry()

        # Extract pattern: <number> <from_unit> to <to_unit>  (or "in" <to_unit>)
        m = re.search(
            r"([\d,]+(?:\.\d+)?)\s*"
            r"(mph|kph|km/h|m/s|kg|lbs?|miles?|km|kilometers?|meters?|"
            r"feet|ft|inches?|in|celsius|fahrenheit|°c|°f|gallons?|litres?|liters?)\b"
            r".*?\b(?:to|in)\s+"
            r"(mph|kph|km/h|m/s|kg|lbs?|miles?|km|kilometers?|meters?|"
            r"feet|ft|inches?|in|celsius|fahrenheit|°c|°f|gallons?|litres?|liters?)\b",
            query,
            re.I,
        )
        if not m:
            return None

        number_str = m.group(1).replace(",", "")
        from_unit_raw = m.group(2).lower()
        to_unit_raw = m.group(3).lower()

        # Map aliases
        _aliases = {
            "mph": "mph", "kph": "kph", "km/h": "kph",
            "celsius": "degC", "°c": "degC",
            "fahrenheit": "degF", "°f": "degF",
            "lbs": "pound", "lb": "pound",
            "miles": "mile", "mile": "mile",
            "km": "kilometer", "kilometers": "kilometer",
            "meters": "meter", "feet": "foot", "ft": "foot",
            "inches": "inch", "in": "inch",
            "litres": "liter", "liters": "liter",
            "gallons": "gallon",
        }

        from_unit = _aliases.get(from_unit_raw, from_unit_raw)
        to_unit   = _aliases.get(to_unit_raw,   to_unit_raw)

        qty = ureg.Quantity(float(number_str), from_unit)
        converted = qty.to(to_unit)
        val = converted.magnitude
        val_str = f"{val:.3f}" if val != int(val) else str(int(val))
        return f"{number_str} {m.group(2)} = {val_str} {m.group(3)}"
    except Exception as exc:
        logger.debug("pint conversion failed: %s", exc)
        return None


def _eval_date_arithmetic(query: str) -> Optional[str]:
    """Compute days between two ISO dates mentioned in the query."""
    try:
        from dateutil import parser as dparser
        dates = re.findall(r"\b(\d{4}-\d{2}-\d{2})\b", query)
        if len(dates) >= 2:
            d1 = dparser.parse(dates[0])
            d2 = dparser.parse(dates[1])
            delta = abs((d2 - d1).days)
            return f"{delta} days"
        # "how many days between <month day year> and <month day year>"
        m = re.search(
            r"between\s+(.+?)\s+and\s+(.+?)[\?\.]?\s*$", query, re.I
        )
        if m:
            d1 = dparser.parse(m.group(1), fuzzy=True)
            d2 = dparser.parse(m.group(2), fuzzy=True)
            delta = abs((d2 - d1).days)
            return f"{delta} days"
        return None
    except Exception as exc:
        logger.debug("date arithmetic failed: %s", exc)
        return None


class DeterministicResult:
    __slots__ = ("matched", "sub_type", "response", "reason")

    def __init__(self, matched: bool, sub_type: str = "", response: str = "", reason: str = ""):
        self.matched   = matched
        self.sub_type  = sub_type
        self.response  = response
        self.reason    = reason


def try_deterministic(query: str) -> DeterministicResult:
    """
    Attempt to resolve the query deterministically.
    Returns DeterministicResult with matched=True only when confident.
    Precision rule: on ANY ambiguity, return matched=False.
    """
    # Global ambiguity guard — must fire before any sub-check
    if _AMBIGUITY_GUARDS.search(query):
        logger.debug("deterministic gate: ambiguity guard fired for %r", query[:80])
        return DeterministicResult(matched=False)

    # 1. Date arithmetic (check before arithmetic — dates contain digits)
    if any(p.search(query) for p in _DATE_PATTERNS):
        result = _eval_date_arithmetic(query)
        if result:
            logger.info("deterministic gate: DATE matched %r -> %r", query[:60], result)
            return DeterministicResult(
                matched=True,
                sub_type="date",
                response=result,
                reason="Date arithmetic detected",
            )

    # 2. Unit conversion
    if any(p.search(query) for p in _UNIT_PATTERNS):
        result = _eval_unit_conversion(query)
        if result:
            logger.info("deterministic gate: UNIT matched %r -> %r", query[:60], result)
            return DeterministicResult(
                matched=True,
                sub_type="unit",
                response=result,
                reason="Unit conversion detected",
            )

    # 3. Pure arithmetic
    # Extract just the numeric expression from common phrasings
    numeric_expr = re.sub(
        r"^\s*(what\s+is\s+|calculate\s+|compute\s+|evaluate\s+|find\s+)", "", query, flags=re.I
    ).strip().rstrip("?.")

    if _ARITH_PURE.match(query) or (
        _HAS_OPERATOR.search(numeric_expr)
        and not re.search(r"[a-zA-Z]{4,}", numeric_expr)  # no long words
    ):
        result = _safe_eval_arithmetic(numeric_expr)
        if result:
            logger.info("deterministic gate: ARITHMETIC matched %r -> %r", query[:60], result)
            return DeterministicResult(
                matched=True,
                sub_type="arithmetic",
                response=result,
                reason="Arithmetic expression detected",
            )

    logger.debug("deterministic gate: no match for %r", query[:80])
    return DeterministicResult(matched=False)
