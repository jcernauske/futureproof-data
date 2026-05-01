"""Tests for EadaIngestor.

Covers the helpers that move data through transformations — UNITID coercion,
sentinel scrub, institution-total filter, column-name parameterization,
reporting_year stamping, schema shape, source_method, and idempotency.

Per CLAUDE.md mandate: every raw ingestor must have coercion-helper unit
tests.  Network fetch + Iceberg promotion are out of scope (upstream / e2e).
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from raw.eada_ingestor import EadaIngestor


FIXTURE_CSV = Path(__file__).parent / "fixtures" / "eada_minimal.csv"


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------


def _make_ingestor(**overrides):
    """Create an EadaIngestor without requiring real config objects.

    Uses ``__new__`` to skip ``BaseIngestor.__init__`` (which requires
    source_config and manifest), then applies the same instance-state
    that ``__init__`` would have set.  Keyword overrides let individual
    tests tune column names / filter / reporting_year without touching
    the framework.
    """
    obj = EadaIngestor.__new__(EadaIngestor)
    obj.filter_column = overrides.get(
        "filter_column", EadaIngestor.INSTITUTION_TOTAL_FILTER_COLUMN
    )
    obj.filter_value = overrides.get(
        "filter_value", EadaIngestor.INSTITUTION_TOTAL_FILTER_VALUE
    )
    obj.exp_column = overrides.get("exp_column", EadaIngestor.DEFAULT_EXP_COLUMN)
    obj.rev_column = overrides.get("rev_column", EadaIngestor.DEFAULT_REV_COLUMN)
    obj.recruiting_column = overrides.get(
        "recruiting_column", EadaIngestor.DEFAULT_RECRUITING_COLUMN
    )
    obj.fte_headcount_column = overrides.get(
        "fte_headcount_column", EadaIngestor.DEFAULT_FTE_HEADCOUNT_COLUMN
    )
    obj.reporting_year = overrides.get(
        "reporting_year", EadaIngestor.DEFAULT_REPORTING_YEAR
    )
    obj._prefetched = None
    return obj


def _fetch_fixture(ingestor, csv_path: Path = FIXTURE_CSV):
    """Run fetch() with the minimal fixture and return the entity payload."""
    entities = {"eada": "EADA test"}
    result = ingestor.fetch(entities, "eada", csv_path=str(csv_path))
    return result["eada"]


# ----------------------------------------------------------------------
# Schema
# ----------------------------------------------------------------------


class TestSchema:
    def test_get_schema_returns_schema(self):
        from pyiceberg.schema import Schema

        ingestor = _make_ingestor()
        schema = ingestor.get_schema()
        assert isinstance(schema, Schema)

    def test_schema_has_eleven_fields(self):
        """Spec §4 (post-2026-04-30 amendment) specifies 11 fields:
        7 payload (incl. eada_fte_headcount) + 4 framework metadata."""
        ingestor = _make_ingestor()
        schema = ingestor.get_schema()
        assert len(schema.fields) == 11

    def test_schema_field_names_match_spec(self):
        ingestor = _make_ingestor()
        schema = ingestor.get_schema()
        names = [f.name for f in schema.fields]
        for expected in (
            "unitid",
            "institution_name",
            "reporting_year",
            "total_athletic_expenses",
            "total_athletic_revenue",
            "recruiting_expenses",
            "eada_fte_headcount",
            "source_url",
            "source_method",
            "ingested_at",
            "load_date",
        ):
            assert expected in names

    def test_schema_unitid_is_long_required(self):
        from pyiceberg.types import LongType

        ingestor = _make_ingestor()
        schema = ingestor.get_schema()
        field = next(f for f in schema.fields if f.name == "unitid")
        assert isinstance(field.field_type, LongType)
        assert field.required

    def test_schema_institution_name_required(self):
        ingestor = _make_ingestor()
        schema = ingestor.get_schema()
        field = next(f for f in schema.fields if f.name == "institution_name")
        assert field.required

    def test_schema_reporting_year_is_int_required(self):
        from pyiceberg.types import IntegerType

        ingestor = _make_ingestor()
        schema = ingestor.get_schema()
        field = next(f for f in schema.fields if f.name == "reporting_year")
        assert isinstance(field.field_type, IntegerType)
        assert field.required

    def test_schema_monetary_fields_are_double_optional(self):
        from pyiceberg.types import DoubleType

        ingestor = _make_ingestor()
        schema = ingestor.get_schema()
        for fname in (
            "total_athletic_expenses",
            "total_athletic_revenue",
            "recruiting_expenses",
        ):
            field = next(f for f in schema.fields if f.name == fname)
            assert isinstance(field.field_type, DoubleType)
            assert not field.required

    def test_schema_eada_fte_headcount_is_double_optional(self):
        """Spec §4 (post-2026-04-30 amendment) — `eada_fte_headcount` is
        double + optional. Captured from EADA's `EFTotalCount` column.
        Optional because the EADA file may rarely omit it for a row."""
        from pyiceberg.types import DoubleType

        ingestor = _make_ingestor()
        schema = ingestor.get_schema()
        field = next(f for f in schema.fields if f.name == "eada_fte_headcount")
        assert isinstance(field.field_type, DoubleType)
        assert not field.required


# ----------------------------------------------------------------------
# UNITID coercion (_coerce_long)
# ----------------------------------------------------------------------


class TestCoerceLong:
    def test_int_passthrough(self):
        assert EadaIngestor._coerce_long(100654) == 100654

    def test_float_truncates_to_int(self):
        assert EadaIngestor._coerce_long(100654.0) == 100654
        assert EadaIngestor._coerce_long(1.2345e5) == 123450

    def test_float_nan_returns_none(self):
        assert EadaIngestor._coerce_long(float("nan")) is None

    def test_plain_string(self):
        assert EadaIngestor._coerce_long("100654") == 100654

    def test_quoted_string_double(self):
        assert EadaIngestor._coerce_long('"100654"') == 100654

    def test_quoted_string_single(self):
        assert EadaIngestor._coerce_long("'100654'") == 100654

    def test_string_with_leading_zeros(self):
        assert EadaIngestor._coerce_long("00100654") == 100654

    def test_string_with_whitespace(self):
        assert EadaIngestor._coerce_long("  100654  ") == 100654

    def test_string_with_decimal_point(self):
        # e.g. UNITID came back as "100654.0" from a float-coerced source
        assert EadaIngestor._coerce_long("100654.0") == 100654

    def test_none_returns_none(self):
        assert EadaIngestor._coerce_long(None) is None

    def test_empty_string_returns_none(self):
        assert EadaIngestor._coerce_long("") is None
        assert EadaIngestor._coerce_long("   ") is None

    def test_malformed_returns_none(self):
        assert EadaIngestor._coerce_long("not_a_number") is None
        assert EadaIngestor._coerce_long("abc123def") is None

    def test_bool_excluded(self):
        # bool is a subclass of int — must be excluded
        assert EadaIngestor._coerce_long(True) is None
        assert EadaIngestor._coerce_long(False) is None


# ----------------------------------------------------------------------
# Sentinel handling (_strip_sentinel)
# ----------------------------------------------------------------------


class TestStripSentinel:
    def test_blank_string_is_sentinel(self):
        assert EadaIngestor._strip_sentinel("") is None

    def test_negative_one_is_sentinel(self):
        assert EadaIngestor._strip_sentinel("-1") is None

    def test_negative_two_is_sentinel(self):
        assert EadaIngestor._strip_sentinel("-2") is None

    def test_padded_sentinels(self):
        # leading/trailing whitespace must still match
        assert EadaIngestor._strip_sentinel(" -1 ") is None
        assert EadaIngestor._strip_sentinel("  -2  ") is None

    def test_legitimate_zero_preserved(self):
        """A real `0` (e.g. zero recruiting expenses) must NOT be scrubbed.

        Per EDA: 363 institution rows in the 2022-23 file have
        ``recruiting_expenses=0`` — these are real, not suppressed.
        """
        assert EadaIngestor._strip_sentinel("0") == "0"
        assert EadaIngestor._strip_sentinel(0) == 0

    def test_legitimate_value_preserved(self):
        assert EadaIngestor._strip_sentinel("100000") == "100000"
        assert EadaIngestor._strip_sentinel("2789771") == "2789771"

    def test_none_passthrough(self):
        assert EadaIngestor._strip_sentinel(None) is None

    def test_non_string_passthrough(self):
        assert EadaIngestor._strip_sentinel(12345) == 12345
        assert EadaIngestor._strip_sentinel(99.5) == 99.5

    def test_strips_whitespace_for_non_sentinel(self):
        # Non-sentinel strings come back stripped.
        assert EadaIngestor._strip_sentinel("  100  ") == "100"


# ----------------------------------------------------------------------
# _coerce_double
# ----------------------------------------------------------------------


class TestCoerceDouble:
    def test_plain_string(self):
        assert EadaIngestor._coerce_double("2789771") == 2789771.0

    def test_dollar_and_comma_stripped(self):
        assert EadaIngestor._coerce_double("$2,789,771") == 2789771.0
        assert EadaIngestor._coerce_double("1,000,000") == 1000000.0

    def test_int_passthrough(self):
        assert EadaIngestor._coerce_double(2789771) == 2789771.0

    def test_zero_preserved(self):
        # zero is a real value — must not be lost
        assert EadaIngestor._coerce_double("0") == 0.0
        assert EadaIngestor._coerce_double(0) == 0.0

    def test_none_returns_none(self):
        assert EadaIngestor._coerce_double(None) is None

    def test_empty_string_returns_none(self):
        assert EadaIngestor._coerce_double("") is None

    def test_malformed_returns_none(self):
        assert EadaIngestor._coerce_double("not_a_number") is None

    def test_bool_excluded(self):
        assert EadaIngestor._coerce_double(True) is None


# ----------------------------------------------------------------------
# Institution-total filter (_is_institution_total)
# ----------------------------------------------------------------------


class TestInstitutionTotalFilter:
    def test_filter_column_none_short_circuits_true(self):
        """When INSTITUTION_TOTAL_FILTER_COLUMN is None, every row passes."""
        ingestor = _make_ingestor(filter_column=None)
        assert ingestor._is_institution_total({}) is True
        assert ingestor._is_institution_total({"anything": "anything"}) is True
        assert ingestor._is_institution_total({"filter_marker": "TEAM"}) is True

    def test_filter_column_none_is_default(self):
        """Default class config is 'no filter applied'."""
        ingestor = _make_ingestor()
        assert ingestor.filter_column is None
        assert ingestor._is_institution_total({"filter_marker": "TEAM"}) is True

    def test_filter_column_with_null_filter_value_keeps_blank(self):
        """When filter_value is None: institution-total iff column is NULL/blank."""
        ingestor = _make_ingestor(filter_column="filter_marker", filter_value=None)
        assert ingestor._is_institution_total({"filter_marker": ""}) is True
        assert ingestor._is_institution_total({"filter_marker": "  "}) is True
        assert ingestor._is_institution_total({"filter_marker": None}) is True
        assert ingestor._is_institution_total({"filter_marker": "TEAM"}) is False

    def test_filter_column_with_explicit_filter_value(self):
        """When filter_value is set: institution-total iff column matches that value."""
        ingestor = _make_ingestor(
            filter_column="filter_marker", filter_value="TOTAL"
        )
        assert ingestor._is_institution_total({"filter_marker": "TOTAL"}) is True
        assert ingestor._is_institution_total({"filter_marker": "total"}) is True  # case-insensitive
        assert ingestor._is_institution_total({"filter_marker": "TEAM"}) is False
        assert ingestor._is_institution_total({"filter_marker": ""}) is False
        assert ingestor._is_institution_total({"filter_marker": None}) is False


# ----------------------------------------------------------------------
# Column-name parameterization
# ----------------------------------------------------------------------


class TestColumnParameterization:
    def test_default_columns_match_eda_pinned(self):
        """Default column names match EDA-confirmed pin (2026-04-30)."""
        ingestor = _make_ingestor()
        assert ingestor.exp_column == "GRND_TOTAL_EXPENSE"
        assert ingestor.rev_column == "GRND_TOTAL_REVENUE"
        assert ingestor.recruiting_column == "RECRUITEXP_TOTAL"

    def test_custom_columns_used_in_flatten(self):
        """Override the column names and confirm flatten reads from those."""
        ingestor = _make_ingestor(
            exp_column="EXP_X",
            rev_column="REV_X",
            recruiting_column="RCR_X",
        )
        records = [
            {
                "unitid": "100654",
                "institution_name": "Test U",
                "EXP_X": "1000",
                "REV_X": "2000",
                "RCR_X": "300",
                # Default column names should be IGNORED:
                "GRND_TOTAL_EXPENSE": "9999999",
                "GRND_TOTAL_REVENUE": "9999999",
                "RECRUITEXP_TOTAL": "9999999",
            }
        ]
        flat = ingestor.flatten({"records": records, "source_method": "csv_cache"}, "eada")
        assert len(flat) == 1
        assert flat[0]["total_athletic_expenses"] == 1000.0
        assert flat[0]["total_athletic_revenue"] == 2000.0
        assert flat[0]["recruiting_expenses"] == 300.0

    def test_default_columns_used_when_not_overridden(self):
        ingestor = _make_ingestor()
        records = [
            {
                "unitid": "100654",
                "institution_name": "Test U",
                "GRND_TOTAL_EXPENSE": "1000",
                "GRND_TOTAL_REVENUE": "2000",
                "RECRUITEXP_TOTAL": "300",
            }
        ]
        flat = ingestor.flatten({"records": records, "source_method": "csv_cache"}, "eada")
        assert flat[0]["total_athletic_expenses"] == 1000.0
        assert flat[0]["total_athletic_revenue"] == 2000.0
        assert flat[0]["recruiting_expenses"] == 300.0


# ----------------------------------------------------------------------
# eada_fte_headcount column (EFTotalCount, added 2026-04-30 per spec §5)
# ----------------------------------------------------------------------


class TestEadaFteHeadcount:
    def test_default_column_is_eftotalcount(self):
        """EDA-pinned default column is `EFTotalCount` (case-sensitive)."""
        assert EadaIngestor.DEFAULT_FTE_HEADCOUNT_COLUMN == "EFTotalCount"
        ingestor = _make_ingestor()
        assert ingestor.fte_headcount_column == "EFTotalCount"

    def test_happy_path_value_coerced_to_double(self):
        """A realistic EFTotalCount is read and coerced to float."""
        ingestor = _make_ingestor()
        records = [
            {
                "unitid": "100654",
                "institution_name": "Test U",
                "GRND_TOTAL_EXPENSE": "1000",
                "GRND_TOTAL_REVENUE": "2000",
                "RECRUITEXP_TOTAL": "300",
                "EFTotalCount": "5196",
            }
        ]
        flat = ingestor.flatten({"records": records, "source_method": "csv_cache"}, "eada")
        assert len(flat) == 1
        assert flat[0]["eada_fte_headcount"] == 5196.0
        assert isinstance(flat[0]["eada_fte_headcount"], float)

    def test_sentinel_values_become_null(self):
        """Suppression sentinels (`-1`, `-2`, blank) → NULL, same as monetary."""
        ingestor = _make_ingestor()
        records = [
            {
                "unitid": "100001",
                "institution_name": "Sentinel -1",
                "EFTotalCount": "-1",
            },
            {
                "unitid": "100002",
                "institution_name": "Sentinel -2",
                "EFTotalCount": "-2",
            },
            {
                "unitid": "100003",
                "institution_name": "Sentinel blank",
                "EFTotalCount": "",
            },
            {
                "unitid": "100004",
                "institution_name": "Sentinel padded",
                "EFTotalCount": "  -1  ",
            },
        ]
        flat = ingestor.flatten({"records": records, "source_method": "csv_cache"}, "eada")
        assert len(flat) == 4
        for row in flat:
            assert row["eada_fte_headcount"] is None

    def test_column_name_parameterizable(self):
        """Override fte_headcount_column → flatten reads from that column."""
        ingestor = _make_ingestor(fte_headcount_column="SomeOtherColumn")
        assert ingestor.fte_headcount_column == "SomeOtherColumn"
        records = [
            {
                "unitid": "100654",
                "institution_name": "Test U",
                "SomeOtherColumn": "12345",
                # Default column should be IGNORED:
                "EFTotalCount": "9999999",
            }
        ]
        flat = ingestor.flatten({"records": records, "source_method": "csv_cache"}, "eada")
        assert len(flat) == 1
        assert flat[0]["eada_fte_headcount"] == 12345.0

    def test_zero_preserved(self):
        """A real `0` (e.g. an institution with no enrollment reported but
        a non-suppressed zero) is NOT scrubbed — same semantics as the
        monetary fields."""
        ingestor = _make_ingestor()
        records = [
            {
                "unitid": "100654",
                "institution_name": "Test U",
                "EFTotalCount": "0",
            }
        ]
        flat = ingestor.flatten({"records": records, "source_method": "csv_cache"}, "eada")
        assert flat[0]["eada_fte_headcount"] == 0.0


# ----------------------------------------------------------------------
# reporting_year stamping
# ----------------------------------------------------------------------


class TestReportingYearStamping:
    def test_default_year_2022(self):
        ingestor = _make_ingestor()
        assert ingestor.reporting_year == 2022

    def test_custom_year_stamped_on_every_row(self):
        ingestor = _make_ingestor(reporting_year=2023)
        records = [
            {"unitid": "100654", "institution_name": "U1"},
            {"unitid": "200001", "institution_name": "U2"},
            {"unitid": "300002", "institution_name": "U3"},
        ]
        flat = ingestor.flatten({"records": records, "source_method": "csv_cache"}, "eada")
        assert len(flat) == 3
        for row in flat:
            assert row["reporting_year"] == 2023

    def test_default_year_stamped_when_not_overridden(self):
        ingestor = _make_ingestor()
        records = [{"unitid": "100654", "institution_name": "U1"}]
        flat = ingestor.flatten({"records": records, "source_method": "csv_cache"}, "eada")
        assert flat[0]["reporting_year"] == 2022


# ----------------------------------------------------------------------
# Flatten end-to-end (fixture CSV)
# ----------------------------------------------------------------------


class TestFlattenFixture:
    def test_fixture_loads(self):
        ingestor = _make_ingestor()
        payload = _fetch_fixture(ingestor)
        # 9 rows in fixture (1 happy + 1 quoted + 1 float + 2 sentinel +
        # 1 blank + 1 bad-UNITID + 1 missing-UNITID + 1 per-team)
        assert len(payload["records"]) == 9

    def test_flatten_drops_unparseable_unitid(self):
        """Rows with malformed or missing UNITID are dropped."""
        ingestor = _make_ingestor()
        payload = _fetch_fixture(ingestor)
        flat = ingestor.flatten(payload, "eada")
        # Drop: not_a_number + empty unitid → 2 dropped.
        # All 7 remaining rows pass (filter_column=None short-circuits).
        assert len(flat) == 7
        unitids = {r["unitid"] for r in flat}
        assert 100654 in unitids
        assert 123456 in unitids  # quoted "00123456"
        assert 123450 in unitids  # float 1.2345e5

    def test_flatten_unitid_quoted_and_padded(self):
        ingestor = _make_ingestor()
        flat = ingestor.flatten(_fetch_fixture(ingestor), "eada")
        by_uid = {r["unitid"]: r for r in flat}
        assert 123456 in by_uid
        assert by_uid[123456]["institution_name"] == "Quoted UNITID University"
        assert by_uid[123456]["total_athletic_expenses"] == 150_000_000.0

    def test_flatten_sentinels_become_null(self):
        """`-1` and `-2` and blank become NULL across all monetary fields."""
        ingestor = _make_ingestor()
        flat = ingestor.flatten(_fetch_fixture(ingestor), "eada")
        by_uid = {r["unitid"]: r for r in flat}

        # 234567: exp=-1, rev=blank, recruiting=5000
        assert by_uid[234567]["total_athletic_expenses"] is None
        assert by_uid[234567]["total_athletic_revenue"] is None
        assert by_uid[234567]["recruiting_expenses"] == 5000.0

        # 345678: all -2
        assert by_uid[345678]["total_athletic_expenses"] is None
        assert by_uid[345678]["total_athletic_revenue"] is None
        assert by_uid[345678]["recruiting_expenses"] is None

        # 456789: all blank
        assert by_uid[456789]["total_athletic_expenses"] is None
        assert by_uid[456789]["total_athletic_revenue"] is None
        assert by_uid[456789]["recruiting_expenses"] is None

    def test_flatten_zero_recruiting_preserved(self):
        """Per EDA: zero recruiting_expenses is real, not a sentinel."""
        ingestor = _make_ingestor()
        flat = ingestor.flatten(_fetch_fixture(ingestor), "eada")
        by_uid = {r["unitid"]: r for r in flat}
        # Float UNITID College has recruiting_expenses=0 in the fixture
        assert by_uid[123450]["recruiting_expenses"] == 0.0

    def test_flatten_with_filter_column_set_drops_team_rows(self):
        """When the filter is enabled, per-team rows are excluded."""
        ingestor = _make_ingestor(filter_column="filter_marker", filter_value=None)
        flat = ingestor.flatten(_fetch_fixture(ingestor), "eada")
        # Only rows where filter_marker is blank/null pass.  The fixture's
        # last row has filter_marker="TEAM" — dropped.
        unitids = {r["unitid"] for r in flat}
        assert 567890 not in unitids

    def test_flatten_default_filter_keeps_all_unitid_valid_rows(self):
        """Default filter_column=None: every row with valid UNITID passes."""
        ingestor = _make_ingestor()
        flat = ingestor.flatten(_fetch_fixture(ingestor), "eada")
        unitids = {r["unitid"] for r in flat}
        assert 567890 in unitids  # per-team-marked row passes when filter is off

    def test_flatten_does_not_add_framework_metadata(self):
        """flatten() returns payload-only fields; metadata is added downstream."""
        ingestor = _make_ingestor()
        flat = ingestor.flatten(_fetch_fixture(ingestor), "eada")
        meta = {"ingested_at", "source_url", "source_method", "load_date"}
        for r in flat:
            assert meta.isdisjoint(set(r.keys()))


# ----------------------------------------------------------------------
# Fetch — source_method
# ----------------------------------------------------------------------


class TestFetchSourceMethod:
    def test_csv_path_sets_source_method_csv_cache(self):
        ingestor = _make_ingestor()
        payload = _fetch_fixture(ingestor)
        assert payload["source_method"] == "csv_cache"

    def test_csv_path_skips_network(self):
        """Explicit csv_path must not call requests.get."""
        ingestor = _make_ingestor()
        with patch("raw.eada_ingestor.requests.get") as mock_get:
            _fetch_fixture(ingestor)
        mock_get.assert_not_called()

    def test_bulk_url_sets_source_method_bulk_csv_download(self):
        """When the bulk URL succeeds, source_method is bulk_csv_download."""
        ingestor = _make_ingestor()
        # Construct a CSV body matching the fixture column shape.
        csv_body = (
            "unitid,institution_name,GRND_TOTAL_EXPENSE,"
            "GRND_TOTAL_REVENUE,RECRUITEXP_TOTAL\n"
            "100654,Test U,1000,2000,300\n"
        )

        class FakeResponse:
            text = csv_body

            def raise_for_status(self):
                return None

        with patch("raw.eada_ingestor.requests.get") as mock_get:
            mock_get.return_value = FakeResponse()
            result = ingestor.fetch(
                {"eada": "test"},
                "eada",
                bulk_url="https://example.com/eada.csv",
            )
        mock_get.assert_called_once()
        assert result["eada"]["source_method"] == "bulk_csv_download"
        assert len(result["eada"]["records"]) == 1
        assert result["eada"]["records"][0]["unitid"] == "100654"

    def test_bulk_url_failure_falls_back_to_cache(self, tmp_path):
        """When the bulk URL fails, fetch falls back to the CSV cache."""
        ingestor = _make_ingestor()
        # Use a cache_dir override pointing at our fixture's parent so the
        # fallback path resolves.  Copy fixture into eada_2022.csv shape.
        import shutil
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        shutil.copy(FIXTURE_CSV, cache_dir / "eada_2022.csv")

        with patch("raw.eada_ingestor.requests.get") as mock_get:
            mock_get.side_effect = Exception("network down")
            result = ingestor.fetch(
                {"eada": "test"},
                "eada",
                bulk_url="https://example.com/eada.csv",
                cache_dir=str(cache_dir),
            )

        assert result["eada"]["source_method"] == "csv_cache"
        assert len(result["eada"]["records"]) == 9

    def test_force_fallback_skips_bulk_url(self, tmp_path):
        """force_fallback=True hits the cache even with bulk_url set."""
        import shutil
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        shutil.copy(FIXTURE_CSV, cache_dir / "eada_2022.csv")

        ingestor = _make_ingestor()
        with patch("raw.eada_ingestor.requests.get") as mock_get:
            result = ingestor.fetch(
                {"eada": "test"},
                "eada",
                bulk_url="https://example.com/eada.csv",
                cache_dir=str(cache_dir),
                force_fallback=True,
            )
        mock_get.assert_not_called()
        assert result["eada"]["source_method"] == "csv_cache"


# ----------------------------------------------------------------------
# Idempotency
# ----------------------------------------------------------------------


class TestIdempotency:
    def test_flatten_twice_produces_identical_output(self):
        """Calling flatten twice on the same input is identical."""
        ingestor = _make_ingestor()
        payload_a = _fetch_fixture(ingestor)
        payload_b = _fetch_fixture(ingestor)

        flat_a = ingestor.flatten(payload_a, "eada")
        flat_b = ingestor.flatten(payload_b, "eada")

        assert flat_a == flat_b
        # Same UNITID set
        assert {r["unitid"] for r in flat_a} == {r["unitid"] for r in flat_b}
        # Same monetary values
        for a, b in zip(flat_a, flat_b):
            assert a["total_athletic_expenses"] == b["total_athletic_expenses"]
            assert a["total_athletic_revenue"] == b["total_athletic_revenue"]
            assert a["recruiting_expenses"] == b["recruiting_expenses"]


# ----------------------------------------------------------------------
# get_source_url — lineage stamp
# ----------------------------------------------------------------------


class TestSourceUrl:
    def test_get_source_url_returns_landing_page(self):
        """source_url stamped on every row is the human-facing landing page."""
        ingestor = _make_ingestor()
        url = ingestor.get_source_url("eada", "csv_cache")
        assert url == "https://ope.ed.gov/athletics/"

    def test_source_url_stable_across_methods(self):
        """Lineage URL doesn't change based on cache vs bulk."""
        ingestor = _make_ingestor()
        a = ingestor.get_source_url("eada", "csv_cache")
        b = ingestor.get_source_url("eada", "bulk_csv_download")
        assert a == b


# ----------------------------------------------------------------------
# Class-level constants (EDA-pinned)
# ----------------------------------------------------------------------


class TestEdaPinnedConstants:
    def test_user_agent_contains_email(self):
        assert "jeff@hyenastudios.com" in EadaIngestor.USER_AGENT

    def test_default_reporting_year_2022(self):
        assert EadaIngestor.DEFAULT_REPORTING_YEAR == 2022

    def test_default_filter_column_is_none(self):
        """InstLevel.xlsx is already one-row-per-UNITID — no filter needed."""
        assert EadaIngestor.INSTITUTION_TOTAL_FILTER_COLUMN is None

    def test_eda_pinned_column_names(self):
        """Column names confirmed during EDA (2026-04-30)."""
        assert EadaIngestor.DEFAULT_EXP_COLUMN == "GRND_TOTAL_EXPENSE"
        assert EadaIngestor.DEFAULT_REV_COLUMN == "GRND_TOTAL_REVENUE"
        assert EadaIngestor.DEFAULT_RECRUITING_COLUMN == "RECRUITEXP_TOTAL"
        assert EadaIngestor.DEFAULT_FTE_HEADCOUNT_COLUMN == "EFTotalCount"

    def test_identity_columns_lowercase(self):
        """EDA confirms identity columns are lowercase in the file."""
        assert EadaIngestor.UNITID_COLUMN == "unitid"
        assert EadaIngestor.INSTNM_COLUMN == "institution_name"

    def test_suppression_sentinels(self):
        assert EadaIngestor.SUPPRESSION_SENTINELS == frozenset({"", "-1", "-2"})
