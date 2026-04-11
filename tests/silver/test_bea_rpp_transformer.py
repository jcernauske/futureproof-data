"""Tests for the Silver zone BEA RPP transformer."""

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

from silver import _us_state_reference as usref
from silver._us_state_reference import (
    BEA_VERIFIED_FIPS,
    FIPS_TO_CENSUS_REGION,
    FIPS_TO_USPS,
)
from silver.bea_rpp_transformer import (
    EXPECTED_ROW_COUNT,
    GRAIN_FIELDS,
    GRAIN_PREFIX,
    derive_census_region,
    derive_purchasing_power_multiplier,
    derive_state_abbr,
    derive_verification_status,
    get_silver_schema,
    promote_bea_rpp,
    transform_row,
    transform_rows,
)


# ---------------------------------------------------------------------------
# Canonical fixture: 51 rows matching the spec-verified values for the 8
# BEA-verified states and plausible estimate values for the other 43.
# ---------------------------------------------------------------------------


LOAD_DATE = datetime.date(2026, 4, 10)
INGESTED_AT = datetime.datetime(2026, 4, 10, 12, 0, 0, tzinfo=datetime.timezone.utc)

# The 8 BEA-verified RPP values — must match the spec exactly.
VERIFIED_RPP: dict[str, float] = {
    "06": 110.7,  # CA
    "15": 110.0,  # HI
    "11": 109.9,  # DC
    "34": 108.8,  # NJ
    "05": 86.9,   # AR
    "28": 87.0,   # MS
    "19": 87.8,   # IA
    "40": 87.8,   # OK
}

# Per-census-region plausible RPP baselines for the 43 estimate rows.
ESTIMATE_RPP_BY_REGION: dict[str, float] = {
    "Northeast": 105.0,
    "Midwest": 95.0,
    "South": 93.0,
    "West": 102.0,
}

# State names (USPS canonical) — only needed for bronze fixture generation.
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


def _build_bronze_fixture() -> list[dict]:
    """Construct a 51-row Bronze-shaped fixture deterministically."""
    rows = []
    for fips in sorted(FIPS_TO_USPS.keys()):
        if fips in VERIFIED_RPP:
            rpp = VERIFIED_RPP[fips]
        else:
            region = FIPS_TO_CENSUS_REGION[fips]
            rpp = ESTIMATE_RPP_BY_REGION[region]
        rows.append(
            {
                "geo_fips": fips,
                "geo_name": FIPS_TO_STATE_NAME[fips],
                "rpp_all_items": rpp,
                "data_year": 2024,
                "ingested_at": datetime.datetime(
                    2026, 4, 10, 8, 0, 0, tzinfo=datetime.timezone.utc
                ),
                "source_url": "https://apps.bea.gov/api/data/",
                "source_method": "csv_cache",
                "load_date": LOAD_DATE,
            }
        )
    return rows


@pytest.fixture
def bronze_rows() -> list[dict]:
    return _build_bronze_fixture()


@pytest.fixture
def ca_row() -> dict:
    """Bronze row for California — a BEA-verified, West-region state."""
    return {
        "geo_fips": "06",
        "geo_name": "California",
        "rpp_all_items": 110.7,
        "data_year": 2024,
        "ingested_at": INGESTED_AT,
        "source_url": "https://apps.bea.gov/api/data/",
        "source_method": "csv_cache",
        "load_date": LOAD_DATE,
    }


# ---------------------------------------------------------------------------
# TestStateReferenceSelfCheck
# ---------------------------------------------------------------------------


class TestStateReferenceSelfCheck:
    """The _us_state_reference module runs its own self-check at import."""

    def test_fips_to_usps_has_51_entries(self):
        assert len(FIPS_TO_USPS) == 51

    def test_fips_to_census_region_has_51_entries(self):
        assert len(FIPS_TO_CENSUS_REGION) == 51

    def test_lookup_key_sets_match(self):
        assert set(FIPS_TO_USPS.keys()) == set(FIPS_TO_CENSUS_REGION.keys())

    def test_bea_verified_is_subset(self):
        assert BEA_VERIFIED_FIPS.issubset(FIPS_TO_USPS.keys())

    def test_bea_verified_has_8_entries(self):
        assert len(BEA_VERIFIED_FIPS) == 8

    def test_bea_verified_membership(self):
        assert BEA_VERIFIED_FIPS == frozenset(
            {"05", "06", "11", "15", "19", "28", "34", "40"}
        )

    def test_cross_validates_against_bronze_ingestor(self):
        """Advisory #5: Silver lookup must match Bronze VALID_STATE_FIPS."""
        from raw.bea_rpp_ingestor import BeaRppIngestor

        assert set(FIPS_TO_USPS.keys()) == set(BeaRppIngestor.VALID_STATE_FIPS)

    def test_self_check_idempotent(self):
        """_self_check is safe to call repeatedly."""
        usref._self_check()
        usref._self_check()

    def test_self_check_detects_length_drift(self, monkeypatch):
        """Temporarily shrinking FIPS_TO_USPS must make _self_check fail."""
        broken = {k: v for k, v in FIPS_TO_USPS.items() if k != "06"}
        monkeypatch.setattr(usref, "FIPS_TO_USPS", broken)
        with pytest.raises(AssertionError, match="FIPS_TO_USPS"):
            usref._self_check()

    def test_self_check_detects_key_mismatch(self, monkeypatch):
        """Mismatched key sets between the two dicts must fail."""
        broken = dict(FIPS_TO_CENSUS_REGION)
        broken.pop("06")
        broken["99"] = "West"
        monkeypatch.setattr(usref, "FIPS_TO_CENSUS_REGION", broken)
        with pytest.raises(AssertionError):
            usref._self_check()

    def test_dc_in_south(self):
        assert FIPS_TO_CENSUS_REGION["11"] == "South"

    def test_census_region_counts(self):
        """Standard Census assignment: NE=9, MW=12, S=17, W=13."""
        counts: dict[str, int] = {}
        for region in FIPS_TO_CENSUS_REGION.values():
            counts[region] = counts.get(region, 0) + 1
        assert counts == {
            "Northeast": 9,
            "Midwest": 12,
            "South": 17,
            "West": 13,
        }


# ---------------------------------------------------------------------------
# TestDeriveStateAbbr
# ---------------------------------------------------------------------------


class TestDeriveStateAbbr:
    def test_california(self):
        assert derive_state_abbr("06") == "CA"

    def test_dc(self):
        assert derive_state_abbr("11") == "DC"

    def test_wyoming(self):
        assert derive_state_abbr("56") == "WY"

    def test_all_values_uppercase_2_letter(self):
        for abbr in FIPS_TO_USPS.values():
            assert len(abbr) == 2
            assert abbr.isupper()

    def test_unknown_fips_raises(self):
        with pytest.raises(ValueError, match="Unknown state_fips"):
            derive_state_abbr("99")


# ---------------------------------------------------------------------------
# TestDeriveCensusRegion
# ---------------------------------------------------------------------------


class TestDeriveCensusRegion:
    @pytest.mark.parametrize(
        "fips,expected",
        [
            ("06", "West"),    # CA
            ("15", "West"),    # HI
            ("34", "Northeast"),  # NJ
            ("19", "Midwest"),  # IA
            ("11", "South"),   # DC — documented Census quirk
            ("05", "South"),   # AR
            ("28", "South"),   # MS
            ("40", "South"),   # OK
        ],
    )
    def test_spot_check_regions(self, fips, expected):
        assert derive_census_region(fips) == expected

    def test_all_regions_are_valid_enum(self):
        valid = {"Northeast", "Midwest", "South", "West"}
        for region in FIPS_TO_CENSUS_REGION.values():
            assert region in valid

    def test_unknown_fips_raises(self):
        with pytest.raises(ValueError, match="Unknown state_fips"):
            derive_census_region("99")


# ---------------------------------------------------------------------------
# TestDerivePurchasingPowerMultiplier
# ---------------------------------------------------------------------------


class TestDerivePurchasingPowerMultiplier:
    def test_national_100_yields_1(self):
        assert derive_purchasing_power_multiplier(100.0) == pytest.approx(1.0)

    def test_ca_spot_check(self):
        assert derive_purchasing_power_multiplier(110.7) == pytest.approx(
            0.9034, abs=1e-3
        )

    def test_ar_spot_check(self):
        assert derive_purchasing_power_multiplier(86.9) == pytest.approx(
            1.1507, abs=1e-3
        )

    def test_zero_raises(self):
        with pytest.raises(ValueError, match="division by zero"):
            derive_purchasing_power_multiplier(0.0)

    def test_none_raises(self):
        with pytest.raises(ValueError, match="None"):
            derive_purchasing_power_multiplier(None)  # type: ignore[arg-type]

    def test_inverse_invariant(self):
        """multiplier * rpp_all_items must equal 100.0 within 0.01 tolerance."""
        for rpp in [86.9, 87.0, 87.8, 108.8, 109.9, 110.0, 110.7, 100.0]:
            mult = derive_purchasing_power_multiplier(rpp)
            assert abs(mult * rpp - 100.0) < 0.01


# ---------------------------------------------------------------------------
# TestDeriveVerificationStatus
# ---------------------------------------------------------------------------


class TestDeriveVerificationStatus:
    @pytest.mark.parametrize(
        "fips",
        ["05", "06", "11", "15", "19", "28", "34", "40"],
    )
    def test_verified_states(self, fips):
        assert derive_verification_status(fips) == "bea_official"

    @pytest.mark.parametrize("fips", ["01", "02", "04", "56", "48", "36"])
    def test_estimate_states(self, fips):
        assert derive_verification_status(fips) == "estimate"

    def test_exactly_8_bea_official(self):
        verified = [f for f in FIPS_TO_USPS.keys() if derive_verification_status(f) == "bea_official"]
        assert len(verified) == 8

    def test_exactly_43_estimate(self):
        estimate = [f for f in FIPS_TO_USPS.keys() if derive_verification_status(f) == "estimate"]
        assert len(estimate) == 43


# ---------------------------------------------------------------------------
# TestTransformRow
# ---------------------------------------------------------------------------


class TestTransformRow:
    def test_returns_dict(self, ca_row):
        result = transform_row(ca_row, ingested_at=INGESTED_AT)
        assert isinstance(result, dict)

    def test_column_set(self, ca_row):
        result = transform_row(ca_row, ingested_at=INGESTED_AT)
        assert set(result.keys()) == {
            "record_id",
            "state_fips",
            "state_name",
            "state_abbr",
            "census_region",
            "rpp_all_items",
            "purchasing_power_multiplier",
            "verification_status",
            "data_year",
            "source_load_date",
            "ingested_at",
        }

    def test_record_id_prefix(self, ca_row):
        result = transform_row(ca_row, ingested_at=INGESTED_AT)
        assert result["record_id"].startswith("rpp-")

    def test_record_id_deterministic(self, ca_row):
        r1 = transform_row(ca_row, ingested_at=INGESTED_AT)
        r2 = transform_row(ca_row, ingested_at=INGESTED_AT)
        assert r1["record_id"] == r2["record_id"]

    def test_record_id_depends_only_on_state_fips(self, ca_row):
        """Changing any non-grain field must not change the record_id."""
        r1 = transform_row(ca_row, ingested_at=INGESTED_AT)
        mutated = dict(ca_row)
        mutated["rpp_all_items"] = 120.0  # different value
        r2 = transform_row(mutated, ingested_at=INGESTED_AT)
        assert r1["record_id"] == r2["record_id"]

    def test_state_fips_passthrough(self, ca_row):
        result = transform_row(ca_row, ingested_at=INGESTED_AT)
        assert result["state_fips"] == "06"

    def test_state_name_renamed_from_geo_name(self, ca_row):
        result = transform_row(ca_row, ingested_at=INGESTED_AT)
        assert result["state_name"] == "California"

    def test_state_abbr_derived(self, ca_row):
        result = transform_row(ca_row, ingested_at=INGESTED_AT)
        assert result["state_abbr"] == "CA"

    def test_census_region_derived(self, ca_row):
        result = transform_row(ca_row, ingested_at=INGESTED_AT)
        assert result["census_region"] == "West"

    def test_rpp_all_items_passthrough(self, ca_row):
        result = transform_row(ca_row, ingested_at=INGESTED_AT)
        assert result["rpp_all_items"] == 110.7

    def test_purchasing_power_multiplier_computed(self, ca_row):
        result = transform_row(ca_row, ingested_at=INGESTED_AT)
        assert result["purchasing_power_multiplier"] == pytest.approx(0.9034, abs=1e-3)

    def test_verification_status_for_ca(self, ca_row):
        result = transform_row(ca_row, ingested_at=INGESTED_AT)
        assert result["verification_status"] == "bea_official"

    def test_data_year_default(self, ca_row):
        result = transform_row(ca_row, ingested_at=INGESTED_AT)
        assert result["data_year"] == 2024

    def test_source_load_date_renamed(self, ca_row):
        result = transform_row(ca_row, ingested_at=INGESTED_AT)
        assert result["source_load_date"] == LOAD_DATE

    def test_ingested_at_uses_override(self, ca_row):
        result = transform_row(ca_row, ingested_at=INGESTED_AT)
        assert result["ingested_at"] == INGESTED_AT

    def test_source_metadata_dropped(self, ca_row):
        result = transform_row(ca_row, ingested_at=INGESTED_AT)
        assert "geo_fips" not in result
        assert "geo_name" not in result
        assert "source_url" not in result
        assert "source_method" not in result

    def test_missing_geo_fips_raises(self):
        with pytest.raises(ValueError, match="Missing state_fips"):
            transform_row(
                {
                    "geo_name": "X",
                    "rpp_all_items": 100.0,
                    "load_date": LOAD_DATE,
                }
            )

    def test_invalid_geo_fips_raises(self):
        with pytest.raises(ValueError, match="Invalid state_fips"):
            transform_row(
                {
                    "geo_fips": "6",
                    "geo_name": "California",
                    "rpp_all_items": 110.7,
                    "load_date": LOAD_DATE,
                }
            )

    def test_unknown_geo_fips_raises(self):
        with pytest.raises(ValueError, match="not a known U.S. state"):
            transform_row(
                {
                    "geo_fips": "99",
                    "geo_name": "Atlantis",
                    "rpp_all_items": 100.0,
                    "load_date": LOAD_DATE,
                }
            )

    def test_missing_geo_name_raises(self):
        with pytest.raises(ValueError, match="Missing geo_name"):
            transform_row(
                {
                    "geo_fips": "06",
                    "geo_name": "",
                    "rpp_all_items": 110.7,
                    "load_date": LOAD_DATE,
                }
            )

    def test_missing_rpp_raises(self):
        with pytest.raises(ValueError, match="Missing rpp_all_items"):
            transform_row(
                {
                    "geo_fips": "06",
                    "geo_name": "California",
                    "load_date": LOAD_DATE,
                }
            )

    def test_missing_load_date_raises(self):
        with pytest.raises(ValueError, match="Missing load_date"):
            transform_row(
                {
                    "geo_fips": "06",
                    "geo_name": "California",
                    "rpp_all_items": 110.7,
                }
            )


# ---------------------------------------------------------------------------
# TestTransformRows — full 51-row pass
# ---------------------------------------------------------------------------


class TestTransformRows:
    def test_51_rows_in_51_rows_out(self, bronze_rows):
        silver = transform_rows(bronze_rows, ingested_at=INGESTED_AT)
        assert len(silver) == 51

    def test_state_fips_unique(self, bronze_rows):
        silver = transform_rows(bronze_rows, ingested_at=INGESTED_AT)
        assert len({r["state_fips"] for r in silver}) == 51

    def test_record_id_unique(self, bronze_rows):
        silver = transform_rows(bronze_rows, ingested_at=INGESTED_AT)
        assert len({r["record_id"] for r in silver}) == 51

    def test_state_abbr_unique(self, bronze_rows):
        silver = transform_rows(bronze_rows, ingested_at=INGESTED_AT)
        assert len({r["state_abbr"] for r in silver}) == 51

    def test_all_four_census_regions_present(self, bronze_rows):
        silver = transform_rows(bronze_rows, ingested_at=INGESTED_AT)
        assert {r["census_region"] for r in silver} == {
            "Northeast",
            "Midwest",
            "South",
            "West",
        }

    def test_exact_8_bea_official(self, bronze_rows):
        silver = transform_rows(bronze_rows, ingested_at=INGESTED_AT)
        bea = [r for r in silver if r["verification_status"] == "bea_official"]
        assert len(bea) == 8

    def test_exact_43_estimate(self, bronze_rows):
        silver = transform_rows(bronze_rows, ingested_at=INGESTED_AT)
        est = [r for r in silver if r["verification_status"] == "estimate"]
        assert len(est) == 43

    def test_bea_official_fips_match_allowlist(self, bronze_rows):
        silver = transform_rows(bronze_rows, ingested_at=INGESTED_AT)
        bea_fips = {r["state_fips"] for r in silver if r["verification_status"] == "bea_official"}
        assert bea_fips == {"05", "06", "11", "15", "19", "28", "34", "40"}

    def test_inverse_invariant_all_rows(self, bronze_rows):
        silver = transform_rows(bronze_rows, ingested_at=INGESTED_AT)
        for r in silver:
            assert abs(r["purchasing_power_multiplier"] * r["rpp_all_items"] - 100.0) < 0.01

    def test_data_year_single_value(self, bronze_rows):
        silver = transform_rows(bronze_rows, ingested_at=INGESTED_AT)
        assert {r["data_year"] for r in silver} == {2024}

    def test_row_count_warn_but_not_raise(self, bronze_rows, caplog):
        """A short Bronze snapshot logs a warning but still transforms."""
        short = bronze_rows[:5]
        with caplog.at_level("WARNING"):
            silver = transform_rows(short, ingested_at=INGESTED_AT)
        assert len(silver) == 5
        assert any("expected 51" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# TestSpotChecks — the 8 BEA-verified canonical values
# ---------------------------------------------------------------------------


class TestSpotChecks:
    """Verify the 8 spec-frozen spot-check rows byte-for-byte."""

    @pytest.fixture
    def by_fips(self, bronze_rows) -> dict[str, dict]:
        silver = transform_rows(bronze_rows, ingested_at=INGESTED_AT)
        return {r["state_fips"]: r for r in silver}

    def test_california(self, by_fips):
        row = by_fips["06"]
        assert row["state_abbr"] == "CA"
        assert row["census_region"] == "West"
        assert row["rpp_all_items"] == 110.7
        assert row["purchasing_power_multiplier"] == pytest.approx(0.9034, abs=1e-3)
        assert row["verification_status"] == "bea_official"

    def test_hawaii(self, by_fips):
        row = by_fips["15"]
        assert row["state_abbr"] == "HI"
        assert row["census_region"] == "West"
        assert row["rpp_all_items"] == 110.0
        assert row["purchasing_power_multiplier"] == pytest.approx(0.9091, abs=1e-3)
        assert row["verification_status"] == "bea_official"

    def test_district_of_columbia(self, by_fips):
        row = by_fips["11"]
        assert row["state_abbr"] == "DC"
        assert row["census_region"] == "South"
        assert row["rpp_all_items"] == 109.9
        assert row["purchasing_power_multiplier"] == pytest.approx(0.9099, abs=1e-3)
        assert row["verification_status"] == "bea_official"

    def test_new_jersey(self, by_fips):
        row = by_fips["34"]
        assert row["state_abbr"] == "NJ"
        assert row["census_region"] == "Northeast"
        assert row["rpp_all_items"] == 108.8
        assert row["purchasing_power_multiplier"] == pytest.approx(0.9191, abs=1e-3)
        assert row["verification_status"] == "bea_official"

    def test_arkansas(self, by_fips):
        row = by_fips["05"]
        assert row["state_abbr"] == "AR"
        assert row["census_region"] == "South"
        assert row["rpp_all_items"] == 86.9
        assert row["purchasing_power_multiplier"] == pytest.approx(1.1507, abs=1e-3)
        assert row["verification_status"] == "bea_official"

    def test_mississippi(self, by_fips):
        row = by_fips["28"]
        assert row["state_abbr"] == "MS"
        assert row["census_region"] == "South"
        assert row["rpp_all_items"] == 87.0
        assert row["purchasing_power_multiplier"] == pytest.approx(1.1494, abs=1e-3)
        assert row["verification_status"] == "bea_official"

    def test_iowa(self, by_fips):
        row = by_fips["19"]
        assert row["state_abbr"] == "IA"
        assert row["census_region"] == "Midwest"
        assert row["rpp_all_items"] == 87.8
        assert row["purchasing_power_multiplier"] == pytest.approx(1.1390, abs=1e-3)
        assert row["verification_status"] == "bea_official"

    def test_oklahoma(self, by_fips):
        row = by_fips["40"]
        assert row["state_abbr"] == "OK"
        assert row["census_region"] == "South"
        assert row["rpp_all_items"] == 87.8
        assert row["purchasing_power_multiplier"] == pytest.approx(1.1390, abs=1e-3)
        assert row["verification_status"] == "bea_official"


# ---------------------------------------------------------------------------
# TestSilverSchema
# ---------------------------------------------------------------------------


class TestSilverSchema:
    def test_field_count(self):
        assert len(get_silver_schema().fields) == 11

    def test_all_fields_required(self):
        for f in get_silver_schema().fields:
            assert f.required, f"{f.name} must be required (NOT NULL)"

    def test_field_types(self):
        types_by_name = {f.name: type(f.field_type) for f in get_silver_schema().fields}
        assert types_by_name["record_id"] is StringType
        assert types_by_name["state_fips"] is StringType
        assert types_by_name["state_name"] is StringType
        assert types_by_name["state_abbr"] is StringType
        assert types_by_name["census_region"] is StringType
        assert types_by_name["rpp_all_items"] is DoubleType
        assert types_by_name["purchasing_power_multiplier"] is DoubleType
        assert types_by_name["verification_status"] is StringType
        assert types_by_name["data_year"] is IntegerType
        assert types_by_name["source_load_date"] is DateType
        assert types_by_name["ingested_at"] is TimestampType

    def test_column_order(self):
        names = [f.name for f in get_silver_schema().fields]
        assert names == [
            "record_id",
            "state_fips",
            "state_name",
            "state_abbr",
            "census_region",
            "rpp_all_items",
            "purchasing_power_multiplier",
            "verification_status",
            "data_year",
            "source_load_date",
            "ingested_at",
        ]

    def test_grain_fields_constant(self):
        assert GRAIN_FIELDS == ["state_fips"]

    def test_grain_prefix_constant(self):
        assert GRAIN_PREFIX == "rpp"

    def test_expected_row_count(self):
        assert EXPECTED_ROW_COUNT == 51


# ---------------------------------------------------------------------------
# TestIntegration — write to a temp Iceberg warehouse via promote_bea_rpp
# ---------------------------------------------------------------------------


def _get_bronze_schema() -> Schema:
    """Minimal Bronze schema sufficient for the transformer's reads."""
    return Schema(
        NestedField(1, "geo_fips", StringType(), required=True),
        NestedField(2, "geo_name", StringType(), required=True),
        NestedField(3, "rpp_all_items", DoubleType(), required=True),
        NestedField(4, "data_year", IntegerType(), required=True),
        NestedField(5, "ingested_at", TimestampType(), required=True),
        NestedField(6, "source_url", StringType(), required=True),
        NestedField(7, "source_method", StringType(), required=True),
        NestedField(8, "load_date", DateType(), required=True),
    )


def _seed_temp_bronze(tmp_path: Path, bronze_rows: list[dict]) -> tuple[Path, Path, Path]:
    """Create a temporary Iceberg warehouse with a seeded bronze.bea_rpp table."""
    from brightsmith.infra.iceberg_setup import append_data, get_catalog, get_or_create_table

    bronze_warehouse = tmp_path / "bronze"
    silver_warehouse = tmp_path / "silver"
    catalog_path = tmp_path / "catalog.db"
    bronze_warehouse.mkdir(parents=True, exist_ok=True)
    silver_warehouse.mkdir(parents=True, exist_ok=True)

    catalog = get_catalog(bronze_warehouse, catalog_path)
    table = get_or_create_table(catalog, "bronze", "bea_rpp", _get_bronze_schema())
    append_data(table, bronze_rows)
    return bronze_warehouse, silver_warehouse, catalog_path


class TestIntegration:
    """End-to-end: run promote_bea_rpp against a temp Iceberg warehouse."""

    def test_end_to_end_51_rows(self, tmp_path, bronze_rows):
        from brightsmith.infra.iceberg_setup import get_catalog, read_with_duckdb

        bronze_wh, silver_wh, catalog_path = _seed_temp_bronze(tmp_path, bronze_rows)

        result = promote_bea_rpp(
            bronze_warehouse=bronze_wh,
            silver_warehouse=silver_wh,
            catalog_path=catalog_path,
            ingested_at=INGESTED_AT,
        )
        assert result["rows_read"] == 51
        assert result["rows_transformed"] == 51
        assert result["promoted"] == 51
        assert result["skipped_dedup"] == 0

        catalog = get_catalog(silver_wh, catalog_path)
        silver_table = catalog.load_table("base.bea_rpp")
        rows = read_with_duckdb(silver_table)
        assert len(rows) == 51
        assert {r["state_fips"] for r in rows} == set(FIPS_TO_USPS.keys())

    def test_end_to_end_11_columns(self, tmp_path, bronze_rows):
        from brightsmith.infra.iceberg_setup import get_catalog, read_with_duckdb

        bronze_wh, silver_wh, catalog_path = _seed_temp_bronze(tmp_path, bronze_rows)
        promote_bea_rpp(
            bronze_warehouse=bronze_wh,
            silver_warehouse=silver_wh,
            catalog_path=catalog_path,
            ingested_at=INGESTED_AT,
        )
        catalog = get_catalog(silver_wh, catalog_path)
        rows = read_with_duckdb(catalog.load_table("base.bea_rpp"))
        assert len(rows[0]) == 11

    def test_idempotent_second_run_zero_new(self, tmp_path, bronze_rows):
        """Re-running the promoter must write 0 new rows."""
        bronze_wh, silver_wh, catalog_path = _seed_temp_bronze(tmp_path, bronze_rows)
        r1 = promote_bea_rpp(
            bronze_warehouse=bronze_wh,
            silver_warehouse=silver_wh,
            catalog_path=catalog_path,
            ingested_at=INGESTED_AT,
        )
        assert r1["promoted"] == 51

        r2 = promote_bea_rpp(
            bronze_warehouse=bronze_wh,
            silver_warehouse=silver_wh,
            catalog_path=catalog_path,
            ingested_at=INGESTED_AT,
        )
        assert r2["promoted"] == 0
        assert r2["skipped_dedup"] == 51

    def test_end_to_end_verification_counts(self, tmp_path, bronze_rows):
        from brightsmith.infra.iceberg_setup import get_catalog, read_with_duckdb

        bronze_wh, silver_wh, catalog_path = _seed_temp_bronze(tmp_path, bronze_rows)
        promote_bea_rpp(
            bronze_warehouse=bronze_wh,
            silver_warehouse=silver_wh,
            catalog_path=catalog_path,
            ingested_at=INGESTED_AT,
        )
        catalog = get_catalog(silver_wh, catalog_path)
        rows = read_with_duckdb(catalog.load_table("base.bea_rpp"))
        bea = sum(1 for r in rows if r["verification_status"] == "bea_official")
        est = sum(1 for r in rows if r["verification_status"] == "estimate")
        assert bea == 8
        assert est == 43
