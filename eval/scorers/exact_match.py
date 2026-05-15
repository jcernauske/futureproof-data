"""Exact-match field scorer. Used for CIP codes, SOC codes, tier
assignments — anything where 'close' is wrong."""

from __future__ import annotations

from typing import Any

from eval.scorers.base import GoldenCase, ScoreResult


def _get_nested(obj: Any, dotted_path: str) -> Any:
    """Look up a dotted path in nested dicts / lists / objects.

    Integer segments index into lists (``alternatives.0.cipcode``); string
    segments dispatch to dict.get or getattr. Returns None on any missing
    segment.
    """
    current: Any = obj
    for segment in dotted_path.split("."):
        if current is None:
            return None
        if segment.isdigit() and isinstance(current, list):
            idx = int(segment)
            current = current[idx] if 0 <= idx < len(current) else None
        elif isinstance(current, dict):
            current = current.get(segment)
        else:
            current = getattr(current, segment, None)
    return current


def score_exact_match(
    *,
    case: GoldenCase,
    actual: Any,
    surface: str,
    field: str,
    expected_value: Any,
) -> ScoreResult:
    """Return 1.0 if actual[field] == expected_value, else 0.0.

    ``field`` accepts dotted paths for nested lookup (e.g. ``alternatives.0.cipcode``).
    """
    actual_value = _get_nested(actual, field)
    passed = actual_value == expected_value
    return ScoreResult(
        case_id=case.case_id,
        surface=surface,
        metric="field_accuracy",
        score=1.0 if passed else 0.0,
        passed=passed,
        details={
            "field": field,
            "expected": expected_value,
            "actual": actual_value,
        },
    )
