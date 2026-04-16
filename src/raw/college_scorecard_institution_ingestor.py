"""Ingestor for U.S. Department of Education College Scorecard institution-level data."""

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


class CollegeScorecardInstitutionIngestor(BaseIngestor):
    """Ingests College Scorecard institution-level cost data into the bronze zone.

    Data source: bulk CSV download from the U.S. Department of Education.
    The CSV contains ~1,900 columns and ~170MB; we extract only ~24 fields.

    Grain: institution (UNITID)

    Key considerations:
    - Large CSV requires selective column reading via csv.DictReader
    - Privacy-suppressed values appear as "PrivacySuppressed" (or "PS" in some
      files) and must be converted to null during flatten()
    - Filter: PREDDEG=3 (predominantly bachelor's) OR ICLEVEL=1 (4-year institution)
    - UNITID is integer/long -- matches the field-of-study file's UNITID
    - CONTROL is integer (1=Public, 2=Private nonprofit, 3=Private for-profit)
    - Dedup on UNITID (one row per institution)
    """

    DOWNLOAD_URL = (
        "https://ed-public-download.app.cloud.gov/downloads/"
        "Most-Recent-Cohorts-Institution.csv"
    )
    USER_AGENT = "FutureProof/0.1 (jeff@hyenastudios.com)"

    # Columns to extract from the source CSV (uppercase) mapped to
    # lowercase Iceberg field names.
    COLUMN_MAP: dict[str, str] = {
        "UNITID": "unitid",
        "INSTNM": "instnm",
        "STABBR": "stabbr",
        "CONTROL": "control",
        "PREDDEG": "preddeg",
        "COSTT4_A": "costt4_a",
        "COSTT4_P": "costt4_p",
        "NPT4_PUB": "npt4_pub",
        "NPT4_PRIV": "npt4_priv",
        "NPT41_PUB": "npt41_pub",
        "NPT42_PUB": "npt42_pub",
        "NPT43_PUB": "npt43_pub",
        "NPT44_PUB": "npt44_pub",
        "NPT45_PUB": "npt45_pub",
        "NPT41_PRIV": "npt41_priv",
        "NPT42_PRIV": "npt42_priv",
        "NPT43_PRIV": "npt43_priv",
        "NPT44_PRIV": "npt44_priv",
        "NPT45_PRIV": "npt45_priv",
        "TUITIONFEE_IN": "tuitionfee_in",
        "TUITIONFEE_OUT": "tuitionfee_out",
        "ROOMBOARD_ON": "roomboard_on",
        "ROOMBOARD_OFF": "roomboard_off",
        "BOOKSUPPLY": "booksupply",
    }

    # Additional columns needed for filtering but not stored in the output.
    _FILTER_COLUMNS = {"ICLEVEL"}

    # Values that represent suppressed or missing data in the source CSV.
    SENTINEL_VALUES = {"PrivacySuppressed", "PS", "NA", "NULL", ""}

    # String fields (returned as-is after sentinel check).
    _STRING_FIELDS = frozenset({"instnm", "stabbr"})

    # Long integer fields.
    _LONG_FIELDS = frozenset({"unitid"})

    # Integer fields.
    _INT_FIELDS = frozenset({"control", "preddeg"})

    # All remaining mapped fields are double.

    def fetch(self, entities: dict, method: str, **kwargs) -> dict:
        """Download College Scorecard institution CSV and filter to 4-year bachelor's.

        Attempts the primary URL. Handles both plain CSV and ZIP-wrapped
        CSV responses.

        Args:
            entities: {entity_id: label} dict from source config.
            method: Fetch method -- "bulk_csv_download" for this source.
            **kwargs: Additional options. Supports ``csv_path`` to skip the
                download and read from a local file instead (used in tests).

        Returns:
            Dict mapping each entity_id to a list of row dicts (pre-filtered
            to PREDDEG=3 or ICLEVEL=1, with sentinel values preserved for
            nullification in flatten()).
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

        response = requests.get(
            self.DOWNLOAD_URL, headers=headers, allow_redirects=True, stream=True, timeout=300
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
        """Parse CSV text, filter to 4-year bachelor's institutions, dedup on UNITID.

        Each row dict contains only the columns listed in COLUMN_MAP,
        keyed by the original uppercase CSV column names. Sentinel values
        are preserved as-is here; nullification happens in flatten().

        Filter logic: PREDDEG == 3 (predominantly bachelor's) OR ICLEVEL == 1
        (4-year institution).

        Dedup: first row per UNITID wins.
        """
        reader = csv.DictReader(io.StringIO(text))
        available_columns = set(reader.fieldnames or [])
        target_columns = set(self.COLUMN_MAP.keys()) & available_columns

        seen_unitids: set[str] = set()
        rows: list[dict[str, str]] = []
        for row in reader:
            # Filter: PREDDEG == 3 OR ICLEVEL == 1
            preddeg_raw = row.get("PREDDEG", "")
            iclevel_raw = row.get("ICLEVEL", "")
            try:
                preddeg_match = int(preddeg_raw) == 3
            except (ValueError, TypeError):
                preddeg_match = False
            try:
                iclevel_match = int(iclevel_raw) == 1
            except (ValueError, TypeError):
                iclevel_match = False

            if not (preddeg_match or iclevel_match):
                continue

            # Dedup on UNITID -- first row wins.
            unitid = row.get("UNITID", "")
            if unitid in seen_unitids:
                continue
            seen_unitids.add(unitid)

            # Keep only the columns we care about.
            filtered = {col: row[col] for col in target_columns}
            rows.append(filtered)

        logger.info(
            "Parsed %d rows after PREDDEG=3/ICLEVEL=1 filter (deduped on UNITID)", len(rows)
        )
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
        grain_fields = ("unitid",)
        flat_rows: list[dict] = []
        skipped = 0
        for raw_row in raw_data:
            record: dict = {}
            for csv_col, iceberg_col in self.COLUMN_MAP.items():
                raw_val = raw_row.get(csv_col)
                record[iceberg_col] = self._coerce(iceberg_col, raw_val)
            # Skip rows with null grain fields -- they can't be deduped.
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
        if field_name in self._STRING_FIELDS:
            return value

        # Long integer fields.
        if field_name in self._LONG_FIELDS:
            try:
                return int(value)
            except (ValueError, TypeError):
                return None

        # Integer fields.
        if field_name in self._INT_FIELDS:
            try:
                return int(value)
            except (ValueError, TypeError):
                return None

        # All remaining fields are double (cost/price fields).
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    def get_schema(self) -> Schema:
        """Define the Iceberg table schema for raw.college_scorecard_institution.

        Matches the fields returned by flatten(). Grain is UNITID.
        """
        return Schema(
            # Identity / grain fields
            NestedField(1, "unitid", LongType(), required=True),
            NestedField(2, "instnm", StringType(), required=True),
            NestedField(3, "stabbr", StringType(), required=True),
            NestedField(4, "control", IntegerType(), required=True),
            NestedField(5, "preddeg", IntegerType(), required=True),
            # Cost of attendance
            NestedField(6, "costt4_a", DoubleType(), required=False),
            NestedField(7, "costt4_p", DoubleType(), required=False),
            # Average net price
            NestedField(8, "npt4_pub", DoubleType(), required=False),
            NestedField(9, "npt4_priv", DoubleType(), required=False),
            # Net price by income quintile -- public
            NestedField(10, "npt41_pub", DoubleType(), required=False),
            NestedField(11, "npt42_pub", DoubleType(), required=False),
            NestedField(12, "npt43_pub", DoubleType(), required=False),
            NestedField(13, "npt44_pub", DoubleType(), required=False),
            NestedField(14, "npt45_pub", DoubleType(), required=False),
            # Net price by income quintile -- private
            NestedField(15, "npt41_priv", DoubleType(), required=False),
            NestedField(16, "npt42_priv", DoubleType(), required=False),
            NestedField(17, "npt43_priv", DoubleType(), required=False),
            NestedField(18, "npt44_priv", DoubleType(), required=False),
            NestedField(19, "npt45_priv", DoubleType(), required=False),
            # Tuition
            NestedField(20, "tuitionfee_in", DoubleType(), required=False),
            NestedField(21, "tuitionfee_out", DoubleType(), required=False),
            # Room and board
            NestedField(22, "roomboard_on", DoubleType(), required=False),
            NestedField(23, "roomboard_off", DoubleType(), required=False),
            # Books and supplies
            NestedField(24, "booksupply", DoubleType(), required=False),
            # Metadata
            NestedField(25, "ingested_at", TimestampType(), required=True),
            NestedField(26, "source_url", StringType(), required=True),
            NestedField(27, "source_method", StringType(), required=True),
            NestedField(28, "load_date", DateType(), required=True),
        )
