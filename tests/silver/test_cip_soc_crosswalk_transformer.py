"""Tests for the Silver zone CIP-SOC crosswalk transformer."""

import datetime

import pytest

from silver.cip_soc_crosswalk_transformer import (
    GRAIN_FIELDS,
    VALID_MATCH_QUALITIES,
    VALID_SOC_MAJOR_GROUPS,
    derive_match_quality,
    get_silver_schema,
    transform_row,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def raw_row():
    """A typical Bronze crosswalk row for Business Admin -> General Managers."""
    return {
        "cipcode": "52.0201",
        "cip_title": "Business Administration and Management, General.",
        "soc_code": "11-1021",
        "soc_title": "General and Operations Managers",
        "ingested_at": datetime.datetime(2026, 4, 8, 12, 0, 0),
        "source_url": "https://nces.ed.gov/ipeds/cipcode/Files/CIP2020_SOC2018_Crosswalk.xlsx",
        "source_method": "xlsx_download",
        "load_date": datetime.date(2026, 4, 8),
    }


@pytest.fixture
def scorecard_cips():
    """Sample scorecard CIP codes (4-digit format as per EDA)."""
    return {"52.0201", "11.0101", "26.0101", "13.0101"}


@pytest.fixture
def bls_socs():
    """Sample BLS SOC codes."""
    return {"11-1021", "11-2021", "15-1252", "29-1211", "25-2031"}


@pytest.fixture
def onet_socs():
    """Sample O*NET BLS SOC codes."""
    return {"11-1021", "15-1252", "29-1211", "19-1042"}


@pytest.fixture
def empty_lookups():
    """Empty lookup sets (no cross-table matches)."""
    return set(), set(), set()


# ---------------------------------------------------------------------------
# TestTransformRow
# ---------------------------------------------------------------------------

class TestTransformRow:
    """Tests for single-row transformation logic."""

    def test_returns_dict(self, raw_row, scorecard_cips, bls_socs, onet_socs):
        result = transform_row(raw_row, scorecard_cips, bls_socs, onet_socs)
        assert isinstance(result, dict)

    def test_record_id_prefix(self, raw_row, scorecard_cips, bls_socs, onet_socs):
        result = transform_row(raw_row, scorecard_cips, bls_socs, onet_socs)
        assert result["record_id"].startswith("xw-")

    def test_record_id_deterministic(self, raw_row, scorecard_cips, bls_socs, onet_socs):
        r1 = transform_row(raw_row, scorecard_cips, bls_socs, onet_socs)
        r2 = transform_row(raw_row, scorecard_cips, bls_socs, onet_socs)
        assert r1["record_id"] == r2["record_id"]

    def test_record_id_changes_with_cipcode(self, raw_row, scorecard_cips, bls_socs, onet_socs):
        r1 = transform_row(raw_row, scorecard_cips, bls_socs, onet_socs)
        raw_row["cipcode"] = "11.0101"
        r2 = transform_row(raw_row, scorecard_cips, bls_socs, onet_socs)
        assert r1["record_id"] != r2["record_id"]

    def test_record_id_changes_with_soc_code(self, raw_row, scorecard_cips, bls_socs, onet_socs):
        r1 = transform_row(raw_row, scorecard_cips, bls_socs, onet_socs)
        raw_row["soc_code"] = "11-2021"
        r2 = transform_row(raw_row, scorecard_cips, bls_socs, onet_socs)
        assert r1["record_id"] != r2["record_id"]

    def test_cipcode_passthrough(self, raw_row, scorecard_cips, bls_socs, onet_socs):
        result = transform_row(raw_row, scorecard_cips, bls_socs, onet_socs)
        assert result["cipcode"] == "52.0201"

    def test_soc_code_passthrough(self, raw_row, scorecard_cips, bls_socs, onet_socs):
        result = transform_row(raw_row, scorecard_cips, bls_socs, onet_socs)
        assert result["soc_code"] == "11-1021"

    def test_cip_title_passthrough(self, raw_row, scorecard_cips, bls_socs, onet_socs):
        result = transform_row(raw_row, scorecard_cips, bls_socs, onet_socs)
        assert result["cip_title"] == "Business Administration and Management, General."

    def test_soc_title_passthrough(self, raw_row, scorecard_cips, bls_socs, onet_socs):
        result = transform_row(raw_row, scorecard_cips, bls_socs, onet_socs)
        assert result["soc_title"] == "General and Operations Managers"

    def test_cip_family_derived(self, raw_row, scorecard_cips, bls_socs, onet_socs):
        result = transform_row(raw_row, scorecard_cips, bls_socs, onet_socs)
        assert result["cip_family"] == "52"

    def test_soc_major_group_derived(self, raw_row, scorecard_cips, bls_socs, onet_socs):
        result = transform_row(raw_row, scorecard_cips, bls_socs, onet_socs)
        assert result["soc_major_group"] == "11"

    def test_source_load_date_renamed(self, raw_row, scorecard_cips, bls_socs, onet_socs):
        result = transform_row(raw_row, scorecard_cips, bls_socs, onet_socs)
        assert result["source_load_date"] == datetime.date(2026, 4, 8)
        assert "load_date" not in result

    def test_ingested_at_is_utc_timestamp(self, raw_row, scorecard_cips, bls_socs, onet_socs):
        result = transform_row(raw_row, scorecard_cips, bls_socs, onet_socs)
        assert isinstance(result["ingested_at"], datetime.datetime)
        assert result["ingested_at"].tzinfo is not None

    def test_source_metadata_dropped(self, raw_row, scorecard_cips, bls_socs, onet_socs):
        result = transform_row(raw_row, scorecard_cips, bls_socs, onet_socs)
        assert "source_url" not in result
        assert "source_method" not in result


# ---------------------------------------------------------------------------
# TestNoMatchFiltering
# ---------------------------------------------------------------------------

class TestNoMatchFiltering:
    """Tests for 99-9999 sentinel row filtering."""

    def test_no_match_filtered_out(self, scorecard_cips, bls_socs, onet_socs):
        """Verify rows with soc_code = '99-9999' are filtered to None."""
        raw = {
            "cipcode": "36.0115",
            "cip_title": "Card Games and Card Dealing.",
            "soc_code": "99-9999",
            "soc_title": "NO MATCH",
            "load_date": datetime.date(2026, 4, 8),
        }
        result = transform_row(raw, scorecard_cips, bls_socs, onet_socs)
        assert result is None

    def test_valid_soc_preserved(self, raw_row, scorecard_cips, bls_socs, onet_socs):
        """Verify non-sentinel rows are preserved."""
        result = transform_row(raw_row, scorecard_cips, bls_socs, onet_socs)
        assert result is not None
        assert result["soc_code"] == "11-1021"


# ---------------------------------------------------------------------------
# TestMatchFlags
# ---------------------------------------------------------------------------

class TestMatchFlags:
    """Tests for cross-table match flag derivation."""

    def test_full_match(self, raw_row, scorecard_cips, bls_socs, onet_socs):
        """52.0201 in scorecard_cips, 11-1021 in bls_socs and onet_socs."""
        result = transform_row(raw_row, scorecard_cips, bls_socs, onet_socs)
        assert result["has_scorecard_match"] is True
        assert result["has_bls_match"] is True
        assert result["has_onet_match"] is True

    def test_no_scorecard_match(self, raw_row, bls_socs, onet_socs):
        """CIP not in scorecard set."""
        result = transform_row(raw_row, set(), bls_socs, onet_socs)
        assert result["has_scorecard_match"] is False

    def test_no_bls_match(self, raw_row, scorecard_cips, onet_socs):
        """SOC not in BLS set."""
        result = transform_row(raw_row, scorecard_cips, set(), onet_socs)
        assert result["has_bls_match"] is False

    def test_no_onet_match(self, raw_row, scorecard_cips, bls_socs):
        """SOC not in O*NET set."""
        result = transform_row(raw_row, scorecard_cips, bls_socs, set())
        assert result["has_onet_match"] is False

    def test_all_false_with_empty_lookups(self, raw_row):
        """All flags false with empty lookup sets."""
        result = transform_row(raw_row, set(), set(), set())
        assert result["has_scorecard_match"] is False
        assert result["has_bls_match"] is False
        assert result["has_onet_match"] is False

    def test_match_uses_cipcode_not_cip_title(self, raw_row, bls_socs, onet_socs):
        """Match should be on cipcode value, not title."""
        # 52.0201 should match, but not some random code
        scorecard = {"52.0201"}
        result = transform_row(raw_row, scorecard, bls_socs, onet_socs)
        assert result["has_scorecard_match"] is True

        result2 = transform_row(raw_row, {"99.0000"}, bls_socs, onet_socs)
        assert result2["has_scorecard_match"] is False


# ---------------------------------------------------------------------------
# TestMatchQuality
# ---------------------------------------------------------------------------

class TestMatchQuality:
    """Tests for match_quality derivation."""

    def test_full(self):
        assert derive_match_quality(True, True, True) == "full"

    def test_partial_no_onet(self):
        assert derive_match_quality(True, True, False) == "partial_no_onet"

    def test_partial_no_bls(self):
        assert derive_match_quality(True, False, True) == "partial_no_bls"

    def test_scorecard_only(self):
        assert derive_match_quality(True, False, False) == "scorecard_only"

    def test_no_scorecard_all_false(self):
        assert derive_match_quality(False, False, False) == "no_scorecard"

    def test_no_scorecard_with_bls(self):
        """Even if BLS matches, no_scorecard takes precedence."""
        assert derive_match_quality(False, True, False) == "no_scorecard"

    def test_no_scorecard_with_onet(self):
        """Even if O*NET matches, no_scorecard takes precedence."""
        assert derive_match_quality(False, False, True) == "no_scorecard"

    def test_no_scorecard_with_both(self):
        """Even if both BLS and O*NET match, no_scorecard takes precedence."""
        assert derive_match_quality(False, True, True) == "no_scorecard"

    def test_match_quality_in_transform_row(self, raw_row, scorecard_cips, bls_socs, onet_socs):
        """Verify match_quality is computed in the full transform."""
        result = transform_row(raw_row, scorecard_cips, bls_socs, onet_socs)
        assert result["match_quality"] == "full"

    def test_match_quality_no_scorecard_in_transform(self, raw_row, bls_socs, onet_socs):
        result = transform_row(raw_row, set(), bls_socs, onet_socs)
        assert result["match_quality"] == "no_scorecard"

    def test_all_quality_values_valid(self):
        """Verify all possible combinations produce valid quality values."""
        for sc in (True, False):
            for bls in (True, False):
                for onet in (True, False):
                    result = derive_match_quality(sc, bls, onet)
                    assert result in VALID_MATCH_QUALITIES


# ---------------------------------------------------------------------------
# TestCipFamily
# ---------------------------------------------------------------------------

class TestCipFamily:
    """Tests for cip_family derivation."""

    def test_business_family(self, raw_row, scorecard_cips, bls_socs, onet_socs):
        result = transform_row(raw_row, scorecard_cips, bls_socs, onet_socs)
        assert result["cip_family"] == "52"

    def test_cs_family(self, raw_row, scorecard_cips, bls_socs, onet_socs):
        raw_row["cipcode"] = "11.0101"
        result = transform_row(raw_row, scorecard_cips, bls_socs, onet_socs)
        assert result["cip_family"] == "11"

    def test_leading_zero_family(self, raw_row, scorecard_cips, bls_socs, onet_socs):
        raw_row["cipcode"] = "01.0000"
        raw_row["soc_code"] = "45-2011"
        result = transform_row(raw_row, scorecard_cips, bls_socs, onet_socs)
        assert result["cip_family"] == "01"


# ---------------------------------------------------------------------------
# TestSocMajorGroup
# ---------------------------------------------------------------------------

class TestSocMajorGroup:
    """Tests for SOC major group derivation."""

    def test_management_group(self, raw_row, scorecard_cips, bls_socs, onet_socs):
        result = transform_row(raw_row, scorecard_cips, bls_socs, onet_socs)
        assert result["soc_major_group"] == "11"

    def test_computer_group(self, raw_row, scorecard_cips, bls_socs, onet_socs):
        raw_row["soc_code"] = "15-1252"
        result = transform_row(raw_row, scorecard_cips, bls_socs, onet_socs)
        assert result["soc_major_group"] == "15"

    def test_all_23_groups_valid(self):
        assert len(VALID_SOC_MAJOR_GROUPS) == 23  # 22 civilian + 55 (Military)

    def test_invalid_major_group_filtered(self, scorecard_cips, bls_socs, onet_socs):
        """SOC code with major group not in the 22 valid groups is filtered."""
        raw = {
            "cipcode": "52.0201",
            "cip_title": "Business.",
            "soc_code": "99-1234",
            "soc_title": "Invalid",
            "load_date": datetime.date(2026, 4, 8),
        }
        result = transform_row(raw, scorecard_cips, bls_socs, onet_socs)
        assert result is None


# ---------------------------------------------------------------------------
# TestValidation
# ---------------------------------------------------------------------------

class TestValidation:
    """Tests for format validation."""

    def test_invalid_cip_format_returns_none(self, scorecard_cips, bls_socs, onet_socs):
        raw = {
            "cipcode": "ABCDEF",
            "cip_title": "Bad CIP",
            "soc_code": "11-1021",
            "soc_title": "Valid SOC",
            "load_date": datetime.date(2026, 4, 8),
        }
        result = transform_row(raw, scorecard_cips, bls_socs, onet_socs)
        assert result is None

    def test_invalid_soc_format_returns_none(self, scorecard_cips, bls_socs, onet_socs):
        raw = {
            "cipcode": "52.0201",
            "cip_title": "Business",
            "soc_code": "111021",
            "soc_title": "Bad SOC",
            "load_date": datetime.date(2026, 4, 8),
        }
        result = transform_row(raw, scorecard_cips, bls_socs, onet_socs)
        assert result is None

    def test_null_cipcode_returns_none(self, scorecard_cips, bls_socs, onet_socs):
        raw = {
            "cipcode": None,
            "soc_code": "11-1021",
            "load_date": datetime.date(2026, 4, 8),
        }
        result = transform_row(raw, scorecard_cips, bls_socs, onet_socs)
        assert result is None

    def test_null_soc_code_returns_none(self, scorecard_cips, bls_socs, onet_socs):
        raw = {
            "cipcode": "52.0201",
            "soc_code": None,
            "load_date": datetime.date(2026, 4, 8),
        }
        result = transform_row(raw, scorecard_cips, bls_socs, onet_socs)
        assert result is None

    def test_cip_missing_dot_returns_none(self, scorecard_cips, bls_socs, onet_socs):
        raw = {
            "cipcode": "520201",
            "cip_title": "Business",
            "soc_code": "11-1021",
            "soc_title": "Managers",
            "load_date": datetime.date(2026, 4, 8),
        }
        result = transform_row(raw, scorecard_cips, bls_socs, onet_socs)
        assert result is None

    def test_soc_with_dot_returns_none(self, scorecard_cips, bls_socs, onet_socs):
        """O*NET format XX-XXXX.XX should be rejected (Bronze stores XX-XXXX)."""
        raw = {
            "cipcode": "52.0201",
            "cip_title": "Business",
            "soc_code": "11-1021.00",
            "soc_title": "Managers",
            "load_date": datetime.date(2026, 4, 8),
        }
        result = transform_row(raw, scorecard_cips, bls_socs, onet_socs)
        assert result is None


# ---------------------------------------------------------------------------
# TestSilverSchema
# ---------------------------------------------------------------------------

class TestSilverSchema:
    """Tests for the Silver Iceberg schema."""

    def test_schema_field_count(self):
        schema = get_silver_schema()
        assert len(schema.fields) == 13

    def test_all_fields_required(self):
        """All 13 Silver columns are NOT NULL per spec."""
        schema = get_silver_schema()
        for field in schema.fields:
            assert field.required, f"Field {field.name} should be required (NOT NULL)"

    def test_required_field_names(self):
        schema = get_silver_schema()
        field_names = {f.name for f in schema.fields}
        expected = {
            "record_id", "cipcode", "cip_title", "cip_family",
            "soc_code", "soc_title", "soc_major_group",
            "has_scorecard_match", "has_bls_match", "has_onet_match",
            "match_quality", "source_load_date", "ingested_at",
        }
        assert field_names == expected

    def test_boolean_fields(self):
        from pyiceberg.types import BooleanType
        schema = get_silver_schema()
        bool_fields = {f.name for f in schema.fields if isinstance(f.field_type, BooleanType)}
        assert bool_fields == {"has_scorecard_match", "has_bls_match", "has_onet_match"}


# ---------------------------------------------------------------------------
# TestGrainFields
# ---------------------------------------------------------------------------

class TestGrainFields:
    """Tests for grain field configuration."""

    def test_grain_fields_correct(self):
        assert GRAIN_FIELDS == ["cipcode", "soc_code"]

    def test_grain_uniqueness(self, raw_row, scorecard_cips, bls_socs, onet_socs):
        """Same cipcode+soc_code produces same record_id."""
        r1 = transform_row(raw_row, scorecard_cips, bls_socs, onet_socs)
        r2 = transform_row(raw_row, scorecard_cips, bls_socs, onet_socs)
        assert r1["record_id"] == r2["record_id"]


# ---------------------------------------------------------------------------
# TestOutputCompleteness
# ---------------------------------------------------------------------------

class TestOutputCompleteness:
    """Tests verifying all output fields are populated."""

    def test_all_14_fields_present(self, raw_row, scorecard_cips, bls_socs, onet_socs):
        result = transform_row(raw_row, scorecard_cips, bls_socs, onet_socs)
        expected_fields = {
            "record_id", "cipcode", "cip_title", "cip_family",
            "soc_code", "soc_title", "soc_major_group",
            "has_scorecard_match", "has_bls_match", "has_onet_match",
            "match_quality", "source_load_date", "ingested_at",
        }
        assert set(result.keys()) == expected_fields

    def test_no_none_values(self, raw_row, scorecard_cips, bls_socs, onet_socs):
        """All output fields should be non-None for a valid row."""
        result = transform_row(raw_row, scorecard_cips, bls_socs, onet_socs)
        for key, value in result.items():
            assert value is not None, f"Field {key} should not be None"
