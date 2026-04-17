"""Tests for the Silver base.onet_experience_profiles transformer.

Covers all 7 cases from spec §Test Matrix (weighted-median edge cases) plus
tier-boundary corners and referential-integrity behavior.
"""

from __future__ import annotations

import datetime
import json

from silver.onet_experience_transformer import (
    CATEGORY_MIDPOINT_YEARS,
    MAX_RW_CATEGORY,
    MIN_RW_CATEGORY,
    RW_ELEMENT_ID,
    RW_SCALE_ID,
    SPEC_NAME,
    _argmax_category,
    _derive_onet_detail,
    _group_rw_rows_by_onet_soc,
    _normalize_distribution,
    derive_experience_tier,
    get_experience_profiles_schema,
    transform_experience_profiles,
    truncate_to_bls_soc,
    weighted_median_category,
)

NOW = datetime.datetime(2026, 4, 16, 12, 0, 0, tzinfo=datetime.timezone.utc)
LOAD_DATE = datetime.date(2026, 4, 16)
EARLIER_LOAD_DATE = datetime.date(2025, 8, 1)


# ---------------------------------------------------------------------------
# Fixture factories
# ---------------------------------------------------------------------------

def make_rw_row(
    onet_soc: str,
    category: int,
    data_value: float,
    *,
    recommend_suppress: str = "N",
    load_date: datetime.date = LOAD_DATE,
    scale_id: str = RW_SCALE_ID,
    element_id: str = RW_ELEMENT_ID,
) -> dict:
    """Minimal raw.onet_experience row passing the RW filter by default."""
    return {
        "onet_soc_code": onet_soc,
        "element_id": element_id,
        "element_name": "Related Work Experience",
        "scale_id": scale_id,
        "category": category,
        "data_value": data_value,
        "recommend_suppress": recommend_suppress,
        "load_date": load_date,
    }


def make_distribution_rows(
    onet_soc: str,
    pct_by_cat: dict[int, float],
    *,
    recommend_suppress: str = "N",
    load_date: datetime.date = LOAD_DATE,
) -> list[dict]:
    """Emit 11 RW rows (one per category), backfilling zeros."""
    rows = []
    for cat in range(MIN_RW_CATEGORY, MAX_RW_CATEGORY + 1):
        rows.append(
            make_rw_row(
                onet_soc,
                cat,
                pct_by_cat.get(cat, 0.0),
                recommend_suppress=recommend_suppress,
                load_date=load_date,
            )
        )
    return rows


# ---------------------------------------------------------------------------
# Constants & small helpers
# ---------------------------------------------------------------------------

class TestConstants:

    def test_midpoint_table_covers_11_categories(self):
        assert set(CATEGORY_MIDPOINT_YEARS.keys()) == set(range(1, 12))

    def test_midpoint_category_11_is_12_years(self):
        # Human-approved Decision 2 in the open-decisions approval file.
        assert CATEGORY_MIDPOINT_YEARS[11] == 12.0

    def test_midpoint_categories_1_and_2_are_zero(self):
        assert CATEGORY_MIDPOINT_YEARS[1] == 0.0
        assert CATEGORY_MIDPOINT_YEARS[2] == 0.0

    def test_spec_name(self):
        assert SPEC_NAME == "silver-base-onet-experience"

    def test_rw_filter_constants(self):
        assert RW_SCALE_ID == "RW"
        assert RW_ELEMENT_ID == "3.A.1"

    def test_schema_has_11_fields(self):
        schema = get_experience_profiles_schema()
        assert len(schema.fields) == 11
        # All fields are required (NOT NULL)
        assert all(f.required for f in schema.fields)


class TestTruncateToBLSSOC:

    def test_standard_detail(self):
        assert truncate_to_bls_soc("15-1252.00") == "15-1252"

    def test_nonzero_detail(self):
        assert truncate_to_bls_soc("15-1252.01") == "15-1252"

    def test_no_dot_returns_as_is(self):
        assert truncate_to_bls_soc("15-1252") == "15-1252"


# ---------------------------------------------------------------------------
# Weighted median
# ---------------------------------------------------------------------------

class TestWeightedMedian:

    def test_empty_returns_none(self):
        # §Test Matrix case 1 — empty distribution
        assert weighted_median_category({}) is None

    def test_all_zero_returns_none(self):
        assert weighted_median_category({c: 0.0 for c in range(1, 12)}) is None

    def test_single_category_100pct(self):
        # §Test Matrix case 2 — single category at 100%
        assert weighted_median_category({7: 100.0}) == 7

    def test_single_category_at_cat_11(self):
        assert weighted_median_category({11: 100.0}) == 11

    def test_chief_exec_senior_heavy(self):
        # Real EDA distribution for 11-1011 Chief Executives
        dist = {7: 9.69, 8: 5.87, 9: 15.09, 10: 1.11, 11: 68.24}
        assert weighted_median_category(dist) == 11

    def test_software_devs_category_9(self):
        # Real EDA distribution for 15-1252 Software Developers
        dist = {1: 4.42, 6: 11.13, 7: 7.13, 8: 15.04, 9: 43.91, 10: 7.82, 11: 10.55}
        assert weighted_median_category(dist) == 9

    def test_retail_salespersons_bimodal(self):
        # Real EDA distribution for 41-2031 Retail Salespersons — bimodal!
        # Cumulative walk: 39.75 / 40.40 / 43.37 / 43.37 / 75.39 → crosses 50 at cat 5
        dist = {
            1: 39.75, 2: 0.65, 3: 2.97, 4: 0.0, 5: 32.02,
            6: 7.29, 7: 6.87, 8: 0.65, 9: 0.0, 10: 9.79, 11: 0.0,
        }
        assert weighted_median_category(dist) == 5

    def test_tie_at_50pct_picks_lower(self):
        # §Test Matrix case 4 — cumulative lands exactly on boundary.
        # 50% at cat 3, 50% at cat 8 → median must be cat 3 (LOWER).
        dist = {3: 50.0, 8: 50.0}
        assert weighted_median_category(dist) == 3

    def test_tie_at_50pct_three_buckets(self):
        # 30 + 20 at cat 4 hits 50 exactly, then 50 more at cat 10.
        dist = {1: 30.0, 4: 20.0, 10: 50.0}
        assert weighted_median_category(dist) == 4

    def test_crossing_just_past_50(self):
        # 49.9 at cat 2, then 0.2 at cat 3 → median is cat 3
        dist = {2: 49.9, 3: 0.2, 5: 49.9}
        assert weighted_median_category(dist) == 3

    def test_sums_less_than_100_ok(self):
        # EDA reports groups sum to 100±0.03 — still deterministic at any total.
        dist = {5: 20.0, 6: 20.0, 7: 20.0}  # total = 60 → half = 30
        # cumulative: 20 @ 5, 40 @ 6 — 40 >= 30 → median = 6
        assert weighted_median_category(dist) == 6


# ---------------------------------------------------------------------------
# Tier derivation (boundary corners)
# ---------------------------------------------------------------------------

class TestTierBoundaries:

    def test_zero_years_entry(self):
        assert derive_experience_tier(0.0) == "entry"

    def test_exactly_one_year_is_entry(self):
        # Boundary: 1.0 → entry (0-1 inclusive)
        assert derive_experience_tier(1.0) == "entry"

    def test_just_above_one_is_early(self):
        assert derive_experience_tier(1.01) == "early"

    def test_exactly_four_is_early(self):
        # Boundary: 4.0 → early (1-4 inclusive)
        assert derive_experience_tier(4.0) == "early"

    def test_just_above_four_is_mid(self):
        assert derive_experience_tier(4.01) == "mid"

    def test_exactly_eight_is_mid(self):
        # Boundary: 8.0 → mid (4-8 inclusive)
        assert derive_experience_tier(8.0) == "mid"

    def test_just_above_eight_is_senior(self):
        assert derive_experience_tier(8.01) == "senior"

    def test_twelve_years_senior(self):
        # Category 11 midpoint
        assert derive_experience_tier(12.0) == "senior"


# ---------------------------------------------------------------------------
# Grouping / filtering
# ---------------------------------------------------------------------------

class TestGroupRWRows:

    def test_filters_non_rw_scales(self):
        rows = [
            make_rw_row("11-1011.00", 11, 68.24, scale_id="RL"),  # filtered out
            make_rw_row("11-1011.00", 11, 68.24, element_id="2.D.1"),  # filtered
            make_rw_row("11-1011.00", 11, 68.24),  # kept
        ]
        grouped = _group_rw_rows_by_onet_soc(rows)
        assert "11-1011.00" in grouped
        assert grouped["11-1011.00"]["distribution"][11] == 68.24

    def test_suppress_or_logic(self):
        rows = [
            make_rw_row("15-1252.00", 9, 43.91, recommend_suppress="N"),
            make_rw_row("15-1252.00", 11, 10.55, recommend_suppress="Y"),
        ]
        grouped = _group_rw_rows_by_onet_soc(rows)
        assert grouped["15-1252.00"]["suppress"] is True

    def test_no_suppress(self):
        rows = [
            make_rw_row("15-1252.00", 9, 43.91, recommend_suppress="N"),
            make_rw_row("15-1252.00", 11, 10.55, recommend_suppress="n/a"),
        ]
        grouped = _group_rw_rows_by_onet_soc(rows)
        assert grouped["15-1252.00"]["suppress"] is False

    def test_invalid_category_dropped(self):
        rows = [
            make_rw_row("15-1252.00", 9, 43.91),
            make_rw_row("15-1252.00", 99, 10.0),  # out of range
            make_rw_row("15-1252.00", 0, 5.0),  # out of range
        ]
        grouped = _group_rw_rows_by_onet_soc(rows)
        # Out-of-range categories never reach the distribution
        dist = grouped["15-1252.00"]["distribution"]
        assert dist[9] == 43.91
        assert 99 not in dist
        assert 0 not in dist


# ---------------------------------------------------------------------------
# Detail derivation
# ---------------------------------------------------------------------------

class TestDeriveOnetDetail:

    def test_all_suppressed_still_produces_detail(self):
        # §Test Matrix case 3 — all suppressed rows. The detail is still
        # produced (so downstream can decide what to do); suppress_flag=True
        # marks it.
        dist = {7: 100.0}
        detail = _derive_onet_detail(dist, suppress=True, load_date=LOAD_DATE)
        assert detail is not None
        assert detail["suppress"] is True
        assert detail["median_category"] == 7

    def test_empty_distribution_returns_none(self):
        detail = _derive_onet_detail({}, suppress=False, load_date=LOAD_DATE)
        assert detail is None

    def test_all_zero_weights_returns_none(self):
        detail = _derive_onet_detail(
            {c: 0.0 for c in range(1, 12)}, suppress=False, load_date=LOAD_DATE
        )
        assert detail is None


# ---------------------------------------------------------------------------
# End-to-end transformation
# ---------------------------------------------------------------------------

class TestTransformExperienceProfiles:

    def test_empty_input(self):
        assert transform_experience_profiles([], None, NOW) == []

    def test_empty_distribution_case_skipped(self):
        # §Test Matrix case 1 — an O*NET-SOC with no RW rows disappears.
        rows = [
            # Only non-RW rows — should be filtered out, yielding no output.
            make_rw_row("11-1011.00", 11, 68.24, scale_id="RL"),
        ]
        assert transform_experience_profiles(rows, None, NOW) == []

    def test_single_category_100pct(self):
        # §Test Matrix case 2
        rows = make_distribution_rows("11-1011.00", {11: 100.0})
        result = transform_experience_profiles(rows, None, NOW)
        assert len(result) == 1
        r = result[0]
        assert r["bls_soc_code"] == "11-1011"
        assert r["experience_category_median"] == 11
        assert r["experience_years_typical"] == 12.0
        assert r["experience_tier"] == "senior"
        assert r["experience_category_mode"] == 11
        assert r["onet_details_averaged"] == 1
        assert r["suppress_flag"] is False
        # All 11 categories appear in the JSON
        parsed = json.loads(r["experience_distribution"])
        assert set(parsed.keys()) == {str(c) for c in range(1, 12)}
        assert parsed["11"] == 100.0

    def test_all_suppressed_produces_row_with_flag(self):
        # §Test Matrix case 3 — all contributing rows flagged Y.
        rows = make_distribution_rows(
            "99-9999.00", {7: 100.0}, recommend_suppress="Y"
        )
        result = transform_experience_profiles(rows, None, NOW)
        assert len(result) == 1
        assert result[0]["suppress_flag"] is True
        assert result[0]["experience_tier"] == "early"

    def test_tie_at_50_picks_lower(self):
        # §Test Matrix case 4 — boundary tie
        rows = make_distribution_rows("99-9999.00", {3: 50.0, 8: 50.0})
        result = transform_experience_profiles(rows, None, NOW)
        assert len(result) == 1
        r = result[0]
        assert r["experience_category_median"] == 3
        assert r["experience_years_typical"] == CATEGORY_MIDPOINT_YEARS[3]  # 0.17
        assert r["experience_tier"] == "entry"

    def test_multi_detail_aggregation(self):
        # §Test Matrix case 5 — 15-1252.00 + 15-1252.01 both present
        # Detail .00 → cat 9 median (years=7, tier=mid)
        # Detail .01 → cat 7 median (years=3, tier=early)
        # Unweighted-mean years = (7 + 3) / 2 = 5.0 → tier=mid
        rows = (
            make_distribution_rows("15-1252.00", {9: 100.0})
            + make_distribution_rows("15-1252.01", {7: 100.0})
        )
        result = transform_experience_profiles(rows, None, NOW)
        assert len(result) == 1
        r = result[0]
        assert r["bls_soc_code"] == "15-1252"
        assert r["onet_details_averaged"] == 2
        assert r["experience_years_typical"] == 5.0
        assert r["experience_tier"] == "mid"
        # Merged dist is avg across details: cat 7 = 50, cat 9 = 50 → tie → 7
        assert r["experience_category_median"] == 7
        parsed = json.loads(r["experience_distribution"])
        assert parsed["7"] == 50.0
        assert parsed["9"] == 50.0

    def test_spot_check_11_1011_senior(self):
        # §Test Matrix case 7a — Chief Executives.
        # Real Silver row averages two O*NET details (.00 cat-11 and .03 cat-8),
        # producing experience_years_typical=8.5, tier=senior. This test uses a
        # single-detail fixture (.00 only), yielding years=12.0 / tier=senior.
        # Both fixture shape and real production shape must resolve to senior.
        dist = {
            1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0, 5: 0.0, 6: 0.0,
            7: 9.69, 8: 5.87, 9: 15.09, 10: 1.11, 11: 68.24,
        }
        rows = make_distribution_rows("11-1011.00", dist)
        result = transform_experience_profiles(rows, None, NOW)
        assert len(result) == 1
        r = result[0]
        assert r["bls_soc_code"] == "11-1011"
        assert r["experience_category_median"] == 11
        assert r["experience_years_typical"] == 12.0  # single-detail fixture
        assert r["experience_tier"] == "senior"
        assert r["onet_details_averaged"] == 1

    def test_spot_check_15_1252_mid(self):
        # §Test Matrix case 7b — Software Developers
        dist = {
            1: 4.42, 6: 11.13, 7: 7.13, 8: 15.04, 9: 43.91, 10: 7.82, 11: 10.55,
        }
        rows = make_distribution_rows("15-1252.00", dist)
        result = transform_experience_profiles(rows, None, NOW)
        assert len(result) == 1
        r = result[0]
        assert r["bls_soc_code"] == "15-1252"
        assert r["experience_category_median"] == 9
        assert r["experience_years_typical"] == 7.0
        assert r["experience_tier"] == "mid"

    def test_spot_check_41_2031_bimodal_entry(self):
        # §Test Matrix case 7c — Retail Salespersons (bimodal!)
        # Weighted median = 5 (not 1-3 despite the cat 1 mode).
        dist = {
            1: 39.75, 2: 0.65, 3: 2.97, 4: 0.0, 5: 32.02,
            6: 7.29, 7: 6.87, 8: 0.65, 9: 0.0, 10: 9.79, 11: 0.0,
        }
        rows = make_distribution_rows("41-2031.00", dist)
        result = transform_experience_profiles(rows, None, NOW)
        assert len(result) == 1
        r = result[0]
        assert r["bls_soc_code"] == "41-2031"
        assert r["experience_category_median"] == 5
        assert r["experience_years_typical"] == 0.75
        assert r["experience_tier"] == "entry"
        # Mode is cat 1 — distinct from median, which is the whole point of
        # tracking both.
        assert r["experience_category_mode"] == 1

    def test_record_id_deterministic(self):
        rows = make_distribution_rows("11-1011.00", {11: 100.0})
        r1 = transform_experience_profiles(rows, None, NOW)[0]
        r2 = transform_experience_profiles(rows, None, NOW)[0]
        assert r1["record_id"] == r2["record_id"]
        assert r1["record_id"].startswith("exp-")

    def test_record_id_uniqueness_across_socs(self):
        rows = (
            make_distribution_rows("11-1011.00", {11: 100.0})
            + make_distribution_rows("15-1252.00", {9: 100.0})
        )
        result = transform_experience_profiles(rows, None, NOW)
        ids = [r["record_id"] for r in result]
        assert len(set(ids)) == len(ids)

    def test_ingested_at_populated(self):
        rows = make_distribution_rows("11-1011.00", {11: 100.0})
        r = transform_experience_profiles(rows, None, NOW)[0]
        assert r["ingested_at"] == NOW

    def test_source_load_date_earliest_wins(self):
        # If a multi-detail has differing load_dates, the MIN is kept
        rows = (
            make_distribution_rows(
                "15-1252.00", {9: 100.0}, load_date=LOAD_DATE
            )
            + make_distribution_rows(
                "15-1252.01", {7: 100.0}, load_date=EARLIER_LOAD_DATE
            )
        )
        r = transform_experience_profiles(rows, None, NOW)[0]
        assert r["source_load_date"] == EARLIER_LOAD_DATE


# ---------------------------------------------------------------------------
# Referential integrity (FK to base.onet_occupations)
# ---------------------------------------------------------------------------

class TestReferentialIntegrity:

    def test_no_filter_when_none(self):
        # valid_bls_socs=None should NOT error; all rows pass.
        rows = (
            make_distribution_rows("11-1011.00", {11: 100.0})
            + make_distribution_rows("99-9999.00", {1: 100.0})
        )
        result = transform_experience_profiles(rows, None, NOW)
        assert {r["bls_soc_code"] for r in result} == {"11-1011", "99-9999"}

    def test_filter_drops_missing(self):
        # LEFT JOIN semantics: BLS SOC not in occupations table is silently dropped.
        rows = (
            make_distribution_rows("11-1011.00", {11: 100.0})
            + make_distribution_rows("99-9999.00", {1: 100.0})
        )
        result = transform_experience_profiles(rows, {"11-1011"}, NOW)
        assert len(result) == 1
        assert result[0]["bls_soc_code"] == "11-1011"

    def test_filter_empty_set_drops_all(self):
        # Never errors on empty valid set — just returns nothing.
        rows = make_distribution_rows("11-1011.00", {11: 100.0})
        result = transform_experience_profiles(rows, set(), NOW)
        assert result == []


# ---------------------------------------------------------------------------
# Distribution JSON normalization
# ---------------------------------------------------------------------------

class TestDistributionJSON:

    def test_all_categories_present(self):
        norm = _normalize_distribution({7: 100.0})
        assert set(norm.keys()) == {str(c) for c in range(1, 12)}
        assert norm["7"] == 100.0
        assert norm["1"] == 0.0

    def test_rounds_to_4dp(self):
        norm = _normalize_distribution({3: 12.345678})
        assert norm["3"] == 12.3457


# ---------------------------------------------------------------------------
# Mode / argmax
# ---------------------------------------------------------------------------

class TestArgmax:

    def test_single_peak(self):
        assert _argmax_category({7: 50.0, 3: 10.0}) == 7

    def test_tie_goes_to_lower(self):
        # 50 at cat 3 and cat 7 — lower wins
        assert _argmax_category({3: 50.0, 7: 50.0}) == 3
