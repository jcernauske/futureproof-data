"""Tests for the Gold zone occupation profiles transformer.

Covers GRW piecewise function (all 8 segments + boundaries), market score,
wage percentile null handling, confidence tier logic, data completeness,
static fields, record IDs, and end-to-end transform with sample data.
"""

import datetime

import pytest

from gold.bls_ooh_occupation_profiles import (
    GOLD_SQL,
    GRAIN_FIELDS,
    GRAIN_PREFIX,
    GRW_BREAKPOINTS,
    _round_half_up,
    add_record_ids,
    compute_grw_score,
    derive_gold_rows,
    get_gold_schema,
)
from brightsmith.infra.grain import compute_grain_id


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_silver_row(
    soc_code="15-1252",
    occupation_title="Software Developers",
    soc_major_group="15",
    soc_major_group_name="Computer and Mathematical",
    broad_occupation_flag=False,
    catchall_flag=False,
    employment_current=1847900,
    employment_projected=2139600,
    employment_change_pct=15.8,
    openings_annual_avg=115200,
    growth_category="growing_fast",
    median_annual_wage=133080.0,
    median_wage_capped=False,
    wage_available=True,
    education_typical="Bachelor's degree",
    education_code=3,
    education_level_name="Bachelor's degree",
    work_experience="None",
    work_experience_code=3,
    training_typical="None",
    training_code=6,
    source_load_date=datetime.date(2026, 4, 7),
    ingested_at=datetime.datetime(2026, 4, 7, 0, 0, 0),
    record_id="ooh-abc123",
    employment_change=291700,
):
    """Build a Silver-shaped row for testing (matches base.bls_ooh schema)."""
    return {
        "record_id": record_id,
        "soc_code": soc_code,
        "occupation_title": occupation_title,
        "soc_major_group": soc_major_group,
        "soc_major_group_name": soc_major_group_name,
        "broad_occupation_flag": broad_occupation_flag,
        "catchall_flag": catchall_flag,
        "employment_current": employment_current,
        "employment_projected": employment_projected,
        "employment_change": employment_change,
        "employment_change_pct": employment_change_pct,
        "openings_annual_avg": openings_annual_avg,
        "growth_category": growth_category,
        "median_annual_wage": median_annual_wage,
        "median_wage_capped": median_wage_capped,
        "wage_available": wage_available,
        "education_typical": education_typical,
        "education_code": education_code,
        "education_level_name": education_level_name,
        "work_experience": work_experience,
        "work_experience_code": work_experience_code,
        "training_typical": training_typical,
        "training_code": training_code,
        "source_load_date": source_load_date,
        "ingested_at": ingested_at,
    }


def _make_multi_rows():
    """Build a set of Silver rows covering key test scenarios.

    Includes occupations with varying wages, null wages, broad/catchall flags,
    and different education codes for wage percentile testing.
    """
    rows = [
        # Software Developers - high growth, high wage
        _make_silver_row(
            soc_code="15-1252",
            occupation_title="Software Developers",
            employment_change_pct=15.8,
            median_annual_wage=133080.0,
            openings_annual_avg=115200,
            education_code=3,
            wage_available=True,
        ),
        # Registered Nurses - moderate growth, high openings
        _make_silver_row(
            soc_code="29-1141",
            occupation_title="Registered Nurses",
            soc_major_group="29",
            soc_major_group_name="Healthcare Practitioners and Technical",
            employment_change_pct=4.9,
            median_annual_wage=93600.0,
            openings_annual_avg=189100,
            education_code=3,
            growth_category="growing",
            wage_available=True,
            record_id="ooh-rn001",
        ),
        # Anesthesiologists - null wage, not broad, not catchall
        _make_silver_row(
            soc_code="29-1211",
            occupation_title="Anesthesiologists",
            soc_major_group="29",
            soc_major_group_name="Healthcare Practitioners and Technical",
            employment_change_pct=3.2,
            median_annual_wage=None,
            openings_annual_avg=1300,
            education_code=1,
            growth_category="growing",
            wage_available=False,
            record_id="ooh-anes001",
        ),
        # Fast food workers - low wage, high openings
        _make_silver_row(
            soc_code="35-3023",
            occupation_title="Fast Food and Counter Workers",
            soc_major_group="35",
            soc_major_group_name="Food Preparation and Serving Related",
            employment_change_pct=6.0,
            median_annual_wage=30160.0,
            openings_annual_avg=904300,
            education_code=8,
            growth_category="growing",
            wage_available=True,
            record_id="ooh-ff001",
        ),
        # Broad occupation code - should be medium confidence
        _make_silver_row(
            soc_code="31-1120",
            occupation_title="Home Health and Personal Care Aides",
            soc_major_group="31",
            soc_major_group_name="Healthcare Support",
            broad_occupation_flag=True,
            employment_change_pct=17.0,
            median_annual_wage=35240.0,
            openings_annual_avg=765800,
            education_code=8,
            growth_category="growing_fast",
            wage_available=True,
            record_id="ooh-broad001",
        ),
        # Catchall occupation - should be medium confidence
        _make_silver_row(
            soc_code="29-1229",
            occupation_title="Physicians, All Other",
            soc_major_group="29",
            soc_major_group_name="Healthcare Practitioners and Technical",
            catchall_flag=True,
            employment_change_pct=2.0,
            median_annual_wage=None,
            openings_annual_avg=3000,
            education_code=1,
            growth_category="growing",
            wage_available=False,
            record_id="ooh-catch001",
        ),
        # Declining occupation
        _make_silver_row(
            soc_code="43-2021",
            occupation_title="Telephone Operators",
            soc_major_group="43",
            soc_major_group_name="Office and Administrative Support",
            employment_change_pct=-27.5,
            median_annual_wage=42300.0,
            openings_annual_avg=300,
            education_code=7,
            growth_category="declining_fast",
            wage_available=True,
            record_id="ooh-decline001",
        ),
        # Another education_code=3 for within-tier ranking
        _make_silver_row(
            soc_code="15-1299",
            occupation_title="Computer Occupations, All Other",
            soc_major_group="15",
            soc_major_group_name="Computer and Mathematical",
            catchall_flag=True,
            employment_change_pct=10.0,
            median_annual_wage=99860.0,
            openings_annual_avg=25000,
            education_code=3,
            growth_category="growing_fast",
            wage_available=True,
            record_id="ooh-comp001",
        ),
    ]
    return rows


@pytest.fixture
def single_row():
    """A single well-populated Silver row (Software Developers)."""
    return [_make_silver_row()]


@pytest.fixture
def multi_rows():
    """Multiple rows covering key scenarios."""
    return _make_multi_rows()


# ---------------------------------------------------------------------------
# Tests: GRW Score Piecewise Function
# ---------------------------------------------------------------------------


class TestGRWScore:
    """Tests for compute_grw_score piecewise linear function."""

    def test_null_input_returns_null(self):
        assert compute_grw_score(None) is None

    def test_floor_at_negative_20(self):
        """<= -20.0 should return 1.0 (floor)."""
        assert compute_grw_score(-20.0) == 1.0
        assert compute_grw_score(-30.0) == 1.0
        assert compute_grw_score(-50.0) == 1.0

    def test_segment_1_decline_fast(self):
        """Band -20.0 to -10.0 -> 1.0 to 2.5."""
        assert compute_grw_score(-20.0) == pytest.approx(1.0)
        assert compute_grw_score(-15.0) == pytest.approx(1.75)
        assert compute_grw_score(-10.0) == pytest.approx(2.5)

    def test_segment_2_decline_moderate(self):
        """Band -10.0 to -1.0 -> 2.5 to 4.0."""
        assert compute_grw_score(-10.0) == pytest.approx(2.5)
        assert compute_grw_score(-5.5) == pytest.approx(3.25)
        assert compute_grw_score(-1.0) == pytest.approx(4.0)

    def test_segment_3_stable(self):
        """Band -1.0 to 1.0 -> 4.0 to 5.0."""
        assert compute_grw_score(-1.0) == pytest.approx(4.0)
        assert compute_grw_score(0.0) == pytest.approx(4.5)
        assert compute_grw_score(1.0) == pytest.approx(5.0)

    def test_segment_4_below_average_growth(self):
        """Band 1.0 to 5.0 -> 5.0 to 6.5."""
        assert compute_grw_score(1.0) == pytest.approx(5.0)
        assert compute_grw_score(3.0) == pytest.approx(5.75)
        assert compute_grw_score(5.0) == pytest.approx(6.5)

    def test_segment_5_above_average_growth(self):
        """Band 5.0 to 10.0 -> 6.5 to 7.5."""
        assert compute_grw_score(5.0) == pytest.approx(6.5)
        assert compute_grw_score(7.5) == pytest.approx(7.0)
        assert compute_grw_score(10.0) == pytest.approx(7.5)

    def test_segment_6_strong_growth(self):
        """Band 10.0 to 20.0 -> 7.5 to 9.0."""
        assert compute_grw_score(10.0) == pytest.approx(7.5)
        assert compute_grw_score(15.0) == pytest.approx(8.25)
        assert compute_grw_score(20.0) == pytest.approx(9.0)

    def test_segment_7_exceptional_growth(self):
        """Band >= 20.0 -> 9.0 to 10.0 (capped at 10.0 via 50.0 upper bound)."""
        assert compute_grw_score(20.0) == pytest.approx(9.0)
        assert compute_grw_score(35.0) == pytest.approx(9.5)
        assert compute_grw_score(50.0) == pytest.approx(10.0)

    def test_cap_at_10(self):
        """Values beyond 50% cap at 10.0."""
        assert compute_grw_score(60.0) == 10.0
        assert compute_grw_score(100.0) == 10.0

    def test_golden_software_developers(self):
        """15-1252: employment_change_pct=15.8 -> grw_score ~8.37."""
        result = compute_grw_score(15.8)
        # Band 10.0-20.0: 7.5 + (15.8-10.0)/10.0 * 1.5 = 7.5 + 0.87 = 8.37
        assert result == pytest.approx(8.37, abs=0.01)

    def test_golden_registered_nurses(self):
        """29-1141: employment_change_pct=4.9 -> grw_score ~6.46."""
        result = compute_grw_score(4.9)
        # Band 1.0-5.0: 5.0 + (4.9-1.0)/4.0 * 1.5 = 5.0 + 1.4625 = 6.4625
        assert result == pytest.approx(6.4625)

    def test_golden_anesthesiologists(self):
        """29-1211: employment_change_pct=3.2 -> grw_score ~5.825."""
        result = compute_grw_score(3.2)
        # Band 1.0-5.0: 5.0 + (3.2-1.0)/4.0 * 1.5 = 5.0 + 0.825 = 5.825
        assert result == pytest.approx(5.825)

    def test_extreme_negative(self):
        """pct=-36.1 -> capped at 1.0 (floor)."""
        assert compute_grw_score(-36.1) == 1.0

    def test_near_cap_positive(self):
        """pct=49.9 -> just under 10.0."""
        result = compute_grw_score(49.9)
        # 9.0 + (49.9-20.0)/30.0 * 1.0 = 9.0 + 0.997 = 9.997
        assert result == pytest.approx(9.997, abs=0.001)
        assert result < 10.0

    def test_boundary_continuity(self):
        """Score function is continuous at all breakpoints."""
        for pct_lo, pct_hi, score_lo, score_hi in GRW_BREAKPOINTS:
            assert compute_grw_score(pct_lo) == pytest.approx(score_lo)
            assert compute_grw_score(pct_hi) == pytest.approx(score_hi)


# ---------------------------------------------------------------------------
# Tests: Round Half Up
# ---------------------------------------------------------------------------


class TestRoundHalfUp:
    """Tests for _round_half_up matching DuckDB ROUND behavior."""

    def test_half_values_round_up(self):
        """DuckDB ROUND(2.5)=3, ROUND(4.5)=5, ROUND(6.5)=7, ROUND(7.5)=8."""
        assert _round_half_up(2.5) == 3
        assert _round_half_up(4.5) == 5
        assert _round_half_up(6.5) == 7
        assert _round_half_up(7.5) == 8

    def test_standard_rounding(self):
        assert _round_half_up(1.4) == 1
        assert _round_half_up(1.6) == 2
        assert _round_half_up(8.37) == 8
        assert _round_half_up(6.4625) == 6


# ---------------------------------------------------------------------------
# Tests: Market Score
# ---------------------------------------------------------------------------


class TestMarketScore:
    """Tests for market score computation."""

    def test_market_score_formula(self, multi_rows):
        """market_score = 0.6 * grw_score + 0.4 * openings_score."""
        result = derive_gold_rows(multi_rows)
        # All rows with both grw and openings should have market_score
        for row in result:
            if row["grw_score"] is not None and row["openings_annual_avg"] is not None:
                assert row["market_score"] is not None
                assert 1.0 <= row["market_score"] <= 10.0

    def test_market_score_null_when_grw_null(self):
        """Market score should be null when grw_score is null."""
        rows = [_make_silver_row(employment_change_pct=None)]
        result = derive_gold_rows(rows)
        assert result[0]["market_score"] is None
        assert result[0]["market_score_rounded"] is None

    def test_market_score_range(self, multi_rows):
        """All market scores should be between 1.0 and 10.0."""
        result = derive_gold_rows(multi_rows)
        for row in result:
            if row["market_score"] is not None:
                assert 1.0 <= row["market_score"] <= 10.0

    def test_market_score_rounded_consistency(self, multi_rows):
        """market_score_rounded should match _round_half_up(market_score)."""
        result = derive_gold_rows(multi_rows)
        for row in result:
            if row["market_score"] is not None:
                assert row["market_score_rounded"] == _round_half_up(row["market_score"])

    def test_high_openings_boosts_market_score(self):
        """An occupation with high openings should have higher market_score than
        one with same growth but low openings."""
        rows = [
            _make_silver_row(
                soc_code="99-0001",
                employment_change_pct=5.0,
                openings_annual_avg=500000,
                record_id="ooh-hi-open",
            ),
            _make_silver_row(
                soc_code="99-0002",
                employment_change_pct=5.0,
                openings_annual_avg=100,
                record_id="ooh-lo-open",
            ),
        ]
        result = derive_gold_rows(rows)
        hi = next(r for r in result if r["soc_code"] == "99-0001")
        lo = next(r for r in result if r["soc_code"] == "99-0002")
        assert hi["market_score"] > lo["market_score"]


# ---------------------------------------------------------------------------
# Tests: Wage Percentile Null Handling
# ---------------------------------------------------------------------------


class TestWagePercentileNullHandling:
    """Tests that null wages are excluded from PERCENT_RANK computation."""

    def test_null_wage_gets_null_percentile(self, multi_rows):
        """Occupations with null median_annual_wage should have null percentiles."""
        result = derive_gold_rows(multi_rows)
        null_wage_rows = [r for r in result if r["median_annual_wage"] is None]
        for row in null_wage_rows:
            assert row["wage_percentile_overall"] is None
            assert row["wage_percentile_education_tier"] is None
            assert row["wage_tier"] is None

    def test_non_null_wage_gets_valid_percentile(self, multi_rows):
        """Occupations with valid wages should have percentiles in [0, 1]."""
        result = derive_gold_rows(multi_rows)
        valid_wage_rows = [r for r in result if r["median_annual_wage"] is not None]
        for row in valid_wage_rows:
            assert row["wage_percentile_overall"] is not None
            assert 0.0 <= row["wage_percentile_overall"] <= 1.0

    def test_wage_percentile_excludes_nulls_from_ranking(self):
        """With 3 wage rows and 1 null-wage row, the lowest wage should have
        percentile 0.0 (not shifted by null participation)."""
        rows = [
            _make_silver_row(soc_code="99-0001", median_annual_wage=30000.0,
                             wage_available=True, record_id="r1"),
            _make_silver_row(soc_code="99-0002", median_annual_wage=60000.0,
                             wage_available=True, record_id="r2"),
            _make_silver_row(soc_code="99-0003", median_annual_wage=90000.0,
                             wage_available=True, record_id="r3"),
            _make_silver_row(soc_code="99-0004", median_annual_wage=None,
                             wage_available=False, record_id="r4"),
        ]
        result = derive_gold_rows(rows)
        low = next(r for r in result if r["soc_code"] == "99-0001")
        mid = next(r for r in result if r["soc_code"] == "99-0002")
        high = next(r for r in result if r["soc_code"] == "99-0003")
        null = next(r for r in result if r["soc_code"] == "99-0004")

        # Null should not participate in ranking
        assert null["wage_percentile_overall"] is None
        # With 3 rows, PERCENT_RANK gives 0.0, 0.5, 1.0
        assert low["wage_percentile_overall"] == pytest.approx(0.0)
        assert mid["wage_percentile_overall"] == pytest.approx(0.5)
        assert high["wage_percentile_overall"] == pytest.approx(1.0)

    def test_wage_percentile_education_tier_partitioned(self):
        """Wage percentile within education tier should partition by education_code."""
        rows = [
            # Education code 3: two occupations
            _make_silver_row(soc_code="99-0001", median_annual_wage=50000.0,
                             education_code=3, wage_available=True, record_id="r1"),
            _make_silver_row(soc_code="99-0002", median_annual_wage=100000.0,
                             education_code=3, wage_available=True, record_id="r2"),
            # Education code 7: two occupations
            _make_silver_row(soc_code="99-0003", median_annual_wage=30000.0,
                             education_code=7, wage_available=True, record_id="r3"),
            _make_silver_row(soc_code="99-0004", median_annual_wage=60000.0,
                             education_code=7, wage_available=True, record_id="r4"),
        ]
        result = derive_gold_rows(rows)
        # Within each education tier of 2, PERCENT_RANK gives 0.0 and 1.0
        r1 = next(r for r in result if r["soc_code"] == "99-0001")
        r2 = next(r for r in result if r["soc_code"] == "99-0002")
        assert r1["wage_percentile_education_tier"] == pytest.approx(0.0)
        assert r2["wage_percentile_education_tier"] == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# Tests: Wage Tier
# ---------------------------------------------------------------------------


class TestWageTier:
    """Tests for wage_tier bucketing."""

    def test_wage_tier_null_when_wage_null(self):
        rows = [_make_silver_row(median_annual_wage=None, wage_available=False)]
        result = derive_gold_rows(rows)
        assert result[0]["wage_tier"] is None

    def test_wage_tier_low(self):
        """Percentile < 0.25 -> low."""
        rows = [
            _make_silver_row(soc_code="99-0001", median_annual_wage=10000.0,
                             wage_available=True, record_id="r1"),
            _make_silver_row(soc_code="99-0002", median_annual_wage=20000.0,
                             wage_available=True, record_id="r2"),
            _make_silver_row(soc_code="99-0003", median_annual_wage=30000.0,
                             wage_available=True, record_id="r3"),
            _make_silver_row(soc_code="99-0004", median_annual_wage=40000.0,
                             wage_available=True, record_id="r4"),
            _make_silver_row(soc_code="99-0005", median_annual_wage=50000.0,
                             wage_available=True, record_id="r5"),
        ]
        result = derive_gold_rows(rows)
        lowest = next(r for r in result if r["soc_code"] == "99-0001")
        # PERCENT_RANK: 0.0 -> low
        assert lowest["wage_tier"] == "low"

    def test_wage_tier_very_high(self):
        """Percentile >= 0.90 -> very_high."""
        rows = [
            _make_silver_row(soc_code=f"99-{i:04d}", median_annual_wage=30000.0 + i * 10000,
                             wage_available=True, record_id=f"r{i}")
            for i in range(11)  # 11 rows to get PERCENT_RANK = 1.0 for top
        ]
        result = derive_gold_rows(rows)
        highest = next(r for r in result if r["soc_code"] == "99-0010")
        assert highest["wage_percentile_overall"] == pytest.approx(1.0)
        assert highest["wage_tier"] == "very_high"

    def test_all_valid_tier_values(self, multi_rows):
        """All non-null wage_tier values should be from the valid set."""
        result = derive_gold_rows(multi_rows)
        valid_tiers = {"low", "below_average", "above_average", "high", "very_high"}
        for row in result:
            if row["wage_tier"] is not None:
                assert row["wage_tier"] in valid_tiers


# ---------------------------------------------------------------------------
# Tests: Confidence Tier
# ---------------------------------------------------------------------------


class TestConfidenceTier:
    """Tests for confidence tier assignment."""

    def test_high_confidence(self):
        """Not broad, not catchall, has wage -> high."""
        rows = [_make_silver_row(
            broad_occupation_flag=False,
            catchall_flag=False,
            wage_available=True,
        )]
        result = derive_gold_rows(rows)
        assert result[0]["confidence_tier"] == "high"

    def test_low_confidence_no_wage(self):
        """wage_available=False -> low, regardless of broad/catchall."""
        rows = [_make_silver_row(
            broad_occupation_flag=False,
            catchall_flag=False,
            wage_available=False,
            median_annual_wage=None,
        )]
        result = derive_gold_rows(rows)
        assert result[0]["confidence_tier"] == "low"

    def test_medium_confidence_broad(self):
        """Broad occupation with wage -> medium."""
        rows = [_make_silver_row(
            broad_occupation_flag=True,
            catchall_flag=False,
            wage_available=True,
        )]
        result = derive_gold_rows(rows)
        assert result[0]["confidence_tier"] == "medium"

    def test_medium_confidence_catchall(self):
        """Catchall occupation with wage -> medium."""
        rows = [_make_silver_row(
            broad_occupation_flag=False,
            catchall_flag=True,
            wage_available=True,
        )]
        result = derive_gold_rows(rows)
        assert result[0]["confidence_tier"] == "medium"

    def test_low_takes_priority_over_catchall(self):
        """wage_available=False + catchall=True -> low (not medium).
        This is the 3-occupation edge case from EDA (27-2099, 29-1229, 29-1249)."""
        rows = [_make_silver_row(
            broad_occupation_flag=False,
            catchall_flag=True,
            wage_available=False,
            median_annual_wage=None,
        )]
        result = derive_gold_rows(rows)
        assert result[0]["confidence_tier"] == "low"

    def test_low_takes_priority_over_broad(self):
        """wage_available=False + broad=True -> low (not medium)."""
        rows = [_make_silver_row(
            broad_occupation_flag=True,
            catchall_flag=False,
            wage_available=False,
            median_annual_wage=None,
        )]
        result = derive_gold_rows(rows)
        assert result[0]["confidence_tier"] == "low"

    def test_confidence_tier_never_null(self, multi_rows):
        """Every row must have a confidence tier."""
        result = derive_gold_rows(multi_rows)
        for row in result:
            assert row["confidence_tier"] in ("high", "medium", "low")


# ---------------------------------------------------------------------------
# Tests: Data Completeness
# ---------------------------------------------------------------------------


class TestDataCompleteness:
    """Tests for data_completeness derivation."""

    def test_all_core_fields_present(self):
        """All 4 core fields non-null -> 1.0."""
        rows = [_make_silver_row()]
        result = derive_gold_rows(rows)
        assert result[0]["data_completeness"] == pytest.approx(1.0)

    def test_wage_null_gives_075(self):
        """3 of 4 core fields non-null -> 0.75."""
        rows = [_make_silver_row(median_annual_wage=None, wage_available=False)]
        result = derive_gold_rows(rows)
        assert result[0]["data_completeness"] == pytest.approx(0.75)

    def test_two_fields_null_gives_050(self):
        """2 of 4 core fields non-null -> 0.50."""
        rows = [_make_silver_row(
            median_annual_wage=None, wage_available=False,
            employment_current=None,
        )]
        result = derive_gold_rows(rows)
        assert result[0]["data_completeness"] == pytest.approx(0.50)

    def test_one_field_present_gives_025(self):
        """1 of 4 core fields non-null -> 0.25."""
        rows = [_make_silver_row(
            median_annual_wage=None, wage_available=False,
            employment_current=None,
            employment_change_pct=None,
        )]
        result = derive_gold_rows(rows)
        assert result[0]["data_completeness"] == pytest.approx(0.25)

    def test_all_null_gives_000(self):
        """All 4 core fields null -> 0.0."""
        rows = [_make_silver_row(
            median_annual_wage=None, wage_available=False,
            employment_current=None,
            employment_change_pct=None,
            openings_annual_avg=None,
        )]
        result = derive_gold_rows(rows)
        assert result[0]["data_completeness"] == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Tests: Static Fields
# ---------------------------------------------------------------------------


class TestStaticFields:
    """Tests for FutureProof stat mapping static fields."""

    def test_backs_stats_all_rows(self, multi_rows):
        result = derive_gold_rows(multi_rows)
        for row in result:
            assert row["backs_stats"] == "ERN,GRW"

    def test_backs_bosses_all_rows(self, multi_rows):
        result = derive_gold_rows(multi_rows)
        for row in result:
            assert row["backs_bosses"] == "Market,Ceiling"


# ---------------------------------------------------------------------------
# Tests: Record ID and Grain
# ---------------------------------------------------------------------------


class TestRecordIdAndGrain:
    """Tests for deterministic record_id computation."""

    def test_record_id_prefix(self, single_row):
        result = derive_gold_rows(single_row)
        promoted_at = datetime.datetime(2026, 4, 7, 0, 0, 0)
        add_record_ids(result, promoted_at)
        assert result[0]["record_id"].startswith("op-")

    def test_record_id_deterministic(self, single_row):
        result1 = derive_gold_rows(single_row)
        result2 = derive_gold_rows(single_row)
        ts = datetime.datetime(2026, 4, 7, 0, 0, 0)
        add_record_ids(result1, ts)
        add_record_ids(result2, ts)
        assert result1[0]["record_id"] == result2[0]["record_id"]

    def test_record_id_changes_with_soc_code(self):
        rows1 = [_make_silver_row(soc_code="15-1252")]
        rows2 = [_make_silver_row(soc_code="29-1141")]
        result1 = derive_gold_rows(rows1)
        result2 = derive_gold_rows(rows2)
        ts = datetime.datetime(2026, 4, 7, 0, 0, 0)
        add_record_ids(result1, ts)
        add_record_ids(result2, ts)
        assert result1[0]["record_id"] != result2[0]["record_id"]

    def test_grain_uniqueness(self, multi_rows):
        result = derive_gold_rows(multi_rows)
        ts = datetime.datetime(2026, 4, 7, 0, 0, 0)
        add_record_ids(result, ts)
        record_ids = [r["record_id"] for r in result]
        assert len(record_ids) == len(set(record_ids))

    def test_promoted_at_added(self, single_row):
        result = derive_gold_rows(single_row)
        ts = datetime.datetime(2026, 4, 7, 12, 0, 0, tzinfo=datetime.timezone.utc)
        add_record_ids(result, ts)
        assert result[0]["promoted_at"] == ts

    def test_grain_uses_soc_code_key(self):
        """Verify the grain hash uses soc_code per spec."""
        grain_row = {"soc_code": "15-1252"}
        expected = compute_grain_id(grain_row, GRAIN_FIELDS, prefix=GRAIN_PREFIX)

        rows = [_make_silver_row(soc_code="15-1252")]
        result = derive_gold_rows(rows)
        ts = datetime.datetime(2026, 4, 7, 0, 0, 0)
        add_record_ids(result, ts)
        assert result[0]["record_id"] == expected


# ---------------------------------------------------------------------------
# Tests: Schema
# ---------------------------------------------------------------------------


class TestGoldSchema:
    """Tests for the Gold Iceberg schema definition."""

    def test_schema_field_count(self):
        schema = get_gold_schema()
        assert len(schema.fields) == 31

    def test_required_fields(self):
        schema = get_gold_schema()
        required = {f.name for f in schema.fields if f.required}
        expected_required = {
            "record_id", "soc_code", "occupation_title",
            "soc_major_group", "soc_major_group_name",
            "broad_occupation_flag", "catchall_flag",
            "growth_category", "wage_available",
            "confidence_tier", "data_completeness",
            "backs_stats", "backs_bosses",
            "source_load_date", "promoted_at",
        }
        assert expected_required == required

    def test_nullable_fields(self):
        schema = get_gold_schema()
        nullable = {f.name for f in schema.fields if not f.required}
        expected_nullable = {
            "employment_current", "employment_projected",
            "employment_change_pct", "openings_annual_avg",
            "grw_score", "grw_score_rounded",
            "median_annual_wage",
            "wage_percentile_overall", "wage_percentile_education_tier",
            "wage_tier",
            "education_code", "education_level_name",
            "work_experience_code", "training_code",
            "market_score", "market_score_rounded",
        }
        assert expected_nullable == nullable


# ---------------------------------------------------------------------------
# Tests: Dropped Fields
# ---------------------------------------------------------------------------


class TestDroppedFields:
    """Tests that Silver-only fields are not in Gold output."""

    def test_dropped_fields_not_in_output(self, single_row):
        result = derive_gold_rows(single_row)
        row = result[0]
        # These fields should be dropped in Gold
        assert "employment_change" not in row
        assert "median_wage_capped" not in row
        assert "education_typical" not in row
        assert "work_experience" not in row
        assert "training_typical" not in row
        assert "ingested_at" not in row


# ---------------------------------------------------------------------------
# Tests: End-to-End Transform
# ---------------------------------------------------------------------------


class TestEndToEnd:
    """End-to-end tests with multi-row sample data."""

    def test_row_count_preserved(self, multi_rows):
        result = derive_gold_rows(multi_rows)
        assert len(result) == len(multi_rows)

    def test_empty_input_returns_empty(self):
        result = derive_gold_rows([])
        assert result == []

    def test_all_fields_present(self, multi_rows):
        """All Gold schema fields should be present in output rows."""
        result = derive_gold_rows(multi_rows)
        ts = datetime.datetime(2026, 4, 7, 0, 0, 0)
        add_record_ids(result, ts)
        expected_fields = {f.name for f in get_gold_schema().fields}
        for row in result:
            row_fields = set(row.keys())
            missing = expected_fields - row_fields
            assert not missing, f"Missing fields: {missing}"

    def test_software_developers_golden_chain(self, multi_rows):
        """Full verification chain for Software Developers (15-1252)."""
        result = derive_gold_rows(multi_rows)
        sd = next(r for r in result if r["soc_code"] == "15-1252")

        # GRW score: pct=15.8, band 10-20: 7.5 + (15.8-10)/10 * 1.5 = 8.37
        assert sd["grw_score"] == pytest.approx(8.37, abs=0.01)
        assert sd["grw_score_rounded"] == 8

        # Wage available
        assert sd["wage_available"] is True
        assert sd["median_annual_wage"] == 133080.0

        # Wage percentile: highest wage in dataset -> 1.0
        assert sd["wage_percentile_overall"] is not None
        assert sd["wage_tier"] in ("high", "very_high")

        # Confidence: not broad, not catchall, has wage
        assert sd["confidence_tier"] == "high"

        # Data completeness: all 4 core fields present
        assert sd["data_completeness"] == pytest.approx(1.0)

        # Market score computed
        assert sd["market_score"] is not None
        assert 1.0 <= sd["market_score"] <= 10.0

    def test_anesthesiologists_golden_chain(self, multi_rows):
        """Full verification chain for Anesthesiologists (29-1211) - null wage case."""
        result = derive_gold_rows(multi_rows)
        anes = next(r for r in result if r["soc_code"] == "29-1211")

        # GRW score: pct=3.2, band 1-5: 5.0 + (3.2-1.0)/4.0 * 1.5 = 5.825
        assert anes["grw_score"] == pytest.approx(5.825)
        assert anes["grw_score_rounded"] == 6

        # Null wage fields
        assert anes["median_annual_wage"] is None
        assert anes["wage_available"] is False
        assert anes["wage_percentile_overall"] is None
        assert anes["wage_percentile_education_tier"] is None
        assert anes["wage_tier"] is None

        # Confidence: no wage -> low
        assert anes["confidence_tier"] == "low"

        # Data completeness: 3/4 (missing wage)
        assert anes["data_completeness"] == pytest.approx(0.75)

        # Market score should still compute (has employment data)
        assert anes["market_score"] is not None

    def test_catchall_null_wage_golden_chain(self, multi_rows):
        """Verify catchall + null wage -> low confidence (not medium)."""
        result = derive_gold_rows(multi_rows)
        catch = next(r for r in result if r["soc_code"] == "29-1229")

        assert catch["catchall_flag"] is True
        assert catch["wage_available"] is False
        assert catch["confidence_tier"] == "low"  # Not medium!

    def test_broad_with_wage_is_medium(self, multi_rows):
        """Broad occupation with wage data -> medium confidence."""
        result = derive_gold_rows(multi_rows)
        broad = next(r for r in result if r["soc_code"] == "31-1120")

        assert broad["broad_occupation_flag"] is True
        assert broad["wage_available"] is True
        assert broad["confidence_tier"] == "medium"

    def test_sorted_by_soc_code(self, multi_rows):
        """Output should be sorted by soc_code ASC."""
        result = derive_gold_rows(multi_rows)
        soc_codes = [r["soc_code"] for r in result]
        assert soc_codes == sorted(soc_codes)
