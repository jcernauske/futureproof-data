"""Tests for the Gold zone regional price parities transformer.

Covers:
  - classify_cost_tier: all 5 buckets + all 4 boundary values (left-closed)
  - compute_adjusted_salary: each anchor ($30K/$50K/$75K/$100K) + rounding
  - derive_gold_rows: passthrough + derivations, ordering, empty input
  - add_record_ids: prefix='rpc', determinism, distinct state_fips
  - Schema: 15 columns, correct order, all required
  - Integration: seed temp Silver warehouse with 51 rows, run transform,
    verify row/column counts, distributions, spot checks, idempotency
"""

from __future__ import annotations

import datetime
from pathlib import Path

import pytest
from pyiceberg.schema import Schema
from pyiceberg.types import (
    DateType,
    DoubleType,
    IntegerType,
    NestedField,
    StringType,
    TimestampType,
)

from brightsmith.infra.grain import compute_grain_id
from gold._cost_tier import COST_TIER_BREAKPOINTS, CostTier, classify_cost_tier
from gold.regional_price_parities_transformer import (
    GRAIN_FIELDS,
    GRAIN_PREFIX,
    SALARY_ANCHORS,
    SILVER_PASSTHROUGH_FIELDS,
    add_record_ids,
    compute_adjusted_salary,
    derive_gold_rows,
    get_gold_schema,
    transform,
)


# ---------------------------------------------------------------------------
# Shared fixture data
# ---------------------------------------------------------------------------

INGESTED_AT = datetime.datetime(2026, 4, 11, 12, 0, 0, tzinfo=datetime.timezone.utc)
LOAD_DATE = datetime.date(2026, 4, 11)

# The 8 BEA-verified states with exact spec values.
VERIFIED_RPP: dict[str, float] = {
    "06": 110.7,  # CA very_high
    "15": 110.0,  # HI very_high
    "11": 109.9,  # DC very_high
    "34": 108.8,  # NJ very_high
    "05": 86.9,   # AR very_low
    "28": 87.0,   # MS very_low
    "19": 87.8,   # IA very_low
    "40": 87.8,   # OK very_low
}

BEA_VERIFIED_FIPS = frozenset(VERIFIED_RPP.keys())

# Per-census-region baseline RPPs for the 43 estimate rows. These are
# chosen to materialize all 5 cost tiers so the integration test can
# check the distribution observed in the EDA (very_high=4, high=8,
# average=13, low=11, very_low=15). We don't need exact BEA values
# here — the estimate rows just need to produce plausible rpp values
# that land in each bucket in the expected proportions.
#
# The EDA distribution assumes the real Silver data. For tests, we use
# a controlled fixture and verify whatever distribution it produces.
ESTIMATE_RPP_BY_REGION: dict[str, float] = {
    "Northeast": 105.0,  # -> high
    "Midwest": 95.0,     # -> low
    "South": 93.0,       # -> low
    "West": 102.0,       # -> average
}

FIPS_TO_STATE_NAME: dict[str, str] = {
    "01": "Alabama", "02": "Alaska", "04": "Arizona", "05": "Arkansas",
    "06": "California", "08": "Colorado", "09": "Connecticut", "10": "Delaware",
    "11": "District of Columbia", "12": "Florida", "13": "Georgia",
    "15": "Hawaii", "16": "Idaho", "17": "Illinois", "18": "Indiana",
    "19": "Iowa", "20": "Kansas", "21": "Kentucky", "22": "Louisiana",
    "23": "Maine", "24": "Maryland", "25": "Massachusetts", "26": "Michigan",
    "27": "Minnesota", "28": "Mississippi", "29": "Missouri", "30": "Montana",
    "31": "Nebraska", "32": "Nevada", "33": "New Hampshire", "34": "New Jersey",
    "35": "New Mexico", "36": "New York", "37": "North Carolina",
    "38": "North Dakota", "39": "Ohio", "40": "Oklahoma", "41": "Oregon",
    "42": "Pennsylvania", "44": "Rhode Island", "45": "South Carolina",
    "46": "South Dakota", "47": "Tennessee", "48": "Texas", "49": "Utah",
    "50": "Vermont", "51": "Virginia", "53": "Washington", "54": "West Virginia",
    "55": "Wisconsin", "56": "Wyoming",
}

FIPS_TO_USPS: dict[str, str] = {
    "01": "AL", "02": "AK", "04": "AZ", "05": "AR", "06": "CA", "08": "CO",
    "09": "CT", "10": "DE", "11": "DC", "12": "FL", "13": "GA", "15": "HI",
    "16": "ID", "17": "IL", "18": "IN", "19": "IA", "20": "KS", "21": "KY",
    "22": "LA", "23": "ME", "24": "MD", "25": "MA", "26": "MI", "27": "MN",
    "28": "MS", "29": "MO", "30": "MT", "31": "NE", "32": "NV", "33": "NH",
    "34": "NJ", "35": "NM", "36": "NY", "37": "NC", "38": "ND", "39": "OH",
    "40": "OK", "41": "OR", "42": "PA", "44": "RI", "45": "SC", "46": "SD",
    "47": "TN", "48": "TX", "49": "UT", "50": "VT", "51": "VA", "53": "WA",
    "54": "WV", "55": "WI", "56": "WY",
}

FIPS_TO_CENSUS_REGION: dict[str, str] = {
    "01": "South", "02": "West", "04": "West", "05": "South", "06": "West",
    "08": "West", "09": "Northeast", "10": "South", "11": "South",
    "12": "South", "13": "South", "15": "West", "16": "West",
    "17": "Midwest", "18": "Midwest", "19": "Midwest", "20": "Midwest",
    "21": "South", "22": "South", "23": "Northeast", "24": "South",
    "25": "Northeast", "26": "Midwest", "27": "Midwest", "28": "South",
    "29": "Midwest", "30": "West", "31": "Midwest", "32": "West",
    "33": "Northeast", "34": "Northeast", "35": "West", "36": "Northeast",
    "37": "South", "38": "Midwest", "39": "Midwest", "40": "South",
    "41": "West", "42": "Northeast", "44": "Northeast", "45": "South",
    "46": "Midwest", "47": "South", "48": "South", "49": "West",
    "50": "Northeast", "51": "South", "53": "West", "54": "South",
    "55": "Midwest", "56": "West",
}


def _silver_schema() -> Schema:
    """Schema for the temp Silver base.bea_rpp table (11 columns)."""
    return Schema(
        NestedField(1, "record_id", StringType(), required=True),
        NestedField(2, "state_fips", StringType(), required=True),
        NestedField(3, "state_name", StringType(), required=True),
        NestedField(4, "state_abbr", StringType(), required=True),
        NestedField(5, "census_region", StringType(), required=True),
        NestedField(6, "rpp_all_items", DoubleType(), required=True),
        NestedField(7, "purchasing_power_multiplier", DoubleType(), required=True),
        NestedField(8, "verification_status", StringType(), required=True),
        NestedField(9, "data_year", IntegerType(), required=True),
        NestedField(10, "source_load_date", DateType(), required=True),
        NestedField(11, "ingested_at", TimestampType(), required=True),
    )


def _build_silver_fixture() -> list[dict]:
    """Construct a 51-row Silver base.bea_rpp fixture deterministically."""
    rows: list[dict] = []
    for fips in sorted(FIPS_TO_USPS.keys()):
        if fips in VERIFIED_RPP:
            rpp = VERIFIED_RPP[fips]
            verification = "bea_official"
        else:
            rpp = ESTIMATE_RPP_BY_REGION[FIPS_TO_CENSUS_REGION[fips]]
            verification = "estimate"
        rows.append(
            {
                "record_id": f"rpp-{fips}fixture0000000",
                "state_fips": fips,
                "state_name": FIPS_TO_STATE_NAME[fips],
                "state_abbr": FIPS_TO_USPS[fips],
                "census_region": FIPS_TO_CENSUS_REGION[fips],
                "rpp_all_items": rpp,
                "purchasing_power_multiplier": 100.0 / rpp,
                "verification_status": verification,
                "data_year": 2024,
                "source_load_date": LOAD_DATE,
                "ingested_at": INGESTED_AT,
            }
        )
    return rows


@pytest.fixture
def silver_rows() -> list[dict]:
    return _build_silver_fixture()


def _seed_temp_silver(tmp_path: Path, silver_data: list[dict]) -> Path:
    """Create a temporary project dir with a seeded base.bea_rpp table."""
    from brightsmith.infra.iceberg_setup import (
        append_data,
        get_catalog,
        get_or_create_table,
    )

    project_dir = tmp_path / "project"
    silver_warehouse = project_dir / "data" / "silver" / "iceberg_warehouse"
    gold_warehouse = project_dir / "data" / "gold" / "iceberg_warehouse"
    catalog_dir = project_dir / "data" / "catalog"
    silver_warehouse.mkdir(parents=True, exist_ok=True)
    gold_warehouse.mkdir(parents=True, exist_ok=True)
    catalog_dir.mkdir(parents=True, exist_ok=True)
    catalog_path = catalog_dir / "catalog.db"

    catalog = get_catalog(silver_warehouse, catalog_path)
    table = get_or_create_table(catalog, "base", "bea_rpp", _silver_schema())
    append_data(table, silver_data)
    return project_dir


# ---------------------------------------------------------------------------
# classify_cost_tier — 5 buckets + boundary values
# ---------------------------------------------------------------------------


class TestClassifyCostTier:
    """Left-closed CASE: breakpoints land in the upper bucket."""

    def test_very_high_well_above_floor(self):
        assert classify_cost_tier(115.0) == "very_high"

    def test_high_midrange(self):
        assert classify_cost_tier(105.0) == "high"

    def test_average_midrange(self):
        assert classify_cost_tier(100.0) == "average"

    def test_low_midrange(self):
        assert classify_cost_tier(94.0) == "low"

    def test_very_low_well_below_floor(self):
        assert classify_cost_tier(80.0) == "very_low"

    # Boundary values — each must land in the UPPER (higher-cost) bucket.

    def test_boundary_108_is_very_high(self):
        """108.0 is the very_high lower bound (inclusive)."""
        assert classify_cost_tier(108.0) == "very_high"

    def test_boundary_103_is_high(self):
        """103.0 is the high lower bound (inclusive)."""
        assert classify_cost_tier(103.0) == "high"

    def test_boundary_97_is_average(self):
        """97.0 is the average lower bound (inclusive)."""
        assert classify_cost_tier(97.0) == "average"

    def test_boundary_91_is_low(self):
        """91.0 is the low lower bound (inclusive)."""
        assert classify_cost_tier(91.0) == "low"

    # Just-below boundaries land in the next-lower bucket.

    def test_just_below_108_is_high(self):
        assert classify_cost_tier(107.999) == "high"

    def test_just_below_103_is_average(self):
        assert classify_cost_tier(102.999) == "average"

    def test_just_below_97_is_low(self):
        assert classify_cost_tier(96.999) == "low"

    def test_just_below_91_is_very_low(self):
        assert classify_cost_tier(90.999) == "very_low"

    def test_returns_string_not_enum(self):
        """Transformer persists strings — function must return a string."""
        result = classify_cost_tier(100.0)
        assert isinstance(result, str)
        assert not isinstance(result, CostTier)  # Plain str, not enum member

    def test_cost_tier_enum_values(self):
        """Frozen enum values per BT-106."""
        assert CostTier.VERY_HIGH.value == "very_high"
        assert CostTier.HIGH.value == "high"
        assert CostTier.AVERAGE.value == "average"
        assert CostTier.LOW.value == "low"
        assert CostTier.VERY_LOW.value == "very_low"

    def test_breakpoints_are_frozen(self):
        """COST_TIER_BREAKPOINTS must have the exact 4 frozen thresholds."""
        thresholds = [t for t, _ in COST_TIER_BREAKPOINTS]
        assert thresholds == [108.0, 103.0, 97.0, 91.0]


# ---------------------------------------------------------------------------
# compute_adjusted_salary — rounding + anchor correctness
# ---------------------------------------------------------------------------


class TestComputeAdjustedSalary:
    """Per-anchor derivations and the 2-decimal rounding rule."""

    def test_adjusted_50k_ca(self):
        """CA multiplier = 100/110.7 ≈ 0.903342 => $45167.12."""
        result = compute_adjusted_salary(50000.0, 100.0 / 110.7)
        assert result == 45167.12

    def test_adjusted_50k_hi(self):
        """HI multiplier = 100/110.0 => $45454.55."""
        result = compute_adjusted_salary(50000.0, 100.0 / 110.0)
        assert result == 45454.55

    def test_adjusted_50k_ia(self):
        """IA multiplier = 100/87.8 => $56947.61."""
        result = compute_adjusted_salary(50000.0, 100.0 / 87.8)
        assert result == 56947.61

    def test_adjusted_30k_ca(self):
        result = compute_adjusted_salary(30000.0, 100.0 / 110.7)
        assert result == 27100.27

    def test_adjusted_75k_ca(self):
        result = compute_adjusted_salary(75000.0, 100.0 / 110.7)
        assert result == 67750.68

    def test_adjusted_100k_ca(self):
        result = compute_adjusted_salary(100000.0, 100.0 / 110.7)
        assert result == 90334.24

    def test_rounded_to_two_decimals(self):
        """Result has at most 2 decimal places of precision."""
        result = compute_adjusted_salary(50000.0, 1.0 / 3.0)  # 16666.666...
        assert result == 16666.67

    def test_multiplier_one_returns_salary(self):
        """Multiplier of 1.0 (national average) returns the input exactly."""
        assert compute_adjusted_salary(50000.0, 1.0) == 50000.0

    def test_high_cost_below_salary(self):
        """Multiplier < 1 (high-cost state) produces result < national."""
        result = compute_adjusted_salary(50000.0, 0.9)
        assert result == 45000.0
        assert result < 50000.0

    def test_low_cost_above_salary(self):
        """Multiplier > 1 (low-cost state) produces result > national."""
        result = compute_adjusted_salary(50000.0, 1.15)
        assert result == 57500.0
        assert result > 50000.0


# ---------------------------------------------------------------------------
# derive_gold_rows
# ---------------------------------------------------------------------------


def _silver_row_for(fips: str) -> dict:
    """Minimal Silver row for a single state (by FIPS)."""
    rpp = VERIFIED_RPP.get(fips, ESTIMATE_RPP_BY_REGION[FIPS_TO_CENSUS_REGION[fips]])
    return {
        "record_id": f"rpp-{fips}test",
        "state_fips": fips,
        "state_name": FIPS_TO_STATE_NAME[fips],
        "state_abbr": FIPS_TO_USPS[fips],
        "census_region": FIPS_TO_CENSUS_REGION[fips],
        "rpp_all_items": rpp,
        "purchasing_power_multiplier": 100.0 / rpp,
        "verification_status": "bea_official" if fips in VERIFIED_RPP else "estimate",
        "data_year": 2024,
        "source_load_date": LOAD_DATE,
        "ingested_at": INGESTED_AT,
    }


class TestDeriveGoldRows:
    """Tests for the derive_gold_rows pure function."""

    def test_empty_input(self):
        assert derive_gold_rows([]) == []

    def test_single_row_passthrough_fields(self):
        """All 8 Silver passthrough fields are carried forward verbatim."""
        silver = [_silver_row_for("06")]
        gold = derive_gold_rows(silver)
        assert len(gold) == 1
        for field in SILVER_PASSTHROUGH_FIELDS:
            assert gold[0][field] == silver[0][field]

    def test_single_row_drops_silver_only_fields(self):
        """record_id, source_load_date, ingested_at are not carried forward here.

        record_id is re-derived in add_record_ids; source_load_date and
        ingested_at are dropped entirely (replaced by promoted_at).
        """
        silver = [_silver_row_for("06")]
        gold = derive_gold_rows(silver)
        assert "source_load_date" not in gold[0]
        assert "ingested_at" not in gold[0]
        # record_id must not be carried from Silver — it's derived in step 2.
        assert "record_id" not in gold[0]

    def test_derives_cost_tier(self):
        silver = [_silver_row_for("06")]  # CA, rpp=110.7
        gold = derive_gold_rows(silver)
        assert gold[0]["cost_tier"] == "very_high"

    def test_derives_all_four_adjusted_salaries(self):
        silver = [_silver_row_for("06")]  # CA
        gold = derive_gold_rows(silver)
        assert gold[0]["adjusted_30k"] == 27100.27
        assert gold[0]["adjusted_50k"] == 45167.12
        assert gold[0]["adjusted_75k"] == 67750.68
        assert gold[0]["adjusted_100k"] == 90334.24

    def test_preserves_input_order(self):
        silver = [_silver_row_for("06"), _silver_row_for("19"), _silver_row_for("28")]
        gold = derive_gold_rows(silver)
        assert [g["state_fips"] for g in gold] == ["06", "19", "28"]

    def test_no_record_id_yet(self):
        """derive_gold_rows must not stamp record_id — that's add_record_ids's job."""
        silver = [_silver_row_for("06")]
        gold = derive_gold_rows(silver)
        assert "record_id" not in gold[0]

    def test_no_promoted_at_yet(self):
        silver = [_silver_row_for("06")]
        gold = derive_gold_rows(silver)
        assert "promoted_at" not in gold[0]

    def test_13_columns_after_derive(self):
        """derive_gold_rows output has 13 fields: 8 passthrough + 1 cost_tier + 4 adjusted."""
        silver = [_silver_row_for("06")]
        gold = derive_gold_rows(silver)
        assert len(gold[0]) == 13


# ---------------------------------------------------------------------------
# add_record_ids
# ---------------------------------------------------------------------------


class TestAddRecordIds:
    """record_id uses prefix 'rpc', promoted_at is stamped."""

    def test_prefix_is_rpc_not_rpp(self):
        """CRITICAL: Gold uses 'rpc' prefix, Silver uses 'rpp'."""
        gold_rows = [{"state_fips": "06"}]
        ts = datetime.datetime(2026, 4, 11, tzinfo=datetime.timezone.utc)
        add_record_ids(gold_rows, ts)
        assert gold_rows[0]["record_id"].startswith("rpc-")
        assert not gold_rows[0]["record_id"].startswith("rpp-")

    def test_grain_prefix_constant(self):
        assert GRAIN_PREFIX == "rpc"

    def test_grain_fields_constant(self):
        assert GRAIN_FIELDS == ["state_fips"]

    def test_deterministic_record_id(self):
        """Same state_fips => same record_id across runs."""
        a = [{"state_fips": "06"}]
        b = [{"state_fips": "06"}]
        ts = datetime.datetime(2026, 4, 11, tzinfo=datetime.timezone.utc)
        add_record_ids(a, ts)
        add_record_ids(b, ts)
        assert a[0]["record_id"] == b[0]["record_id"]

    def test_different_state_fips_different_ids(self):
        rows = [{"state_fips": "06"}, {"state_fips": "19"}]
        ts = datetime.datetime(2026, 4, 11, tzinfo=datetime.timezone.utc)
        add_record_ids(rows, ts)
        assert rows[0]["record_id"] != rows[1]["record_id"]

    def test_matches_compute_grain_id_contract(self):
        rows = [{"state_fips": "06"}]
        ts = datetime.datetime(2026, 4, 11, tzinfo=datetime.timezone.utc)
        add_record_ids(rows, ts)
        expected = compute_grain_id({"state_fips": "06"}, ["state_fips"], prefix="rpc")
        assert rows[0]["record_id"] == expected

    def test_stamps_promoted_at(self):
        rows = [{"state_fips": "06"}]
        ts = datetime.datetime(2026, 4, 11, 12, 0, 0, tzinfo=datetime.timezone.utc)
        add_record_ids(rows, ts)
        assert rows[0]["promoted_at"] == ts


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------


class TestGoldSchema:
    """The Iceberg schema must match the physical model exactly."""

    def test_15_columns(self):
        schema = get_gold_schema()
        assert len(schema.fields) == 15

    def test_column_order(self):
        schema = get_gold_schema()
        names = [f.name for f in schema.fields]
        assert names == [
            "record_id",
            "state_fips",
            "state_name",
            "state_abbr",
            "census_region",
            "rpp_all_items",
            "purchasing_power_multiplier",
            "cost_tier",
            "adjusted_30k",
            "adjusted_50k",
            "adjusted_75k",
            "adjusted_100k",
            "verification_status",
            "data_year",
            "promoted_at",
        ]

    def test_all_required(self):
        schema = get_gold_schema()
        for field in schema.fields:
            assert field.required, f"{field.name} must be NOT NULL"

    def test_salary_anchors_match_schema_columns(self):
        schema_cols = {f.name for f in get_gold_schema().fields}
        for _, col in SALARY_ANCHORS:
            assert col in schema_cols


# ---------------------------------------------------------------------------
# Integration — temp warehouse end-to-end
# ---------------------------------------------------------------------------


class TestIntegration:
    """Seed a temp Silver warehouse with 51 rows and run transform()."""

    def test_end_to_end_51_rows(self, tmp_path, silver_rows):
        from brightsmith.infra.iceberg_setup import get_catalog, read_with_duckdb

        project_dir = _seed_temp_silver(tmp_path, silver_rows)
        result = transform(project_dir=project_dir)

        assert result["rows_read"] == 51
        assert result["rows_derived"] == 51
        assert result["promoted"] == 51

        gold_warehouse = project_dir / "data" / "gold" / "iceberg_warehouse"
        catalog_path = project_dir / "data" / "catalog" / "catalog.db"
        catalog = get_catalog(gold_warehouse, catalog_path)
        table = catalog.load_table("consumable.regional_price_parities")
        rows = read_with_duckdb(table)
        assert len(rows) == 51

    def test_end_to_end_15_column_schema(self, tmp_path, silver_rows):
        from brightsmith.infra.iceberg_setup import get_catalog, read_with_duckdb

        project_dir = _seed_temp_silver(tmp_path, silver_rows)
        transform(project_dir=project_dir)

        gold_warehouse = project_dir / "data" / "gold" / "iceberg_warehouse"
        catalog_path = project_dir / "data" / "catalog" / "catalog.db"
        catalog = get_catalog(gold_warehouse, catalog_path)
        table = catalog.load_table("consumable.regional_price_parities")
        assert len(table.schema().fields) == 15
        rows = read_with_duckdb(table)
        assert len(rows[0]) == 15

    def test_end_to_end_all_five_cost_tiers(self, tmp_path, silver_rows):
        """With the test fixture the 5 cost tiers must all be populated.

        very_high: 4 verified states (CA, HI, DC, NJ)
        high: Northeast estimates (105.0) — 9 - 1 NJ - 1 DC-not-NE = 8
        average: West estimates (102.0) — 13 - 3 (CA, HI, AK?) -- computed
        low: Midwest (95.0) + South (93.0) estimates
        very_low: 4 verified states (AR, MS, IA, OK)
        """
        from brightsmith.infra.iceberg_setup import get_catalog, read_with_duckdb

        project_dir = _seed_temp_silver(tmp_path, silver_rows)
        transform(project_dir=project_dir)

        gold_warehouse = project_dir / "data" / "gold" / "iceberg_warehouse"
        catalog_path = project_dir / "data" / "catalog" / "catalog.db"
        catalog = get_catalog(gold_warehouse, catalog_path)
        rows = read_with_duckdb(catalog.load_table("consumable.regional_price_parities"))

        tiers = {r["cost_tier"] for r in rows}
        assert tiers == {"very_high", "high", "average", "low", "very_low"}

    def test_end_to_end_verification_status_carry_forward(
        self, tmp_path, silver_rows
    ):
        """8 bea_official + 43 estimate per Bronze Condition 7."""
        from brightsmith.infra.iceberg_setup import get_catalog, read_with_duckdb

        project_dir = _seed_temp_silver(tmp_path, silver_rows)
        transform(project_dir=project_dir)

        gold_warehouse = project_dir / "data" / "gold" / "iceberg_warehouse"
        catalog_path = project_dir / "data" / "catalog" / "catalog.db"
        catalog = get_catalog(gold_warehouse, catalog_path)
        rows = read_with_duckdb(catalog.load_table("consumable.regional_price_parities"))

        bea = sum(1 for r in rows if r["verification_status"] == "bea_official")
        est = sum(1 for r in rows if r["verification_status"] == "estimate")
        assert bea == 8
        assert est == 43

    def test_end_to_end_spot_checks_all_8(self, tmp_path, silver_rows):
        """All 8 BEA-verified states match spec values exactly (not within tolerance)."""
        from brightsmith.infra.iceberg_setup import get_catalog, read_with_duckdb

        project_dir = _seed_temp_silver(tmp_path, silver_rows)
        transform(project_dir=project_dir)

        gold_warehouse = project_dir / "data" / "gold" / "iceberg_warehouse"
        catalog_path = project_dir / "data" / "catalog" / "catalog.db"
        catalog = get_catalog(gold_warehouse, catalog_path)
        rows = read_with_duckdb(catalog.load_table("consumable.regional_price_parities"))
        by_fips = {r["state_fips"]: r for r in rows}

        expected = {
            # fips : (state_abbr, cost_tier, rpp_all_items, adjusted_50k)
            "06": ("CA", "very_high", 110.7, 45167.12),
            "15": ("HI", "very_high", 110.0, 45454.55),
            "11": ("DC", "very_high", 109.9, 45495.91),
            "34": ("NJ", "very_high", 108.8, 45955.88),
            "05": ("AR", "very_low", 86.9, 57537.40),
            "28": ("MS", "very_low", 87.0, 57471.26),
            "19": ("IA", "very_low", 87.8, 56947.61),
            "40": ("OK", "very_low", 87.8, 56947.61),
        }
        for fips, (abbr, tier, rpp, adj50k) in expected.items():
            row = by_fips[fips]
            assert row["state_abbr"] == abbr, f"{fips}: state_abbr mismatch"
            assert row["cost_tier"] == tier, f"{fips}: cost_tier mismatch"
            assert row["rpp_all_items"] == rpp, f"{fips}: rpp mismatch"
            assert row["adjusted_50k"] == adj50k, (
                f"{fips}: adjusted_50k={row['adjusted_50k']} expected {adj50k}"
            )
            assert row["verification_status"] == "bea_official"

    def test_end_to_end_ca_below_national(self, tmp_path, silver_rows):
        """CA adjusted_50k < 50000 (high-cost sanity)."""
        from brightsmith.infra.iceberg_setup import get_catalog, read_with_duckdb

        project_dir = _seed_temp_silver(tmp_path, silver_rows)
        transform(project_dir=project_dir)
        gold_warehouse = project_dir / "data" / "gold" / "iceberg_warehouse"
        catalog_path = project_dir / "data" / "catalog" / "catalog.db"
        catalog = get_catalog(gold_warehouse, catalog_path)
        rows = read_with_duckdb(catalog.load_table("consumable.regional_price_parities"))
        ca = next(r for r in rows if r["state_fips"] == "06")
        assert ca["adjusted_50k"] < 50000.0

    def test_end_to_end_ia_above_national(self, tmp_path, silver_rows):
        """IA adjusted_50k > 50000 (low-cost sanity)."""
        from brightsmith.infra.iceberg_setup import get_catalog, read_with_duckdb

        project_dir = _seed_temp_silver(tmp_path, silver_rows)
        transform(project_dir=project_dir)
        gold_warehouse = project_dir / "data" / "gold" / "iceberg_warehouse"
        catalog_path = project_dir / "data" / "catalog" / "catalog.db"
        catalog = get_catalog(gold_warehouse, catalog_path)
        rows = read_with_duckdb(catalog.load_table("consumable.regional_price_parities"))
        ia = next(r for r in rows if r["state_fips"] == "19")
        assert ia["adjusted_50k"] > 50000.0

    def test_idempotent_second_run_zero_new(self, tmp_path, silver_rows):
        """Re-running transform produces 0 new rows."""
        project_dir = _seed_temp_silver(tmp_path, silver_rows)
        r1 = transform(project_dir=project_dir)
        assert r1["promoted"] == 51
        assert r1["skipped_dedup"] == 0

        r2 = transform(project_dir=project_dir)
        assert r2["promoted"] == 0
        assert r2["skipped_dedup"] == 51

    def test_end_to_end_data_year_constant(self, tmp_path, silver_rows):
        from brightsmith.infra.iceberg_setup import get_catalog, read_with_duckdb

        project_dir = _seed_temp_silver(tmp_path, silver_rows)
        transform(project_dir=project_dir)
        gold_warehouse = project_dir / "data" / "gold" / "iceberg_warehouse"
        catalog_path = project_dir / "data" / "catalog" / "catalog.db"
        catalog = get_catalog(gold_warehouse, catalog_path)
        rows = read_with_duckdb(catalog.load_table("consumable.regional_price_parities"))
        assert {r["data_year"] for r in rows} == {2024}

    def test_end_to_end_zero_nulls(self, tmp_path, silver_rows):
        """Contract: 0% nulls on all 15 columns."""
        from brightsmith.infra.iceberg_setup import get_catalog, read_with_duckdb

        project_dir = _seed_temp_silver(tmp_path, silver_rows)
        transform(project_dir=project_dir)
        gold_warehouse = project_dir / "data" / "gold" / "iceberg_warehouse"
        catalog_path = project_dir / "data" / "catalog" / "catalog.db"
        catalog = get_catalog(gold_warehouse, catalog_path)
        rows = read_with_duckdb(catalog.load_table("consumable.regional_price_parities"))
        for row in rows:
            for column, value in row.items():
                assert value is not None, f"null in {column}"

    def test_end_to_end_record_ids_unique(self, tmp_path, silver_rows):
        from brightsmith.infra.iceberg_setup import get_catalog, read_with_duckdb

        project_dir = _seed_temp_silver(tmp_path, silver_rows)
        transform(project_dir=project_dir)
        gold_warehouse = project_dir / "data" / "gold" / "iceberg_warehouse"
        catalog_path = project_dir / "data" / "catalog" / "catalog.db"
        catalog = get_catalog(gold_warehouse, catalog_path)
        rows = read_with_duckdb(catalog.load_table("consumable.regional_price_parities"))
        ids = [r["record_id"] for r in rows]
        assert len(ids) == len(set(ids)) == 51
        assert all(rid.startswith("rpc-") for rid in ids)

    def test_end_to_end_inverse_invariant(self, tmp_path, silver_rows):
        from brightsmith.infra.iceberg_setup import get_catalog, read_with_duckdb

        project_dir = _seed_temp_silver(tmp_path, silver_rows)
        transform(project_dir=project_dir)
        gold_warehouse = project_dir / "data" / "gold" / "iceberg_warehouse"
        catalog_path = project_dir / "data" / "catalog" / "catalog.db"
        catalog = get_catalog(gold_warehouse, catalog_path)
        rows = read_with_duckdb(catalog.load_table("consumable.regional_price_parities"))
        for row in rows:
            product = row["purchasing_power_multiplier"] * row["rpp_all_items"]
            assert abs(product - 100.0) <= 0.01

    def test_end_to_end_adjusted_derivation_invariant(self, tmp_path, silver_rows):
        """Every adjusted_Nk must equal round(N*1000*multiplier, 2) within 0.01."""
        from brightsmith.infra.iceberg_setup import get_catalog, read_with_duckdb

        project_dir = _seed_temp_silver(tmp_path, silver_rows)
        transform(project_dir=project_dir)
        gold_warehouse = project_dir / "data" / "gold" / "iceberg_warehouse"
        catalog_path = project_dir / "data" / "catalog" / "catalog.db"
        catalog = get_catalog(gold_warehouse, catalog_path)
        rows = read_with_duckdb(catalog.load_table("consumable.regional_price_parities"))
        for row in rows:
            m = row["purchasing_power_multiplier"]
            assert abs(row["adjusted_30k"] - round(30000.0 * m, 2)) <= 0.01
            assert abs(row["adjusted_50k"] - round(50000.0 * m, 2)) <= 0.01
            assert abs(row["adjusted_75k"] - round(75000.0 * m, 2)) <= 0.01
            assert abs(row["adjusted_100k"] - round(100000.0 * m, 2)) <= 0.01
