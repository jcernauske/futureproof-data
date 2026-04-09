"""Tests for BlsOohIngestor."""

from pathlib import Path

import pytest

from raw.bls_ooh_ingestor import BlsOohIngestor

SAMPLE_XLSX = Path(__file__).parent / "bls_ooh_sample.xlsx"


def _make_ingestor():
    """Create a BlsOohIngestor without requiring real config objects.

    Uses __new__ to skip BaseIngestor.__init__ which requires
    source_config and manifest. Safe for testing schema/constants.
    """
    obj = BlsOohIngestor.__new__(BlsOohIngestor)
    return obj


def _fetch_sample(ingestor):
    """Run fetch() on the local sample XLSX and return the raw rows."""
    entities = {"occupations": "All Occupations"}
    result = ingestor.fetch(entities, "bulk_xlsx_download", xlsx_path=str(SAMPLE_XLSX))
    return result["occupations"]


class TestSchema:
    """Tests for get_schema()."""

    def test_get_schema_returns_schema(self):
        """Verify get_schema returns a valid Iceberg Schema."""
        from pyiceberg.schema import Schema

        ingestor = _make_ingestor()
        schema = ingestor.get_schema()
        assert isinstance(schema, Schema)

    def test_schema_has_grain_field(self):
        """Verify schema includes the grain field: soc_code."""
        ingestor = _make_ingestor()
        schema = ingestor.get_schema()
        field_names = [field.name for field in schema.fields]
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
        expected = [
            "soc_code",
            "occupation_title",
            "employment_current",
            "employment_projected",
            "employment_change",
            "employment_change_pct",
            "openings_annual_avg",
            "median_annual_wage",
            "median_wage_capped",
            "education_typical",
            "education_code",
            "work_experience",
            "work_experience_code",
            "training_typical",
            "training_code",
        ]
        for name in expected:
            assert name in field_names

    def test_schema_field_count(self):
        """Verify schema has the expected number of fields (15 data + 4 metadata)."""
        ingestor = _make_ingestor()
        schema = ingestor.get_schema()
        assert len(schema.fields) == 19


class TestConstants:
    """Tests for class-level constants."""

    def test_download_url_is_set(self):
        """Verify the download URL constant is configured."""
        assert "bls.gov" in BlsOohIngestor.DOWNLOAD_URL

    def test_user_agent_is_browser_like(self):
        """Verify User-Agent header looks like a browser, not a bot."""
        assert "Mozilla" in BlsOohIngestor.USER_AGENT
        assert "Chrome" in BlsOohIngestor.USER_AGENT

    def test_column_map_has_all_fields(self):
        """Verify COLUMN_MAP covers all 14 data fields."""
        assert len(BlsOohIngestor.COLUMN_MAP) == 14
        assert "soc_code" in BlsOohIngestor.COLUMN_MAP
        assert "median_annual_wage" in BlsOohIngestor.COLUMN_MAP
        assert "occupation_title" in BlsOohIngestor.COLUMN_MAP


class TestFetch:
    """Tests for fetch() using the local sample XLSX."""

    def test_fetch_returns_dict(self):
        """Verify fetch() returns a dict keyed by entity id."""
        ingestor = _make_ingestor()
        entities = {"occupations": "All Occupations"}
        result = ingestor.fetch(entities, "bulk_xlsx_download", xlsx_path=str(SAMPLE_XLSX))
        assert isinstance(result, dict)
        assert "occupations" in result

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

    def test_fetch_filters_out_summary_rows(self):
        """Verify summary rows (SOC ending in 0000) are excluded."""
        ingestor = _make_ingestor()
        rows = _fetch_sample(ingestor)
        for row in rows:
            soc = str(row["soc_code"]).replace("-", "")
            assert not soc.endswith("0000"), f"Summary row {row['soc_code']} should be filtered"

    def test_fetch_row_count(self):
        """Verify the expected number of detail rows (11 total - 1 summary = 10)."""
        ingestor = _make_ingestor()
        rows = _fetch_sample(ingestor)
        assert len(rows) == 10


class TestFlatten:
    """Tests for flatten() -- type coercion, wage parsing, column mapping."""

    def test_flatten_returns_list_of_dicts(self):
        """Verify flatten() returns a list of dicts."""
        ingestor = _make_ingestor()
        rows = _fetch_sample(ingestor)
        flat = ingestor.flatten(rows, "occupations")
        assert isinstance(flat, list)
        assert len(flat) > 0
        assert isinstance(flat[0], dict)

    def test_flatten_uses_lowercase_keys(self):
        """Verify flatten() uses lowercase Iceberg field names."""
        ingestor = _make_ingestor()
        rows = _fetch_sample(ingestor)
        flat = ingestor.flatten(rows, "occupations")
        expected_keys = {
            "soc_code",
            "occupation_title",
            "employment_current",
            "employment_projected",
            "employment_change",
            "employment_change_pct",
            "openings_annual_avg",
            "median_annual_wage",
            "median_wage_capped",
            "education_typical",
            "education_code",
            "work_experience",
            "work_experience_code",
            "training_typical",
            "training_code",
        }
        for record in flat:
            assert set(record.keys()) == expected_keys

    def test_flatten_wage_capping(self):
        """Verify '>=239,200' is parsed to 239200.0 with median_wage_capped=True."""
        ingestor = _make_ingestor()
        rows = _fetch_sample(ingestor)
        flat = ingestor.flatten(rows, "occupations")
        # Surgeons row has top-coded wage
        surgeons = [r for r in flat if r["soc_code"] == "29-1248"]
        assert len(surgeons) == 1
        assert surgeons[0]["median_annual_wage"] == 239200.0
        assert surgeons[0]["median_wage_capped"] is True

    def test_flatten_na_wage(self):
        """Verify 'N/A' wage is parsed to None with median_wage_capped=False."""
        ingestor = _make_ingestor()
        rows = _fetch_sample(ingestor)
        flat = ingestor.flatten(rows, "occupations")
        # Legislators row has N/A wage
        legislators = [r for r in flat if r["soc_code"] == "11-1031"]
        assert len(legislators) == 1
        assert legislators[0]["median_annual_wage"] is None
        assert legislators[0]["median_wage_capped"] is False

    def test_flatten_converts_employment_from_thousands(self):
        """Verify employment figures are multiplied by 1000."""
        ingestor = _make_ingestor()
        rows = _fetch_sample(ingestor)
        flat = ingestor.flatten(rows, "occupations")
        # Software developers: 1795.5 thousand -> 1795500
        devs = [r for r in flat if r["soc_code"] == "15-1252"]
        assert len(devs) == 1
        assert devs[0]["employment_current"] == 1795500
        assert isinstance(devs[0]["employment_current"], int)

    def test_flatten_soc_code_stays_string(self):
        """Verify SOC codes remain as strings."""
        ingestor = _make_ingestor()
        rows = _fetch_sample(ingestor)
        flat = ingestor.flatten(rows, "occupations")
        for record in flat:
            assert isinstance(record["soc_code"], str)

    def test_flatten_coerces_education_codes_to_int(self):
        """Verify education, work experience, and training codes are int."""
        ingestor = _make_ingestor()
        rows = _fetch_sample(ingestor)
        flat = ingestor.flatten(rows, "occupations")
        for record in flat:
            if record["education_code"] is not None:
                assert isinstance(record["education_code"], int)
            if record["work_experience_code"] is not None:
                assert isinstance(record["work_experience_code"], int)
            if record["training_code"] is not None:
                assert isinstance(record["training_code"], int)

    def test_flatten_skips_null_grain_fields(self):
        """Verify rows with null soc_code are skipped."""
        ingestor = _make_ingestor()
        raw_data = [
            {"soc_code": None, "occupation_title": "Unknown"},
            {"soc_code": "15-1252", "occupation_title": "Software developers"},
        ]
        flat = ingestor.flatten(raw_data, "test")
        assert len(flat) == 1
        assert flat[0]["soc_code"] == "15-1252"

    def test_flatten_does_not_add_metadata_fields(self):
        """Verify flatten() does NOT add ingested_at, source_url, etc."""
        ingestor = _make_ingestor()
        rows = _fetch_sample(ingestor)
        flat = ingestor.flatten(rows, "occupations")
        metadata_fields = {"ingested_at", "source_url", "source_method", "load_date"}
        for record in flat:
            assert metadata_fields.isdisjoint(set(record.keys()))


class TestCoerceEdgeCases:
    """Tests for coercion edge cases."""

    def test_none_input_returns_none(self):
        """Verify None input returns None for various coercion methods."""
        ingestor = _make_ingestor()
        assert ingestor._coerce_soc(None) is None
        assert ingestor._coerce_string(None) is None
        assert ingestor._coerce_employment(None) is None
        assert ingestor._coerce_double(None) is None
        assert ingestor._coerce_int(None) is None

    def test_empty_string_returns_none(self):
        """Verify empty strings return None."""
        ingestor = _make_ingestor()
        assert ingestor._coerce_soc("") is None
        assert ingestor._coerce_string("") is None
        assert ingestor._coerce_employment("") is None
        assert ingestor._coerce_double("") is None
        assert ingestor._coerce_int("") is None

    def test_dollar_signs_and_commas_stripped_from_wage(self):
        """Verify wage parsing handles $ and commas."""
        ingestor = _make_ingestor()
        wage, capped = ingestor._parse_wage("$130,160")
        assert wage == 130160.0
        assert capped is False

    def test_wage_or_more_pattern(self):
        """Verify '$239,200 or more' pattern is detected as capped."""
        ingestor = _make_ingestor()
        wage, capped = ingestor._parse_wage("$239,200 or more")
        assert wage == 239200.0
        assert capped is True

    def test_wage_none_returns_none_false(self):
        """Verify None wage returns (None, False)."""
        ingestor = _make_ingestor()
        wage, capped = ingestor._parse_wage(None)
        assert wage is None
        assert capped is False

    def test_negative_employment_change(self):
        """Verify negative employment change values are handled correctly."""
        ingestor = _make_ingestor()
        raw_data = [{
            "soc_code": "43-9021",
            "occupation_title": "Data entry keyers",
            "employment_current": 150.0,
            "employment_projected": 120.0,
            "employment_change_num": -30.0,
            "employment_change_pct": -20.0,
            "openings_annual_avg": 10.0,
            "median_annual_wage": 38000,
            "education_typical": "High school diploma or equivalent",
            "work_experience": "None",
            "training_typical": "Moderate-term on-the-job training",
        }]
        flat = ingestor.flatten(raw_data, "test")
        assert len(flat) == 1
        assert flat[0]["employment_change"] == -30000
        assert flat[0]["employment_change_pct"] == -20.0

    def test_derive_code_from_label(self):
        """Verify education/experience/training codes are derived from string labels."""
        ingestor = _make_ingestor()
        raw_data = [{
            "soc_code": "15-1252",
            "occupation_title": "Software developers",
            "employment_current": 1800.0,
            "employment_projected": 2100.0,
            "employment_change_num": 300.0,
            "employment_change_pct": 16.7,
            "openings_annual_avg": 150.0,
            "median_annual_wage": 130000,
            "education_typical": "Bachelor's degree",
            "work_experience": "None",
            "training_typical": "None",
        }]
        flat = ingestor.flatten(raw_data, "test")
        assert flat[0]["education_code"] == 3  # Bachelor's degree
        assert flat[0]["work_experience_code"] == 3  # None required
        assert flat[0]["training_code"] == 6  # None required

    def test_derive_code_all_education_levels(self):
        """Verify all 8 BLS education levels map to codes 1-8."""
        ingestor = _make_ingestor()
        expected = {
            "Doctoral or professional degree": 1,
            "Master's degree": 2,
            "Bachelor's degree": 3,
            "Associate's degree": 4,
            "Postsecondary nondegree award": 5,
            "Some college, no degree": 6,
            "High school diploma or equivalent": 7,
            "No formal educational credential": 8,
        }
        for label, code in expected.items():
            result = ingestor._derive_code(None, label, ingestor._EDUCATION_CODE_MAP)
            assert result == code, f"{label} should map to {code}, got {result}"

    def test_derive_code_prefers_raw_code(self):
        """Verify raw code column takes precedence over label derivation."""
        ingestor = _make_ingestor()
        result = ingestor._derive_code(5, "Bachelor's degree", ingestor._EDUCATION_CODE_MAP)
        assert result == 5  # Uses raw code, not label (which would be 3)

    def test_numeric_wage_not_capped(self):
        """Verify numeric wage values (no >= notation) are not flagged as capped."""
        ingestor = _make_ingestor()
        wage, capped = ingestor._parse_wage(238380)
        assert wage == 238380.0
        assert capped is False

    def test_wage_integer_input(self):
        """Verify integer wage values (from XLSX numeric cells) are handled."""
        ingestor = _make_ingestor()
        wage, capped = ingestor._parse_wage(81680)
        assert wage == 81680.0
        assert capped is False


FULL_XLSX = Path("data/raw/xlsx_cache/bls_ooh.xlsx")


class TestFullDataset:
    """Tests against the full BLS Employment Projections dataset.

    These tests require the real BLS XLSX file at data/raw/xlsx_cache/bls_ooh.xlsx.
    Skip if the file doesn't exist (CI environments without the download).
    """

    @pytest.fixture(autouse=True)
    def skip_if_no_data(self):
        if not FULL_XLSX.exists():
            pytest.skip("Full BLS XLSX not available")

    def test_full_row_count_in_range(self):
        """Verify full dataset has 750-900 detail occupation rows."""
        ingestor = _make_ingestor()
        raw = ingestor.fetch({"ooh": "OOH"}, "xlsx", xlsx_path=str(FULL_XLSX))
        flat = ingestor.flatten(raw["ooh"], "ooh")
        assert 750 <= len(flat) <= 900, f"Expected 750-900 rows, got {len(flat)}"

    def test_full_all_soc_codes_valid(self):
        """Verify all SOC codes match XX-XXXX format."""
        import re
        ingestor = _make_ingestor()
        raw = ingestor.fetch({"ooh": "OOH"}, "xlsx", xlsx_path=str(FULL_XLSX))
        flat = ingestor.flatten(raw["ooh"], "ooh")
        for r in flat:
            assert re.match(r"^\d{2}-\d{4}$", r["soc_code"]), f"Bad SOC: {r['soc_code']}"

    def test_full_no_duplicate_soc_codes(self):
        """Verify no duplicate SOC codes in full dataset."""
        ingestor = _make_ingestor()
        raw = ingestor.fetch({"ooh": "OOH"}, "xlsx", xlsx_path=str(FULL_XLSX))
        flat = ingestor.flatten(raw["ooh"], "ooh")
        soc_codes = [r["soc_code"] for r in flat]
        assert len(soc_codes) == len(set(soc_codes)), "Duplicate SOC codes found"

    def test_full_no_summary_soc_codes(self):
        """Verify no summary SOC codes (ending in 0000) in output."""
        ingestor = _make_ingestor()
        raw = ingestor.fetch({"ooh": "OOH"}, "xlsx", xlsx_path=str(FULL_XLSX))
        flat = ingestor.flatten(raw["ooh"], "ooh")
        for r in flat:
            digits = r["soc_code"].replace("-", "")
            assert not digits.endswith("0000"), f"Summary SOC: {r['soc_code']}"

    def test_full_education_codes_complete(self):
        """Verify all 8 education codes are present in full dataset."""
        ingestor = _make_ingestor()
        raw = ingestor.fetch({"ooh": "OOH"}, "xlsx", xlsx_path=str(FULL_XLSX))
        flat = ingestor.flatten(raw["ooh"], "ooh")
        codes = set(r["education_code"] for r in flat if r["education_code"] is not None)
        assert codes == {1, 2, 3, 4, 5, 6, 7, 8}

    def test_full_has_negative_employment_change(self):
        """Verify full dataset contains declining occupations."""
        ingestor = _make_ingestor()
        raw = ingestor.fetch({"ooh": "OOH"}, "xlsx", xlsx_path=str(FULL_XLSX))
        flat = ingestor.flatten(raw["ooh"], "ooh")
        neg = [r for r in flat if r["employment_change"] is not None and r["employment_change"] < 0]
        assert len(neg) > 50, f"Expected >50 declining occupations, got {len(neg)}"

    def test_full_wage_null_rate_under_five_percent(self):
        """Verify null wage rate is under 5%."""
        ingestor = _make_ingestor()
        raw = ingestor.fetch({"ooh": "OOH"}, "xlsx", xlsx_path=str(FULL_XLSX))
        flat = ingestor.flatten(raw["ooh"], "ooh")
        null_wages = [r for r in flat if r["median_annual_wage"] is None]
        null_rate = len(null_wages) / len(flat)
        assert null_rate < 0.05, f"Null wage rate {null_rate:.1%} exceeds 5%"
