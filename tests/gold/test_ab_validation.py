"""Tests for the 8-gate A/B validation in reports/gemma_vs_karpathy_comparison.py.

Each gate is exercised with both pass and fail cases, plus the outlier
list and the markdown render.
"""

import importlib.util
from pathlib import Path


# Load the comparison module by file path because ``reports/`` isn't
# on the default package path.
_COMP_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "reports"
    / "gemma_vs_karpathy_comparison.py"
)
_SPEC = importlib.util.spec_from_file_location("ab_comparison", _COMP_PATH)
assert _SPEC is not None and _SPEC.loader is not None
_MOD = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MOD)

validate_ab_comparison = _MOD.validate_ab_comparison
render_markdown_report = _MOD.render_markdown_report


def _paired(gemma_vals, karpathy_vals, categories=None):
    """Build the gemma/karpathy dict shape validate_ab_comparison expects."""
    if categories is None:
        categories = ["business-and-financial"] * len(gemma_vals)
    gemma, karpathy = {}, {}
    for i, (g, k, cat) in enumerate(zip(gemma_vals, karpathy_vals, categories)):
        soc = f"13-{2051 + i:04d}"
        gemma[soc] = {"exposure_score": g, "rationale": f"gemma {i}"}
        karpathy[soc] = {
            "exposure_score": k,
            "category": cat,
            "occupation_title": f"title {i}",
            "rationale": f"karpathy {i}",
        }
    return gemma, karpathy


# ---------------------------------------------------------------------------
# Gate 1: correlation
# ---------------------------------------------------------------------------


class TestCorrelationGate:
    def test_perfect_correlation_passes(self):
        """Identical scores → correlation = 1.0."""
        gemma, karpathy = _paired([1, 3, 5, 7, 9, 10], [1, 3, 5, 7, 9, 10])
        result = validate_ab_comparison(gemma, karpathy)
        assert result["gates"]["correlation"]["value"] == 1.0
        assert result["gates"]["correlation"]["pass"]

    def test_weak_correlation_fails(self):
        """Random-looking scores with r ≈ 0 fail the 0.6 floor."""
        gemma, karpathy = _paired([1, 10, 2, 9, 3, 8], [1, 2, 3, 4, 5, 6])
        result = validate_ab_comparison(gemma, karpathy)
        assert not result["gates"]["correlation"]["pass"]


# ---------------------------------------------------------------------------
# Gate 2: mean absolute diff
# ---------------------------------------------------------------------------


class TestMadGate:
    def test_exact_match_mad_zero(self):
        gemma, karpathy = _paired([5, 5, 5], [5, 5, 5])
        result = validate_ab_comparison(gemma, karpathy)
        assert result["gates"]["mean_absolute_diff"]["value"] == 0.0
        assert result["gates"]["mean_absolute_diff"]["pass"]

    def test_large_diff_fails(self):
        gemma, karpathy = _paired([0, 0, 0, 0], [10, 10, 10, 10])
        result = validate_ab_comparison(gemma, karpathy)
        assert result["gates"]["mean_absolute_diff"]["value"] == 10.0
        assert not result["gates"]["mean_absolute_diff"]["pass"]


# ---------------------------------------------------------------------------
# Gate 3: mean signed delta
# ---------------------------------------------------------------------------


class TestMeanDeltaGate:
    def test_symmetric_differences_pass(self):
        """+2 and -2 cancel out → mean delta = 0."""
        gemma, karpathy = _paired([7, 3, 7, 3], [5, 5, 5, 5])
        result = validate_ab_comparison(gemma, karpathy)
        assert result["gates"]["mean_signed_delta"]["value"] == 0.0
        assert result["gates"]["mean_signed_delta"]["pass"]

    def test_systematic_skew_fails(self):
        """Gemma consistently 3 points higher → mean delta = 3."""
        gemma, karpathy = _paired([6, 7, 8, 9], [3, 4, 5, 6])
        result = validate_ab_comparison(gemma, karpathy)
        assert result["gates"]["mean_signed_delta"]["value"] == 3.0
        assert not result["gates"]["mean_signed_delta"]["pass"]


# ---------------------------------------------------------------------------
# Gate 4: category bias
# ---------------------------------------------------------------------------


class TestCategoryBiasGate:
    def test_small_n_categories_do_not_gate(self):
        """A single-row category with bias=10 shouldn't fail Gate 4."""
        # Put a 10-row exact-match category + a 1-row wildly-off category.
        exact_cats = ["a"] * 10
        exact_g = [5] * 10
        exact_k = [5] * 10
        # Extra row — category "b" with n=1 and bias=10.
        gemma, karpathy = _paired(
            exact_g + [10], exact_k + [0], exact_cats + ["b"]
        )
        result = validate_ab_comparison(gemma, karpathy)
        # Category "b" has n=1 < 10, so it shouldn't be gated.
        assert result["gates"]["category_bias"]["pass"]

    def test_large_n_category_with_big_bias_fails(self):
        """A 10-row category with mean bias > 2.0 triggers Gate 4."""
        gemma, karpathy = _paired(
            [8] * 12, [5] * 12, ["biased-category"] * 12
        )
        result = validate_ab_comparison(gemma, karpathy)
        assert not result["gates"]["category_bias"]["pass"]
        violations = result["gates"]["category_bias"]["violations"]
        assert any(v["category"] == "biased-category" for v in violations)


# ---------------------------------------------------------------------------
# Gate 5: mode collapse
# ---------------------------------------------------------------------------


class TestModeCollapseGate:
    def test_healthy_distribution_passes(self):
        """Scores spread across the scale → mode concentration <= 40%."""
        gemma_vals = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        karpathy_vals = gemma_vals[:]
        gemma, karpathy = _paired(gemma_vals, karpathy_vals)
        result = validate_ab_comparison(gemma, karpathy)
        assert result["gates"]["mode_collapse"]["pass"]

    def test_mode_dominates_fails(self):
        """50% of rows on score 7 → mode > 40% → fail."""
        # 6 rows at 7, 4 rows spread across 2-5 → mode = 60%.
        gemma_vals = [7, 7, 7, 7, 7, 7, 2, 3, 4, 5]
        karpathy_vals = [7, 7, 7, 7, 7, 7, 2, 3, 4, 5]
        gemma, karpathy = _paired(gemma_vals, karpathy_vals)
        result = validate_ab_comparison(gemma, karpathy)
        assert not result["gates"]["mode_collapse"]["pass"]


# ---------------------------------------------------------------------------
# Gate 6: std dev floor
# ---------------------------------------------------------------------------


class TestStdDevGate:
    def test_spread_distribution_passes(self):
        """Wide spread → std dev > 1.5."""
        gemma_vals = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        gemma, karpathy = _paired(gemma_vals, gemma_vals)
        result = validate_ab_comparison(gemma, karpathy)
        assert result["gates"]["std_dev_floor"]["pass"]

    def test_narrow_cluster_fails(self):
        """Scores clustered 5-6 → std dev < 1.5."""
        gemma_vals = [5, 5, 5, 6, 6, 6, 5, 6, 5, 6]
        gemma, karpathy = _paired(gemma_vals, gemma_vals)
        result = validate_ab_comparison(gemma, karpathy)
        assert not result["gates"]["std_dev_floor"]["pass"]


# ---------------------------------------------------------------------------
# Gate 7: bucket coverage
# ---------------------------------------------------------------------------


class TestBucketCoverageGate:
    def test_all_buckets_populated_passes(self):
        gemma_vals = [1, 2, 5, 6, 8, 9] * 3  # 18 rows across all 3 buckets
        gemma, karpathy = _paired(gemma_vals, gemma_vals)
        result = validate_ab_comparison(gemma, karpathy)
        assert result["gates"]["bucket_coverage"]["pass"]

    def test_missing_low_bucket_fails(self):
        """No scores in 0-3 → bucket_coverage fails."""
        gemma_vals = [4, 5, 6, 7, 8, 9, 10] * 3  # 21 rows, no low
        gemma, karpathy = _paired(gemma_vals, gemma_vals)
        result = validate_ab_comparison(gemma, karpathy)
        assert not result["gates"]["bucket_coverage"]["pass"]


# ---------------------------------------------------------------------------
# Gate 8: outlier list + rate
# ---------------------------------------------------------------------------


class TestOutlierGate:
    def test_no_outliers_passes(self):
        gemma_vals = [5] * 20
        karpathy_vals = [5] * 20
        gemma, karpathy = _paired(gemma_vals, karpathy_vals)
        result = validate_ab_comparison(gemma, karpathy)
        assert result["gates"]["outlier_rate"]["pass"]
        assert result["outliers"] == []

    def test_outliers_are_listed(self):
        """|Δ| ≥ 4 rows appear in the outliers list."""
        # 20 exact-match rows + 1 outlier (Δ=5).
        gemma_vals = [5] * 20 + [10]
        karpathy_vals = [5] * 20 + [5]
        gemma, karpathy = _paired(gemma_vals, karpathy_vals)
        result = validate_ab_comparison(gemma, karpathy)
        assert len(result["outliers"]) == 1
        assert result["outliers"][0]["delta"] == 5

    def test_too_many_outliers_fails(self):
        """Outlier rate > 5% fails Gate 8."""
        # 10 matched + 2 outliers → 2/12 = 16.7% > 5%
        gemma_vals = [5] * 10 + [10, 10]
        karpathy_vals = [5] * 10 + [5, 5]
        gemma, karpathy = _paired(gemma_vals, karpathy_vals)
        result = validate_ab_comparison(gemma, karpathy)
        assert not result["gates"]["outlier_rate"]["pass"]


# ---------------------------------------------------------------------------
# Overall pass / empty / report render
# ---------------------------------------------------------------------------


class TestOverallAndReport:
    def test_overall_pass_when_all_gates_pass(self):
        gemma_vals = list(range(1, 11)) + list(range(1, 11))
        gemma, karpathy = _paired(gemma_vals, gemma_vals)
        result = validate_ab_comparison(gemma, karpathy)
        assert result["overall_pass"]

    def test_overall_fails_when_any_gate_fails(self):
        gemma_vals = [5, 5, 5, 5, 5, 5, 5, 5, 5, 5]  # mode collapse
        gemma, karpathy = _paired(gemma_vals, gemma_vals)
        result = validate_ab_comparison(gemma, karpathy)
        assert not result["overall_pass"]

    def test_empty_overlap_returns_not_pass(self):
        """No shared SOCs → overall_pass=False with a message."""
        gemma = {"13-2051": {"exposure_score": 5, "rationale": ""}}
        karpathy = {"15-1252": {
            "exposure_score": 5, "category": "x",
            "occupation_title": "", "rationale": "",
        }}
        result = validate_ab_comparison(gemma, karpathy)
        assert not result["overall_pass"]
        assert result["overlap_count"] == 0

    def test_markdown_report_contains_gate_table(self):
        gemma_vals = list(range(1, 11))
        gemma, karpathy = _paired(gemma_vals, gemma_vals)
        result = validate_ab_comparison(gemma, karpathy)
        md = render_markdown_report(result)
        assert "# Gemma 4 vs Karpathy AI Exposure Score Comparison" in md
        assert "1. Pearson correlation" in md
        assert "8. Outlier rate" in md

    def test_markdown_report_lists_outliers(self):
        gemma_vals = [5] * 19 + [10]
        karpathy_vals = [5] * 20
        gemma, karpathy = _paired(gemma_vals, karpathy_vals)
        result = validate_ab_comparison(gemma, karpathy)
        md = render_markdown_report(result)
        assert "Outlier list" in md
        assert "Outlier rationale diff" in md

    def test_fail_policy_note_shown_on_fail(self):
        gemma_vals = [5] * 20  # mode collapse
        gemma, karpathy = _paired(gemma_vals, gemma_vals)
        result = validate_ab_comparison(gemma, karpathy)
        md = render_markdown_report(result)
        assert "blocks the Gold promote" in md
