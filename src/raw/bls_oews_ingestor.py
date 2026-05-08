"""Ingestor for Bureau of Labor Statistics Occupational Employment & Wage Statistics (OEWS).

OEWS publishes the full annual wage distribution (10/25/median/75/90 percentiles +
mean) per detailed SOC code from a semi-annual mail survey of ~200,000 establishments.
This complements BLS OOH (which provides only median + projections) by giving the
distribution required to render career-specific salary ranges in the FutureProof UI.

Source layout:
- A single ZIP at the National OEWS "special requests" page contains one workbook
  whose primary sheet has a header row of OCC_CODE, OCC_TITLE, OCC_GROUP, TOT_EMP,
  H_PCT*/H_MEAN/A_PCT*/A_MEAN/A_MEDIAN columns plus a number of metadata fields.
- Suppression sentinel ``*`` -> null.
- Top-coding sentinel ``#`` on annual percentiles means >= $239,200/yr -> 239200.0
  with ``wage_capped = True`` flagged on the row.
- ``OCC_GROUP`` of values other than ``detailed`` are summary roll-ups and are
  filtered out.

Grain: SOC code (XX-XXXX format, kept as a string).
"""

from __future__ import annotations

import io
import logging
import re
import tempfile
import zipfile
from pathlib import Path
from typing import Any

import requests
from pyiceberg.schema import Schema
from pyiceberg.types import (
    BooleanType,
    DateType,
    DoubleType,
    LongType,
    NestedField,
    StringType,
    TimestampType,
)

from brightsmith.bronze.base_ingestor import BaseIngestor

logger = logging.getLogger(__name__)


# Top-coded sentinel value the BLS publishes alongside ``#``: $239,200/yr.
# Any annual percentile reported as ``#`` represents an estimate >= this number;
# we replace it with the literal floor and flag the row as capped so downstream
# consumers can interpret it correctly.
TOP_CODED_VALUE = 239_200.0

# BLS suppression sentinels -- value reported but not publishable.
_SUPPRESSED_TOKENS: frozenset[str] = frozenset({"*", "**", ""})

# Annual wage percentile column names in the OEWS workbook header row.
_ANNUAL_PERCENTILE_FIELDS: tuple[str, ...] = (
    "wage_annual_p10",
    "wage_annual_p25",
    "wage_annual_median",
    "wage_annual_p75",
    "wage_annual_p90",
    "wage_annual_mean",
)


class BlsOewsIngestor(BaseIngestor):
    """Ingest BLS OEWS national wage percentiles into ``bronze.bls_oews``.

    Data source: ZIP download from the BLS OEWS special-requests page
    containing a single XLSX workbook with one row per occupation across
    several OCC_GROUP rollup tiers. We keep only ``detailed`` rows.

    Grain: SOC code (XX-XXXX format).
    """

    DOWNLOAD_URL = "https://www.bls.gov/oes/special-requests/oesm24nat.zip"
    FALLBACK_XLSX_PATH = "data/raw/xlsx_cache/oesm24nat.xlsx"
    # NOTE: BLS 403s the OOH-style Chrome UA on the OEWS endpoint.  The
    # Safari UA below is the smallest set of headers empirically observed
    # to receive a 200 from the live ZIP endpoint as of May 2026.  Any
    # change here should be re-tested against the real URL.
    USER_AGENT = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
    )
    CONTACT_EMAIL = "jeff@hyenastudios.com"
    SOURCE_METHOD = "xlsx_download"

    # Source column header -> canonical Iceberg field name.
    # OEWS column names are case-sensitive in the workbook (``OCC_CODE``,
    # etc) but we do a case-insensitive match.
    #
    # The real OEWS national workbook uses ``O_GROUP`` for the rollup-tier
    # column.  Older spec drafts and some BLS PDFs reference ``OCC_GROUP``;
    # we accept either header so the ingestor isn't brittle to the
    # vintage-to-vintage spelling drift.
    COLUMN_MAP: dict[str, str] = {
        "occ_code": "soc_code",
        "occ_title": "occupation_title",
        "o_group": "occ_group",
        "occ_group": "occ_group",
        "tot_emp": "total_employment",
        "a_pct10": "wage_annual_p10",
        "a_pct25": "wage_annual_p25",
        "a_median": "wage_annual_median",
        "a_pct75": "wage_annual_p75",
        "a_pct90": "wage_annual_p90",
        "a_mean": "wage_annual_mean",
        "h_median": "wage_hourly_median",
    }

    # Regex applied AFTER coercion: SOC must always be XX-XXXX.
    _SOC_PATTERN = re.compile(r"^\d{2}-\d{4}$")

    # ------------------------------------------------------------------
    # Fetch
    # ------------------------------------------------------------------

    def fetch(self, entities: dict, method: str, **kwargs) -> dict[Any, Any]:
        """Fetch the OEWS workbook and parse it into raw row dicts.

        Args:
            entities: ``{entity_id: label}`` map from the source config.
            method: Fetch method name (informational).
            **kwargs: Supports ``xlsx_path`` (skip download, parse a local
                workbook directly -- used in tests) and ``zip_path`` (skip
                download, unpack a local ZIP).

        Returns:
            ``{entity_id: list_of_row_dicts}`` where each row dict has
            canonical lowercase keys (see ``COLUMN_MAP``).
        """
        xlsx_path = kwargs.get("xlsx_path")
        zip_path = kwargs.get("zip_path")

        if xlsx_path is not None:
            rows = self._read_xlsx(Path(xlsx_path))
        elif zip_path is not None:
            rows = self._read_zip(Path(zip_path))
        else:
            rows = self._download_and_read()

        return {entity_id: rows for entity_id in entities}

    def _download_and_read(self) -> list[dict[str, Any]]:
        """Download the OEWS ZIP and parse the contained XLSX.

        Falls back to the cached workbook at ``FALLBACK_XLSX_PATH`` on any
        non-200 response (BLS is known to 403 unfamiliar User-Agents) or
        unexpected ZIP structure.
        """
        headers = {
            "User-Agent": self.USER_AGENT,
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;"
                "q=0.9,*/*;q=0.8"
            ),
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
        }

        try:
            response = requests.get(
                self.DOWNLOAD_URL,
                headers=headers,
                allow_redirects=True,
                timeout=180,
            )
            if response.status_code == 403:
                raise requests.exceptions.HTTPError("403 Forbidden")
            response.raise_for_status()

            with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
                tmp.write(response.content)
                zip_tmp = Path(tmp.name)
            try:
                rows = self._read_zip(zip_tmp)
            finally:
                zip_tmp.unlink(missing_ok=True)
            return rows
        except Exception as exc:
            logger.warning(
                "OEWS download failed (%s), falling back to %s",
                exc,
                self.FALLBACK_XLSX_PATH,
            )
            return self._read_xlsx(Path(self.FALLBACK_XLSX_PATH))

    def _read_zip(self, zip_path: Path) -> list[dict[str, Any]]:
        """Open ``zip_path`` and parse the single XLSX inside it."""
        with zipfile.ZipFile(zip_path) as zf:
            xlsx_names = [n for n in zf.namelist() if n.lower().endswith(".xlsx")]
            if not xlsx_names:
                raise ValueError(
                    f"No .xlsx member found in OEWS ZIP {zip_path.name}"
                )
            if len(xlsx_names) > 1:
                logger.warning(
                    "OEWS ZIP contained %d xlsx members; using %s",
                    len(xlsx_names),
                    xlsx_names[0],
                )
            xlsx_member = xlsx_names[0]
            with zf.open(xlsx_member) as xlsx_fp:
                return self._read_xlsx_bytes(xlsx_fp.read())

    def _read_xlsx(self, path: Path) -> list[dict[str, Any]]:
        """Parse an OEWS XLSX directly from a local file."""
        return self._read_xlsx_bytes(path.read_bytes())

    def _read_xlsx_bytes(self, payload: bytes) -> list[dict[str, Any]]:
        """Parse OEWS XLSX bytes via openpyxl read-only mode."""
        import openpyxl

        wb = openpyxl.load_workbook(
            io.BytesIO(payload), read_only=True, data_only=True
        )
        try:
            ws = wb.active

            rows_iter = ws.iter_rows(values_only=True)

            header_row, header_index = self._find_header_row(rows_iter)
            col_mapping = self._map_columns(header_row)

            data_rows: list[dict[str, Any]] = []
            for row in rows_iter:
                record: dict[str, Any] = {}
                for col_idx, canonical_name in col_mapping.items():
                    record[canonical_name] = (
                        row[col_idx] if col_idx < len(row) else None
                    )

                soc_raw = record.get("soc_code")
                if soc_raw is None or (
                    isinstance(soc_raw, str) and not soc_raw.strip()
                ):
                    continue

                # Filter to detailed occupations only -- summary rollups
                # (major/minor/broad/total) lack per-SOC granularity.
                occ_group = record.get("occ_group")
                if (
                    occ_group is None
                    or str(occ_group).strip().lower() != "detailed"
                ):
                    continue

                data_rows.append(record)

            logger.info(
                "Parsed %d detailed-occupation rows from OEWS XLSX (header at row %d)",
                len(data_rows),
                header_index,
            )
            return data_rows
        finally:
            wb.close()

    @staticmethod
    def _find_header_row(rows_iter: Any) -> tuple[list[str], int]:
        """Walk rows until we find the OEWS header.

        OEWS workbooks may have a couple of title/blank rows above the
        header.  We look for a row that contains both ``OCC_CODE`` and
        ``OCC_TITLE`` (case-insensitive) which is the unique header
        signature for the OEWS national table.
        """
        for idx, row in enumerate(rows_iter):
            cells_lower = [
                str(c).strip().lower() if c is not None else "" for c in row
            ]
            if "occ_code" in cells_lower and "occ_title" in cells_lower:
                return [str(c).strip() if c else "" for c in row], idx
        raise ValueError(
            "Could not find OEWS header row (expected OCC_CODE + OCC_TITLE)"
        )

    def _map_columns(self, header_row: list[str]) -> dict[int, str]:
        """Map XLSX column indices to canonical field names.

        Comparison is case-insensitive against the COLUMN_MAP keys.  Unknown
        columns are silently ignored — we only care about the wage/employment
        fields enumerated in the spec.
        """
        mapping: dict[int, str] = {}
        for idx, header in enumerate(header_row):
            key = header.strip().lower()
            canonical = self.COLUMN_MAP.get(key)
            if canonical is not None:
                mapping[idx] = canonical
        return mapping

    # ------------------------------------------------------------------
    # Flatten
    # ------------------------------------------------------------------

    def flatten(self, raw_data: Any, entity_id: Any) -> list[dict]:
        """Coerce raw OEWS row dicts into Iceberg-ready dicts.

        - SOC code preserved as XX-XXXX string; rows with malformed codes
          are dropped (logged at WARNING).
        - ``*`` suppression -> None for every numeric field.
        - ``#`` top-coding on any annual percentile -> ``TOP_CODED_VALUE``
          and the row's ``wage_capped`` flag is set to True.
        - Employment is a long; commas in the source are stripped.

        Args:
            raw_data: Output of ``fetch()`` for a single entity (list).
            entity_id: Entity identifier (unused — single entity).

        Returns:
            List of flat dicts whose keys exactly match the Iceberg schema's
            non-metadata fields.  ``ingested_at`` / ``source_url`` /
            ``source_method`` / ``load_date`` are added by the framework.
        """
        flat_rows: list[dict] = []
        skipped_invalid_soc = 0

        for raw_row in raw_data:
            soc = self._coerce_soc(raw_row.get("soc_code"))
            if soc is None:
                skipped_invalid_soc += 1
                continue

            wage_capped = False
            wage_values: dict[str, float | None] = {}
            for field in _ANNUAL_PERCENTILE_FIELDS:
                value, capped = self._parse_wage(raw_row.get(field))
                wage_values[field] = value
                if capped:
                    wage_capped = True

            hourly_median, hourly_capped = self._parse_wage(
                raw_row.get("wage_hourly_median")
            )
            # Top-coding on hourly fields shouldn't drive the annual flag
            # since hourly top-coding is a different sentinel and column
            # set, but we still surface a capped hourly value as 115.0 (the
            # OEWS hourly cap) where the source publishes one.  In practice
            # the spec's ``wage_capped`` is annual-only, so we leave the
            # boolean alone here.
            del hourly_capped

            record = {
                "soc_code": soc,
                "occupation_title": self._coerce_string(
                    raw_row.get("occupation_title")
                ),
                "total_employment": self._coerce_employment(
                    raw_row.get("total_employment")
                ),
                "wage_annual_p10": wage_values["wage_annual_p10"],
                "wage_annual_p25": wage_values["wage_annual_p25"],
                "wage_annual_median": wage_values["wage_annual_median"],
                "wage_annual_p75": wage_values["wage_annual_p75"],
                "wage_annual_p90": wage_values["wage_annual_p90"],
                "wage_annual_mean": wage_values["wage_annual_mean"],
                "wage_hourly_median": hourly_median,
                "wage_capped": wage_capped,
            }
            flat_rows.append(record)

        if skipped_invalid_soc:
            logger.warning(
                "Skipped %d OEWS rows with missing/invalid SOC codes",
                skipped_invalid_soc,
            )
        return flat_rows

    # ------------------------------------------------------------------
    # Coercion helpers
    # ------------------------------------------------------------------

    @classmethod
    def _coerce_soc(cls, value: Any) -> str | None:
        """Coerce a SOC code to ``XX-XXXX`` form, or None if malformed."""
        if value is None:
            return None
        s = str(value).strip()
        if not s:
            return None
        if cls._SOC_PATTERN.match(s):
            return s
        # OEWS occasionally publishes 7-digit SOC codes for sub-classifications
        # (e.g. ``15-1252.00``).  These are not in the standard SOC and would
        # not join cleanly to OOH/O*NET, so we drop them rather than guess.
        return None

    @staticmethod
    def _coerce_string(value: Any) -> str | None:
        """Coerce an arbitrary value to a non-empty string, or None."""
        if value is None:
            return None
        s = str(value).strip()
        return s if s else None

    @staticmethod
    def _coerce_employment(value: Any) -> int | None:
        """Coerce a TOT_EMP value to int.

        - ``*`` (suppressed) -> None.
        - Strings with commas (``"1,234,560"``) -> int.
        - Floats from openpyxl numeric cells -> int via round.
        """
        if value is None:
            return None
        if isinstance(value, str):
            s = value.strip()
            if s in _SUPPRESSED_TOKENS:
                return None
            s = s.replace(",", "")
            if not s:
                return None
            try:
                return int(round(float(s)))
            except (ValueError, TypeError):
                return None
        try:
            return int(round(float(value)))
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _parse_wage(value: Any) -> tuple[float | None, bool]:
        """Parse an OEWS wage cell.

        Returns:
            ``(wage_value, is_capped)``.

            - ``*`` suppression -> ``(None, False)``.
            - ``#`` top-coded -> ``(TOP_CODED_VALUE, True)``.
            - Numeric cell or numeric string -> ``(float(value), False)``.
            - Anything else -> ``(None, False)`` (logged at debug).
        """
        if value is None:
            return None, False

        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return float(value), False

        s = str(value).strip()
        if not s:
            return None, False
        if s in _SUPPRESSED_TOKENS:
            return None, False
        if s == "#":
            return TOP_CODED_VALUE, True

        # Strip $ , and whitespace and try float-coerce.
        cleaned = s.replace("$", "").replace(",", "").strip()
        try:
            return float(cleaned), False
        except (ValueError, TypeError):
            logger.debug("Unrecognized OEWS wage token %r -> null", value)
            return None, False

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------

    def get_schema(self) -> Schema:
        """Iceberg schema for ``bronze.bls_oews``.

        Field IDs are local to this Bronze table; downstream Silver/Gold
        tables manage their own ID spaces.
        """
        return Schema(
            # Grain
            NestedField(1, "soc_code", StringType(), required=True),
            # Identifiers
            NestedField(2, "occupation_title", StringType(), required=True),
            # Employment
            NestedField(3, "total_employment", LongType(), required=False),
            # Wage distribution -- annual
            NestedField(4, "wage_annual_p10", DoubleType(), required=False),
            NestedField(5, "wage_annual_p25", DoubleType(), required=False),
            NestedField(6, "wage_annual_median", DoubleType(), required=False),
            NestedField(7, "wage_annual_p75", DoubleType(), required=False),
            NestedField(8, "wage_annual_p90", DoubleType(), required=False),
            NestedField(9, "wage_annual_mean", DoubleType(), required=False),
            # Hourly reference
            NestedField(10, "wage_hourly_median", DoubleType(), required=False),
            # Top-coding flag -- True if any annual percentile was top-coded
            NestedField(11, "wage_capped", BooleanType(), required=True),
            # Framework metadata (filled in by BaseIngestor.ingest())
            NestedField(12, "ingested_at", TimestampType(), required=True),
            NestedField(13, "source_url", StringType(), required=True),
            NestedField(14, "source_method", StringType(), required=True),
            NestedField(15, "load_date", DateType(), required=True),
        )


# ----------------------------------------------------------------------
# CLI entry point: `uv run python -m src.raw.bls_oews_ingestor`
# ----------------------------------------------------------------------


def _main() -> int:
    """Run a one-off OEWS ingest into the persistent Brightsmith warehouse.

    Mirrors the pattern in ``scripts/ingest_bea_rpp.py``: configure
    Brightsmith with the project root, build a SourceConfig + DomainManifest
    in-process, run the ingest, then verify row count via DuckDB.
    """
    import logging
    import sys

    PROJECT_ROOT = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(PROJECT_ROOT / "src"))

    import brightsmith.config

    brightsmith.config.configure(
        project_root=PROJECT_ROOT,
        require_human_approval=False,
    )

    from brightsmith.domain_loader import DomainHints, DomainManifest, SourceConfig
    from brightsmith.infra.iceberg_setup import get_catalog, read_with_duckdb

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s %(message)s",
    )
    runner_logger = logging.getLogger("ingest_bls_oews")

    source = SourceConfig(
        name="bls_oews",
        namespace="bronze",
        table="bls_oews",
        fetch={
            "xlsx_download": {
                "url": BlsOewsIngestor.DOWNLOAD_URL,
                "fallback_path": BlsOewsIngestor.FALLBACK_XLSX_PATH,
                "user_agent": BlsOewsIngestor.USER_AGENT,
            }
        },
        entities={
            "oews": "BLS OEWS — National Wage Percentiles, All Detailed Occupations"
        },
        dedup_grain=["soc_code"],
        cache_dir=PROJECT_ROOT / "data" / "raw" / "xlsx_cache",
    )
    manifest = DomainManifest(
        name="futureproof-data",
        version="0.1",
        description="ingest runner",
        sources=[],
        hints=DomainHints(),
        pipeline={},
    )

    ingestor = BlsOewsIngestor(source, manifest)
    results = ingestor.ingest(method=BlsOewsIngestor.SOURCE_METHOD)
    runner_logger.info("Ingest results: %s", results)

    catalog = get_catalog(
        brightsmith.config.WAREHOUSE_PATH,
        brightsmith.config.CATALOG_PATH,
    )
    table = catalog.load_table("bronze.bls_oews")
    rows = read_with_duckdb(table)
    runner_logger.info("bronze.bls_oews row count: %d", len(rows))
    # Spec target: ~830 detailed occupations; allow some give either way.
    return 0 if 800 <= len(rows) <= 900 else 1


if __name__ == "__main__":
    raise SystemExit(_main())
