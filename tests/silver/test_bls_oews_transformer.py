"""Tests for the Silver zone BLS OEWS transformer."""

from __future__ import annotations

import datetime
import logging
from pathlib import Path

import pytest
from pyiceberg.schema import Schema
from pyiceberg.types import (
    BooleanType,
    DateType,
    DoubleType,
    LongType,
    NestedField,
    StringType,
    TimestampType,
)

from silver.bls_oews_transformer import (
    GRAIN_FIELDS,
    GRAIN_PREFIX,
    SPEC_NAME,
    TOP_CODED_VALUE,
    check_monotonicity,
    get_silver_schema,
    normalize_top_code,
    promote_bls_oews,
    transform_row,
    transform_rows,
)


# ---------------------------------------------------------------------------
# Constants and fixtures
# ---------------------------------------------------------------------------


LOAD_DATE = datetime.date(2026, 5, 6)
INGESTED_AT = datetime.datetime(2026, 5, 6, 12, 0, 0, tzinfo=datetime.timezone.utc)


@pytest.fixture
def software_developers() -> dict:
    """Bronze row for SOC 15-1252 — a fully populated, uncapped occupation."""
    return {
        "soc_code": "15-1252",
        "occupation_title": "Software Developers",
        "total_employment": 1656880,
        "wage_annual_p10": 77020.0,
        "wage_annual_p25": 98220.0,
        "wage_annual_median": 133080.0,
        "wage_annual_p75": 168570.0,
        "wage_annual_p90": 208620.0,
        "wage_annual_mean": 138110.0,
        "wage_hourly_median": 63.98,
        "wage_capped": False,
        "ingested_at": datetime.datetime(2026, 5, 6, 8, 0, 0, tzinfo=datetime.timezone.utc),
        "source_url": "https://www.bls.gov/oes/special-requests/oesm24nat.zip",
        "source_method": "xlsx_download",
        "load_date": LOAD_DATE,
    }


@pytest.fixture
def chief_executives() -> dict:
    """Bronze row for SOC 11-1011 — a top-coded occupation (p75 and p90 at 239200)."""
    return {
        "soc_code": "11-1011",
        "occupation_title": "Chief Executives",
        "total_employment": 211230,
        "wage_annual_p10": 90050.0,
        "wage_annual_p25": 130880.0,
        "wage_annual_median": 206420.0,
        "wage_annual_p75": 239200.0,
        "wage_annual_p90": 239200.0,
        "wage_annual_mean": 258900.0,
        "wage_hourly_median": 99.24,
        "wage_capped": True,
        "ingested_at": datetime.datetime(2026, 5, 6, 8, 0, 0, tzinfo=datetime.timezone.utc),
        "source_url": "https://www.bls.gov/oes/special-requests/oesm24nat.zip",
        "source_method": "xlsx_download",
        "load_date": LOAD_DATE,
    }


@pytest.fixture
def all_suppressed() -> dict:
    """Bronze row with full wage suppression (entertainment cluster pattern)."""
    return {
        "soc_code": "27-2011",
        "occupation_title": "Actors",
        "total_employment": 39400,
        "wage_annual_p10": None,
        "wage_annual_p25": None,
        "wage_annual_median": None,
        "wage_annual_p75": None,
        "wage_annual_p90": None,
        "wage_annual_mean": None,
        "wage_hourly_median": 26.81,
        "wage_capped": False,
        "ingested_at": datetime.datetime(2026, 5, 6, 8, 0, 0, tzinfo=datetime.timezone.utc),
        "source_url": "https://www.bls.gov/oes/special-requests/oesm24nat.zip",
        "source_method": "xlsx_download",
        "load_date": LOAD_DATE,
    }


# ---------------------------------------------------------------------------
# TestSilverSchema
# ---------------------------------------------------------------------------


class TestSilverSchema:
    """Tests for the Silver Iceberg schema definition."""

    def test_field_count(self):
        assert len(get_silver_schema().fields) == 13

    def test_field_names_and_order(self):
        names = [f.name for f in get_silver_schema().fields]
        assert names == [
            "record_id",
            "soc_code",
            "occupation_title",
            "total_employment",
            "wage_annual_p10",
            "wage_annual_p25",
            "wage_annual_median",
            "wage_annual_p75",
            "wage_annual_p90",
            "wage_annual_mean",
            "wage_capped",
            "source_load_date",
            "ingested_at",
        ]

    def test_required_fields(self):
        required = {f.name for f in get_silver_schema().fields if f.required}
        assert required == {
            "record_id",
            "soc_code",
            "occupation_title",
            "wage_capped",
            "source_load_date",
            "ingested_at",
        }

    def test_nullable_fields(self):
        nullable = {f.name for f in get_silver_schema().fields if not f.required}
        assert nullable == {
            "total_employment",
            "wage_annual_p10",
            "wage_annual_p25",
            "wage_annual_median",
            "wage_annual_p75",
            "wage_annual_p90",
            "wage_annual_mean",
        }

    def test_field_types(self):
        types_by_name = {f.name: type(f.field_type) for f in get_silver_schema().fields}
        assert types_by_name["record_id"] is StringType
        assert types_by_name["soc_code"] is StringType
        assert types_by_name["occupation_title"] is StringType
        assert types_by_name["total_employment"] is LongType
        assert types_by_name["wage_annual_p10"] is DoubleType
        assert types_by_name["wage_annual_p25"] is DoubleType
        assert types_by_name["wage_annual_median"] is DoubleType
        assert types_by_name["wage_annual_p75"] is DoubleType
        assert types_by_name["wage_annual_p90"] is DoubleType
        assert types_by_name["wage_annual_mean"] is DoubleType
        assert types_by_name["wage_capped"] is BooleanType
        assert types_by_name["source_load_date"] is DateType
        assert types_by_name["ingested_at"] is TimestampType

    def test_grain_fields_constant(self):
        assert GRAIN_FIELDS == ["soc_code"]

    def test_grain_prefix_constant(self):
        assert GRAIN_PREFIX == "oews"

    def test_spec_name_constant(self):
        assert SPEC_NAME == "silver-base-bls-oews"


# ---------------------------------------------------------------------------
# TestTransformRow
# ---------------------------------------------------------------------------


class TestTransformRow:
    """Tests for single-row transformation logic."""

    def test_returns_dict(self, software_developers):
        result = transform_row(software_developers, ingested_at=INGESTED_AT)
        assert isinstance(result, dict)

    def test_column_set(self, software_developers):
        result = transform_row(software_developers, ingested_at=INGESTED_AT)
        assert set(result.keys()) == {
            "record_id",
            "soc_code",
            "occupation_title",
            "total_employment",
            "wage_annual_p10",
            "wage_annual_p25",
            "wage_annual_median",
            "wage_annual_p75",
            "wage_annual_p90",
            "wage_annual_mean",
            "wage_capped",
            "source_load_date",
            "ingested_at",
        }

    def test_record_id_prefix(self, software_developers):
        result = transform_row(software_developers, ingested_at=INGESTED_AT)
        assert result["record_id"].startswith("oews-")

    def test_record_id_deterministic(self, software_developers):
        r1 = transform_row(software_developers, ingested_at=INGESTED_AT)
        r2 = transform_row(software_developers, ingested_at=INGESTED_AT)
        assert r1["record_id"] == r2["record_id"]

    def test_record_id_changes_with_soc_code(self, software_developers):
        r1 = transform_row(software_developers, ingested_at=INGESTED_AT)
        mutated = dict(software_developers)
        mutated["soc_code"] = "15-1253"
        r2 = transform_row(mutated, ingested_at=INGESTED_AT)
        assert r1["record_id"] != r2["record_id"]

    def test_record_id_depends_only_on_soc_code(self, software_developers):
        """Changing any non-grain field must NOT change the record_id."""
        r1 = transform_row(software_developers, ingested_at=INGESTED_AT)
        mutated = dict(software_developers)
        mutated["wage_annual_median"] = 200_000.0
        r2 = transform_row(mutated, ingested_at=INGESTED_AT)
        assert r1["record_id"] == r2["record_id"]

    def test_soc_code_passthrough(self, software_developers):
        result = transform_row(software_developers, ingested_at=INGESTED_AT)
        assert result["soc_code"] == "15-1252"

    def test_occupation_title_passthrough(self, software_developers):
        result = transform_row(software_developers, ingested_at=INGESTED_AT)
        assert result["occupation_title"] == "Software Developers"

    def test_total_employment_passthrough(self, software_developers):
        result = transform_row(software_developers, ingested_at=INGESTED_AT)
        assert result["total_employment"] == 1656880

    def test_all_wage_percentiles_passthrough(self, software_developers):
        result = transform_row(software_developers, ingested_at=INGESTED_AT)
        assert result["wage_annual_p10"] == 77020.0
        assert result["wage_annual_p25"] == 98220.0
        assert result["wage_annual_median"] == 133080.0
        assert result["wage_annual_p75"] == 168570.0
        assert result["wage_annual_p90"] == 208620.0
        assert result["wage_annual_mean"] == 138110.0

    def test_wage_capped_passthrough_false(self, software_developers):
        result = transform_row(software_developers, ingested_at=INGESTED_AT)
        assert result["wage_capped"] is False

    def test_wage_capped_passthrough_true(self, chief_executives):
        result = transform_row(chief_executives, ingested_at=INGESTED_AT)
        assert result["wage_capped"] is True

    def test_source_load_date_renamed(self, software_developers):
        result = transform_row(software_developers, ingested_at=INGESTED_AT)
        assert result["source_load_date"] == LOAD_DATE
        assert "load_date" not in result

    def test_ingested_at_uses_override(self, software_developers):
        result = transform_row(software_developers, ingested_at=INGESTED_AT)
        assert result["ingested_at"] == INGESTED_AT

    def test_ingested_at_default_is_utc(self, software_developers):
        result = transform_row(software_developers)
        assert isinstance(result["ingested_at"], datetime.datetime)
        assert result["ingested_at"].tzinfo is not None

    def test_source_metadata_dropped(self, software_developers):
        result = transform_row(software_developers, ingested_at=INGESTED_AT)
        # Bronze-only fields must not survive into Silver
        assert "source_url" not in result
        assert "source_method" not in result
        assert "wage_hourly_median" not in result
        assert "load_date" not in result

    def test_soc_code_strip(self, software_developers):
        software_developers["soc_code"] = "  15-1252  "
        result = transform_row(software_developers, ingested_at=INGESTED_AT)
        assert result["soc_code"] == "15-1252"


# ---------------------------------------------------------------------------
# TestSocCodeValidation
# ---------------------------------------------------------------------------


class TestSocCodeValidation:
    """Tests for SOC code validation."""

    def test_missing_soc_code_raises(self):
        with pytest.raises(ValueError, match="Missing soc_code"):
            transform_row({"occupation_title": "x", "load_date": LOAD_DATE})

    def test_null_soc_code_raises(self):
        with pytest.raises(ValueError, match="Missing soc_code"):
            transform_row({"soc_code": None, "occupation_title": "x", "load_date": LOAD_DATE})

    def test_empty_soc_code_raises(self):
        with pytest.raises(ValueError, match="Empty soc_code"):
            transform_row({"soc_code": "", "occupation_title": "x", "load_date": LOAD_DATE})

    def test_whitespace_soc_code_raises(self):
        with pytest.raises(ValueError, match="Empty soc_code"):
            transform_row({"soc_code": "   ", "occupation_title": "x", "load_date": LOAD_DATE})

    def test_unhyphenated_soc_code_raises(self):
        with pytest.raises(ValueError, match="Invalid SOC code format"):
            transform_row({"soc_code": "151252", "occupation_title": "x", "load_date": LOAD_DATE})

    def test_alpha_soc_code_raises(self):
        with pytest.raises(ValueError, match="Invalid SOC code format"):
            transform_row({"soc_code": "AB-CDEF", "occupation_title": "x", "load_date": LOAD_DATE})

    def test_extra_digits_soc_code_raises(self):
        with pytest.raises(ValueError, match="Invalid SOC code format"):
            transform_row({"soc_code": "15-1252.00", "occupation_title": "x", "load_date": LOAD_DATE})

    def test_short_soc_code_raises(self):
        with pytest.raises(ValueError, match="Invalid SOC code format"):
            transform_row({"soc_code": "1-1252", "occupation_title": "x", "load_date": LOAD_DATE})

    def test_missing_occupation_title_raises(self, software_developers):
        software_developers["occupation_title"] = None
        with pytest.raises(ValueError, match="Missing occupation_title"):
            transform_row(software_developers, ingested_at=INGESTED_AT)

    def test_empty_occupation_title_raises(self, software_developers):
        software_developers["occupation_title"] = ""
        with pytest.raises(ValueError, match="Missing occupation_title"):
            transform_row(software_developers, ingested_at=INGESTED_AT)

    def test_missing_load_date_raises(self, software_developers):
        del software_developers["load_date"]
        with pytest.raises(ValueError, match="Missing load_date"):
            transform_row(software_developers, ingested_at=INGESTED_AT)


# ---------------------------------------------------------------------------
# TestMonotonicity
# ---------------------------------------------------------------------------


class TestMonotonicity:
    """Tests for the wage-percentile monotonicity check."""

    def test_monotone_row_returns_no_violations(self):
        record = {
            "wage_annual_p10": 30000.0,
            "wage_annual_p25": 50000.0,
            "wage_annual_median": 70000.0,
            "wage_annual_p75": 90000.0,
            "wage_annual_p90": 110000.0,
        }
        assert check_monotonicity(record) == []

    def test_all_nulls_returns_no_violations(self):
        record = {
            "wage_annual_p10": None,
            "wage_annual_p25": None,
            "wage_annual_median": None,
            "wage_annual_p75": None,
            "wage_annual_p90": None,
        }
        assert check_monotonicity(record) == []

    def test_violation_p25_below_p10(self):
        record = {
            "wage_annual_p10": 50000.0,
            "wage_annual_p25": 40000.0,
            "wage_annual_median": 70000.0,
            "wage_annual_p75": 90000.0,
            "wage_annual_p90": 110000.0,
        }
        violations = check_monotonicity(record)
        assert len(violations) == 1
        assert "p10=50000.0" in violations[0]
        assert "p25=40000.0" in violations[0]

    def test_violation_median_below_p25(self):
        record = {
            "wage_annual_p10": 30000.0,
            "wage_annual_p25": 60000.0,
            "wage_annual_median": 50000.0,
            "wage_annual_p75": 90000.0,
            "wage_annual_p90": 110000.0,
        }
        violations = check_monotonicity(record)
        assert len(violations) == 1

    def test_two_violations(self):
        record = {
            "wage_annual_p10": 30000.0,
            "wage_annual_p25": 50000.0,
            "wage_annual_median": 40000.0,  # below p25
            "wage_annual_p75": 35000.0,     # below median
            "wage_annual_p90": 110000.0,
        }
        violations = check_monotonicity(record)
        # median<p25 violation; p75 is checked against the previous non-null
        # (median=40000), so p75=35000<40000 is also a violation.
        assert len(violations) == 2

    def test_skips_nulls_in_chain(self):
        """If p25 is null, p10 should be compared against median directly."""
        record = {
            "wage_annual_p10": 30000.0,
            "wage_annual_p25": None,
            "wage_annual_median": 70000.0,
            "wage_annual_p75": 90000.0,
            "wage_annual_p90": 110000.0,
        }
        assert check_monotonicity(record) == []

    def test_skips_nulls_violation_still_caught(self):
        """A violation that spans a null gap still reports."""
        record = {
            "wage_annual_p10": 50000.0,
            "wage_annual_p25": None,
            "wage_annual_median": 40000.0,  # below p10
            "wage_annual_p75": 90000.0,
            "wage_annual_p90": 110000.0,
        }
        violations = check_monotonicity(record)
        assert len(violations) == 1
        assert "p10" in violations[0]
        assert "median" in violations[0]

    def test_transform_does_not_skip_violation_row(self, caplog):
        """Per spec, monotonicity violations are LOGGED but the row is kept."""
        bad_row = {
            "soc_code": "99-9999",
            "occupation_title": "Test Job",
            "wage_annual_p10": 50000.0,
            "wage_annual_p25": 40000.0,  # violation
            "wage_annual_median": 70000.0,
            "wage_annual_p75": 90000.0,
            "wage_annual_p90": 110000.0,
            "wage_capped": False,
            "load_date": LOAD_DATE,
        }
        with caplog.at_level(logging.WARNING, logger="silver.bls_oews_transformer"):
            result = transform_row(bad_row, ingested_at=INGESTED_AT)
        assert result["soc_code"] == "99-9999"
        assert result["wage_annual_p25"] == 40000.0
        assert any("Monotonicity violation" in r.message for r in caplog.records)

    def test_equal_consecutive_values_ok(self):
        """Strict equality is permitted (top-coded chains)."""
        record = {
            "wage_annual_p10": 30000.0,
            "wage_annual_p25": 50000.0,
            "wage_annual_median": 70000.0,
            "wage_annual_p75": TOP_CODED_VALUE,
            "wage_annual_p90": TOP_CODED_VALUE,
        }
        assert check_monotonicity(record) == []


# ---------------------------------------------------------------------------
# TestTopCodeNormalization
# ---------------------------------------------------------------------------


class TestTopCodeNormalization:
    """Tests for top-code value normalization to exactly $239,200."""

    def test_capped_row_already_at_floor_unchanged(self, chief_executives):
        result = transform_row(chief_executives, ingested_at=INGESTED_AT)
        assert result["wage_annual_p75"] == TOP_CODED_VALUE
        assert result["wage_annual_p90"] == TOP_CODED_VALUE

    def test_uncapped_row_unchanged(self, software_developers):
        """If wage_capped=False, normalization is a no-op."""
        result = transform_row(software_developers, ingested_at=INGESTED_AT)
        assert result["wage_annual_p10"] == 77020.0
        assert result["wage_annual_p90"] == 208620.0

    def test_capped_row_with_drift_snaps_to_floor(self):
        """A capped row with floating-point drift (239199.99) snaps to exactly 239200."""
        record = {
            "wage_capped": True,
            "wage_annual_p10": 90000.0,
            "wage_annual_p25": 130000.0,
            "wage_annual_median": 200000.0,
            "wage_annual_p75": 239199.99,  # drift
            "wage_annual_p90": 239200.5,   # drift
        }
        normalize_top_code(record)
        assert record["wage_annual_p75"] == TOP_CODED_VALUE
        assert record["wage_annual_p90"] == TOP_CODED_VALUE

    def test_capped_normalization_does_not_touch_unrelated_values(self):
        """Capped row's non-cap percentiles are preserved verbatim."""
        record = {
            "wage_capped": True,
            "wage_annual_p10": 90000.0,
            "wage_annual_p25": 130000.0,
            "wage_annual_median": 200000.0,
            "wage_annual_p75": TOP_CODED_VALUE,
            "wage_annual_p90": TOP_CODED_VALUE,
        }
        normalize_top_code(record)
        assert record["wage_annual_p10"] == 90000.0
        assert record["wage_annual_p25"] == 130000.0
        assert record["wage_annual_median"] == 200000.0

    def test_uncapped_row_drift_left_alone(self):
        """An uncapped row with values near 239200 is NOT touched."""
        record = {
            "wage_capped": False,
            "wage_annual_p90": 239100.0,  # not capped, just very high
        }
        normalize_top_code(record)
        assert record["wage_annual_p90"] == 239100.0

    def test_capped_with_nulls_ok(self):
        record = {
            "wage_capped": True,
            "wage_annual_p10": None,
            "wage_annual_p25": None,
            "wage_annual_median": None,
            "wage_annual_p75": TOP_CODED_VALUE,
            "wage_annual_p90": TOP_CODED_VALUE,
        }
        normalize_top_code(record)
        assert record["wage_annual_p75"] == TOP_CODED_VALUE


# ---------------------------------------------------------------------------
# TestSuppressionPreservation
# ---------------------------------------------------------------------------


class TestSuppressionPreservation:
    """Tests for full-suppression rows (Bronze parsed `*` -> null)."""

    def test_all_suppressed_row_kept(self, all_suppressed):
        """A row with all wages null must still be promoted."""
        result = transform_row(all_suppressed, ingested_at=INGESTED_AT)
        assert result["soc_code"] == "27-2011"
        assert result["wage_annual_p10"] is None
        assert result["wage_annual_p25"] is None
        assert result["wage_annual_median"] is None
        assert result["wage_annual_p75"] is None
        assert result["wage_annual_p90"] is None
        assert result["wage_annual_mean"] is None

    def test_all_suppressed_row_no_monotonicity_violation(self, all_suppressed, caplog):
        with caplog.at_level(logging.WARNING, logger="silver.bls_oews_transformer"):
            transform_row(all_suppressed, ingested_at=INGESTED_AT)
        assert not any("Monotonicity" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# TestTransformRows
# ---------------------------------------------------------------------------


class TestTransformRows:
    """Tests for the multi-row transform path."""

    def test_three_rows_produces_three_silver_rows(
        self, software_developers, chief_executives, all_suppressed
    ):
        bronze = [software_developers, chief_executives, all_suppressed]
        silver = transform_rows(bronze, ingested_at=INGESTED_AT)
        assert len(silver) == 3

    def test_record_ids_unique(self, software_developers, chief_executives, all_suppressed):
        bronze = [software_developers, chief_executives, all_suppressed]
        silver = transform_rows(bronze, ingested_at=INGESTED_AT)
        assert len({r["record_id"] for r in silver}) == 3

    def test_soc_codes_preserved(self, software_developers, chief_executives, all_suppressed):
        bronze = [software_developers, chief_executives, all_suppressed]
        silver = transform_rows(bronze, ingested_at=INGESTED_AT)
        assert {r["soc_code"] for r in silver} == {"15-1252", "11-1011", "27-2011"}

    def test_malformed_row_skipped_not_raised(self, software_developers, caplog):
        """A row with a malformed SOC code is logged and skipped, not raised."""
        bad = dict(software_developers)
        bad["soc_code"] = "BAD"
        bronze = [software_developers, bad]
        with caplog.at_level(logging.WARNING, logger="silver.bls_oews_transformer"):
            silver = transform_rows(bronze, ingested_at=INGESTED_AT)
        assert len(silver) == 1
        assert silver[0]["soc_code"] == "15-1252"
        assert any("Skipping malformed Bronze row" in r.message for r in caplog.records)

    def test_duplicate_soc_codes_raise(self, software_developers):
        """Two rows with the same SOC code raise — the promote dedup would
        skip one silently, so we fail loudly first."""
        bronze = [software_developers, dict(software_developers)]
        with pytest.raises(ValueError, match="Duplicate soc_code"):
            transform_rows(bronze, ingested_at=INGESTED_AT)

    def test_ingested_at_consistent_across_rows(
        self, software_developers, chief_executives
    ):
        bronze = [software_developers, chief_executives]
        silver = transform_rows(bronze, ingested_at=INGESTED_AT)
        assert all(r["ingested_at"] == INGESTED_AT for r in silver)


# ---------------------------------------------------------------------------
# TestSpotChecks — golden values from the spec
# ---------------------------------------------------------------------------


class TestSpotChecks:
    """Verify spec-frozen calibration values pass through unchanged."""

    def test_software_developers_median(self, software_developers):
        result = transform_row(software_developers, ingested_at=INGESTED_AT)
        assert result["wage_annual_median"] == 133080.0

    def test_software_developers_band(self, software_developers):
        """Per spec spot-check: median in [110K, 150K]."""
        result = transform_row(software_developers, ingested_at=INGESTED_AT)
        assert 110_000 <= result["wage_annual_median"] <= 150_000

    def test_chief_executives_p75_p90_capped(self, chief_executives):
        result = transform_row(chief_executives, ingested_at=INGESTED_AT)
        assert result["wage_annual_p75"] == TOP_CODED_VALUE
        assert result["wage_annual_p90"] == TOP_CODED_VALUE
        assert result["wage_capped"] is True


# ---------------------------------------------------------------------------
# TestIntegration — end-to-end via temp Iceberg warehouse
# ---------------------------------------------------------------------------


def _get_bronze_schema() -> Schema:
    """Minimal Bronze schema sufficient for the transformer's reads."""
    return Schema(
        NestedField(1, "soc_code", StringType(), required=True),
        NestedField(2, "occupation_title", StringType(), required=True),
        NestedField(3, "total_employment", LongType(), required=False),
        NestedField(4, "wage_annual_p10", DoubleType(), required=False),
        NestedField(5, "wage_annual_p25", DoubleType(), required=False),
        NestedField(6, "wage_annual_median", DoubleType(), required=False),
        NestedField(7, "wage_annual_p75", DoubleType(), required=False),
        NestedField(8, "wage_annual_p90", DoubleType(), required=False),
        NestedField(9, "wage_annual_mean", DoubleType(), required=False),
        NestedField(10, "wage_hourly_median", DoubleType(), required=False),
        NestedField(11, "wage_capped", BooleanType(), required=True),
        NestedField(12, "ingested_at", TimestampType(), required=True),
        NestedField(13, "source_url", StringType(), required=True),
        NestedField(14, "source_method", StringType(), required=True),
        NestedField(15, "load_date", DateType(), required=True),
    )


def _seed_temp_bronze(tmp_path: Path, bronze_rows: list[dict]) -> tuple[Path, Path, Path]:
    from brightsmith.infra.iceberg_setup import (
        append_data,
        get_catalog,
        get_or_create_table,
    )

    bronze_warehouse = tmp_path / "bronze"
    silver_warehouse = tmp_path / "silver"
    catalog_path = tmp_path / "catalog.db"
    bronze_warehouse.mkdir(parents=True, exist_ok=True)
    silver_warehouse.mkdir(parents=True, exist_ok=True)

    catalog = get_catalog(bronze_warehouse, catalog_path)
    table = get_or_create_table(catalog, "bronze", "bls_oews", _get_bronze_schema())
    append_data(table, bronze_rows)
    return bronze_warehouse, silver_warehouse, catalog_path


class TestIntegration:
    """End-to-end: run promote_bls_oews against a temp Iceberg warehouse."""

    def test_end_to_end_three_rows(
        self, tmp_path, software_developers, chief_executives, all_suppressed
    ):
        from brightsmith.infra.iceberg_setup import get_catalog, read_with_duckdb

        bronze_rows = [software_developers, chief_executives, all_suppressed]
        bronze_wh, silver_wh, catalog_path = _seed_temp_bronze(tmp_path, bronze_rows)

        result = promote_bls_oews(
            bronze_warehouse=bronze_wh,
            silver_warehouse=silver_wh,
            catalog_path=catalog_path,
            ingested_at=INGESTED_AT,
        )
        assert result["rows_read"] == 3
        assert result["rows_transformed"] == 3
        assert result["rows_skipped_transform"] == 0
        assert result["promoted"] == 3
        assert result["skipped_dedup"] == 0
        assert result["wage_capped_count"] == 1

        catalog = get_catalog(silver_wh, catalog_path)
        rows = read_with_duckdb(catalog.load_table("base.bls_oews"))
        assert len(rows) == 3
        assert {r["soc_code"] for r in rows} == {"15-1252", "11-1011", "27-2011"}

    def test_end_to_end_thirteen_columns(
        self, tmp_path, software_developers, chief_executives
    ):
        from brightsmith.infra.iceberg_setup import get_catalog, read_with_duckdb

        bronze_wh, silver_wh, catalog_path = _seed_temp_bronze(
            tmp_path, [software_developers, chief_executives]
        )
        promote_bls_oews(
            bronze_warehouse=bronze_wh,
            silver_warehouse=silver_wh,
            catalog_path=catalog_path,
            ingested_at=INGESTED_AT,
        )
        catalog = get_catalog(silver_wh, catalog_path)
        rows = read_with_duckdb(catalog.load_table("base.bls_oews"))
        assert len(rows[0]) == 13

    def test_idempotent_second_run_zero_new(
        self, tmp_path, software_developers, chief_executives
    ):
        bronze_rows = [software_developers, chief_executives]
        bronze_wh, silver_wh, catalog_path = _seed_temp_bronze(tmp_path, bronze_rows)

        r1 = promote_bls_oews(
            bronze_warehouse=bronze_wh,
            silver_warehouse=silver_wh,
            catalog_path=catalog_path,
            ingested_at=INGESTED_AT,
        )
        assert r1["promoted"] == 2

        r2 = promote_bls_oews(
            bronze_warehouse=bronze_wh,
            silver_warehouse=silver_wh,
            catalog_path=catalog_path,
            ingested_at=INGESTED_AT,
        )
        assert r2["promoted"] == 0
        assert r2["skipped_dedup"] == 2

    def test_end_to_end_top_code_preserved(self, tmp_path, chief_executives):
        from brightsmith.infra.iceberg_setup import get_catalog, read_with_duckdb

        bronze_wh, silver_wh, catalog_path = _seed_temp_bronze(
            tmp_path, [chief_executives]
        )
        promote_bls_oews(
            bronze_warehouse=bronze_wh,
            silver_warehouse=silver_wh,
            catalog_path=catalog_path,
            ingested_at=INGESTED_AT,
        )
        catalog = get_catalog(silver_wh, catalog_path)
        rows = read_with_duckdb(catalog.load_table("base.bls_oews"))
        ceo = next(r for r in rows if r["soc_code"] == "11-1011")
        assert ceo["wage_capped"] is True
        assert ceo["wage_annual_p75"] == TOP_CODED_VALUE
        assert ceo["wage_annual_p90"] == TOP_CODED_VALUE
