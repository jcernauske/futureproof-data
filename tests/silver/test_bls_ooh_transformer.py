"""Tests for the Silver zone BLS OOH transformer."""

import datetime

import pytest

from silver.bls_ooh_transformer import (
    BROAD_OCCUPATION_CODES,
    EDUCATION_LEVEL_LOOKUP,
    SOC_MAJOR_GROUP_LOOKUP,
    derive_growth_category,
    get_silver_schema,
    transform_row,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def raw_row():
    """A typical Bronze row for Software Developers (15-1252)."""
    return {
        "soc_code": "15-1252",
        "occupation_title": "Software developers",
        "employment_current": 1795500,
        "employment_projected": 2094200,
        "employment_change": 298700,
        "employment_change_pct": 16.6,
        "openings_annual_avg": 140700,
        "median_annual_wage": 130160.0,
        "median_wage_capped": False,
        "education_typical": "Bachelor's degree",
        "education_code": 3,
        "work_experience": "None",
        "work_experience_code": 3,
        "training_typical": "None",
        "training_code": 6,
        "ingested_at": datetime.datetime(2026, 4, 7, 12, 0, 0),
        "source_url": "https://bls.gov",
        "source_method": "bulk_xlsx_download",
        "load_date": datetime.date(2026, 4, 7),
    }


@pytest.fixture
def declining_row():
    """A Bronze row for a declining occupation."""
    return {
        "soc_code": "43-9021",
        "occupation_title": "Data entry keyers",
        "employment_current": 150000,
        "employment_projected": 96000,
        "employment_change": -54000,
        "employment_change_pct": -36.1,
        "openings_annual_avg": 10400,
        "median_annual_wage": 38000.0,
        "median_wage_capped": False,
        "education_typical": "High school diploma or equivalent",
        "education_code": 7,
        "work_experience": "None",
        "work_experience_code": 3,
        "training_typical": "Moderate-term on-the-job training",
        "training_code": 4,
        "load_date": datetime.date(2026, 4, 7),
    }


@pytest.fixture
def null_wage_row():
    """A Bronze row for a null-wage occupation (physician)."""
    return {
        "soc_code": "29-1211",
        "occupation_title": "Anesthesiologists",
        "employment_current": 31100,
        "employment_projected": 33100,
        "employment_change": 2000,
        "employment_change_pct": 6.5,
        "openings_annual_avg": 2200,
        "median_annual_wage": None,
        "median_wage_capped": False,
        "education_typical": "Doctoral or professional degree",
        "education_code": 1,
        "work_experience": "None",
        "work_experience_code": 3,
        "training_typical": "Internship/residency",
        "training_code": 1,
        "load_date": datetime.date(2026, 4, 7),
    }


# ---------------------------------------------------------------------------
# TestTransformRow
# ---------------------------------------------------------------------------

class TestTransformRow:
    """Tests for single-row transformation logic."""

    def test_returns_dict(self, raw_row):
        result = transform_row(raw_row)
        assert isinstance(result, dict)

    def test_record_id_prefix(self, raw_row):
        result = transform_row(raw_row)
        assert result["record_id"].startswith("ooh-")

    def test_record_id_deterministic(self, raw_row):
        r1 = transform_row(raw_row)
        r2 = transform_row(raw_row)
        assert r1["record_id"] == r2["record_id"]

    def test_record_id_changes_with_soc_code(self, raw_row):
        r1 = transform_row(raw_row)
        raw_row["soc_code"] = "15-1253"
        r2 = transform_row(raw_row)
        assert r1["record_id"] != r2["record_id"]

    def test_soc_code_passthrough(self, raw_row):
        result = transform_row(raw_row)
        assert result["soc_code"] == "15-1252"

    def test_occupation_title_passthrough(self, raw_row):
        result = transform_row(raw_row)
        assert result["occupation_title"] == "Software developers"

    def test_soc_major_group_derived(self, raw_row):
        result = transform_row(raw_row)
        assert result["soc_major_group"] == "15"

    def test_soc_major_group_name_derived(self, raw_row):
        result = transform_row(raw_row)
        assert result["soc_major_group_name"] == "Computer and Mathematical"

    def test_broad_occupation_flag_false(self, raw_row):
        result = transform_row(raw_row)
        assert result["broad_occupation_flag"] is False

    def test_catchall_flag_false(self, raw_row):
        result = transform_row(raw_row)
        assert result["catchall_flag"] is False

    def test_growth_category_growing_fast(self, raw_row):
        """16.6% should be growing_fast (10 <= pct < 20)."""
        result = transform_row(raw_row)
        assert result["growth_category"] == "growing_fast"

    def test_wage_available_true(self, raw_row):
        result = transform_row(raw_row)
        assert result["wage_available"] is True

    def test_education_level_name(self, raw_row):
        result = transform_row(raw_row)
        assert result["education_level_name"] == "Bachelor's degree"

    def test_source_load_date_renamed(self, raw_row):
        result = transform_row(raw_row)
        assert result["source_load_date"] == datetime.date(2026, 4, 7)
        assert "load_date" not in result

    def test_ingested_at_is_utc_timestamp(self, raw_row):
        result = transform_row(raw_row)
        assert isinstance(result["ingested_at"], datetime.datetime)
        assert result["ingested_at"].tzinfo is not None

    def test_source_metadata_dropped(self, raw_row):
        result = transform_row(raw_row)
        assert "source_url" not in result
        assert "source_method" not in result

    def test_employment_fields_passthrough(self, raw_row):
        result = transform_row(raw_row)
        assert result["employment_current"] == 1795500
        assert result["employment_projected"] == 2094200
        assert result["employment_change"] == 298700
        assert result["employment_change_pct"] == 16.6
        assert result["openings_annual_avg"] == 140700

    def test_median_wage_capped_passthrough(self, raw_row):
        result = transform_row(raw_row)
        assert result["median_wage_capped"] is False


# ---------------------------------------------------------------------------
# TestNullWage
# ---------------------------------------------------------------------------

class TestNullWage:
    """Tests for null-wage occupation handling."""

    def test_null_wage_preserved(self, null_wage_row):
        result = transform_row(null_wage_row)
        assert result["median_annual_wage"] is None

    def test_wage_available_false(self, null_wage_row):
        result = transform_row(null_wage_row)
        assert result["wage_available"] is False

    def test_null_wage_row_not_dropped(self, null_wage_row):
        """Null-wage rows must be preserved, not dropped."""
        result = transform_row(null_wage_row)
        assert result is not None
        assert result["soc_code"] == "29-1211"


# ---------------------------------------------------------------------------
# TestDecliningOccupation
# ---------------------------------------------------------------------------

class TestDecliningOccupation:
    """Tests for declining occupation handling."""

    def test_negative_employment_change(self, declining_row):
        result = transform_row(declining_row)
        assert result["employment_change"] == -54000

    def test_growth_category_declining_fast(self, declining_row):
        """-36.1% should be declining_fast (< -10)."""
        result = transform_row(declining_row)
        assert result["growth_category"] == "declining_fast"


# ---------------------------------------------------------------------------
# TestGrowthCategory
# ---------------------------------------------------------------------------

class TestGrowthCategory:
    """Tests for growth_category derivation with boundary values."""

    def test_none_returns_none(self):
        assert derive_growth_category(None) is None

    def test_declining_fast_deeply_negative(self):
        assert derive_growth_category(-50.0) == "declining_fast"

    def test_declining_fast_at_minus_10_point_1(self):
        assert derive_growth_category(-10.1) == "declining_fast"

    def test_declining_at_minus_10(self):
        """Exactly -10.0 is declining (not declining_fast), since < -10 is the boundary."""
        assert derive_growth_category(-10.0) == "declining"

    def test_declining_at_minus_1_point_1(self):
        assert derive_growth_category(-1.1) == "declining"

    def test_stable_at_minus_1(self):
        """Exactly -1.0 is stable (not declining), since < -1 is the boundary."""
        assert derive_growth_category(-1.0) == "stable"

    def test_stable_at_zero(self):
        assert derive_growth_category(0.0) == "stable"

    def test_stable_at_0_point_9(self):
        assert derive_growth_category(0.9) == "stable"

    def test_growing_at_1(self):
        """Exactly 1.0 is growing (not stable), since < 1 is the boundary."""
        assert derive_growth_category(1.0) == "growing"

    def test_growing_at_9_point_9(self):
        assert derive_growth_category(9.9) == "growing"

    def test_growing_fast_at_10(self):
        """Exactly 10.0 is growing_fast (not growing), since < 10 is the boundary."""
        assert derive_growth_category(10.0) == "growing_fast"

    def test_growing_fast_at_19_point_9(self):
        assert derive_growth_category(19.9) == "growing_fast"

    def test_booming_at_20(self):
        """Exactly 20.0 is booming (not growing_fast), since < 20 is the boundary."""
        assert derive_growth_category(20.0) == "booming"

    def test_booming_at_49_point_9(self):
        assert derive_growth_category(49.9) == "booming"


# ---------------------------------------------------------------------------
# TestBroadOccupationFlag
# ---------------------------------------------------------------------------

class TestBroadOccupationFlag:
    """Tests for broad_occupation_flag derivation."""

    @pytest.mark.parametrize("soc_code", [
        "13-1020", "13-2020", "29-2010", "31-1120",
        "39-7010", "47-4090", "51-2090",
    ])
    def test_all_seven_broad_codes_flagged(self, soc_code, raw_row):
        raw_row["soc_code"] = soc_code
        # Adjust major group to match
        result = transform_row(raw_row)
        assert result["broad_occupation_flag"] is True

    def test_exactly_seven_broad_codes(self):
        assert len(BROAD_OCCUPATION_CODES) == 7

    def test_regular_code_not_flagged(self, raw_row):
        result = transform_row(raw_row)
        assert result["broad_occupation_flag"] is False

    def test_code_ending_in_zero_but_not_broad(self, raw_row):
        """35-2010 ends in 0 but is NOT in the broad list."""
        raw_row["soc_code"] = "35-2010"
        result = transform_row(raw_row)
        assert result["broad_occupation_flag"] is False


# ---------------------------------------------------------------------------
# TestCatchallFlag
# ---------------------------------------------------------------------------

class TestCatchallFlag:
    """Tests for catchall_flag derivation."""

    def test_all_other_in_title(self, raw_row):
        raw_row["occupation_title"] = "Managers, all other"
        result = transform_row(raw_row)
        assert result["catchall_flag"] is True

    def test_all_other_case_insensitive(self, raw_row):
        raw_row["occupation_title"] = "Business operations specialists, ALL OTHER"
        result = transform_row(raw_row)
        assert result["catchall_flag"] is True

    def test_no_all_other(self, raw_row):
        result = transform_row(raw_row)
        assert result["catchall_flag"] is False

    def test_partial_match_other(self, raw_row):
        """Title with 'other' but not 'all other' should not flag."""
        raw_row["occupation_title"] = "Other managers"
        result = transform_row(raw_row)
        assert result["catchall_flag"] is False


# ---------------------------------------------------------------------------
# TestSOCMajorGroup
# ---------------------------------------------------------------------------

class TestSOCMajorGroup:
    """Tests for SOC major group derivation."""

    def test_all_22_groups_in_lookup(self):
        assert len(SOC_MAJOR_GROUP_LOOKUP) == 22

    def test_management_group(self, raw_row):
        raw_row["soc_code"] = "11-1011"
        result = transform_row(raw_row)
        assert result["soc_major_group"] == "11"
        assert result["soc_major_group_name"] == "Management"

    def test_healthcare_group(self, raw_row):
        raw_row["soc_code"] = "29-1141"
        result = transform_row(raw_row)
        assert result["soc_major_group"] == "29"
        assert result["soc_major_group_name"] == "Healthcare Practitioners and Technical"

    def test_transportation_group(self, raw_row):
        raw_row["soc_code"] = "53-3032"
        result = transform_row(raw_row)
        assert result["soc_major_group"] == "53"
        assert result["soc_major_group_name"] == "Transportation and Material Moving"

    def test_invalid_major_group_raises(self, raw_row):
        raw_row["soc_code"] = "99-1234"
        with pytest.raises(ValueError, match="Unknown SOC major group"):
            transform_row(raw_row)


# ---------------------------------------------------------------------------
# TestEducationLevelName
# ---------------------------------------------------------------------------

class TestEducationLevelName:
    """Tests for education_level_name derivation."""

    @pytest.mark.parametrize("code,expected", [
        (1, "Doctoral or professional degree"),
        (2, "Master's degree"),
        (3, "Bachelor's degree"),
        (4, "Associate's degree"),
        (5, "Postsecondary nondegree award"),
        (6, "Some college, no degree"),
        (7, "High school diploma or equivalent"),
        (8, "No formal educational credential"),
    ])
    def test_all_education_codes(self, code, expected, raw_row):
        raw_row["education_code"] = code
        result = transform_row(raw_row)
        assert result["education_level_name"] == expected

    def test_null_education_code_gives_null_name(self, raw_row):
        raw_row["education_code"] = None
        result = transform_row(raw_row)
        assert result["education_level_name"] is None


# ---------------------------------------------------------------------------
# TestValidation
# ---------------------------------------------------------------------------

class TestValidation:
    """Tests for SOC code validation."""

    def test_missing_soc_code_raises(self):
        with pytest.raises(ValueError, match="Missing soc_code"):
            transform_row({"occupation_title": "Test"})

    def test_null_soc_code_raises(self):
        with pytest.raises(ValueError, match="Missing soc_code"):
            transform_row({"soc_code": None})

    def test_empty_soc_code_raises(self):
        with pytest.raises(ValueError, match="Missing soc_code"):
            transform_row({"soc_code": ""})

    def test_invalid_format_raises(self):
        with pytest.raises(ValueError, match="Invalid SOC code format"):
            transform_row({"soc_code": "151252", "occupation_title": "Bad"})

    def test_alpha_soc_code_raises(self):
        with pytest.raises(ValueError, match="Invalid SOC code format"):
            transform_row({"soc_code": "AB-CDEF", "occupation_title": "Bad"})


# ---------------------------------------------------------------------------
# TestSilverSchema
# ---------------------------------------------------------------------------

class TestSilverSchema:
    """Tests for the Silver Iceberg schema."""

    def test_schema_field_count(self):
        schema = get_silver_schema()
        assert len(schema.fields) == 25

    def test_required_fields(self):
        schema = get_silver_schema()
        required = {f.name for f in schema.fields if f.required}
        expected_required = {
            "record_id", "soc_code", "occupation_title",
            "soc_major_group", "soc_major_group_name",
            "broad_occupation_flag", "catchall_flag",
            "median_wage_capped", "wage_available",
            "source_load_date", "ingested_at",
        }
        assert expected_required.issubset(required)

    def test_nullable_fields(self):
        schema = get_silver_schema()
        nullable = {f.name for f in schema.fields if not f.required}
        expected_nullable = {
            "employment_current", "employment_projected",
            "employment_change", "employment_change_pct",
            "openings_annual_avg", "growth_category",
            "median_annual_wage",
            "education_typical", "education_code", "education_level_name",
            "work_experience", "work_experience_code",
            "training_typical", "training_code",
        }
        assert expected_nullable == nullable
