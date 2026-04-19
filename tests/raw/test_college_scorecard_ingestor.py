"""Tests for CollegeScorecardIngestor."""

from pathlib import Path


from raw.college_scorecard_ingestor import CollegeScorecardIngestor

SAMPLE_CSV = Path(__file__).parent / "college_scorecard_sample.csv"


def _make_ingestor():
    """Create a CollegeScorecardIngestor without requiring real config objects.

    Uses __new__ to skip BaseIngestor.__init__ which requires
    source_config and manifest. Safe for testing schema/constants.
    """
    obj = CollegeScorecardIngestor.__new__(CollegeScorecardIngestor)
    return obj


def _fetch_sample(ingestor):
    """Run fetch() on the local sample CSV and return the raw rows."""
    entities = {"credential_levels": "Bachelor's Degree"}
    result = ingestor.fetch(entities, "bulk_csv_download", csv_path=str(SAMPLE_CSV))
    return result["credential_levels"]


class TestSchema:
    """Tests for get_schema()."""

    def test_get_schema_returns_schema(self):
        """Verify get_schema returns a valid Iceberg Schema."""
        from pyiceberg.schema import Schema

        ingestor = _make_ingestor()
        schema = ingestor.get_schema()
        assert isinstance(schema, Schema)

    def test_schema_has_grain_fields(self):
        """Verify schema includes the grain fields: unitid, cipcode, credlev."""
        ingestor = _make_ingestor()
        schema = ingestor.get_schema()
        field_names = [field.name for field in schema.fields]
        assert "unitid" in field_names
        assert "cipcode" in field_names
        assert "credlev" in field_names

    def test_schema_has_metadata_fields(self):
        """Verify schema includes framework metadata fields."""
        ingestor = _make_ingestor()
        schema = ingestor.get_schema()
        field_names = [field.name for field in schema.fields]
        for name in ("ingested_at", "source_url", "source_method", "load_date"):
            assert name in field_names

    def test_schema_has_outcome_fields(self):
        """Verify schema includes key outcome fields."""
        ingestor = _make_ingestor()
        schema = ingestor.get_schema()
        field_names = [field.name for field in schema.fields]
        assert "md_earn_wne" in field_names
        assert "earn_mdn_hi_1yr" in field_names
        assert "earn_mdn_hi_2yr" in field_names
        assert "debt_all_stgp_eval_mdn" in field_names

    def test_schema_field_count(self):
        """Verify schema has the expected number of fields (13 data + 4 metadata)."""
        ingestor = _make_ingestor()
        schema = ingestor.get_schema()
        assert len(schema.fields) == 17


class TestConstants:
    """Tests for class-level constants."""

    def test_download_url_is_set(self):
        """Verify the download URL constant is configured."""
        assert "ed-public-download" in CollegeScorecardIngestor.DOWNLOAD_URL

    def test_fallback_url_is_set(self):
        """Verify the fallback URL points to the known working location."""
        assert "scorecard.network" in CollegeScorecardIngestor.FALLBACK_URL
        assert CollegeScorecardIngestor.FALLBACK_URL.endswith(".zip")

    def test_user_agent_contains_email(self):
        """Verify User-Agent header includes contact email."""
        assert "jeff@hyenastudios.com" in CollegeScorecardIngestor.USER_AGENT

    def test_credlev_filter_is_bachelors(self):
        """Verify MVP filter is set to bachelor's degree (CREDLEV=3)."""
        assert CollegeScorecardIngestor.CREDLEV_FILTER == 3

    def test_column_map_has_all_fields(self):
        """Verify COLUMN_MAP covers all 13 data fields."""
        assert len(CollegeScorecardIngestor.COLUMN_MAP) == 13
        assert "UNITID" in CollegeScorecardIngestor.COLUMN_MAP
        assert "CIPCODE" in CollegeScorecardIngestor.COLUMN_MAP
        assert "MD_EARN_WNE" in CollegeScorecardIngestor.COLUMN_MAP


class TestFetch:
    """Tests for fetch() using the local sample CSV."""

    def test_fetch_returns_dict(self):
        """Verify fetch() returns a dict keyed by entity id."""
        ingestor = _make_ingestor()
        entities = {"credential_levels": "Bachelor's Degree"}
        result = ingestor.fetch(entities, "bulk_csv_download", csv_path=str(SAMPLE_CSV))
        assert isinstance(result, dict)
        assert "credential_levels" in result

    def test_fetch_returns_rows(self):
        """Verify fetch() returns a non-empty list of row dicts."""
        ingestor = _make_ingestor()
        rows = _fetch_sample(ingestor)
        assert isinstance(rows, list)
        assert len(rows) > 0
        assert isinstance(rows[0], dict)

    def test_fetch_filters_credlev(self):
        """Verify all returned rows have CREDLEV=3."""
        ingestor = _make_ingestor()
        rows = _fetch_sample(ingestor)
        for row in rows:
            assert row["CREDLEV"] == "3"

    def test_fetch_preserves_cipcode_as_string(self):
        """Verify CIPCODE values are preserved as strings (not coerced to float/int)."""
        ingestor = _make_ingestor()
        rows = _fetch_sample(ingestor)
        for row in rows:
            cipcode = row["CIPCODE"]
            assert isinstance(cipcode, str)

    def test_fetch_only_keeps_target_columns(self):
        """Verify fetch() only retains columns listed in COLUMN_MAP."""
        ingestor = _make_ingestor()
        rows = _fetch_sample(ingestor)
        allowed = set(CollegeScorecardIngestor.COLUMN_MAP.keys())
        for row in rows:
            assert set(row.keys()).issubset(allowed)

    def test_fetch_returns_same_data_for_all_entities(self):
        """Verify fetch() returns the same rows for every entity key."""
        ingestor = _make_ingestor()
        entities = {"a": "first", "b": "second"}
        result = ingestor.fetch(entities, "bulk_csv_download", csv_path=str(SAMPLE_CSV))
        assert result["a"] == result["b"]

    def test_fetch_row_count_matches_sample(self):
        """Verify all 50 data rows from the sample are returned (all are CREDLEV=3)."""
        ingestor = _make_ingestor()
        rows = _fetch_sample(ingestor)
        # The sample has 50 data rows, all CREDLEV=3.
        assert len(rows) == 50


class TestFlatten:
    """Tests for flatten() — type coercion, sentinel handling, column mapping."""

    def test_flatten_returns_list_of_dicts(self):
        """Verify flatten() returns a list of dicts."""
        ingestor = _make_ingestor()
        rows = _fetch_sample(ingestor)
        flat = ingestor.flatten(rows, "credential_levels")
        assert isinstance(flat, list)
        assert len(flat) > 0
        assert isinstance(flat[0], dict)

    def test_flatten_uses_lowercase_keys(self):
        """Verify flatten() maps uppercase CSV columns to lowercase Iceberg names."""
        ingestor = _make_ingestor()
        rows = _fetch_sample(ingestor)
        flat = ingestor.flatten(rows, "credential_levels")
        expected_keys = set(CollegeScorecardIngestor.COLUMN_MAP.values())
        for record in flat:
            assert set(record.keys()) == expected_keys

    def test_flatten_converts_ps_to_none(self):
        """Verify 'PS' sentinel values are converted to None."""
        ingestor = _make_ingestor()
        # The first row in the sample has PS for DEBT_ALL_STGP_EVAL_MDN.
        rows = _fetch_sample(ingestor)
        flat = ingestor.flatten(rows, "credential_levels")
        first = flat[0]
        assert first["debt_all_stgp_eval_mdn"] is None

    def test_flatten_converts_na_to_none(self):
        """Verify 'NA' sentinel values are converted to None."""
        ingestor = _make_ingestor()
        rows = _fetch_sample(ingestor)
        flat = ingestor.flatten(rows, "credential_levels")
        # First row has NA for IPEDSCOUNT1 and IPEDSCOUNT2.
        first = flat[0]
        assert first["ipedscount1"] is None
        assert first["ipedscount2"] is None

    def test_flatten_converts_privacy_suppressed_to_none(self):
        """Verify the full 'PrivacySuppressed' string is also handled."""
        ingestor = _make_ingestor()
        raw = [{"UNITID": "100654", "INSTNM": "Test U", "CIPCODE": "11.0701",
                "CIPDESC": "CS", "CREDDESC": "Bachelor's", "CREDLEV": "3",
                "MD_EARN_WNE": "PrivacySuppressed", "EARN_MDN_HI_1YR": "50000",
                "EARN_MDN_HI_2YR": "55000", "DEBT_ALL_STGP_EVAL_MDN": "20000",
                "IPEDSCOUNT1": "100", "IPEDSCOUNT2": "50"}]
        flat = ingestor.flatten(raw, "test")
        assert flat[0]["md_earn_wne"] is None

    def test_flatten_coerces_unitid_to_int(self):
        """Verify UNITID is coerced to an integer."""
        ingestor = _make_ingestor()
        rows = _fetch_sample(ingestor)
        flat = ingestor.flatten(rows, "credential_levels")
        assert isinstance(flat[0]["unitid"], int)
        assert flat[0]["unitid"] == 100654

    def test_flatten_coerces_credlev_to_int(self):
        """Verify CREDLEV is coerced to an integer."""
        ingestor = _make_ingestor()
        rows = _fetch_sample(ingestor)
        flat = ingestor.flatten(rows, "credential_levels")
        assert isinstance(flat[0]["credlev"], int)
        assert flat[0]["credlev"] == 3

    def test_flatten_coerces_earnings_to_float(self):
        """Verify earnings fields are coerced to float when present."""
        ingestor = _make_ingestor()
        raw = [{"UNITID": "100654", "INSTNM": "Test U", "CIPCODE": "11.0701",
                "CIPDESC": "CS", "CREDDESC": "Bachelor's", "CREDLEV": "3",
                "MD_EARN_WNE": "65000", "EARN_MDN_HI_1YR": "50000",
                "EARN_MDN_HI_2YR": "55000", "DEBT_ALL_STGP_EVAL_MDN": "20000",
                "IPEDSCOUNT1": "100", "IPEDSCOUNT2": "50"}]
        flat = ingestor.flatten(raw, "test")
        assert isinstance(flat[0]["md_earn_wne"], float)
        assert flat[0]["md_earn_wne"] == 65000.0
        assert isinstance(flat[0]["earn_mdn_hi_1yr"], float)

    def test_flatten_cipcode_stays_string(self):
        """Verify CIPCODE remains a string after flatten (preserving leading zeros)."""
        ingestor = _make_ingestor()
        rows = _fetch_sample(ingestor)
        flat = ingestor.flatten(rows, "credential_levels")
        for record in flat:
            assert isinstance(record["cipcode"], str)
        # First row has CIPCODE "0100" — must not become 100 or 100.0.
        assert flat[0]["cipcode"] == "0100"

    def test_flatten_missing_column_returns_none(self):
        """Verify that a column absent from the source data produces None."""
        ingestor = _make_ingestor()
        # MD_EARN_WNE is not in the sample CSV.
        rows = _fetch_sample(ingestor)
        flat = ingestor.flatten(rows, "credential_levels")
        # Since the column is missing from the CSV, all values should be None.
        for record in flat:
            assert record["md_earn_wne"] is None

    def test_flatten_does_not_add_metadata_fields(self):
        """Verify flatten() does NOT add ingested_at, source_url, etc.

        The framework (BaseIngestor.ingest) adds these fields, not flatten().
        """
        ingestor = _make_ingestor()
        rows = _fetch_sample(ingestor)
        flat = ingestor.flatten(rows, "credential_levels")
        metadata_fields = {"ingested_at", "source_url", "source_method", "load_date"}
        for record in flat:
            assert metadata_fields.isdisjoint(set(record.keys()))

    def test_flatten_row_count_matches_fetch(self):
        """Verify flatten() produces one output row per input row."""
        ingestor = _make_ingestor()
        rows = _fetch_sample(ingestor)
        flat = ingestor.flatten(rows, "credential_levels")
        assert len(flat) == len(rows)

    def test_flatten_ipedscount_coerced_to_int(self):
        """Verify IPEDSCOUNT fields are coerced to int when numeric."""
        ingestor = _make_ingestor()
        # Row index 2 has IPEDSCOUNT1=3, IPEDSCOUNT2=9.
        rows = _fetch_sample(ingestor)
        flat = ingestor.flatten(rows, "credential_levels")
        row_with_counts = flat[2]
        assert isinstance(row_with_counts["ipedscount1"], int)
        assert row_with_counts["ipedscount1"] == 3
        assert isinstance(row_with_counts["ipedscount2"], int)
        assert row_with_counts["ipedscount2"] == 9


class TestCoerceEdgeCases:
    """Tests for _coerce() edge cases."""

    def test_coerce_empty_string_to_none(self):
        """Verify empty strings are treated as null."""
        ingestor = _make_ingestor()
        assert ingestor._coerce("md_earn_wne", "") is None

    def test_coerce_whitespace_sentinel_to_none(self):
        """Verify sentinel values with surrounding whitespace are nullified."""
        ingestor = _make_ingestor()
        assert ingestor._coerce("md_earn_wne", " PS ") is None
        assert ingestor._coerce("md_earn_wne", " NA ") is None

    def test_coerce_none_input_to_none(self):
        """Verify None input stays None."""
        ingestor = _make_ingestor()
        assert ingestor._coerce("unitid", None) is None

    def test_coerce_invalid_number_to_none(self):
        """Verify non-numeric strings in numeric fields become None."""
        ingestor = _make_ingestor()
        assert ingestor._coerce("unitid", "abc") is None
        assert ingestor._coerce("md_earn_wne", "not_a_number") is None
