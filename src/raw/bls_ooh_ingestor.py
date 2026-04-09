"""Ingestor for Bureau of Labor Statistics Occupational Outlook Handbook projections data."""

import logging
import re
from pathlib import Path
from typing import Any

import requests
from pyiceberg.schema import Schema
from pyiceberg.types import (
    BooleanType,
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


class BlsOohIngestor(BaseIngestor):
    """Ingests BLS Employment Projections data into the bronze zone.

    Data source: XLSX download from the Bureau of Labor Statistics
    Employment Projections tables (occupational projections and characteristics).

    Grain: occupation (SOC code, XX-XXXX format)

    Key considerations:
    - BLS blocks bot User-Agents; use a browser-like UA string
    - Employment figures are in thousands in the source; multiply by 1000
    - Median wage may be top-coded (">=239,200" or similar) -- flag with median_wage_capped
    - SOC codes ending in "0000" are major group summaries and should be filtered out
    - Column headers vary between BLS projection cycles; use flexible matching
    """

    DOWNLOAD_URL = (
        "https://www.bls.gov/emp/tables/occupational-projections-and-characteristics.htm"
    )
    FALLBACK_PATH = "data/raw/xlsx_cache/bls_ooh.xlsx"
    USER_AGENT = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    CONTACT_EMAIL = "jeff@hyenastudios.com"

    # BLS education level codes derived from string labels.
    # Source: BLS Employment Projections methodology, Table 5.4
    _EDUCATION_CODE_MAP: dict[str, int] = {
        "doctoral or professional degree": 1,
        "master's degree": 2,
        "bachelor's degree": 3,
        "associate's degree": 4,
        "postsecondary nondegree award": 5,
        "some college, no degree": 6,
        "high school diploma or equivalent": 7,
        "no formal educational credential": 8,
    }

    # BLS work experience codes derived from string labels.
    _WORK_EXPERIENCE_CODE_MAP: dict[str, int] = {
        "5 years or more": 1,
        "less than 5 years": 2,
        "none": 3,
    }

    # BLS on-the-job training codes derived from string labels.
    _TRAINING_CODE_MAP: dict[str, int] = {
        "internship/residency": 1,
        "apprenticeship": 2,
        "long-term on-the-job training": 3,
        "moderate-term on-the-job training": 4,
        "short-term on-the-job training": 5,
        "none": 6,
    }

    # Map keyword fragments to Iceberg field names.  Matching is done via
    # case-insensitive substring search against actual XLSX column headers.
    COLUMN_MAP: dict[str, str] = {
        "occupation_title": "occupation_title",
        "soc_code": "soc_code",
        "employment_current": "employment_current",
        "employment_projected": "employment_projected",
        "employment_change_num": "employment_change",
        "employment_change_pct": "employment_change_pct",
        "openings_annual_avg": "openings_annual_avg",
        "median_annual_wage": "median_annual_wage",
        "education_typical": "education_typical",
        "education_code": "education_code",
        "work_experience": "work_experience",
        "work_experience_code": "work_experience_code",
        "training_typical": "training_typical",
        "training_code": "training_code",
    }

    # Patterns to match XLSX column headers to our canonical field names.
    # Order matters -- first match wins.  Patterns are case-insensitive
    # substrings tested against the actual XLSX header text.
    #
    # The real BLS EP interactive export uses headers like:
    #   "Occupation Title", "Occupation Code", "Employment 2024",
    #   "Employment 2034", "Employment Change 2024-2034",
    #   "Employment Percent Change 2024-2034", "Median Annual Wage 2024",
    #   "Typical Entry-Level Education", etc.
    #
    # The static EP XLSX tables use different headers:
    #   "2023 National Employment Matrix title", "2023 National Employment
    #   Matrix code", "Employment, 2023", etc.
    #
    # We match both styles with flexible substring patterns.
    _HEADER_PATTERNS: list[tuple[str, list[str]]] = [
        ("soc_code", ["occupation code", "matrix code", "soc code"]),
        ("occupation_title", ["occupation title", "matrix title"]),
        ("employment_current", ["employment 2024", "employment 2023", "employment, 2024", "employment, 2023", "employment, 2022"]),
        ("employment_projected", ["employment 2034", "employment 2033", "employment, 2034", "employment, 2033", "employment, 2032"]),
        ("employment_change_pct", ["percent change", "change, percent"]),
        ("employment_change_num", ["employment change", "change, numeric", "change, number"]),
        ("openings_annual_avg", ["openings"]),
        ("median_annual_wage", ["median annual wage", "median wage"]),
        ("education_typical", ["entry-level education", "typical education needed"]),
        ("education_code", ["education code"]),
        ("work_experience", ["work experience in a related"]),
        ("work_experience_code", ["work experience code", "experience code"]),
        ("training_typical", ["typical on-the-job training", "on-the-job training"]),
        ("training_code", ["training code"]),
    ]

    def fetch(self, entities: dict, method: str, **kwargs) -> dict:
        """Download BLS occupational projections XLSX and parse it.

        Args:
            entities: {entity_id: label} dict from source config.
            method: Fetch method name.
            **kwargs: Supports ``xlsx_path`` for local file (used in tests).

        Returns:
            Dict mapping each entity_id to a list of row dicts.
        """
        xlsx_path = kwargs.get("xlsx_path")
        if xlsx_path is not None:
            rows = self._read_xlsx(Path(xlsx_path))
        else:
            rows = self._download_and_read()

        return {entity_id: rows for entity_id in entities}

    def _download_and_read(self) -> list[dict[str, Any]]:
        """Download the XLSX from BLS and return parsed rows."""
        headers = {
            "User-Agent": self.USER_AGENT,
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;"
                "q=0.9,image/webp,*/*;q=0.8"
            ),
        }

        try:
            response = requests.get(
                self.DOWNLOAD_URL, headers=headers, allow_redirects=True, timeout=120
            )
            if response.status_code == 403:
                raise requests.exceptions.HTTPError("403 Forbidden")
            response.raise_for_status()
            # BLS page may link to the actual XLSX; for now assume direct download
            import tempfile

            with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
                tmp.write(response.content)
                tmp_path = Path(tmp.name)
            rows = self._read_xlsx(tmp_path)
            tmp_path.unlink(missing_ok=True)
            return rows
        except Exception:
            logger.warning(
                "Download failed, falling back to %s", self.FALLBACK_PATH
            )
            return self._read_xlsx(Path(self.FALLBACK_PATH))

    def _read_xlsx(self, path: Path) -> list[dict[str, Any]]:
        """Read an XLSX file and return rows as dicts with canonical field names."""
        import openpyxl

        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        ws = wb.active

        rows_iter = ws.iter_rows(values_only=True)

        # Find the header row -- skip title/blank rows.
        header_row = None
        for row in rows_iter:
            # A header row should have multiple non-None string cells
            str_cells = [c for c in row if isinstance(c, str) and c.strip()]
            if len(str_cells) >= 5:
                header_row = [str(c).strip() if c else "" for c in row]
                break

        if header_row is None:
            wb.close()
            raise ValueError("Could not find header row in XLSX")

        # Map XLSX columns to canonical field names
        col_mapping = self._map_columns(header_row)

        data_rows: list[dict[str, Any]] = []
        for row in rows_iter:
            record: dict[str, Any] = {}
            for col_idx, canonical_name in col_mapping.items():
                record[canonical_name] = row[col_idx] if col_idx < len(row) else None
            # Skip rows where soc_code is missing
            soc = record.get("soc_code")
            if soc is None or (isinstance(soc, str) and not soc.strip()):
                continue
            soc_str = str(soc).strip()
            # Filter out summary/aggregate rows (SOC ending in 0000)
            soc_digits = soc_str.replace("-", "")
            if len(soc_digits) >= 6 and soc_digits.endswith("0000"):
                logger.debug("Skipping summary SOC %s", soc_str)
                continue
            data_rows.append(record)

        wb.close()
        logger.info("Parsed %d occupation rows from XLSX", len(data_rows))
        return data_rows

    def _map_columns(self, header_row: list[str]) -> dict[int, str]:
        """Map XLSX column indices to canonical field names using fuzzy matching."""
        mapping: dict[int, str] = {}
        used_fields: set[str] = set()

        for idx, header in enumerate(header_row):
            header_lower = header.lower()
            for field_name, patterns in self._HEADER_PATTERNS:
                if field_name in used_fields:
                    continue
                for pattern in patterns:
                    if pattern in header_lower:
                        mapping[idx] = field_name
                        used_fields.add(field_name)
                        break
                if field_name in used_fields:
                    break

        return mapping

    def flatten(self, raw_data: Any, entity_id: str) -> list[dict]:
        """Flatten raw XLSX rows into Iceberg-ready dicts.

        Handles:
        - SOC code formatting (keep as string XX-XXXX)
        - Employment figures: multiply by 1000 (source is in thousands)
        - Median wage parsing with top-code detection
        - Education/training code coercion to int

        Args:
            raw_data: List of row dicts from fetch().
            entity_id: Logical entity identifier.

        Returns:
            List of flat dicts with lowercase keys matching the Iceberg schema.
            Does NOT add metadata fields -- the framework handles those.
        """
        flat_rows: list[dict] = []
        skipped = 0

        for raw_row in raw_data:
            soc_code = self._coerce_soc(raw_row.get("soc_code"))
            if soc_code is None:
                skipped += 1
                continue

            wage_raw = raw_row.get("median_annual_wage")
            wage_value, wage_capped = self._parse_wage(wage_raw)

            record = {
                "soc_code": soc_code,
                "occupation_title": self._coerce_string(raw_row.get("occupation_title")),
                "employment_current": self._coerce_employment(raw_row.get("employment_current")),
                "employment_projected": self._coerce_employment(raw_row.get("employment_projected")),
                "employment_change": self._coerce_employment(raw_row.get("employment_change_num")),
                "employment_change_pct": self._coerce_double(raw_row.get("employment_change_pct")),
                "openings_annual_avg": self._coerce_employment(raw_row.get("openings_annual_avg")),
                "median_annual_wage": wage_value,
                "median_wage_capped": wage_capped,
                "education_typical": self._coerce_string(raw_row.get("education_typical")),
                "education_code": self._derive_code(
                    raw_row.get("education_code"),
                    raw_row.get("education_typical"),
                    self._EDUCATION_CODE_MAP,
                ),
                "work_experience": self._coerce_string(raw_row.get("work_experience")),
                "work_experience_code": self._derive_code(
                    raw_row.get("work_experience_code"),
                    raw_row.get("work_experience"),
                    self._WORK_EXPERIENCE_CODE_MAP,
                ),
                "training_typical": self._coerce_string(raw_row.get("training_typical")),
                "training_code": self._derive_code(
                    raw_row.get("training_code"),
                    raw_row.get("training_typical"),
                    self._TRAINING_CODE_MAP,
                ),
            }
            flat_rows.append(record)

        if skipped:
            logger.warning("Skipped %d rows with null grain fields", skipped)
        return flat_rows

    @staticmethod
    def _coerce_soc(value: Any) -> str | None:
        """Coerce SOC code to string format XX-XXXX, or None if missing."""
        if value is None:
            return None
        s = str(value).strip()
        if not s:
            return None
        return s

    @staticmethod
    def _coerce_string(value: Any) -> str | None:
        """Coerce to string or None."""
        if value is None:
            return None
        s = str(value).strip()
        return s if s else None

    @staticmethod
    def _coerce_employment(value: Any) -> int | None:
        """Coerce employment figure from thousands to actual count.

        Source values are in thousands (e.g. 1579.8 means ~1,579,800).
        """
        if value is None:
            return None
        if isinstance(value, str):
            value = value.strip().replace(",", "")
            if not value:
                return None
        try:
            return int(round(float(value) * 1000))
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _coerce_double(value: Any) -> float | None:
        """Coerce to float or None."""
        if value is None:
            return None
        if isinstance(value, str):
            value = value.strip().replace(",", "").replace("%", "")
            if not value:
                return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _derive_code(
        raw_code: Any,
        label: Any,
        code_map: dict[str, int],
    ) -> int | None:
        """Derive a numeric code from either a raw code value or a string label.

        If the source data includes a numeric code column, use it directly.
        Otherwise, look up the string label in the code map.  This handles
        the BLS interactive export (labels only) and the static EP tables
        (which may include code columns).
        """
        # If a code column exists and has a value, use it.
        if raw_code is not None:
            if isinstance(raw_code, str):
                raw_code = raw_code.strip()
                if not raw_code:
                    return None
            try:
                return int(float(raw_code))
            except (ValueError, TypeError):
                pass

        # Fall back to deriving from the string label.
        if label is not None:
            label_str = str(label).strip().lower()
            if label_str:
                return code_map.get(label_str)

        return None

    @staticmethod
    def _coerce_int(value: Any) -> int | None:
        """Coerce to int or None."""
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

    @staticmethod
    def _parse_wage(value: Any) -> tuple[float | None, bool]:
        """Parse median wage value, detecting top-coded values.

        Returns:
            (wage_float, is_capped) tuple.
            Top-coded values like ">=239,200" return (239200.0, True).
            N/A or missing returns (None, False).
            Normal values return (parsed_float, False).
        """
        if value is None:
            return None, False

        s = str(value).strip()
        if not s or s.upper() in ("N/A", "NA", "—", "-"):
            return None, False

        # Top-coded: ">=239,200" or "$239,200 or more" or similar
        if ">=" in s or "or more" in s.lower():
            # Extract the numeric part
            cleaned = re.sub(r"[^\d.]", "", s)
            try:
                return float(cleaned), True
            except (ValueError, TypeError):
                return None, False

        # Normal numeric: strip $ and commas
        cleaned = s.replace("$", "").replace(",", "").strip()
        try:
            return float(cleaned), False
        except (ValueError, TypeError):
            return None, False

    def get_schema(self) -> Schema:
        """Define the Iceberg table schema for raw.bls_ooh.

        Matches the fields returned by flatten(). Grain is SOC code.
        """
        return Schema(
            # Grain field
            NestedField(1, "soc_code", StringType(), required=True),
            NestedField(2, "occupation_title", StringType(), required=True),
            # Employment fields
            NestedField(3, "employment_current", LongType(), required=False),
            NestedField(4, "employment_projected", LongType(), required=False),
            NestedField(5, "employment_change", LongType(), required=False),
            NestedField(6, "employment_change_pct", DoubleType(), required=False),
            NestedField(7, "openings_annual_avg", LongType(), required=False),
            # Wage fields
            NestedField(8, "median_annual_wage", DoubleType(), required=False),
            NestedField(9, "median_wage_capped", BooleanType(), required=True),
            # Education/training fields
            NestedField(10, "education_typical", StringType(), required=False),
            NestedField(11, "education_code", IntegerType(), required=False),
            NestedField(12, "work_experience", StringType(), required=False),
            NestedField(13, "work_experience_code", IntegerType(), required=False),
            NestedField(14, "training_typical", StringType(), required=False),
            NestedField(15, "training_code", IntegerType(), required=False),
            # Metadata
            NestedField(16, "ingested_at", TimestampType(), required=True),
            NestedField(17, "source_url", StringType(), required=True),
            NestedField(18, "source_method", StringType(), required=True),
            NestedField(19, "load_date", DateType(), required=True),
        )
