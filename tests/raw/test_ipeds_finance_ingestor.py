"""Tests for IpedsFinanceIngestor (raw.ipeds_finance).

Covers helpers that move data through the five-source UNION + JOIN pipeline:
sentinel handling, numeric coercion, EFIA NULL-safe FTE sum, HD lookup,
HD filter, cross-form deduplication detection, year-suffix filename
helpers, Ellipsis-sentinel resolution, _rv revised-CSV preference, and the
end-to-end flatten() against synthetic 3-form fixtures.

Per the staff-engineer canonical test list (governance/approvals/
full-pipeline-ipeds-finance-staff-review.md): 14 raw assertions minimum.
"""

from __future__ import annotations

import io
import zipfile
from pathlib import Path
from unittest.mock import patch

import pytest
from pyiceberg.schema import Schema

from raw.ipeds_finance_ingestor import IpedsFinanceIngestor


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------


def _make_ingestor(**overrides) -> IpedsFinanceIngestor:
    """Construct an IpedsFinanceIngestor without the BaseIngestor.__init__ contract.

    Matches the EADA / BEA-RPP fixture pattern: __new__ to skip the framework
    init that requires source_config + manifest, then set the same instance
    state __init__ would have produced. Lets individual tests tune the column
    overrides without touching the manifest layer.
    """
    obj = IpedsFinanceIngestor.__new__(IpedsFinanceIngestor)
    obj.fiscal_year = overrides.get("fiscal_year", IpedsFinanceIngestor.DEFAULT_FISCAL_YEAR)
    # F1A
    obj.f1a_instruction_col = overrides.get(
        "f1a_instruction_col", IpedsFinanceIngestor.DEFAULT_F1A_INSTRUCTION_COL
    )
    obj.f1a_institutional_support_col = overrides.get(
        "f1a_institutional_support_col",
        IpedsFinanceIngestor.DEFAULT_F1A_INSTITUTIONAL_SUPPORT_COL,
    )
    obj.f1a_endowment_eoy_col = overrides.get(
        "f1a_endowment_eoy_col", IpedsFinanceIngestor.DEFAULT_F1A_ENDOWMENT_EOY_COL
    )
    # F2
    obj.f2_instruction_col = overrides.get(
        "f2_instruction_col", IpedsFinanceIngestor.DEFAULT_F2_INSTRUCTION_COL
    )
    obj.f2_institutional_support_col = overrides.get(
        "f2_institutional_support_col",
        IpedsFinanceIngestor.DEFAULT_F2_INSTITUTIONAL_SUPPORT_COL,
    )
    obj.f2_endowment_eoy_col = overrides.get(
        "f2_endowment_eoy_col", IpedsFinanceIngestor.DEFAULT_F2_ENDOWMENT_EOY_COL
    )
    # F3
    obj.f3_instruction_col = overrides.get(
        "f3_instruction_col", IpedsFinanceIngestor.DEFAULT_F3_INSTRUCTION_COL
    )
    obj.f3_institutional_support_col = overrides.get(
        "f3_institutional_support_col",
        IpedsFinanceIngestor.DEFAULT_F3_INSTITUTIONAL_SUPPORT_COL,
    )
    obj.f3_endowment_eoy_col = overrides.get(
        "f3_endowment_eoy_col", IpedsFinanceIngestor.DEFAULT_F3_ENDOWMENT_EOY_COL
    )
    # EFIA
    obj.efia_fte_ug_col = overrides.get(
        "efia_fte_ug_col", IpedsFinanceIngestor.DEFAULT_EFIA_FTE_UG_COL
    )
    obj.efia_fte_gd_col = overrides.get(
        "efia_fte_gd_col", IpedsFinanceIngestor.DEFAULT_EFIA_FTE_GD_COL
    )
    obj.efia_fte_dpp_col = overrides.get(
        "efia_fte_dpp_col", IpedsFinanceIngestor.DEFAULT_EFIA_FTE_DPP_COL
    )
    obj._prefetched = None
    return obj


def _hd_row(unitid: int, name: str, iclevel: int = 1, hloffer: int = 5) -> dict:
    """Synthetic IPEDS HD2YYYY row."""
    return {
        "UNITID": str(unitid),
        "INSTNM": name,
        "ICLEVEL": str(iclevel),
        "HLOFFER": str(hloffer),
    }


def _f1a_row(unitid: int, instruction: str = "10000000",
             inst_supp: str = "3000000", endow: str = "50000000") -> dict:
    """Synthetic F1A row with locked column codes."""
    return {
        "UNITID": str(unitid),
        "F1C011": instruction,
        "F1C071": inst_supp,
        "F1H02": endow,
    }


def _f2_row(unitid: int, instruction: str = "5000000",
            inst_supp: str = "1500000", endow: str = "10000000") -> dict:
    return {
        "UNITID": str(unitid),
        "F2E011": instruction,
        "F2E061": inst_supp,
        "F2H02": endow,
    }


def _f3_row(unitid: int, instruction: str = "2000000",
            inst_supp: str = "2200000") -> dict:
    """Synthetic F3 row — no F3H endowment family (genuinely N/A)."""
    return {
        "UNITID": str(unitid),
        "F3E011": instruction,
        "F3E03C1": inst_supp,
    }


def _efia_row(unitid: int, ug: str | None = "1000",
              gd: str | None = "200", dpp: str | None = "0") -> dict:
    return {
        "UNITID": str(unitid),
        "FTEUG": ug if ug is not None else "",
        "FTEGD": gd if gd is not None else "",
        "FTEDPP": dpp if dpp is not None else "",
    }


# ----------------------------------------------------------------------
# Sentinel handling — IPEDS suppression sentinels → None BEFORE coercion
# ----------------------------------------------------------------------


class TestStripSentinel:
    @pytest.mark.parametrize(
        "sentinel",
        ["", "-1", "-2", ".", "PrivacySuppressed"],
    )
    def test_each_sentinel_returns_none(self, sentinel):
        """Spec §4 sentinel set: {empty, -1, -2, ., PrivacySuppressed}."""
        assert IpedsFinanceIngestor._strip_sentinel(sentinel) is None

    def test_sentinel_with_whitespace(self):
        """Sentinels are compared after .strip() — leading/trailing space tolerated."""
        assert IpedsFinanceIngestor._strip_sentinel("  -1  ") is None
        assert IpedsFinanceIngestor._strip_sentinel("\t.\n") is None
        assert IpedsFinanceIngestor._strip_sentinel(" PrivacySuppressed ") is None

    def test_real_string_passes_through_stripped(self):
        """Non-sentinel strings are returned with whitespace stripped."""
        assert IpedsFinanceIngestor._strip_sentinel("12345") == "12345"
        assert IpedsFinanceIngestor._strip_sentinel("  12345  ") == "12345"
        assert IpedsFinanceIngestor._strip_sentinel("$1,234,567") == "$1,234,567"

    def test_none_passes_through(self):
        assert IpedsFinanceIngestor._strip_sentinel(None) is None

    def test_numeric_passes_through_unchanged(self):
        """Non-string values bypass sentinel comparison entirely."""
        assert IpedsFinanceIngestor._strip_sentinel(123) == 123
        assert IpedsFinanceIngestor._strip_sentinel(123.45) == 123.45
        # The integer 0 is NOT a sentinel — only the literal "0" string would be.
        # But "0" isn't in the sentinel set either; only "" / -1 / -2 / . / PrivacySuppressed.
        assert IpedsFinanceIngestor._strip_sentinel(0) == 0


# ----------------------------------------------------------------------
# Numeric coercion — long / double / int
# ----------------------------------------------------------------------


class TestCoerceLong:
    """UNITID → long (int). Handles int, float, plain/quoted strings,
    leading-zeros, NaN, bool, unparseable inputs."""

    def test_int(self):
        assert IpedsFinanceIngestor._coerce_long(243744) == 243744

    def test_string(self):
        assert IpedsFinanceIngestor._coerce_long("243744") == 243744

    def test_quoted_string(self):
        """IPEDS occasionally ships quoted UNITIDs."""
        assert IpedsFinanceIngestor._coerce_long('"243744"') == 243744
        assert IpedsFinanceIngestor._coerce_long("'243744'") == 243744

    def test_leading_zero_string(self):
        """A leading zero must not corrupt the value."""
        assert IpedsFinanceIngestor._coerce_long("00123456") == 123456

    def test_float_with_value(self):
        assert IpedsFinanceIngestor._coerce_long(243744.0) == 243744

    def test_scientific_notation_string(self):
        """A scientific-notation float-string should fall through float()."""
        assert IpedsFinanceIngestor._coerce_long("1.2345e5") == 123450

    def test_nan_returns_none(self):
        assert IpedsFinanceIngestor._coerce_long(float("nan")) is None

    def test_none_returns_none(self):
        assert IpedsFinanceIngestor._coerce_long(None) is None

    def test_empty_returns_none(self):
        assert IpedsFinanceIngestor._coerce_long("") is None
        assert IpedsFinanceIngestor._coerce_long("   ") is None

    def test_bool_returns_none(self):
        """A bool is technically an int subclass — must NOT silently become 0/1."""
        assert IpedsFinanceIngestor._coerce_long(True) is None
        assert IpedsFinanceIngestor._coerce_long(False) is None

    def test_unparseable_returns_none(self):
        assert IpedsFinanceIngestor._coerce_long("abc") is None
        assert IpedsFinanceIngestor._coerce_long("12abc") is None


class TestCoerceDouble:
    """double coercion: handles thousands separators and dollar signs."""

    def test_plain_float(self):
        assert IpedsFinanceIngestor._coerce_double(110.7) == 110.7

    def test_int(self):
        assert IpedsFinanceIngestor._coerce_double(100) == 100.0

    def test_string_plain(self):
        assert IpedsFinanceIngestor._coerce_double("123456.78") == 123456.78

    def test_string_with_thousands_separators(self):
        assert IpedsFinanceIngestor._coerce_double("2,683,135,000") == 2683135000.0

    def test_string_with_dollar_sign(self):
        assert IpedsFinanceIngestor._coerce_double("$1234567") == 1234567.0

    def test_string_with_dollar_and_commas(self):
        assert IpedsFinanceIngestor._coerce_double("$2,683,135,000") == 2683135000.0

    def test_none_returns_none(self):
        assert IpedsFinanceIngestor._coerce_double(None) is None

    def test_empty_returns_none(self):
        assert IpedsFinanceIngestor._coerce_double("") is None

    def test_nan_returns_none(self):
        assert IpedsFinanceIngestor._coerce_double(float("nan")) is None

    def test_bool_returns_none(self):
        assert IpedsFinanceIngestor._coerce_double(True) is None

    def test_unparseable_returns_none(self):
        assert IpedsFinanceIngestor._coerce_double("not a number") is None


# ----------------------------------------------------------------------
# Optional override — Ellipsis vs None resolution
# ----------------------------------------------------------------------


class TestResolveOptionalOverride:
    """The Ellipsis-sentinel pattern: ... = use class default; None = disable."""

    def test_ellipsis_returns_default(self):
        """Passing ... means 'use class default'."""
        assert IpedsFinanceIngestor._resolve_optional_override(..., "F3E011") == "F3E011"

    def test_explicit_none_returns_none(self):
        """Passing None explicitly means 'disable lookup' (column doesn't exist)."""
        assert IpedsFinanceIngestor._resolve_optional_override(None, "F3E011") is None

    def test_explicit_string_overrides_default(self):
        """A string override takes precedence over the default."""
        assert IpedsFinanceIngestor._resolve_optional_override("F3CUSTOM", "F3E011") == "F3CUSTOM"

    def test_ellipsis_with_none_default(self):
        """Ellipsis with a None default returns None (the default)."""
        assert IpedsFinanceIngestor._resolve_optional_override(..., None) is None


# ----------------------------------------------------------------------
# EFIA NULL-safe FTE sum
# ----------------------------------------------------------------------


class TestBuildEfiaLookup:
    def test_sum_three_components(self):
        """Total FTE = COALESCE(UG,0) + COALESCE(GD,0) + COALESCE(DPP,0)."""
        ingestor = _make_ingestor()
        rows = [_efia_row(100, ug="1000", gd="200", dpp="50")]
        lookup = ingestor._build_efia_lookup(rows)
        assert lookup[100] == 1250.0

    def test_all_three_null_returns_none(self):
        """If all three FTE components are NULL, total is NULL — NOT 0.

        This is the key NULL-safe sum invariant: 0+0+0=0 would silently produce
        a meaningless zero that downstream per-FTE math would divide by.
        """
        ingestor = _make_ingestor()
        rows = [_efia_row(101, ug="", gd="", dpp="")]
        lookup = ingestor._build_efia_lookup(rows)
        assert lookup[101] is None

    def test_two_null_one_present_uses_present(self):
        """One present component → sum is that component, not 0."""
        ingestor = _make_ingestor()
        rows = [_efia_row(102, ug="500", gd="", dpp="")]
        lookup = ingestor._build_efia_lookup(rows)
        assert lookup[102] == 500.0

    def test_sentinels_treated_as_null(self):
        """IPEDS sentinels should pass through to NULL-safe sum semantics."""
        ingestor = _make_ingestor()
        rows = [_efia_row(103, ug="-1", gd="100", dpp="-2")]
        lookup = ingestor._build_efia_lookup(rows)
        assert lookup[103] == 100.0

    def test_unparseable_unitid_dropped_with_warning(self, caplog):
        ingestor = _make_ingestor()
        rows = [
            {"UNITID": "abc", "FTEUG": "100", "FTEGD": "0", "FTEDPP": "0"},
            _efia_row(104, ug="500"),
        ]
        with caplog.at_level("WARNING"):
            lookup = ingestor._build_efia_lookup(rows)
        assert 104 in lookup
        assert any("unparseable UNITID" in r.message for r in caplog.records)

    def test_duplicate_unitid_keeps_first_warns(self, caplog):
        """EFIA grain is one-row-per-UNITID; duplicates indicate data anomaly."""
        ingestor = _make_ingestor()
        rows = [
            _efia_row(105, ug="100", gd="0", dpp="0"),
            _efia_row(105, ug="999", gd="0", dpp="0"),  # duplicate
        ]
        with caplog.at_level("WARNING"):
            lookup = ingestor._build_efia_lookup(rows)
        assert lookup[105] == 100.0  # first wins
        assert any("duplicate UNITID" in r.message for r in caplog.records)


# ----------------------------------------------------------------------
# HD lookup — institution_name + ICLEVEL/HLOFFER filter columns
# ----------------------------------------------------------------------


class TestBuildHdLookup:
    def test_carries_name_iclevel_hloffer(self):
        ingestor = _make_ingestor()
        rows = [_hd_row(243744, "Stanford University", iclevel=1, hloffer=9)]
        lookup = ingestor._build_hd_lookup(rows)
        assert lookup[243744]["institution_name"] == "Stanford University"
        assert lookup[243744]["iclevel"] == 1
        assert lookup[243744]["hloffer"] == 9

    def test_skips_unparseable_unitid(self, caplog):
        ingestor = _make_ingestor()
        rows = [
            {"UNITID": "garbage", "INSTNM": "Bad", "ICLEVEL": "1", "HLOFFER": "5"},
            _hd_row(200, "Good University"),
        ]
        with caplog.at_level("WARNING"):
            lookup = ingestor._build_hd_lookup(rows)
        assert 200 in lookup
        assert "garbage" not in lookup
        assert any("unparseable UNITID" in r.message for r in caplog.records)


# ----------------------------------------------------------------------
# Filename helpers — IPEDS year-suffix patterns
# ----------------------------------------------------------------------


class TestFilenameHelpers:
    def test_fy_filename_fy23(self):
        """FY23 (academic year 2022-23) → F2223_F1A."""
        ingestor = _make_ingestor()
        assert ingestor._fy_filename("F1A", 2023) == "F2223_F1A"
        assert ingestor._fy_filename("F2", 2023) == "F2223_F2"
        assert ingestor._fy_filename("F3", 2023) == "F2223_F3"

    def test_fy_filename_fy24(self):
        """FY24 (academic year 2023-24) → F2324_F1A."""
        ingestor = _make_ingestor()
        assert ingestor._fy_filename("F1A", 2024) == "F2324_F1A"

    def test_efia_filename_fy23(self):
        """EFIA uses YYYY (calendar year ending the 12-month window)."""
        ingestor = _make_ingestor()
        assert ingestor._efia_filename(2023) == "EFIA2023"
        assert ingestor._efia_filename(2024) == "EFIA2024"

    def test_hd_filename_fy23(self):
        ingestor = _make_ingestor()
        assert ingestor._hd_filename(2023) == "HD2023"


# ----------------------------------------------------------------------
# Schema — spec §4 raw schema exactly
# ----------------------------------------------------------------------


class TestSchema:
    def test_get_schema_returns_schema(self):
        ingestor = _make_ingestor()
        assert isinstance(ingestor.get_schema(), Schema)

    def test_field_count(self):
        """Spec §4: 8 payload + 4 framework metadata = 12."""
        ingestor = _make_ingestor()
        assert len(ingestor.get_schema().fields) == 12

    def test_field_names_match_spec(self):
        ingestor = _make_ingestor()
        names = [f.name for f in ingestor.get_schema().fields]
        for expected in (
            "unitid", "institution_name", "report_form", "fiscal_year",
            "institutional_support_expenses", "instruction_expenses",
            "endowment_value", "total_fte_enrollment",
            "source_url", "source_method", "ingested_at", "load_date",
        ):
            assert expected in names

    def test_unitid_is_required(self):
        ingestor = _make_ingestor()
        unitid_field = next(f for f in ingestor.get_schema().fields if f.name == "unitid")
        assert unitid_field.required

    def test_endowment_value_is_optional(self):
        """F3 endowment is structurally NULL — column must be nullable."""
        ingestor = _make_ingestor()
        endow_field = next(
            f for f in ingestor.get_schema().fields if f.name == "endowment_value"
        )
        assert not endow_field.required


# ----------------------------------------------------------------------
# Source URL — pipe-delimited five-file lineage
# ----------------------------------------------------------------------


class TestSourceUrl:
    def test_url_contains_all_five_files(self):
        """Spec §4: row-level source_url is pipe-delimited list of five inputs."""
        ingestor = _make_ingestor(fiscal_year=2023)
        url = ingestor.get_source_url("any-entity", "csv_cache")
        assert "F2223_F1A" in url
        assert "F2223_F2" in url
        assert "F2223_F3" in url
        assert "EFIA2023" in url
        assert "HD2023" in url

    def test_pipe_delimiter(self):
        ingestor = _make_ingestor(fiscal_year=2023)
        url = ingestor.get_source_url("any-entity", "csv_cache")
        assert url.count("|") == 4  # 5 URLs joined by 4 pipes


# ----------------------------------------------------------------------
# User-Agent
# ----------------------------------------------------------------------


class TestUserAgent:
    def test_user_agent_constant(self):
        """Per CLAUDE.md: every download must carry the FutureProof UA."""
        assert IpedsFinanceIngestor.USER_AGENT == "FutureProof/0.1 (jeff@hyenastudios.com)"

    def test_chunk_size_constant(self):
        """CLAUDE.md: read CSVs in 50,000-row chunks."""
        assert IpedsFinanceIngestor.CSV_CHUNK_SIZE == 50_000


# ----------------------------------------------------------------------
# CSV chunked iteration — verify chunking yields all rows
# ----------------------------------------------------------------------


class TestCsvChunking:
    def test_iter_csv_chunks_yields_all_rows(self):
        """Synthetic CSV must round-trip every row through the chunked iterator."""
        ingestor = _make_ingestor()
        text = "UNITID,FTEUG\n100,1000\n200,2000\n300,3000\n"
        rows = list(ingestor._iter_csv_chunks(io.StringIO(text)))
        assert len(rows) == 3
        assert rows[0] == {"UNITID": "100", "FTEUG": "1000"}
        assert rows[2]["UNITID"] == "300"

    def test_parse_csv_text_handles_empty_body(self):
        ingestor = _make_ingestor()
        rows = ingestor._parse_csv_text("UNITID,FTEUG\n")
        assert rows == []


# ----------------------------------------------------------------------
# _read_zip_file — prefer "_rv" revised CSV when both ship
# ----------------------------------------------------------------------


class TestReadZipFilePrefersRv:
    def test_rv_csv_wins_over_original(self, tmp_path):
        """When both `_rv.csv` and `<file>.csv` ship in the same zip, the
        revised file supersedes the original per NCES revision policy."""
        zip_path = tmp_path / "F2223_F1A.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            # Original has UNITID 100 with old value
            zf.writestr("f2223_f1a.csv", "UNITID,F1C011\n100,9999999\n")
            # Revised has UNITID 100 with new value (this should win)
            zf.writestr("f2223_f1a_rv.csv", "UNITID,F1C011\n100,1234567\n")

        ingestor = _make_ingestor()
        rows = ingestor._read_zip_file(zip_path)
        assert len(rows) == 1
        assert rows[0]["UNITID"] == "100"
        assert rows[0]["F1C011"] == "1234567"  # revised value


# ----------------------------------------------------------------------
# Per-file fetch resolution — explicit path → cache → bulk
# ----------------------------------------------------------------------


class TestFetchOneResolution:
    def test_explicit_path_bypasses_cache_and_network(self, tmp_path):
        """An explicit_path always reads the local CSV, no cache/network."""
        csv_path = tmp_path / "fixture.csv"
        csv_path.write_text("UNITID,F1C011\n100,500000\n")
        ingestor = _make_ingestor()
        with patch("raw.ipeds_finance_ingestor.requests.get") as mock_get:
            rows, method = ingestor._fetch_one(
                str(csv_path), "ignored", tmp_path, force_fallback=False
            )
        mock_get.assert_not_called()
        assert method == "csv_cache"
        assert len(rows) == 1
        assert rows[0]["UNITID"] == "100"

    def test_force_fallback_with_no_cache_raises(self, tmp_path):
        """force_fallback=True must raise when cache is missing — not silently
        re-download."""
        ingestor = _make_ingestor()
        with pytest.raises(FileNotFoundError, match="cache miss"):
            ingestor._fetch_one(None, "MISSING", tmp_path, force_fallback=True)

    def test_local_zip_cache_wins_over_csv_cache(self, tmp_path):
        """When both .zip and .csv exist in cache, the zip is read first."""
        zip_path = tmp_path / "EFIA2023.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("efia2023.csv", "UNITID,FTEUG\n200,1000\n")
        # And a .csv that should be ignored
        (tmp_path / "EFIA2023.csv").write_text(
            "UNITID,FTEUG\n200,9999\n"
        )
        ingestor = _make_ingestor()
        rows, method = ingestor._fetch_one(
            None, "EFIA2023", tmp_path, force_fallback=False
        )
        assert method == "csv_cache"
        # Zip won — UG = 1000, not 9999
        assert rows[0]["FTEUG"] == "1000"


# ----------------------------------------------------------------------
# _flatten_one — HD miss / HD filter / per-form coalescing
# ----------------------------------------------------------------------


class TestFlattenOne:
    def test_hd_miss_drops_row(self):
        """A finance row with no HD record (no name/filter columns) is dropped."""
        ingestor = _make_ingestor()
        stats = {"unparseable_unitid": 0, "hd_miss": 0, "hd_filter_rejected": 0}
        result = ingestor._flatten_one(
            _f1a_row(999),
            "F1A", "F1C011", "F1C071", "F1H02",
            efia_by_unitid={},
            hd_by_unitid={},  # 999 not in HD
            stats=stats,
        )
        assert result is None
        assert stats["hd_miss"] == 1

    def test_hd_filter_rejects_iclevel_2(self):
        """ICLEVEL=2 (2-year) must be filtered out."""
        ingestor = _make_ingestor()
        stats = {"unparseable_unitid": 0, "hd_miss": 0, "hd_filter_rejected": 0}
        hd = {1: {"institution_name": "X", "iclevel": 2, "hloffer": 5}}
        result = ingestor._flatten_one(
            _f1a_row(1), "F1A", "F1C011", "F1C071", "F1H02",
            efia_by_unitid={}, hd_by_unitid=hd, stats=stats,
        )
        assert result is None
        assert stats["hd_filter_rejected"] == 1

    def test_hd_filter_rejects_hloffer_4(self):
        """HLOFFER=4 (associate's-only) must be filtered out (need ≥5)."""
        ingestor = _make_ingestor()
        stats = {"unparseable_unitid": 0, "hd_miss": 0, "hd_filter_rejected": 0}
        hd = {1: {"institution_name": "X", "iclevel": 1, "hloffer": 4}}
        result = ingestor._flatten_one(
            _f1a_row(1), "F1A", "F1C011", "F1C071", "F1H02",
            efia_by_unitid={}, hd_by_unitid=hd, stats=stats,
        )
        assert result is None
        assert stats["hd_filter_rejected"] == 1

    def test_hd_filter_accepts_iclevel_1_hloffer_5(self):
        """ICLEVEL=1 AND HLOFFER=5 (bachelor's) is the boundary — must pass."""
        ingestor = _make_ingestor()
        stats = {"unparseable_unitid": 0, "hd_miss": 0, "hd_filter_rejected": 0}
        hd = {1: {"institution_name": "Bachelor U", "iclevel": 1, "hloffer": 5}}
        result = ingestor._flatten_one(
            _f1a_row(1), "F1A", "F1C011", "F1C071", "F1H02",
            efia_by_unitid={1: 1000.0}, hd_by_unitid=hd, stats=stats,
        )
        assert result is not None
        assert result["unitid"] == 1
        assert result["institution_name"] == "Bachelor U"
        assert result["report_form"] == "F1A"

    def test_unparseable_unitid_drops_row(self):
        """A row with garbage UNITID is dropped, stats incremented."""
        ingestor = _make_ingestor()
        stats = {"unparseable_unitid": 0, "hd_miss": 0, "hd_filter_rejected": 0}
        result = ingestor._flatten_one(
            {"UNITID": "garbage", "F1C011": "100"},
            "F1A", "F1C011", "F1C071", "F1H02",
            efia_by_unitid={}, hd_by_unitid={}, stats=stats,
        )
        assert result is None
        assert stats["unparseable_unitid"] == 1

    def test_f3_endowment_col_none_produces_null_endowment(self):
        """F3 has no F3H endowment column — endowment must coalesce to NULL."""
        ingestor = _make_ingestor()
        stats = {"unparseable_unitid": 0, "hd_miss": 0, "hd_filter_rejected": 0}
        hd = {500: {"institution_name": "ForProfit U", "iclevel": 1, "hloffer": 7}}
        result = ingestor._flatten_one(
            _f3_row(500),
            "F3", "F3E011", "F3E03C1",
            None,  # endowment column = None for F3
            efia_by_unitid={500: 504.0}, hd_by_unitid=hd, stats=stats,
        )
        assert result is not None
        assert result["endowment_value"] is None  # NEVER imputed to 0
        assert result["instruction_expenses"] == 2_000_000.0
        assert result["institutional_support_expenses"] == 2_200_000.0


# ----------------------------------------------------------------------
# End-to-end flatten — UNION 3 forms + LEFT JOIN EFIA + HD filter
# ----------------------------------------------------------------------


class TestFlattenEndToEnd:
    """Synthetic 3-form fixture (F1A=2, F2=2, F3=2) with one HD-rejected
    row, one HD-miss, one F3-endowment-NULL — assert exact row count
    and per-form mix."""

    def _build_payload(self) -> dict:
        f1a_rows = [
            _f1a_row(100, instruction="500000000"),  # passes filter
            _f1a_row(101, instruction="100000000"),  # WILL FAIL HD filter (HLOFFER=2)
        ]
        f2_rows = [
            _f2_row(200),  # passes
            _f2_row(201),  # WILL HD-miss (no HD entry for 201)
        ]
        f3_rows = [
            _f3_row(300),  # passes; endowment NULL by structure
            _f3_row(301),  # passes; endowment NULL
        ]
        efia_by_unitid = {
            100: 50_000.0,
            200: 1_500.0,
            300: 504.0,
            301: 250.0,
        }
        hd_by_unitid = {
            100: {"institution_name": "Big Public U", "iclevel": 1, "hloffer": 9},
            101: {"institution_name": "Community Coll", "iclevel": 1, "hloffer": 2},  # FAIL
            200: {"institution_name": "Private NFP", "iclevel": 1, "hloffer": 7},
            # 201 intentionally absent → HD miss
            300: {"institution_name": "ForProfit Online", "iclevel": 1, "hloffer": 5},
            301: {"institution_name": "ForProfit Campus", "iclevel": 1, "hloffer": 5},
        }
        return {
            "f1a_rows": f1a_rows,
            "f2_rows": f2_rows,
            "f3_rows": f3_rows,
            "efia_by_unitid": efia_by_unitid,
            "hd_by_unitid": hd_by_unitid,
            "source_method": "csv_cache",
        }

    def test_flatten_drops_hd_rejects_and_misses(self):
        """6 inputs → 4 surviving rows (lose 1 HD-filter, 1 HD-miss)."""
        ingestor = _make_ingestor(fiscal_year=2023)
        flat = ingestor.flatten(self._build_payload(), "ipeds_finance")
        assert len(flat) == 4

    def test_flatten_form_mix_preserved(self):
        ingestor = _make_ingestor(fiscal_year=2023)
        flat = ingestor.flatten(self._build_payload(), "ipeds_finance")
        forms = sorted(r["report_form"] for r in flat)
        # 1 F1A + 1 F2 + 2 F3 (after filter/miss attrition)
        assert forms == ["F1A", "F2", "F3", "F3"]

    def test_flatten_stamps_fiscal_year(self):
        ingestor = _make_ingestor(fiscal_year=2023)
        flat = ingestor.flatten(self._build_payload(), "ipeds_finance")
        for row in flat:
            assert row["fiscal_year"] == 2023

    def test_flatten_efia_left_join(self):
        """total_fte_enrollment populated from EFIA lookup; NULL when missing."""
        ingestor = _make_ingestor(fiscal_year=2023)
        flat = ingestor.flatten(self._build_payload(), "ipeds_finance")
        by_unitid = {r["unitid"]: r for r in flat}
        assert by_unitid[100]["total_fte_enrollment"] == 50_000.0
        assert by_unitid[300]["total_fte_enrollment"] == 504.0

    def test_flatten_f3_endowment_is_null(self):
        """All F3 rows must have endowment_value = None."""
        ingestor = _make_ingestor(fiscal_year=2023)
        flat = ingestor.flatten(self._build_payload(), "ipeds_finance")
        f3_rows = [r for r in flat if r["report_form"] == "F3"]
        assert len(f3_rows) == 2
        assert all(r["endowment_value"] is None for r in f3_rows)

    def test_flatten_no_framework_metadata(self):
        """flatten() does NOT add ingested_at / source_url / source_method /
        load_date — those come from BaseIngestor.ingest()."""
        ingestor = _make_ingestor(fiscal_year=2023)
        flat = ingestor.flatten(self._build_payload(), "ipeds_finance")
        framework_keys = {"ingested_at", "source_url", "source_method", "load_date"}
        for row in flat:
            assert framework_keys.isdisjoint(row.keys())

    def test_flatten_form_coalescing_columns(self):
        """F1A uses F1C011/F1C071/F1H02; F2 uses F2E011/F2E061/F2H02;
        F3 uses F3E011/F3E03C1 (no F3H). Cross-form coalescing is per-form."""
        ingestor = _make_ingestor(fiscal_year=2023)
        flat = ingestor.flatten(self._build_payload(), "ipeds_finance")
        by_unitid = {r["unitid"]: r for r in flat}
        # F1A row
        assert by_unitid[100]["instruction_expenses"] == 500_000_000.0
        assert by_unitid[100]["institutional_support_expenses"] == 3_000_000.0
        assert by_unitid[100]["endowment_value"] == 50_000_000.0
        # F2 row
        assert by_unitid[200]["instruction_expenses"] == 5_000_000.0
        # F3 row
        assert by_unitid[300]["instruction_expenses"] == 2_000_000.0
        assert by_unitid[300]["institutional_support_expenses"] == 2_200_000.0
        assert by_unitid[300]["endowment_value"] is None  # F3 N/A

    def test_flatten_sentinels_become_null(self):
        """Sentinel values in finance forms must surface as NULL, not 0/-1."""
        ingestor = _make_ingestor(fiscal_year=2023)
        payload = {
            "f1a_rows": [
                {"UNITID": "100", "F1C011": "-1", "F1C071": "PrivacySuppressed", "F1H02": ""},
            ],
            "f2_rows": [],
            "f3_rows": [],
            "efia_by_unitid": {100: 1000.0},
            "hd_by_unitid": {100: {"institution_name": "X", "iclevel": 1, "hloffer": 9}},
            "source_method": "csv_cache",
        }
        flat = ingestor.flatten(payload, "ipeds_finance")
        assert len(flat) == 1
        assert flat[0]["instruction_expenses"] is None
        assert flat[0]["institutional_support_expenses"] is None
        assert flat[0]["endowment_value"] is None

    def test_cross_form_duplicate_unitid_warns(self, caplog):
        """An institution should appear in exactly one of F1A/F2/F3.
        Cross-form duplicates trigger a warning (data anomaly)."""
        ingestor = _make_ingestor(fiscal_year=2023)
        payload = {
            "f1a_rows": [_f1a_row(777)],
            "f2_rows": [_f2_row(777)],  # duplicate UNITID across forms
            "f3_rows": [],
            "efia_by_unitid": {777: 1000.0},
            "hd_by_unitid": {777: {"institution_name": "Confused U", "iclevel": 1, "hloffer": 9}},
            "source_method": "csv_cache",
        }
        with caplog.at_level("WARNING"):
            flat = ingestor.flatten(payload, "ipeds_finance")
        # Both rows are emitted — dedup is BaseIngestor's job — but warning fires
        assert len(flat) == 2
        assert any("multiple finance forms" in r.message for r in caplog.records)


# ----------------------------------------------------------------------
# Integration — end-to-end ingest into a temp Iceberg warehouse
# ----------------------------------------------------------------------


class TestIngestIntegration:
    """End-to-end ingest into a temporary Iceberg warehouse using small
    in-memory CSV fixtures for all five inputs.

    This is the load-bearing integration test: proves the full pipeline
    (fetch → flatten → BaseIngestor metadata stamp → Iceberg append) works
    end-to-end with realistic per-form column codes."""

    def _write_fixtures(self, tmp_path: Path) -> Path:
        """Stage all five fixture CSVs in a cache dir, return the dir."""
        cache = tmp_path / "ipeds_cache"
        cache.mkdir()
        # F1A: 1 row passing, 1 with sentinel-null instruction
        (cache / "F2223_F1A.csv").write_text(
            "UNITID,F1C011,F1C071,F1H02\n"
            "243744,2683135000,810116000,36494893000\n"  # Stanford
            "110635,1002622163,250000000,5000000000\n"  # UC Berkeley (synthetic)
        )
        # F2: 1 row
        (cache / "F2223_F2.csv").write_text(
            "UNITID,F2E011,F2E061,F2H02\n"
            "139959,500000000,150000000,2000000000\n"
        )
        # F3: 1 row, NO F3H column (genuinely N/A for for-profits)
        (cache / "F2223_F3.csv").write_text(
            "UNITID,F3E011,F3E03C1\n"
            "199193,50000000,55000000\n"
        )
        # EFIA: covers all 4 UNITIDs
        (cache / "EFIA2023.csv").write_text(
            "UNITID,FTEUG,FTEGD,FTEDPP\n"
            "243744,8000,10000,1094\n"   # Stanford 19,094
            "110635,32000,11000,500\n"    # Berkeley 43,500
            "139959,5000,1000,0\n"
            "199193,500,4,0\n"
        )
        # HD: all 4 UNITIDs — all bachelor's-or-above
        (cache / "HD2023.csv").write_text(
            "UNITID,INSTNM,ICLEVEL,HLOFFER\n"
            "243744,Stanford University,1,9\n"
            "110635,University of California-Berkeley,1,9\n"
            "139959,Northeastern University,1,9\n"
            "199193,For-Profit Online U,1,7\n"
        )
        return cache

    def test_ingest_lands_4_rows_with_metadata(self, tmp_path):
        """End-to-end: 4 rows out, framework metadata stamped, schema honored."""
        from brightsmith.domain_loader import DomainHints, DomainManifest, SourceConfig
        from brightsmith.infra.iceberg_setup import get_catalog, read_with_duckdb

        cache = self._write_fixtures(tmp_path)
        source = SourceConfig(
            name="ipeds_finance",
            namespace="bronze",
            table="ipeds_finance",
            fetch={"ipeds_finance": {}},
            entities={"ipeds_finance": "IPEDS Finance — integration test"},
            dedup_grain=["unitid"],
            cache_dir=cache,
        )
        manifest = DomainManifest(
            name="futureproof-data-test",
            version="0.1",
            description="test",
            sources=[],
            hints=DomainHints(),
            pipeline={},
        )

        warehouse = tmp_path / "warehouse"
        catalog_path = tmp_path / "catalog.db"
        warehouse.mkdir(parents=True, exist_ok=True)

        ingestor = IpedsFinanceIngestor(source, manifest, fiscal_year=2023)
        results = ingestor.ingest(
            warehouse_path=warehouse,
            catalog_path=catalog_path,
            cache_dir=cache,
        )
        assert "ipeds_finance" in results
        assert results["ipeds_finance"]["rows"] == 4

        catalog = get_catalog(warehouse, catalog_path)
        rows = read_with_duckdb(catalog.load_table("bronze.ipeds_finance"))
        assert len(rows) == 4

        # Verify Stanford anchor exactly
        stanford = next(r for r in rows if r["unitid"] == 243744)
        assert stanford["institution_name"] == "Stanford University"
        assert stanford["report_form"] == "F1A"
        assert stanford["fiscal_year"] == 2023
        assert stanford["instruction_expenses"] == 2683135000.0
        assert stanford["institutional_support_expenses"] == 810116000.0
        assert stanford["endowment_value"] == 36494893000.0
        assert stanford["total_fte_enrollment"] == 19094.0  # 8000+10000+1094

        # Framework metadata stamped on every row
        for row in rows:
            assert row["source_method"] == "csv_cache"
            assert row["source_url"]  # non-empty
            assert row["ingested_at"] is not None
            assert row["load_date"] is not None

        # F3 row has NULL endowment (no F3H column)
        f3 = next(r for r in rows if r["report_form"] == "F3")
        assert f3["unitid"] == 199193
        assert f3["endowment_value"] is None
        assert f3["institutional_support_expenses"] == 55_000_000.0  # F3E03C1

    def test_ingest_idempotent_second_run(self, tmp_path):
        """Re-running ingest with the same cache produces 0 new rows."""
        from brightsmith.domain_loader import DomainHints, DomainManifest, SourceConfig

        cache = self._write_fixtures(tmp_path)
        source = SourceConfig(
            name="ipeds_finance",
            namespace="bronze",
            table="ipeds_finance",
            fetch={"ipeds_finance": {}},
            entities={"ipeds_finance": "IPEDS Finance — integration test"},
            dedup_grain=["unitid"],
            cache_dir=cache,
        )
        manifest = DomainManifest(
            name="futureproof-data-test", version="0.1", description="test",
            sources=[], hints=DomainHints(), pipeline={},
        )
        warehouse = tmp_path / "warehouse"
        catalog_path = tmp_path / "catalog.db"
        warehouse.mkdir(parents=True, exist_ok=True)

        ingestor = IpedsFinanceIngestor(source, manifest, fiscal_year=2023)
        r1 = ingestor.ingest(warehouse_path=warehouse, catalog_path=catalog_path, cache_dir=cache)
        assert r1["ipeds_finance"]["rows"] == 4

        # Second run — must skip all 4
        ingestor2 = IpedsFinanceIngestor(source, manifest, fiscal_year=2023)
        r2 = ingestor2.ingest(warehouse_path=warehouse, catalog_path=catalog_path, cache_dir=cache)
        assert r2["ipeds_finance"]["rows"] == 0
        assert r2["ipeds_finance"]["skipped"] == 4
