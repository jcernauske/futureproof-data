"""Content checks for prose fields.

Replaces score-field scoring for surfaces where production server-overwrites
Gemma's numeric output. Tests what Gemma actually controls: prose presence,
directional content, and length bounds.

Two scorers here:

  ``score_directional_content`` — pass if the prose field contains at least
  one substring from ``expected_directional`` (case-insensitive). Use for
  testing whether a headline directionally matches the data: a low-wage case
  headline should mention "low", "limited", "modest", etc.

  ``score_length_range`` — pass if a prose field is between ``min_chars`` and
  ``max_chars`` (inclusive). Catches empty headlines, truncated responses,
  and runaway generation. Cheap structural test.
"""

from __future__ import annotations

from typing import Any

from eval.scorers.base import GoldenCase, ScoreResult
from eval.scorers.exact_match import _get_nested


def score_directional_content(
    *,
    case: GoldenCase,
    actual: Any,
    surface: str,
    field: str,
    expected_directional: list[str],
    require_all: bool = False,
) -> ScoreResult:
    """Pass if the field's string value contains at least one of
    ``expected_directional`` (case-insensitive).

    ``require_all=True`` flips the semantics to "contains every substring".
    Use for headlines where multiple anchors should appear (e.g. both
    "growing" and the percent figure).
    """
    value = _get_nested(actual, field)
    if not isinstance(value, str) or not value:
        return ScoreResult(
            case_id=case.case_id,
            surface=surface,
            metric="content_check",
            score=0.0,
            passed=False,
            details={
                "field": field,
                "expected_any": expected_directional,
                "actual": value,
                "reason": "field missing or empty",
            },
        )

    haystack = value.lower()
    hits = [needle for needle in expected_directional if needle.lower() in haystack]
    if require_all:
        passed = len(hits) == len(expected_directional)
    else:
        passed = len(hits) > 0

    return ScoreResult(
        case_id=case.case_id,
        surface=surface,
        metric="content_check",
        score=1.0 if passed else 0.0,
        passed=passed,
        details={
            "field": field,
            "expected_any" if not require_all else "expected_all": expected_directional,
            "hits": hits,
            "actual_excerpt": value[:140],
        },
    )


def score_length_range(
    *,
    case: GoldenCase,
    actual: Any,
    surface: str,
    field: str,
    min_chars: int = 1,
    max_chars: int = 1000,
) -> ScoreResult:
    """Pass if the field's string value length is in ``[min_chars, max_chars]``."""
    value = _get_nested(actual, field)
    if not isinstance(value, str):
        return ScoreResult(
            case_id=case.case_id,
            surface=surface,
            metric="length_range",
            score=0.0,
            passed=False,
            details={"field": field, "actual_type": type(value).__name__},
        )

    length = len(value)
    passed = min_chars <= length <= max_chars
    return ScoreResult(
        case_id=case.case_id,
        surface=surface,
        metric="length_range",
        score=1.0 if passed else 0.0,
        passed=passed,
        details={
            "field": field,
            "length": length,
            "min": min_chars,
            "max": max_chars,
        },
    )
