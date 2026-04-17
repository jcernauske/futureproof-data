"""Smoke tests for the Anthropic LEFT JOIN in ai_exposure_transformer.

Validates that:
  - The Gold schema gained the 4 new Anthropic columns.
  - blend_scores accepts an ``anthropic_rows`` kwarg.
  - When Anthropic data is supplied, each blended row gets the four
    new columns populated by LEFT JOIN on soc_code.
  - When Anthropic data is missing/omitted, the columns emit None
    and the existing blending behavior is unchanged.

@test-writer will expand these into full regression coverage; this
file only guarantees the schema evolution and JOIN logic land safely.
"""

from __future__ import annotations

import datetime

import pytest

from gold.ai_exposure_transformer import (
    _index_anthropic,
    blend_scores,
    get_gold_schema,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def promoted_at() -> datetime.datetime:
    return datetime.datetime(2026, 4, 16, 12, 0, 0, tzinfo=datetime.timezone.utc)


@pytest.fixture
def gemma_row() -> dict:
    return {
        "exposure_score": 7,
        "rationale": "Financial analysts rely on quantitative models...",
        "primary_title": "Financial Analysts",
        "task_breakdown_automatable": '["data aggregation"]',
        "task_breakdown_human": '["client advisory"]',
        "model_tag": "gemma4:26b-a4b",
        "error": None,
    }


@pytest.fixture
def karpathy_row() -> dict:
    return {
        "exposure_score": 8,
        "rationale": "Karpathy rationale for financial analysts",
        "occupation_title": "Financial Analysts",
        "category": "business-and-financial",
    }


@pytest.fixture
def anthropic_row() -> dict:
    return {
        "soc_code": "13-2051",
        "observed_exposure_pct": 3.7,
        "automation_pct": 45.0,
        "augmentation_pct": 50.0,
        "task_count": 5,
        "source_release": "release_2025_03_27",
        "soc_match": True,
    }


# ---------------------------------------------------------------------------
# Schema evolution
# ---------------------------------------------------------------------------


class TestSchemaEvolution:
    """The 4 new Anthropic columns are present in the Gold schema."""

    def test_schema_adds_anthropic_fields(self) -> None:
        names = {f.name for f in get_gold_schema().fields}
        for new_field in (
            "ai_adoption_share",
            "automation_pct",
            "anthropic_task_count",
            "anthropic_source_release",
        ):
            assert new_field in names, f"Missing field: {new_field}"

    def test_schema_preserves_v4_fields(self) -> None:
        """Regression: Gemma/Karpathy blending fields still present."""
        names = {f.name for f in get_gold_schema().fields}
        for preserved in (
            "record_id", "soc_code", "occupation_title", "exposure_score",
            "stat_res", "boss_ai_score", "rationale", "category",
            "task_breakdown_automatable", "task_breakdown_human",
            "scoring_model", "model_tag", "karpathy_score",
        ):
            assert preserved in names


# ---------------------------------------------------------------------------
# Index helper
# ---------------------------------------------------------------------------


class TestIndexAnthropic:
    def test_indexes_by_soc_code(self, anthropic_row) -> None:
        indexed = _index_anthropic([anthropic_row])
        assert "13-2051" in indexed

    def test_drops_null_soc(self) -> None:
        indexed = _index_anthropic([{"soc_code": None, "observed_exposure_pct": 1.0}])
        assert indexed == {}

    def test_drops_empty_soc(self) -> None:
        indexed = _index_anthropic([{"soc_code": "", "observed_exposure_pct": 1.0}])
        assert indexed == {}


# ---------------------------------------------------------------------------
# blend_scores LEFT JOIN behavior
# ---------------------------------------------------------------------------


class TestBlendScoresAnthropicJoin:
    """LEFT JOIN of Anthropic observed exposure onto the blend."""

    def test_blend_with_anthropic_populates_new_fields(
        self, gemma_row, karpathy_row, anthropic_row, promoted_at,
    ) -> None:
        blended = blend_scores(
            gemma_rows={"13-2051": gemma_row},
            karpathy_rows={"13-2051": karpathy_row},
            promoted_at=promoted_at,
            anthropic_rows={"13-2051": anthropic_row},
        )
        assert len(blended) == 1
        row = blended[0]
        # Silver column observed_exposure_pct is renamed to ai_adoption_share
        # at the Gold blend boundary (v4).
        assert row["ai_adoption_share"] == 3.7
        assert row["automation_pct"] == 45.0
        assert row["anthropic_task_count"] == 5
        assert row["anthropic_source_release"] == "release_2025_03_27"

    def test_blend_without_anthropic_still_emits_new_fields_as_none(
        self, gemma_row, karpathy_row, promoted_at,
    ) -> None:
        """LEFT JOIN semantics: missing Anthropic = None, not missing."""
        blended = blend_scores(
            gemma_rows={"13-2051": gemma_row},
            karpathy_rows={"13-2051": karpathy_row},
            promoted_at=promoted_at,
            anthropic_rows=None,
        )
        row = blended[0]
        assert row["ai_adoption_share"] is None
        assert row["automation_pct"] is None
        assert row["anthropic_task_count"] is None
        assert row["anthropic_source_release"] is None

    def test_blend_unmatched_anthropic_keeps_row_with_none(
        self, gemma_row, karpathy_row, promoted_at,
    ) -> None:
        """A SOC with no Anthropic match should still be in output."""
        blended = blend_scores(
            gemma_rows={"13-2051": gemma_row},
            karpathy_rows={"13-2051": karpathy_row},
            promoted_at=promoted_at,
            anthropic_rows={"15-1252": {"observed_exposure_pct": 99.0}},
        )
        assert len(blended) == 1
        assert blended[0]["soc_code"] == "13-2051"
        assert blended[0]["ai_adoption_share"] is None

    def test_blend_preserves_existing_gemma_preference(
        self, gemma_row, karpathy_row, anthropic_row, promoted_at,
    ) -> None:
        """Regression: Anthropic JOIN does not disturb Gemma > Karpathy."""
        blended = blend_scores(
            gemma_rows={"13-2051": gemma_row},
            karpathy_rows={"13-2051": karpathy_row},
            promoted_at=promoted_at,
            anthropic_rows={"13-2051": anthropic_row},
        )
        row = blended[0]
        assert row["scoring_model"] == "gemma-4"
        assert row["exposure_score"] == 7  # from Gemma
        assert row["karpathy_score"] == 8  # Karpathy preserved for A/B
