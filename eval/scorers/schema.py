"""Schema-validity scorer: does the production output parse against a
declared Pydantic model? Pass/fail with the validation error attached."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ValidationError

from eval.scorers.base import GoldenCase, ScoreResult


def score_schema_validity(
    *,
    case: GoldenCase,
    actual: Any,
    surface: str,
    schema: type[BaseModel],
) -> ScoreResult:
    """Validate ``actual`` against ``schema``. ``actual`` may be a dict or
    a model instance; in either case we round-trip through schema validation
    to ensure all required fields are present and well-typed.
    """
    if actual is None:
        return ScoreResult(
            case_id=case.case_id,
            surface=surface,
            metric="schema_valid",
            score=0.0,
            passed=False,
            error="actual is None",
        )

    try:
        if isinstance(actual, BaseModel):
            payload = actual.model_dump()
        else:
            payload = actual
        schema.model_validate(payload)
    except ValidationError as exc:
        return ScoreResult(
            case_id=case.case_id,
            surface=surface,
            metric="schema_valid",
            score=0.0,
            passed=False,
            error=str(exc),
        )

    return ScoreResult(
        case_id=case.case_id,
        surface=surface,
        metric="schema_valid",
        score=1.0,
        passed=True,
    )
