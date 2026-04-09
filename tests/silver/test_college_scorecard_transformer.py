"""Tests for the Silver zone College Scorecard transformer."""

import datetime

import pytest

from silver.college_scorecard_transformer import (
    CIP_FAMILIES,
    CONTROL_MAP,
    normalize_cipcode,
    transform_row,
    get_silver_schema,
)


class TestNormalizeCipcode:
    """Tests for CIP code normalization (4-digit -> XX.XXXX)."""

    def test_four_digit_inserts_dot(self):
        assert normalize_cipcode("5202") == "52.02"

    def test_leading_zeros_preserved(self):
        assert normalize_cipcode("0100") == "01.00"

    def test_already_normalized_passes_through(self):
        assert normalize_cipcode("52.02") == "52.02"

    def test_four_digit_all_zeros(self):
        assert normalize_cipcode("0000") == "00.00"

    def test_four_digit_all_nines(self):
        assert normalize_cipcode("9999") == "99.99"

    def test_longer_code_passes_through(self):
        """6-digit codes without dots pass through unchanged (not expected in this dataset)."""
        assert normalize_cipcode("520201") == "520201"


class TestTransformRow:
    """Tests for single-row transformation logic."""

    @pytest.fixture
    def raw_row(self):
        return {
            "unitid": 110635,
            "instnm": "Stanford University",
            "cipcode": "5202",
            "cipdesc": "Business Administration.",
            "creddesc": "Bachelor's Degree",
            "credlev": 3,
            "control": "Private nonprofit",
            "md_earn_wne": None,
            "earn_mdn_hi_1yr": 85000.0,
            "earn_mdn_hi_2yr": 92000.0,
            "debt_all_stgp_eval_mdn": 18500.0,
            "ipedscount1": 150,
            "ipedscount2": 155,
            "ingested_at": datetime.datetime(2026, 4, 6, 2, 34, 20),
            "source_url": "https://example.com",
            "source_method": "bulk_csv_download",
            "load_date": datetime.date(2026, 4, 6),
        }

    def test_returns_dict(self, raw_row):
        result = transform_row(raw_row)
        assert isinstance(result, dict)

    def test_cipcode_normalized(self, raw_row):
        result = transform_row(raw_row)
        assert result["cipcode"] == "52.02"

    def test_cip_family_extracted(self, raw_row):
        result = transform_row(raw_row)
        assert result["cip_family"] == "52"

    def test_cip_family_name_populated(self, raw_row):
        result = transform_row(raw_row)
        assert "Business" in result["cip_family_name"]

    def test_institution_control_mapped(self, raw_row):
        result = transform_row(raw_row)
        assert result["institution_control"] == "Private nonprofit"

    def test_institution_control_numeric(self, raw_row):
        raw_row["control"] = "1"
        result = transform_row(raw_row)
        assert result["institution_control"] == "Public"

    def test_institution_control_null(self, raw_row):
        raw_row["control"] = None
        result = transform_row(raw_row)
        assert result["institution_control"] is None

    def test_column_renames(self, raw_row):
        result = transform_row(raw_row)
        assert result["institution_name"] == "Stanford University"
        assert result["program_name"] == "Business Administration."
        assert result["credential_level"] == 3
        assert result["credential_description"] == "Bachelor's Degree"
        assert result["earnings_1yr_median"] == 85000.0
        assert result["earnings_2yr_median"] == 92000.0
        assert result["debt_median"] == 18500.0
        assert result["completions_count_1"] == 150
        assert result["completions_count_2"] == 155

    def test_small_cohort_flag_false_for_large(self, raw_row):
        result = transform_row(raw_row)
        assert result["small_cohort_flag"] is False

    def test_small_cohort_flag_true_for_small(self, raw_row):
        raw_row["ipedscount1"] = 15
        result = transform_row(raw_row)
        assert result["small_cohort_flag"] is True

    def test_small_cohort_flag_true_for_null(self, raw_row):
        raw_row["ipedscount1"] = None
        result = transform_row(raw_row)
        assert result["small_cohort_flag"] is True

    def test_small_cohort_flag_true_at_boundary(self, raw_row):
        raw_row["ipedscount1"] = 29
        result = transform_row(raw_row)
        assert result["small_cohort_flag"] is True

    def test_small_cohort_flag_false_at_threshold(self, raw_row):
        raw_row["ipedscount1"] = 30
        result = transform_row(raw_row)
        assert result["small_cohort_flag"] is False

    def test_record_id_generated(self, raw_row):
        result = transform_row(raw_row)
        assert result["record_id"].startswith("cs-")

    def test_record_id_deterministic(self, raw_row):
        result1 = transform_row(raw_row)
        result2 = transform_row(raw_row)
        assert result1["record_id"] == result2["record_id"]

    def test_record_id_changes_with_grain(self, raw_row):
        result1 = transform_row(raw_row)
        raw_row["cipcode"] = "1101"
        result2 = transform_row(raw_row)
        assert result1["record_id"] != result2["record_id"]

    def test_md_earn_wne_dropped(self, raw_row):
        result = transform_row(raw_row)
        assert "md_earn_wne" not in result

    def test_raw_metadata_dropped(self, raw_row):
        result = transform_row(raw_row)
        assert "source_url" not in result
        assert "source_method" not in result

    def test_null_unitid_returns_none(self, raw_row):
        raw_row["unitid"] = None
        assert transform_row(raw_row) is None

    def test_null_cipcode_returns_none(self, raw_row):
        raw_row["cipcode"] = None
        assert transform_row(raw_row) is None

    def test_null_credlev_returns_none(self, raw_row):
        raw_row["credlev"] = None
        assert transform_row(raw_row) is None

    def test_earnings_null_preserved(self, raw_row):
        raw_row["earn_mdn_hi_1yr"] = None
        raw_row["earn_mdn_hi_2yr"] = None
        raw_row["debt_all_stgp_eval_mdn"] = None
        result = transform_row(raw_row)
        assert result["earnings_1yr_median"] is None
        assert result["earnings_2yr_median"] is None
        assert result["debt_median"] is None

    def test_ingested_at_is_timestamp(self, raw_row):
        result = transform_row(raw_row)
        assert isinstance(result["ingested_at"], datetime.datetime)

    def test_source_load_date_preserved(self, raw_row):
        result = transform_row(raw_row)
        assert result["source_load_date"] == datetime.date(2026, 4, 6)


class TestCipFamilies:
    """Tests for CIP family lookup table."""

    def test_common_families_present(self):
        assert "52" in CIP_FAMILIES  # Business
        assert "11" in CIP_FAMILIES  # CS
        assert "51" in CIP_FAMILIES  # Health
        assert "13" in CIP_FAMILIES  # Education
        assert "14" in CIP_FAMILIES  # Engineering

    def test_unknown_family_handled(self):
        raw = {
            "unitid": 100000, "instnm": "Test", "cipcode": "9900",
            "cipdesc": "Unknown", "creddesc": "Bachelor's Degree",
            "credlev": 3, "ipedscount1": 50, "load_date": datetime.date(2026, 1, 1),
        }
        result = transform_row(raw)
        assert "Unknown" in result["cip_family_name"]


class TestControlMap:
    """Tests for institution control type mapping."""

    def test_numeric_codes(self):
        assert CONTROL_MAP["1"] == "Public"
        assert CONTROL_MAP["2"] == "Private nonprofit"
        assert CONTROL_MAP["3"] == "Private for-profit"

    def test_text_values(self):
        assert CONTROL_MAP["Public"] == "Public"
        assert CONTROL_MAP["Private nonprofit"] == "Private nonprofit"
        assert CONTROL_MAP["Private for-profit"] == "Private for-profit"


class TestSilverSchema:
    """Tests for the Silver Iceberg schema."""

    def test_schema_field_count(self):
        schema = get_silver_schema()
        assert len(schema.fields) == 18

    def test_required_fields(self):
        schema = get_silver_schema()
        required = {f.name for f in schema.fields if f.required}
        assert "record_id" in required
        assert "unitid" in required
        assert "cipcode" in required
        assert "credential_level" in required
        assert "small_cohort_flag" in required

    def test_nullable_fields(self):
        schema = get_silver_schema()
        nullable = {f.name for f in schema.fields if not f.required}
        assert "earnings_1yr_median" in nullable
        assert "earnings_2yr_median" in nullable
        assert "debt_median" in nullable
        assert "completions_count_1" in nullable
        assert "completions_count_2" in nullable
        assert "institution_control" in nullable
