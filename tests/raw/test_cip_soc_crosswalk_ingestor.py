"""Tests for CipSocCrosswalkIngestor."""

import re
from pathlib import Path

import pytest

from raw.cip_soc_crosswalk_ingestor import CipSocCrosswalkIngestor

SAMPLE_XLSX = Path(__file__).parent / "cip_soc_crosswalk_sample.xlsx"


def _make_ingestor():
    """Create a CipSocCrosswalkIngestor without requiring real config objects.

    Uses __new__ to skip BaseIngestor.__init__ which requires
    source_config and manifest. Safe for testing schema/constants.
    """
    obj = CipSocCrosswalkIngestor.__new__(CipSocCrosswalkIngestor)
    return obj


def _fetch_sample(ingestor):
    """Run fetch() on the local sample XLSX and return the raw rows."""
    entities = {"crosswalk": "CIP-SOC Crosswalk"}
    result = ingestor.fetch(entities, "xlsx_download", xlsx_path=str(SAMPLE_XLSX))
    return result["crosswalk"]


class TestSchema:
    """Tests for get_schema()."""

    def test_get_schema_returns_schema(self):
        """Verify get_schema returns a valid Iceberg Schema."""
        from pyiceberg.schema import Schema

        ingestor = _make_ingestor()
        schema = ingestor.get_schema()
        assert isinstance(schema, Schema)

    def test_schema_has_grain_fields(self):
        """Verify schema includes the grain fields: cipcode, soc_code."""
        ingestor = _make_ingestor()
        schema = ingestor.get_schema()
        field_names = [field.name for field in schema.fields]
        assert "cipcode" in field_names
        assert "soc_code" in field_names

    def test_schema_has_metadata_fields(self):
        """Verify schema includes framework metadata fields."""
        ingestor = _make_ingestor()
        schema = ingestor.get_schema()
        field_names = [field.name for field in schema.fields]
        for name in ("ingested_at", "source_url", "source_method", "load_date"):
            assert name in field_names

    def test_schema_has_all_data_fields(self):
        """Verify schema includes all expected data fields."""
        ingestor = _make_ingestor()
        schema = ingestor.get_schema()
        field_names = [field.name for field in schema.fields]
        expected = ["cipcode", "cip_title", "soc_code", "soc_title"]
        for name in expected:
            assert name in field_names

    def test_schema_field_count(self):
        """Verify schema has the expected number of fields (4 data + 4 metadata)."""
        ingestor = _make_ingestor()
        schema = ingestor.get_schema()
        assert len(schema.fields) == 8


class TestConstants:
    """Tests for class-level constants."""

    def test_download_url_is_set(self):
        """Verify the download URL constant is configured."""
        assert "nces.ed.gov" in CipSocCrosswalkIngestor.DOWNLOAD_URL

    def test_column_map_has_four_fields(self):
        """Verify COLUMN_MAP covers all 4 data columns."""
        assert len(CipSocCrosswalkIngestor.COLUMN_MAP) == 4

    def test_column_map_keys_match_xlsx(self):
        """Verify COLUMN_MAP keys match the expected XLSX column names."""
        expected_keys = {"CIP2020Code", "CIP2020Title", "SOC2018Code", "SOC2018Title"}
        assert set(CipSocCrosswalkIngestor.COLUMN_MAP.keys()) == expected_keys

    def test_column_map_values_are_lowercase(self):
        """Verify COLUMN_MAP values are lowercase Iceberg field names."""
        for value in CipSocCrosswalkIngestor.COLUMN_MAP.values():
            assert value == value.lower()

    def test_target_sheet_name(self):
        """Verify the target sheet name matches the NCES XLSX structure."""
        assert CipSocCrosswalkIngestor.TARGET_SHEET == "CIP-SOC"


class TestFetch:
    """Tests for fetch() using the local sample XLSX."""

    def test_fetch_returns_dict(self):
        """Verify fetch() returns a dict keyed by entity id."""
        ingestor = _make_ingestor()
        entities = {"crosswalk": "CIP-SOC Crosswalk"}
        result = ingestor.fetch(entities, "xlsx_download", xlsx_path=str(SAMPLE_XLSX))
        assert isinstance(result, dict)
        assert "crosswalk" in result

    def test_fetch_returns_rows(self):
        """Verify fetch() returns a non-empty list of row dicts."""
        ingestor = _make_ingestor()
        rows = _fetch_sample(ingestor)
        assert isinstance(rows, list)
        assert len(rows) > 0
        assert isinstance(rows[0], dict)

    def test_fetch_loads_from_local_xlsx_path(self):
        """Verify fetch() can load from a local xlsx_path kwarg."""
        ingestor = _make_ingestor()
        entities = {"test": "Test"}
        result = ingestor.fetch(entities, "test", xlsx_path=str(SAMPLE_XLSX))
        assert len(result["test"]) > 0

    def test_fetch_row_count(self):
        """Verify the expected number of data rows (12 string + 2 float CIP = 14)."""
        ingestor = _make_ingestor()
        rows = _fetch_sample(ingestor)
        assert len(rows) == 14

    def test_fetch_preserves_no_match_rows(self):
        """Verify fetch() does not filter out 99-9999 sentinel rows (that's Silver's job)."""
        ingestor = _make_ingestor()
        rows = _fetch_sample(ingestor)
        no_match = [r for r in rows if str(r.get("soc_code", "")).strip() == "99-9999"]
        assert len(no_match) == 2

    def test_fetch_reads_correct_sheet(self):
        """Verify fetch() reads from the CIP-SOC sheet, not File Guide."""
        ingestor = _make_ingestor()
        rows = _fetch_sample(ingestor)
        # If it read the wrong sheet, we'd get nonsensical data
        assert any("cipcode" in r for r in rows)


class TestFlatten:
    """Tests for flatten() -- CIP code coercion, field mapping."""

    def test_flatten_returns_list_of_dicts(self):
        """Verify flatten() returns a list of dicts."""
        ingestor = _make_ingestor()
        rows = _fetch_sample(ingestor)
        flat = ingestor.flatten(rows, "crosswalk")
        assert isinstance(flat, list)
        assert len(flat) > 0
        assert isinstance(flat[0], dict)

    def test_flatten_uses_lowercase_keys(self):
        """Verify flatten() uses lowercase Iceberg field names."""
        ingestor = _make_ingestor()
        rows = _fetch_sample(ingestor)
        flat = ingestor.flatten(rows, "crosswalk")
        expected_keys = {"cipcode", "cip_title", "soc_code", "soc_title"}
        for record in flat:
            assert set(record.keys()) == expected_keys

    def test_flatten_cipcode_is_string(self):
        """Verify all CIP codes are strings after flattening."""
        ingestor = _make_ingestor()
        rows = _fetch_sample(ingestor)
        flat = ingestor.flatten(rows, "crosswalk")
        for record in flat:
            assert isinstance(record["cipcode"], str)

    def test_flatten_cipcode_format(self):
        """Verify all CIP codes match XX.XXXX format."""
        ingestor = _make_ingestor()
        rows = _fetch_sample(ingestor)
        flat = ingestor.flatten(rows, "crosswalk")
        for record in flat:
            assert re.match(r"^\d{2}\.\d{4}$", record["cipcode"]), (
                f"Invalid CIP format: {record['cipcode']}"
            )

    def test_flatten_soc_code_is_string(self):
        """Verify all SOC codes are strings after flattening."""
        ingestor = _make_ingestor()
        rows = _fetch_sample(ingestor)
        flat = ingestor.flatten(rows, "crosswalk")
        for record in flat:
            assert isinstance(record["soc_code"], str)

    def test_flatten_soc_code_format(self):
        """Verify all SOC codes match XX-XXXX format (including 99-9999)."""
        ingestor = _make_ingestor()
        rows = _fetch_sample(ingestor)
        flat = ingestor.flatten(rows, "crosswalk")
        for record in flat:
            assert re.match(r"^\d{2}-\d{4}$", record["soc_code"]), (
                f"Invalid SOC format: {record['soc_code']}"
            )

    def test_flatten_float_cipcode_converted(self):
        """Verify float CIP codes from openpyxl are converted to XX.XXXX strings."""
        ingestor = _make_ingestor()
        rows = _fetch_sample(ingestor)
        flat = ingestor.flatten(rows, "crosswalk")
        # The sample has 14.0101 as a float -- should become "14.0101"
        engineering = [r for r in flat if r["cip_title"] == "Engineering, General."]
        assert len(engineering) == 1
        assert engineering[0]["cipcode"] == "14.0101"

    def test_flatten_float_cipcode_leading_zero(self):
        """Verify float CIP 1.0000 is zero-padded to '01.0000'."""
        ingestor = _make_ingestor()
        rows = _fetch_sample(ingestor)
        flat = ingestor.flatten(rows, "crosswalk")
        agriculture = [r for r in flat if r["cip_title"] == "Agriculture, General."]
        assert len(agriculture) == 1
        assert agriculture[0]["cipcode"] == "01.0000"

    def test_flatten_preserves_no_match_rows(self):
        """Verify flatten() preserves 99-9999 sentinel rows (filtering is Silver's job)."""
        ingestor = _make_ingestor()
        rows = _fetch_sample(ingestor)
        flat = ingestor.flatten(rows, "crosswalk")
        no_match = [r for r in flat if r["soc_code"] == "99-9999"]
        assert len(no_match) == 2

    def test_flatten_does_not_add_metadata_fields(self):
        """Verify flatten() does NOT add ingested_at, source_url, etc."""
        ingestor = _make_ingestor()
        rows = _fetch_sample(ingestor)
        flat = ingestor.flatten(rows, "crosswalk")
        metadata_fields = {"ingested_at", "source_url", "source_method", "load_date"}
        for record in flat:
            assert metadata_fields.isdisjoint(set(record.keys()))

    def test_flatten_skips_null_fields(self):
        """Verify rows with null cipcode or soc_code are skipped."""
        ingestor = _make_ingestor()
        raw_data = [
            {"cipcode": None, "cip_title": "Unknown", "soc_code": "11-1021", "soc_title": "Test"},
            {"cipcode": "52.0201", "cip_title": "Business", "soc_code": None, "soc_title": "Test"},
            {"cipcode": "52.0201", "cip_title": "Business", "soc_code": "11-1021", "soc_title": "Valid"},
        ]
        flat = ingestor.flatten(raw_data, "test")
        assert len(flat) == 1
        assert flat[0]["cipcode"] == "52.0201"

    def test_flatten_strips_whitespace(self):
        """Verify title fields are stripped of whitespace."""
        ingestor = _make_ingestor()
        raw_data = [
            {
                "cipcode": "52.0201",
                "cip_title": "  Business Admin  ",
                "soc_code": "11-1021",
                "soc_title": "  General Managers  ",
            },
        ]
        flat = ingestor.flatten(raw_data, "test")
        assert flat[0]["cip_title"] == "Business Admin"
        assert flat[0]["soc_title"] == "General Managers"


class TestCoerceCipcode:
    """Tests for CIP code coercion edge cases."""

    def test_none_returns_none(self):
        assert CipSocCrosswalkIngestor._coerce_cipcode(None) is None

    def test_empty_string_returns_none(self):
        assert CipSocCrosswalkIngestor._coerce_cipcode("") is None

    def test_float_52_0201(self):
        assert CipSocCrosswalkIngestor._coerce_cipcode(52.0201) == "52.0201"

    def test_float_1_0(self):
        """Float 1.0 should become '01.0000'."""
        assert CipSocCrosswalkIngestor._coerce_cipcode(1.0) == "01.0000"

    def test_float_14_0101(self):
        assert CipSocCrosswalkIngestor._coerce_cipcode(14.0101) == "14.0101"

    def test_string_already_formatted(self):
        assert CipSocCrosswalkIngestor._coerce_cipcode("52.0201") == "52.0201"

    def test_string_short_detail(self):
        """String '52.02' should be padded to '52.0200'."""
        assert CipSocCrosswalkIngestor._coerce_cipcode("52.02") == "52.0200"

    def test_string_single_digit_family(self):
        """String '1.0000' should be padded to '01.0000'."""
        assert CipSocCrosswalkIngestor._coerce_cipcode("1.0000") == "01.0000"

    def test_integer_input(self):
        """Integer 52 should produce a zero-padded result."""
        result = CipSocCrosswalkIngestor._coerce_cipcode(52)
        assert isinstance(result, str)
        assert "." in result


class TestCoerceSoc:
    """Tests for SOC code coercion edge cases."""

    def test_none_returns_none(self):
        assert CipSocCrosswalkIngestor._coerce_soc(None) is None

    def test_empty_string_returns_none(self):
        assert CipSocCrosswalkIngestor._coerce_soc("") is None

    def test_string_passthrough(self):
        assert CipSocCrosswalkIngestor._coerce_soc("15-1252") == "15-1252"

    def test_sentinel_passthrough(self):
        assert CipSocCrosswalkIngestor._coerce_soc("99-9999") == "99-9999"

    def test_strips_whitespace(self):
        assert CipSocCrosswalkIngestor._coerce_soc("  15-1252  ") == "15-1252"


FULL_XLSX = Path("data/raw/xlsx_cache/CIP2020_SOC2018_Crosswalk.xlsx")


class TestFullDataset:
    """Tests against the full NCES crosswalk XLSX.

    These tests require the real XLSX file at data/raw/xlsx_cache/.
    Skip if the file doesn't exist.
    """

    @pytest.fixture(autouse=True)
    def skip_if_no_data(self):
        if not FULL_XLSX.exists():
            pytest.skip("Full NCES crosswalk XLSX not available")

    def test_full_row_count_in_range(self):
        """Verify full dataset has 5500-6500 rows (EDA found 6097)."""
        ingestor = _make_ingestor()
        raw = ingestor.fetch({"xw": "CIP-SOC"}, "xlsx", xlsx_path=str(FULL_XLSX))
        flat = ingestor.flatten(raw["xw"], "xw")
        assert 5500 <= len(flat) <= 6500, f"Expected 5500-6500 rows, got {len(flat)}"

    def test_full_all_cip_codes_valid(self):
        """Verify all CIP codes match XX.XXXX format."""
        ingestor = _make_ingestor()
        raw = ingestor.fetch({"xw": "CIP-SOC"}, "xlsx", xlsx_path=str(FULL_XLSX))
        flat = ingestor.flatten(raw["xw"], "xw")
        for r in flat:
            assert re.match(r"^\d{2}\.\d{4}$", r["cipcode"]), f"Bad CIP: {r['cipcode']}"

    def test_full_all_soc_codes_valid(self):
        """Verify all SOC codes match XX-XXXX format."""
        ingestor = _make_ingestor()
        raw = ingestor.fetch({"xw": "CIP-SOC"}, "xlsx", xlsx_path=str(FULL_XLSX))
        flat = ingestor.flatten(raw["xw"], "xw")
        for r in flat:
            assert re.match(r"^\d{2}-\d{4}$", r["soc_code"]), f"Bad SOC: {r['soc_code']}"

    def test_full_no_duplicate_grain(self):
        """Verify no duplicate cipcode x soc_code pairs."""
        ingestor = _make_ingestor()
        raw = ingestor.fetch({"xw": "CIP-SOC"}, "xlsx", xlsx_path=str(FULL_XLSX))
        flat = ingestor.flatten(raw["xw"], "xw")
        grains = [(r["cipcode"], r["soc_code"]) for r in flat]
        assert len(grains) == len(set(grains)), "Duplicate grain found"

    def test_full_has_no_match_rows(self):
        """Verify the full dataset contains 99-9999 sentinel rows."""
        ingestor = _make_ingestor()
        raw = ingestor.fetch({"xw": "CIP-SOC"}, "xlsx", xlsx_path=str(FULL_XLSX))
        flat = ingestor.flatten(raw["xw"], "xw")
        no_match = [r for r in flat if r["soc_code"] == "99-9999"]
        assert len(no_match) > 100, f"Expected >100 no-match rows, got {len(no_match)}"
