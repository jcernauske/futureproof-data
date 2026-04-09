"""Ingestors for O*NET database tables.

Downloads a ZIP archive containing tab-delimited text files and loads
each into a separate Iceberg table in the raw namespace.

Architecture: OnetBaseIngestor handles ZIP download/cache and shared
coercion utilities. Seven thin subclasses each target one file/table.
"""

import csv
import io
import logging
import zipfile
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


class OnetBaseIngestor(BaseIngestor):
    """Shared base for all O*NET table ingestors.

    Handles ZIP download, extraction, caching, and common coercion
    utilities. Subclasses define SOURCE_FILENAME, get_schema(), and
    optionally override flatten() for table-specific coercion.
    """

    DOWNLOAD_URL = "https://www.onetcenter.org/dl_files/database/db_30_2_text.zip"
    CACHE_DIR = "data/raw/onet_cache"
    USER_AGENT = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    # Subclasses MUST set this to the filename inside the ZIP (e.g., "Occupation Data.txt")
    SOURCE_FILENAME: str = ""

    def fetch(self, entities: dict, method: str, **kwargs) -> dict:
        """Download O*NET ZIP, extract the target file, and parse it.

        Args:
            entities: {entity_id: label} dict from source config.
            method: Fetch method name.
            **kwargs: Supports ``cache_dir`` for local file directory (used in tests).

        Returns:
            Dict mapping each entity_id to a list of row dicts.
        """
        cache_dir = kwargs.get("cache_dir")
        if cache_dir is not None:
            rows = self._read_from_cache(Path(cache_dir))
        else:
            rows = self._download_and_read()

        return {entity_id: rows for entity_id in entities}

    def _download_and_read(self) -> list[dict[str, str]]:
        """Download the ZIP from O*NET, extract, and return parsed rows."""
        headers = {
            "User-Agent": self.USER_AGENT,
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;"
                "q=0.9,image/webp,*/*;q=0.8"
            ),
        }

        try:
            response = requests.get(
                self.DOWNLOAD_URL, headers=headers, allow_redirects=True, timeout=300
            )
            response.raise_for_status()
            return self._extract_and_parse(response.content)
        except Exception:
            logger.warning(
                "Download failed, falling back to cache at %s", self.CACHE_DIR
            )
            return self._read_from_cache(Path(self.CACHE_DIR))

    def _extract_and_parse(self, zip_content: bytes) -> list[dict[str, str]]:
        """Extract the target file from the ZIP and parse tab-delimited rows."""
        with zipfile.ZipFile(io.BytesIO(zip_content)) as zf:
            # Find the target file (may be in a subdirectory)
            target = None
            for name in zf.namelist():
                if name.endswith(self.SOURCE_FILENAME):
                    target = name
                    break
            if target is None:
                raise ValueError(
                    f"File '{self.SOURCE_FILENAME}' not found in ZIP. "
                    f"Available: {zf.namelist()}"
                )
            content = zf.read(target)

        return self._parse_tsv(content)

    def _read_from_cache(self, cache_dir: Path) -> list[dict[str, str]]:
        """Read the target file from the local cache directory."""
        # Try exact filename first, then search subdirectories
        path = cache_dir / self.SOURCE_FILENAME
        if not path.exists():
            # Search for the file in subdirectories
            matches = list(cache_dir.rglob(self.SOURCE_FILENAME))
            if not matches:
                raise FileNotFoundError(
                    f"'{self.SOURCE_FILENAME}' not found in {cache_dir}"
                )
            path = matches[0]

        content = path.read_bytes()
        return self._parse_tsv(content)

    def _parse_tsv(self, content: bytes) -> list[dict[str, str]]:
        """Parse tab-delimited content into a list of row dicts."""
        # Remove BOM if present
        if content.startswith(b"\xef\xbb\xbf"):
            content = content[3:]

        text = content.decode("utf-8")
        reader = csv.DictReader(io.StringIO(text), delimiter="\t")
        rows = list(reader)
        logger.info(
            "Parsed %d rows from %s", len(rows), self.SOURCE_FILENAME
        )
        return rows

    # --- Shared coercion utilities ---

    @staticmethod
    def _coerce_string(value: Any) -> str | None:
        """Coerce to stripped string or None."""
        if value is None:
            return None
        s = str(value).strip()
        return s if s else None

    @staticmethod
    def _coerce_onet_soc(value: Any) -> str | None:
        """Coerce O*NET-SOC code to string, preserving XX-XXXX.XX format."""
        if value is None:
            return None
        s = str(value).strip()
        return s if s else None

    @staticmethod
    def _coerce_double(value: Any) -> float | None:
        """Coerce to float or None."""
        if value is None:
            return None
        if isinstance(value, str):
            value = value.strip()
            if not value or value.lower() == "n/a":
                return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _coerce_int(value: Any) -> int | None:
        """Coerce to int or None."""
        if value is None:
            return None
        if isinstance(value, str):
            value = value.strip()
            if not value or value.lower() == "n/a":
                return None
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _coerce_long(value: Any) -> int | None:
        """Coerce to long (Python int) or None."""
        if value is None:
            return None
        if isinstance(value, str):
            value = value.strip()
            if not value or value.lower() == "n/a":
                return None
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return None


class OnetOccupationsIngestor(OnetBaseIngestor):
    """Ingestor for O*NET Occupation Data (raw.onet_occupations)."""

    SOURCE_FILENAME = "Occupation Data.txt"

    def flatten(self, raw_data: Any, entity_id: str) -> list[dict]:
        """Flatten Occupation Data rows into Iceberg-ready dicts."""
        flat_rows: list[dict] = []
        skipped = 0

        for raw_row in raw_data:
            onet_soc = self._coerce_onet_soc(raw_row.get("O*NET-SOC Code"))
            if onet_soc is None:
                skipped += 1
                continue

            record = {
                "onet_soc_code": onet_soc,
                "title": self._coerce_string(raw_row.get("Title")),
                "description": self._coerce_string(raw_row.get("Description")),
            }

            if record["title"] is None or record["description"] is None:
                skipped += 1
                continue

            flat_rows.append(record)

        if skipped:
            logger.warning("Skipped %d rows with null grain/required fields", skipped)
        return flat_rows

    def get_schema(self) -> Schema:
        """Iceberg schema for raw.onet_occupations."""
        return Schema(
            NestedField(1, "onet_soc_code", StringType(), required=True),
            NestedField(2, "title", StringType(), required=True),
            NestedField(3, "description", StringType(), required=True),
            # Metadata
            NestedField(4, "ingested_at", TimestampType(), required=True),
            NestedField(5, "source_url", StringType(), required=True),
            NestedField(6, "source_method", StringType(), required=True),
            NestedField(7, "load_date", DateType(), required=True),
        )


class OnetTaskStatementsIngestor(OnetBaseIngestor):
    """Ingestor for O*NET Task Statements (raw.onet_task_statements)."""

    SOURCE_FILENAME = "Task Statements.txt"

    def flatten(self, raw_data: Any, entity_id: str) -> list[dict]:
        """Flatten Task Statements rows into Iceberg-ready dicts."""
        flat_rows: list[dict] = []
        skipped = 0

        for raw_row in raw_data:
            onet_soc = self._coerce_onet_soc(raw_row.get("O*NET-SOC Code"))
            task_id = self._coerce_long(raw_row.get("Task ID"))
            task = self._coerce_string(raw_row.get("Task"))

            if onet_soc is None or task_id is None or task is None:
                skipped += 1
                continue

            record = {
                "onet_soc_code": onet_soc,
                "task_id": task_id,
                "task": task,
                "task_type": self._coerce_string(raw_row.get("Task Type")),
                "incumbents_responding": self._coerce_int(
                    raw_row.get("Incumbents Responding")
                ),
                "date": self._coerce_string(raw_row.get("Date")),
                "domain_source": self._coerce_string(raw_row.get("Domain Source")),
            }
            flat_rows.append(record)

        if skipped:
            logger.warning("Skipped %d rows with null grain/required fields", skipped)
        return flat_rows

    def get_schema(self) -> Schema:
        """Iceberg schema for raw.onet_task_statements."""
        return Schema(
            NestedField(1, "onet_soc_code", StringType(), required=True),
            NestedField(2, "task_id", LongType(), required=True),
            NestedField(3, "task", StringType(), required=True),
            NestedField(4, "task_type", StringType(), required=False),
            NestedField(5, "incumbents_responding", IntegerType(), required=False),
            NestedField(6, "date", StringType(), required=False),
            NestedField(7, "domain_source", StringType(), required=False),
            # Metadata
            NestedField(8, "ingested_at", TimestampType(), required=True),
            NestedField(9, "source_url", StringType(), required=True),
            NestedField(10, "source_method", StringType(), required=True),
            NestedField(11, "load_date", DateType(), required=True),
        )


class OnetWorkActivitiesIngestor(OnetBaseIngestor):
    """Ingestor for O*NET Work Activities (raw.onet_work_activities)."""

    SOURCE_FILENAME = "Work Activities.txt"

    def flatten(self, raw_data: Any, entity_id: str) -> list[dict]:
        """Flatten Work Activities rows into Iceberg-ready dicts."""
        flat_rows: list[dict] = []
        skipped = 0

        for raw_row in raw_data:
            onet_soc = self._coerce_onet_soc(raw_row.get("O*NET-SOC Code"))
            element_id = self._coerce_string(raw_row.get("Element ID"))
            element_name = self._coerce_string(raw_row.get("Element Name"))
            scale_id = self._coerce_string(raw_row.get("Scale ID"))
            data_value = self._coerce_double(raw_row.get("Data Value"))

            if any(v is None for v in (onet_soc, element_id, element_name, scale_id, data_value)):
                skipped += 1
                continue

            record = {
                "onet_soc_code": onet_soc,
                "element_id": element_id,
                "element_name": element_name,
                "scale_id": scale_id,
                "data_value": data_value,
                "n": self._coerce_int(raw_row.get("N")),
                "standard_error": self._coerce_double(raw_row.get("Standard Error")),
                "lower_ci_bound": self._coerce_double(raw_row.get("Lower CI Bound")),
                "upper_ci_bound": self._coerce_double(raw_row.get("Upper CI Bound")),
                "recommend_suppress": self._coerce_string(raw_row.get("Recommend Suppress")),
                "not_relevant": self._coerce_string(raw_row.get("Not Relevant")),
                "date": self._coerce_string(raw_row.get("Date")),
                "domain_source": self._coerce_string(raw_row.get("Domain Source")),
            }
            flat_rows.append(record)

        if skipped:
            logger.warning("Skipped %d rows with null grain/required fields", skipped)
        return flat_rows

    def get_schema(self) -> Schema:
        """Iceberg schema for raw.onet_work_activities."""
        return Schema(
            NestedField(1, "onet_soc_code", StringType(), required=True),
            NestedField(2, "element_id", StringType(), required=True),
            NestedField(3, "element_name", StringType(), required=True),
            NestedField(4, "scale_id", StringType(), required=True),
            NestedField(5, "data_value", DoubleType(), required=True),
            NestedField(6, "n", IntegerType(), required=False),
            NestedField(7, "standard_error", DoubleType(), required=False),
            NestedField(8, "lower_ci_bound", DoubleType(), required=False),
            NestedField(9, "upper_ci_bound", DoubleType(), required=False),
            NestedField(10, "recommend_suppress", StringType(), required=False),
            NestedField(11, "not_relevant", StringType(), required=False),
            NestedField(12, "date", StringType(), required=False),
            NestedField(13, "domain_source", StringType(), required=False),
            # Metadata
            NestedField(14, "ingested_at", TimestampType(), required=True),
            NestedField(15, "source_url", StringType(), required=True),
            NestedField(16, "source_method", StringType(), required=True),
            NestedField(17, "load_date", DateType(), required=True),
        )


class OnetWorkContextIngestor(OnetBaseIngestor):
    """Ingestor for O*NET Work Context (raw.onet_work_context).

    Same structure as Work Activities plus a category column for
    categorical context items.
    """

    SOURCE_FILENAME = "Work Context.txt"

    def flatten(self, raw_data: Any, entity_id: str) -> list[dict]:
        """Flatten Work Context rows into Iceberg-ready dicts."""
        flat_rows: list[dict] = []
        skipped = 0

        for raw_row in raw_data:
            onet_soc = self._coerce_onet_soc(raw_row.get("O*NET-SOC Code"))
            element_id = self._coerce_string(raw_row.get("Element ID"))
            element_name = self._coerce_string(raw_row.get("Element Name"))
            scale_id = self._coerce_string(raw_row.get("Scale ID"))
            data_value = self._coerce_double(raw_row.get("Data Value"))

            if any(v is None for v in (onet_soc, element_id, element_name, scale_id, data_value)):
                skipped += 1
                continue

            record = {
                "onet_soc_code": onet_soc,
                "element_id": element_id,
                "element_name": element_name,
                "scale_id": scale_id,
                "data_value": data_value,
                "n": self._coerce_int(raw_row.get("N")),
                "standard_error": self._coerce_double(raw_row.get("Standard Error")),
                "lower_ci_bound": self._coerce_double(raw_row.get("Lower CI Bound")),
                "upper_ci_bound": self._coerce_double(raw_row.get("Upper CI Bound")),
                "recommend_suppress": self._coerce_string(raw_row.get("Recommend Suppress")),
                "not_relevant": self._coerce_string(raw_row.get("Not Relevant")),
                "date": self._coerce_string(raw_row.get("Date")),
                "domain_source": self._coerce_string(raw_row.get("Domain Source")),
                "category": self._coerce_int(raw_row.get("Category")),
            }
            flat_rows.append(record)

        if skipped:
            logger.warning("Skipped %d rows with null grain/required fields", skipped)
        return flat_rows

    def get_schema(self) -> Schema:
        """Iceberg schema for raw.onet_work_context."""
        return Schema(
            NestedField(1, "onet_soc_code", StringType(), required=True),
            NestedField(2, "element_id", StringType(), required=True),
            NestedField(3, "element_name", StringType(), required=True),
            NestedField(4, "scale_id", StringType(), required=True),
            NestedField(5, "data_value", DoubleType(), required=True),
            NestedField(6, "n", IntegerType(), required=False),
            NestedField(7, "standard_error", DoubleType(), required=False),
            NestedField(8, "lower_ci_bound", DoubleType(), required=False),
            NestedField(9, "upper_ci_bound", DoubleType(), required=False),
            NestedField(10, "recommend_suppress", StringType(), required=False),
            NestedField(11, "not_relevant", StringType(), required=False),
            NestedField(12, "date", StringType(), required=False),
            NestedField(13, "domain_source", StringType(), required=False),
            NestedField(14, "category", IntegerType(), required=False),
            # Metadata
            NestedField(15, "ingested_at", TimestampType(), required=True),
            NestedField(16, "source_url", StringType(), required=True),
            NestedField(17, "source_method", StringType(), required=True),
            NestedField(18, "load_date", DateType(), required=True),
        )


class OnetRelatedOccupationsIngestor(OnetBaseIngestor):
    """Ingestor for O*NET Related Occupations (raw.onet_related_occupations).

    Derives is_primary from the index: 1-10 = primary, 11-20 = supplemental.
    """

    SOURCE_FILENAME = "Related Occupations.txt"

    def flatten(self, raw_data: Any, entity_id: str) -> list[dict]:
        """Flatten Related Occupations rows into Iceberg-ready dicts.

        Derives is_primary from the Relatedness Tier column when available
        (O*NET 30.2+), falling back to index range (1-10 = primary).
        """
        flat_rows: list[dict] = []
        skipped = 0

        for raw_row in raw_data:
            onet_soc = self._coerce_onet_soc(raw_row.get("O*NET-SOC Code"))
            related_soc = self._coerce_onet_soc(raw_row.get("Related O*NET-SOC Code"))
            related_index = self._coerce_int(raw_row.get("Index"))

            if onet_soc is None or related_soc is None or related_index is None:
                skipped += 1
                continue

            # Derive is_primary from Relatedness Tier if available, else from index
            tier = self._coerce_string(raw_row.get("Relatedness Tier"))
            if tier is not None:
                is_primary = tier.startswith("Primary")
            else:
                is_primary = related_index <= 10

            record = {
                "onet_soc_code": onet_soc,
                "related_onet_soc_code": related_soc,
                "related_index": related_index,
                "is_primary": is_primary,
                "relatedness_tier": tier,
            }
            flat_rows.append(record)

        if skipped:
            logger.warning("Skipped %d rows with null grain/required fields", skipped)
        return flat_rows

    def get_schema(self) -> Schema:
        """Iceberg schema for raw.onet_related_occupations."""
        return Schema(
            NestedField(1, "onet_soc_code", StringType(), required=True),
            NestedField(2, "related_onet_soc_code", StringType(), required=True),
            NestedField(3, "related_index", IntegerType(), required=True),
            NestedField(4, "is_primary", BooleanType(), required=True),
            NestedField(5, "relatedness_tier", StringType(), required=False),
            # Metadata
            NestedField(6, "ingested_at", TimestampType(), required=True),
            NestedField(7, "source_url", StringType(), required=True),
            NestedField(8, "source_method", StringType(), required=True),
            NestedField(9, "load_date", DateType(), required=True),
        )
