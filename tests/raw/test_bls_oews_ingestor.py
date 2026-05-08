"""Tests for BlsOewsIngestor.

Mirrors the structure of test_bls_ooh_ingestor.py: schema/constant tests
that don't require real config objects, fetch+flatten tests against a small
sample XLSX, edge-case tests for coercion helpers, and an integration test
that round-trips through a temp Iceberg warehouse.  The live network test
is opt-in (``-m network``) and skipped by default.
"""

from __future__ import annotations

import io
import zipfile
from pathlib import Path
from unittest.mock import patch

import pytest

from raw.bls_oews_ingestor import TOP_CODED_VALUE, BlsOewsIngestor

SAMPLE_XLSX = Path(__file__).parent / "bls_oews_sample.xlsx"
FALLBACK_XLSX = Path("data/raw/xlsx_cache/oesm24nat.xlsx")


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------


def _make_ingestor() -> BlsOewsIngestor:
    """Construct without invoking BaseIngestor.__init__ (which needs config)."""
    return BlsOewsIngestor.__new__(BlsOewsIngestor)


def _fetch_sample(ingestor: BlsOewsIngestor) -> list[dict]:
    """Run fetch() against the local sample XLSX and return rows."""
    entities = {"oews": "OEWS sample"}
    result = ingestor.fetch(entities, "xlsx_download", xlsx_path=str(SAMPLE_XLSX))
    return result["oews"]


def _by_soc(rows: list[dict]) -> dict[str, dict]:
    """Index a list of row dicts by ``soc_code`` for spot-check lookups."""
    return {r["soc_code"]: r for r in rows}


# ----------------------------------------------------------------------
# Schema
# ----------------------------------------------------------------------


class TestSchema:
    def test_get_schema_returns_schema(self):
        from pyiceberg.schema import Schema

        schema = _make_ingestor().get_schema()
        assert isinstance(schema, Schema)

    def test_schema_has_grain_field(self):
        names = [f.name for f in _make_ingestor().get_schema().fields]
        assert "soc_code" in names

    def test_schema_has_metadata_fields(self):
        names = [f.name for f in _make_ingestor().get_schema().fields]
        for expected in ("ingested_at", "source_url", "source_method", "load_date"):
            assert expected in names

    def test_schema_has_all_data_fields(self):
        names = [f.name for f in _make_ingestor().get_schema().fields]
        for expected in (
            "soc_code",
            "occupation_title",
            "total_employment",
            "wage_annual_p10",
            "wage_annual_p25",
            "wage_annual_median",
            "wage_annual_p75",
            "wage_annual_p90",
            "wage_annual_mean",
            "wage_hourly_median",
            "wage_capped",
        ):
            assert expected in names

    def test_schema_field_count(self):
        # 11 data fields + 4 framework metadata fields.
        assert len(_make_ingestor().get_schema().fields) == 15

    def test_wage_capped_is_required(self):
        schema = _make_ingestor().get_schema()
        field = next(f for f in schema.fields if f.name == "wage_capped")
        assert field.required


# ----------------------------------------------------------------------
# Constants / configuration
# ----------------------------------------------------------------------


class TestConstants:
    def test_download_url_targets_bls(self):
        assert "bls.gov" in BlsOewsIngestor.DOWNLOAD_URL
        assert BlsOewsIngestor.DOWNLOAD_URL.endswith(".zip")

    def test_user_agent_is_browser_like(self):
        # Spec note: BLS aggressively 403s bot-shaped UAs.  Match OOH approach.
        assert "Mozilla" in BlsOewsIngestor.USER_AGENT

    def test_fallback_path_under_xlsx_cache(self):
        assert BlsOewsIngestor.FALLBACK_XLSX_PATH.startswith("data/raw/xlsx_cache/")

    def test_top_coded_value_is_239_200(self):
        assert TOP_CODED_VALUE == 239200.0

    def test_column_map_covers_required_fields(self):
        canonical = set(BlsOewsIngestor.COLUMN_MAP.values())
        for required in (
            "soc_code",
            "occupation_title",
            "occ_group",
            "total_employment",
            "wage_annual_p10",
            "wage_annual_p25",
            "wage_annual_median",
            "wage_annual_p75",
            "wage_annual_p90",
            "wage_annual_mean",
            "wage_hourly_median",
        ):
            assert required in canonical


# ----------------------------------------------------------------------
# Fetch
# ----------------------------------------------------------------------


class TestFetch:
    def test_fetch_returns_dict_keyed_by_entity(self):
        entities = {"oews": "OEWS"}
        result = _make_ingestor().fetch(
            entities, "xlsx_download", xlsx_path=str(SAMPLE_XLSX)
        )
        assert isinstance(result, dict)
        assert "oews" in result

    def test_fetch_returns_rows(self):
        rows = _fetch_sample(_make_ingestor())
        assert isinstance(rows, list)
        assert len(rows) > 0
        assert isinstance(rows[0], dict)

    def test_fetch_filters_non_detailed_groups(self):
        """OCC_GROUP != 'detailed' rows are excluded."""
        rows = _fetch_sample(_make_ingestor())
        for row in rows:
            assert str(row.get("occ_group", "")).strip().lower() == "detailed", (
                f"Non-detailed row leaked through: {row.get('soc_code')!r}"
            )

    def test_fetch_filters_summary_rollup_socs(self):
        """The ``11-0000`` major-group SOC must not appear in fetched rows."""
        rows = _fetch_sample(_make_ingestor())
        soc_codes = {r["soc_code"] for r in rows}
        assert "11-0000" not in soc_codes
        assert "11-1000" not in soc_codes  # broad-group rollup
        assert "29-1100" not in soc_codes  # minor-group rollup
        assert "00-0000" not in soc_codes  # all-occupations rollup

    def test_fetch_row_count_matches_detailed_count(self):
        """Sample contains 5 detailed rows out of 9 total."""
        rows = _fetch_sample(_make_ingestor())
        assert len(rows) == 5

    def test_fetch_reads_local_xlsx_path(self):
        rows = _fetch_sample(_make_ingestor())
        soc_codes = {r["soc_code"] for r in rows}
        assert "15-1252" in soc_codes  # software developers
        assert "29-1141" in soc_codes  # registered nurses


# ----------------------------------------------------------------------
# ZIP unpacking
# ----------------------------------------------------------------------


class TestZipUnpack:
    def test_read_zip_extracts_xlsx(self, tmp_path: Path):
        zip_path = tmp_path / "oesm24nat.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.write(SAMPLE_XLSX, arcname="oesm24nat.xlsx")

        rows = _make_ingestor()._read_zip(zip_path)
        assert len(rows) == 5

    def test_read_zip_raises_when_no_xlsx(self, tmp_path: Path):
        zip_path = tmp_path / "empty.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("readme.txt", "no xlsx here")

        with pytest.raises(ValueError, match="No .xlsx member"):
            _make_ingestor()._read_zip(zip_path)

    def test_fetch_supports_zip_path_kwarg(self, tmp_path: Path):
        """A caller can pass ``zip_path`` directly (used to test the ZIP code path)."""
        zip_path = tmp_path / "oesm24nat.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.write(SAMPLE_XLSX, arcname="oesm24nat.xlsx")

        result = _make_ingestor().fetch(
            {"oews": "OEWS"}, "xlsx_download", zip_path=str(zip_path)
        )
        assert len(result["oews"]) == 5


# ----------------------------------------------------------------------
# Flatten
# ----------------------------------------------------------------------


class TestFlatten:
    def test_flatten_returns_list_of_dicts(self):
        ingestor = _make_ingestor()
        rows = _fetch_sample(ingestor)
        flat = ingestor.flatten(rows, "oews")
        assert isinstance(flat, list)
        assert len(flat) == 5
        assert all(isinstance(r, dict) for r in flat)

    def test_flatten_uses_lowercase_iceberg_keys(self):
        ingestor = _make_ingestor()
        flat = ingestor.flatten(_fetch_sample(ingestor), "oews")
        expected = {
            "soc_code",
            "occupation_title",
            "total_employment",
            "wage_annual_p10",
            "wage_annual_p25",
            "wage_annual_median",
            "wage_annual_p75",
            "wage_annual_p90",
            "wage_annual_mean",
            "wage_hourly_median",
            "wage_capped",
        }
        for record in flat:
            assert set(record.keys()) == expected

    def test_flatten_does_not_add_framework_metadata(self):
        """ingested_at / source_url / source_method / load_date are framework-owned."""
        ingestor = _make_ingestor()
        flat = ingestor.flatten(_fetch_sample(ingestor), "oews")
        meta = {"ingested_at", "source_url", "source_method", "load_date"}
        for r in flat:
            assert meta.isdisjoint(set(r.keys()))

    def test_flatten_soc_code_preserved_as_string(self):
        ingestor = _make_ingestor()
        flat = ingestor.flatten(_fetch_sample(ingestor), "oews")
        for r in flat:
            assert isinstance(r["soc_code"], str)
            # SOC must still be XX-XXXX after flatten (no hyphen-stripping).
            assert "-" in r["soc_code"]
            assert len(r["soc_code"]) == 7

    def test_flatten_top_coded_wage_sets_capped_flag(self):
        """``#`` in any annual percentile -> 239200 + wage_capped=True."""
        ingestor = _make_ingestor()
        flat = ingestor.flatten(_fetch_sample(ingestor), "oews")
        ceos = _by_soc(flat)["11-1011"]
        # Sample has '#' in both A_PCT75 and A_PCT90; A_MEAN is a real number.
        assert ceos["wage_annual_p75"] == TOP_CODED_VALUE
        assert ceos["wage_annual_p90"] == TOP_CODED_VALUE
        assert ceos["wage_capped"] is True
        # Lower percentiles still parse cleanly even when upper ones are capped.
        assert ceos["wage_annual_p25"] == 131000.0
        assert ceos["wage_annual_median"] == 206000.0
        # A_MEAN was a real number ($246,440) not '#' -- carried verbatim.
        assert ceos["wage_annual_mean"] == 246440.0

    def test_flatten_normal_wages_not_capped(self):
        """Rows with no ``#`` sentinels have wage_capped=False."""
        ingestor = _make_ingestor()
        flat = ingestor.flatten(_fetch_sample(ingestor), "oews")
        devs = _by_soc(flat)["15-1252"]
        assert devs["wage_capped"] is False
        # Software developers should have a real distribution.
        assert devs["wage_annual_p25"] == 98000.0
        assert devs["wage_annual_median"] == 130000.0
        assert devs["wage_annual_p75"] == 168000.0

    def test_flatten_suppressed_wages_become_null(self):
        """``*`` in every numeric column -> all wage fields null, total_employment kept."""
        ingestor = _make_ingestor()
        flat = ingestor.flatten(_fetch_sample(ingestor), "oews")
        maids = _by_soc(flat)["37-2012"]
        for field in (
            "wage_annual_p10",
            "wage_annual_p25",
            "wage_annual_median",
            "wage_annual_p75",
            "wage_annual_p90",
            "wage_annual_mean",
            "wage_hourly_median",
        ):
            assert maids[field] is None, f"{field} should be null when source is '*'"
        # Suppressed wages do not flag the row as capped.
        assert maids["wage_capped"] is False
        # Employment is still present.
        assert maids["total_employment"] == 900000

    def test_flatten_total_employment_is_int_with_commas(self):
        """``"3,175,390"`` -> 3175390 (int)."""
        ingestor = _make_ingestor()
        flat = ingestor.flatten(_fetch_sample(ingestor), "oews")
        rns = _by_soc(flat)["29-1141"]
        assert rns["total_employment"] == 3175390
        assert isinstance(rns["total_employment"], int)

    def test_flatten_monotonic_distribution_for_clean_rows(self):
        """For rows where p10..p90 are all non-null, the spec requires p10<=p25<=...<=p90."""
        ingestor = _make_ingestor()
        flat = ingestor.flatten(_fetch_sample(ingestor), "oews")
        for r in flat:
            ladder = [
                r["wage_annual_p10"],
                r["wage_annual_p25"],
                r["wage_annual_median"],
                r["wage_annual_p75"],
                r["wage_annual_p90"],
            ]
            if any(v is None for v in ladder):
                continue  # mixed-null rows don't apply
            for i in range(len(ladder) - 1):
                assert ladder[i] <= ladder[i + 1], (
                    f"{r['soc_code']} non-monotonic at index {i}: {ladder}"
                )

    def test_flatten_skips_rows_with_invalid_soc(self):
        """7-digit SOC like ``15-1252.00`` and empty SOC are dropped."""
        ingestor = _make_ingestor()
        raw_data = [
            {
                "soc_code": None,
                "occupation_title": "x",
                "occ_group": "detailed",
                "total_employment": 1,
                "wage_annual_p10": 10000,
                "wage_annual_p25": 20000,
                "wage_annual_median": 30000,
                "wage_annual_p75": 40000,
                "wage_annual_p90": 50000,
                "wage_annual_mean": 25000,
                "wage_hourly_median": 14.5,
            },
            {
                "soc_code": "15-1252.00",  # OEWS sub-classification, not standard
                "occupation_title": "y",
                "occ_group": "detailed",
                "total_employment": 1,
                "wage_annual_p10": 10000,
                "wage_annual_p25": 20000,
                "wage_annual_median": 30000,
                "wage_annual_p75": 40000,
                "wage_annual_p90": 50000,
                "wage_annual_mean": 25000,
                "wage_hourly_median": 14.5,
            },
            {
                "soc_code": "15-1252",
                "occupation_title": "Software Developers",
                "occ_group": "detailed",
                "total_employment": 100,
                "wage_annual_p10": 78000,
                "wage_annual_p25": 98000,
                "wage_annual_median": 130000,
                "wage_annual_p75": 168000,
                "wage_annual_p90": 204000,
                "wage_annual_mean": 138110,
                "wage_hourly_median": 62.5,
            },
        ]
        flat = ingestor.flatten(raw_data, "oews")
        assert len(flat) == 1
        assert flat[0]["soc_code"] == "15-1252"


# ----------------------------------------------------------------------
# Coercion edge cases
# ----------------------------------------------------------------------


class TestCoercion:
    def test_coerce_soc_valid(self):
        assert BlsOewsIngestor._coerce_soc("15-1252") == "15-1252"

    def test_coerce_soc_strips_whitespace(self):
        assert BlsOewsIngestor._coerce_soc("  29-1141 ") == "29-1141"

    def test_coerce_soc_rejects_non_standard(self):
        # OEWS publishes detailed sub-classes like ``15-1252.00`` we do not
        # carry into bronze (no clean OOH/O*NET join).
        assert BlsOewsIngestor._coerce_soc("15-1252.00") is None
        assert BlsOewsIngestor._coerce_soc("151252") is None
        assert BlsOewsIngestor._coerce_soc("") is None
        assert BlsOewsIngestor._coerce_soc(None) is None

    def test_parse_wage_suppressed(self):
        wage, capped = BlsOewsIngestor._parse_wage("*")
        assert wage is None
        assert capped is False

    def test_parse_wage_top_coded(self):
        wage, capped = BlsOewsIngestor._parse_wage("#")
        assert wage == TOP_CODED_VALUE
        assert capped is True

    def test_parse_wage_numeric_str_with_dollar(self):
        wage, capped = BlsOewsIngestor._parse_wage("$130,160")
        assert wage == 130160.0
        assert capped is False

    def test_parse_wage_numeric_input(self):
        wage, capped = BlsOewsIngestor._parse_wage(98000)
        assert wage == 98000.0
        assert capped is False

    def test_parse_wage_unknown_token(self):
        wage, capped = BlsOewsIngestor._parse_wage("???")
        assert wage is None
        assert capped is False

    def test_parse_wage_none(self):
        wage, capped = BlsOewsIngestor._parse_wage(None)
        assert wage is None
        assert capped is False

    def test_coerce_employment_suppressed(self):
        assert BlsOewsIngestor._coerce_employment("*") is None

    def test_coerce_employment_with_commas(self):
        assert BlsOewsIngestor._coerce_employment("3,175,390") == 3175390

    def test_coerce_employment_float_to_int(self):
        assert BlsOewsIngestor._coerce_employment(1234.7) == 1235

    def test_coerce_employment_none(self):
        assert BlsOewsIngestor._coerce_employment(None) is None
        assert BlsOewsIngestor._coerce_employment("") is None


# ----------------------------------------------------------------------
# Integration: round-trip through a temp Iceberg warehouse + idempotency
# ----------------------------------------------------------------------


class TestIngestIntegration:
    """End-to-end ingest + idempotency using the sample XLSX."""

    def _build_ingestor(self, tmp_path: Path) -> tuple[BlsOewsIngestor, Path, Path]:
        from brightsmith.domain_loader import (
            DomainHints,
            DomainManifest,
            SourceConfig,
        )

        source = SourceConfig(
            name="bls_oews",
            namespace="bronze",
            table="bls_oews",
            fetch={
                "xlsx_download": {
                    "fallback_path": str(SAMPLE_XLSX),
                }
            },
            entities={"oews": "OEWS — integration test"},
            dedup_grain=["soc_code"],
            cache_dir=tmp_path,
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

        return BlsOewsIngestor(source, manifest), warehouse, catalog_path

    def test_ingest_lands_detailed_rows(self, tmp_path: Path):
        from brightsmith.infra.iceberg_setup import get_catalog, read_with_duckdb

        ingestor, warehouse, catalog_path = self._build_ingestor(tmp_path)

        results = ingestor.ingest(
            warehouse_path=warehouse,
            catalog_path=catalog_path,
            xlsx_path=str(SAMPLE_XLSX),
        )
        assert results["oews"]["rows"] == 5

        catalog = get_catalog(warehouse, catalog_path)
        table = catalog.load_table("bronze.bls_oews")
        rows = read_with_duckdb(table)
        assert len(rows) == 5

        by_soc = _by_soc(rows)
        # Spot check: software developers carries the expected distribution
        assert by_soc["15-1252"]["wage_annual_median"] == 130000.0
        # Spot check: chief executives is top-coded
        assert by_soc["11-1011"]["wage_capped"] is True
        # Spot check: maids' wages are all null
        assert by_soc["37-2012"]["wage_annual_median"] is None

    def test_ingest_is_idempotent(self, tmp_path: Path):
        """Re-running on the same source file must not duplicate rows."""
        from brightsmith.infra.iceberg_setup import get_catalog, read_with_duckdb

        ingestor, warehouse, catalog_path = self._build_ingestor(tmp_path)

        first = ingestor.ingest(
            warehouse_path=warehouse,
            catalog_path=catalog_path,
            xlsx_path=str(SAMPLE_XLSX),
        )
        assert first["oews"]["rows"] == 5

        second = ingestor.ingest(
            warehouse_path=warehouse,
            catalog_path=catalog_path,
            xlsx_path=str(SAMPLE_XLSX),
        )
        # No new rows -- all 5 SOCs are deduped.
        assert second["oews"]["rows"] == 0
        assert second["oews"]["skipped"] == 5

        catalog = get_catalog(warehouse, catalog_path)
        table = catalog.load_table("bronze.bls_oews")
        rows = read_with_duckdb(table)
        assert len(rows) == 5  # not 10


# ----------------------------------------------------------------------
# Download fallback behavior
# ----------------------------------------------------------------------


class TestDownloadFallback:
    def test_download_falls_back_to_cached_xlsx_on_403(self, monkeypatch):
        """A 403 response from BLS triggers the fallback XLSX path."""
        ingestor = _make_ingestor()

        class FakeResponse:
            status_code = 403
            content = b""

            def raise_for_status(self):
                raise RuntimeError("should not be reached")

        with patch("raw.bls_oews_ingestor.requests.get") as mock_get, patch.object(
            BlsOewsIngestor,
            "_read_xlsx",
            return_value=[{"soc_code": "15-1252", "occ_group": "detailed"}],
        ) as mock_read:
            mock_get.return_value = FakeResponse()
            rows = ingestor._download_and_read()

        mock_get.assert_called_once()
        # Fell back to the cached file path.
        called_with = mock_read.call_args.args[0]
        assert str(called_with).endswith(BlsOewsIngestor.FALLBACK_XLSX_PATH)
        assert rows == [{"soc_code": "15-1252", "occ_group": "detailed"}]

    def test_download_success_unpacks_zip(self, monkeypatch):
        """A 200 response is treated as ZIP bytes and unpacked."""
        ingestor = _make_ingestor()

        # Build an in-memory ZIP wrapping the sample XLSX.
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.write(SAMPLE_XLSX, arcname="oesm24nat.xlsx")
        zip_bytes = buf.getvalue()

        class FakeResponse:
            status_code = 200
            content = zip_bytes

            def raise_for_status(self):
                return None

        with patch("raw.bls_oews_ingestor.requests.get") as mock_get:
            mock_get.return_value = FakeResponse()
            rows = ingestor._download_and_read()

        mock_get.assert_called_once()
        assert len(rows) == 5

    def test_download_user_agent_is_browser_like(self, monkeypatch):
        """The UA header must NOT look like a Python bot (BLS will 403)."""
        ingestor = _make_ingestor()

        captured: dict[str, dict] = {}

        class FakeResponse:
            status_code = 200
            content = b""

            def raise_for_status(self):
                return None

        def fake_get(url, headers=None, **kw):
            captured["headers"] = headers or {}
            return FakeResponse()

        with patch(
            "raw.bls_oews_ingestor.requests.get", side_effect=fake_get
        ), patch.object(BlsOewsIngestor, "_read_zip", return_value=[]):
            try:
                ingestor._download_and_read()
            except Exception:
                pass

        assert "Mozilla" in captured["headers"]["User-Agent"]


# ----------------------------------------------------------------------
# Full-dataset checks (require the real OEWS fallback file)
# ----------------------------------------------------------------------


class TestFullDataset:
    """Tests against the real OEWS workbook at FALLBACK_XLSX.

    Skips when the real file isn't present (e.g. a clean clone before the
    first download).  These mirror the spec's Bronze DQ thresholds without
    requiring network access.
    """

    @pytest.fixture(autouse=True)
    def skip_if_no_data(self):
        if not FALLBACK_XLSX.exists():
            pytest.skip(f"Full OEWS workbook not available at {FALLBACK_XLSX}")

    def test_full_row_count_in_range(self):
        ingestor = _make_ingestor()
        raw = ingestor.fetch(
            {"oews": "OEWS"}, "xlsx_download", xlsx_path=str(FALLBACK_XLSX)
        )
        flat = ingestor.flatten(raw["oews"], "oews")
        # Spec: 800 <= row count <= 900 detailed occupations.
        assert 800 <= len(flat) <= 900, f"Expected 800-900 rows, got {len(flat)}"

    def test_full_all_soc_codes_match_pattern(self):
        import re

        ingestor = _make_ingestor()
        raw = ingestor.fetch(
            {"oews": "OEWS"}, "xlsx_download", xlsx_path=str(FALLBACK_XLSX)
        )
        flat = ingestor.flatten(raw["oews"], "oews")
        for r in flat:
            assert re.match(r"^\d{2}-\d{4}$", r["soc_code"]), (
                f"Bad SOC: {r['soc_code']}"
            )

    def test_full_no_duplicate_soc_codes(self):
        ingestor = _make_ingestor()
        raw = ingestor.fetch(
            {"oews": "OEWS"}, "xlsx_download", xlsx_path=str(FALLBACK_XLSX)
        )
        flat = ingestor.flatten(raw["oews"], "oews")
        soc_codes = [r["soc_code"] for r in flat]
        assert len(soc_codes) == len(set(soc_codes))

    def test_full_median_non_null_rate(self):
        """At least 95% of detailed SOCs should have a non-null annual median."""
        ingestor = _make_ingestor()
        raw = ingestor.fetch(
            {"oews": "OEWS"}, "xlsx_download", xlsx_path=str(FALLBACK_XLSX)
        )
        flat = ingestor.flatten(raw["oews"], "oews")
        non_null = [r for r in flat if r["wage_annual_median"] is not None]
        rate = len(non_null) / len(flat)
        assert rate >= 0.95, f"Median non-null rate {rate:.1%} below 95%"

    def test_full_monotonicity(self):
        """Every row with full p10..p90 distribution must be monotonic."""
        ingestor = _make_ingestor()
        raw = ingestor.fetch(
            {"oews": "OEWS"}, "xlsx_download", xlsx_path=str(FALLBACK_XLSX)
        )
        flat = ingestor.flatten(raw["oews"], "oews")
        for r in flat:
            ladder = [
                r["wage_annual_p10"],
                r["wage_annual_p25"],
                r["wage_annual_median"],
                r["wage_annual_p75"],
                r["wage_annual_p90"],
            ]
            if any(v is None for v in ladder):
                continue
            for i in range(len(ladder) - 1):
                assert ladder[i] <= ladder[i + 1], (
                    f"{r['soc_code']} non-monotonic: {ladder}"
                )

    def test_full_software_developer_median_in_band(self):
        """Spec spot-check: 15-1252 median between $110K and $150K."""
        ingestor = _make_ingestor()
        raw = ingestor.fetch(
            {"oews": "OEWS"}, "xlsx_download", xlsx_path=str(FALLBACK_XLSX)
        )
        flat = ingestor.flatten(raw["oews"], "oews")
        devs = [r for r in flat if r["soc_code"] == "15-1252"]
        assert len(devs) == 1
        assert 110000 <= devs[0]["wage_annual_median"] <= 150000

    def test_full_registered_nurse_median_in_band(self):
        """Spec spot-check: 29-1141 median between $75K and $100K."""
        ingestor = _make_ingestor()
        raw = ingestor.fetch(
            {"oews": "OEWS"}, "xlsx_download", xlsx_path=str(FALLBACK_XLSX)
        )
        flat = ingestor.flatten(raw["oews"], "oews")
        rns = [r for r in flat if r["soc_code"] == "29-1141"]
        assert len(rns) == 1
        assert 75000 <= rns[0]["wage_annual_median"] <= 100000


# ----------------------------------------------------------------------
# Live network test (skipped by default; runs with `-m network`)
# ----------------------------------------------------------------------


@pytest.mark.network
class TestLiveDownload:
    def test_live_download_returns_detailed_rows(self):
        ingestor = _make_ingestor()
        rows = ingestor._download_and_read()
        assert isinstance(rows, list)
        # National OEWS has ~830 detailed occupations -- give a wide envelope
        # to absorb year-over-year SOC list shifts.
        assert 750 <= len(rows) <= 950
        # Sanity: at least one row matches a spec spot-check SOC.
        soc_codes = {r.get("soc_code") for r in rows if isinstance(r, dict)}
        assert soc_codes.intersection({"15-1252", "29-1141"})
