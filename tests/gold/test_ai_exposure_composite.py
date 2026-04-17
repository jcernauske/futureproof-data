"""Tests for the S4 v4 Option B composite formula.

Covers the pure helpers (`percent_rank`, `velocity_from_percentile`,
`compute_composite`, `derive_stats`) plus an end-to-end check that
`blend_scores` actually applies the composite to every row.

See docs/specs/three-signal-ai-exposure-composite-v3.md §4 (v4 Option B).
"""

from __future__ import annotations

import datetime

import pytest

from gold.ai_exposure_transformer import (
    blend_scores,
    compute_composite,
    derive_stats,
    percent_rank,
    velocity_from_percentile,
)


# ---------------------------------------------------------------------------
# percent_rank
# ---------------------------------------------------------------------------


class TestPercentRank:
    def test_basic_monotonic(self) -> None:
        """Values rank 0 / 50 / 100 for 3 evenly-spaced inputs."""
        assert percent_rank([1.0, 2.0, 3.0]) == [0.0, 50.0, 100.0]

    def test_preserves_none_slots(self) -> None:
        result = percent_rank([1.0, None, 3.0, None, 2.0])
        assert result[0] == 0.0
        assert result[1] is None
        assert result[2] == 100.0
        assert result[3] is None
        assert result[4] == 50.0

    def test_all_none_returns_all_none(self) -> None:
        assert percent_rank([None, None, None]) == [None, None, None]

    def test_single_value_is_100(self) -> None:
        """Degenerate case — a single non-null value gets percentile 100."""
        assert percent_rank([42.0, None]) == [100.0, None]

    def test_empty_input(self) -> None:
        assert percent_rank([]) == []

    def test_unsorted_input_ranks_correctly(self) -> None:
        """Order of the input must not matter — only rank."""
        result = percent_rank([3.0, 1.0, 2.0])
        assert result[0] == 100.0  # 3.0 is largest
        assert result[1] == 0.0    # 1.0 is smallest
        assert result[2] == 50.0   # 2.0 is middle


# ---------------------------------------------------------------------------
# velocity_from_percentile
# ---------------------------------------------------------------------------


class TestVelocityFromPercentile:
    @pytest.mark.parametrize("pct,expected", [
        (100.0, "saturating"),
        (95.0,  "saturating"),
        (90.0,  "saturating"),
        (89.99, "accelerating"),
        (75.0,  "accelerating"),
        (70.0,  "accelerating"),
        (69.99, "emerging"),
        (50.0,  "emerging"),
        (40.0,  "emerging"),
        (39.99, "nascent"),
        (10.0,  "nascent"),
        (0.0,   "nascent"),
    ])
    def test_label_boundaries(self, pct: float, expected: str) -> None:
        assert velocity_from_percentile(pct) == expected

    def test_none_is_unknown(self) -> None:
        assert velocity_from_percentile(None) == "unknown"


# ---------------------------------------------------------------------------
# compute_composite — fallback routing + method labels
# ---------------------------------------------------------------------------


class TestComputeComposite:
    def test_three_signal_full_blend(self) -> None:
        """Gemma + Karpathy + Anthropic → three_signal, percentile → confidence."""
        composite, conf, vel, method = compute_composite(
            gemma_score=8,
            karpathy_score=6,
            ai_adoption_share=0.25,
            adoption_percentile=80.0,
        )
        # confidence = 0.3 + 0.7 * 80/100 = 0.86
        assert conf is not None
        assert abs(conf - 0.86) < 1e-9
        # composite = 0.86*8 + 0.14*6 = 6.88 + 0.84 = 7.72 → round = 8
        assert composite == 8
        assert vel == "accelerating"
        assert method == "three_signal"

    def test_two_signal_no_anthropic(self) -> None:
        """Karpathy + Gemma but no adoption share → fallback confidence 0.5."""
        composite, conf, vel, method = compute_composite(
            gemma_score=8,
            karpathy_score=6,
            ai_adoption_share=None,
            adoption_percentile=None,
        )
        assert conf == 0.5
        assert vel == "unknown"
        assert method == "two_signal_no_anthropic"
        # composite = 0.5*8 + 0.5*6 = 7
        assert composite == 7

    def test_gemma_only_no_karpathy_no_anthropic(self) -> None:
        composite, conf, vel, method = compute_composite(
            gemma_score=7,
            karpathy_score=None,
            ai_adoption_share=None,
            adoption_percentile=None,
        )
        assert composite == 7
        assert method == "gemma_only"
        assert vel == "unknown"
        assert conf == 0.5

    def test_gemma_plus_anthropic_no_karpathy(self) -> None:
        """Gemma has score, Anthropic gives percentile, but no Karpathy baseline."""
        composite, conf, vel, method = compute_composite(
            gemma_score=7,
            karpathy_score=None,
            ai_adoption_share=0.1,
            adoption_percentile=65.0,
        )
        # Falls to gemma_plus_anthropic: composite = theoretical unchanged
        assert composite == 7
        assert method == "gemma_plus_anthropic"
        assert vel == "emerging"
        # confidence still computed even though unused for composite math
        assert conf is not None
        assert 0.3 <= conf <= 1.0

    def test_karpathy_only_no_gemma(self) -> None:
        composite, conf, vel, method = compute_composite(
            gemma_score=None,
            karpathy_score=4,
            ai_adoption_share=0.05,
            adoption_percentile=30.0,
        )
        # No theoretical → composite = baseline, method = karpathy_only
        assert composite == 4
        assert method == "karpathy_only"
        assert vel == "nascent"

    def test_observed_override_when_gemma_zero_but_adoption_present(self) -> None:
        """Edge case: Gemma says 0 but Anthropic shows adoption > 0."""
        composite, conf, vel, method = compute_composite(
            gemma_score=0,
            karpathy_score=5,
            ai_adoption_share=0.5,
            adoption_percentile=95.0,
        )
        # confidence = 0.3 + 0.7 * 95/100 = 0.965
        # composite = baseline * confidence = 5 * 0.965 = 4.825 → round = 5
        assert method == "observed_override"
        assert composite == 5
        assert vel == "saturating"

    def test_gemma_zero_no_adoption_not_override(self) -> None:
        """Gemma=0 without adoption data does NOT trigger observed_override."""
        composite, _, _, method = compute_composite(
            gemma_score=0,
            karpathy_score=5,
            ai_adoption_share=None,
            adoption_percentile=None,
        )
        assert method == "two_signal_no_anthropic"
        # Normal blend: 0.5*0 + 0.5*5 = 2.5 → round = 2 (banker's → nearest even)
        assert composite in (2, 3)

    def test_no_data_both_signals_missing(self) -> None:
        composite, conf, vel, method = compute_composite(
            gemma_score=None,
            karpathy_score=None,
            ai_adoption_share=None,
            adoption_percentile=None,
        )
        assert composite is None
        assert method == "no_data"
        assert vel == "unknown"
        assert conf is None

    def test_composite_clamps_to_10(self) -> None:
        """A theoretical pegged to 10 can't exceed 10 after blending."""
        composite, _, _, _ = compute_composite(
            gemma_score=10,
            karpathy_score=10,
            ai_adoption_share=1.0,
            adoption_percentile=100.0,
        )
        assert composite == 10

    def test_composite_clamps_to_0(self) -> None:
        """A theoretical pegged to 0 stays 0 under any blend (when not override)."""
        composite, _, _, method = compute_composite(
            gemma_score=0,
            karpathy_score=0,
            ai_adoption_share=None,
            adoption_percentile=None,
        )
        assert composite == 0
        assert method == "two_signal_no_anthropic"

    def test_confidence_clamped_low_percentile(self) -> None:
        """Percentile 0 still produces confidence 0.3 (floor)."""
        _, conf, vel, _ = compute_composite(
            gemma_score=5,
            karpathy_score=5,
            ai_adoption_share=0.001,
            adoption_percentile=0.0,
        )
        assert conf is not None
        assert conf == pytest.approx(0.3)
        assert vel == "nascent"

    def test_confidence_clamped_high_percentile(self) -> None:
        """Percentile 100 caps confidence at 1.0."""
        _, conf, _, _ = compute_composite(
            gemma_score=5,
            karpathy_score=5,
            ai_adoption_share=5.0,
            adoption_percentile=100.0,
        )
        assert conf == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# derive_stats
# ---------------------------------------------------------------------------


class TestDeriveStats:
    @pytest.mark.parametrize("composite,expected_res,expected_boss", [
        (0, 10, 1),   # max resilience, weakest fight
        (1, 10, 1),   # 11-1=10 capped, max(1,1)=1
        (2, 9, 2),
        (5, 6, 5),
        (8, 3, 8),
        (10, 1, 10),  # min resilience, hardest fight
    ])
    def test_inversion_table(
        self, composite: int, expected_res: int, expected_boss: int,
    ) -> None:
        stat_res, boss_ai = derive_stats(composite)
        assert stat_res == expected_res
        assert boss_ai == expected_boss

    def test_none_propagates(self) -> None:
        assert derive_stats(None) == (None, None)


# ---------------------------------------------------------------------------
# End-to-end: blend_scores applies composite
# ---------------------------------------------------------------------------


PROMOTED_AT = datetime.datetime(2026, 4, 16, 0, 0, 0, tzinfo=datetime.timezone.utc)


def _gemma(score: int, soc: str = "13-2051") -> dict:
    return {
        "soc_code": score and soc,  # always truthy for test inputs
        "exposure_score": score,
        "rationale": "A rationale long enough to pass any downstream length checks.",
        "primary_title": "Test Occupation",
        "scoring_model": "gemma-4",
        "model_tag": "gemma4:test",
        "task_breakdown_automatable": None,
        "task_breakdown_human": None,
        "error": None,
    }


def _karpathy(score: int) -> dict:
    return {
        "exposure_score": score,
        "rationale": "Karpathy rationale.",
        "occupation_title": "Test Occupation (Karpathy)",
        "category": "business-and-financial",
        "bls_match": True,
    }


class TestBlendScoresAppliesComposite:
    def test_single_row_full_signals_stat_res_matches_composite(self) -> None:
        blended = blend_scores(
            gemma_rows={"13-2051": _gemma(8)},
            karpathy_rows={"13-2051": _karpathy(6)},
            promoted_at=PROMOTED_AT,
            anthropic_rows={"13-2051": {"observed_exposure_pct": 0.25}},
        )
        assert len(blended) == 1
        row = blended[0]

        # Single-row adoption → percentile is 100 (degenerate but valid)
        assert row["adoption_percentile"] == 100.0
        assert row["velocity_label"] == "saturating"
        assert row["composite_method"] == "three_signal"
        assert row["composite_exposure"] is not None
        # stat_res and boss_ai_score derive from composite, not raw exposure_score
        stat_res, boss_ai = derive_stats(row["composite_exposure"])
        assert row["stat_res"] == stat_res
        assert row["boss_ai_score"] == boss_ai

    def test_percentile_computed_across_rows(self) -> None:
        """Three rows with different shares → spread of percentiles."""
        blended = blend_scores(
            gemma_rows={"a": _gemma(5), "b": _gemma(5), "c": _gemma(5)},
            karpathy_rows={},
            promoted_at=PROMOTED_AT,
            anthropic_rows={
                "a": {"observed_exposure_pct": 0.01},
                "b": {"observed_exposure_pct": 0.05},
                "c": {"observed_exposure_pct": 1.0},
            },
        )
        by_soc = {r["soc_code"]: r for r in blended}
        assert by_soc["a"]["adoption_percentile"] == 0.0
        assert by_soc["b"]["adoption_percentile"] == 50.0
        assert by_soc["c"]["adoption_percentile"] == 100.0

    def test_row_without_anthropic_gets_unknown_velocity(self) -> None:
        blended = blend_scores(
            gemma_rows={"13-2051": _gemma(7)},
            karpathy_rows={"13-2051": _karpathy(6)},
            promoted_at=PROMOTED_AT,
            anthropic_rows=None,
        )
        row = blended[0]
        assert row["velocity_label"] == "unknown"
        assert row["composite_method"] == "two_signal_no_anthropic"
        assert row["adoption_percentile"] is None
        assert row["confidence_weight"] == 0.5

    def test_all_provenance_fields_populated_on_every_row(self) -> None:
        """Regression: no row may be missing composite provenance keys."""
        blended = blend_scores(
            gemma_rows={"13-2051": _gemma(6)},
            karpathy_rows={"29-1141": _karpathy(4)},
            promoted_at=PROMOTED_AT,
            anthropic_rows=None,
        )
        keys = {
            "composite_exposure", "adoption_percentile",
            "confidence_weight", "velocity_label", "composite_method",
            "ai_adoption_share",
        }
        for row in blended:
            missing = keys - set(row)
            assert not missing, f"Row {row['soc_code']} missing {missing}"
