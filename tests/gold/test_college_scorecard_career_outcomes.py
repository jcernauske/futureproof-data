"""Tests for the Gold zone career outcomes transformer.

Covers all derivation logic, edge cases, grain uniqueness, and idempotency.
Minimum 15 tests required for consumable zone per staff engineer rules.
"""

import datetime

import pytest

from gold.college_scorecard_career_outcomes import (
    CSI_ENRICHMENT_COLUMNS,
    GRAIN_FIELDS,
    GRAIN_PREFIX,
    _snap_outcome_completeness,
    add_record_ids,
    derive_gold_rows,
    get_gold_schema,
)
from brightsmith.infra.grain import compute_grain_id
from pyiceberg.types import DoubleType, StringType


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_silver_row(
    unitid=100000,
    institution_name="Test University",
    institution_control=None,
    cipcode="52.02",
    program_name="Business Administration",
    cip_family="52",
    cip_family_name="Business, Management, Marketing, and Related Support Services",
    credential_level=3,
    earnings_1yr_median=50000.0,
    earnings_2yr_median=55000.0,
    debt_median=25000.0,
    completions_count_1=100,
    completions_count_2=105,
    small_cohort_flag=False,
    source_load_date=datetime.date(2026, 4, 6),
    ingested_at=datetime.datetime(2026, 4, 6, 0, 0, 0),
    record_id="cs-abc123",
):
    """Build a Silver-shaped row for testing."""
    return {
        "record_id": record_id,
        "unitid": unitid,
        "institution_name": institution_name,
        "institution_control": institution_control,
        "cipcode": cipcode,
        "program_name": program_name,
        "cip_family": cip_family,
        "cip_family_name": cip_family_name,
        "credential_level": credential_level,
        "earnings_1yr_median": earnings_1yr_median,
        "earnings_2yr_median": earnings_2yr_median,
        "debt_median": debt_median,
        "completions_count_1": completions_count_1,
        "completions_count_2": completions_count_2,
        "small_cohort_flag": small_cohort_flag,
        "source_load_date": source_load_date,
        "ingested_at": ingested_at,
    }


def _make_institution_row(
    unitid=100000,
    net_price_annual=20000.0,
    cost_of_attendance_annual=60000.0,
    net_price_4yr=None,
    institution_control="Private nonprofit",
    tuition_in_state=35000.0,
    tuition_out_of_state=55000.0,
    room_board_on_campus=15000.0,
):
    """Build an institution-silver-shaped row for CSI enrichment tests.

    Mirrors the columns read by the ``institution`` CTE in GOLD_SQL.
    """
    if net_price_4yr is None and net_price_annual is not None:
        net_price_4yr = net_price_annual * 4
    return {
        "unitid": unitid,
        "net_price_annual": net_price_annual,
        "cost_of_attendance_annual": cost_of_attendance_annual,
        "net_price_4yr": net_price_4yr,
        "institution_control": institution_control,
        "tuition_in_state": tuition_in_state,
        "tuition_out_of_state": tuition_out_of_state,
        "room_board_on_campus": room_board_on_campus,
    }


def _make_cip_family_rows(cip_family, cip_family_name, earnings_list, debt_list=None):
    """Build multiple Silver rows for a single CIP family with varying earnings."""
    rows = []
    for i, earn in enumerate(earnings_list):
        debt = debt_list[i] if debt_list else 25000.0
        rows.append(_make_silver_row(
            unitid=100000 + i,
            cipcode=f"{cip_family}.{i:02d}",
            cip_family=cip_family,
            cip_family_name=cip_family_name,
            earnings_1yr_median=earn,
            earnings_2yr_median=earn * 1.1 if earn is not None else None,
            debt_median=debt,
            record_id=f"cs-test{cip_family}{i:03d}",
        ))
    return rows


@pytest.fixture
def single_row():
    """A single well-populated Silver row."""
    return [_make_silver_row()]


@pytest.fixture
def cip_family_5_rows():
    """5 rows in the same CIP family with varying earnings."""
    return _make_cip_family_rows(
        "11", "Computer and Information Sciences",
        [40000.0, 50000.0, 60000.0, 70000.0, 80000.0],
        [20000.0, 22000.0, 24000.0, 26000.0, 28000.0],
    )


@pytest.fixture
def two_cip_families():
    """Rows across two CIP families."""
    fam1 = _make_cip_family_rows(
        "11", "Computer Science",
        [40000.0, 60000.0, 80000.0],
    )
    fam2 = _make_cip_family_rows(
        "52", "Business",
        [30000.0, 40000.0, 50000.0],
    )
    return fam1 + fam2


# ---------------------------------------------------------------------------
# Tests: Schema
# ---------------------------------------------------------------------------


class TestGoldSchema:
    """Tests for the Gold Iceberg schema definition."""

    def test_schema_field_count(self):
        schema = get_gold_schema()
        # 31 original career-outcomes columns + 6 CSI enrichment columns
        # (field IDs 32-37) + 1 roi_cost_basis column (field ID 38, added
        # by plan ~/.claude/plans/why-are-we-still-jaunty-curry.md so
        # downstream can tell which numerator drove the cost-based DTE)
        # + 1 state_abbr column (field ID 39, added for regional price
        # parity lookups).
        assert len(schema.fields) == 39

    def test_required_fields(self):
        schema = get_gold_schema()
        required = {f.name for f in schema.fields if f.required}
        expected_required = {
            "record_id", "unitid", "institution_name", "cipcode",
            "program_name", "cip_family", "cip_family_name",
            "credential_level", "small_cohort_flag", "confidence_tier",
            "has_earnings", "has_debt", "outcome_completeness",
            "source_load_date", "promoted_at",
        }
        assert expected_required.issubset(required)

    def test_nullable_fields(self):
        schema = get_gold_schema()
        nullable = {f.name for f in schema.fields if not f.required}
        expected_nullable = {
            "institution_control", "earnings_1yr_median", "earnings_2yr_median",
            "debt_median", "completions_count", "earnings_1yr_p25",
            "earnings_1yr_p75", "debt_to_earnings_annual",
            "debt_to_earnings_tier", "earnings_growth_rate",
            "cip_family_earnings_rank", "program_value_index",
        }
        assert expected_nullable.issubset(nullable)


# ---------------------------------------------------------------------------
# Tests: Percentile Bands
# ---------------------------------------------------------------------------


class TestPercentileBands:
    """Tests for CIP-family percentile band derivation."""

    def test_percentile_bands_computed_for_5_rows(self, cip_family_5_rows):
        result = derive_gold_rows(cip_family_5_rows)
        # All 5 rows should have the same percentile bands
        p25_values = {r["earnings_1yr_p25"] for r in result}
        p75_values = {r["earnings_1yr_p75"] for r in result}
        assert len(p25_values) == 1  # All same CIP family -> same band
        assert len(p75_values) == 1
        p25 = p25_values.pop()
        p75 = p75_values.pop()
        assert p25 is not None
        assert p75 is not None
        assert p25 <= p75

    def test_percentile_band_ordering_invariant(self, cip_family_5_rows):
        result = derive_gold_rows(cip_family_5_rows)
        for row in result:
            if row["earnings_1yr_p25"] is not None:
                assert row["earnings_1yr_p25"] <= row["earnings_1yr_p75"]
            if row["earnings_2yr_p25"] is not None:
                assert row["earnings_2yr_p25"] <= row["earnings_2yr_p75"]
            if row["debt_p25"] is not None:
                assert row["debt_p25"] <= row["debt_p75"]

    def test_percentile_bands_null_when_fewer_than_3(self):
        """CIP families with < 3 non-null earnings get null bands."""
        rows = _make_cip_family_rows(
            "99", "Rare Field",
            [40000.0, 50000.0, None, None],  # Only 2 non-null
        )
        result = derive_gold_rows(rows)
        for row in result:
            assert row["earnings_1yr_p25"] is None
            assert row["earnings_1yr_p75"] is None

    def test_percentile_bands_valid_at_exactly_3(self):
        """CIP families with exactly 3 non-null values get valid bands."""
        rows = _make_cip_family_rows(
            "98", "Minimum Threshold",
            [30000.0, 50000.0, 70000.0],
        )
        result = derive_gold_rows(rows)
        assert result[0]["earnings_1yr_p25"] is not None
        assert result[0]["earnings_1yr_p75"] is not None

    def test_different_cip_families_get_different_bands(self, two_cip_families):
        result = derive_gold_rows(two_cip_families)
        cip11_rows = [r for r in result if r["cip_family"] == "11"]
        cip52_rows = [r for r in result if r["cip_family"] == "52"]
        # CS should have higher bands than Business
        assert cip11_rows[0]["earnings_1yr_p25"] > cip52_rows[0]["earnings_1yr_p25"]


# ---------------------------------------------------------------------------
# Tests: Debt-to-Earnings Ratio and Tier
# ---------------------------------------------------------------------------


class TestDebtToEarnings:
    """Tests for debt-to-earnings ratio and tier derivation."""

    def test_dte_computed_correctly(self, single_row):
        result = derive_gold_rows(single_row)
        row = result[0]
        expected = 25000.0 / 50000.0  # 0.5
        assert row["debt_to_earnings_annual"] == pytest.approx(expected)

    def test_dte_null_when_debt_null(self):
        rows = [_make_silver_row(debt_median=None)]
        result = derive_gold_rows(rows)
        assert result[0]["debt_to_earnings_annual"] is None

    def test_dte_null_when_earnings_null(self):
        rows = [_make_silver_row(earnings_1yr_median=None)]
        result = derive_gold_rows(rows)
        assert result[0]["debt_to_earnings_annual"] is None

    def test_dte_tier_low(self):
        rows = [_make_silver_row(debt_median=10000.0, earnings_1yr_median=50000.0)]
        result = derive_gold_rows(rows)
        assert result[0]["debt_to_earnings_tier"] == "Low"

    def test_dte_tier_moderate(self):
        rows = [_make_silver_row(debt_median=50000.0, earnings_1yr_median=50000.0)]
        result = derive_gold_rows(rows)
        assert result[0]["debt_to_earnings_tier"] == "Moderate"

    def test_dte_tier_high(self):
        rows = [_make_silver_row(debt_median=90000.0, earnings_1yr_median=50000.0)]
        result = derive_gold_rows(rows)
        assert result[0]["debt_to_earnings_tier"] == "High"

    def test_dte_tier_very_high(self):
        rows = [_make_silver_row(debt_median=130000.0, earnings_1yr_median=50000.0)]
        result = derive_gold_rows(rows)
        assert result[0]["debt_to_earnings_tier"] == "Very High"

    def test_dte_tier_null_when_ratio_null(self):
        rows = [_make_silver_row(debt_median=None)]
        result = derive_gold_rows(rows)
        assert result[0]["debt_to_earnings_tier"] is None

    def test_dte_tier_boundary_075(self):
        """0.75 exactly should be 'Moderate' (>= 0.75)."""
        rows = [_make_silver_row(debt_median=37500.0, earnings_1yr_median=50000.0)]
        result = derive_gold_rows(rows)
        assert result[0]["debt_to_earnings_annual"] == pytest.approx(0.75)
        assert result[0]["debt_to_earnings_tier"] == "Moderate"

    def test_dte_tier_boundary_150(self):
        """1.5 exactly should be 'High' (>= 1.5)."""
        rows = [_make_silver_row(debt_median=75000.0, earnings_1yr_median=50000.0)]
        result = derive_gold_rows(rows)
        assert result[0]["debt_to_earnings_annual"] == pytest.approx(1.5)
        assert result[0]["debt_to_earnings_tier"] == "High"

    def test_dte_tier_boundary_250(self):
        """2.5 exactly should be 'Very High' (>= 2.5)."""
        rows = [_make_silver_row(debt_median=125000.0, earnings_1yr_median=50000.0)]
        result = derive_gold_rows(rows)
        assert result[0]["debt_to_earnings_annual"] == pytest.approx(2.5)
        assert result[0]["debt_to_earnings_tier"] == "Very High"


# ---------------------------------------------------------------------------
# Tests: Earnings Growth Rate
# ---------------------------------------------------------------------------


class TestEarningsGrowthRate:
    """Tests for cross-cohort earnings differential."""

    def test_growth_rate_computed(self, single_row):
        result = derive_gold_rows(single_row)
        expected = (55000.0 - 50000.0) / 50000.0  # 0.1
        assert result[0]["earnings_growth_rate"] == pytest.approx(expected)

    def test_growth_rate_null_when_1yr_null(self):
        rows = [_make_silver_row(earnings_1yr_median=None)]
        result = derive_gold_rows(rows)
        assert result[0]["earnings_growth_rate"] is None

    def test_growth_rate_null_when_2yr_null(self):
        rows = [_make_silver_row(earnings_2yr_median=None)]
        result = derive_gold_rows(rows)
        assert result[0]["earnings_growth_rate"] is None

    def test_growth_rate_negative_allowed(self):
        """Negative growth is valid (cross-cohort, not regression)."""
        rows = [_make_silver_row(earnings_1yr_median=60000.0, earnings_2yr_median=50000.0)]
        result = derive_gold_rows(rows)
        assert result[0]["earnings_growth_rate"] < 0


# ---------------------------------------------------------------------------
# Tests: CIP Family Earnings Rank
# ---------------------------------------------------------------------------


class TestCipFamilyEarningsRank:
    """Tests for PERCENT_RANK within CIP family."""

    def test_rank_range(self, cip_family_5_rows):
        result = derive_gold_rows(cip_family_5_rows)
        ranks = [r["cip_family_earnings_rank"] for r in result
                 if r["cip_family_earnings_rank"] is not None]
        assert min(ranks) >= 0.0
        assert max(ranks) <= 1.0

    def test_rank_null_when_earnings_null(self):
        rows = [_make_silver_row(earnings_1yr_median=None)]
        result = derive_gold_rows(rows)
        assert result[0]["cip_family_earnings_rank"] is None

    def test_rank_highest_earner_is_1(self, cip_family_5_rows):
        result = derive_gold_rows(cip_family_5_rows)
        # Row with 80000 should have rank 1.0
        highest = [r for r in result if r["earnings_1yr_median"] == 80000.0]
        assert len(highest) == 1
        assert highest[0]["cip_family_earnings_rank"] == pytest.approx(1.0)

    def test_rank_lowest_earner_is_0(self, cip_family_5_rows):
        result = derive_gold_rows(cip_family_5_rows)
        lowest = [r for r in result if r["earnings_1yr_median"] == 40000.0]
        assert len(lowest) == 1
        assert lowest[0]["cip_family_earnings_rank"] == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Tests: Program Value Index
# ---------------------------------------------------------------------------


class TestProgramValueIndex:
    """Tests for ROI proxy (earnings / debt)."""

    def test_pvi_computed(self, single_row):
        result = derive_gold_rows(single_row)
        expected = 50000.0 / 25000.0  # 2.0
        assert result[0]["program_value_index"] == pytest.approx(expected)

    def test_pvi_null_when_debt_null(self):
        rows = [_make_silver_row(debt_median=None)]
        result = derive_gold_rows(rows)
        assert result[0]["program_value_index"] is None

    def test_pvi_null_when_earnings_null(self):
        rows = [_make_silver_row(earnings_1yr_median=None)]
        result = derive_gold_rows(rows)
        assert result[0]["program_value_index"] is None


# ---------------------------------------------------------------------------
# Tests: Confidence Tier
# ---------------------------------------------------------------------------


class TestConfidenceTier:
    """Tests for data quality tier assignment."""

    def test_high_confidence(self):
        rows = [_make_silver_row(
            small_cohort_flag=False,
            earnings_1yr_median=50000.0,
            debt_median=25000.0,
        )]
        result = derive_gold_rows(rows)
        assert result[0]["confidence_tier"] == "high"

    def test_medium_confidence_earnings_only(self):
        rows = [_make_silver_row(
            small_cohort_flag=False,
            earnings_1yr_median=50000.0,
            earnings_2yr_median=None,
            debt_median=None,
        )]
        result = derive_gold_rows(rows)
        assert result[0]["confidence_tier"] == "medium"

    def test_medium_confidence_debt_only(self):
        rows = [_make_silver_row(
            small_cohort_flag=False,
            earnings_1yr_median=None,
            earnings_2yr_median=None,
            debt_median=25000.0,
        )]
        result = derive_gold_rows(rows)
        assert result[0]["confidence_tier"] == "medium"

    def test_low_confidence(self):
        rows = [_make_silver_row(
            small_cohort_flag=True,
            earnings_1yr_median=50000.0,
            debt_median=25000.0,
        )]
        result = derive_gold_rows(rows)
        assert result[0]["confidence_tier"] == "low"

    def test_insufficient_confidence(self):
        rows = [_make_silver_row(
            small_cohort_flag=True,
            earnings_1yr_median=None,
            earnings_2yr_median=None,
            debt_median=None,
        )]
        result = derive_gold_rows(rows)
        assert result[0]["confidence_tier"] == "insufficient"

    def test_insufficient_large_cohort_no_data(self):
        """Large cohort but no outcome data -> insufficient."""
        rows = [_make_silver_row(
            small_cohort_flag=False,
            earnings_1yr_median=None,
            earnings_2yr_median=None,
            debt_median=None,
        )]
        result = derive_gold_rows(rows)
        assert result[0]["confidence_tier"] == "insufficient"


# ---------------------------------------------------------------------------
# Tests: Convenience Flags and Outcome Completeness
# ---------------------------------------------------------------------------


class TestConvenienceFlags:
    """Tests for has_earnings, has_debt, and outcome_completeness."""

    def test_has_earnings_true_with_1yr(self):
        rows = [_make_silver_row(earnings_1yr_median=50000.0, earnings_2yr_median=None)]
        result = derive_gold_rows(rows)
        assert result[0]["has_earnings"] is True

    def test_has_earnings_true_with_2yr(self):
        rows = [_make_silver_row(earnings_1yr_median=None, earnings_2yr_median=55000.0)]
        result = derive_gold_rows(rows)
        assert result[0]["has_earnings"] is True

    def test_has_earnings_false(self):
        rows = [_make_silver_row(earnings_1yr_median=None, earnings_2yr_median=None)]
        result = derive_gold_rows(rows)
        assert result[0]["has_earnings"] is False

    def test_has_debt_true(self, single_row):
        result = derive_gold_rows(single_row)
        assert result[0]["has_debt"] is True

    def test_has_debt_false(self):
        rows = [_make_silver_row(debt_median=None)]
        result = derive_gold_rows(rows)
        assert result[0]["has_debt"] is False

    def test_outcome_completeness_1_0(self, single_row):
        result = derive_gold_rows(single_row)
        assert result[0]["outcome_completeness"] == pytest.approx(1.0)

    def test_outcome_completeness_0_67(self):
        rows = [_make_silver_row(debt_median=None)]
        result = derive_gold_rows(rows)
        assert result[0]["outcome_completeness"] == pytest.approx(0.67)

    def test_outcome_completeness_0_33(self):
        rows = [_make_silver_row(
            earnings_1yr_median=None, earnings_2yr_median=None, debt_median=25000.0
        )]
        result = derive_gold_rows(rows)
        assert result[0]["outcome_completeness"] == pytest.approx(0.33)

    def test_outcome_completeness_0_0(self):
        rows = [_make_silver_row(
            earnings_1yr_median=None, earnings_2yr_median=None, debt_median=None
        )]
        result = derive_gold_rows(rows)
        assert result[0]["outcome_completeness"] == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Tests: Record ID and Grain
# ---------------------------------------------------------------------------


class TestRecordIdAndGrain:
    """Tests for deterministic record_id computation."""

    def test_record_id_prefix(self, single_row):
        result = derive_gold_rows(single_row)
        promoted_at = datetime.datetime(2026, 4, 6, 0, 0, 0)
        add_record_ids(result, promoted_at)
        assert result[0]["record_id"].startswith("co-")

    def test_record_id_deterministic(self, single_row):
        result1 = derive_gold_rows(single_row)
        result2 = derive_gold_rows(single_row)
        ts = datetime.datetime(2026, 4, 6, 0, 0, 0)
        add_record_ids(result1, ts)
        add_record_ids(result2, ts)
        assert result1[0]["record_id"] == result2[0]["record_id"]

    def test_record_id_changes_with_grain(self):
        rows1 = [_make_silver_row(unitid=100000)]
        rows2 = [_make_silver_row(unitid=200000)]
        result1 = derive_gold_rows(rows1)
        result2 = derive_gold_rows(rows2)
        ts = datetime.datetime(2026, 4, 6, 0, 0, 0)
        add_record_ids(result1, ts)
        add_record_ids(result2, ts)
        assert result1[0]["record_id"] != result2[0]["record_id"]

    def test_grain_uniqueness(self, two_cip_families):
        result = derive_gold_rows(two_cip_families)
        ts = datetime.datetime(2026, 4, 6, 0, 0, 0)
        add_record_ids(result, ts)
        record_ids = [r["record_id"] for r in result]
        assert len(record_ids) == len(set(record_ids))

    def test_promoted_at_added(self, single_row):
        result = derive_gold_rows(single_row)
        ts = datetime.datetime(2026, 4, 6, 12, 0, 0, tzinfo=datetime.timezone.utc)
        add_record_ids(result, ts)
        assert result[0]["promoted_at"] == ts

    def test_grain_uses_credlev_key(self):
        """Verify the grain hash uses 'credlev' (spec field name), not 'credential_level'."""
        grain_row = {"unitid": 100000, "cipcode": "52.02", "credlev": 3}
        expected = compute_grain_id(grain_row, GRAIN_FIELDS, prefix=GRAIN_PREFIX)

        rows = [_make_silver_row(unitid=100000, cipcode="52.02", credential_level=3)]
        result = derive_gold_rows(rows)
        ts = datetime.datetime(2026, 4, 6, 0, 0, 0)
        add_record_ids(result, ts)
        assert result[0]["record_id"] == expected


# ---------------------------------------------------------------------------
# Tests: Edge Cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Tests for edge cases: all-null inputs, zero denominators, etc."""

    def test_all_null_outcome_fields(self):
        """Row with all outcome fields null should still produce a valid row."""
        rows = [_make_silver_row(
            earnings_1yr_median=None,
            earnings_2yr_median=None,
            debt_median=None,
        )]
        result = derive_gold_rows(rows)
        assert len(result) == 1
        row = result[0]
        assert row["debt_to_earnings_annual"] is None
        assert row["debt_to_earnings_tier"] is None
        assert row["earnings_growth_rate"] is None
        assert row["program_value_index"] is None
        assert row["cip_family_earnings_rank"] is None
        assert row["has_earnings"] is False
        assert row["has_debt"] is False
        assert row["outcome_completeness"] == 0.0
        assert row["confidence_tier"] in ("insufficient", "low")

    def test_empty_input_returns_empty(self):
        result = derive_gold_rows([])
        assert result == []

    def test_completions_count_renamed_from_completions_count_1(self, single_row):
        result = derive_gold_rows(single_row)
        assert "completions_count" in result[0]
        assert "completions_count_1" not in result[0]
        assert result[0]["completions_count"] == 100

    def test_dropped_fields_not_in_output(self, single_row):
        result = derive_gold_rows(single_row)
        row = result[0]
        assert "completions_count_2" not in row
        assert "credential_description" not in row
        assert "ingested_at" not in row

    def test_institution_control_nullable(self):
        """institution_control can be null (100% null from Bronze, known gap)."""
        rows = [_make_silver_row(institution_control=None)]
        result = derive_gold_rows(rows)
        assert result[0]["institution_control"] is None

    def test_row_count_preserved(self, two_cip_families):
        result = derive_gold_rows(two_cip_families)
        assert len(result) == len(two_cip_families)


# ---------------------------------------------------------------------------
# Tests: Snap Outcome Completeness
# ---------------------------------------------------------------------------


class TestSnapOutcomeCompleteness:
    """Tests for the floating-point snap helper."""

    def test_snaps_exact_values(self):
        assert _snap_outcome_completeness(0.0) == 0.0
        assert _snap_outcome_completeness(0.33) == 0.33
        assert _snap_outcome_completeness(0.67) == 0.67
        assert _snap_outcome_completeness(1.0) == 1.0

    def test_snaps_close_values(self):
        assert _snap_outcome_completeness(0.333333) == 0.33
        assert _snap_outcome_completeness(0.666667) == 0.67
        assert _snap_outcome_completeness(0.001) == 0.0
        assert _snap_outcome_completeness(0.999) == 1.0


# ---------------------------------------------------------------------------
# Tests: CSI Enrichment (spec raw-ingest-college-scorecard-institution §Zone 3)
# ---------------------------------------------------------------------------


class TestCsiEnrichmentSchema:
    """Schema-level assertions for the 6 net-new CSI enrichment columns."""

    def test_csi_enrichment_columns_exist(self):
        """All 6 CSI enrichment columns are present in the Iceberg schema."""
        schema = get_gold_schema()
        names = {f.name for f in schema.fields}
        for col in CSI_ENRICHMENT_COLUMNS:
            assert col in names, f"Missing CSI enrichment column: {col}"

    def test_csi_enrichment_columns_are_double_and_nullable(self):
        schema = get_gold_schema()
        by_name = {f.name: f for f in schema.fields}
        for col in CSI_ENRICHMENT_COLUMNS:
            field = by_name[col]
            assert isinstance(field.field_type, DoubleType), (
                f"{col} must be DoubleType, got {field.field_type}"
            )
            assert field.required is False, f"{col} must be nullable"

    def test_institution_control_is_nullable_string(self):
        """institution_control is kept at field ID 4 and is nullable (spec
        §Zone 3: the column is re-sourced from the institution file; unmatched
        UNITIDs must produce NULL not a constraint violation)."""
        schema = get_gold_schema()
        by_name = {f.name: f for f in schema.fields}
        field = by_name["institution_control"]
        assert field.field_id == 4
        assert isinstance(field.field_type, StringType)
        assert field.required is False

    def test_csi_enrichment_field_ids_are_32_through_37(self):
        """Spec §Zone 3 + physical model: field IDs 32-37 for the 6 net-new
        columns. Existing field IDs must not be reused."""
        schema = get_gold_schema()
        by_name = {f.name: f for f in schema.fields}
        expected = {
            "net_price_annual": 32,
            "cost_of_attendance_annual": 33,
            "net_price_4yr": 34,
            "tuition_in_state": 35,
            "tuition_out_of_state": 36,
            "room_board_on_campus": 37,
        }
        for name, field_id in expected.items():
            assert by_name[name].field_id == field_id


class TestCsiEnrichmentDerive:
    """Row-level assertions for ``derive_gold_rows`` with CSI enrichment."""

    def test_derive_output_contains_all_seven_enrichment_columns(self, single_row):
        """All 7 enrichment columns (6 new + institution_control) are present
        on every derived row with the correct types when an institution row is
        supplied."""
        inst = [_make_institution_row(unitid=100000)]
        result = derive_gold_rows(single_row, inst)
        assert len(result) == 1
        row = result[0]
        # 6 net-new enrichment columns populated from the institution row
        for col in CSI_ENRICHMENT_COLUMNS:
            assert col in row, f"Missing column in output: {col}"
            assert isinstance(row[col], float), (
                f"{col} must be float, got {type(row[col]).__name__}"
            )
        # institution_control populated from the institution row (str)
        assert row["institution_control"] == "Private nonprofit"

    def test_left_join_preserves_row_count_when_no_match(self, two_cip_families):
        """LEFT JOIN must not drop any silver rows even when NO institution
        rows match. count(in) == count(out)."""
        # Zero matching institutions
        result = derive_gold_rows(two_cip_families, institution_rows=[])
        assert len(result) == len(two_cip_families)
        # All CSI enrichment columns are null for every row
        for row in result:
            for col in CSI_ENRICHMENT_COLUMNS:
                assert row[col] is None, (
                    f"{col} should be NULL with no institution match"
                )
            assert row["institution_control"] is None

    def test_left_join_preserves_row_count_partial_match(self, two_cip_families):
        """Partial match: some silver unitids match, some don't. Row count is
        still preserved and unmatched rows get NULLs."""
        # two_cip_families uses unitids 100000, 100001, 100002 (cip 11) and
        # 100000, 100001, 100002 (cip 52). Provide an institution row for
        # only one of them.
        inst = [_make_institution_row(unitid=100001, institution_control="Public")]
        result = derive_gold_rows(two_cip_families, inst)
        assert len(result) == len(two_cip_families)
        matched = [r for r in result if r["unitid"] == 100001]
        unmatched = [r for r in result if r["unitid"] != 100001]
        # Matched rows have populated enrichment
        assert len(matched) >= 1
        for row in matched:
            assert row["net_price_annual"] is not None
            assert row["institution_control"] == "Public"
        # Unmatched rows have null enrichment
        for row in unmatched:
            assert row["net_price_annual"] is None
            assert row["institution_control"] is None

    def test_net_price_4yr_equals_4x_annual(self, single_row):
        """Silver invariant preserved in Gold: net_price_4yr ≈ annual × 4
        within $1 tolerance (GLD-CSI-003)."""
        inst = [_make_institution_row(
            unitid=100000,
            net_price_annual=12345.67,
            net_price_4yr=12345.67 * 4,
        )]
        result = derive_gold_rows(single_row, inst)
        row = result[0]
        assert row["net_price_annual"] == pytest.approx(12345.67)
        assert row["net_price_4yr"] == pytest.approx(12345.67 * 4)
        assert abs(row["net_price_4yr"] - row["net_price_annual"] * 4) <= 1.0

    def test_institution_control_resourced_from_institution_file(self, single_row):
        """Spec §Zone 3: institution_control on the output is sourced from the
        institution file, NOT carried forward from the field-of-study silver
        row. Verify by supplying a field-of-study row with a conflicting value
        and confirming the institution-file value wins."""
        # Silver row's institution_control is None (default), but even if a
        # field-of-study value were propagated incorrectly, the institution
        # file must override.
        silver = [_make_silver_row(
            unitid=100000,
            institution_control="STALE_VALUE",  # Should not appear in output.
        )]
        inst = [_make_institution_row(
            unitid=100000,
            institution_control="Public",
        )]
        result = derive_gold_rows(silver, inst)
        assert result[0]["institution_control"] == "Public"

    def test_empty_institution_rows_defaults_to_nulls(self, single_row):
        """When the institution silver side is empty, derive_gold_rows must
        still succeed and produce NULLs for all 7 enrichment columns."""
        result = derive_gold_rows(single_row, institution_rows=None)
        row = result[0]
        for col in CSI_ENRICHMENT_COLUMNS:
            assert row[col] is None
