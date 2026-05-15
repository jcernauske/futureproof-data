"""Core eval models. One GoldenCase = one labeled input. One ScoreResult =
one (case, metric) measurement."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class GoldenCase(BaseModel):
    """One labeled example for a surface."""

    case_id: str = Field(..., description="Stable identifier, e.g., 'intent_001'.")
    inputs: dict[str, Any] = Field(
        ...,
        description="Surface-specific input payload. The adapter knows how to "
        "destructure this into the production function call.",
    )
    expected: dict[str, Any] = Field(
        default_factory=dict,
        description="Surface-specific expected output. Shape depends on the "
        "scorer: schema-validity uses {schema: '...'}, exact-match uses "
        "{field: value}, rubric uses {rubric_notes: '...'}.",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Categorical labels. Standard tags: 'happy', 'edge', "
        "'ood' (out-of-distribution), 'adversarial'.",
    )
    notes: str | None = None


class ScoreResult(BaseModel):
    """One measurement of one case along one metric."""

    case_id: str
    surface: str
    metric: str = Field(
        ...,
        description="schema_valid | field_accuracy | tool_call | rubric | latency",
    )
    score: float = Field(
        ...,
        description="0.0–1.0 for accuracy/quality metrics; seconds for latency.",
    )
    passed: bool
    details: dict[str, Any] = Field(default_factory=dict)
    latency_ms: int | None = None
    tokens_input: int | None = None
    tokens_output: int | None = None
    error: str | None = None
