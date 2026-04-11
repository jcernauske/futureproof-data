"""Tests for BeaRppIngestor."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from raw.bea_rpp_ingestor import BeaRppIngestor


CACHE_CSV = Path("data/raw/bea_cache/bea_rpp_2024.csv")


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------


def _make_ingestor():
    """Create a BeaRppIngestor without requiring real config objects.

    Uses __new__ to skip BaseIngestor.__init__ which requires
    source_config and manifest. Safe for schema/parser/coercion tests.
    """
    return BeaRppIngestor.__new__(BeaRppIngestor)


def _fetch_from_csv(ingestor, csv_path: Path = CACHE_CSV):
    """Run fetch() with a direct CSV path and return the entity payload."""
    entities = {"rpp": "BEA RPP — test"}
    result = ingestor.fetch(entities, "csv_cache", csv_path=str(csv_path))
    return result["rpp"]


def _sample_api_response() -> dict:
    """A minimal valid BEA API JSON response with three state rows and one metro row."""
    return {
        "BEAAPI": {
            "Results": {
                "Statistic": "Regional Price Parities",
                "UTCProductionTime": "2026-02-15T10:00:00",
                "Dimensions": [],
                "Data": [
                    {
                        "GeoFips": "06000",
                        "GeoName": "California",
                        "TimePeriod": "2024",
                        "CL_UNIT": "Index",
                        "UNIT_MULT": "0",
                        "DataValue": "110.7",
                    },
                    {
                        "GeoFips": "19000",
                        "GeoName": "Iowa",
                        "TimePeriod": "2024",
                        "CL_UNIT": "Index",
                        "UNIT_MULT": "0",
                        "DataValue": "87.8",
                    },
                    {
                        "GeoFips": "11000",
                        "GeoName": "District of Columbia",
                        "TimePeriod": "2024",
                        "CL_UNIT": "Index",
                        "UNIT_MULT": "0",
                        "DataValue": "109.9",
                    },
                    # A metro row that sneaks in — should be filtered with a warning
                    {
                        "GeoFips": "31080",
                        "GeoName": "Los Angeles-Long Beach-Anaheim, CA (Metro)",
                        "TimePeriod": "2024",
                        "CL_UNIT": "Index",
                        "UNIT_MULT": "0",
                        "DataValue": "115.5",
                    },
                ],
            }
        }
    }


# ----------------------------------------------------------------------
# Schema
# ----------------------------------------------------------------------


class TestSchema:
    def test_get_schema_returns_schema(self):
        from pyiceberg.schema import Schema

        ingestor = _make_ingestor()
        schema = ingestor.get_schema()
        assert isinstance(schema, Schema)

    def test_schema_has_grain_field(self):
        ingestor = _make_ingestor()
        schema = ingestor.get_schema()
        names = [f.name for f in schema.fields]
        assert "geo_fips" in names

    def test_schema_has_all_data_fields(self):
        ingestor = _make_ingestor()
        schema = ingestor.get_schema()
        names = [f.name for f in schema.fields]
        for expected in (
            "geo_fips",
            "geo_name",
            "rpp_all_items",
            "data_year",
        ):
            assert expected in names

    def test_schema_has_metadata_fields(self):
        ingestor = _make_ingestor()
        schema = ingestor.get_schema()
        names = [f.name for f in schema.fields]
        for expected in ("ingested_at", "source_url", "source_method", "load_date"):
            assert expected in names

    def test_schema_field_count(self):
        ingestor = _make_ingestor()
        schema = ingestor.get_schema()
        # 4 data fields + 4 metadata fields
        assert len(schema.fields) == 8

    def test_rpp_all_items_required(self):
        ingestor = _make_ingestor()
        schema = ingestor.get_schema()
        field = next(f for f in schema.fields if f.name == "rpp_all_items")
        assert field.required


# ----------------------------------------------------------------------
# API response parsing
# ----------------------------------------------------------------------


class TestParseApiResponse:
    def test_parses_valid_response(self):
        ingestor = _make_ingestor()
        records = ingestor._parse_api_response(_sample_api_response())
        assert isinstance(records, list)
        assert len(records) == 4

    def test_records_have_required_keys(self):
        ingestor = _make_ingestor()
        records = ingestor._parse_api_response(_sample_api_response())
        for r in records:
            assert "GeoFips" in r
            assert "GeoName" in r
            assert "DataValue" in r

    def test_rejects_non_dict_response(self):
        ingestor = _make_ingestor()
        with pytest.raises(ValueError, match="not a dict"):
            ingestor._parse_api_response("oops")

    def test_rejects_missing_beaapi(self):
        ingestor = _make_ingestor()
        with pytest.raises(ValueError, match="BEAAPI"):
            ingestor._parse_api_response({"Foo": "bar"})

    def test_rejects_missing_results(self):
        ingestor = _make_ingestor()
        with pytest.raises(ValueError, match="Results"):
            ingestor._parse_api_response({"BEAAPI": {}})

    def test_rejects_api_error_object(self):
        ingestor = _make_ingestor()
        payload = {
            "BEAAPI": {
                "Results": {"Error": {"APIErrorCode": "3", "APIErrorDescription": "Invalid key"}}
            }
        }
        with pytest.raises(ValueError, match="error"):
            ingestor._parse_api_response(payload)

    def test_rejects_missing_data_array(self):
        ingestor = _make_ingestor()
        payload = {"BEAAPI": {"Results": {}}}
        with pytest.raises(ValueError, match="Data"):
            ingestor._parse_api_response(payload)

    def test_rejects_empty_data_array(self):
        ingestor = _make_ingestor()
        payload = {"BEAAPI": {"Results": {"Data": []}}}
        with pytest.raises(ValueError, match="empty"):
            ingestor._parse_api_response(payload)

    def test_rejects_record_missing_keys(self):
        ingestor = _make_ingestor()
        payload = {
            "BEAAPI": {
                "Results": {
                    "Data": [{"GeoFips": "06000"}],
                }
            }
        }
        with pytest.raises(ValueError, match="missing required keys"):
            ingestor._parse_api_response(payload)


# ----------------------------------------------------------------------
# CSV parsing
# ----------------------------------------------------------------------


class TestReadCsv:
    def test_reads_cache_file(self):
        ingestor = _make_ingestor()
        rows = ingestor._read_csv_file(CACHE_CSV)
        assert isinstance(rows, list)
        assert len(rows) == 51

    def test_csv_has_expected_columns(self):
        ingestor = _make_ingestor()
        rows = ingestor._read_csv_file(CACHE_CSV)
        assert {"GeoFips", "GeoName", "TimePeriod", "DataValue"}.issubset(rows[0].keys())

    def test_csv_contains_verified_california(self):
        ingestor = _make_ingestor()
        rows = ingestor._read_csv_file(CACHE_CSV)
        ca = [r for r in rows if r["GeoName"] == "California"]
        assert len(ca) == 1
        assert float(ca[0]["DataValue"]) == 110.7


# ----------------------------------------------------------------------
# Flatten + state FIPS filter
# ----------------------------------------------------------------------


class TestFlatten:
    def test_flatten_from_api_payload_filters_metro(self):
        ingestor = _make_ingestor()
        records = ingestor._parse_api_response(_sample_api_response())
        payload = {"records": records, "source_method": "bea_api"}
        flat = ingestor.flatten(payload, "rpp")
        # 3 state rows; metro row "31080" must be excluded
        assert len(flat) == 3
        fips = {r["geo_fips"] for r in flat}
        assert fips == {"06", "19", "11"}

    def test_flatten_from_csv_cache_row_count(self):
        ingestor = _make_ingestor()
        payload = _fetch_from_csv(ingestor)
        flat = ingestor.flatten(payload, "rpp")
        assert len(flat) == 51

    def test_flatten_geo_fips_is_two_char_string(self):
        ingestor = _make_ingestor()
        payload = _fetch_from_csv(ingestor)
        flat = ingestor.flatten(payload, "rpp")
        for r in flat:
            assert isinstance(r["geo_fips"], str)
            assert len(r["geo_fips"]) == 2
            assert r["geo_fips"].isdigit()

    def test_flatten_includes_dc(self):
        ingestor = _make_ingestor()
        payload = _fetch_from_csv(ingestor)
        flat = ingestor.flatten(payload, "rpp")
        dc = [r for r in flat if r["geo_fips"] == "11"]
        assert len(dc) == 1
        assert dc[0]["geo_name"] == "District of Columbia"
        assert dc[0]["rpp_all_items"] == 109.9

    def test_flatten_verified_values(self):
        """Spot-check all verified reference values from the spec."""
        ingestor = _make_ingestor()
        payload = _fetch_from_csv(ingestor)
        flat = ingestor.flatten(payload, "rpp")
        by_name = {r["geo_name"]: r for r in flat}

        expected = {
            "California": 110.7,
            "Hawaii": 110.0,
            "District of Columbia": 109.9,
            "New Jersey": 108.8,
            "Arkansas": 86.9,
            "Mississippi": 87.0,
            "Iowa": 87.8,
            "Oklahoma": 87.8,
        }
        for name, value in expected.items():
            assert by_name[name]["rpp_all_items"] == value, (
                f"{name} RPP mismatch"
            )

    def test_flatten_filters_metro_rows_not_in_valid_states(self):
        """Direct test of the state-FIPS filter: a 2-digit code outside 01-56/11 is dropped."""
        ingestor = _make_ingestor()
        # A fake territory code (Puerto Rico 72) — valid 2-digit but not in our allow list.
        payload = {
            "records": [
                {"GeoFips": "06000", "GeoName": "California", "TimePeriod": "2024", "DataValue": "110.7"},
                {"GeoFips": "72000", "GeoName": "Puerto Rico", "TimePeriod": "2024", "DataValue": "95.0"},
            ],
            "source_method": "csv_cache",
        }
        flat = ingestor.flatten(payload, "rpp")
        assert len(flat) == 1
        assert flat[0]["geo_fips"] == "06"

    def test_flatten_filters_five_digit_metro_codes(self):
        """Metro/CBSA 5-digit codes that don't end in 000 are dropped."""
        ingestor = _make_ingestor()
        payload = {
            "records": [
                {"GeoFips": "06000", "GeoName": "California", "TimePeriod": "2024", "DataValue": "110.7"},
                {"GeoFips": "31080", "GeoName": "Los Angeles Metro", "TimePeriod": "2024", "DataValue": "115.0"},
                {"GeoFips": "35620", "GeoName": "New York Metro", "TimePeriod": "2024", "DataValue": "118.0"},
            ],
            "source_method": "bea_api",
        }
        flat = ingestor.flatten(payload, "rpp")
        assert len(flat) == 1
        assert flat[0]["geo_fips"] == "06"

    def test_flatten_data_year_is_int(self):
        ingestor = _make_ingestor()
        payload = _fetch_from_csv(ingestor)
        flat = ingestor.flatten(payload, "rpp")
        for r in flat:
            assert isinstance(r["data_year"], int)
            assert r["data_year"] == 2024

    def test_flatten_does_not_add_framework_metadata(self):
        ingestor = _make_ingestor()
        payload = _fetch_from_csv(ingestor)
        flat = ingestor.flatten(payload, "rpp")
        meta = {"ingested_at", "source_url", "source_method", "load_date"}
        for r in flat:
            assert meta.isdisjoint(set(r.keys()))

    def test_flatten_rpp_range_sanity(self):
        ingestor = _make_ingestor()
        payload = _fetch_from_csv(ingestor)
        flat = ingestor.flatten(payload, "rpp")
        for r in flat:
            assert 80.0 <= r["rpp_all_items"] <= 130.0, (
                f"{r['geo_name']} RPP {r['rpp_all_items']} outside sanity range"
            )


# ----------------------------------------------------------------------
# Coercion helpers
# ----------------------------------------------------------------------


class TestCoercion:
    def test_normalize_five_digit_state(self):
        assert BeaRppIngestor._normalize_geo_fips("06000") == "06"
        assert BeaRppIngestor._normalize_geo_fips("01000") == "01"
        assert BeaRppIngestor._normalize_geo_fips("56000") == "56"

    def test_normalize_two_digit_state(self):
        assert BeaRppIngestor._normalize_geo_fips("6") == "06"
        assert BeaRppIngestor._normalize_geo_fips("06") == "06"

    def test_normalize_metro_code_returned_as_is(self):
        # 5-digit metro codes don't end in 000
        result = BeaRppIngestor._normalize_geo_fips("31080")
        assert result == "31080"

    def test_normalize_empty_returns_none(self):
        assert BeaRppIngestor._normalize_geo_fips("") is None
        assert BeaRppIngestor._normalize_geo_fips(None) is None
        assert BeaRppIngestor._normalize_geo_fips("  ") is None

    def test_coerce_double(self):
        assert BeaRppIngestor._coerce_double("110.7") == 110.7
        assert BeaRppIngestor._coerce_double("87.8") == 87.8
        assert BeaRppIngestor._coerce_double(None) is None
        assert BeaRppIngestor._coerce_double("") is None
        assert BeaRppIngestor._coerce_double("bad") is None

    def test_coerce_int(self):
        assert BeaRppIngestor._coerce_int("2024") == 2024
        assert BeaRppIngestor._coerce_int(2024) == 2024
        assert BeaRppIngestor._coerce_int(None) is None


# ----------------------------------------------------------------------
# Fetch fallback behavior
# ----------------------------------------------------------------------


class TestFetchFallback:
    def test_csv_path_bypasses_api(self):
        """Explicit csv_path never hits the API."""
        ingestor = _make_ingestor()
        with patch("raw.bea_rpp_ingestor.requests.get") as mock_get:
            payload = _fetch_from_csv(ingestor)
        mock_get.assert_not_called()
        assert payload["source_method"] == "csv_cache"
        assert len(payload["records"]) == 51

    def test_no_api_key_falls_back_to_csv(self, monkeypatch):
        """If BEA_API_KEY is missing, fetch goes straight to the CSV cache."""
        monkeypatch.delenv("BEA_API_KEY", raising=False)
        ingestor = _make_ingestor()
        with patch("raw.bea_rpp_ingestor.requests.get") as mock_get:
            result = ingestor.fetch({"rpp": "test"}, "bea_api")
        mock_get.assert_not_called()
        payload = result["rpp"]
        assert payload["source_method"] == "csv_cache"
        assert len(payload["records"]) == 51

    def test_api_failure_falls_back_to_csv(self, monkeypatch):
        """When the API raises, fetch retries once then falls back to CSV."""
        monkeypatch.setenv("BEA_API_KEY", "dummy-key")
        ingestor = _make_ingestor()

        with patch("raw.bea_rpp_ingestor.requests.get") as mock_get:
            mock_get.side_effect = Exception("network down")
            result = ingestor.fetch({"rpp": "test"}, "bea_api")

        # Should have retried once before falling back (total 2 calls).
        assert mock_get.call_count == 2
        payload = result["rpp"]
        assert payload["source_method"] == "csv_cache"
        assert len(payload["records"]) == 51

    def test_api_success_returns_parsed_records(self, monkeypatch):
        """When the API succeeds, fetch returns its parsed records."""
        monkeypatch.setenv("BEA_API_KEY", "dummy-key")
        ingestor = _make_ingestor()

        class FakeResponse:
            status_code = 200

            def raise_for_status(self):
                return None

            def json(self):
                return _sample_api_response()

        with patch("raw.bea_rpp_ingestor.requests.get") as mock_get:
            mock_get.return_value = FakeResponse()
            result = ingestor.fetch({"rpp": "test"}, "bea_api")

        payload = result["rpp"]
        assert payload["source_method"] == "bea_api"
        assert len(payload["records"]) == 4

    def test_force_fallback_skips_api(self, monkeypatch):
        """force_fallback=True causes CSV cache even with valid key."""
        monkeypatch.setenv("BEA_API_KEY", "dummy-key")
        ingestor = _make_ingestor()
        with patch("raw.bea_rpp_ingestor.requests.get") as mock_get:
            result = ingestor.fetch({"rpp": "test"}, "bea_api", force_fallback=True)
        mock_get.assert_not_called()
        assert result["rpp"]["source_method"] == "csv_cache"


# ----------------------------------------------------------------------
# Integration: write to a temp Iceberg warehouse via BaseIngestor.ingest()
# ----------------------------------------------------------------------


class TestIngestIntegration:
    """End-to-end ingest into a temporary Iceberg warehouse using the CSV cache."""

    def test_ingest_lands_51_rows(self, tmp_path, monkeypatch):
        from brightsmith.domain_loader import (
            DomainHints,
            DomainManifest,
            SourceConfig,
        )
        from brightsmith.infra.iceberg_setup import get_catalog, read_with_duckdb

        # Make sure no stray env key can redirect us to the live API
        monkeypatch.delenv("BEA_API_KEY", raising=False)

        source = SourceConfig(
            name="bea_rpp",
            namespace="bronze",
            table="bea_rpp",
            fetch={"bea_api": {"fallback_path": str(CACHE_CSV)}},
            entities={"rpp": "BEA RPP — integration test"},
            dedup_grain=["geo_fips"],
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

        ingestor = BeaRppIngestor(source, manifest)
        results = ingestor.ingest(
            warehouse_path=warehouse,
            catalog_path=catalog_path,
            csv_path=str(CACHE_CSV),
        )

        assert "rpp" in results
        assert results["rpp"]["rows"] == 51

        catalog = get_catalog(warehouse, catalog_path)
        table = catalog.load_table("bronze.bea_rpp")
        rows = read_with_duckdb(table)
        assert len(rows) == 51

        # Verify verified values survived the round trip
        by_name = {r["geo_name"]: r for r in rows}
        assert by_name["California"]["rpp_all_items"] == 110.7
        assert by_name["Iowa"]["rpp_all_items"] == 87.8
        assert by_name["Arkansas"]["rpp_all_items"] == 86.9

        # source_method was set to "csv_cache" (fallback path)
        for r in rows:
            assert r["source_method"] == "csv_cache"


# ----------------------------------------------------------------------
# Live network test (skipped by default)
# ----------------------------------------------------------------------


@pytest.mark.network
class TestLiveApi:
    def test_live_bea_api(self):
        import os

        api_key = os.environ.get("BEA_API_KEY")
        if not api_key:
            pytest.skip("BEA_API_KEY not set")

        ingestor = _make_ingestor()
        records = ingestor._fetch_from_api(api_key)
        assert len(records) >= 51
        # Every state record should parse into a valid 2-digit FIPS
        payload = {"records": records, "source_method": "bea_api"}
        flat = ingestor.flatten(payload, "rpp")
        assert len(flat) == 51
