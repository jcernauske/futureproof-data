"""Tolerant field scorers: numeric bands, set membership, fuzzy string."""

from __future__ import annotations

from difflib import SequenceMatcher
from typing import Any

from eval.scorers.base import GoldenCase, ScoreResult
from eval.scorers.exact_match import _get_nested


def score_tolerant_match(
    *,
    case: GoldenCase,
    actual: Any,
    surface: str,
    field: str,
    expected_value: Any,
    numeric_tolerance: float = 0.0,
    string_similarity_threshold: float = 1.0,
    accepted_set: set[Any] | None = None,
) -> ScoreResult:
    """Score with one of three tolerance modes (pick whichever is non-default).

    - ``numeric_tolerance``: pass if abs(actual - expected) <= tolerance.
    - ``string_similarity_threshold``: pass if SequenceMatcher ratio >= threshold.
    - ``accepted_set``: pass if actual ∈ accepted_set (use when multiple answers
      are correct, e.g., {"data_science", "data_analytics"}).
    """
    actual_value = _get_nested(actual, field)

    if accepted_set is not None:
        passed = actual_value in accepted_set
        details = {"field": field, "actual": actual_value, "accepted": list(accepted_set)}
    elif isinstance(expected_value, (int, float)) and isinstance(actual_value, (int, float)):
        passed = abs(float(actual_value) - float(expected_value)) <= numeric_tolerance
        details = {
            "field": field,
            "expected": expected_value,
            "actual": actual_value,
            "tolerance": numeric_tolerance,
        }
    elif isinstance(expected_value, str) and isinstance(actual_value, str):
        ratio = SequenceMatcher(None, expected_value.lower(), actual_value.lower()).ratio()
        passed = ratio >= string_similarity_threshold
        details = {
            "field": field,
            "expected": expected_value,
            "actual": actual_value,
            "similarity": round(ratio, 3),
            "threshold": string_similarity_threshold,
        }
    else:
        # Heterogeneous types — fall back to equality.
        passed = actual_value == expected_value
        details = {"field": field, "expected": expected_value, "actual": actual_value}

    return ScoreResult(
        case_id=case.case_id,
        surface=surface,
        metric="field_accuracy",
        score=1.0 if passed else 0.0,
        passed=passed,
        details=details,
    )
