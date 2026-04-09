"""Ingestor for U.S. Department of Education College Scorecard field-of-study data."""

import csv
import io
import logging
import zipfile
from pathlib import Path
from typing import Any

import requests
from pyiceberg.schema import Schema
from pyiceberg.types import (
    DateType,
    DoubleType,
    IntegerType,
    LongType,
    NestedField,
    StringType,
    TimestampType,
)

from brightsmith.bronze.base_ingestor import BaseIngestor

logger = logging.getLogger(__name__)


class CollegeScorecardIngestor(BaseIngestor):
    """Ingests College Scorecard field-of-study-level data into the bronze zone.

    Data source: bulk CSV download from the U.S. Department of Education.
    The ZIP file contains a single CSV with ~174 columns and ~500MB uncompressed.

    Grain: institution (UNITID) x program (CIPCODE) x credential level (CREDLEV)

    Key considerations:
    - Large CSV requires chunked reading via the stdlib csv module
    - Privacy-suppressed values appear as "PrivacySuppressed" (or "PS" in some
      sample files) and must be converted to null during flatten()
    - MVP filter: CREDLEV=3 (bachelor's degree only)
    - CIPCODE must remain a string to preserve leading zeros and XX.XXXX format
    """

    DOWNLOAD_URL = (
        "https://ed-public-download.app.cloud.gov/downloads/"
        "Most-Recent-Cohorts-Field-of-Study.csv"
    )
    FALLBACK_URL = (
        "https://ed-public-download.scorecard.network/downloads/"
        "Most-Recent-Cohorts-Field-of-Study_04172025.zip"
    )
    USER_AGENT = "FutureProof/0.1 (jeff@hyenastudios.com)"

    # MVP: only bachelor's degrees
    CREDLEV_FILTER = 3

    # Columns to extract from the source CSV (uppercase) mapped to
    # lowercase Iceberg field names.
    COLUMN_MAP: dict[str, str] = {
        "UNITID": "unitid",
        "INSTNM": "instnm",
        "CIPCODE": "cipcode",
        "CIPDESC": "cipdesc",
        "CREDDESC": "creddesc",
        "CREDLEV": "credlev",
        "MD_EARN_WNE": "md_earn_wne",
        "EARN_MDN_HI_1YR": "earn_mdn_hi_1yr",
        "EARN_MDN_HI_2YR": "earn_mdn_hi_2yr",
        "DEBT_ALL_STGP_EVAL_MDN": "debt_all_stgp_eval_mdn",
        "IPEDSCOUNT1": "ipedscount1",
        "IPEDSCOUNT2": "ipedscount2",
        "CONTROL": "control",
    }

    # Values that represent suppressed or missing data in the source CSV.
    SENTINEL_VALUES = {"PrivacySuppressed", "PS", "NA", "NULL", ""}

    def fetch(self, entities: dict, method: str, **kwargs) -> dict:
        """Download College Scorecard bulk CSV and filter to bachelor's degrees.

        Attempts the primary URL first. If that returns a non-200 status, falls
        back to the known working ZIP URL. Handles both plain CSV and ZIP-wrapped
        CSV responses.

        Args:
            entities: {entity_id: label} dict from source config.
            method: Fetch method -- "bulk_csv_download" for this source.
            **kwargs: Additional options. Supports ``csv_path`` to skip the
                download and read from a local file instead (used in tests).

        Returns:
            Dict mapping each entity_id to a list of row dicts (pre-filtered
            to CREDLEV=3, with sentinel values already nullified).
        """
        csv_path = kwargs.get("csv_path")
        if csv_path is not None:
            rows = self._read_csv(Path(csv_path))
        else:
            rows = self._download_and_read()

        # Return the same filtered rows for every entity key.
        return {entity_id: rows for entity_id in entities}

    def _download_and_read(self) -> list[dict[str, str]]:
        """Download the CSV from the remote URL and return parsed rows."""
        headers = {"User-Agent": self.USER_AGENT}

        # Try primary URL first.
        response = requests.get(
            self.DOWNLOAD_URL, headers=headers, allow_redirects=True, stream=True, timeout=300
        )

        if response.status_code != 200:
            logger.warning(
                "Primary URL returned %d, falling back to %s",
                response.status_code,
                self.FALLBACK_URL,
            )
            response = requests.get(
                self.FALLBACK_URL, headers=headers, allow_redirects=True, stream=True, timeout=300
            )
            response.raise_for_status()

        content = response.content

        # If the response is a ZIP, extract the CSV from it.
        if self._is_zip(content):
            content = self._extract_csv_from_zip(content)

        # Remove BOM if present.
        if content.startswith(b"\xef\xbb\xbf"):
            content = content[3:]

        text = content.decode("utf-8")
        return self._parse_csv_text(text)

    @staticmethod
    def _is_zip(content: bytes) -> bool:
        """Check if content starts with the ZIP magic bytes."""
        return content[:4] == b"PK\x03\x04"

    @staticmethod
    def _extract_csv_from_zip(content: bytes) -> bytes:
        """Extract the first CSV file from a ZIP archive in memory."""
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            csv_names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
            if not csv_names:
                raise ValueError("ZIP archive contains no CSV files")
            return zf.read(csv_names[0])

    def _read_csv(self, path: Path) -> list[dict[str, str]]:
        """Read a local CSV file and return filtered rows as raw string dicts."""
        text = path.read_text(encoding="utf-8-sig")
        return self._parse_csv_text(text)

    def _parse_csv_text(self, text: str) -> list[dict[str, str]]:
        """Parse CSV text, filter to CREDLEV=3, return list of raw row dicts.

        Each row dict contains only the columns listed in COLUMN_MAP,
        keyed by the original uppercase CSV column names. Sentinel values
        are preserved as-is here; nullification happens in flatten().
        """
        reader = csv.DictReader(io.StringIO(text))
        available_columns = set(reader.fieldnames or [])
        target_columns = set(self.COLUMN_MAP.keys()) & available_columns

        rows: list[dict[str, str]] = []
        for row in reader:
            # Filter to bachelor's degrees.
            credlev_raw = row.get("CREDLEV", "")
            try:
                if int(credlev_raw) != self.CREDLEV_FILTER:
                    continue
            except (ValueError, TypeError):
                continue

            # Keep only the columns we care about.
            filtered = {col: row[col] for col in target_columns}
            rows.append(filtered)

        logger.info("Parsed %d rows after CREDLEV=%d filter", len(rows), self.CREDLEV_FILTER)
        return rows

    def flatten(self, raw_data: Any, entity_id: str) -> list[dict]:
        """Flatten raw CSV rows into Iceberg-ready dicts.

        Converts sentinel strings ("PrivacySuppressed", "PS", "NA") to None
        and coerces numeric fields to their target Python types.

        Args:
            raw_data: List of row dicts from fetch(), keyed by uppercase
                CSV column names.
            entity_id: Logical entity identifier (unused but required by
                the framework).

        Returns:
            List of flat dicts with lowercase keys matching the Iceberg schema.
            Does NOT add metadata fields (ingested_at, source_url, etc.) --
            the framework handles those.
        """
        grain_fields = ("unitid", "cipcode", "credlev")
        flat_rows: list[dict] = []
        skipped = 0
        for raw_row in raw_data:
            record: dict = {}
            for csv_col, iceberg_col in self.COLUMN_MAP.items():
                raw_val = raw_row.get(csv_col)
                record[iceberg_col] = self._coerce(iceberg_col, raw_val)
            # Skip rows with null grain fields — they can't be deduped.
            if any(record.get(f) is None for f in grain_fields):
                skipped += 1
                continue
            flat_rows.append(record)
        if skipped:
            logger.warning("Skipped %d rows with null grain fields", skipped)
        return flat_rows

    def _coerce(self, field_name: str, value: str | None) -> Any:
        """Coerce a raw string value to the appropriate Python type.

        Returns None for sentinel values. Converts numeric strings to
        int/float based on the field's expected type in the schema.
        """
        if value is None or value.strip() in self.SENTINEL_VALUES:
            return None

        value = value.strip()

        # String fields: return as-is.
        if field_name in ("instnm", "cipcode", "cipdesc", "creddesc", "control"):
            return value

        # Long integer fields.
        if field_name in ("unitid", "ipedscount1", "ipedscount2"):
            try:
                return int(value)
            except (ValueError, TypeError):
                return None

        # Integer fields.
        if field_name == "credlev":
            try:
                return int(value)
            except (ValueError, TypeError):
                return None

        # Double fields (earnings, debt).
        if field_name in (
            "md_earn_wne",
            "earn_mdn_hi_1yr",
            "earn_mdn_hi_2yr",
            "debt_all_stgp_eval_mdn",
        ):
            try:
                return float(value)
            except (ValueError, TypeError):
                return None

        return value

    def get_schema(self) -> Schema:
        """Define the Iceberg table schema for raw.college_scorecard.

        Matches the fields returned by flatten(). Grain is
        UNITID x CIPCODE x CREDLEV.
        """
        return Schema(
            # Identity / grain fields
            NestedField(1, "unitid", LongType(), required=True),
            NestedField(2, "instnm", StringType(), required=False),
            NestedField(3, "cipcode", StringType(), required=True),
            NestedField(4, "cipdesc", StringType(), required=False),
            NestedField(5, "creddesc", StringType(), required=False),
            NestedField(6, "credlev", IntegerType(), required=True),
            NestedField(17, "control", StringType(), required=False),
            # Outcome fields
            NestedField(7, "md_earn_wne", DoubleType(), required=False),
            NestedField(8, "earn_mdn_hi_1yr", DoubleType(), required=False),
            NestedField(9, "earn_mdn_hi_2yr", DoubleType(), required=False),
            NestedField(10, "debt_all_stgp_eval_mdn", DoubleType(), required=False),
            # Completions counts
            NestedField(11, "ipedscount1", LongType(), required=False),
            NestedField(12, "ipedscount2", LongType(), required=False),
            # Metadata
            NestedField(13, "ingested_at", TimestampType(), required=True),
            NestedField(14, "source_url", StringType(), required=True),
            NestedField(15, "source_method", StringType(), required=True),
            NestedField(16, "load_date", DateType(), required=True),
        )
