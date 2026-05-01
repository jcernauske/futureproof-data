"""Ingestor for EADA (Equity in Athletics Disclosure Act) Athletics Survey.

Lands the EADA Athletics Disclosure Survey institution-totals file into
Iceberg table ``raw.eada`` (~2,040 rows, one row per institution per
academic reporting year).

Source: U.S. Department of Education, Office of Postsecondary Education
Custom Data Cutting Tool at ``https://ope.ed.gov/athletics/``.  The
human-facing landing page hides the bulk endpoints, but the SPA backend
exposes an unauthenticated JSON+zip API discovered during EDA
(2026-04-30, see ``governance/eda/full-pipeline-eada-raw-eda.md``):

    GET https://ope.ed.gov/athletics/api/dataFiles/years
    GET https://ope.ed.gov/athletics/api/dataFiles/fileList
    GET https://ope.ed.gov/athletics/api/dataFiles/file?fileName=<FileName>

Each annual zip (e.g. ``EADA_2022-2023.zip``) contains two relevant
spreadsheets:
  - ``InstLevel.xlsx`` — institution-totals, one row per UNITID
    (~2,040 rows × 168 cols).  This is what we ingest.
  - ``Schools.xlsx`` — per-team rows keyed (UNITID, SPORTSCODE).
    NOT ingested by this pipeline.

Because ``InstLevel.xlsx`` is already one-row-per-UNITID by
construction, **no in-pipeline filter is required**.  The class-level
``INSTITUTION_TOTAL_FILTER_COLUMN`` is therefore ``None``, and
``_is_institution_total()`` short-circuits to ``True``.  The
configurable filter is retained as a fallback for hypothetical future
mixed-file ingestion.

Spec: ``docs/specs/full-pipeline-eada.md`` §3 + §4.
EDA report: ``governance/eda/full-pipeline-eada-raw-eda.md``.

Cache + fallback path:
    The orchestrator workflow caches the converted CSV at
    ``data/raw/eada_cache/eada_<year>.csv`` (the EDA pre-converted
    ``InstLevel.xlsx`` for 2022–23 is already on disk).  The ingestor
    reads the cache by default; the SPA API endpoints above are the
    refresh path for future cycles.
"""

from __future__ import annotations

import csv
import logging
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
from brightsmith.domain_loader import DomainManifest, SourceConfig

logger = logging.getLogger(__name__)


class EadaIngestor(BaseIngestor):
    """Ingests the EADA Athletics Disclosure Survey institution-totals
    file into the bronze zone.

    Data source: ``InstLevel.xlsx`` extracted from the annual EADA zip
    (``EADA_<YYYY-YYYY>.zip``) served by
    ``https://ope.ed.gov/athletics/`` and its SPA backend
    (``/api/dataFiles/file?fileName=...``).  The xlsx is pre-converted
    to CSV at ``data/raw/eada_cache/eada_<year>.csv`` and read by this
    ingestor.

    Grain: institution (UNITID), one row per academic reporting year.

    Key considerations:

    - **No in-pipeline filter required.** ``InstLevel.xlsx`` is already
      one-row-per-UNITID by construction.  ``filter_column`` defaults
      to ``None`` and ``_is_institution_total()`` short-circuits to
      ``True``.  EDA-confirmed 2026-04-30 — see
      ``governance/eda/full-pipeline-eada-raw-eda.md``.
    - **Monetary column names (EDA-confirmed 2026-04-30).** The actual
      column names are ``GRND_TOTAL_EXPENSE``, ``GRND_TOTAL_REVENUE``,
      and ``RECRUITEXP_TOTAL`` (NOT the ``*_TOTAL_TOTAL`` variants
      assumed in the spec working draft).
    - **Identity columns are lowercase** in EADA — ``unitid`` and
      ``institution_name`` (NOT ``UNITID`` / ``INSTNM``).
    - **UNITID coercion is `long`.** EADA may deliver UNITID as int,
      string with quotes, or string with leading zeros.  All variants
      are coerced explicitly to ``int`` (Iceberg ``long``) and
      non-null-asserted on every row.  Rows with an unparseable UNITID
      are dropped with a warning, not silently ignored.
    - **Suppression sentinels** (``""``/blank, ``"-1"``, ``"-2"``) →
      NULL across all numeric fields BEFORE type coercion.  EDA
      observed zero sentinel hits in the 2022–23 institution-totals
      file, but the pre-coercion sentinel scrub remains for safety
      against future cycles.
    - **Reporting year** is encoded in the cache filename only — there
      is no in-row year column.  Stamped from
      ``DEFAULT_REPORTING_YEAR`` (academic year start; 2022 = the
      2022–23 cycle).
    - **User-Agent** header on every download:
      ``FutureProof/0.1 (jeff@hyenastudios.com)``.
    - **Cache-first.** The ingestor reads
      ``data/raw/eada_cache/eada_<year>.csv`` by default and reports
      ``source_method = "csv_cache"``.  An explicit ``bulk_url`` kwarg
      enables the SPA-API refresh path when needed.
    """

    # ------------------------------------------------------------------
    # Source URL / fallback / headers
    # ------------------------------------------------------------------
    # Human-facing landing page (stamped on every row for lineage).  The
    # actual download path goes through the SPA backend at
    # ``/api/dataFiles/file?fileName=EADA_<YYYY-YYYY>.zip`` (discovered
    # during EDA, see governance/eda/full-pipeline-eada-raw-eda.md).
    # Live network fetches are wired via the ``bulk_url`` kwarg; the
    # default fast path reads the local CSV cache.
    BULK_URL_TEMPLATE = "https://ope.ed.gov/athletics/"
    FALLBACK_CSV_PATH = "data/raw/eada_cache"
    USER_AGENT = "FutureProof/0.1 (jeff@hyenastudios.com)"
    DEFAULT_REPORTING_YEAR = 2022

    # ------------------------------------------------------------------
    # EDA-PINNED CONSTANTS
    # ------------------------------------------------------------------
    # EDA-confirmed 2026-04-30, see governance/eda/full-pipeline-eada-raw-eda.md
    # ("EadaIngestor Configuration Pin" section).
    #
    # The institution-totals file (`InstLevel.xlsx` → cached as
    # `data/raw/eada_cache/eada_<year>.csv`) is already one-row-per-UNITID
    # by construction.  No in-pipeline filter is required; the per-team
    # rows live in a separate file (`Schools.xlsx`) which this ingestor
    # does not consume.  ``_is_institution_total()`` short-circuits to
    # ``True`` when ``filter_column is None``.
    INSTITUTION_TOTAL_FILTER_COLUMN: str | None = None
    INSTITUTION_TOTAL_FILTER_VALUE: str | None = None

    # EDA-confirmed 2026-04-30 — actual InstLevel.xlsx column names.  The
    # spec's working assumptions (`EXP_TOTAL_TOTAL`, `REV_TOTAL_TOTAL`,
    # `RECRUITEXP_TOTAL_TOTAL`) do not exist in the file.
    DEFAULT_EXP_COLUMN: str = "GRND_TOTAL_EXPENSE"
    DEFAULT_REV_COLUMN: str = "GRND_TOTAL_REVENUE"
    DEFAULT_RECRUITING_COLUMN: str = "RECRUITEXP_TOTAL"

    # EDA-confirmed 2026-04-30 — EADA's in-file FTE / 12-month enrollment
    # headcount column.  Added 2026-04-30 per spec §5 Option-C amendment;
    # `eada_fte_headcount` is required as the fallback FTE source for
    # institutions missing from `base.ipeds_finance` (~25.5% of EADA
    # reporters, predominantly 2-year colleges).  See spec §3 EDA-correction
    # block and §4 Raw Schema row for `eada_fte_headcount`.
    DEFAULT_FTE_HEADCOUNT_COLUMN: str = "EFTotalCount"

    # EDA-confirmed 2026-04-30 — identity columns are lowercase in EADA
    # (NOT `UNITID` / `INSTNM`).
    UNITID_COLUMN: str = "unitid"
    INSTNM_COLUMN: str = "institution_name"

    # EADA suppression sentinels per spec §4 implementation notes.
    # Treated as NULL across all numeric fields BEFORE type coercion.
    SUPPRESSION_SENTINELS: frozenset[str] = frozenset({"", "-1", "-2"})

    # ------------------------------------------------------------------
    # Init
    # ------------------------------------------------------------------
    def __init__(
        self,
        source_config: SourceConfig,
        manifest: DomainManifest,
        *,
        institution_total_filter_column: str | None | object = ...,
        institution_total_filter_value: str | None | object = ...,
        exp_column: str | None = None,
        rev_column: str | None = None,
        recruiting_column: str | None = None,
        fte_headcount_column: str | None = None,
        reporting_year: int | None = None,
    ) -> None:
        """Construct an EadaIngestor.

        Every column-name and sentinel parameter exists so the
        EDA-pinned configuration can be tuned without a code change.
        Defaults are the EDA-confirmed values pinned 2026-04-30 (see
        ``governance/eda/full-pipeline-eada-raw-eda.md``).

        Args:
            source_config: Brightsmith source config.
            manifest: Brightsmith domain manifest.
            institution_total_filter_column: Override for the column
                whose value distinguishes institution-total rows from
                per-team rows.  Pass ``None`` to disable the filter
                entirely (``_is_institution_total()`` short-circuits to
                ``True``) — appropriate when reading the canonical
                ``InstLevel.xlsx``-derived CSV which is already
                one-row-per-UNITID.  Pass the literal sentinel ``...``
                (Ellipsis, the default) to keep the class default of
                ``None``.
            institution_total_filter_value: Override for the sentinel
                value indicating an institution-total row when a filter
                column is in use.  Pass ``None`` to mean "the column is
                NULL/empty".  Pass the literal sentinel ``...``
                (Ellipsis, the default) to keep the class default.
            exp_column: Override for the total-expenses column name.
                Default ``"GRND_TOTAL_EXPENSE"``.
            rev_column: Override for the total-revenue column name.
                Default ``"GRND_TOTAL_REVENUE"``.
            recruiting_column: Override for the recruiting-expenses
                column name.  Default ``"RECRUITEXP_TOTAL"``.
            fte_headcount_column: Override for the EADA in-file FTE /
                12-month enrollment headcount column.  Default
                ``"EFTotalCount"``.  Captured as ``eada_fte_headcount``
                in the raw schema and used as the §5 Option-C fallback
                FTE source for institutions missing from
                ``base.ipeds_finance``.
            reporting_year: Override for the EADA reporting-cycle year
                stamped on every row.  Default
                ``DEFAULT_REPORTING_YEAR`` (``2022`` for the 2022–23
                cycle).
        """
        super().__init__(source_config, manifest)

        # Use Ellipsis as a sentinel for both filter parameters so
        # callers can explicitly pass ``None`` (= "no filter applied" or
        # "match NULL") without colliding with "use class default".
        if institution_total_filter_column is ...:
            self.filter_column: str | None = self.INSTITUTION_TOTAL_FILTER_COLUMN
        else:
            assert institution_total_filter_column is None or isinstance(
                institution_total_filter_column, str
            ), "institution_total_filter_column must be str | None"
            self.filter_column = institution_total_filter_column

        if institution_total_filter_value is ...:
            self.filter_value: str | None = self.INSTITUTION_TOTAL_FILTER_VALUE
        else:
            assert institution_total_filter_value is None or isinstance(
                institution_total_filter_value, str
            ), "institution_total_filter_value must be str | None"
            self.filter_value = institution_total_filter_value

        self.exp_column: str = exp_column or self.DEFAULT_EXP_COLUMN
        self.rev_column: str = rev_column or self.DEFAULT_REV_COLUMN
        self.recruiting_column: str = (
            recruiting_column or self.DEFAULT_RECRUITING_COLUMN
        )
        self.fte_headcount_column: str = (
            fte_headcount_column or self.DEFAULT_FTE_HEADCOUNT_COLUMN
        )
        self.reporting_year: int = (
            reporting_year if reporting_year is not None else self.DEFAULT_REPORTING_YEAR
        )

        self._prefetched: dict[Any, Any] | None = None

    # ------------------------------------------------------------------
    # Ingest override (capture the true source_method per row)
    # ------------------------------------------------------------------
    def ingest(self, *args: Any, **kwargs: Any) -> dict:
        """Run the BaseIngestor pipeline, fixing source_method post-hoc.

        Mirrors the BEA RPP pattern: the framework otherwise overwrites
        each row's ``source_method`` with the ``method`` argument passed
        to ``ingest()``, but we want the value to reflect whether we
        actually pulled from the bulk URL or fell back to the CSV cache
        — a determination made during ``fetch()``.
        """
        entities = kwargs.pop("entities", None) or self.source.entities
        warehouse_path = kwargs.pop("warehouse_path", None)
        catalog_path = kwargs.pop("catalog_path", None)
        kwargs.pop("method", None)

        raw_data = self.fetch(entities, method="eada", **kwargs)
        sample = next(iter(raw_data.values())) if raw_data else {}
        effective_method: str = sample.get("source_method", "csv_cache")
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
    def fetch(self, entities: dict, method: str, **kwargs: Any) -> dict:
        """Fetch EADA rows via the bulk URL (preferred) or the CSV cache.

        Args:
            entities: ``{entity_id: label}`` from source config.
            method: Fetch method name (informational).
            **kwargs: Supports:
                - ``csv_path``: explicit local CSV path (used in tests;
                  skips the network).
                - ``bulk_url``: explicit override URL.
                - ``force_fallback``: True to skip the network entirely.
                - ``cache_dir``: override default fallback CSV
                  directory (``data/raw/eada_cache``).
                - ``reporting_year``: override the cached file's year
                  suffix (``eada_<year>.csv``).

        Returns:
            ``{entity_id: {"records": [...], "source_method": "..."}}``.
            ``source_method`` is one of ``"bulk_csv_download"`` or
            ``"csv_cache"``.
        """
        # Reuse the payload stashed by ingest() if present (avoids a
        # second network call when ingest() ran fetch() itself).
        prefetched = self._prefetched
        if prefetched:
            return prefetched

        csv_path = kwargs.get("csv_path")
        bulk_url = kwargs.get("bulk_url")
        force_fallback = bool(kwargs.get("force_fallback"))
        cache_dir = kwargs.get("cache_dir")
        cache_year = kwargs.get("reporting_year") or self.reporting_year

        # Explicit CSV path always wins (used in tests).
        if csv_path:
            records = self._read_csv_file(Path(csv_path))
            payload = {"records": records, "source_method": "csv_cache"}
            return {entity_id: payload for entity_id in entities}

        # Try the bulk URL if one was supplied and we aren't forced to
        # fall back.
        if bulk_url and not force_fallback:
            try:
                records = self._fetch_from_bulk_url(bulk_url)
                payload = {
                    "records": records,
                    "source_method": "bulk_csv_download",
                }
                return {entity_id: payload for entity_id in entities}
            except Exception as exc:
                logger.warning(
                    "EADA bulk fetch failed (%s); falling back to CSV cache",
                    exc,
                )

        # Fall back to local CSV cache.
        fallback_dir = Path(cache_dir) if cache_dir else Path(self.FALLBACK_CSV_PATH)
        fallback_path = (
            fallback_dir
            if fallback_dir.is_file()
            else fallback_dir / f"eada_{cache_year}.csv"
        )
        records = self._read_csv_file(fallback_path)
        payload = {"records": records, "source_method": "csv_cache"}
        return {entity_id: payload for entity_id in entities}

    def _fetch_from_bulk_url(self, url: str) -> list[dict]:
        """Download the EADA bulk CSV and parse it into a list of dicts.

        Single attempt — EADA's site is small enough that retry/backoff
        is not justified at this volume.  Caller is expected to fall
        back to the CSV cache on any failure (including HTTP errors,
        non-CSV content types, and parse errors).
        """
        headers = {"User-Agent": self.USER_AGENT}
        response = requests.get(url, headers=headers, timeout=60)
        response.raise_for_status()

        text = response.text
        reader = csv.DictReader(text.splitlines())
        rows = [dict(r) for r in reader]
        if not rows:
            raise ValueError("EADA bulk download returned an empty CSV")
        logger.info("Downloaded %d EADA rows from %s", len(rows), url)
        return rows

    def _read_csv_file(self, path: Path) -> list[dict]:
        """Read a local EADA CSV cache file."""
        with open(path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            rows = [dict(r) for r in reader]
        logger.info("Read %d records from EADA CSV cache %s", len(rows), path)
        return rows

    # ------------------------------------------------------------------
    # Flatten
    # ------------------------------------------------------------------
    def flatten(self, raw_data: Any, entity_id: Any) -> list[dict]:
        """Flatten raw EADA records into Iceberg-ready dicts.

        Steps applied per-row, in order:
            1. Filter out per-team rows using the EDA-pinned
               institution-total marker.  Rows that fail the filter are
               dropped silently (not logged per-row — too noisy for
               ~2,100 rows of survey data).
            2. Apply suppression sentinels (``""``/blank, ``"-1"``,
               ``"-2"``) → NULL across all numeric fields BEFORE
               type coercion.
            3. Coerce ``UNITID`` to ``int`` (Iceberg ``long``).  Rows
               with an unparseable UNITID are dropped with a warning.
            4. Coerce monetary fields to ``float`` (Iceberg ``double``).
            5. Stamp ``reporting_year`` from the configured constant.

        Framework metadata (``ingested_at``, ``source_url``,
        ``source_method``, ``load_date``) is added by
        ``BaseIngestor.ingest()`` after this method returns.

        Args:
            raw_data: dict with keys ``records`` and ``source_method``.
            entity_id: logical entity id (unused — single entity).

        Returns:
            List of flat dicts ready for Iceberg append.
        """
        records: list[dict] = raw_data["records"]

        flat_rows: list[dict] = []
        per_team_filtered = 0
        unparseable_unitid = 0

        for row in records:
            # 1. Institution-total filter.
            if not self._is_institution_total(row):
                per_team_filtered += 1
                continue

            # 3. UNITID coercion (run before sentinel-stripping the
            # numeric fields so we can drop bad-UNITID rows early).
            unitid = self._coerce_long(row.get(self.UNITID_COLUMN))
            if unitid is None:
                unparseable_unitid += 1
                logger.warning(
                    "Dropping EADA row with unparseable UNITID: %r",
                    row.get(self.UNITID_COLUMN),
                )
                continue

            # 2 + 4. Sentinel-strip then coerce monetary + FTE fields.
            total_athletic_expenses = self._coerce_double(
                self._strip_sentinel(row.get(self.exp_column))
            )
            total_athletic_revenue = self._coerce_double(
                self._strip_sentinel(row.get(self.rev_column))
            )
            recruiting_expenses = self._coerce_double(
                self._strip_sentinel(row.get(self.recruiting_column))
            )
            # EADA's in-file FTE (12-month enrollment headcount).  Same
            # sentinel-then-coerce pattern as the monetary fields — see
            # spec §5 Option-C amendment.
            eada_fte_headcount = self._coerce_double(
                self._strip_sentinel(row.get(self.fte_headcount_column))
            )

            record = {
                "unitid": unitid,
                "institution_name": self._coerce_string(row.get(self.INSTNM_COLUMN)),
                "reporting_year": self.reporting_year,
                "total_athletic_expenses": total_athletic_expenses,
                "total_athletic_revenue": total_athletic_revenue,
                "recruiting_expenses": recruiting_expenses,
                "eada_fte_headcount": eada_fte_headcount,
            }
            flat_rows.append(record)

        if per_team_filtered:
            logger.info(
                "Filtered %d EADA per-team rows (kept %d institution totals)",
                per_team_filtered,
                len(flat_rows),
            )
        if unparseable_unitid:
            logger.warning(
                "Dropped %d EADA rows with unparseable UNITID values",
                unparseable_unitid,
            )

        return flat_rows

    def get_source_url(self, entity_id: Any, method: str) -> str:
        """Return the source URL stamped on every row for lineage.

        Always points at the EADA landing page rather than a transient
        bulk URL, so audit trails remain stable across runs.
        """
        return self.BULK_URL_TEMPLATE

    # ------------------------------------------------------------------
    # Filter / sentinel / coercion helpers
    # ------------------------------------------------------------------
    def _is_institution_total(self, row: dict) -> bool:
        """Return True iff the row is an institution-total (not per-team).

        EDA-confirmed 2026-04-30: when ``filter_column`` is ``None``
        (the default — applies when reading the canonical
        ``InstLevel.xlsx`` institution-totals file), there is no filter
        to apply and every row is by construction an institution total.
        We short-circuit to ``True`` in that case.

        Otherwise the marker is configurable: when ``filter_value`` is
        ``None`` we treat NULL/blank as the institution-total signal;
        otherwise we match the configured sentinel string exactly,
        case-insensitively.  This branch supports a fallback path
        against future EADA format changes (e.g. a mixed file).
        """
        if self.filter_column is None:
            return True
        cell = row.get(self.filter_column)
        if self.filter_value is None:
            # Institution total iff the column is NULL/blank.
            return cell is None or (isinstance(cell, str) and cell.strip() == "")
        if cell is None:
            return False
        cell_str = cell.strip() if isinstance(cell, str) else str(cell)
        return cell_str.casefold() == self.filter_value.casefold()

    @classmethod
    def _strip_sentinel(cls, value: Any) -> Any:
        """Replace EADA suppression sentinels with ``None``.

        Applied BEFORE numeric coercion per spec §4.  Sentinels are
        compared as stripped strings so ``" -1 "`` and ``"-1"`` are
        treated identically.  Non-string values pass through unchanged.
        """
        if value is None:
            return None
        if isinstance(value, str):
            stripped = value.strip()
            if stripped in cls.SUPPRESSION_SENTINELS:
                return None
            return stripped
        return value

    @staticmethod
    def _coerce_long(value: Any) -> int | None:
        """Coerce UNITID to ``int`` (Iceberg ``long``).

        Handles int, float, plain string, quoted string, and
        leading-zero string variants.  Returns ``None`` on failure;
        callers drop rows with ``None`` UNITIDs (UNITID is required
        non-null per the schema).
        """
        if value is None:
            return None
        if isinstance(value, bool):  # bool is a subclass of int — exclude
            return None
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            if value != value:  # NaN
                return None
            return int(value)
        if isinstance(value, str):
            s = value.strip().strip('"').strip("'")
            if not s:
                return None
            # Handle leading zeros and trailing decimals.
            try:
                return int(s)
            except ValueError:
                try:
                    return int(float(s))
                except (ValueError, TypeError):
                    return None
        return None

    @staticmethod
    def _coerce_double(value: Any) -> float | None:
        """Coerce a sentinel-stripped value to ``float`` (Iceberg ``double``)."""
        if value is None:
            return None
        if isinstance(value, bool):
            return None
        if isinstance(value, (int, float)):
            f = float(value)
            if f != f:  # NaN
                return None
            return f
        if isinstance(value, str):
            s = value.strip().replace(",", "").replace("$", "")
            if not s:
                return None
            try:
                return float(s)
            except (ValueError, TypeError):
                return None
        return None

    @staticmethod
    def _coerce_string(value: Any) -> str | None:
        if value is None:
            return None
        s = str(value).strip()
        return s if s else None

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------
    def get_schema(self) -> Schema:
        """Define the Iceberg table schema for ``raw.eada``.

        Matches the spec §4 Raw Schema exactly (post-2026-04-30
        Option-C amendment).  Field IDs 1-7 are the EADA payload; 8-11
        are framework metadata stamped by ``BaseIngestor.ingest()``.

        Field 7 (``eada_fte_headcount``) was added 2026-04-30 to support
        the §5 Option-C COALESCE FTE source.  See spec §3 EDA-correction
        block and §4 Raw Schema row.
        """
        return Schema(
            # Grain field
            NestedField(1, "unitid", LongType(), required=True),
            # Data fields
            NestedField(2, "institution_name", StringType(), required=True),
            NestedField(3, "reporting_year", IntegerType(), required=True),
            NestedField(4, "total_athletic_expenses", DoubleType(), required=False),
            NestedField(5, "total_athletic_revenue", DoubleType(), required=False),
            NestedField(6, "recruiting_expenses", DoubleType(), required=False),
            NestedField(7, "eada_fte_headcount", DoubleType(), required=False),
            # Framework metadata
            NestedField(8, "source_url", StringType(), required=True),
            NestedField(9, "source_method", StringType(), required=True),
            NestedField(10, "ingested_at", TimestampType(), required=True),
            NestedField(11, "load_date", DateType(), required=True),
        )
