"""Ingestor for BEA Regional Price Parities (SARPP — All Items).

Ingests state-level Regional Price Parity index values for 50 states
and the District of Columbia from the U.S. Bureau of Economic Analysis
(BEA) Regional Economic Accounts.  Primary path is the BEA JSON API;
fallback is a locally-cached CSV that mirrors the API field layout so
the same parser handles both paths.

Grain: 2-digit state FIPS code (geo_fips).
"""

from __future__ import annotations

import csv
import logging
import os
import time
from pathlib import Path
from typing import Any

import requests
from pyiceberg.schema import Schema
from pyiceberg.types import (
    DateType,
    DoubleType,
    IntegerType,
    NestedField,
    StringType,
    TimestampType,
)

from brightsmith.bronze.base_ingestor import BaseIngestor

logger = logging.getLogger(__name__)


class BeaRppIngestor(BaseIngestor):
    """Ingests BEA Regional Price Parities into the bronze zone.

    Data source: BEA JSON API (Regional dataset, table SARPP, LineCode=1,
    GeoFips=STATE, Year=2024).  Falls back to a locally-cached CSV if the
    API is unavailable, rate limited, missing an API key, or returns a
    response that does not match the expected schema.

    Grain: geo_fips (2-digit state FIPS code, zero-padded string)

    Key considerations:
    - BEA API returns DataValue as a string (e.g. "110.7") — coerce to float
    - Parse BEAAPI.Results.Data — fail loudly on schema drift
    - Filter to state-level rows only (2-digit FIPS 01-56 plus 11 for DC).
      Metro/CBSA rows are logged as a warning and dropped.
    - Single retry with short backoff on transient API failure, then fall
      back to the CSV cache.
    - CSV columns mirror the BEA API field names so one parser handles both.
    """

    API_URL_TEMPLATE = (
        "https://apps.bea.gov/api/data/"
        "?&UserID={api_key}"
        "&method=GetData"
        "&datasetname=Regional"
        "&TableName=SARPP"
        "&LineCode=1"
        "&Year=2024"
        "&GeoFips=STATE"
        "&ResultFormat=JSON"
    )
    FALLBACK_CSV_PATH = "data/raw/bea_cache/bea_rpp_2024.csv"
    USER_AGENT = "FutureProof/0.1 (jeff@hyenastudios.com)"
    API_ENV_KEY = "BEA_API_KEY"
    DEFAULT_YEAR = 2024

    # Valid 2-digit state FIPS codes (50 states + DC).  Territory codes
    # (60, 66, 69, 72, 78) are NOT included — this pipeline is 50 states + DC.
    VALID_STATE_FIPS: frozenset[str] = frozenset(
        {f"{code:02d}" for code in (
            1, 2, 4, 5, 6, 8, 9,
            10, 11, 12, 13, 15, 16, 17, 18, 19,
            20, 21, 22, 23, 24, 25, 26, 27, 28, 29,
            30, 31, 32, 33, 34, 35, 36, 37, 38, 39,
            40, 41, 42, 44, 45, 46, 47, 48, 49,
            50, 51, 53, 54, 55, 56,
        )}
    )

    # ------------------------------------------------------------------
    # Ingest override (to reflect true source_method in rows)
    # ------------------------------------------------------------------

    def ingest(self, *args, **kwargs) -> dict:
        """Run the BaseIngestor pipeline, fixing source_method post-hoc.

        The framework always overwrites each row's ``source_method`` with
        the ``method`` argument passed to ingest().  For BEA RPP we want
        the row-level value to reflect whether we actually hit the API
        or fell back to the CSV cache — a decision only made during
        fetch().  We run fetch() eagerly here, capture the real method,
        then pass it through as the framework's method argument and
        stash the pre-fetched payload so BaseIngestor.fetch() won't
        duplicate the work.
        """
        # Normalize kwargs
        entities = kwargs.pop("entities", None) or self.source.entities
        warehouse_path = kwargs.pop("warehouse_path", None)
        catalog_path = kwargs.pop("catalog_path", None)
        # Drop any caller-supplied method — we will supply our own.
        kwargs.pop("method", None)

        # Run fetch once, up front, to determine the true source_method.
        raw_data = self.fetch(entities, method="bea_rpp", **kwargs)
        sample = next(iter(raw_data.values())) if raw_data else {}
        effective_method = sample.get("source_method", "csv_cache")
        self._prefetched = raw_data

        try:
            return super().ingest(
                entities=entities,
                method=effective_method,
                warehouse_path=warehouse_path,
                catalog_path=catalog_path,
                **kwargs,
            )
        finally:
            self._prefetched = None

    # ------------------------------------------------------------------
    # Fetch
    # ------------------------------------------------------------------

    def fetch(self, entities: dict, method: str, **kwargs) -> dict:
        """Fetch BEA RPP rows via API (preferred) or CSV cache (fallback).

        Args:
            entities: {entity_id: label} dict from source config.
            method: Fetch method name (informational only).
            **kwargs: Supports:
                - ``csv_path``: explicit local CSV (used in tests; skips API)
                - ``api_key``: override BEA_API_KEY env var
                - ``force_fallback``: True to skip the API call entirely
                - ``cache_dir``: override default fallback CSV location

        Returns:
            Dict mapping each entity_id to a dict with keys
            ``records`` (list of raw BEA-shaped dicts) and ``source_method``
            ("bea_api" or "csv_cache").
        """
        # Reuse the payload stashed by ingest() if present (avoids a
        # second network call when ingest() ran fetch() itself).
        prefetched = getattr(self, "_prefetched", None)
        if prefetched:
            return prefetched

        csv_path = kwargs.get("csv_path")
        api_key = kwargs.get("api_key") or os.environ.get(self.API_ENV_KEY)
        force_fallback = bool(kwargs.get("force_fallback"))
        cache_dir = kwargs.get("cache_dir")

        # Explicit CSV path always wins (used in tests)
        if csv_path:
            records = self._read_csv_file(Path(csv_path))
            payload = {"records": records, "source_method": "csv_cache"}
            return {entity_id: payload for entity_id in entities}

        # Try the API if we have a key and aren't forced to fall back
        if api_key and not force_fallback:
            try:
                records = self._fetch_from_api(api_key)
                payload = {"records": records, "source_method": "bea_api"}
                return {entity_id: payload for entity_id in entities}
            except Exception as exc:
                logger.warning(
                    "BEA API fetch failed (%s), falling back to CSV cache", exc
                )

        # Fall back to CSV cache
        fallback_path = Path(cache_dir) if cache_dir else Path(self.FALLBACK_CSV_PATH)
        if fallback_path.is_dir():
            fallback_path = fallback_path / "bea_rpp_2024.csv"
        records = self._read_csv_file(fallback_path)
        payload = {"records": records, "source_method": "csv_cache"}
        return {entity_id: payload for entity_id in entities}

    def _fetch_from_api(self, api_key: str) -> list[dict]:
        """Call the BEA API with a single retry on transient failure."""
        url = self.API_URL_TEMPLATE.format(api_key=api_key)
        headers = {"User-Agent": self.USER_AGENT}

        last_exc: Exception | None = None
        for attempt in (1, 2):
            try:
                response = requests.get(url, headers=headers, timeout=30)
                response.raise_for_status()
                data = response.json()
                return self._parse_api_response(data)
            except Exception as exc:
                last_exc = exc
                if attempt == 1:
                    logger.warning(
                        "BEA API attempt %d failed (%s), retrying", attempt, exc
                    )
                    time.sleep(1.5)
                    continue
                raise
        # Unreachable — loop either returns or raises.
        raise RuntimeError(f"BEA API fetch failed: {last_exc}")

    # ------------------------------------------------------------------
    # Parsers
    # ------------------------------------------------------------------

    def _parse_api_response(self, data: Any) -> list[dict]:
        """Extract the Data array from a BEA API JSON response.

        Asserts the expected nested structure and raises ValueError on
        any shape drift so the ingestor can fall back to the CSV cache.
        """
        if not isinstance(data, dict):
            raise ValueError(f"BEA API response is not a dict: {type(data).__name__}")

        beaapi = data.get("BEAAPI")
        if not isinstance(beaapi, dict):
            raise ValueError("BEA API response missing BEAAPI object")

        # BEA returns errors inside Results.Error
        results = beaapi.get("Results")
        if not isinstance(results, dict):
            raise ValueError("BEA API response missing BEAAPI.Results object")

        if "Error" in results:
            raise ValueError(f"BEA API returned error: {results['Error']}")

        records = results.get("Data")
        if not isinstance(records, list):
            raise ValueError("BEA API response missing BEAAPI.Results.Data array")

        if not records:
            raise ValueError("BEA API returned an empty Data array")

        required_keys = {"GeoFips", "GeoName", "DataValue"}
        for idx, row in enumerate(records[:3]):
            if not isinstance(row, dict):
                raise ValueError(
                    f"BEA API Data[{idx}] is not an object: {type(row).__name__}"
                )
            missing = required_keys - set(row.keys())
            if missing:
                raise ValueError(
                    f"BEA API Data[{idx}] missing required keys: {sorted(missing)}"
                )

        logger.info("Parsed %d records from BEA API response", len(records))
        return records

    def _read_csv_file(self, path: Path) -> list[dict]:
        """Read a CSV cache file whose columns mirror the BEA API field names."""
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        logger.info("Read %d records from CSV cache %s", len(rows), path)
        return rows

    # ------------------------------------------------------------------
    # Flatten
    # ------------------------------------------------------------------

    def flatten(self, raw_data: Any, entity_id: str) -> list[dict]:
        """Flatten raw BEA records into Iceberg-ready dicts.

        - Zero-pads geo_fips to 2-char string (state FIPS).
        - Filters to state-level 2-digit FIPS (50 states + DC).
        - Logs a warning (not error) if metro/CBSA rows appear.
        - Adds ``source_method`` so it lands in the row before the
          framework metadata pass.

        Args:
            raw_data: Dict with keys ``records`` and ``source_method``.
            entity_id: Logical entity identifier (unused — single entity).

        Returns:
            List of flat dicts with lowercase keys matching the schema.
            Does NOT add ingested_at / source_url / load_date — the
            framework handles those in BaseIngestor.ingest().
        """
        records = raw_data["records"]

        flat_rows: list[dict] = []
        metro_skipped = 0
        non_state_skipped = 0

        for row in records:
            geo_fips_raw = row.get("GeoFips")
            if geo_fips_raw is None:
                continue

            geo_fips = self._normalize_geo_fips(geo_fips_raw)
            if geo_fips is None:
                continue

            # Metro areas have 5-digit CBSA codes; the BEA SARPP API may
            # return them if a caller forgets GeoFips=STATE.  Filter and
            # log, do not error out.
            if len(geo_fips) != 2:
                metro_skipped += 1
                continue

            if geo_fips not in self.VALID_STATE_FIPS:
                non_state_skipped += 1
                continue

            rpp_value = self._coerce_double(row.get("DataValue"))
            data_year = self._coerce_int(row.get("TimePeriod")) or self.DEFAULT_YEAR

            record = {
                "geo_fips": geo_fips,
                "geo_name": self._coerce_string(row.get("GeoName")),
                "rpp_all_items": rpp_value,
                "data_year": data_year,
            }
            flat_rows.append(record)

        if metro_skipped:
            logger.warning(
                "Filtered %d metro/CBSA rows from BEA RPP response", metro_skipped
            )
        if non_state_skipped:
            logger.warning(
                "Filtered %d non-state rows from BEA RPP response", non_state_skipped
            )

        logger.info("Flattened %d state-level BEA RPP rows", len(flat_rows))
        return flat_rows

    def get_source_url(self, entity_id: Any, method: str) -> str:
        """Return the source URL for lineage/audit purposes.

        API key is redacted from the URL for safety.
        """
        return self.API_URL_TEMPLATE.format(api_key="REDACTED")

    # ------------------------------------------------------------------
    # Coercion helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_geo_fips(value: Any) -> str | None:
        """Normalize GeoFips to a zero-padded numeric string.

        BEA returns 5-digit codes like "06000" for state California and
        "31080" for metro Los Angeles.  State codes are in the form
        XX000 — strip the trailing zeros to get a 2-digit state FIPS.
        CSV cache follows the same convention.

        Returns:
            - 2-char zero-padded string for state-level rows
            - original string for metro/CBSA rows (caller filters those)
            - None if the value is empty/unparseable
        """
        if value is None:
            return None
        s = str(value).strip()
        if not s:
            return None
        # Strip any non-digit characters
        digits = "".join(ch for ch in s if ch.isdigit())
        if not digits:
            return None

        # State-level GeoFips is 5 digits ending in "000" (e.g. "06000").
        # In that case the state FIPS is the first 2 digits.
        if len(digits) == 5 and digits.endswith("000"):
            return digits[:2].zfill(2)
        # Already a 2-digit state code
        if len(digits) <= 2:
            return digits.zfill(2)
        # Metro/CBSA or unknown — return as-is so the caller can filter.
        return digits

    @staticmethod
    def _coerce_string(value: Any) -> str | None:
        if value is None:
            return None
        s = str(value).strip()
        return s if s else None

    @staticmethod
    def _coerce_double(value: Any) -> float | None:
        if value is None:
            return None
        if isinstance(value, str):
            value = value.strip().replace(",", "")
            if not value:
                return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _coerce_int(value: Any) -> int | None:
        if value is None:
            return None
        if isinstance(value, str):
            value = value.strip()
            if not value:
                return None
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return None

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------

    def get_schema(self) -> Schema:
        """Define the Iceberg table schema for bronze.bea_rpp.

        Matches the fields returned by flatten() plus framework metadata.
        Grain is geo_fips.
        """
        return Schema(
            # Grain field
            NestedField(1, "geo_fips", StringType(), required=True),
            # Data fields
            NestedField(2, "geo_name", StringType(), required=True),
            NestedField(3, "rpp_all_items", DoubleType(), required=True),
            NestedField(4, "data_year", IntegerType(), required=True),
            # Metadata
            NestedField(5, "ingested_at", TimestampType(), required=True),
            NestedField(6, "source_url", StringType(), required=True),
            NestedField(7, "source_method", StringType(), required=True),
            NestedField(8, "load_date", DateType(), required=True),
        )
