"""Tests for CollegeScorecardInstitutionIngestor."""

from pathlib import Path

from raw.college_scorecard_institution_ingestor import CollegeScorecardInstitutionIngestor

SAMPLE_CSV = Path(__file__).parent / "college_scorecard_institution_sample.csv"


def _make_ingestor():
    """Create a CollegeScorecardInstitutionIngestor without requiring real config objects.

    Uses __new__ to skip BaseIngestor.__init__ which requires
    source_config and manifest. Safe for testing schema/constants.
    """
    obj = CollegeScorecardInstitutionIngestor.__new__(CollegeScorecardInstitutionIngestor)
    return obj


def _fetch_sample(ingestor):
    """Run fetch() on the local sample CSV and return the raw rows."""
    entities = {"institutions": "4-Year Institutions"}
    result = ingestor.fetch(entities, "bulk_csv_download", csv_path=str(SAMPLE_CSV))
    return result["institutions"]


class TestSchema:
    """Tests for get_schema()."""

    def test_get_schema_returns_schema(self):
        """Verify get_schema returns a valid Iceberg Schema."""
        from pyiceberg.schema import Schema

        ingestor = _make_ingestor()
        schema = ingestor.get_schema()
        assert isinstance(schema, Schema)

    def test_schema_has_grain_fields(self):
        """Verify schema includes the grain field: unitid."""
        ingestor = _make_ingestor()
        schema = ingestor.get_schema()
        field_names = [field.name for field in schema.fields]
        assert "unitid" in field_names

    def test_schema_has_identity_fields(self):
        """Verify schema includes identity fields."""
        ingestor = _make_ingestor()
        schema = ingestor.get_schema()
        field_names = [field.name for field in schema.fields]
        for name in ("unitid", "instnm", "stabbr", "control", "preddeg"):
            assert name in field_names

    def test_schema_has_cost_fields(self):
        """Verify schema includes cost/price fields."""
        ingestor = _make_ingestor()
        schema = ingestor.get_schema()
        field_names = [field.name for field in schema.fields]
        for name in ("costt4_a", "costt4_p", "npt4_pub", "npt4_priv",
                      "tuitionfee_in", "tuitionfee_out", "roomboard_on",
                      "roomboard_off", "booksupply"):
            assert name in field_names

    def test_schema_has_quintile_fields(self):
        """Verify schema includes net price by income quintile fields."""
        ingestor = _make_ingestor()
        schema = ingestor.get_schema()
        field_names = [field.name for field in schema.fields]
        for i in range(1, 6):
            assert f"npt4{i}_pub" in field_names
            assert f"npt4{i}_priv" in field_names

    def test_schema_has_metadata_fields(self):
        """Verify schema includes framework metadata fields."""
        ingestor = _make_ingestor()
        schema = ingestor.get_schema()
        field_names = [field.name for field in schema.fields]
        for name in ("ingested_at", "source_url", "source_method", "load_date"):
            assert name in field_names

    def test_schema_field_count(self):
        """Verify schema has the expected number of fields (24 data + 4 metadata)."""
        ingestor = _make_ingestor()
        schema = ingestor.get_schema()
        assert len(schema.fields) == 28


class TestConstants:
    """Tests for class-level constants."""

    def test_download_url_is_set(self):
        """Verify the download URL constant points to institution-level data."""
        assert "ed-public-download" in CollegeScorecardInstitutionIngestor.DOWNLOAD_URL
        assert "Institution" in CollegeScorecardInstitutionIngestor.DOWNLOAD_URL

    def test_user_agent_contains_email(self):
        """Verify User-Agent header includes contact email."""
        assert "jeff@hyenastudios.com" in CollegeScorecardInstitutionIngestor.USER_AGENT

    def test_column_map_has_all_fields(self):
        """Verify COLUMN_MAP covers all 24 data fields."""
        assert len(CollegeScorecardInstitutionIngestor.COLUMN_MAP) == 24
        assert "UNITID" in CollegeScorecardInstitutionIngestor.COLUMN_MAP
        assert "COSTT4_A" in CollegeScorecardInstitutionIngestor.COLUMN_MAP
        assert "NPT4_PUB" in CollegeScorecardInstitutionIngestor.COLUMN_MAP
        assert "BOOKSUPPLY" in CollegeScorecardInstitutionIngestor.COLUMN_MAP

    def test_sentinel_values_include_all_variants(self):
        """Verify sentinel values cover all known suppressed/missing markers."""
        sentinels = CollegeScorecardInstitutionIngestor.SENTINEL_VALUES
        assert "PrivacySuppressed" in sentinels
        assert "PS" in sentinels
        assert "NA" in sentinels
        assert "NULL" in sentinels
        assert "" in sentinels


class TestFetch:
    """Tests for fetch() using the local sample CSV."""

    def test_fetch_returns_dict(self):
        """Verify fetch() returns a dict keyed by entity id."""
        ingestor = _make_ingestor()
        entities = {"institutions": "4-Year Institutions"}
        result = ingestor.fetch(entities, "bulk_csv_download", csv_path=str(SAMPLE_CSV))
        assert isinstance(result, dict)
        assert "institutions" in result

    def test_fetch_returns_rows(self):
        """Verify fetch() returns a non-empty list of row dicts."""
        ingestor = _make_ingestor()
        rows = _fetch_sample(ingestor)
        assert isinstance(rows, list)
        assert len(rows) > 0
        assert isinstance(rows[0], dict)

    def test_fetch_filters_preddeg_3(self):
        """Verify rows with PREDDEG=3 are included."""
        ingestor = _make_ingestor()
        rows = _fetch_sample(ingestor)
        # All PREDDEG=3 rows should be present
        unitids = {row["UNITID"] for row in rows}
        assert "100654" in unitids  # PREDDEG=3

    def test_fetch_filters_iclevel_1(self):
        """Verify rows with ICLEVEL=1 (but PREDDEG != 3) are included."""
        ingestor = _make_ingestor()
        rows = _fetch_sample(ingestor)
        unitids = {row["UNITID"] for row in rows}
        # Row 101365 has PREDDEG=2 but ICLEVEL=1, should be included
        assert "101365" in unitids

    def test_fetch_excludes_non_matching(self):
        """Verify rows with PREDDEG != 3 AND ICLEVEL != 1 are excluded."""
        ingestor = _make_ingestor()
        rows = _fetch_sample(ingestor)
        unitids = {row["UNITID"] for row in rows}
        # Row 999999 has PREDDEG=2 and ICLEVEL=2, should be excluded
        assert "999999" not in unitids

    def test_fetch_deduplicates_on_unitid(self):
        """Verify no duplicate UNITIDs in the result."""
        ingestor = _make_ingestor()
        rows = _fetch_sample(ingestor)
        unitids = [row["UNITID"] for row in rows]
        assert len(unitids) == len(set(unitids))

    def test_fetch_only_keeps_target_columns(self):
        """Verify fetch() only retains columns listed in COLUMN_MAP."""
        ingestor = _make_ingestor()
        rows = _fetch_sample(ingestor)
        allowed = set(CollegeScorecardInstitutionIngestor.COLUMN_MAP.keys())
        for row in rows:
            assert set(row.keys()).issubset(allowed)

    def test_fetch_returns_same_data_for_all_entities(self):
        """Verify fetch() returns the same rows for every entity key."""
        ingestor = _make_ingestor()
        entities = {"a": "first", "b": "second"}
        result = ingestor.fetch(entities, "bulk_csv_download", csv_path=str(SAMPLE_CSV))
        assert result["a"] == result["b"]

    def test_fetch_row_count(self):
        """Verify correct number of rows after filtering.

        Sample has 12 data rows:
        - 8 with PREDDEG=3, ICLEVEL=1 (included)
        - 1 with PREDDEG=2, ICLEVEL=1 (included via ICLEVEL filter)
        - 1 with PREDDEG=2, ICLEVEL=2 (excluded -- neither filter matches)
        - 1 with empty UNITID, PREDDEG=3, ICLEVEL=1 (included in fetch)
        - 1 Huntingdon (PREDDEG=3, ICLEVEL=1) (included)
        Total: 11 rows pass filter. 1 excluded.
        """
        ingestor = _make_ingestor()
        rows = _fetch_sample(ingestor)
        assert len(rows) == 11


class TestFlatten:
    """Tests for flatten() -- type coercion, sentinel handling, column mapping."""

    def test_flatten_returns_list_of_dicts(self):
        """Verify flatten() returns a list of dicts."""
        ingestor = _make_ingestor()
        rows = _fetch_sample(ingestor)
        flat = ingestor.flatten(rows, "institutions")
        assert isinstance(flat, list)
        assert len(flat) > 0
        assert isinstance(flat[0], dict)

    def test_flatten_uses_lowercase_keys(self):
        """Verify flatten() maps uppercase CSV columns to lowercase Iceberg names."""
        ingestor = _make_ingestor()
        rows = _fetch_sample(ingestor)
        flat = ingestor.flatten(rows, "institutions")
        expected_keys = set(CollegeScorecardInstitutionIngestor.COLUMN_MAP.values())
        for record in flat:
            assert set(record.keys()) == expected_keys

    def test_flatten_converts_ps_to_none(self):
        """Verify 'PS' sentinel values are converted to None."""
        ingestor = _make_ingestor()
        rows = _fetch_sample(ingestor)
        flat = ingestor.flatten(rows, "institutions")
        # Alabama State (100724) has PS for costt4_p and npt4_priv
        asu = next(r for r in flat if r["unitid"] == 100724)
        assert asu["costt4_p"] is None
        assert asu["npt4_priv"] is None

    def test_flatten_converts_null_string_to_none(self):
        """Verify 'NULL' sentinel values are converted to None."""
        ingestor = _make_ingestor()
        rows = _fetch_sample(ingestor)
        flat = ingestor.flatten(rows, "institutions")
        # Alabama A&M (100654) has NULL for costt4_p
        aamu = next(r for r in flat if r["unitid"] == 100654)
        assert aamu["costt4_p"] is None

    def test_flatten_converts_na_to_none(self):
        """Verify 'NA' sentinel values are converted to None."""
        ingestor = _make_ingestor()
        rows = _fetch_sample(ingestor)
        flat = ingestor.flatten(rows, "institutions")
        # Alabama State (100724) has NA for booksupply
        asu = next(r for r in flat if r["unitid"] == 100724)
        assert asu["booksupply"] is None

    def test_flatten_converts_privacy_suppressed_to_none(self):
        """Verify the full 'PrivacySuppressed' string is also handled."""
        ingestor = _make_ingestor()
        raw = [{"UNITID": "100654", "INSTNM": "Test U", "STABBR": "AL",
                "CONTROL": "1", "PREDDEG": "3",
                "COSTT4_A": "PrivacySuppressed", "COSTT4_P": "20000",
                "NPT4_PUB": "10000", "NPT4_PRIV": "NULL",
                "NPT41_PUB": "5000", "NPT42_PUB": "6000",
                "NPT43_PUB": "7000", "NPT44_PUB": "8000", "NPT45_PUB": "9000",
                "NPT41_PRIV": "NULL", "NPT42_PRIV": "NULL",
                "NPT43_PRIV": "NULL", "NPT44_PRIV": "NULL", "NPT45_PRIV": "NULL",
                "TUITIONFEE_IN": "8000", "TUITIONFEE_OUT": "18000",
                "ROOMBOARD_ON": "7000", "ROOMBOARD_OFF": "7000",
                "BOOKSUPPLY": "1200"}]
        flat = ingestor.flatten(raw, "test")
        assert flat[0]["costt4_a"] is None

    def test_flatten_coerces_unitid_to_int(self):
        """Verify UNITID is coerced to an integer."""
        ingestor = _make_ingestor()
        rows = _fetch_sample(ingestor)
        flat = ingestor.flatten(rows, "institutions")
        assert isinstance(flat[0]["unitid"], int)
        assert flat[0]["unitid"] == 100654

    def test_flatten_coerces_control_to_int(self):
        """Verify CONTROL is coerced to an integer."""
        ingestor = _make_ingestor()
        rows = _fetch_sample(ingestor)
        flat = ingestor.flatten(rows, "institutions")
        assert isinstance(flat[0]["control"], int)
        assert flat[0]["control"] == 1

    def test_flatten_coerces_preddeg_to_int(self):
        """Verify PREDDEG is coerced to an integer."""
        ingestor = _make_ingestor()
        rows = _fetch_sample(ingestor)
        flat = ingestor.flatten(rows, "institutions")
        assert isinstance(flat[0]["preddeg"], int)
        assert flat[0]["preddeg"] == 3

    def test_flatten_coerces_cost_to_float(self):
        """Verify cost fields are coerced to float when present."""
        ingestor = _make_ingestor()
        rows = _fetch_sample(ingestor)
        flat = ingestor.flatten(rows, "institutions")
        first = flat[0]
        assert isinstance(first["costt4_a"], float)
        assert first["costt4_a"] == 23053.0

    def test_flatten_coerces_net_price_to_float(self):
        """Verify net price fields are coerced to float when present."""
        ingestor = _make_ingestor()
        rows = _fetch_sample(ingestor)
        flat = ingestor.flatten(rows, "institutions")
        first = flat[0]
        assert isinstance(first["npt4_pub"], float)
        assert first["npt4_pub"] == 13067.0

    def test_flatten_coerces_tuition_to_float(self):
        """Verify tuition fields are coerced to float when present."""
        ingestor = _make_ingestor()
        rows = _fetch_sample(ingestor)
        flat = ingestor.flatten(rows, "institutions")
        first = flat[0]
        assert isinstance(first["tuitionfee_in"], float)
        assert isinstance(first["tuitionfee_out"], float)

    def test_flatten_skips_null_grain_fields(self):
        """Verify rows with null UNITID are skipped in flatten()."""
        ingestor = _make_ingestor()
        rows = _fetch_sample(ingestor)
        flat = ingestor.flatten(rows, "institutions")
        # The sample has a row with empty UNITID that passes fetch filter.
        # flatten() should skip it because unitid coerces to None.
        unitids = [r["unitid"] for r in flat]
        assert None not in unitids
        # Should have one fewer row than fetch returned
        assert len(flat) == len(rows) - 1

    def test_flatten_instnm_stays_string(self):
        """Verify INSTNM remains a string after flatten."""
        ingestor = _make_ingestor()
        rows = _fetch_sample(ingestor)
        flat = ingestor.flatten(rows, "institutions")
        assert isinstance(flat[0]["instnm"], str)
        assert flat[0]["instnm"] == "Alabama A & M University"

    def test_flatten_stabbr_stays_string(self):
        """Verify STABBR remains a string after flatten."""
        ingestor = _make_ingestor()
        rows = _fetch_sample(ingestor)
        flat = ingestor.flatten(rows, "institutions")
        assert isinstance(flat[0]["stabbr"], str)
        assert flat[0]["stabbr"] == "AL"

    def test_flatten_does_not_add_metadata_fields(self):
        """Verify flatten() does NOT add ingested_at, source_url, etc.

        The framework (BaseIngestor.ingest) adds these fields, not flatten().
        """
        ingestor = _make_ingestor()
        rows = _fetch_sample(ingestor)
        flat = ingestor.flatten(rows, "institutions")
        metadata_fields = {"ingested_at", "source_url", "source_method", "load_date"}
        for record in flat:
            assert metadata_fields.isdisjoint(set(record.keys()))

    def test_flatten_private_institution_has_priv_net_price(self):
        """Verify private institution (CONTROL=2) has npt4_priv populated."""
        ingestor = _make_ingestor()
        rows = _fetch_sample(ingestor)
        flat = ingestor.flatten(rows, "institutions")
        # Faulkner (101189) is CONTROL=2
        faulkner = next(r for r in flat if r["unitid"] == 101189)
        assert faulkner["control"] == 2
        assert isinstance(faulkner["npt4_priv"], float)
        assert faulkner["npt4_pub"] is None


class TestCoerceEdgeCases:
    """Tests for _coerce() edge cases."""

    def test_coerce_empty_string_to_none(self):
        """Verify empty strings are treated as null."""
        ingestor = _make_ingestor()
        assert ingestor._coerce("costt4_a", "") is None

    def test_coerce_whitespace_sentinel_to_none(self):
        """Verify sentinel values with surrounding whitespace are nullified."""
        ingestor = _make_ingestor()
        assert ingestor._coerce("costt4_a", " PS ") is None
        assert ingestor._coerce("costt4_a", " NA ") is None

    def test_coerce_none_input_to_none(self):
        """Verify None input stays None."""
        ingestor = _make_ingestor()
        assert ingestor._coerce("unitid", None) is None

    def test_coerce_invalid_number_to_none(self):
        """Verify non-numeric strings in numeric fields become None."""
        ingestor = _make_ingestor()
        assert ingestor._coerce("unitid", "abc") is None
        assert ingestor._coerce("costt4_a", "not_a_number") is None
        assert ingestor._coerce("control", "xyz") is None
